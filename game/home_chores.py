"""🧹 Việc nhà hôm nay: small things to do at home, each once a life day, with a small visible reward (story mode).

Owner 23/10: "hiện tại nhà ở với đảo chưa ổn lắm, tăng tương tác hơn". The home had decor, repairs, the pool and the
bath (game/relax.py), the baby (game/cradle.py), the household (game/household.py) and the pets (game/pets.py); this is
the everyday layer the overview (public/js/v4/home-overview.js) puts in one card:

* 🧹 Dọn dẹp nhà cửa: anywhere you live.
* 🌿 Tưới cây, chăm vườn: a garden, a balcony, a terrace or a plant placed somewhere (deco tag 'plant').
* 🍳 Nấu một bữa cơm nhà: a kitchen in the place.
* 🐾 Chơi với thú cưng: a pet (game/pets.py) or the household's cat or dog.
* 💞 Quây quần cả nhà: a spouse (married) or a child at home (game/household.py, game/cradle.py's baby).

Rewards, all capped and small next to a day's pay: the first SPIRIT_MAX chores of a day add 1 tinh thần each; the
BONUS_AT-th chore of a day pays BONUS_XU xu "nhà gọn gàng" and moves the streak (consecutive life days with that
bonus); every STREAK_EVERY-th day of a streak adds STREAK_XU xu. At most BONUS_XU + STREAK_XU xu a life day.

State journey['chores'] (absent until the first chore; an older build ignores it): {v, day (life day of `did`), did
[chores done that day], paid (0|1: the day's bonus paid), streak, last (life day of the last bonus, 0: never), n}.
Command: jr_chore_do {act}. Deterministic: the line is seeded by the journey seed, the life day and the chore.
"""
from __future__ import annotations

import random
import re

from . import price_index as pi

VERSION = 1
KEYS = frozenset({'v', 'day', 'did', 'paid', 'streak', 'last', 'n'})
COMMANDS = ('jr_chore_do',)
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
SPIRIT_MAX = 2                       # chores a day that add tinh thần
BONUS_AT = 3                         # the chore of the day that pays "nhà gọn gàng"
BONUS_XU = pi.price(5, luxury=False)
STREAK_EVERY = 7
STREAK_XU = pi.price(15, luxury=False)
KIND, LABEL = 'life', '🧹 Việc nhà gọn gàng'
GREEN_TYPES = ('yard', 'balcony', 'terrace', 'pavilion', 'pool', 'infinity')
KITCHEN_TYPES = ('kitchen',)

ACTS = {
    'don_nha': dict(emoji='🧹', name='Dọn dẹp nhà cửa', need=None,
                    lines=('Bạn quét nhà, lau bàn, gấp gọn chăn gối. Nhà thơm mùi nắng.',
                           'Bạn mở hết cửa sổ, hút bụi một vòng. Góc nào cũng sáng sủa hẳn.',
                           'Bạn dọn lại kệ sách, lau bụi khung ảnh. Nhìn đâu cũng thấy dễ chịu.')),
    'tuoi_cay': dict(emoji='🌿', name='Tưới cây, chăm vườn', need='green',
                     lines=('Bạn tưới từng chậu cây, ngắt mấy lá úa. Lá xanh mướt, đọng nước long lanh.',
                            'Bạn xới đất, bón chút phân, cây nào cũng như vươn mình đón nắng.',
                            'Vòi nước phun mưa nhỏ, cầu vồng mini hiện ra giữa vườn. Bạn bật cười.')),
    'nau_com': dict(emoji='🍳', name='Nấu một bữa cơm nhà', need='kitchen',
                    lines=('Nồi canh chua sôi lăn tăn, đĩa cá kho thơm lừng. Bữa cơm nhà đơn giản mà ngon.',
                           'Bạn chiên mấy quả trứng, xào đĩa rau muống tỏi. Ăn xong thấy ấm bụng.',
                           'Bạn thử món mới học trên mạng. Hơi mặn chút, nhưng vẫn vui.')),
    'choi_pet': dict(emoji='🐾', name='Chơi với thú cưng', need='pet',
                     lines=('{pet} quấn quýt bên chân, bạn ném bóng, bé chạy theo vẫy đuôi rối rít.',
                            'Bạn chải lông cho {pet}, bé lim dim nằm ườn ra sàn.',
                            '{pet} lăn tròn đòi gãi bụng. Cả nhà cười nghiêng ngả.')),
    'ca_nha': dict(emoji='💞', name='Quây quần cả nhà', need='family',
                   lines=('Cả nhà ngồi xem phim, chia nhau đĩa trái cây. Chuyện nhỏ cũng thành vui.',
                          'Tối nay cả nhà ngồi kể chuyện trong ngày, tiếng cười rộn cả phòng.',
                          'Bạn pha ấm trà, cả nhà ngồi ngắm phố lên đèn. Bình yên ghê.')),
}
WHY = {'green': 'Cần vườn, ban công hoặc một chậu cây', 'kitchen': 'Chỗ ở này chưa có bếp', 'pet': 'Chưa có thú cưng',
       'family': 'Chưa có gia đình ở cùng'}


def _core():
    from . import engine
    return engine


def get(s: dict) -> dict | None:
    b = s['journey'].get('chores')
    return b if isinstance(b, dict) else None


def _today(s: dict) -> list:
    b = get(s)
    return list(b['did']) if b and b.get('day') == s['journey']['life_day'] else []


def _pet_name(s: dict) -> str | None:
    j = s['journey']
    pets = j.get('pets') if isinstance(j.get('pets'), dict) else {}
    for p in pets.get('list') or ():
        if isinstance(p, dict) and isinstance(p.get('n'), str) and p['n']:
            return p['n']
    hh = j.get('household') if isinstance(j.get('household'), dict) else {}
    m = hh.get('pet')
    return m['name'] if isinstance(m, dict) and isinstance(m.get('name'), str) and m['name'] else None


def _family(s: dict) -> bool:
    from . import housing as hs
    if hs._spouse(s):
        return True
    hh = s['journey'].get('household') if isinstance(s['journey'].get('household'), dict) else {}
    return isinstance(hh.get('child'), dict)


def has(s: dict, rooms: list, kinds: list) -> dict:
    """What the place offers: rooms [room dicts with 'type'], kinds [deco item kinds placed]."""
    from . import deco_content as DC
    types = {r.get('type') for r in rooms if isinstance(r, dict)}
    plant = any('plant' in (DC.ITEMS.get(k) or {}).get('tags', ()) for k in kinds)
    return dict(green=bool(types & set(GREEN_TYPES)) or plant, kitchen=bool(types & set(KITCHEN_TYPES)),
                pet=_pet_name(s) is not None, family=_family(s))


def _place(s: dict) -> dict:
    from . import deco
    L = deco.layout(s)
    return has(s, L['rooms'], [L['kinds'][u] for u in L['pos'] if u in L['kinds']])


def _from_public(s: dict, dpub: dict | None) -> dict:
    """has() from deco.public (journey.public: no second layout)."""
    from . import deco_content as DC
    if not isinstance(dpub, dict):
        return has(s, [], [])
    rooms = list(dpub.get('rooms') or [])
    for m in dpub.get('more') or ():
        kit = DC.KITS.get(m.get('t')) if isinstance(m, dict) else None
        if kit:
            rooms.append(kit)
    return has(s, rooms, [it.get('k') for it in dpub.get('items') or () if isinstance(it, dict)])


def why_not(s: dict, act: str, there: dict) -> str:
    x = ACTS[act]
    if act in _today(s):
        return 'Hôm nay làm rồi'
    if x['need'] and not there[x['need']]:
        return WHY[x['need']]
    return ''


def public(s: dict, dpub: dict | None) -> dict | None:
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    there = _from_public(s, dpub)
    did = _today(s)
    b = get(s)
    streak = b['streak'] if b and b['last'] >= j['life_day'] - 1 else 0
    # Small (it rides on every state): what was done today, what this place lacks (a WHY code; the texts, the names and the
    # rules are in the catalogue: journey.content()['homelife']['chores']), the bonus once paid and a running streak.
    no = {k: x['need'] for k, x in ACTS.items() if x['need'] and not there[x['need']]}
    paid = bool(b and b['day'] == j['life_day'] and b['paid'])
    return dict(done=[k for k in ACTS if k in did], **({'no': no} if no else {}), **({'paid': True} if paid else {}),
                **({'streak': streak} if streak else {}))


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s.get('journey')
    need(isinstance(j, dict) and bool(j.get('story')), 'Việc nhà chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'act'} and p.get('act') in ACTS, 'Chọn một việc nhé.')
    act = p['act']
    x = ACTS[act]
    why = why_not(s, act, _place(s))
    need(why != 'Hôm nay làm rồi', f'Hôm nay bạn đã {x["name"].lower()} rồi. Mai nhé!', 'already_done')
    need(not why, f'{why}.', 'not_here')
    day = j['life_day']
    b = get(s)
    if b is None:
        b = j['chores'] = dict(v=VERSION, day=day, did=[], paid=0, streak=0, last=0, n=0)
    if b['day'] != day:
        b['day'], b['did'], b['paid'] = day, [], 0
    b['did'].append(act)
    b['n'] = min(10**6, b['n'] + 1)
    from . import needs as nd
    got = nd._spirit(s, 1) if len(b['did']) <= SPIRIT_MAX else 0
    effects = [f'😊 Tinh thần +{got}'] if got else []
    xu = 0
    if len(b['did']) >= BONUS_AT and not b['paid']:
        b['paid'] = 1
        b['streak'] = b['streak'] + 1 if b['last'] == day - 1 else 1
        b['last'] = day
        xu = BONUS_XU + (STREAK_XU if b['streak'] % STREAK_EVERY == 0 else 0)
        from . import journey as jr
        jr._wallet(j, xu, KIND, LABEL)
        effects.append(f'🏠 Nhà gọn gàng +{xu} xu' + (f' · 🔥 {b["streak"]} ngày liền' if b['streak'] > 1 else ''))
    line = random.Random(f'chore|{j.get("seed", 0)}|{day}|{act}').choice(x['lines']).format(pet=_pet_name(s) or 'Bé cưng')
    return dict(message=f'{x["emoji"]} {line}', effects=effects, chore=dict(act=act, xu=xu, spirit=got))


# ---------------------------------------------------------------- saves
def _ok(b, life_day: int) -> bool:
    return (isinstance(b, dict) and set(b) == KEYS and b['v'] == VERSION
            and all(type(b[k]) is int for k in ('day', 'paid', 'streak', 'last', 'n'))
            and 1 <= b['day'] <= life_day and b['paid'] in (0, 1) and 0 <= b['last'] <= b['day']
            and 0 <= b['streak'] <= 10**6 and 0 <= b['n'] <= 10**6
            and isinstance(b['did'], list) and len(b['did']) <= 16 and len(set(b['did'])) == len(b['did'])
            and all(isinstance(a, str) and ID_RE.fullmatch(a) for a in b['did']))


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'chores' not in j:
        return
    _core().need(_ok(j['chores'], j.get('life_day', 1)), 'Dữ liệu việc nhà không hợp lệ.', 'invalid_save')


def upgrade(j: dict) -> None:
    if isinstance(j, dict) and 'chores' in j and not _ok(j['chores'], j.get('life_day', 1) if type(j.get('life_day')) is int else 0):
        j.pop('chores')
