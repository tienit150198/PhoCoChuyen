"""🛕 Đi chùa: a calm outing to chùa Gió Lành, open to everyone in the story (not only the pagoda's monk).

Owner: "mn đi chùa được nhé". Small and free on purpose: a few quiet acts at the pagoda by the river landing,
each once per life day, at most DAILY of them a day. They lift tinh thần a little (journey.life.spirit), sitting
still wakes you up a little, and on the full moon and the first of the lunar month the pagoda's vegetarian lunch
fills you up. Never xu, never a cost, nothing that can go wrong.

* The lunar day is read off the life day (LUNAR_OFFSET: life day 1 is the 11th, so the first full moon comes on
  life day 5). Rằm (15) and mùng 1 (1) are the days of the free vegetarian meal.
* A wish (the `nguyen` act) is one of WISHES, a short line written on a slip of red paper and tied by the gate.

State (absent in older saves; created on the first visit, validate() checks it strictly when present):
  journey['chua'] = {v, day (the life day of `did`), did (acts done that day), n (acts done in all)}.
Command (through journey.action): jr_chua_do {act, wish?}. Story mode only (code 'locked' otherwise); the same act
twice a day is refused with 'already_done', a fourth act with 'limit'. An older build answers jr_chua_do with
'unknown_action' and ignores journey['chua'] (journey.validate allows extra keys).
"""
from __future__ import annotations

from . import needs as nd

VERSION = 1
DAILY = 3                 # acts per life day
LUNAR_OFFSET = 10         # life day 1 = the 11th of the lunar month
KEYS = {'v', 'day', 'did', 'n'}

# id → what it is: spirit (tinh thần), wake (tỉnh táo), full (no bụng) added; feast: only on rằm / mùng 1.
ACTS = {
    'huong': dict(emoji='🪔', name='Thắp một nén hương', spirit=2, wake=0, full=0, feast=False,
                  text='Bạn thắp một nén hương ở lư lớn ngoài sân, đứng lặng một lúc. Khói hương bay chầm chậm qua hàng cau.'),
    'chuong': dict(emoji='🔔', name='Nghe chuông chùa', spirit=2, wake=0, full=0, feast=False,
                   text='Tiếng chuông đồng trầm trầm ngân ra tới bến sông. Bạn đứng nghe tới khi tiếng ngân tắt hẳn.'),
    'ngoi': dict(emoji='🍃', name='Ngồi yên ở hiên chùa', spirit=2, wake=6, full=0, feast=False,
                 text='Bạn ngồi ở hiên, nhìn mấy con cá đỏ dưới hồ sen. Gió sông mát, đầu óc nhẹ hẳn.'),
    'nguyen': dict(emoji='📜', name='Viết một lời nguyện', spirit=3, wake=0, full=0, feast=False,
                   text='Bạn viết lên mảnh giấy đỏ, buộc vào hàng rào cạnh cổng tam quan.'),
    'quet': dict(emoji='🧹', name='Phụ quét sân chùa', spirit=3, wake=0, full=0, feast=False,
                 text='Bạn mượn cây chổi tre, phụ quét lá bàng ngoài sân. Quét xong, sân sạch, lòng cũng nhẹ.'),
    'com': dict(emoji='🍚', name='Ăn cơm chay cùng mọi người', spirit=2, wake=0, full=30, feast=True,
                text='Bà Nhạn múc cho bạn bát canh nấm nóng. Cả bàn ăn chậm, nói nhỏ, ai cũng no.'),
}
WISHES = {
    'nha': 'Cho cả nhà mạnh khỏe.',
    'viec': 'Cho công việc suôn sẻ.',
    'ban': 'Cho người bạn đang ốm mau khỏe.',
    'pho': 'Cho khu phố bình an.',
}


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _story(s: dict) -> bool:
    j = s.get('journey')
    return isinstance(j, dict) and bool(j.get('story'))


def lunar(life_day: int) -> int:
    """The lunar day (1..30) of a life day."""
    return (max(1, int(life_day)) - 1 + LUNAR_OFFSET) % 30 + 1


def feast_day(life_day: int) -> bool:
    return lunar(life_day) in (1, 15)


def lunar_label(life_day: int) -> str:
    d = lunar(life_day)
    return 'Rằm' if d == 15 else 'Mùng 1' if d == 1 else f'Mùng {d}' if d <= 10 else f'Ngày {d} âm lịch'


def _today(s: dict) -> list:
    """The acts done today ([] when the record is absent or belongs to an earlier day)."""
    c = s['journey'].get('chua')
    return list(c['did']) if isinstance(c, dict) and c.get('day') == s['journey']['life_day'] else []


def why_not(s: dict, act: str) -> str:
    """Why this act cannot be done now ('' = it can)."""
    j = s['journey']
    did = _today(s)
    if act in did:
        return 'Hôm nay làm rồi'
    if len(did) >= DAILY:
        return 'Hôm nay ở chùa đủ rồi'
    if ACTS[act]['feast'] and not feast_day(j['life_day']):
        return 'Chỉ rằm và mùng 1'
    if ACTS[act]['full']:
        n = nd.get(s)
        if n and n['day'] == j['life_day'] and n['full'] >= nd.FULL_CAP:
            return 'Bụng no rồi'
    return ''


# ---------------------------------------------------------------- command
COMMANDS = ('jr_chua_do',)


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    need(_story(s), 'Đi chùa chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'act', 'wish'} and p.get('act') in ACTS, 'Chọn một việc ở chùa nhé.')
    act = p['act']
    x = ACTS[act]
    wish = p.get('wish')
    if act == 'nguyen':
        need(wish in WISHES, 'Chọn một lời nguyện nhé.')
    else:
        need(wish is None, 'Chọn một việc ở chùa nhé.')
    why = why_not(s, act)
    need(why != 'Hôm nay làm rồi', 'Hôm nay bạn làm việc này rồi. Mai lại ghé nhé.', 'already_done')
    need(why != 'Hôm nay ở chùa đủ rồi', f'Hôm nay ghé chùa đủ {DAILY} việc rồi. Mai lại ghé nhé.', 'limit')
    need(why != 'Chỉ rằm và mùng 1', 'Chùa nấu cơm chay mời mọi người vào rằm và mùng 1.', 'not_now')
    need(not why, 'Bụng no rồi, để bữa sau nhé.', 'too_full')
    j = s['journey']
    c = j.get('chua')
    if not isinstance(c, dict) or c.get('day') != j['life_day']:
        c = j['chua'] = dict(v=VERSION, day=j['life_day'], did=[], n=int(c['n']) if isinstance(c, dict) else 0)
    c['did'].append(act)
    c['n'] = min(10**6, c['n'] + 1)
    got = nd._spirit(s, x['spirit'])
    parts = []
    if x['wake'] or x['full']:
        n = nd.ensure(s)
        if x['wake']:
            n['wake'] = nd._clamp(n['wake'] + x['wake'])
            parts.append(f'tỉnh táo {n["wake"]}')
        if x['full']:
            n['full'] = nd._clamp(n['full'] + x['full'])
            parts.append(f'no bụng {n["full"]}')
    if got:
        parts.insert(0, f'tinh thần +{got}')
    text = f'{x["text"]} “{WISHES[wish]}”' if act == 'nguyen' else x['text']
    tail = f' ({", ".join(parts)})' if parts else ''
    return dict(message=f'{x["emoji"]} {text}{tail}', effects=[])


# ---------------------------------------------------------------- view
def public(s: dict) -> dict:
    if not _story(s):
        return dict(enabled=False)
    j = s['journey']
    did = _today(s)
    day = j['life_day']
    acts = []
    for k, x in ACTS.items():
        why = why_not(s, k)
        acts.append(dict(id=k, emoji=x['emoji'], name=x['name'], spirit=x['spirit'], wake=x['wake'], full=x['full'],
                         feast=x['feast'], done=k in did, ok=not why, why=why))
    return dict(enabled=True, lunar=lunar(day), label=lunar_label(day), feast=feast_day(day), daily=DAILY,
                left=max(0, DAILY - len(did)), acts=acts, wishes=[dict(id=k, text=v) for k, v in WISHES.items()])


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'chua' not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu đi chùa không hợp lệ.'
    c = j['chua']
    need(isinstance(c, dict) and set(c) == KEYS and c.get('v') == VERSION, bad, 'invalid_save')
    integer(c['day'], 1, 10**6)
    need(c['day'] <= j['life_day'], bad, 'invalid_save')
    did = c['did']
    need(isinstance(did, list) and len(did) <= DAILY and len(did) == len(set(did)) and set(did) <= set(ACTS), bad, 'invalid_save')
    integer(c['n'], 0, 10**6)
    need(c['n'] >= len(did), bad, 'invalid_save')
