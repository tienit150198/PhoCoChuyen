"""Free, repeatable visits to chùa Gió Lành.

Spirit gains stop naturally at 100; visiting, praying and hanging cards remain
available. Only the feast calendar and fullness restrict the vegetarian meal.
The v1 record keeps unique acts for today's history and a saturated lifetime
counter. Optional private cards retain the latest 40; older cards go to the
journey archive in the same Store transaction. Cards survive life-day rollover.
Older clients can still submit preset wishes and draw the original acts list.
"""
from __future__ import annotations

import re
import secrets

from . import needs as nd
from . import archive as ar

VERSION = 1
CARDS_KEPT = 40
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
    # only in the walkable pagoda (SCENE_ACTS): the prayer is put together by the player, the chant is kept by them
    'khan': dict(emoji='🙏', name='Quỳ khấn trước điện Phật', spirit=3, wake=0, full=0, feast=False,
                 text='Bạn quỳ trên chiếu, chắp tay khấn nhỏ.'),
    'tung': dict(emoji='📿', name='Tụng kinh cùng thầy', spirit=4, wake=0, full=0, feast=False, text=''),
}
SCENE_ACTS = ('khan', 'tung')
BEATS = 12                # mõ beats in one chant
WISHES = {
    'nha': 'Cho cả nhà mạnh khỏe.',
    'viec': 'Cho công việc suôn sẻ.',
    'ban': 'Cho người bạn đang ốm mau khỏe.',
    'pho': 'Cho khu phố bình an.',
}
# A hope for luck is a prayer, not a gameplay guarantee or money reward.
KHAN_WHAT = {
    'khoe': 'được mạnh khỏe',
    'binh_an': 'được bình an',
    'thanh_than': 'được thanh thản trong lòng',
    'thuong': 'luôn thương nhau',
    'sieng': 'siêng năng, làm việc tử tế',
    'kien_nhan': 'biết kiên nhẫn hơn mỗi ngày',
    'yen_nghi': 'được yên nghỉ',
    'may_man': 'gặp nhiều may mắn',
}
KHAN_WHO = {   # id → (words, what may go with it)
    'cha_me': ('cha mẹ', ('khoe', 'binh_an', 'thanh_than', 'may_man')),
    'ca_nha': ('cả nhà', ('khoe', 'binh_an', 'thuong', 'may_man')),
    'ong_ba': ('ông bà đã khuất', ('yen_nghi',)),
    'ban': ('người bạn đang ốm', ('khoe', 'thanh_than', 'may_man')),
    'pho': ('bà con khu phố', ('binh_an', 'thuong', 'may_man')),
    'minh': ('bản thân con', ('thanh_than', 'sieng', 'kien_nhan', 'may_man')),
}
# Thầy Huệ Minh, a few words for the day (two lines picked by the lunar day; rằm and mùng 1 have their own).
ABBOT = (
    'Đi chậm thôi con. Chùa không có gì phải vội.',
    'Thắp một nén hương là đủ. Lòng thành không nằm ở số nén.',
    'Hôm nay con mệt thì ngồi nghỉ ở hiên. Nghỉ cũng là tu.',
    'Nói lời hiền với người nhà trước, rồi hẵng khấn cho người xa.',
    'Ăn cơm thì biết mình đang ăn cơm. Quét sân thì biết mình đang quét sân.',
    'Giận ai thì thở ba hơi thật chậm rồi hẵng nói.',
    'Cầu cho người khác bình an, lòng mình cũng an theo.',
    'Chùa không bán may mắn. Việc lành con làm mới theo con về nhà.',
    'Mỗi sáng thức dậy, mỉm cười một cái trước khi cầm điện thoại.',
)
ABBOT_RAM = 'Rằm rồi, tối nay chùa có khóa lễ. Con ở lại ăn bát cơm chay với mọi người nhé.'
ABBOT_MUNG1 = 'Mùng một đầu tháng, mình bắt đầu lại cho nhẹ nhàng. Việc cũ chưa xong thì làm tiếp, đừng tự trách.'


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
    if ACTS[act]['feast'] and not feast_day(j['life_day']):
        return 'Chỉ rằm và mùng 1'
    if ACTS[act]['full']:
        n = nd.get(s)
        if n and n['day'] == j['life_day'] and n['full'] >= nd.FULL_CAP:
            return 'Bụng no rồi'
    return ''


def chant_text(beat: int) -> str:
    """How the chant went: the more beats kept, the warmer; never a scolding."""
    if beat >= BEATS - 2:
        return 'Tiếng mõ của bạn đều, hòa vào giọng tụng trầm của thầy. Tụng xong, cả chánh điện lặng yên.'
    if beat >= BEATS // 2:
        return 'Có lúc bạn gõ lệch nhịp, thầy vẫn tụng chậm rãi chờ bạn bắt kịp. Tụng xong, lòng nhẹ hẳn.'
    return 'Bạn gõ mõ chưa quen tay. Thầy cười hiền: “Lần sau mình tụng chậm hơn chút.”'


def abbot_lines(life_day: int) -> list:
    """Thầy Huệ Minh's words for the day: the rằm / mùng 1 line first on those days, then two from ABBOT."""
    d = lunar(life_day)
    i = (life_day * 7) % len(ABBOT)
    out = [ABBOT[i], ABBOT[(i + 4) % len(ABBOT)]]
    if d == 15:
        out.insert(0, ABBOT_RAM)
    elif d == 1:
        out.insert(0, ABBOT_MUNG1)
    return out


# Legacy wishes retain their exact wording when represented as cards.
WISH_CARD = {'nha': ('ca_nha', 'khoe'), 'viec': ('minh', 'sieng'),
             'ban': ('ban', 'khoe'), 'pho': ('pho', 'binh_an')}
CARD_KEYS = {'id', 'day', 'recipient', 'blessing', 'name', 'message', 'text', 'wish'}


def _plain(value, limit: int) -> str:
    e = _core()
    e.need(isinstance(value, str) and len(value) <= limit, 'Lời nguyện quá dài hoặc không hợp lệ.')
    text = ' '.join(e.clean_text(value, max_length=limit, minimum=0).split())
    e.need('<' not in text and '>' not in text, 'Lời nguyện chỉ dùng văn bản thuần.')
    return text


def _card_text(recipient: str, blessing: str, name: str, message: str, wish: str = '') -> str:
    if wish:
        return WISHES[wish]
    who = name or KHAN_WHO[recipient][0]
    return f'Con cầu mong {who} {KHAN_WHAT[blessing]}.' + (f' {message}' if message else '')


def _new_card(p: dict, day: int) -> dict:
    e = _core()
    e.need(type(p.get('public', False)) is bool, 'Quyền xem bảng lời chúc không hợp lệ.')
    if p.get('wish') is not None:
        wish = p['wish']
        e.need(isinstance(wish, str) and wish in WISHES, 'Chọn một lời nguyện nhé.')
        e.need(set(p) <= {'act', 'wish', 'public'}, 'Chọn một việc ở chùa nhé.')
        recipient, blessing = WISH_CARD[wish]
        name = message = ''
    else:
        e.need(set(p) <= {'act', 'recipient', 'blessing', 'name', 'message', 'public'}, 'Chọn một việc ở chùa nhé.')
        recipient, blessing = p.get('recipient'), p.get('blessing')
        e.need(isinstance(recipient, str) and recipient in KHAN_WHO, 'Bạn khấn cho ai?')
        e.need(isinstance(blessing, str) and blessing in KHAN_WHO[recipient][1], 'Bạn mong điều gì?')
        name, message = _plain(p.get('name', ''), 40), _plain(p.get('message', ''), 140)
        wish = ''
    return dict(id=secrets.token_hex(16), day=day, recipient=recipient, blessing=blessing,
                name=name, message=message, wish=wish,
                text=_card_text(recipient, blessing, name, message, wish))


# ---------------------------------------------------------------- command
COMMANDS = ('jr_chua_do',)


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    need(_story(s), 'Đi chùa chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'act', 'wish', 'who', 'what', 'beat', 'recipient', 'blessing', 'name', 'message', 'public'}
         and isinstance(p.get('act'), str) and p['act'] in ACTS,
         'Chọn một việc ở chùa nhé.')
    act = p['act']
    x = ACTS[act]
    who, what, beat = p.get('who'), p.get('what'), p.get('beat')
    extra = {k for k in ('wish', 'who', 'what', 'beat', 'recipient', 'blessing', 'name', 'message', 'public') if k in p}
    card = None
    if act == 'nguyen':
        card = _new_card(p, s['journey']['life_day'])
    elif act == 'khan':
        need(isinstance(who, str) and who in KHAN_WHO, 'Bạn khấn cho ai?')
        need(isinstance(what, str) and what in KHAN_WHO[who][1], 'Bạn mong điều gì?')
        need(extra == {'who', 'what'}, 'Chọn một việc ở chùa nhé.')
    elif act == 'tung':
        need(type(beat) is int and 0 <= beat <= BEATS and extra == {'beat'}, 'Buổi tụng kinh không hợp lệ.')
    else:
        need(not extra, 'Chọn một việc ở chùa nhé.')
    why = why_not(s, act)
    need(why != 'Chỉ rằm và mùng 1', 'Chùa nấu cơm chay mời mọi người vào rằm và mùng 1.', 'not_now')
    need(not why, 'Bụng no rồi, để bữa sau nhé.', 'too_full')
    j = s['journey']
    c = j.get('chua')
    if not isinstance(c, dict):
        c = j['chua'] = dict(v=VERSION, day=j['life_day'], did=[], n=0)
    elif c['day'] != j['life_day']:
        c.update(day=j['life_day'], did=[])
    if act not in c['did']:
        c['did'].append(act)
    if card is not None:
        c['cards'] = ar.last(c.get('cards', []) + [card], CARDS_KEPT, 'chua.cards', ar.JOURNEY)
    c['n'] = min(10**6, c['n'] + 1)
    got = nd._spirit(s, 1 + 3 * beat // BEATS if act == 'tung' else x['spirit'])
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
    if act == 'nguyen':
        text = f'{x["text"]} “{card["text"]}”'
    elif act == 'khan':
        text = f'{x["text"]} “Con cầu mong {KHAN_WHO[who][0]} {KHAN_WHAT[what]}.”'
    elif act == 'tung':
        text = chant_text(beat)
    else:
        text = x['text']
    tail = f' ({", ".join(parts)})' if parts else ''
    result = dict(message=f'{x["emoji"]} {text}{tail}', effects=[])
    if card is not None:
        result['chua_card'] = dict(id=card['id'], public=p.get('public', False))
    return result


# ---------------------------------------------------------------- view
def public(s: dict) -> dict:
    if not _story(s):
        return dict(enabled=False)
    j = s['journey']
    did = _today(s)
    day = j['life_day']
    spirit = (j.get('life') or {}).get('spirit', 0)
    acts, more = [], []
    for k, x in ACTS.items():
        why = why_not(s, k)
        (more if k in SCENE_ACTS else acts).append(
            dict(id=k, emoji=x['emoji'], name=x['name'], spirit=min(x['spirit'], max(0, 100 - spirit)), wake=x['wake'], full=x['full'],
                 feast=x['feast'], done=k in did, ok=not why, why=why))
    return dict(enabled=True, unlimited=True, sharing=True, spirit=spirit,
                lunar=lunar(day), label=lunar_label(day), feast=feast_day(day),
                cards=[dict(row) for row in (j.get('chua') or {}).get('cards', [])],
                card_choices=dict(recipients=[dict(id=k, text=v[0], blessings=list(v[1])) for k, v in KHAN_WHO.items()],
                                  blessings=[dict(id=k, text=v) for k, v in KHAN_WHAT.items()]),
                acts=acts, wishes=[dict(id=k, text=v) for k, v in WISHES.items()],
                more=more, chant=dict(beats=BEATS), abbot=abbot_lines(day),
                khan=dict(who=[dict(id=k, text=v[0], what=list(v[1])) for k, v in KHAN_WHO.items()],
                          what=[dict(id=k, text=v) for k, v in KHAN_WHAT.items()]))


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'chua' not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu đi chùa không hợp lệ.'
    c = j['chua']
    need(isinstance(c, dict) and KEYS <= set(c) <= KEYS | {'cards'}
         and type(c.get('v')) is int and c['v'] == VERSION, bad, 'invalid_save')
    integer(c['day'], 1, 10**6)
    need(c['day'] <= j['life_day'], bad, 'invalid_save')
    did = c['did']
    need(isinstance(did, list) and len(did) <= len(ACTS) and all(isinstance(a, str) for a in did)
         and len(did) == len(set(did)) and set(did) <= set(ACTS), bad, 'invalid_save')
    integer(c['n'], 0, 10**6)
    need(c['n'] >= len(did), bad, 'invalid_save')
    if 'cards' not in c:
        return
    cards = c['cards']
    need(isinstance(cards, list) and len(cards) <= CARDS_KEPT, bad, 'invalid_save')
    seen, previous_day = set(), 0
    for row in cards:
        need(isinstance(row, dict) and set(row) == CARD_KEYS, bad, 'invalid_save')
        need(isinstance(row['id'], str) and re.fullmatch(r'[0-9a-f]{32}', row['id'])
             and row['id'] not in seen, bad, 'invalid_save')
        seen.add(row['id'])
        need(type(row['day']) is int and 1 <= row['day'] <= c['day']
             and row['day'] >= previous_day, bad, 'invalid_save')
        previous_day = row['day']
        recipient, blessing, wish = row['recipient'], row['blessing'], row['wish']
        need(isinstance(recipient, str) and recipient in KHAN_WHO, bad, 'invalid_save')
        need(isinstance(blessing, str) and blessing in KHAN_WHO[recipient][1], bad, 'invalid_save')
        need(isinstance(wish, str) and (not wish or wish in WISHES), bad, 'invalid_save')
        need(not wish or (recipient, blessing) == WISH_CARD[wish], bad, 'invalid_save')
        for key, limit in (('name', 40), ('message', 140)):
            try:
                clean = _plain(row[key], limit)
            except e.GameError:
                need(False, bad, 'invalid_save')
            need(clean == row[key], bad, 'invalid_save')
        need(not wish or not (row['name'] or row['message']), bad, 'invalid_save')
        need(row['text'] == _card_text(recipient, blessing, row['name'], row['message'], wish), bad, 'invalid_save')
