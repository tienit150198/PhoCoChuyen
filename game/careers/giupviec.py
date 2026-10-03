"""Giúp việc theo giờ: tổ Nhà Thơm của cô Mai (plugin career).

Cô Mai has cleaned homes by the hour for twenty years; now she keeps the booking book and the player goes
from flat to flat with the cleaning cart. The family home of the Nội trợ career is one household all day;
this job is many households, a few rooms each, paid per job. What the job is:

* the morning (``setup`` task): wash yesterday's cloths and top up the bottles on the cart (each bottle
  holds BOTTLE uses; a fresh one comes from the stock room), then set off;
* a job (``job`` task) is one client's flat: ring the bell and hear what they say (``ask``), then work
  room by room. In a room every surface is a spot with some dirt; the player picks a tool and a product
  from the cart and taps the spot, one wipe at a time. The right pair takes a layer off; a wrong tool or
  product does nothing (time lost), a harsh one damages the surface, the red toilet cloth anywhere but
  the toilet spreads germs. Top to bottom, dry before wet: cleaning a higher spot drops dust on the
  lower ones already done (they need another wipe), and mopping before sweeping only smears the dust;
* the client's words and things: a surface to leave alone (the work desk), a cat to carry out before the
  vacuum, a toddler or a cat at home (floors with clean water only), a fragile vase to lift off and put
  back, a ring or a watch to put in the little tray for the client;
* the walk-through (``gv_check``): the client walks every room; what is still dirty, broken or out of
  place is named, the reaction settles the pay (consequences), the pay comes by transfer; a job with
  nothing to say makes the client a regular, who adds a little to the next job; tips come from the
  shared tips rules;
* the apprenticeship: on the first APPRENTICE jobs cô Mai comes along and stops each kind of mistake
  once before it happens (nothing recorded).

Mistakes go through consequences (cq.slip / cq.react); money only through the engine's money().
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from .. import consequences as cq
from . import giupviec_content as gc

ID = 'giupviec'
GEN = 1

PEOPLE = gc.PEOPLE
TOOLS = gc.TOOLS
PRODUCTS = gc.PRODUCTS
SPOTS = gc.SPOTS
ROOMS = gc.ROOMS
ITEMS_CARE = gc.ITEMS_CARE
HOMES = gc.HOMES
NOTES = gc.NOTES
JOBS = gc.JOBS
KINDS = gc.KINDS
STAGES = gc.STAGES
MODS = gc.MODS
MOD = {m['id']: m for m in MODS}
DESK = gc.DESK
SITUATIONS = gc.SITUATIONS
REG_STORY = gc.REG_STORY
INTRO = gc.INTRO
APPRENTICE = gc.APPRENTICE
LESSONS = gc.LESSONS
CATCH = gc.CATCH

ITEMS = [
    dict(id='chai_kinh', name='Chai nước lau kính', emoji='🫧', group='chai', unit='chai', cost=3, start=2),
    dict(id='chai_da_nang', name='Chai tẩy rửa dịu', emoji='🧴', group='chai', unit='chai', cost=3, start=2),
    dict(id='chai_dau_mo', name='Chai tẩy dầu mỡ', emoji='🍋', group='chai', unit='chai', cost=4, start=2),
    dict(id='chai_toilet', name='Chai tẩy bồn cầu', emoji='🧪', group='chai', unit='chai', cost=3, start=2),
    dict(id='chai_lau_san', name='Can nước lau sàn', emoji='🌸', group='chai', unit='can', cost=4, start=2),
]
PRICES = dict(room=12)
REGULAR_BONUS = 4          # a happy client adds this to the next job
TET_BONUS = 6              # the big clean before the holidays
BOTTLE = 12                # wipes in one bottle on the cart
BOTTLE_LOW = 3             # setting off with less than this in a bottle today's jobs need is a slip
WASTE_PATIENCE = 3         # a wipe that does nothing: the client's time
REDO_PATIENCE = 2          # a spot done again because dust fell on it
MAX_DIRT = 3

# ================================================================ small helpers
def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Khách'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def key_of(room: str, spot: str) -> str:
    return f'{room}.{spot}'


def spot_rows(n: dict) -> list:
    """[(room, spot id, key, dirt at the start, focus)] of a job, room by room."""
    return [(r['id'], x['id'], key_of(r['id'], x['id']), x['dirt'], x['focus']) for r in n['rooms'] for x in r['spots']]


def right_products(n: dict, spot: str) -> tuple:
    """The products that clean this spot in this home (a cat or a toddler: floors with clean water only)."""
    if n.get('gentle') and spot in gc.FLOOR_WET:
        return ('nuoc',)
    return SPOTS[spot]['products']


# ================================================================ tasks
def _job_for(day: int, slot: int, mod: str) -> tuple:
    """The booking of this slot; the clients of the earlier slots that day are left out (one visit a day each)."""
    if day == 1:
        return JOBS[(slot - 1) % 3]
    seen, pick = set(), None
    for s in range(1, slot + 1):
        pool = [j for j in JOBS if j[4] <= day and j[5] in (None, mod)]
        fresh = [j for j in pool if j[0] not in seen] or pool
        weighted = [j for j in fresh for _ in range(3 if j[5] else 1)]
        pick = weighted[kit.rng(ID, day, s).randrange(len(weighted))]
        seen.add(pick[0])
    return pick


def _rooms_for(day: int, slot: int, home: dict, fixed, mod: str) -> list:
    if fixed:
        return list(fixed)
    r = kit.rng(ID, 'rooms', day, slot)
    ids = list(home['rooms'])
    tier = kit.tier(day)
    n = 2 if tier == 0 else r.choice((2, 3)) if tier == 1 else 3
    if mod == 'tet':
        n += 1
    n = min(n, len(ids))
    pick = set(r.sample(ids, n))
    return [x for x in ids if x in pick]


def _spots_for(day: int, slot: int, room: str, home: dict, mod: str) -> list:
    always, optional = home['rooms'][room]
    r = kit.rng(ID, 'spots', day, slot, room)
    tier = kit.tier(day)
    k = min(len(optional), 0 if tier == 0 and r.random() < .5 else 1 if tier <= 1 else 2)
    chosen = list(always) + [x for x in optional if x in set(r.sample(list(optional), k))]
    out = []
    for sid in chosen:
        sp = SPOTS[sid]
        dirt = 1 + (r.random() < .4)
        if mod == 'bui' and sp['lvl'] == 0:
            dirt += 1
        if mod == 'mua' and sp['lvl'] >= 2:
            dirt += 1
        if mod == 'nom' and (sp['lvl'] == 3 or 'khan_xanh' in sp['tools']):
            dirt += 1
        if mod == 'tet':
            dirt += 1
        out.append(dict(id=sid, dirt=min(MAX_DIRT, dirt), focus=False))
    # The way the room looks, not the order to clean it in.
    out.sort(key=lambda x: _hash('gv-order', day, slot, room, x['id']))
    return out


def _fresh_fields() -> dict:
    return dict(gen=GEN, stage='work', room=None, dirt={}, items={}, touched=[], scrubs=0, waste=0, redo=0,
                price=None, regular=False, check=None, story=None)


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    if slot == 0:
        note = {'mua': 'Mưa dầm: sàn nhà khách nhiều bùn, mang đủ nước lau sàn.', 'nom': 'Trời nồm: gương kính đọng nước, châm đầy chai lau kính.',
                'tet': 'Mùa tổng vệ sinh: nhà nào cũng bẩn hơn, châm đầy mọi chai.'}.get(mod, 'Giặt khăn hôm qua, châm các chai trên xe rồi lên đường.')
        return kit.base_task(ID, day, slot, serial, 0, 'Soạn xe đồ nghề đầu ngày',
                             'Cô Mai nhắn: “Hôm nay lịch kín nhé con. Giặt khăn hôm qua, châm đầy mấy chai trên xe rồi hẵng đi.”',
                             kind='setup', needs=dict(setup=True, note=note), **_fresh_fields())
    i, title, opening, fixed, _, _ = _job_for(day, slot, mod)
    home = HOMES[i]
    rooms = [dict(id=rid, spots=_spots_for(day, slot, rid, home, mod)) for rid in _rooms_for(day, slot, home, fixed, mod)]
    keys = {key_of(r['id'], x['id']) for r in rooms for x in r['spots']}
    notes = list(home['notes'])
    skip = [key_of(*gc.SKIP[n]) for n in notes if n in gc.SKIP and key_of(*gc.SKIP[n]) in keys]
    r = kit.rng(ID, 'focus', day, slot)
    focus = []
    if 'glove' in notes:
        focus = [key_of(rm['id'], x['id']) for rm in rooms for x in rm['spots'] if SPOTS[x['id']]['lvl'] == 0]
    elif day >= 2 and r.random() < .35:
        pool = [key_of(rm['id'], x['id']) for rm in rooms for x in rm['spots'] if SPOTS[x['id']]['lvl'] == 1
                and key_of(rm['id'], x['id']) not in skip]
        focus = [r.choice(pool)] if pool else []
    for rm in rooms:
        for x in rm['spots']:
            if key_of(rm['id'], x['id']) in focus:
                x['focus'] = True
                x['dirt'] = max(2, x['dirt'])
    items = [dict(id=iid, room=room, spot=spot) for iid, room, spot in home['items'] if key_of(room, spot) in keys]
    say = [NOTES[n][2] for n in notes]
    if focus and 'glove' not in notes:
        rm, sid = focus[0].split('.')
        say.append(f'{PEOPLE[i][0]} dặn thêm: “{SPOTS[sid]["name"]} {_lower(ROOMS[rm]["name"])} lau kỹ giúp nhé.”')
    needs = dict(home=i, place=home['place'], rooms=rooms, items=items, notes=notes, skip=skip,
                 gentle=any(n in gc.GENTLE for n in notes), tet=mod == 'tet', note=' '.join(say))
    return kit.base_task(ID, day, slot, serial, i, title, opening, kind='job', needs=needs, **_fresh_fields())


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
        return
    if not t['dirt']:
        t['dirt'] = {k: d for _, _, k, d, _ in spot_rows(t['needs'])}
        t['items'] = {x['id']: 'on' for x in t['needs']['items']}
    d = _data(c)
    reg = d['regulars'].get(str(_npc_index(t)))
    t['regular'] = bool(reg and reg.get('happy'))


# ================================================================ the career's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, jobs=0, rooms=0, wipes=0, redo=0, perfect=0, earned=0)


def initial() -> dict:
    return dict(v=1, intro=False, cart=dict(day=0, cloths='dirty', out=False, bottles={p: BOTTLE // 2 for p in gc.BOTTLES}),
                hand=dict(tool=None, product=None), regulars={}, today=_fresh_today(0),
                stats=dict(jobs=0, rooms=0, wipes=0, redo=0, perfect=0, broke=0, kept=0), desk=kit.desk_initial(),
                learn=dict(task=None, codes=[], done=False))


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'cart', 'hand', 'learn'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, copy.deepcopy(v))
    for p in gc.BOTTLES:
        d['cart']['bottles'].setdefault(p, 0)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


def learning(d: dict) -> bool:
    """Học nghề: the first APPRENTICE jobs, cô Mai along."""
    return not d['learn']['done'] and d['stats']['jobs'] < APPRENTICE


def _catch(d: dict, t: dict, code: str) -> dict | None:
    """While learning, cô Mai stops each kind of mistake once before it happens (nothing recorded)."""
    if not learning(d) or code not in CATCH:
        return None
    lr = d['learn']
    if lr['task'] != t['id']:
        lr['task'], lr['codes'] = t['id'], []
    if code in lr['codes']:
        return None
    lr['codes'].append(code)
    return dict(message=f'🧺 Cô Mai: “{CATCH[code]}”', correct=False, lesson=code)


# ================================================================ the actions
FREE = ('gv_intro',)
NO_TICK = ('gv_intro', 'gv_desk', 'gv_tool', 'gv_product', 'gv_fill', 'gv_wipe', 'gv_move', 'gv_back')
PHYSICAL = ('gv_check',)


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'gv_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Xe đồ nghề đang chờ ở sảnh.')
    desk = d['desk']
    if name == 'gv_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện cần quyết, xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có trong việc dọn nhà.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    if learning(d):
        return             # no surprises while cô Mai is still teaching
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tổ giúp việc.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_out(d: dict) -> None:
    kit.need(d['cart']['out'], 'Chưa soạn xe: giặt khăn, châm chai rồi bấm “Lên đường” nhé.')


def _need_work(t: dict) -> None:
    kit.need(t['known'], 'Bấm chuông, nghe khách dặn đã nhé.')
    kit.need(t['stage'] == 'work', 'Nhà này dọn xong rồi.')


# ---------------------------------------------------------------- the cart (morning)
def _wash(s, c, d, p):
    cart = d['cart']
    kit.need(cart['cloths'] != 'clean', 'Khăn sạch rồi.')
    cart['cloths'] = 'clean'
    return dict(message='🧺 Giặt khăn bằng nước ấm, vắt kiệt, phơi khô. Xanh, vàng, đỏ, mỗi màu một chồng.')


def _fill(s, c, d, p):
    v = kit.one_of(p.get('product'), gc.BOTTLES, 'Trên xe không có chai này.')
    x = PRODUCTS[v]
    left = d['cart']['bottles'][v]
    kit.need(left < BOTTLE, f'Chai {_lower(x["name"])} còn đầy.')
    kit.need(kit.stock(c, x['item']) > 0, f'Hết {_lower(kit.item(ID, x["item"])["name"])} trong kho. Nhập thêm ở Kho nhé.')
    cost = kit.take(c, x['item'], 1)
    if left and cost:
        kit.waste(c, x['item'], 1, cost * left // BOTTLE, 'Chai cũ còn dư khi thay')
    d['cart']['bottles'][v] = BOTTLE
    return dict(message=f'{x["emoji"]} Châm đầy chai {_lower(x["name"])}: đủ {BOTTLE} lần lau.' + (f' Chai cũ còn {left} lần thì đổ chung.' if left else ''))


def _today_products(c: dict) -> set:
    out = set()
    for t in c['tasks']:
        if t.get('career') == ID and t['kind'] == 'job' and t['day'] == c['day'] and t['status'] not in ('completed', 'cancelled', 'referred'):
            for _, sid, _, _, _ in spot_rows(t['needs']):
                for pr in right_products(t['needs'], sid):
                    if PRODUCTS[pr]['item']:
                        out.add(pr)
                        break
    return out


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    cart = d['cart']
    kit.need(not cart['out'], 'Xe đã lên đường rồi.')
    if cart['cloths'] != 'clean':
        t['mistakes'] += 1
        cq.slip(t, 'cloths', 1, 'Khăn hôm qua chưa giặt, mùi chua, lau đâu dính bẩn đó.', 'khăn chưa giặt')
    low = [pr for pr in sorted(_today_products(c)) if cart['bottles'][pr] < BOTTLE_LOW]
    if low:
        t['mistakes'] += 1
        cq.slip(t, 'bottle', 1, f'Chai {_lower(PRODUCTS[low[0]]["name"])} sắp cạn mà không châm, tới nhà khách thì hết.', 'chai sắp cạn')
    cart['out'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Giặt khăn, châm chai, lên đường.')
    return dict(message='🛵 Lên đường! ' + ('Cô Mai nhắn: “Xe gọn gàng thế là chuẩn, đi cẩn thận nhé.”' if ok else 'Cô Mai nhắn: “Đi đi con, mai nhớ soạn xe kỹ hơn.”'),
                celebrate=ok)


# ---------------------------------------------------------------- in a client's flat
def _room(s, c, d, p):
    t = _task(c, p, ('job',))
    _need_out(d)
    _need_work(t)
    rid = kit.one_of(p.get('room'), [r['id'] for r in t['needs']['rooms']], 'Nhà này không có phòng đó.')
    kit.need(t['room'] != rid, 'Đang ở phòng này rồi.')
    t['room'] = rid
    kit.start_work(t)
    left = sum(1 for room, _, k, _, _ in spot_rows(t['needs']) if room == rid and t['dirt'].get(k, 0) > 0 and k not in t['needs']['skip'])
    return dict(message=f'{ROOMS[rid]["emoji"]} Sang {_lower(ROOMS[rid]["name"])}: còn {left} chỗ cần dọn.')


def _tool(s, c, d, p):
    v = kit.one_of(p.get('tool'), TOOLS, 'Trên xe không có dụng cụ này.')
    d['hand']['tool'] = v
    x = TOOLS[v]
    return dict(message=f'{x["emoji"]} Cầm {_lower(x["name"])}.')


def _product(s, c, d, p):
    v = kit.one_of(p.get('product'), PRODUCTS, 'Trên xe không có chai này.')
    d['hand']['product'] = v
    x = PRODUCTS[v]
    return dict(message=f'{x["emoji"]} {"Không dùng gì, lau khô." if v == "kho" else "Dùng " + _lower(x["name"]) + "."}')


def _item_on(t: dict, room: str, spot: str) -> dict | None:
    for x in t['needs']['items']:
        if x['room'] == room and x['spot'] == spot and t['items'].get(x['id']) == 'on':
            return x
    return None


def _wasted(t: dict, d: dict) -> None:
    t['waste'] = min(999, t['waste'] + 1)
    t['patience'] = max(25, t.get('patience', 100) - WASTE_PATIENCE)


def _wipe(s, c, d, p):
    """One wipe of one spot with what is in hand."""
    t = _task(c, p, ('job',))
    _need_out(d)
    _need_work(t)
    n = t['needs']
    kit.need(t['room'], 'Chọn phòng để dọn trước đã.')
    sid = kit.one_of(p.get('spot'), [x['id'] for r in n['rooms'] if r['id'] == t['room'] for x in r['spots']], 'Phòng này không có chỗ đó.')
    key = key_of(t['room'], sid)
    sp = SPOTS[sid]
    tool, prod = d['hand']['tool'], d['hand']['product']
    kit.need(tool, 'Chọn dụng cụ trên xe trước đã.')
    kit.need(prod, 'Chọn chai (hoặc lau khô) trước đã.')
    kit.start_work(t)
    who = _who(t)
    # the client said to leave it alone
    if key in n['skip']:
        caught = _catch(d, t, 'skip')
        if caught:
            return caught
        if key not in t['touched']:
            t['touched'].append(key)
            t['mistakes'] += 1
            cq.slip(t, 'skip', 2, f'Tôi dặn để nguyên {_lower(sp["name"])} mà, giờ giấy tờ lộn xộn hết.', f'động vào {_lower(sp["name"])} khách dặn để nguyên')
        return dict(message=f'⚠️ {who} đã dặn để nguyên {_lower(sp["name"])}!', correct=False)
    # something sits on it
    item = _item_on(t, t['room'], sid)
    if item:
        it = ITEMS_CARE[item['id']]
        caught = _catch(d, t, it['kind'])
        if caught:
            return caught
        t['mistakes'] += 1
        if it['kind'] == 'fragile':
            if _hash('gv-break', t['id'], item['id']) % 2 == 0:
                t['items'][item['id']] = 'broken'
                d['stats']['broke'] += 1
                cq.slip(t, 'broke', 3, it['broke'], f'làm vỡ {_lower(it["name"])}')
                due = min(c['money'], it['comp'])
                if due:
                    kit.money(s, c, -due, f'Đền {_lower(it["name"])}: {t["title"]}'[:120], t['id'], 'compensation')
                return dict(message=f'💥 {it["broke"]}' + (f' Đền {due} xu.' if due else ''), correct=False)
            cq.slip(t, 'wobble', 1, f'Lau mà không nhấc {_lower(it["name"])} ra, suýt rơi.', f'không nhấc {_lower(it["name"])} ra')
            return dict(message=f'😰 {it["name"]} chao đảo, may mà kịp giữ! Nhấc ra trước đã.', correct=False)
        if it['kind'] == 'valuable':
            t['items'][item['id']] = 'safe'
            t['patience'] = max(25, t.get('patience', 100) - 10)
            cq.slip(t, 'lost_' + item['id'][:20], 2, it['lost'], f'không cất {_lower(it["name"])} trước khi lau')
            return dict(message=f'😱 {it["lost"]} Bạn lấy lại được, cất vào khay.', correct=False)
        t['items'][item['id']] = 'off'     # the pet runs off
        cq.slip(t, 'pet', 1, it['lost'], 'làm mèo hoảng')
        return dict(message=f'🙀 {it["lost"]}', correct=False)
    if t['dirt'].get(key, 0) <= 0:
        return dict(message=f'✨ {sp["name"]} sạch rồi.')
    # the red cloth is for the toilet only
    if tool == 'khan_do' and sid != 'bon_cau':
        caught = _catch(d, t, 'red_cloth')
        if caught:
            return caught
        t['mistakes'] += 1
        cq.slip(t, 'red_cloth', 2, f'Lấy khăn lau bồn cầu đi lau {_lower(sp["name"])}! Mất vệ sinh quá.', 'khăn bồn cầu lau chỗ khác')
        _wasted(t, d)
        return dict(message=f'🟥 Khăn đỏ là khăn bồn cầu: lau {_lower(sp["name"])} bằng khăn này là mang bẩn đi khắp nhà.', correct=False)
    # a harsh tool or product on this surface
    harm = sp['harm'].get(prod) or sp['harm'].get(tool)
    if n.get('gentle') and sid in gc.FLOOR_WET and prod not in ('nuoc',) and prod != 'kho':
        harm = harm or (2, 'Nhà có bé (có mèo) mà lau sàn bằng hóa chất, mùi nồng cả buổi.', 'lau sàn bằng hóa chất')
        code = 'gentle'
    else:
        code = 'harm'
    if harm:
        caught = _catch(d, t, code)
        if caught:
            return caught
        t['mistakes'] += 1
        cq.slip(t, code if code == 'gentle' else 'harm_' + sid[:20], harm[0], harm[1], harm[2])
        _use(d, prod)
        _wasted(t, d)
        return dict(message=f'⚠️ {harm[1]}', correct=False)
    if tool not in sp['tools']:
        _wasted(t, d)
        return dict(message=f'🤔 {TOOLS[tool]["name"]} không hợp với {_lower(sp["name"])} ({sp["mat"]}). Đổi dụng cụ khác.', correct=False)
    if prod not in right_products(n, sid):
        if PRODUCTS[prod]['item']:
            kit.need(d['cart']['bottles'][prod] > 0, f'Chai {_lower(PRODUCTS[prod]["name"])} cạn rồi. Châm ở xe đồ nghề nhé.')
            _use(d, prod)
        _wasted(t, d)
        return dict(message=f'🤔 {PRODUCTS[prod]["name"]} không làm sạch {sp["mat"]} được. Đổi chai khác.', correct=False)
    if PRODUCTS[prod]['item']:
        kit.need(d['cart']['bottles'][prod] > 0, f'Chai {_lower(PRODUCTS[prod]["name"])} cạn rồi. Châm ở xe đồ nghề nhé.')
    # dry before wet: mopping a floor still dusty only smears it
    if sp['lvl'] == 3:
        dusty = [k for room, s2, k, _, _ in spot_rows(n) if room == t['room'] and SPOTS[s2]['lvl'] == 2 and t['dirt'].get(k, 0) > 0]
        if dusty:
            caught = _catch(d, t, 'wet_first')
            if caught:
                return caught
            _use(d, prod)
            _wasted(t, d)
            return dict(message='💧 Sàn còn bụi tóc: lau ướt chỉ làm bụi bết thành vệt. Quét trước, lau sau.', correct=False)
    _use(d, prod)
    t['dirt'][key] -= 1
    t['scrubs'] = min(9999, t['scrubs'] + 1)
    d['today']['wipes'] += 1
    d['stats']['wipes'] += 1
    if t['dirt'][key] > 0:
        return dict(message=f'{TOOLS[tool]["emoji"]} Lau {_lower(sp["name"])}… còn {t["dirt"][key]} lượt nữa.', correct=True)
    # top to bottom: dust falls on what is below and already clean
    fell = []
    if sp['lvl'] < 3:
        for room, s2, k, d0, _ in spot_rows(n):
            if room == t['room'] and k != key and SPOTS[s2]['lvl'] > sp['lvl'] and d0 > 0 and t['dirt'].get(k, 0) == 0 and k not in n['skip']:
                t['dirt'][k] = 1
                fell.append(SPOTS[s2]['name'])
    msg = f'✨ {sp["name"]} sạch bong.'
    if fell:
        t['redo'] = min(999, t['redo'] + len(fell))
        d['today']['redo'] += len(fell)
        d['stats']['redo'] += len(fell)
        t['patience'] = max(25, t.get('patience', 100) - REDO_PATIENCE * len(fell))
        msg += f' Nhưng bụi rơi xuống {", ".join(_lower(x) for x in fell)} vừa lau: phải lau lại.'
    return dict(message=msg, correct=not fell)


def _use(d: dict, prod: str) -> None:
    if PRODUCTS.get(prod, {}).get('item') and d['cart']['bottles'][prod] > 0:
        d['cart']['bottles'][prod] -= 1


def _move(s, c, d, p):
    t = _task(c, p, ('job',))
    _need_work(t)
    x = next((i for i in t['needs']['items'] if i['id'] == p.get('item')), None)
    kit.need(x, 'Không có món này.')
    kit.need(t['room'] == x['room'], f'{ITEMS_CARE[x["id"]]["name"]} ở {_lower(ROOMS[x["room"]]["name"])}.')
    kit.need(t['items'].get(x['id']) == 'on', 'Món này đã cất rồi.')
    it = ITEMS_CARE[x['id']]
    kit.start_work(t)
    if it['kind'] == 'valuable':
        t['items'][x['id']] = 'safe'
        return dict(message=f'{it["emoji"]} Cất {_lower(it["name"])} vào khay nhỏ trên kệ. Lát báo {_who(t)}.')
    t['items'][x['id']] = 'off'
    if it['kind'] == 'pet':
        return dict(message=f'{it["emoji"]} Bế Mướp sang phòng ngủ, khép cửa. Mướp ngáp một cái rồi ngủ tiếp.')
    return dict(message=f'{it["emoji"]} Nhấc {_lower(it["name"])} ra, đặt lên khăn mềm ở góc an toàn.')


def _back(s, c, d, p):
    t = _task(c, p, ('job',))
    _need_work(t)
    x = next((i for i in t['needs']['items'] if i['id'] == p.get('item')), None)
    kit.need(x and ITEMS_CARE[x['id']]['kind'] == 'fragile', 'Không có món này.')
    kit.need(t['room'] == x['room'], f'{ITEMS_CARE[x["id"]]["name"]} ở {_lower(ROOMS[x["room"]]["name"])}.')
    kit.need(t['items'].get(x['id']) == 'off', 'Món này đang ở chỗ cũ.')
    t['items'][x['id']] = 'back'
    it = ITEMS_CARE[x['id']]
    return dict(message=f'{it["emoji"]} Đặt {_lower(it["name"])} lại đúng chỗ cũ, xoay đúng mặt như lúc đầu.')


# ---------------------------------------------------------------- the walk-through
def check_slips(t: dict) -> list:
    """What the client will notice walking through now: (code, sev, words, note)."""
    n = t['needs']
    out = []
    dirty = [(room, sid, focus) for room, sid, k, _, focus in spot_rows(n) if k not in n['skip'] and t['dirt'].get(k, 0) > 0]
    foc = [x for x in dirty if x[2]]
    if foc:
        room, sid, _ = foc[0]
        out.append(('focus', 2, f'Tôi dặn lau kỹ {_lower(SPOTS[sid]["name"])} mà vẫn còn bẩn.', 'chỗ khách dặn kỹ vẫn bẩn'))
    rest = [x for x in dirty if not x[2]]
    if rest:
        room, sid, _ = rest[0]
        more = f' và {len(rest) - 1} chỗ nữa' if len(rest) > 1 else ''
        out.append(('dirty', 1 if len(rest) <= 2 else 2, f'{SPOTS[sid]["name"]} {_lower(ROOMS[room]["name"])} vẫn bẩn{more}.', 'còn chỗ chưa sạch'))
    for x in n['items']:
        it = ITEMS_CARE[x['id']]
        if it['kind'] == 'fragile' and t['items'].get(x['id']) == 'off':
            out.append(('not_back', 1, f'{it["name"]} để dưới góc, không đặt lại chỗ cũ.', 'không đặt đồ lại chỗ cũ'))
    return out


def _check(s, c, d, p):
    t = _task(c, p, ('job',))
    _need_out(d)
    _need_work(t)
    kit.need(t['room'] or t['scrubs'], 'Chưa dọn chỗ nào. Chọn phòng để bắt đầu nhé.')
    found = check_slips(t)
    for code, *_ in found:
        caught = _catch(d, t, code)
        if caught:
            return caught
    who = _who(t)
    n = t['needs']
    lines = []
    for r in n['rooms']:
        bad = [SPOTS[x['id']]['name'] for x in r['spots'] if key_of(r['id'], x['id']) not in n['skip'] and t['dirt'].get(key_of(r['id'], x['id']), 0) > 0]
        lines.append(dict(room=r['id'], ok=not bad, note=', '.join(bad[:2])))
    for code, sev, words, note in found:
        t['mistakes'] += 1
        cq.slip(t, code, sev, words, note)
    kept = [ITEMS_CARE[x['id']] for x in n['items'] if ITEMS_CARE[x['id']]['kind'] == 'valuable' and t['items'].get(x['id']) == 'safe'
            and not any(r['code'] == 'lost_' + x['id'][:20] for r in cq.slips(t))]
    price = len(n['rooms']) * max(1, int(kit.price(c, 'room', PRICES['room']))) + (REGULAR_BONUS if t['regular'] else 0) + (TET_BONUS if n.get('tet') else 0)
    t['price'] = price
    t['check'] = lines
    react = cq.react(s, c, t, price, who=who)
    pay = react['pay']
    i = str(_npc_index(t))
    clean = not cq.slips(t)
    reg = d['regulars'].setdefault(i, dict(visits=0, happy=False))
    reg['visits'] = min(999, reg['visits'] + 1)
    reg['happy'] = clean
    d['today']['jobs'] += 1
    d['stats']['jobs'] += 1
    d['today']['rooms'] += len(n['rooms'])
    d['stats']['rooms'] += len(n['rooms'])
    d['stats']['kept'] += len(kept)
    if clean:
        d['today']['perfect'] += 1
        d['stats']['perfect'] += 1
    d['today']['earned'] += pay
    head = f'🚪 {who} đi một vòng: ' + ' · '.join(f'{"✓" if x["ok"] else "✗"} {_lower(ROOMS[x["room"]]["name"])}' for x in lines) + '.'
    parts = [head]
    if kept:
        parts.append(f'💍 Đưa {who} khay đồ: {", ".join(_lower(x["name"]) for x in kept)}. “Ôi, cảm ơn em!”')
    if clean:
        parts.append(f'{who}: “Sạch quá, lần sau em lại tới nhé!”')
    if react['message']:
        parts.append(react['message'])
    if pay:
        parts.append(f'💸 Ting ting: nhận {pay} xu tiền công' + (' (khách quen).' if t['regular'] else '.'))
        kit.bank(pay)
    msg = _finish(s, c, d, t, pay, ' '.join(parts))
    grad = _graduate(d)
    return dict(message=f'{msg}{grad}', celebrate=clean or bool(grad))


def _graduate(d: dict) -> str:
    if d['learn']['done'] or d['stats']['jobs'] < APPRENTICE:
        return ''
    d['learn'].update(done=True, task=None, codes=[])
    return ' 🎓 Học nghề xong! Cô Mai: “Từ mai con tự đi một mình được rồi. Có gì gọi cô.”'


def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str) -> str:
    i = _npc_index(t)
    story = ''
    if i in REG_STORY and t['kind'] == 'job' and not cq.slips(t):
        visits = d['regulars'].get(str(i), {}).get('visits', 1)
        lines = REG_STORY[i]
        story = lines[min(visits, len(lines)) - 1]
        t['story'] = story
    t['stage'] = 'done'
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


ACTIONS = {
    'gv_wash': _wash, 'gv_fill': _fill, 'gv_open': _open,
    'gv_room': _room, 'gv_tool': _tool, 'gv_product': _product, 'gv_wipe': _wipe, 'gv_move': _move, 'gv_back': _back,
    'gv_check': _check,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['cart'].update(day=day, out=False)
    d['hand'] = dict(tool=None, product=None)
    d['today'] = _fresh_today(day)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    setup = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if setup is None and not any(t.get('career') == ID and t['day'] == day and t.get('kind') == 'setup' for t in c['tasks']):
        setup = make_task(day, 0, c['turn'])
        c['tasks'].append(setup)
        on_task(s, c, setup)
    if setup:
        c['active_task'] = setup['id']
        setup['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    lines = [f'🧹 Dọn {today["jobs"]} nhà, {today["rooms"]} phòng, {today["wipes"]} lượt lau.']
    if today['jobs']:
        lines.append(f'⭐ {today["perfect"]}/{today["jobs"]} nhà khách khen sạch, không chê chỗ nào.' +
                     (' Cô Mai: “Giỏi lắm!”' if today['perfect'] == today['jobs'] else ' Cô Mai: “Trên cao trước, khô trước ướt sau nhé.”'))
    if today['redo']:
        lines.append(f'🔁 {today["redo"]} chỗ phải lau lại vì bụi rơi từ trên xuống.')
    if desk_note:
        lines.append(desk_note)
    d['cart'].update(out=False, cloths='dirty')
    d['hand'] = dict(tool=None, product=None)
    tm = mod_of(c['day'] + 1)
    bottles = d['cart']['bottles']
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS}
    low = [x['id'] for x in ITEMS if stock[x['id']] <= 1]
    return dict(tomorrow=dict(emoji=tm['emoji'], label=tm['label'], hint=tm['hint']), lines=lines,
                note='Trên xe: ' + ', '.join(f'{PRODUCTS[p]["short"]} {bottles[p]}' for p in gc.BOTTLES) + ' lần lau.',
                jobs=today['jobs'], rooms=today['rooms'], perfect=today['perfect'], redo=today['redo'], earned=today['earned'], low=low)


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        cl = 3 if 'cloths' in codes else 5
        bt = 3 if 'bottle' in codes else 5
        return dict(criteria=[dict(key='cloth', label='Khăn sạch', score=cl, note='khăn giặt sạch' if cl == 5 else 'khăn chưa giặt'),
                              dict(key='bottles', label='Chai đủ dùng', score=bt, note='chai châm đầy' if bt == 5 else 'chai sắp cạn')])
    clean = 2 if 'focus' in codes or ('dirty' in codes and any(x['code'] == 'dirty' and x['sev'] >= 2 for x in cq.slips(t))) \
        else 4 if 'dirty' in codes else 5
    care = 1 if 'broke' in codes else 2 if codes & {'skip', 'pet'} or any(x.startswith('lost_') for x in codes) else \
        4 if codes & {'wobble', 'not_back'} else 5
    tools = 2 if 'red_cloth' in codes else 3 if 'gentle' in codes or any(x.startswith('harm_') for x in codes) else 5
    return dict(criteria=[dict(key='clean', label='Sạch sẽ', score=clean, note='chỗ nào cũng sạch' if clean == 5 else 'còn chỗ chưa sạch'),
                          dict(key='care', label='Giữ đồ, nhớ lời dặn', score=care, note='đồ đạc nguyên vẹn, đúng lời dặn' if care == 5 else 'chưa cẩn thận với đồ đạc'),
                          dict(key='tools', label='Đúng khăn, đúng chai', score=tools, note='đúng dụng cụ, không hỏng đồ' if tools == 5 else 'dùng sai khăn, sai chai'),
                          dict(key='speed', label='Gọn gàng', score=speed, note=f'còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return 'Cô Mai dặn: giặt khăn hôm qua, châm các chai sắp cạn rồi lên đường. ' + n['note']
    rooms = ', '.join(_lower(ROOMS[r['id']]['name']) for r in n['rooms'])
    return f'{n["place"]}: dọn {rooms}. {n["note"]}'.strip()


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS} if c['ext'].get('inv') else {}
    on = not d['learn']['done'] and d['stats']['jobs'] < APPRENTICE
    n = min(d['stats']['jobs'], APPRENTICE - 1)
    return dict(intro=d['intro'], cart=d['cart'], hand=d['hand'], stock=stock,
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID),
                learn=dict(on=on, n=d['stats']['jobs'], of=APPRENTICE, title=LESSONS[n][0] if on else None, text=LESSONS[n][1] if on else None))


def content() -> dict:
    return dict(tools=TOOLS, products=PRODUCTS, bottles=list(gc.BOTTLES), spots=SPOTS, rooms=ROOMS, care=ITEMS_CARE, notes=NOTES,
                levels=gc.LEVELS, floor_wet=list(gc.FLOOR_WET), bottle=BOTTLE, bottle_low=BOTTLE_LOW, prices=PRICES, intro=INTRO,
                apprentice=APPRENTICE, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'setup':
        return 'Giặt khăn → châm chai sắp cạn → Lên đường.'
    return ('Nghe khách dặn → chọn phòng → cầm đúng dụng cụ, đúng chai → lau từ trên cao xuống, khô trước ướt sau → '
            'nhấc đồ dễ vỡ ra rồi đặt lại, cất đồ quý vào khay → mời khách kiểm nhà.')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'wash':
        d['cart']['cloths'] = 'clean'
        return 'Đã giặt khăn, phơi khô, xếp ba màu.'
    if e.get('role') == 'carry':
        return 'Đã xách xô, cây lau lên tận cửa nhà khách.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tổ giúp việc sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc dọn nhà không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc dọn nhà sai.')
    n = t['needs']
    rows = spot_rows(n) if t['kind'] == 'job' else []
    keys = {k for _, _, k, _, _ in rows}
    kit.need(t.get('room') is None or t['room'] in {r['id'] for r in n.get('rooms', [])}, 'Phòng đang dọn sai.')
    dirt = t.get('dirt')
    kit.need(isinstance(dirt, dict) and set(dirt) <= keys, 'Độ bẩn sai.')
    for v in dirt.values():
        kit.integer(v, 0, MAX_DIRT)
    items = t.get('items')
    ids = {x['id'] for x in n.get('items', [])} if t['kind'] == 'job' else set()
    kit.need(isinstance(items, dict) and set(items) <= ids and all(v in ('on', 'off', 'back', 'safe', 'broken') for v in items.values()), 'Đồ đạc trong nhà sai.')
    for k, v in items.items():
        kind = ITEMS_CARE[k]['kind']
        kit.need(v in {'fragile': ('on', 'off', 'back', 'broken'), 'valuable': ('on', 'safe'), 'pet': ('on', 'off')}[kind], 'Đồ đạc trong nhà sai.')
    touched = t.get('touched')
    kit.need(isinstance(touched, list) and len(touched) <= len(keys) and set(touched) <= set(n.get('skip', [])) and len(set(touched)) == len(touched),
             'Chỗ khách dặn sai.')
    for k in ('scrubs', 'waste', 'redo'):
        kit.integer(t.get(k), 0, 9999)
    if t.get('price') is not None:
        kit.integer(t['price'], 0, 10 ** 6)
    _vbool(t.get('regular'))
    chk = t.get('check')
    if chk is not None:
        kit.need(isinstance(chk, list) and len(chk) <= 6, 'Kiểm nhà sai.')
        for x in chk:
            kit.need(isinstance(x, dict) and set(x) == {'room', 'ok', 'note'} and x['room'] in ROOMS and type(x['ok']) is bool
                     and isinstance(x['note'], str) and len(x['note']) <= 120, 'Kiểm nhà sai.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    cart = d['cart']
    kit.need(isinstance(cart, dict) and set(cart) == {'day', 'cloths', 'out', 'bottles'} and cart['cloths'] in ('clean', 'dirty'), 'Xe đồ nghề sai.')
    kit.integer(cart['day'], 0, 10 ** 7)
    _vbool(cart['out'])
    kit.need(isinstance(cart['bottles'], dict) and set(cart['bottles']) == set(gc.BOTTLES), 'Chai trên xe sai.')
    for v in cart['bottles'].values():
        kit.integer(v, 0, BOTTLE)
    h = d['hand']
    kit.need(isinstance(h, dict) and set(h) == {'tool', 'product'} and (h['tool'] is None or h['tool'] in TOOLS)
             and (h['product'] is None or h['product'] in PRODUCTS), 'Dụng cụ trên tay sai.')
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'task', 'codes', 'done'}, 'Học nghề sai.')
    kit.need(lr['task'] is None or (isinstance(lr['task'], str) and len(lr['task']) <= 80), 'Học nghề sai.')
    kit.need(isinstance(lr['codes'], list) and len(lr['codes']) <= len(CATCH) and set(lr['codes']) <= set(CATCH), 'Học nghề sai.')
    _vbool(lr['done'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in HOMES}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits', 'happy'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
        _vbool(v['happy'])
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu tổ giúp việc sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='gv_', category='service',
    meta=dict(short='Giúp việc theo giờ', place='Tổ giúp việc Nhà Thơm', tagline='Trên cao trước, khô trước ướt sau.', icon='sparkles',
              color='#3f9d8f', light='#e2f4f0', weather='Sáng nắng nhẹ', work='Nhà khách hẹn', station='Xe đồ nghề',
              greeting='Giặt khăn, châm chai rồi lên đường. Tới nhà khách thì nghe dặn, dọn từ trên cao xuống, khô trước ướt sau nhé.',
              caption='Nhà ai cũng sạch thơm', map_label='25 · TỔ GIÚP VIỆC NHÀ THƠM'),
    people=PEOPLE,
    staff=[('Lụa', 'wash', 'Cháu cô Mai, giặt khăn vắt kiệt, gấp ba màu thẳng tắp.', 80, 88),
           ('Tâm', 'carry', 'Khỏe như vâm, xách xô nước lên tầng bảy không thở dốc.', 82, 78),
           ('Hồng', 'wash', 'Pha nước lau đúng liều, chai nào cũng dán nhãn.', 72, 92),
           ('Phúc', 'carry', 'Thuộc đường từng ngõ, nhớ cả mã cổng chung cư.', 78, 82)],
    roles={'wash': 'Giặt khăn, pha nước', 'carry': 'Xách đồ, đưa xe'},
    inventory=dict(items=ITEMS, capacity=40),
    prices=PRICES,
    tip=3,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🧺', 'Xe đồ nghề gọn gàng', [('Khăn xanh', 'Kính, gương'), ('Khăn vàng', 'Bàn, bếp'), ('Khăn đỏ', 'Chỉ bồn cầu'), ('Cây lau', 'Sàn, sau cùng')],
              ['Giặt khăn, châm chai', 'Nghe khách dặn', 'Trên cao trước, khô trước ướt sau', 'Mời khách kiểm nhà']),
    stories=[('Ba cái khăn', ('Ngày đầu đi làm, cô Mai đưa bạn ba cái khăn: xanh, vàng, đỏ.',
                              'Cô bảo: “Khăn đỏ mà lẫn sang bàn bếp là mang bồn cầu vào nồi cơm nhà người ta.”',
                              'Từ đó bạn gấp ba màu ba chồng, không bao giờ lẫn.')),
             ('Ngón tay trên nóc tủ', ('Cô Mai kiểm nhà bằng một ngón tay vuốt lên nóc tủ.',
                                       'Ngón tay sạch thì cô gật đầu, ngón tay xám thì cô cười: “Lên ghế đi con.”',
                                       'Giờ tới nhà nào bạn cũng nhìn lên trên trước.')),
             ('Cái khay sứ', ('Nhà bà Xuân có cái khay sứ nhỏ trên kệ gương.',
                              'Nhẫn, bông tai, đồng hồ, gì nằm lung tung bạn đều cất vào đó rồi nhắn bà.',
                              'Bà bảo: “Có con, bà không còn sợ mất đồ.”'))],
    review_asides=['Nhà sạch thơm, chỗ nào cũng bóng.', 'Đồ đạc nguyên chỗ, không mất không vỡ gì.',
                   'Nhớ đúng từng lời tôi dặn.', 'Làm có thứ tự, nhanh mà kỹ.'],
    situations=SITUATIONS,
    more_line='Cô Mai nhắn thêm một lịch hẹn mới.',
    open_line='Đã nhận lịch hẹn hôm nay. Soạn xe đồ nghề rồi lên đường nhé.',
    guide='Sáng: giặt khăn, châm chai → Lên đường. Mỗi nhà: nghe dặn → chọn phòng → cầm đúng dụng cụ, đúng chai → lau từ trên cao xuống, '
          'khô trước ướt sau → nhấc đồ dễ vỡ ra rồi đặt lại, cất đồ quý vào khay → Mời khách kiểm nhà.',
)
