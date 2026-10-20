"""💛 Thân thiết với NPC: what being close to someone is worth (owner 21/10: "để mọi người biết sự quan trọng của việc lấy
lòng NPC", "lấy lòng NPC thì kinh doanh được nhiều tiền hơn … hoặc là sẽ được mở thêm gì đó mà mọi người k biết").

Built on Điểm thân quen (game/closeness.py: one 0–100 score per person, five tiers, chats, gifts, invites, reviews and
the gentle decay after 14 days apart). That module still owns the score; this one adds what the score is worth and a
few more reasons to come back each day. Every number is decided here, on the server:

* 💼 Khách ruột: finishing a job for a customer at Người quen or closer pays PAY_PCT % more (2 / 4 / 6 %), +KEEP_PCT if
  you chatted or gave them something in the last KEEP_DAYS Vietnam days; Bà Sáu's 📜 bí kíp adds RECIPE_PCT on food
  careers; a 🤝 khách sộp referral adds REF_PCT on its jobs. At most MAX_PCT % of the job's pay, JOB_CAP xu a job and
  DAY_CAP xu a Vietnam day for the whole save, only on a life day inside the real-time allowance (interest_clock.
  day_paid), into the career's fund with category 'revenue' (engine.task_done → pay_bonus). Never on a player order.
* 🏘️ Each neighbour has their own perks: Bà Tám bớt tiền phòng (−10 / −20 % rent while living in her attic:
  journey.living_cost → living), Cô Ba sells street gifts 10 / 20 % cheaper and, hidden, a jar of homemade me; one
  weekly favour each (qn_favour: a meal, a parcel into the gift bag, the tổ party, a referral post, strong tea, the
  secret rooftop, vegetables), once per FAVOUR_DAYS Vietnam days.
* 🔒 Hidden rows (content HIDDEN flag) read "???" until reached; when one opens, that person says so in the 💌 inbox
  (a closeness 'care' row, a kind every release accepts) and the 👥 menu shows a ✨ badge until the sheet is opened
  (qn_gw_seen). Chuyện riêng: a neighbour at Như người nhà after ERRANDS_FOR_STORY small favours done for them.
* 📝 Việc nhờ: one small request a Vietnam day from someone you know (bring something with a tag): done by giving
  them any gift with that tag, +ERRAND_GAIN. 🎂 Sinh nhật: a gift on their birthday (Vietnam date) counts twice, once
  a Vietnam day.
* Rate limit: chats and gifts move one person's score by at most VN_GAIN_CAP a Vietnam day (closeness still allows
  one chat and one gift per life day; life days can be ended quickly, real days cannot).

Save: s['journey'][KEY] (optional; absent until the first goodwill event; an older release keeps it unread:
journey.validate allows extra keys, tests/test_goodwill.py replays that rule). Nothing in closeness' own block (an
older release checks its keys exactly), no new title, no new inbox kind, no new bag item, no new ledger category.

Kill switch MNL_NPCGW_OFF=1: every perk off, no new gain (errands, birthdays, reveals, favours, referrals), the per-day
cap lifted (the closeness rules of before); the block is kept untouched and works again when the switch is cleared.
"""
from __future__ import annotations

import datetime
import os
import random

from .goodwill_content import (BIRTHDAY_LINE, BIRTHDAYS, CAST, COMMON, ERRAND_ASK, ERRAND_DONE, ERRANDS, ERRANDS_FOR_STORY,
                               FAVOUR_ITEMS, FAVOUR_LINES, FAVOURS, HIDDEN_GIFT, KEEP_PCT, PAY_PCT, REFER_LINE, REVEAL,
                               STORIES, TITLES)

KEY = 'npcgw'
VERSION = 1
MAX_PCT = 10          # % of one job's pay, everything added
JOB_CAP = 200         # xu one job's bonus pays at most
DAY_CAP = 1000        # xu a Vietnam day, the whole save
KEEP_DAYS = 7         # "giữ liên lạc": a chat or a gift within this many Vietnam days
RECIPE_PCT = 2
REF_PCT = 10
REF_JOBS = 3
REF_DAYS = 7
FAVOUR_DAYS = 7
VN_GAIN_CAP = 12      # closeness one person gains from chats and gifts in one Vietnam day
ERRAND_GAIN = 3
SPIRIT = dict(ba_tam=5, co_lua=3, be_ti=6, chu_tu=3)
WAKE = 20
PARTY_GAIN = 1
RENT_PCT = {4: 10, 5: 20}
SHOP_PCT = {4: 10, 5: 20}
PEOPLE_MAX = 400
LIST_MAX = 60
FOOD = ('milk_tea', 'restaurant', 'cafe_bakery', 'tra_da', 'fruit', 'ice_cream', 'pho', 'com', 'naucom', 'banquet')
KEYS = {'v', 'p', 'fav', 'ref', 'pay', 'err', 'errn', 'told', 'seen'}
REF_KEYS = {'c', 'n', 'u', 'by'}
ERR_KEYS = {'d', 'who', 'tag', 'st'}
BLOCK_DEFAULT = dict(v=VERSION, p={}, fav={}, ref=None, pay=[0, 0], err=None, errn={}, told=[], seen=[])


def off() -> bool:
    return os.environ.get('MNL_NPCGW_OFF') == '1'


def vn_day(t: float | None = None) -> int:
    """Days since 1970 in Vietnam time (the game's test clock: careers.kit)."""
    if t is None:
        from .careers import kit
        t = kit.now()
    return int((t + 7 * 3600) // 86400)


def _qn():
    from . import closeness
    return closeness


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _block(s: dict) -> dict | None:
    """The block, created on first use (None outside a journey)."""
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict):
        return None
    b = j.get(KEY)
    if not isinstance(b, dict):
        b = j[KEY] = {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in BLOCK_DEFAULT.items()}
    return b


def _trim(d: dict, order) -> None:
    while len(d) > PEOPLE_MAX:
        d.pop(min(d, key=order))


def _person(b: dict, pid: str) -> list:
    """[gain day, gained that day, last touch day, birthday bonus day]."""
    row = b['p'].get(pid)
    if row is None:
        row = b['p'][pid] = [0, 0, 0, 0]
        _trim(b['p'], lambda k: b['p'][k][2])
    return row


def _tier(s: dict, pid: str) -> int:
    return _qn().tier(s, pid)


def _cast(pid: str) -> bool:
    return _qn().is_cast(pid)


def _story_mode(s: dict) -> bool:
    return bool((s.get('journey') or {}).get('story'))


# ---------------------------------------------------------------- rate limit and contact
def cap(s: dict, pid: str, delta: int) -> int:
    """A chat's or a gift's gain, within VN_GAIN_CAP for this person today (losses pass)."""
    if off() or delta <= 0:
        return delta
    b = _block(s)
    if b is None:
        return delta
    row = _person(b, pid)
    vn = vn_day()
    if row[0] != vn:
        row[0], row[1] = vn, 0
    allowed = max(0, min(delta, VN_GAIN_CAP - row[1]))
    row[1] += allowed
    return allowed


def room(s: dict, pid: str) -> int:
    """What chats and gifts can still add to this person today (VN_GAIN_CAP while off)."""
    b = get(s)
    row = (b or {}).get('p', {}).get(pid)
    if off() or not row or row[0] != vn_day():
        return VN_GAIN_CAP
    return max(0, VN_GAIN_CAP - row[1])


def touch(s: dict, pid: str) -> None:
    """A chat or a gift: "giữ liên lạc" for KEEP_DAYS days."""
    if off():
        return
    b = _block(s)
    if b is not None:
        _person(b, pid)[2] = vn_day()


def kept(s: dict, pid: str, vn: int | None = None) -> bool:
    b = get(s)
    row = (b or {}).get('p', {}).get(pid)
    vn = vn_day() if vn is None else vn
    return bool(row) and row[2] > 0 and vn - row[2] < KEEP_DAYS


# ---------------------------------------------------------------- unlocks
def _rows(pid: str | None) -> tuple:
    return CAST.get(pid, ()) if pid else COMMON


def _row(pid: str, rid: str):
    return next((r for r in CAST.get(pid, ()) if r[1] == rid), None)


def _has(s: dict, pid: str, rid: str) -> bool:
    """A neighbour's perk row is reached (tier, and the errands for a Chuyện riêng). False while off."""
    if off():
        return False
    r = _row(pid, rid)
    if r is None or _tier(s, pid) < r[0]:
        return False
    if rid == 'story':
        return ((get(s) or {}).get('errn') or {}).get(pid, 0) >= ERRANDS_FOR_STORY
    return True


def _best_customer(s: dict) -> int:
    best = 0
    qn = _qn()
    for c in (s.get('careers') or {}).values():
        for npc, v in ((c or {}).get('relationships') or {}).items() if isinstance(c, dict) else ():
            if type(v) is int and v > best and npc not in qn.ALIAS:
                best = v
    return best


def reached(s: dict) -> list[str]:
    """Ids of the hidden rows reached now: 'pid:row', 'refer' (a customer at Như người nhà), 'all' (every neighbour
    at Thân thiết)."""
    if off():
        return []
    out = []
    for pid, rows in CAST.items():
        for r in rows:
            if r[5] and _has(s, pid, r[1]):
                out.append(f'{pid}:{r[1]}')
    if _best_customer(s) >= 80:
        out.append('refer')
    if all(_tier(s, pid) >= 4 for pid in CAST):
        out.append('all')
    return out


def _reveal_text(s: dict, rid: str) -> tuple[str, str]:
    """(who, words) of the line that announces a hidden row."""
    qn = _qn()
    if rid == 'refer':
        who = _closest_customer(s)
        return who, qn._fill(s, REVEAL['refer'], who=qn.name_of(who))
    if rid == 'all':
        return 'co_lua', REVEAL['all']
    pid, row = rid.split(':', 1)
    if row == 'story':
        return pid, qn._fill(s, REVEAL['story'], who=qn.name_of(pid))
    return pid, qn._fill(s, REVEAL[rid])


def _closest_customer(s: dict) -> str:
    qn = _qn()
    best, who = -1, 'co_lua'
    for c in (s.get('careers') or {}).values():
        for npc, v in ((c or {}).get('relationships') or {}).items() if isinstance(c, dict) else ():
            if type(v) is int and v > best and npc not in qn.ALIAS and qn.home(npc) == npc:
                best, who = v, npc
    return who


def reveal(s: dict) -> list[str]:
    """Newly reached hidden rows: that person tells you (an inbox 'care' row) once. Returns the notes."""
    if off():
        return []
    new = [rid for rid in reached(s) if rid not in ((get(s) or {}).get('told') or [])]
    if not new:
        return []
    b = _block(s)
    qn = _qn()
    st = qn._state(s)
    d = qn.today(s)
    notes = []
    for rid in new:
        who, text = _reveal_text(s, rid)
        qn._push(st, 'care', who, text, d, state='done')
        b['told'] = (b['told'] + [rid])[-LIST_MAX:]
        notes.append(f'✨ {text}')
    return notes


def fresh(s: dict) -> int:
    """Hidden rows told but not looked at yet (the 👥 badge)."""
    b = get(s)
    if not b or off():
        return 0
    return sum(1 for x in b['told'] if x not in b['seen'])


# ---------------------------------------------------------------- 💼 pay
def pay_pct(s: dict, career: str, npc: str, vn: int | None = None) -> int:
    """What finishing a job for `npc` at `career` adds, in percent (the referral not counted)."""
    if off():
        return 0
    qn = _qn()
    pid = qn.home(npc)
    if not pid:
        return 0
    tr = _tier(s, pid)
    pct = PAY_PCT.get(tr, 0)
    if pct and kept(s, pid, vn):
        pct += KEEP_PCT
    if career in FOOD and _has(s, 'ba_sau', 'recipe'):
        pct += RECIPE_PCT
    return min(MAX_PCT, pct)


def _ref_live(b: dict | None, vn: int) -> dict | None:
    r = (b or {}).get('ref')
    return r if isinstance(r, dict) and r['n'] > 0 and vn <= r['u'] else None


def pay_bonus(s: dict, c: dict, t: dict, reward: int) -> int:
    """engine.task_done (a completed job, its pay added): the regular's extra, into the career's fund. Returns xu."""
    if off() or type(reward) is not int or reward <= 0 or not isinstance(t, dict) or t.get('player_order'):
        return 0
    career, npc = t.get('career'), t.get('npc')
    if not isinstance(career, str) or not isinstance(npc, str):
        return 0
    vn = vn_day()
    pct = pay_pct(s, career, npc, vn)
    b = get(s)
    ref = _ref_live(b, vn)
    use_ref = ref is not None and ref['c'] == career
    if use_ref:
        pct = min(MAX_PCT, pct + REF_PCT)
    if pct <= 0:
        return 0
    from . import interest_clock as icl
    if not icl.day_paid(s):
        return 0
    b = _block(s)
    if b is None:
        return 0
    if b['pay'][0] != vn:
        b['pay'] = [vn, 0]
    room = DAY_CAP - b['pay'][1]
    bonus = min(JOB_CAP, room, (reward * pct + 50) // 100)   # rounded: a 6-xu glass of trà đá adds nothing
    if bonus <= 0:
        return 0
    if use_ref:
        b['ref']['n'] -= 1
    from . import engine
    qn = _qn()
    why = f'🤝 Khách sộp do {qn.name_of(ref["by"])} giới thiệu trả thêm' if use_ref and qn.home(ref['by']) else '💛 Khách quen trả thêm'
    engine.money(s, c, bonus, why, t.get('id'), 'revenue')
    b['pay'][1] += bonus
    return bonus


# ---------------------------------------------------------------- 🏠 Bà Tám's rent, 🛒 Cô Ba's prices
def living(j: dict, out: dict) -> dict:
    """journey.living_cost: Bà Tám takes less rent from someone close who lives in her attic."""
    if off() or not isinstance(j, dict) or not j.get('story') or out.get('where') != 'attic':
        return out
    v = (((j.get('life') or {}).get('bonds')) or {}).get('ba_tam')
    if type(v) is not int:
        return out
    pct = RENT_PCT.get(_qn().tier_of(max(0, min(100, v))), 0)
    if not pct or out['rent'] <= 0:
        return out
    cut = min(out['rent'], max(1, out['rent'] * pct // 100))
    return dict(out, total=out['total'] - cut, rent=out['rent'] - cut, perk=cut)


def shop_pct(s: dict) -> int:
    if off():
        return 0
    return SHOP_PCT.get(_tier(s, 'co_ba'), 0)


def gift_price(s: dict, price: int) -> int:
    """A street gift's price (Cô Ba's discount)."""
    pct = shop_pct(s)
    if not pct or price <= 0:
        return price
    return max(1, price - max(1, price * pct // 100))


def hidden_gift(s: dict) -> dict | None:
    return dict(HIDDEN_GIFT) if _has(s, 'co_ba', 'item') else None


# ---------------------------------------------------------------- 🎂 birthdays, 📝 errands
_BD: dict = {}


def birthday(pid: str) -> tuple[int, int]:
    """(day, month): the neighbours' are written, everyone else's drawn once from their id."""
    if pid in BIRTHDAYS:
        return BIRTHDAYS[pid]
    got = _BD.get(pid)
    if got is None:
        d = datetime.date(2001, 1, 1) + datetime.timedelta(days=random.Random('gw-bd|' + pid).randrange(365))
        got = (d.day, d.month)
        if len(_BD) < 5000:
            _BD[pid] = got
    return got


def _date(vn: int) -> datetime.date:
    return datetime.date(1970, 1, 1) + datetime.timedelta(days=vn)


def is_birthday(pid: str, vn: int | None = None) -> bool:
    d = _date(vn_day() if vn is None else vn)
    return birthday(pid) == (d.day, d.month)


def _errand_pick(s: dict, vn: int) -> dict | None:
    qn = _qn()
    people = qn.known(s, 2)
    if not people:
        return None
    rng = random.Random(f'gw-err|{(s.get("journey") or {}).get("seed", 0)}|{vn}')
    cast = [p for p in people if qn.is_cast(p)]
    others = [p for p in people if not qn.is_cast(p)]
    pool = cast if cast and (not others or rng.random() < .6) else others
    who = pool[rng.randrange(len(pool))]
    t = qn.taste(who)
    kid = qn.is_kid(who)
    from .closeness_content import KID_NOT, KID_POOL
    ok = [x for x in ERRANDS if x not in t['dislikes'] and (not kid or (x in KID_POOL and x not in KID_NOT))]
    liked = [x for x in t['likes'] if x in ok]
    pick = liked or ok
    if not pick:
        return None
    return dict(d=vn, who=who, tag=pick[rng.randrange(len(pick))], st='open')


def errand(s: dict, ensure: bool = False) -> dict | None:
    """Today's việc nhờ (stored on the first command of the Vietnam day)."""
    if off():
        return None
    vn = vn_day()
    b = get(s)
    e = (b or {}).get('err')
    if isinstance(e, dict) and e['d'] == vn:
        return e
    if not ensure:
        return None
    e = _errand_pick(s, vn)
    if e is None:
        return None
    b = _block(s)
    if b is None:
        return None
    b['err'] = e
    return e


def errand_view(s: dict) -> dict | None:
    e = errand(s)
    qn = _qn()
    if not e or not qn.home(e['who']):
        return None
    what, why = ERRANDS[e['tag']]
    from .closeness_content import TAGS
    return dict(who=e['who'], who_name=qn.name_of(e['who']), tag=e['tag'], emoji=TAGS[e['tag']][0], what=what,
                text=qn._fill(s, ERRAND_ASK, who=qn.name_of(e['who']), what=what, why=why), done=e['st'] == 'done')


def on_gift(s: dict, pid: str, item: dict, got: int) -> list[str]:
    """After a gift landed (closeness qn_gift): the birthday doubles it, a matching errand is done. Returns lines."""
    if off():
        return []
    qn = _qn()
    out = []
    b = _block(s)
    if b is None:
        return out
    vn = vn_day()
    row = _person(b, pid)
    row[2] = vn
    if got > 0 and is_birthday(pid, vn) and row[3] != vn:
        row[3] = vn
        extra = qn.change(s, pid, got, 'Quà đúng ngày sinh nhật.', 'gift')
        out.append(qn._fill(s, BIRTHDAY_LINE, who=qn.name_of(pid)))
        out.append(qn._note(pid, extra))
    e = errand(s)
    if e and e['st'] == 'open' and e['who'] == pid and e['tag'] in set(item.get('tags') or ()):
        e['st'] = 'done'
        b['errn'][pid] = min(999, b['errn'].get(pid, 0) + 1)
        _trim(b['errn'], lambda k: b['errn'][k])
        g = qn.change(s, pid, ERRAND_GAIN, 'Giúp một việc nhờ.', 'gift')
        out.append(qn._fill(s, ERRAND_DONE, who=qn.name_of(pid)))
        out.append(qn._note(pid, g))
    return [x for x in out if x]


# ---------------------------------------------------------------- 🤝 referrals
def _set_ref(b: dict, career: str, by: str, vn: int) -> None:
    b['ref'] = dict(c=career, n=REF_JOBS, u=vn + REF_DAYS, by=by)


def after_chat(s: dict, pid: str) -> list[str]:
    """A chat with a customer at Như người nhà: once a week they send friends to their place (one referral at a time)."""
    if off() or _cast(pid) or 'refer' not in reached(s) or _tier(s, pid) < 5:
        return []
    qn = _qn()
    b = _block(s)
    vn = vn_day()
    if b is None or _ref_live(b, vn) or vn - b['fav'].get(pid, -FAVOUR_DAYS) < FAVOUR_DAYS:
        return []
    career = qn._npcs()[pid]['career_id']
    if career not in (s.get('careers') or {}):
        return []
    from .content import CAREER_META
    b['fav'][pid] = vn
    _trim(b['fav'], lambda k: b['fav'][k])
    _set_ref(b, career, pid, vn)
    text = qn._fill(s, REFER_LINE, who=qn.name_of(pid), place=CAREER_META.get(career, {}).get('place', 'chỗ bạn làm'))
    qn._push(qn._state(s), 'care', pid, text, qn.today(s), state='done')
    return [f'🤝 {text}']


# ---------------------------------------------------------------- commands
COMMANDS = ('qn_favour', 'qn_gw_seen')


def apply(s: dict, career: str | None, name: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    qn = _qn()
    need(not off(), 'Hôm nay mọi người bận cả rồi, để hôm khác nhé.', 'paused')
    result = dict(message='', effects=[])
    b = _block(s)
    need(b is not None, 'Chưa có hàng xóm nào ở đây.')
    if name == 'qn_gw_seen':
        need(set(p) == set(), 'Dữ liệu thao tác không hợp lệ.')
        b['seen'] = [x for x in b['told']][-LIST_MAX:]
        return result
    need(set(p) == {'who'} and isinstance(p['who'], str) and p['who'] in FAVOURS, 'Không tìm thấy người này.')
    pid = p['who']
    rid, _label = FAVOURS[pid]
    r = _row(pid, rid)
    need(_has(s, pid, rid), f'Thân với {qn.name_of(pid)} hơn chút nữa đã nhé.', 'locked')
    vn = vn_day()
    last = b['fav'].get(pid)
    if last is not None:
        left = FAVOUR_DAYS - (vn - last)
        need(left <= 0, f'Tuần này {qn.name_of(pid)} giúp rồi. {left} ngày nữa ghé lại nhé.', 'already_done')
    line = FAVOUR_LINES[pid]
    life = (s.get('journey') or {}).get('life')
    spirit_ok = _story_mode(s) and isinstance(life, dict) and type(life.get('spirit')) is int

    def lift(n: int) -> int:
        if not spirit_ok:
            return 0
        got = max(0, min(n, 100 - life['spirit']))
        life['spirit'] += got
        return got

    if pid == 'anh_khoa':
        cid, c = qn._fund(s, career)
        need(c is not None and c.get('started'), 'Mở một nơi làm việc trước để anh Khoa có chỗ mà khen nhé.')
        need(_ref_live(b, vn) is None, 'Khách được giới thiệu lần trước còn chưa tới hết. Phục vụ xong rồi nhờ tiếp nhé.', 'already_done')
        _set_ref(b, cid, pid, vn)
        from .content import CAREER_META
        result['effects'].append(f'🤝 {REF_JOBS} khách sộp sẽ ghé {CAREER_META.get(cid, {}).get("place", "chỗ bạn làm")}: mỗi khách trả thêm {REF_PCT}%.')
    elif pid in FAVOUR_ITEMS:
        st = qn._state(s)
        item = random.Random(f'gw-fav|{pid}|{vn}').choice(FAVOUR_ITEMS[pid])
        need(st['bag'].get(item, 0) < qn.BAG_MAX, 'Túi quà đầy món này rồi. Dùng bớt rồi nhận tiếp nhé.')
        qn._bag_add(st, item)
        rec = qn._rec(st, pid, qn.today(s))
        rec['got'] += 1
        qn._log(st, qn.today(s), pid, 0, f'Tặng bạn {qn._lc(qn.RECEIVED[item]["name"])}.', 'got')
        result['effects'].append(f'🎒 {qn.RECEIVED[item]["emoji"]} {qn.RECEIVED[item]["name"]} vào túi quà.')
    elif pid == 'co_lua':
        for other in CAST:
            if other != pid and _tier(s, other) >= 2:
                result['effects'].append(qn._note(other, qn.change(s, other, PARTY_GAIN, 'Gặp nhau ở tiệc tổ dân phố.', 'invite')))
        got = lift(SPIRIT['co_lua'])
        if got:
            result['effects'].append(f'Tinh thần +{got}.')
    elif pid == 'chu_tu':
        n = (s.get('journey') or {}).get('needs')
        if _story_mode(s) and isinstance(n, dict) and type(n.get('wake')) is int:
            got = max(0, min(WAKE, 100 - n['wake']))
            n['wake'] += got
            result['effects'].append(f'Tỉnh táo +{got}.' if got else 'Tỉnh táo đã đầy rồi.')
        else:
            got = lift(SPIRIT['chu_tu'])
            if got:
                result['effects'].append(f'Tinh thần +{got}.')
    else:
        got = lift(SPIRIT.get(pid, 0))
        if got:
            result['effects'].append(f'Tinh thần +{got}.')
    b['fav'][pid] = vn
    _trim(b['fav'], lambda k: b['fav'][k])
    st = qn._state(s)
    qn._rec(st, pid, qn.today(s)).update(seen=qn.today(s), dec=0)
    result.update(message=f'{r[2]} {line}', who=pid)
    result['effects'] = [x for x in result['effects'] if x]
    return result


# ---------------------------------------------------------------- the view
def _ladder(s: dict, pid: str | None, told: set) -> list[dict]:
    out = []
    for r in _rows(pid):
        tier, rid, emoji, name, words, hidden = r
        if pid:
            open_ = _has(s, pid, rid)
            known = not hidden or open_
        else:
            open_ = None      # per person (the client compares the tier)
            known = not hidden or rid in told
        out.append(dict(tier=tier, id=rid, emoji=emoji if known else '🔒', name=name if known else '???',
                        words=words if known else '', hidden=hidden, open=open_))
    return out


def public(s: dict, d: dict) -> None:
    """closeness.public: adds d['gw'] (the perks, today's errand, titles, stories) and each person's p['gw']."""
    if off():
        d['gw'] = dict(on=False)
        return
    b = get(s) or BLOCK_DEFAULT
    vn = vn_day()
    told = set(b['told'])
    qn = _qn()
    ref = _ref_live(b, vn)
    from .content import CAREER_META
    titles = [dict(emoji=TITLES['co_lua'][0], name=TITLES['co_lua'][1])] if _has(s, 'co_lua', 'title') else []
    if 'all' in told and all(_tier(s, p) >= 4 for p in CAST):
        titles.append(dict(emoji=TITLES['all'][0], name=TITLES['all'][1]))
    hg = hidden_gift(s)
    shop = shop_pct(s)
    if shop or hg:
        for g in d.get('gifts') or []:
            if g.get('src') == 'buy':
                g['was'] = g['price']
                g['price'] = gift_price(s, g['price'])
        if hg:
            d['gifts'].insert(0, dict(id=hg['id'], src='buy', name=hg['name'], emoji=hg['emoji'], price=gift_price(s, hg['price']),
                                      was=hg['price'], tags=list(hg['tags']), secret=True))
    for p in d.get('people') or []:
        pid = p['id']
        row = b['p'].get(pid)
        dd, mm = birthday(pid)
        fav = None
        if pid in FAVOURS:
            rid, label = FAVOURS[pid]
            r = _row(pid, rid)
            if _has(s, pid, rid):
                last = b['fav'].get(pid)
                left = 0 if last is None else max(0, FAVOUR_DAYS - (vn - last))
                fav = dict(label=label, left=left, emoji=r[2])
        g = dict(pct=pay_pct(s, p['career'], pid, vn) if p.get('career') else 0,
                 keep=bool(row) and row[2] > 0 and vn - row[2] < KEEP_DAYS,
                 bday=f'{dd:02d}/{mm:02d}' if p['tier'] >= 3 else None,
                 bday_today=p['tier'] >= 3 and is_birthday(pid, vn),
                 errn=b['errn'].get(pid, 0), fav=fav,
                 ladder=_ladder(s, pid, told) if p.get('cast') else None,
                 story=STORIES[pid] if p.get('cast') and _has(s, pid, 'story') else None)
        p['gw'] = {k: v for k, v in g.items() if v}   # compact: a veteran knows a few hundred people
    d['gw'] = dict(on=True, common=_ladder(s, None, told), errand=errand_view(s), titles=titles, fresh=fresh(s),
                   shop_pct=shop, ref=dict(place=CAREER_META.get(ref['c'], {}).get('place', ''), n=ref['n'], pct=REF_PCT, by=qn.name_of(ref['by'])
                                           if qn.home(ref['by']) else '') if ref else None,
                   pay_today=b['pay'][1] if b['pay'][0] == vn else 0, day_cap=DAY_CAP, max_pct=MAX_PCT,
                   rent_pct=RENT_PCT.get(_tier(s, 'ba_tam'), 0), story_need=ERRANDS_FOR_STORY,
                   bdays=[p['name'] for p in d.get('people') or [] if p['gw'].get('bday_today')][:5])


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    b = get(s)
    j = s.get('journey') if isinstance(s, dict) else None
    if b is None:
        if isinstance(j, dict) and KEY in j:
            from . import engine as e
            e.need(False, 'Dữ liệu thân thiết không hợp lệ.', 'invalid_save')
        return
    from . import engine as e
    need, integer = e.need, e.integer
    qn = _qn()
    bad = 'Dữ liệu thân thiết không hợp lệ.'
    need(set(b) == KEYS and b['v'] == VERSION, bad, 'invalid_save')
    need(isinstance(b['p'], dict) and len(b['p']) <= PEOPLE_MAX, bad, 'invalid_save')
    for pid, row in b['p'].items():
        need(qn.home(pid) == pid and isinstance(row, list) and len(row) == 4, bad, 'invalid_save')
        integer(row[0], 0, 10**7)
        integer(row[1], 0, VN_GAIN_CAP)
        integer(row[2], 0, 10**7)
        integer(row[3], 0, 10**7)
    need(isinstance(b['fav'], dict) and len(b['fav']) <= PEOPLE_MAX and all(qn.home(k) == k for k in b['fav']), bad, 'invalid_save')
    for v in b['fav'].values():
        integer(v, 0, 10**7)
    if b['ref'] is not None:
        r = b['ref']
        need(isinstance(r, dict) and set(r) == REF_KEYS and r['c'] in (s.get('careers') or {}) and qn.home(r['by']) == r['by'],
             bad, 'invalid_save')
        integer(r['n'], 0, REF_JOBS)
        integer(r['u'], 0, 10**7)
    need(isinstance(b['pay'], list) and len(b['pay']) == 2, bad, 'invalid_save')
    integer(b['pay'][0], 0, 10**7)
    integer(b['pay'][1], 0, DAY_CAP)
    if b['err'] is not None:
        r = b['err']
        need(isinstance(r, dict) and set(r) == ERR_KEYS and qn.home(r['who']) == r['who'] and r['tag'] in ERRANDS
             and r['st'] in ('open', 'done'), bad, 'invalid_save')
        integer(r['d'], 0, 10**7)
    need(isinstance(b['errn'], dict) and len(b['errn']) <= PEOPLE_MAX and all(qn.home(k) == k for k in b['errn']), bad, 'invalid_save')
    for v in b['errn'].values():
        integer(v, 0, 999)
    for k in ('told', 'seen'):
        need(isinstance(b[k], list) and len(b[k]) <= LIST_MAX and all(isinstance(x, str) and 0 < len(x) <= 40 for x in b[k]),
             bad, 'invalid_save')
