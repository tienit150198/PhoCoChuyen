"""Thư viện – Lưu trữ phường Mây: the ward library and its archive (plugin career).

Cô Nguyệt has kept the ward's books and records for thirty years; the player works beside her. What the job is:

* the morning (``open`` task): read the hygrometer of the archive store (paper keeps at 45–60 %: above that the
  dehumidifier goes on), look at the insect traps (book lice, cockroaches, rats each have their own right answer;
  spraying insecticide on the shelves never is), open the reading room and put out the rules board;
* the circulation desk (``desk`` task) in three ways:
  - ``borrow``: look the title up (call number, on the shelf / reference only / out on loan), check the reader's card
    (in date, three books at most, no unpaid fee), then lend with the due date, renew the card, settle the old fee,
    or offer what fits (read it in the room, copy a chapter, reserve it);
  - ``return``: look at the book (wet, torn, written in, lost), read the due stamp, ask why it is late, then name the
    fee yourself (one xu a day, fifteen at most, plus the damage): the reader pays, haggles, makes excuses or refuses
    by their hidden traits; waive it when the reason is good (and ask first), write it in the debt book, or call
    cô Nguyệt; then mend the book the right way (archival tape, blotting paper, a note) and shelve it;
  - ``recommend``: ask what they liked last and what they feel like now, then pick one of four books;
* cataloguing (``catalog``): a cart of new or donated books: the class of each (a ten-class scheme), the author
  mark (three letters of the given name), and weeding the junk donations (mould, outdated law, pirated copies,
  torn) while keeping the old-but-good ones;
* the reading room round (``room``): two or three people breaking the rules (noise, phone calls, food, a snorer,
  a couple, bags holding seats, a cable across the aisle, smoking by the archive, photographing a whole book...).
  Each is answered the player's own way and takes it by hidden traits (calm, sulk, blow up and need a second word);
* the archive window (``archive``): after cô Nguyệt's briefing (once), check the papers, have the request form
  filled, read the record's access level in the index, decide (copy / ask for papers / ask the ward leader /
  refuse), put on cotton gloves and a mask, fetch the right box (a misfiled or lent record means searching the
  neighbouring box or the hand-over book before ever writing it off), make a certified copy (originals never leave
  the store), log it and hand over;
* the awkward asks: on most jobs someone wants something (renew by phone for a month, see a neighbour's land file,
  photocopy a whole textbook, give the deputy chairman the file without signing, a bribe, a flirt, a lost child...),
  dozens of them (library_content.DEMANDS). The player answers yes / the proper alternative / no / call cô Nguyệt;
  people decide by their traits; giving in to something wrong is never rewarded;
* surprises between jobs (kit desk scripts), the debt book for unpaid fees, real-life situations, a certificate
  (Chứng chỉ nghiệp vụ lưu trữ: a small allowance on every archive request).

The ward pays an allowance per job (through consequences.react: mistakes cut it); fees and fines are the library's
takings (money() with categories 'fine', 'card_fee', 'copy_fee'). Everything random is rolled from the day, slot
or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from . import street_folk as folk
from . import library_content as LC
from .. import consequences as cq
from .library_content import PEOPLE

ID = 'library'
GEN = 1
KINDS = ('open', 'desk', 'catalog', 'room', 'archive')
MODES = ('borrow', 'return', 'recommend')
PAY = dict(desk=8, catalog=10, room=8, archive=12)
CERT_ID = 'archive_craft'      # certificate_content.GROUPS: holding it adds the archive allowance
CERT_BONUS = 3
CERT_FREE_DAY = 6              # outside the story (no certificates) the allowance starts on this day
DM_RATE = 70                   # % of jobs (from day 2) where someone asks for something
CARD_STATES = ('ok', 'expired', 'limit', 'debt')
LOAN_STATES = ('avail', 'ref', 'out')
FEE_STATES = ('open', 'paid', 'debt', 'waived', 'none')
DM_STATES = ('wait', 'on', 'done')
OFF_PERSONA = {'on_ao': 'genz', 'dien_thoai': 'bossy', 'an_uong': 'genz', 'ngu_ngay': 'genz', 'cap_doi': 'genz', 'giu_cho': 'picky',
               'day_sac': 'quiet', 'hut_thuoc': 'sour', 'chup_ca_cuon': 'quiet', 'xe_trang': 'quiet', 'tre_chay': 'picky',
               'xem_video': 'bossy', 'gac_chan': 'sour', 'livestream': 'genz', 'nguoi_say': 'sour'}
WORD_OF = {'soft': 'away', 'offer': 'away', 'rule': 'answer', 'out': 'refuse'}


# ================================================================ small helpers
def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, LC.MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError, AttributeError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Bạn đọc'


def _persona(i: int) -> str | None:
    return PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None


def _tr(t: dict, extra: str = '') -> dict:
    return folk.traits(f'{t["id"]}{extra}', _persona(_npc_index(t)))


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _plain(s: str) -> str:
    """Upper case without Vietnamese marks (author marks)."""
    src = 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'
    dst = 'aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd'
    low = s.lower()
    return ''.join(dst[src.index(ch)] if ch in src else ch for ch in low).upper()


def author_mark(author: str) -> str:
    """Three letters of the author's given name (the last word), upper case, no marks."""
    return _plain(author.split()[-1])[:3]


def has_cert(s: dict) -> bool:
    j = s.get('journey') or {}
    rec = (j.get('certificates') or {}).get(CERT_ID)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def cert_bonus(s: dict, c: dict) -> int:
    if (s.get('journey') or {}).get('story'):
        return CERT_BONUS if has_cert(s) else 0
    return CERT_BONUS if c['day'] >= CERT_FREE_DAY else 0


def late_fee(days: int) -> int:
    return min(LC.FINE_CAP, max(0, days) * LC.FINE_DAY)


def dmg_fee(x: dict) -> int:
    fee = LC.DAMAGE[x['damage']][1]
    return x['price'] if fee is None else fee


def excuse_ok(x: dict) -> bool:
    return bool(x['late']) and LC.EXCUSE[x['excuse']][1]


def fee_due(x: dict) -> tuple[int, int]:
    """(the full fee by the rules, the least the rules allow when a good reason waives the late part)."""
    full = late_fee(x['late']) + dmg_fee(x)
    return full, (dmg_fee(x) if excuse_ok(x) else full)


# ================================================================ tasks
DAY1 = ('desk', 'catalog', 'room', 'archive', 'desk', 'room', 'catalog', 'desk', 'archive', 'room', 'desk')
WEIGHTS = {'normal': dict(desk=4, room=2, catalog=2, archive=2), 'thi': dict(desk=3, room=5, catalog=1, archive=1),
           'nom': dict(desk=3, room=2, catalog=3, archive=2), 'he': dict(desk=5, room=3, catalog=1, archive=1),
           'kiem_tra': dict(desk=3, room=1, catalog=2, archive=5)}


def _kind(day: int, slot: int, mod: str) -> str:
    if slot == 0:
        return 'open'
    if day == 1:
        return DAY1[(slot - 1) % len(DAY1)]
    if slot == 1:
        return 'desk'
    w = WEIGHTS.get(mod, WEIGHTS['normal'])
    pick = kit.rng(ID, 'kind', day, slot).random() * sum(w.values())
    for k in ('desk', 'room', 'catalog', 'archive'):
        pick -= w[k]
        if pick < 0:
            return k
    return 'desk'


def _weighted(r, rows: list) -> object:
    total = sum(w for _, w in rows)
    x = r.random() * total
    for v, w in rows:
        x -= w
        if x < 0:
            return v
    return rows[-1][0]


def _common(kind: str) -> dict:
    st = {'open': dict(seen=[], dehum=False, pest=None, room=False, board=False),
          'catalog': dict(cls={}, mark={}, weed={}),
          'room': dict(done={}, quiet=100),
          'archive': dict(seen=[], decision=None, approved=None, box=None, found=False, search=[], gear=[], copy=None, logged=False)}.get(kind)
    return dict(gen=GEN, st=st, story=None)


def _make_open(day: int, slot: int, serial: int, mod: str) -> dict:
    r = kit.rng(ID, 'open', day)
    if mod == 'nom':
        hum = r.randint(62, 74)
    elif day > 1 and r.random() < .3:
        hum = r.randint(61, 66)
    else:
        hum = r.randint(48, 58)
    pest = 'none' if day == 1 else _weighted(r, [('none', 3), ('mot', 1), ('gian', 1), ('chuot', 1)])
    if mod == 'nom' and pest == 'none' and r.random() < .5:
        pest = 'mot'
    needs = dict(note=mod_of(day)['hint'], rules=[f'Kho giấy giữ độ ẩm {LC.HUM_OK[0]}–{LC.HUM_OK[1]}%: cao hơn thì bật máy hút ẩm.',
                                                   'Thấy dấu côn trùng, chuột thì xử lý ngay, không xịt thuốc lên sách.'])
    return kit.base_task(ID, day, slot, serial, 0, 'Mở cửa thư viện buổi sáng',
                         'Cô Nguyệt: “Sáng nào cũng vậy: xem ẩm kế kho, soi bẫy, mở phòng đọc, dựng bảng nội quy. Kho mà ẩm là giấy hỏng cả loạt.”',
                         kind='open', needs=needs, _x=dict(hum=hum, pest=pest), **_common('open'))


DESK_NPC = (1, 2, 3, 7, 4, 6)


def _make_desk(day: int, slot: int, serial: int, mod: str) -> dict:
    r = kit.rng(ID, 'desk', day, slot)
    if day == 1:
        mode = {1: 'borrow', 5: 'return', 8: 'recommend'}.get(slot, ('borrow', 'return', 'recommend')[slot % 3])
    else:
        mode = _weighted(r, [('borrow', 4), ('return', 4), ('recommend', 2 if mod != 'he' else 3)])
    npc = DESK_NPC[r.randrange(len(DESK_NPC))]
    if mod == 'he' and r.random() < .4:
        npc = r.choice((3, 7))
    common = dict(_common('desk'), fee=None)
    if mode == 'borrow':
        book = r.choice(sorted(LC.LOANS))
        status = 'ref' if book in LC.REFERENCE else _weighted(r, [('avail', 6), ('out', 2)])
        card = _weighted(r, [('ok', 6), ('expired', 2)] + ([('limit', 1), ('debt', 1)] if day > 1 else []))
        title = LC.LOANS[book][0]
        x = dict(status=status, card=card, owe=r.randint(4, 9) if card == 'debt' else 0, back=day + r.randint(2, 9) if status == 'out' else 0)
        st = dict(looked=False, carded=False, renewed=False, settled=False)
        return kit.base_task(ID, day, slot, serial, npc, f'Mượn “{title}”', f'“Cho mình mượn cuốn {title} với.”', kind='desk',
                             needs=dict(mode='borrow', book=book), _x=x, **dict(common, st=st))
    if mode == 'return':
        book = r.choice(sorted(k for k in LC.LOANS if k not in LC.REFERENCE))
        late = _weighted(r, [(0, 2), (r.randint(1, 5), 3), (r.randint(6, 20), 3)])
        damage = 'none' if day == 1 else _weighted(r, [('none', 5), ('pen', 1), ('torn', 1), ('wet', 1), ('lost', 1)])
        excuse = 'none' if not late else _weighted(r, [('vien', 1), ('lu', 1), ('quen', 2), ('di_choi', 1), ('none', 1)])
        title = LC.LOANS[book][0]
        opening = (f'“Cuốn {title} mình làm mất rồi… giờ tính sao?”' if damage == 'lost' else f'“Trả sách nè: cuốn {title}.”')
        x = dict(late=late, damage=damage, excuse=excuse, price=r.randint(20, 45))
        st = dict(inspected=False, dated=False, why=False, repair=None, shelved=False)
        return kit.base_task(ID, day, slot, serial, npc, f'Trả “{title}”', opening, kind='desk',
                             needs=dict(mode='return', book=book), _x=x, **dict(common, st=st))
    genre = r.choice(sorted(LC.GENRE))
    easy = r.random() < .5
    match = next(k for k, v in LC.TASTE.items() if v[0] == genre and v[1] == easy)
    other = next(k for k, v in LC.TASTE.items() if v[0] == genre and v[1] != easy)
    rest = [k for k, v in sorted(LC.TASTE.items()) if v[0] != genre]
    r.shuffle(rest)
    cands = [match, other] + rest[:2]
    r.shuffle(cands)
    st = dict(asked=[], pick=None)
    return kit.base_task(ID, day, slot, serial, npc, 'Nhờ gợi ý một cuốn sách', '“Thư viện có cuốn gì hay hay không? Gợi ý giùm một cuốn đi.”',
                         kind='desk', needs=dict(mode='recommend', cands=cands), _x=dict(genre=genre, easy=easy), **dict(common, st=st))


def _marks(r, book: str) -> list:
    title, author = LC.BOOKS[book][0], LC.BOOKS[book][1]
    opts = []
    for m in (author_mark(author), _plain(author.split()[0])[:3], _plain(title.split()[0])[:3], _plain(author.split()[-2] if len(author.split()) > 2 else title.split()[-1])[:3]):
        if m and m not in opts:
            opts.append(m)
    opts = opts[:3]
    r.shuffle(opts)
    return opts


def _make_catalog(day: int, slot: int, serial: int, mod: str) -> dict:
    r = kit.rng(ID, 'catalog', day, slot)
    n = 3 if day == 1 else 4
    junk = day > 1 and r.random() < (.75 if mod == 'nom' else .6)
    good = sorted(LC.GOOD_BOOKS)
    r.shuffle(good)
    books = good[:n - (1 if junk else 0)]
    if junk:
        books.append(r.choice(sorted(LC.JUNK_BOOKS)))
    r.shuffle(books)
    donor = junk or r.random() < .4
    npc = r.choice((1, 3, 6)) if donor else 0
    marks = {b: _marks(r, b) for b in books}
    title = 'Thùng sách tặng cần biên mục' if donor else 'Lô sách mới mua cần biên mục'
    opening = ('“Tặng thư viện thùng sách nhà tôi, xếp lên kệ cho bà con đọc nhé.”' if donor
               else 'Cô Nguyệt: “Sách mới về, xếp lớp, ghi ký hiệu tác giả, dán nhãn rồi lên kệ nhé.”')
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='catalog',
                         needs=dict(src='tang' if donor else 'mua', books=books, marks=marks), _x={}, **_common('catalog'))


def _make_room(day: int, slot: int, serial: int, mod: str) -> dict:
    r = kit.rng(ID, 'room', day, slot)
    pool = sorted(LC.OFFENCES)
    if day == 1:
        pool = [k for k in pool if k not in ('hut_thuoc', 'nguoi_say', 'cap_doi')]
    weights = [(k, 3 if mod == 'thi' and k in ('on_ao', 'an_uong', 'ngu_ngay', 'giu_cho', 'day_sac') else
                3 if mod == 'he' and k in ('tre_chay', 'on_ao') else 1) for k in pool]
    picked = []
    while len(picked) < (2 if day == 1 else 3):
        k = _weighted(r, [(k, w) for k, w in weights if k not in picked])
        picked.append(k)
    npc = r.choice((1, 2, 3))
    return kit.base_task(ID, day, slot, serial, npc, 'Một vòng phòng đọc', '“Phòng đọc ồn quá, cán bộ thư viện đâu rồi?”', kind='room',
                         needs=dict(offenders=picked), _x={}, **_common('room'))


def _box_code(m: int, b: int, h: int) -> str:
    return f'Mục lục {m} · Hộp {b} · Hồ sơ {h:02d}'


def _make_archive(day: int, slot: int, serial: int, mod: str) -> dict:
    r = kit.rng(ID, 'archive', day, slot)
    pool = [i for i, x in enumerate(LC.REQUESTS) if x[10] <= day]
    i = pool[r.randrange(len(pool))]
    npc, title, opening, record, purpose, docs, level, right, fragile, lost, _ = LC.REQUESTS[i]
    m, b, h = r.randint(1, 4), r.randint(3, 40), r.randint(1, 30)
    boxes = [_box_code(m, b, h), _box_code(m, b + 1, h), _box_code(m, b, (h % 30) + 1)]
    order = [0, 1, 2]
    r.shuffle(order)
    boxes = [boxes[k] for k in order]
    x = dict(level=level, right=right, box=order.index(0), fragile=fragile, lost=lost, orig=record.startswith('Bản gốc'))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='archive',
                         needs=dict(req=i, record=record, purpose=purpose, docs=list(docs), boxes=boxes), _x=x, **_common('archive'))


MAKERS = dict(open=_make_open, desk=_make_desk, catalog=_make_catalog, room=_make_room, archive=_make_archive)


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    return MAKERS[_kind(day, slot, mod)](day, slot, serial, mod)


FIXED = ('needs', '_x')


# ---------------------------------------------------------------- the ask a job carries
def demand_of(t: dict) -> str | None:
    """Who asks for something on this job (a pure function of the job's id, day and kind)."""
    kind, day = t.get('kind'), t.get('day', 1)
    if kind == 'open':
        return None
    if day == 1:
        if int(str(t.get('id', '0')).rsplit('-', 1)[-1]) not in (1, 3):
            return None
    elif folk.roll('tv-dm', t['id']) >= DM_RATE:
        return None
    pool = [x['id'] for x in LC.DEMANDS if kind in x['kinds'] and x['min_day'] <= day]
    return pool[folk.roll('tv-dm-n', t['id']) % len(pool)] if pool else None


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'open':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
    dm = demand_of(t)
    if dm:
        t['dm'] = dict(id=dm, state='wait', choice=None)


# ================================================================ the library's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, jobs=0, lent=0, returned=0, fines=0, waived=0, overcharged=0, shelved=0, weeded=0, records=0, room=0, asks=0, good_asks=0)


def initial() -> dict:
    return dict(v=1, intro=False, trained=False, regulars={}, today=_fresh_today(0),
                stats=dict(jobs=0, lent=0, fines=0, waived=0, overcharged=0, shelved=0, weeded=0, records=0, privacy=0, asks=0, good_asks=0, bad_asks=0),
                desk=kit.desk_initial(), debts=[])


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
    return d


# ================================================================ the actions
FREE = ('tv_intro', 'tv_chase', 'tv_train')
NO_TICK = ('tv_intro', 'tv_desk', 'tv_ask', 'tv_train', 'tv_chase', 'tv_look', 'tv_lookup', 'tv_card', 'tv_why', 'tv_q', 'tv_see',
           'tv_class', 'tv_mark', 'tv_weed', 'tv_fine', 'tv_fee', 'tv_decide', 'tv_gear', 'tv_log')
PHYSICAL = ('tv_box', 'tv_search', 'tv_repair', 'tv_shelve', 'tv_deal', 'tv_catdone', 'tv_copy')
OUTSIDE = ('tv_intro', 'tv_desk', 'tv_chase', 'tv_train')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'tv_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Cô Nguyệt đang chờ ở quầy.')
    desk = d['desk']
    if name == 'tv_desk':
        return kit.desk_choose(s, c, ID, desk, LC.DESK, p.get('option'))
    if name in ('tv_chase', 'tv_train'):
        return ACTIONS[name](s, c, d, p)
    kit.desk_block(desk, 'Có chuyện bất ngờ ở thư viện, quyết xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở thư viện.')
    if name != 'tv_ask':
        t = next((x for x in c['tasks'] if x['id'] == p.get('task') and x.get('career') == ID), None)
        if t and t['status'] not in ('completed', 'referred', 'cancelled'):
            stop = _demand_gate(t)
            if stop:
                return stop
    result = fn(s, c, d, p)
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, LC.DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(LC.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
    return result


def _task(c: dict, p: dict, kinds=None, mode=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc thư viện.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    if mode:
        kit.need((t.get('needs') or {}).get('mode') == mode, 'Thao tác này không dành cho việc đang làm.')
    return t


def _known(t: dict) -> None:
    kit.need(t['known'], 'Nghe bạn đọc nói đã nhé.')


def _slip(t: dict, code: str, sev: int, text: str, note: str = '', safety: bool = False) -> None:
    t['mistakes'] += 1
    cq.slip(t, code, sev, text, note, safety=safety)


def _finish(s: dict, c: dict, d: dict, t: dict, pay: int, narrative: str) -> str:
    """Close a job once: the ward's allowance (cut by the reader's reaction to mistakes), the regulars' line."""
    who = _who(t)
    react = cq.react(s, c, t, max(0, int(pay)), who=who) if t['kind'] != 'open' else dict(pay=0, message='')
    i = _npc_index(t)
    story = ''
    if i in LC.REG_STORY and t['kind'] != 'open':
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        lines = LC.REG_STORY[i]
        story = lines[min(r['visits'], len(lines)) - 1]
        t['story'] = story
    if t['kind'] != 'open':
        d['today']['jobs'] += 1
        d['stats']['jobs'] += 1
    kit.start_work(t)
    text = ' '.join(x for x in (narrative, react['message']) if x).strip()
    kit.complete(s, c, t, react['pay'], (text or t['title'])[:300])
    out = f'{text} 💬 {story}'.strip() if story else text
    if react['pay']:
        out += f' (+{react["pay"]} xu phụ cấp)'
    return out


# ---------------------------------------------------------------- the awkward asks
def _demand(t: dict) -> dict | None:
    dm = t.get('dm')
    return LC.DEMAND.get(dm['id']) if isinstance(dm, dict) else None


def _demand_gate(t: dict) -> dict | None:
    """Someone steps in with their ask the first time the job is touched after it is known; until answered, it waits."""
    dm, x = t.get('dm'), _demand(t)
    if not x or not t.get('known') or dm['state'] == 'done':
        return None
    kit.need(dm['state'] != 'on', 'Đang có người nhờ việc: trả lời họ trước đã.')
    dm['state'] = 'on'
    return dict(message=f'🙋 {x["who"]}: {x["text"]}', surprise=True)


def _ask(s, c, d, p):
    t = _task(c, p)
    dm, x = t.get('dm'), _demand(t)
    kit.need(x and dm['state'] == 'on', 'Không có ai đang nhờ việc.')
    choice = kit.one_of(p.get('choice'), LC.CHOICES, 'Chọn cách trả lời.')
    who = x['who']
    tr = folk.traits(f'{t["id"]}:{x["id"]}', _persona(x['npc']) if x['npc'] is not None else x['persona'])
    dm.update(state='done', choice=choice)
    d['today']['asks'] += 1
    d['stats']['asks'] += 1
    good = choice in x['best']
    sev = x['bad'].get(choice, 0)
    if good:
        d['today']['good_asks'] += 1
        d['stats']['good_asks'] += 1
        c['xp'] += 3
    if sev:
        d['stats']['bad_asks'] += 1
        if x['typ'] == 'privacy':
            d['stats']['privacy'] += 1
        _slip(t, f'd_{x["id"]}'[:32], sev, x['lose'] or f'{who} nhờ việc sai mà cũng chiều theo.', f'chiều theo: {_lower(x["yes"] if choice == "yes" else x["no"])}'[:120])
    if choice == 'yes':
        line = x['yes_out'] or ('Bạn chiều theo. ' + ('Lần này êm, nhưng cô Nguyệt nhìn bạn lắc đầu.' if sev else f'{who} vui ra mặt.'))
        if not sev:
            for o in c['tasks']:
                if o.get('career') == ID and o['id'] != t['id'] and o['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in o:
                    o['patience'] = max(25, o['patience'] - 3)
        return dict(message=f'🙋 {line}', correct=not sev)
    if choice == 'boss':
        t['patience'] = max(25, t.get('patience', 100) - 8)
        reply = x['alt'] if good else 'Việc này em tự trả lời được mà, lần sau cứ theo nội quy nhé.'
        line = f'Cô Nguyệt ra quầy, nói nhỏ mà rõ: “{reply}” {who} nghe ra.'
        return dict(message=f'🙋 {line}', correct=not sev, celebrate=good)
    how = folk.word(tr, 'away' if choice == 'alt' else 'refuse')
    line = (x['alt_out'] if choice == 'alt' and x['alt_out'] and how == 'calm' else LC.TAKE[how][folk.roll('tv-take', t['id']) % 2].format(who=who))
    head = f'Bạn: “{x["alt"]}.” ' if choice == 'alt' else 'Bạn từ chối nhẹ nhàng. '
    if how == 'blowup':
        t['patience'] = max(25, t.get('patience', 100) - 8)
        t['heat'] = min(9, int(t.get('heat') or 0) + 1)
        if good:
            line += ' Cô Nguyệt nhắn: “Em làm đúng rồi, đừng lo.”'
            c['xp'] += 2
        elif x['npc'] is not None and not sev:
            kit.review(s, c, kit.npc_id(ID, x['npc']), 2, f'Nhờ có chút việc mà cán bộ thư viện từ chối cứng nhắc.', t['id'])
    return dict(message=f'🙋 {head}{line}', correct=not sev, celebrate=good and how == 'calm')


# ---------------------------------------------------------------- the morning
def _look(s, c, d, p):
    t = _task(c, p, ('open',))
    what = kit.one_of(p.get('what'), ('am', 'bay', 'phong', 'bang'), 'Việc buổi sáng không có.')
    st, x = t['st'], t['_x']
    kit.start_work(t)
    if what == 'phong':
        kit.need(not st['room'], 'Phòng đọc mở rồi.')
        st['room'] = True
        return dict(message='🔑 Mở cửa phòng đọc, bật đèn, bật quạt, kéo rèm cho sáng.')
    if what == 'bang':
        kit.need(not st['board'], 'Bảng nội quy dựng rồi.')
        st['board'] = True
        return dict(message='📋 Dựng bảng nội quy ở cửa: giữ yên lặng, không ăn uống, nghe điện thoại ngoài hành lang.')
    kit.need(what not in st['seen'], 'Xem rồi.')
    st['seen'].append(what)
    if what == 'am':
        hi = x['hum'] > LC.HUM_OK[1]
        return dict(message=f'🌡️ Ẩm kế kho chỉ {x["hum"]}%.' + (' Cao hơn mức cho phép của kho giấy.' if hi else ' Trong mức cho phép.'))
    return dict(message=f'🪤 {LC.PESTS[x["pest"]]}')


def _dehum(s, c, d, p):
    t = _task(c, p, ('open',))
    st = t['st']
    st['dehum'] = not st['dehum']
    return dict(message='💧 Bật máy hút ẩm kho, hẹn giờ chạy tới trưa.' if st['dehum'] else 'Tắt máy hút ẩm.')


def _pest(s, c, d, p):
    t = _task(c, p, ('open',))
    st = t['st']
    kit.need('bay' in st['seen'], 'Soi bẫy trước đã nhé.')
    how = kit.one_of(p.get('how'), LC.PEST_FIX, 'Cách xử lý không có.')
    st['pest'] = how
    return dict(message=f'🪤 {LC.PEST_FIX[how]}.')


def _openup(s, c, d, p):
    t = _task(c, p, ('open',))
    st, x = t['st'], t['_x']
    kit.need(st['room'], 'Mở phòng đọc đã nhé.')
    hi = x['hum'] > LC.HUM_OK[1]
    if 'am' not in st['seen']:
        _slip(t, 'no_hum', 1, 'Sáng không ai xem ẩm kế kho.', 'chưa xem ẩm kế')
    if hi and not st['dehum']:
        _slip(t, 'damp', 2, f'Kho ẩm {x["hum"]}% mà không bật máy hút ẩm, giấy mềm oặt.', 'kho ẩm không hút ẩm')
    if 'bay' not in st['seen']:
        _slip(t, 'no_trap', 1, 'Không ai soi bẫy côn trùng sáng nay.', 'chưa soi bẫy')
    elif st['pest'] != LC.PEST_BEST[x['pest']] and not (x['pest'] == 'none' and st['pest'] is None):
        bad = st['pest'] in (None, 'ke') and x['pest'] != 'none'
        if st['pest'] == 'xit':
            _slip(t, 'spray', 2, 'Xịt thuốc diệt côn trùng thẳng lên kệ sách, mùi hắc cả phòng, thuốc dính lên trang.', 'xịt thuốc lên sách')
        elif bad:
            _slip(t, 'pest', 2, 'Thấy dấu côn trùng mà để đó, mấy hôm sau cả kệ bị hại.', 'bỏ qua côn trùng')
        else:
            _slip(t, 'pest_wrong', 1, 'Xử lý côn trùng chưa đúng cách.', 'xử lý chưa đúng')
    if not st['board']:
        _slip(t, 'no_board', 1, 'Không dựng bảng nội quy, bạn đọc không biết quy định.', 'thiếu bảng nội quy')
    ok = not cq.slips(t)
    msg = _finish(s, c, d, t, 0, 'Mở cửa thư viện.')
    return dict(message='📚 ' + ('Cô Nguyệt gật đầu: “Kho ổn, phòng đọc sẵn sàng.” ' if ok else 'Cô Nguyệt nhắc: “Sáng ra là phải kỹ, kho hỏng thì không cứu được.” ') + msg,
                celebrate=ok)


# ---------------------------------------------------------------- the desk: borrowing
def _lookup(s, c, d, p):
    t = _task(c, p, ('desk',), 'borrow')
    _known(t)
    t['st']['looked'] = True
    kit.start_work(t)
    x, (title, call, shelf) = t['_x'], LC.LOANS[t['needs']['book']]
    tail = {'avail': 'còn trên kệ.', 'ref': 'sách tra cứu: chỉ đọc tại chỗ, không cho mượn về.', 'out': f'đang có người mượn, hẹn trả ngày {x["back"]}.'}[x['status']]
    return dict(message=f'🔎 {title} · {call} · {shelf} · {tail}')


def _card(s, c, d, p):
    t = _task(c, p, ('desk',), 'borrow')
    _known(t)
    t['st']['carded'] = True
    x = t['_x']
    return dict(message='🪪 ' + {'ok': 'Thẻ còn hạn, đang mượn một cuốn.', 'expired': 'Thẻ hết hạn từ tháng trước.',
                                'limit': f'Đang mượn đủ {LC.LOAN_MAX} cuốn, chưa trả cuốn nào.',
                                'debt': f'Còn nợ {x["owe"]} xu phí trả trễ lần trước.'}[x['card']])


def _renew(s, c, d, p):
    t = _task(c, p, ('desk',), 'borrow')
    st, x = t['st'], t['_x']
    kit.need(st['carded'], 'Kiểm thẻ trước đã.')
    kit.need(x['card'] == 'expired' and not st['renewed'], 'Thẻ không cần gia hạn.')
    st['renewed'] = True
    kit.money(s, c, LC.CARD_FEE, f'Phí gia hạn thẻ: {_who(t)}'[:120], t['id'], 'card_fee')
    return dict(message=f'🪪 Gia hạn thẻ một năm, thu {LC.CARD_FEE} xu, đưa biên lai.')


def _settle(s, c, d, p):
    t = _task(c, p, ('desk',), 'borrow')
    st, x = t['st'], t['_x']
    kit.need(st['carded'] and x['card'] == 'debt' and not st['settled'], 'Thẻ không có nợ phí.')
    amount = kit.integer(p.get('amount'), 0, x['owe'])
    st['settled'] = True
    if amount:
        kit.money(s, c, amount, f'Thu nợ phí trễ hạn: {_who(t)}'[:120], t['id'], 'fine')
        d['today']['fines'] += amount
        d['stats']['fines'] += amount
    if amount < x['owe']:
        d['today']['waived'] += x['owe'] - amount
        _slip(t, 'lenient', 1, 'Nợ phí cũ được bớt mà không có lý do, kế toán phường hỏi.', 'bớt nợ không lý do')
    return dict(message=f'💵 {_who(t)} trả {amount} xu nợ cũ. Thẻ mở lại.')


def _lend(s, c, d, p):
    t = _task(c, p, ('desk',), 'borrow')
    st, x = t['st'], t['_x']
    kit.need(st['looked'], 'Tra máy xem sách còn không đã.')
    kit.need(st['carded'], 'Kiểm thẻ bạn đọc trước đã.')
    kit.need(x['status'] != 'out', 'Sách đang có người mượn: giúp bạn đọc đặt trước nhé.')
    if x['status'] == 'ref':
        _slip(t, 'ref_out', 2, 'Sách tra cứu mà cho mượn về, người khác cần tra không có.', 'cho mượn sách tra cứu')
    if x['card'] == 'expired' and not st['renewed']:
        _slip(t, 'card', 1, 'Thẻ hết hạn mà vẫn cho mượn.', 'thẻ hết hạn')
    if x['card'] == 'limit':
        _slip(t, 'limit', 1, f'Mượn quá {LC.LOAN_MAX} cuốn một thẻ.', 'quá số sách cho mượn')
    if x['card'] == 'debt' and not st['settled']:
        _slip(t, 'debt_card', 1, 'Thẻ còn nợ phí mà vẫn cho mượn tiếp.', 'thẻ còn nợ phí')
    d['today']['lent'] += 1
    d['stats']['lent'] += 1
    due = c['day'] + LC.LOAN_DAYS
    msg = _finish(s, c, d, t, PAY['desk'], f'Đóng dấu hạn trả ngày {due}, đưa sách cho {_who(t)}.')
    return dict(message='📗 ' + msg, celebrate=not cq.slips(t))


OFFERS = {'room': 'Mời đọc tại phòng đọc', 'copy': 'Photo phần cần (dưới một phần mười cuốn)', 'reserve': 'Ghi phiếu đặt trước, báo khi sách về',
          'return_first': 'Trả bớt một cuốn rồi mượn tiếp', 'decline': 'Từ chối, giải thích nội quy'}


def _offer(s, c, d, p):
    t = _task(c, p, ('desk',), 'borrow')
    st, x = t['st'], t['_x']
    kit.need(st['looked'], 'Tra máy xem sách còn không đã.')
    how = kit.one_of(p.get('how'), OFFERS, 'Cách giúp không có.')
    status, card = x['status'], x['card']
    if status == 'ref':
        if how == 'reserve':
            _slip(t, 'wrong_offer', 1, 'Sách tra cứu thì đọc tại chỗ được luôn, đặt trước làm gì.', 'gợi ý chưa hợp')
    elif status == 'out':
        if how in ('room', 'copy'):
            _slip(t, 'wrong_offer', 1, 'Sách đang có người mượn, đọc tại chỗ sao được.', 'gợi ý chưa hợp')
    else:
        kit.need(st['carded'], 'Kiểm thẻ bạn đọc trước đã.')
        if card == 'ok':
            _slip(t, 'needless_no', 2, 'Sách có trên kệ, thẻ còn hạn mà không cho mượn.', 'từ chối vô cớ')
        elif card == 'expired' and how in ('decline', 'return_first'):
            _slip(t, 'needless_no', 1, 'Thẻ hết hạn thì gia hạn hai phút là xong, sao lại từ chối.', 'không gia hạn thẻ')
        elif card == 'limit' and how not in ('return_first', 'room', 'decline'):
            _slip(t, 'wrong_offer', 1, 'Mượn đủ ba cuốn rồi: trả bớt một cuốn hoặc đọc tại chỗ.', 'gợi ý chưa hợp')
    msg = _finish(s, c, d, t, PAY['desk'], f'{OFFERS[how]}: {_who(t)} gật đầu.')
    return dict(message='🙏 ' + msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the desk: returns, fees, repairs
def _fee(t: dict) -> dict:
    if t.get('fee') is None:
        t['fee'] = dict(state='open', asked=None, counter=None, tries=0, paid=0, tone=None)
    return t['fee']


def _inspect(s, c, d, p):
    t = _task(c, p, ('desk',), 'return')
    _known(t)
    t['st']['inspected'] = True
    kit.start_work(t)
    x = t['_x']
    if x['damage'] == 'lost':
        return dict(message=f'📕 Bạn đọc làm mất sách. Giá bìa {x["price"]} xu.')
    return dict(message=f'📖 Lật từng trang: {_lower(LC.DAMAGE[x["damage"]][0])}.')


def _date(s, c, d, p):
    t = _task(c, p, ('desk',), 'return')
    _known(t)
    t['st']['dated'] = True
    late = t['_x']['late']
    return dict(message=f'📅 Dấu hạn trả: {"đúng hạn" if not late else f"trễ {late} ngày"}.')


def _why(s, c, d, p):
    t = _task(c, p, ('desk',), 'return')
    _known(t)
    t['st']['why'] = True
    x = t['_x']
    return dict(message=f'💬 {_who(t)}: {LC.EXCUSE[x["excuse"]][0] if x["late"] else "“Đúng hạn mà, trả liền đó.”"}')


def _fine_slips(s: dict, c: dict, d: dict, t: dict, amount: int) -> None:
    """What the rules say about the amount taken (and waived)."""
    x, st = t['_x'], t['st']
    full, least = fee_due(x)
    if amount > full:
        d['today']['overcharged'] += amount - full
        d['stats']['overcharged'] += amount - full
        _slip(t, 'overcharge', 2, f'Nội quy ghi rõ {full} xu mà thu {amount} xu.', 'thu phí quá nội quy')
    elif amount < full:
        d['today']['waived'] += full - amount
        d['stats']['waived'] += full - amount
        if amount < least:
            _slip(t, 'lenient', 1, 'Miễn giảm phí không có lý do chính đáng, kế toán phường nhắc.', 'miễn giảm không lý do')
        elif not st['why']:
            _slip(t, 'no_reason', 1, 'Miễn phí mà không hỏi lý do, sổ không ghi gì.', 'miễn không ghi lý do')


def _fine(s, c, d, p):
    """The player names the fee (and the tone); the reader decides by their traits."""
    t = _task(c, p, ('desk',), 'return')
    st, x = t['st'], t['_x']
    kit.need(st['inspected'] and st['dated'], 'Kiểm sách và xem dấu hạn trả trước khi tính phí.')
    fee = _fee(t)
    kit.need(fee['state'] == 'open', 'Khoản phí này xong rồi.')
    amount = kit.integer(p.get('amount'), 0, 300)
    tone = kit.one_of(p.get('tone') or 'soft', ('soft', 'strict'), 'Chọn cách nói.')
    full, _ = fee_due(x)
    who = _who(t)
    fee.update(asked=amount, tone=tone)
    if amount == 0:
        fee.update(state='waived' if full else 'none', counter=None)
        _fine_slips(s, c, d, t, 0)
        return dict(message=f'🤝 Không thu phí. {who}: “Cảm ơn nha!”' if full else f'✅ Không có phí gì. {who} gật đầu.')
    tr = _tr(t)
    if amount > full and tr['savvy'] >= 50:
        fee['tries'] = min(9, fee['tries'] + 1)
        _slip(t, 'overcharge_caught', 1, f'Tính phí sai nội quy, bị bạn đọc chỉ ra ngay ở quầy.', 'tính phí sai')
        return dict(message=f'🧾 {who} chỉ tay lên bảng nội quy: “Một xu một ngày, tối đa {LC.FINE_CAP} xu mỗi cuốn. Tính lại đi!”', correct=False)
    if amount > full:
        # Someone who does not know the rules may just pay what they are told (and the fee is still wrong).
        jp = folk.judge_price(tr, max(1, full), amount, fee['tries'])
        r = dict(kind='paid') if jp['kind'] in ('cheap', 'accept') else dict(kind='haggle', counter=jp['counter']) if jp['kind'] == 'counter' else dict(kind='refuse')
    else:
        r = folk.fee(tr, max(1, full), amount, tone, fee['tries'])
    if r['kind'] == 'paid':
        fee.update(state='paid', paid=amount, counter=None)
        kit.money(s, c, amount, f'Phí trả sách: {t["title"]}'[:120], t['id'], 'fine')
        d['today']['fines'] += amount
        d['stats']['fines'] += amount
        _fine_slips(s, c, d, t, amount)
        return dict(message=f'💵 {who} nộp {amount} xu, nhận biên lai.')
    fee['tries'] = min(9, fee['tries'] + 1)
    if r['kind'] == 'haggle':
        fee['counter'] = max(0, min(amount - 1, r['counter']))
        return dict(message=f'🧾 {who}: “{amount} xu lận hả? {fee["counter"]} xu thôi, được thì nộp liền.”')
    if r['kind'] == 'excuse':
        return dict(message=f'🧾 {who}: “Hôm nay không mang đủ tiền, để bữa sau được không?”')
    return dict(message=f'🧾 {who}: “Không nộp! Trễ có mấy ngày mà phạt, thư viện gì kỳ vậy!”', correct=False)


def _fee_act(s, c, d, p):
    """After a no: write it in the debt book, waive it, or call cô Nguyệt."""
    t = _task(c, p, ('desk',), 'return')
    st, x = t['st'], t['_x']
    kit.need(st['inspected'] and st['dated'], 'Kiểm sách và xem dấu hạn trả trước khi tính phí.')
    fee = _fee(t)
    kit.need(fee['state'] == 'open', 'Khoản phí này xong rồi.')
    how = kit.one_of(p.get('how'), ('later', 'waive', 'boss'), 'Chọn cách xử lý.')
    full, least = fee_due(x)
    who = _who(t)
    if how == 'waive':
        fee.update(state='waived', paid=0)
        _fine_slips(s, c, d, t, 0)
        return dict(message=f'🤝 Miễn phí cho {who}, ghi vào sổ.' + (' Cô Nguyệt gật đầu: lý do chính đáng.' if excuse_ok(x) and st['why'] and not dmg_fee(x) else ''))
    if how == 'boss':
        tr = _tr(t)
        t['patience'] = max(25, t.get('patience', 100) - 10)
        amount = fee['asked'] if fee['asked'] is not None and least <= fee['asked'] <= full else least
        if tr['honest'] >= 35 and amount:
            fee.update(state='paid', paid=amount, counter=None)
            kit.money(s, c, amount, f'Phí trả sách: {t["title"]}'[:120], t['id'], 'fine')
            d['today']['fines'] += amount
            d['stats']['fines'] += amount
            _fine_slips(s, c, d, t, amount)
            return dict(message=f'👩‍🏫 Cô Nguyệt giải thích nội quy từ tốn. {who} nộp {amount} xu.')
        how = 'later'
    kit.need(len(folk.open_debts(d['debts'])) < folk.DEBT_MAX, 'Sổ nợ phí đầy rồi: đòi bớt nợ cũ đã.')
    owe = fee['asked'] if fee['asked'] else full
    owe = max(1, min(owe, full)) if full else 0
    fee.update(state='debt', paid=0)
    if owe:
        d['debts'] = folk.trim_debts(d['debts'] + [folk.debt_line(f'no-{t["id"]}', _npc_index(t), who, t['id'], c['day'], owe, t['title'])])
    _fine_slips(s, c, d, t, owe)
    return dict(message=f'📒 Ghi sổ nợ phí: {who} còn nợ {owe} xu, khóa thẻ tới khi trả.')


def _repair(s, c, d, p):
    t = _task(c, p, ('desk',), 'return')
    st, x = t['st'], t['_x']
    kit.need(st['inspected'], 'Kiểm sách trước đã.')
    kit.need(x['damage'] not in ('none', 'lost'), 'Sách không cần sửa.')
    kit.need(st['repair'] is None, 'Đã xử lý rồi.')
    how = kit.one_of(p.get('how'), LC.REPAIR, 'Cách sửa không có.')
    if how == 'bang_giay':
        kit.need(kit.stock(c, 'bang_giay') > 0, 'Hết băng giấy sửa sách. Mở kho mua thêm nhé.')
        kit.take(c, 'bang_giay', 1)
    st['repair'] = how
    right = LC.REPAIR[how][1] == x['damage']
    if not right:
        if how == 'bang_keo':
            _slip(t, 'tape', 1, 'Băng keo trong vài tháng là ố vàng, dính chặt trang, càng hỏng thêm.', 'dùng băng keo thường')
        elif how == 'say':
            _slip(t, 'heat', 1, 'Sấy nóng, phơi nắng làm giấy cong vênh, giòn gãy.', 'sấy nóng sách ướt')
        else:
            _slip(t, 'wrong_fix', 1, 'Sửa không đúng kiểu hỏng của sách.', 'sửa chưa đúng cách')
    return dict(message=f'🛠️ {LC.REPAIR[how][0]}.' + ('' if right else ' Hừm, không ổn lắm.'), correct=right)


def _shelve(s, c, d, p):
    t = _task(c, p, ('desk',), 'return')
    st, x = t['st'], t['_x']
    kit.need(st['inspected'] and st['dated'], 'Kiểm sách và xem dấu hạn trả trước đã.')
    full, _ = fee_due(x)
    fee = t.get('fee')
    if full:
        kit.need(fee is not None and fee['state'] != 'open', 'Tính phí xong rồi mới cất sách.')
    if x['damage'] not in ('none', 'lost') and st['repair'] is None:
        _slip(t, 'unrepaired', 1, 'Sách hỏng mà đưa thẳng lên kệ, người sau mượn lại càng hỏng.', 'chưa sửa sách')
    st['shelved'] = True
    d['today']['returned'] += 1
    title = LC.LOANS[t['needs']['book']][0]
    what = (f'Ghi sổ mất sách, đặt mua bổ sung cuốn {title}.' if x['damage'] == 'lost' else f'Cất {title} lên kệ đúng ký hiệu.')
    msg = _finish(s, c, d, t, PAY['desk'], what)
    return dict(message='📚 ' + msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the desk: a recommendation
def _q(s, c, d, p):
    t = _task(c, p, ('desk',), 'recommend')
    _known(t)
    q = kit.one_of(p.get('q'), ('last', 'mood'), 'Câu hỏi không có.')
    st, x = t['st'], t['_x']
    kit.need(q not in st['asked'], 'Hỏi rồi.')
    st['asked'].append(q)
    kit.start_work(t)
    line = LC.TASTE_LAST[x['genre']] if q == 'last' else LC.TASTE_MOOD[x['easy']]
    return dict(message=f'💬 {_who(t)}: {line}')


def _rec(s, c, d, p):
    t = _task(c, p, ('desk',), 'recommend')
    _known(t)
    st, x = t['st'], t['_x']
    book = kit.one_of(p.get('book'), t['needs']['cands'], 'Cuốn này không có trên xe gợi ý.')
    st['pick'] = book
    g, easy = LC.TASTE[book][0], LC.TASTE[book][1]
    who, title = _who(t), LC.LOANS[book][0]
    if g != x['genre']:
        _slip(t, 'rec_miss', 2, f'Gợi ý cuốn {title}, chẳng hợp gu chút nào.', 'gợi ý sai gu')
        line = f'{who} lật vài trang, nhăn mặt: “Không phải gu mình lắm…” nhưng vẫn mượn cho phải phép.'
    elif easy != x['easy']:
        _slip(t, 'rec_meh', 1, f'Cuốn {title} đúng gu mà {"nặng quá" if not easy else "nhẹ quá"} so với mình lúc này.', 'gợi ý chưa vừa')
        line = f'{who}: “Đúng thể loại mình thích, mà {"hơi nặng đầu" if not easy else "hơi nhẹ quá"}.”'
    else:
        c['xp'] += 3
        line = f'{who} mắt sáng rỡ: “Đúng cuốn mình cần luôn! Sao biết hay vậy?”'
    d['today']['lent'] += 1
    d['stats']['lent'] += 1
    msg = _finish(s, c, d, t, PAY['desk'], f'Gợi ý “{title}”. {line}')
    return dict(message='💡 ' + msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- cataloguing
def _book(t: dict, p: dict) -> str:
    return kit.one_of(p.get('book'), t['needs']['books'], 'Cuốn này không có trên xe sách.')


def _class(s, c, d, p):
    t = _task(c, p, ('catalog',))
    _known(t)
    b = _book(t, p)
    cls = kit.one_of(p.get('cls'), LC.CLASS_IDS, 'Lớp không có.')
    kit.need(b not in t['st']['weed'], 'Cuốn này đang để riêng loại bỏ.')
    t['st']['cls'][b] = cls
    kit.start_work(t)
    return dict(message=f'🏷️ {LC.BOOKS[b][0]}: lớp {cls} · {LC.CLASS_NAME[cls]}.')


def _mark(s, c, d, p):
    t = _task(c, p, ('catalog',))
    _known(t)
    b = _book(t, p)
    mark = kit.one_of(p.get('mark'), t['needs']['marks'][b], 'Ký hiệu không có.')
    kit.need(b not in t['st']['weed'], 'Cuốn này đang để riêng loại bỏ.')
    t['st']['mark'][b] = mark
    kit.start_work(t)
    return dict(message=f'✍️ {LC.BOOKS[b][0]}: ký hiệu tác giả {mark}.')


def _weed(s, c, d, p):
    t = _task(c, p, ('catalog',))
    _known(t)
    b = _book(t, p)
    st = t['st']
    reason = p.get('reason')
    if not reason:
        st['weed'].pop(b, None)
        return dict(message=f'↩️ Để {LC.BOOKS[b][0]} lại xe biên mục.')
    reason = kit.one_of(reason, LC.WEED, 'Lý do không có.')
    st['weed'][b] = reason
    st['cls'].pop(b, None)
    st['mark'].pop(b, None)
    kit.start_work(t)
    return dict(message=f'🗑️ Để riêng {LC.BOOKS[b][0]}: {_lower(LC.WEED[reason])}.')


def _catdone(s, c, d, p):
    t = _task(c, p, ('catalog',))
    _known(t)
    st, books = t['st'], t['needs']['books']
    keep = [b for b in books if b not in st['weed']]
    kit.need(all(b in st['cls'] and b in st['mark'] for b in keep), 'Còn cuốn chưa xếp lớp hoặc chưa ghi ký hiệu tác giả.')
    wrong_cls = [b for b in keep if LC.BOOKS[b][4] is None and st['cls'][b] != LC.BOOKS[b][2]]
    wrong_mark = [b for b in keep if LC.BOOKS[b][4] is None and st['mark'][b] != author_mark(LC.BOOKS[b][1])]
    junk_kept = [b for b in keep if LC.BOOKS[b][4]]
    good_weeded = [b for b in books if b in st['weed'] and not LC.BOOKS[b][4]]
    if wrong_cls:
        _slip(t, 'wrong_class', 2 if len(wrong_cls) > 1 else 1, f'{len(wrong_cls)} cuốn xếp nhầm lớp, bạn đọc tìm mãi không ra.', 'xếp nhầm lớp')
    if wrong_mark:
        _slip(t, 'wrong_mark', 1, f'{len(wrong_mark)} cuốn ghi sai ký hiệu tác giả.', 'sai ký hiệu tác giả')
    if junk_kept:
        mould = any(LC.BOOKS[b][4] == 'moc' for b in junk_kept)
        _slip(t, 'junk_shelved', 2 if mould else 1, 'Sách mốc, sách lậu lên kệ chung.' if mould else 'Sách hỏng, lỗi thời, in lậu lẫn lên kệ.', 'không lọc sách hỏng')
    if good_weeded:
        rare = 'kieu_1960' in good_weeded
        _slip(t, 'weeded_good', 2 if rare else 1, 'Bỏ cả sách quý in năm 1960.' if rare else 'Loại nhầm sách còn tốt.', 'loại nhầm sách tốt')
    n = len(keep)
    labels = min(n, kit.stock(c, 'nhan'))
    if labels:
        kit.take(c, 'nhan', labels)
    if labels < n:
        _slip(t, 'no_label', 1, 'Sách lên kệ mà chưa có nhãn gáy.', 'thiếu nhãn gáy')
    weeded = len(books) - n
    d['today']['shelved'] += n
    d['stats']['shelved'] += n
    d['today']['weeded'] += weeded
    d['stats']['weeded'] += weeded
    who = _who(t)
    tail = f' {who} nhận giấy cảm ơn.' if t['needs']['src'] == 'tang' else ''
    msg = _finish(s, c, d, t, PAY['catalog'], f'Dán nhãn, xếp {n} cuốn lên kệ' + (f', để riêng {weeded} cuốn chờ thanh lý.' if weeded else '.') + tail)
    return dict(message='🏷️ ' + msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the reading room
def _deal(s, c, d, p):
    t = _task(c, p, ('room',))
    _known(t)
    who = kit.one_of(p.get('who'), t['needs']['offenders'], 'Không có ai như vậy trong phòng.')
    how = kit.one_of(p.get('how'), LC.ANSWERS, 'Chọn cách nhắc.')
    st = t['st']
    row = st['done'].get(who)
    kit.need(row is None or row['res'] == 'blowup', 'Chuyện này xong rồi.')
    kit.start_work(t)
    emoji, title, text, best, ok, bad, safety, offer = LC.OFFENCES[who]
    tries = (row or {}).get('tries', 0) + 1
    if how == 'ignore':
        sev = bad.get('ignore', 1)
        st['done'][who] = dict(how='ignore', res='ignored', tries=tries)
        st['quiet'] = max(0, st['quiet'] - 15 * sev)
        _slip(t, f'r_{who}'[:32], sev, f'{title} mà cán bộ thư viện để kệ.', f'bỏ qua: {_lower(title)}', safety=safety)
        return dict(message=f'🙈 Để kệ. {emoji} {title} cứ thế tiếp tục, mấy bàn bên lắc đầu.', correct=False)
    if how in bad:
        _slip(t, f'r_{who}'[:32], bad[how], f'{title}: cách nhắc chưa hợp, làm to chuyện.' if how == 'out' else f'{title}: xử lý chưa đúng cách.',
              f'nhắc chưa hợp: {_lower(title)}', safety=safety and bad[how] >= 2)
    if row and row['res'] == 'blowup':
        # A second word: a firm one ends it; cô Nguyệt or the ward guard steps in when it does not.
        res = 'sulk'
        st['done'][who] = dict(how=how, res=res, tries=tries)
        st['quiet'] = max(0, st['quiet'] - 5)
        line = ('Bạn nói chắc chắn mà từ tốn. Người kia lẩm bẩm rồi cũng làm theo.' if how in ('rule', 'out', 'offer')
                else 'Người kia vẫn càu nhàu, cô Nguyệt phải ra nói thêm một câu mới xong.')
        return dict(message=f'{emoji} {line}')
    tr = folk.traits(f'{t["id"]}:{who}', OFF_PERSONA.get(who))
    res = folk.word(tr, WORD_OF[how])
    if how in best and res == 'blowup' and tr['rude'] < 60:
        res = 'sulk'      # the right word, said nicely, rarely ends in a scene
    st['done'][who] = dict(how=how, res=res, tries=tries)
    label = offer if how == 'offer' else {'soft': 'Bạn ghé tận nơi nhắc nhỏ', 'rule': 'Bạn chỉ lên bảng nội quy', 'out': 'Bạn mời ra khỏi phòng'}[how]
    if res == 'calm':
        line = f'{label}. Người kia cười ngượng, làm theo ngay.'
        if how in best:
            c['xp'] += 2
    elif res == 'sulk':
        st['quiet'] = max(0, st['quiet'] - 5)
        line = f'{label}. Người kia lầm bầm “gì căng vậy” nhưng cũng thôi.'
    else:
        st['quiet'] = max(0, st['quiet'] - 15)
        t['heat'] = min(9, int(t.get('heat') or 0) + 1)
        line = f'{label}. Người kia cãi lại to tiếng, cả phòng quay lại nhìn. Phải nói thêm một lần nữa.'
    return dict(message=f'{emoji} {title}: {line}', correct=res != 'blowup')


def _rounddone(s, c, d, p):
    t = _task(c, p, ('room',))
    _known(t)
    st = t['st']
    left = [k for k in t['needs']['offenders'] if k not in st['done'] or st['done'][k]['res'] == 'blowup']
    kit.need(not left, 'Còn chuyện trong phòng chưa xong.')
    d['today']['room'] += 1
    quiet = st['quiet']
    tail = 'Phòng đọc yên trở lại, chỉ còn tiếng lật trang.' if quiet >= 80 else 'Phòng đọc tạm yên, vẫn còn vài tiếng xì xào.' if quiet >= 50 else 'Phòng đọc vẫn ồn, mấy người đọc bỏ về sớm.'
    msg = _finish(s, c, d, t, PAY['room'], tail)
    return dict(message='🤫 ' + msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the archive window
def _train(s, c, d, p):
    """Cô Nguyệt's briefing before the first records request (once): every answer right, or try again."""
    kit.need(not d['trained'], 'Đã tập huấn nghiệp vụ lưu trữ rồi.')
    answers = p.get('answers')
    kit.need(isinstance(answers, list) and len(answers) == len(LC.TRAINING), 'Trả lời đủ các câu đã nhé.')
    wrong = [i + 1 for i, (q, a) in enumerate(zip(LC.TRAINING, answers)) if a != q[2]]
    if wrong:
        return dict(message=f'👩‍🏫 Cô Nguyệt: “Câu {", ".join(map(str, wrong))} chưa đúng. Đọc lại rồi làm lại nhé.”', correct=False)
    d['trained'] = True
    c['xp'] += 5
    return dict(message='👩‍🏫 Cô Nguyệt trao chùm chìa khóa kho: “Đúng hết. Hồ sơ của dân là của dân, mình chỉ giữ hộ.”', celebrate=True)


def _see(s, c, d, p):
    t = _task(c, p, ('archive',))
    _known(t)
    what = kit.one_of(p.get('what'), ('id', 'form', 'index'), 'Việc này không có.')
    st, x, n = t['st'], t['_x'], t['needs']
    kit.need(what not in st['seen'], 'Làm rồi.')
    st['seen'].append(what)
    kit.start_work(t)
    if what == 'id':
        docs = ', '.join(_lower(LC.DOCS[k]) for k in n['docs']) or 'không mang giấy tờ gì'
        return dict(message=f'🪪 {_who(t)} đưa: {docs}.')
    if what == 'form':
        return dict(message=f'📝 {_who(t)} điền phiếu yêu cầu: hồ sơ cần xem, mục đích, ký tên.')
    return dict(message=f'📇 Mục lục: “{n["record"]}” · {LC.LEVELS[x["level"]]} · {n["boxes"][x["box"]]}.')


def _decide(s, c, d, p):
    t = _task(c, p, ('archive',))
    _known(t)
    st, x = t['st'], t['_x']
    kit.need(d['trained'], 'Chưa tập huấn nghiệp vụ lưu trữ: làm bài tập huấn của cô Nguyệt trước nhé.')
    kit.need(st['decision'] is None, 'Đã quyết rồi.')
    kit.need('id' in st['seen'] and 'index' in st['seen'], 'Kiểm giấy tờ và tra mục lục trước khi quyết.')
    choice = kit.one_of(p.get('choice'), LC.DECISIONS, 'Chọn cách xử lý.')
    st['decision'] = choice
    right, who = x['right'], _who(t)
    go_on = False
    if choice == right:
        good = True
        if choice in ('give', 'approve'):
            go_on = True
            if choice == 'approve':
                st['approved'] = True
                line = 'Lãnh đạo phường ký duyệt phiếu. Vào kho lấy hồ sơ.'
            else:
                line = 'Đủ điều kiện. Vào kho lấy hồ sơ.'
        else:
            line = ('Bạn chỉ rõ còn thiếu giấy gì, nộp ở đâu, hẹn quay lại.' if choice == 'paper'
                    else 'Bạn giải thích từ tốn vì sao không được, chỉ nơi làm đúng thủ tục.')
    else:
        good = False
        if choice == 'approve' and right == 'give':
            go_on, st['approved'] = True, True
            t['patience'] = max(25, t.get('patience', 100) - 10)
            line = 'Lãnh đạo phường: “Tài liệu này không cần tôi duyệt.” Mất thêm một lúc chờ.'
            good = None
        elif choice == 'give':
            go_on = True
            code, sev, text = {'paper': ('no_papers', 2, 'Cấp hồ sơ khi còn thiếu giấy tờ.'),
                               'approve': ('no_approval', 3, 'Cấp hồ sơ hạn chế mà không có lãnh đạo duyệt.'),
                               'refuse': ('privacy', 3, 'Cấp hồ sơ cá nhân của người khác cho người không có quyền.')}[right]
            _slip(t, code, sev, text, 'cấp sai quy định')
            if right == 'refuse':
                d['stats']['privacy'] += 1
            line = 'Bạn đồng ý cấp. Vào kho lấy hồ sơ.'
        elif choice == 'approve':
            _slip(t, 'push_up', 1, 'Việc không đúng thủ tục mà đẩy lên lãnh đạo, mất thời gian cả hai bên.', 'đẩy việc lên lãnh đạo')
            line = 'Lãnh đạo phường trả phiếu về: “Việc này không duyệt được.”'
        elif choice == 'paper':
            _slip(t, 'wrong_paper', 1, 'Bắt bổ sung giấy tờ vô lý, đi lại mất công.' if right == 'give' else 'Hướng dẫn giấy tờ cho việc không đúng thủ tục, người ta mất công.', 'hướng dẫn chưa đúng')
            line = 'Bạn đưa danh sách giấy tờ cần bổ sung.'
        else:
            _slip(t, 'wrong_refuse', 2 if right == 'give' else 1, 'Đủ điều kiện mà bị từ chối.' if right == 'give' else 'Từ chối mà không chỉ đường làm đúng.', 'từ chối chưa đúng')
            line = 'Bạn từ chối.'
    if go_on:
        return dict(message=f'🗂️ {line}', correct=good is not False)
    msg = _finish(s, c, d, t, PAY['archive'] + cert_bonus(s, c), f'{line} {who} ra về.')
    return dict(message='🗂️ ' + msg, correct=good is not False, celebrate=bool(good) and not cq.slips(t))


def _need_go(t: dict) -> None:
    kit.need(t['st']['decision'] in ('give', 'approve') and (t['st']['decision'] != 'approve' or t['st']['approved']), 'Quyết cấp hồ sơ trước đã.')


def _gear(s, c, d, p):
    t = _task(c, p, ('archive',))
    _need_go(t)
    item = kit.one_of(p.get('item'), ('gang', 'khau_trang'), 'Đồ bảo hộ không có.')
    st = t['st']
    kit.need(item not in st['gear'], 'Đeo rồi.')
    if item == 'gang':
        kit.need(kit.stock(c, 'gang_vai') > 0, 'Hết găng tay vải. Mở kho mua thêm nhé.')
        kit.take(c, 'gang_vai', 1)
    st['gear'].append(item)
    return dict(message='🧤 Đeo găng tay vải sạch.' if item == 'gang' else '😷 Đeo khẩu trang.')


def _box(s, c, d, p):
    t = _task(c, p, ('archive',))
    _need_go(t)
    st, x, n = t['st'], t['_x'], t['needs']
    kit.need(not st['found'], 'Đã lấy được hồ sơ rồi.')
    i = kit.integer(p.get('box'), 0, len(n['boxes']) - 1)
    if st['box'] is None:
        if 'gang' not in st['gear']:
            _slip(t, 'bare', 1, 'Cầm hồ sơ cũ bằng tay trần, mồ hôi tay làm ố giấy.', 'không đeo găng tay')
        if 'khau_trang' not in st['gear']:
            _slip(t, 'dust', 1, 'Mở hộp hồ sơ bụi mà không đeo khẩu trang, ho cả buổi.', 'không đeo khẩu trang')
    st['box'] = i
    if i != x['box']:
        t['mistakes'] += 1
        t['patience'] = max(25, t.get('patience', 100) - 8)
        return dict(message=f'📦 Hộp “{n["boxes"][i]}” là hồ sơ khác. Đọc lại mục lục.', correct=False)
    if x['lost']:
        return dict(message='📦 Mở đúng hộp mục lục ghi… mà không thấy hồ sơ đâu! Đừng vội kết luận mất.', surprise=True)
    st['found'] = True
    return dict(message=f'📦 Lấy được hồ sơ “{n["record"]}”.' + (' Giấy giòn, mép đã mủn: cầm thật nhẹ tay.' if x['fragile'] else ''))


SEARCH = {'neighbour': 'Tìm các hộp kế bên', 'log': 'Xem sổ giao nhận hồ sơ', 'report': 'Lập biên bản thất lạc, báo lãnh đạo'}


def _search(s, c, d, p):
    t = _task(c, p, ('archive',))
    _need_go(t)
    st, x = t['st'], t['_x']
    kit.need(x['lost'] and st['box'] == x['box'] and not st['found'], 'Không cần tìm thêm.')
    where = kit.one_of(p.get('where'), SEARCH, 'Cách tìm không có.')
    kit.need(where not in st['search'], 'Tìm chỗ đó rồi.')
    st['search'].append(where)
    if where == 'report':
        _slip(t, 'hasty_report', 2, 'Chưa tìm kỹ đã lập biên bản mất hồ sơ, sau mới thấy nằm ngay hộp bên.', 'báo mất khi chưa tìm kỹ')
        msg = _finish(s, c, d, t, PAY['archive'], 'Lập biên bản thất lạc, hẹn người dân khi có kết quả.')
        return dict(message='🗂️ ' + msg, correct=False)
    if where == 'neighbour':
        if x['lost'] == 'misfiled':
            st['found'] = True
            return dict(message='🔍 Hồ sơ kẹp nhầm trong hộp kế bên! Bạn đặt lại đúng chỗ, ghi chú vào mục lục.', celebrate=True)
        return dict(message='🔍 Hộp kế bên không có. Xem sổ giao nhận thử.')
    if x['lost'] == 'lent':
        st['found'] = True
        return dict(message='🔍 Sổ giao nhận ghi: phòng địa chính mượn từ tuần trước, chưa trả. Gọi điện, họ mang trả ngay.', celebrate=True)
    return dict(message='🔍 Sổ giao nhận không ghi ai mượn. Tìm các hộp kế bên thử.')


COPY = {'copy': 'Sao chụp, đóng dấu sao y bản lưu trữ', 'original': 'Đưa bản gốc cho mang đi'}


def _copy(s, c, d, p):
    t = _task(c, p, ('archive',))
    _need_go(t)
    st, x = t['st'], t['_x']
    kit.need(st['found'], 'Lấy được hồ sơ đã.')
    kit.need(st['copy'] is None, 'Làm rồi.')
    how = kit.one_of(p.get('how'), COPY, 'Cách cấp không có.')
    st['copy'] = how
    who = _who(t)
    if how == 'original':
        if x['orig']:
            return dict(message='📜 Bản gốc cho ủy ban mượn theo phiếu đã duyệt, hẹn trả trong ngày. Nhớ ghi sổ, người nhận ký.')
        _slip(t, 'original_out', 3 if x['fragile'] else 2, 'Bản gốc lưu trữ mang ra khỏi kho, không ai biết bao giờ về.', 'đưa bản gốc ra ngoài')
        return dict(message=f'📜 Bạn đưa bản gốc cho {who}… Cô Nguyệt nhìn thấy, mặt biến sắc.', correct=False)
    if t['npc'] != kit.npc_id(ID, 5):
        kit.money(s, c, LC.COPY_FEE, f'Phí sao lục hồ sơ: {who}'[:120], t['id'], 'copy_fee')
    if x['orig']:
        _slip(t, 'copy_only', 1, 'Ủy ban đã duyệt mượn bản gốc mà chỉ đưa bản sao, phải chạy xuống lấy lại.', 'chưa đúng phiếu duyệt')
    return dict(message=f'🖨️ Sao chụp rõ nét, đóng dấu “sao y bản lưu trữ”' + ('.' if t['npc'] == kit.npc_id(ID, 5) else f', thu {LC.COPY_FEE} xu, đưa biên lai.'))


def _log(s, c, d, p):
    t = _task(c, p, ('archive',))
    _need_go(t)
    kit.need(not t['st']['logged'], 'Đã ghi sổ rồi.')
    t['st']['logged'] = True
    return dict(message='📒 Ghi sổ khai thác: ngày, hồ sơ, mục đích; người nhận ký tên.')


def _handover(s, c, d, p):
    t = _task(c, p, ('archive',))
    _need_go(t)
    st = t['st']
    kit.need(st['copy'] is not None, 'Sao chụp hồ sơ trước đã.')
    if not st['logged']:
        _slip(t, 'no_log', 2, 'Hồ sơ ra vào không ghi sổ khai thác.', 'không ghi sổ')
    if 'form' not in st['seen']:
        _slip(t, 'no_form', 1, 'Cấp hồ sơ mà không có phiếu yêu cầu.', 'thiếu phiếu yêu cầu')
    d['today']['records'] += 1
    d['stats']['records'] += 1
    msg = _finish(s, c, d, t, PAY['archive'] + cert_bonus(s, c), f'Trả hộp về kệ, bàn giao cho {_who(t)}.')
    return dict(message='🗂️ ' + msg, celebrate=not cq.slips(t))


def _chase(s, c, d, p):
    return folk.chase_action(s, c, ID, d['debts'], p, _persona)


ACTIONS = {
    'tv_ask': _ask,
    'tv_look': _look, 'tv_dehum': _dehum, 'tv_pest': _pest, 'tv_openup': _openup,
    'tv_lookup': _lookup, 'tv_card': _card, 'tv_renew': _renew, 'tv_settle': _settle, 'tv_lend': _lend, 'tv_offer': _offer,
    'tv_inspect': _inspect, 'tv_date': _date, 'tv_why': _why, 'tv_fine': _fine, 'tv_fee': _fee_act, 'tv_repair': _repair, 'tv_shelve': _shelve,
    'tv_q': _q, 'tv_rec': _rec,
    'tv_class': _class, 'tv_mark': _mark, 'tv_weed': _weed, 'tv_catdone': _catdone,
    'tv_deal': _deal, 'tv_rounddone': _rounddone,
    'tv_train': _train, 'tv_see': _see, 'tv_decide': _decide, 'tv_gear': _gear, 'tv_box': _box, 'tv_search': _search,
    'tv_copy': _copy, 'tv_log': _log, 'tv_handover': _handover,
    'tv_chase': _chase,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'open' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    opening = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'open' and t['day'] == day
                    and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if opening is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        opening = make_task(day, 0, c['turn'])
        c['tasks'].append(opening)
        on_task(s, c, opening)
    if opening:
        c['active_task'] = opening['id']
        opening['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], LC.DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    for note in folk.auto_repay(s, c, ID, d['debts'], _persona):
        kit.log(s, c, 'surprise', note)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], LC.DESK)
    td = d['today']
    lines = [f'📚 Làm {td["jobs"]} việc: cho mượn {td["lent"]} cuốn, nhận trả {td["returned"]}, biên mục {td["shelved"]} cuốn, {td["records"]} lượt hồ sơ.']
    if td['fines']:
        lines.append(f'💵 Thu {td["fines"]} xu phí trả trễ, phí hỏng sách.')
    if td['waived']:
        lines.append(f'🤝 Miễn giảm {td["waived"]} xu.')
    if td['overcharged']:
        lines.append(f'🧾 Cô Nguyệt dò sổ: thu quá nội quy {td["overcharged"]} xu. “Tiền phạt là để nhắc, không phải để kiếm.”')
    if td['asks']:
        lines.append(f'🙋 {td["asks"]} lần có người nhờ vả, {td["good_asks"]} lần trả lời khéo đúng nội quy.')
    if desk_note:
        lines.append(desk_note)
    owe = folk.open_debts(d['debts'])
    if owe:
        lines.append(f'📒 Sổ nợ phí còn {len(owe)} người.')
    return dict(lines=lines, note='Sáng mai nhớ xem ẩm kế kho và soi bẫy trước khi mở phòng đọc.', jobs=td['jobs'], lent=td['lent'],
                fines=td['fines'], waived=td['waived'], overcharged=td['overcharged'], shelved=td['shelved'], records=td['records'])


# ================================================================ reviews
CRITERIA = {
    'open': (('care', 'Giữ kho tốt'), ('ready', 'Mở cửa đủ bước')),
    'desk': (('rule', 'Đúng nội quy'), ('fair', 'Phí công bằng'), ('kind', 'Mềm mỏng'), ('speed', 'Nhanh')),
    'catalog': (('class', 'Phân loại đúng'), ('weed', 'Lọc sách hỏng'), ('rule', 'Đúng quy định'), ('speed', 'Nhanh')),
    'room': (('quiet', 'Phòng đọc yên'), ('kind', 'Mềm mỏng'), ('safe', 'An toàn'), ('speed', 'Nhanh')),
    'archive': (('law', 'Đúng thủ tục'), ('privacy', 'Giữ kín hồ sơ'), ('care', 'Giữ gìn bản gốc'), ('speed', 'Nhanh')),
}
CODE_CRIT = {
    'no_hum': 'care', 'damp': 'care', 'no_trap': 'care', 'spray': 'care', 'pest': 'care', 'pest_wrong': 'care', 'no_board': 'ready',
    'ref_out': 'rule', 'card': 'rule', 'limit': 'rule', 'debt_card': 'rule', 'wrong_offer': 'rule', 'needless_no': 'kind',
    'lenient': 'fair', 'overcharge': 'fair', 'overcharge_caught': 'fair', 'no_reason': 'fair',
    'tape': 'rule', 'heat': 'rule', 'wrong_fix': 'rule', 'unrepaired': 'rule', 'rec_miss': 'rule', 'rec_meh': 'rule',
    'wrong_class': 'class', 'wrong_mark': 'class', 'junk_shelved': 'weed', 'weeded_good': 'weed', 'no_label': 'class',
    'no_papers': 'law', 'no_approval': 'privacy', 'privacy': 'privacy', 'push_up': 'law', 'wrong_paper': 'law', 'wrong_refuse': 'law',
    'bare': 'care', 'dust': 'care', 'hasty_report': 'law', 'original_out': 'care', 'copy_only': 'law', 'no_log': 'law', 'no_form': 'law',
}
NOTES = {'care': 'kho, sách, bản gốc được giữ gìn', 'ready': 'đủ bước buổi sáng', 'rule': 'làm đúng nội quy', 'fair': 'phí đúng nội quy',
         'kind': 'nói năng mềm mỏng', 'class': 'lớp, ký hiệu đúng', 'weed': 'lọc đúng sách hỏng', 'quiet': 'phòng đọc yên',
         'safe': 'không để chuyện nguy hiểm', 'law': 'đúng thủ tục lưu trữ', 'privacy': 'không lộ hồ sơ của ai'}


def _crit_of(t: dict, code: str) -> str:
    keys = [k for k, _ in CRITERIA[t['kind']]]
    if code.startswith('d_'):
        x = LC.DEMAND.get(code[2:])
        want = 'privacy' if x and x['typ'] == 'privacy' else 'safe' if x and x['typ'] == 'safety' else 'rule'
    elif code.startswith('r_'):
        off = LC.OFFENCES.get(code[2:])
        want = 'safe' if off and off[6] else 'quiet'
    else:
        want = CODE_CRIT.get(code, keys[0])
    return want if want in keys else ('law' if 'law' in keys else keys[0])


def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 80 else 4 if p >= 60 else 3 if p >= 40 else 2
    lost = {}
    for r in cq.slips(t):
        k = _crit_of(t, r['code'])
        lost[k] = lost.get(k, 0) + r['sev']
    rows = []
    for key, label in CRITERIA.get(t['kind'], CRITERIA['desk']):
        if key == 'speed':
            rows.append(dict(key='speed', label=label, score=speed, note=f'chờ còn {p}% kiên nhẫn'))
            continue
        score = max(1, 5 - lost.get(key, 0))
        if key == 'kind':
            score = max(1, score - min(2, int(t.get('heat') or 0)))
        if key == 'quiet' and isinstance(t.get('st'), dict):
            q = t['st'].get('quiet', 100)
            score = max(1, min(score, 5 if q >= 80 else 4 if q >= 60 else 3 if q >= 40 else 2))
        rows.append(dict(key=key, label=label, score=score, note=NOTES.get(key, label) if score == 5 else 'chưa ổn'))
    return dict(criteria=rows)


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n, k = t['needs'], t['kind']
    if k == 'open':
        return 'Buổi sáng: xem ẩm kế kho, soi bẫy, mở phòng đọc, dựng bảng nội quy. ' + n['note']
    if k == 'desk':
        if n['mode'] == 'recommend':
            return f'{_who(t)} nhờ gợi ý một cuốn sách: hỏi gu trước, rồi chọn một trong bốn cuốn.'
        title = LC.LOANS[n['book']][0]
        return f'{_who(t)} {"muốn mượn" if n["mode"] == "borrow" else "trả"} cuốn “{title}”.'
    if k == 'catalog':
        return f'{len(n["books"])} cuốn {"sách tặng" if n["src"] == "tang" else "sách mới"} chờ biên mục: xếp lớp, ghi ký hiệu tác giả, lọc sách hỏng.'
    if k == 'room':
        return 'Phòng đọc: ' + ', '.join(_lower(LC.OFFENCES[o][1]) for o in n['offenders']) + '.'
    return f'{_who(t)} xin hồ sơ “{n["record"]}” · mục đích: {_lower(n["purpose"])}.'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    v.pop('dm', None)
    dm, x = t.get('dm'), _demand(t)
    if x and dm['state'] != 'wait':
        v['ask'] = dict(id=x['id'], state=dm['state'], choice=dm['choice'], who=x['who'], text=x['text'], alt=x['alt'], yes=x['yes'], no=x['no'])
    if not v['known']:
        v['needs'] = None
        return v
    h, st, kind, n = t['_x'], t['st'], t['kind'], t['needs']
    if kind == 'open':
        v['hum'] = h['hum'] if 'am' in st['seen'] else None
        v['pest'] = h['pest'] if 'bay' in st['seen'] else None
    elif kind == 'desk':
        mode = n['mode']
        if mode == 'borrow':
            title, call, shelf = LC.LOANS[n['book']]
            v['info'] = dict(title=title, call=call, shelf=shelf, status=h['status'], back=h['back']) if st['looked'] else dict(title=title)
            v['cardinfo'] = dict(card=h['card'], owe=h['owe']) if st['carded'] else None
        elif mode == 'return':
            v['info'] = dict(title=LC.LOANS[n['book']][0], call=LC.LOANS[n['book']][1])
            v['damage'] = h['damage'] if st['inspected'] else None
            v['late'] = h['late'] if st['dated'] else None
            v['excuse'] = (LC.EXCUSE[h['excuse']][0] if h['late'] else '“Đúng hạn mà.”') if st['why'] else None
            if st['inspected'] and st['dated']:
                v['fees'] = dict(late=late_fee(h['late']), damage=dmg_fee(h), price=h['price'] if h['damage'] == 'lost' else None)
        else:
            v['clues'] = {q: (LC.TASTE_LAST[h['genre']] if q == 'last' else LC.TASTE_MOOD[h['easy']]) for q in st['asked']}
            v['cands'] = [dict(id=b, title=LC.LOANS[b][0], call=LC.LOANS[b][1], genre=LC.GENRE[LC.TASTE[b][0]], easy=LC.TASTE[b][1]) for b in n['cands']]
    elif kind == 'catalog':
        v['books'] = [dict(id=b, title=LC.BOOKS[b][0], author=LC.BOOKS[b][1], hint=LC.BOOKS[b][3]) for b in n['books']]
    elif kind == 'room':
        v['offenders'] = [dict(id=o, emoji=LC.OFFENCES[o][0], title=LC.OFFENCES[o][1], text=LC.OFFENCES[o][2], offer=LC.OFFENCES[o][7]) for o in n['offenders']]
    elif kind == 'archive':
        if 'id' not in st['seen']:
            v['needs'] = dict(n, docs=None)
        v['index'] = dict(level=h['level'], label=LC.LEVELS[h['level']], box=h['box']) if 'index' in st['seen'] else None
        v['lost'] = bool(h['lost']) and st['box'] == h['box'] and not st['found']
    return v


def public_data(c: dict) -> dict:
    d = tree_copy(c['ext']['data'])
    for k, v in initial().items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    return dict(intro=d['intro'], trained=d['trained'], mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], LC.DESK, ID), debts=folk.public_debts(d['debts']))


def content() -> dict:
    return dict(intro=LC.INTRO, classes=LC.CLASSES, class_tips=list(LC.CLASS_TIPS), weed=LC.WEED,
                damage={k: dict(label=v[0], fee=v[1]) for k, v in LC.DAMAGE.items()}, repair={k: v[0] for k, v in LC.REPAIR.items()},
                fine_day=LC.FINE_DAY, fine_cap=LC.FINE_CAP, card_fee=LC.CARD_FEE, copy_fee=LC.COPY_FEE, loan_days=LC.LOAN_DAYS, loan_max=LC.LOAN_MAX,
                loans={k: dict(title=v[0], call=v[1], shelf=v[2]) for k, v in LC.LOANS.items()}, offers=OFFERS,
                answers=dict(LC.ANSWER_LABEL), levels=LC.LEVELS, decisions=LC.DECISIONS, docs=LC.DOCS, search=SEARCH, copy=COPY,
                training=[dict(q=q, options=[dict(id=o, label=l) for o, l in opts]) for q, opts, _ in LC.TRAINING],
                pests=LC.PESTS, pest_fix=LC.PEST_FIX, hum_ok=list(LC.HUM_OK), excuse_rule='Trả trễ vì ốm đau nằm viện, thiên tai (có giấy tờ, lời xác nhận): được miễn phí trễ hạn, ghi rõ lý do.',
                debt_max=folk.DEBT_MAX, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'open':
        return 'Xem ẩm kế (trên 60% thì bật máy hút ẩm) → soi bẫy, xử lý đúng → mở phòng đọc → dựng bảng nội quy → Mở cửa.'
    if k == 'catalog':
        return 'Mỗi cuốn: chọn lớp, chọn ký hiệu tác giả (3 chữ đầu của tên) hoặc để riêng sách hỏng → Xếp lên kệ.'
    if k == 'room':
        return 'Mỗi chuyện trong phòng: chọn cách nhắc hợp với chuyện đó; ai cãi lại thì nói thêm một lần → Xong vòng phòng đọc.'
    if k == 'archive':
        return 'Kiểm giấy tờ → phiếu yêu cầu → tra mục lục → quyết → găng tay, khẩu trang → lấy đúng hộp → sao y → ghi sổ → bàn giao.'
    mode = (t.get('needs') or {}).get('mode')
    if mode == 'return':
        return 'Kiểm sách → xem dấu hạn → hỏi lý do nếu trễ → tự đề xuất phí (1 xu/ngày, tối đa 15, cộng phí hỏng) → sửa sách → cất lên kệ.'
    if mode == 'recommend':
        return 'Hỏi cuốn gần nhất thích và đang muốn đọc gì → chọn cuốn hợp cả hai.'
    return 'Tra máy → kiểm thẻ → cho mượn, hoặc gia hạn thẻ, thu nợ cũ, mời đọc tại chỗ, đặt trước.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'shelf':
        return 'Đã xếp lại kệ trả sách theo ký hiệu, lau bụi một dãy kệ.'
    if e.get('role') == 'room':
        if t and t.get('career') == ID and t.get('kind') == 'room' and t['status'] not in ('completed', 'cancelled') and t.get('known'):
            for o in t['needs']['offenders']:
                if o not in t['st']['done'] and not LC.OFFENCES[o][6]:
                    t['st']['done'][o] = dict(how='soft', res='calm', tries=1)
                    return f'Đã ghé nhắc nhỏ: {_lower(LC.OFFENCES[o][1])}.'
        return 'Đã đi một vòng phòng đọc, nhắc nhỏ mấy bàn nói chuyện.'
    return None


# ================================================================ saves
def _vbool(v) -> None:
    kit.need(type(v) is bool, 'Dữ liệu thư viện sai.')


def _vlist(v, allowed, n: int) -> None:
    kit.need(isinstance(v, list) and len(v) <= n and len(set(v)) == len(v) and all(x in allowed for x in v), 'Dữ liệu thư viện sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS, 'Việc thư viện không hợp lệ.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện bạn đọc sai.')
    if 'heat' in t:
        kit.integer(t['heat'], 0, 9)
    st, k, n = t.get('st'), t['kind'], t.get('needs') or {}
    kit.need(isinstance(st, dict), 'Việc thư viện sai.')
    if k == 'open':
        kit.need(set(st) == {'seen', 'dehum', 'pest', 'room', 'board'}, 'Việc buổi sáng sai.')
        _vlist(st['seen'], ('am', 'bay'), 2)
        for x in ('dehum', 'room', 'board'):
            _vbool(st[x])
        kit.need(st['pest'] in (None, *LC.PEST_FIX), 'Việc buổi sáng sai.')
    elif k == 'desk':
        mode = n.get('mode')
        keys = {'borrow': {'looked', 'carded', 'renewed', 'settled'}, 'return': {'inspected', 'dated', 'why', 'repair', 'shelved'},
                'recommend': {'asked', 'pick'}}.get(mode)
        kit.need(keys is not None and set(st) == keys, 'Việc ở quầy sai.')
        if mode == 'recommend':
            _vlist(st['asked'], ('last', 'mood'), 2)
            kit.need(st['pick'] in (None, *n['cands']), 'Việc ở quầy sai.')
        else:
            for x in keys - {'repair'}:
                _vbool(st[x])
            if mode == 'return':
                kit.need(st['repair'] in (None, *LC.REPAIR), 'Việc ở quầy sai.')
        fee = t.get('fee')
        if fee is not None:
            kit.need(isinstance(fee, dict) and set(fee) == {'state', 'asked', 'counter', 'tries', 'paid', 'tone'} and fee['state'] in FEE_STATES
                     and fee['tone'] in (None, 'soft', 'strict'), 'Phí sai.')
            for x in ('asked', 'counter'):
                if fee[x] is not None:
                    kit.integer(fee[x], 0, 300)
            kit.integer(fee['tries'], 0, 9)
            kit.integer(fee['paid'], 0, 300)
    elif k == 'catalog':
        kit.need(set(st) == {'cls', 'mark', 'weed'} and all(isinstance(st[x], dict) for x in st), 'Việc biên mục sai.')
        books = n.get('books') or []
        for b, v in st['cls'].items():
            kit.need(b in books and v in LC.CLASS_IDS, 'Việc biên mục sai.')
        for b, v in st['mark'].items():
            kit.need(b in books and v in n['marks'][b], 'Việc biên mục sai.')
        for b, v in st['weed'].items():
            kit.need(b in books and v in LC.WEED, 'Việc biên mục sai.')
    elif k == 'room':
        kit.need(set(st) == {'done', 'quiet'} and isinstance(st['done'], dict), 'Việc phòng đọc sai.')
        kit.integer(st['quiet'], 0, 100)
        for o, v in st['done'].items():
            kit.need(o in n.get('offenders', ()) and isinstance(v, dict) and set(v) == {'how', 'res', 'tries'} and v['how'] in LC.ANSWERS
                     and v['res'] in ('calm', 'sulk', 'blowup', 'ignored'), 'Việc phòng đọc sai.')
            kit.integer(v['tries'], 1, 9)
    else:
        kit.need(set(st) == {'seen', 'decision', 'approved', 'box', 'found', 'search', 'gear', 'copy', 'logged'}, 'Việc lưu trữ sai.')
        _vlist(st['seen'], ('id', 'form', 'index'), 3)
        _vlist(st['search'], SEARCH, 3)
        _vlist(st['gear'], ('gang', 'khau_trang'), 2)
        kit.need(st['decision'] in (None, *LC.DECISIONS) and st['approved'] in (None, True) and st['copy'] in (None, *COPY), 'Việc lưu trữ sai.')
        if st['box'] is not None:
            kit.integer(st['box'], 0, len(n.get('boxes') or ()) - 1)
        for x in ('found', 'logged'):
            _vbool(st[x])
    if 'dm' in t:
        dm = t['dm']
        x = LC.DEMAND.get(dm.get('id')) if isinstance(dm, dict) else None
        kit.need(x is not None and k in x['kinds'] and set(dm) == {'id', 'state', 'choice'} and dm['state'] in DM_STATES
                 and dm['choice'] in (None, *LC.CHOICES), 'Chuyện nhờ vả sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    for k in ('intro', 'trained'):
        _vbool(d[k])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in LC.REG_STORY}, 'Sổ bạn đọc quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ bạn đọc quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu thư viện sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], LC.DESK)
    folk.validate_debts(d['debts'], len(PEOPLE), kit.need)


# ================================================================ items in the storeroom
ITEMS = [
    dict(id='nhan', name='Nhãn gáy sách', emoji='🏷️', group='supply', unit='tờ', cost=1, life=720, start=16),
    dict(id='bang_giay', name='Băng giấy sửa sách', emoji='🩹', group='supply', unit='cuộn', cost=3, life=720, start=4),
    dict(id='gang_vai', name='Găng tay vải cotton', emoji='🧤', group='gear', unit='đôi', cost=1, life=180, start=6),
]

# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='tv_', category='service',
    meta=dict(short='Thư viện – Lưu trữ', place='Thư viện – Lưu trữ phường Mây', tagline='Đúng nội quy, đúng ký hiệu, kín hồ sơ.', icon='book',
              color='#5b6f9e', light='#e8ecf6', weather='Nắng nhẹ qua ô cửa phòng đọc', work='Việc ở thư viện', station='Quầy mượn trả',
              greeting='Sáng xem ẩm kế kho, soi bẫy, mở phòng đọc. Ở quầy: tra máy, kiểm thẻ, tính phí đúng nội quy. Hồ sơ lưu trữ: đủ giấy tờ mới cấp.',
              caption='Mỗi cuốn sách một chỗ, mỗi hồ sơ một chủ', map_label='33 · THƯ VIỆN PHƯỜNG MÂY'),
    people=PEOPLE,
    staff=[('Hằng', 'shelf', 'Thuộc ký hiệu cả kho, xếp giá nhanh như chớp.', 82, 90),
           ('Khoa', 'room', 'Sinh viên làm thêm, nhắc ai cũng nhẹ nhàng, chẳng ai giận.', 76, 88),
           ('Mỹ', 'shelf', 'Tỉ mỉ, dán nhãn thẳng tắp, ghét sách xếp lộn.', 74, 94),
           ('Phát', 'room', 'Cao to, hiền khô, đứng đâu là chỗ đó im lặng.', 84, 80)],
    roles={'shelf': 'Xếp giá, dán nhãn', 'room': 'Trực phòng đọc'},
    inventory=dict(items=ITEMS, capacity=40),
    tip=1,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🏷️', 'Xếp sách đúng kệ', [('Bếp nhà ngày mưa', '600'), ('Thơ tình mùa hạ', '800'), ('Truyện cổ tích làng', '300'), ('Từ điển chính tả', '400')],
              ['Xem ẩm kế, soi bẫy', 'Tra máy, kiểm thẻ', 'Tính phí đúng nội quy', 'Kín hồ sơ, đúng thủ tục']),
    stories=LC.STORIES,
    review_asides=LC.REVIEW_ASIDES,
    situations=LC.SITUATIONS,
    more_line='Có bạn đọc mới tới quầy.',
    open_line='Cô Nguyệt mở cửa nhà văn hóa. Xem ẩm kế kho, soi bẫy rồi mở phòng đọc nhé.',
    guide='Sáng: ẩm kế kho, bẫy côn trùng, mở phòng đọc. Quầy: tra máy, kiểm thẻ, cho mượn; nhận trả: kiểm sách, tính phí đúng nội quy, sửa sách. '
          'Biên mục: lớp + ký hiệu tác giả, lọc sách hỏng. Phòng đọc: nhắc khéo. Lưu trữ: giấy tờ, mục lục, đúng hộp, sao y, ghi sổ.',
)
