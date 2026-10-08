"""👶 Bé nhà mình (feedback #252 "cho em bé xuất hiện trong nhà… bế đi chơi", #145 "chủ đề gia đình").

The babies themselves already exist: the personal child of journey['household'] (game/household.py) and the
couple's shared child or a custody copy (game/family.py, PostgreSQL). This file adds what happens around them,
never what they cost:

* Lớn dần (`grow`): sơ sinh → biết bò → chập chững, by the baby's age in days (a personal child: life days since it
  came home; a shared child: Vietnam calendar days since it was born, like its care). Only how it is drawn and named
  in the room (public/js/v4/baby-art.js); the care stages of household/family are unchanged.
* Khoảnh khắc (moments) in the home room (public/js/v4/reno.js + home-walk.js): 🍼 cho bú / đút ăn, 🎶 ru ngủ,
  🧸 chơi cùng. Free, once per life day per baby, each one gắn bó +1, and tinh thần +1 for the first SPIRIT_DAY
  moments of a day (whatever the baby). Nothing decays, nothing is charged, nothing can be missed: no chore.
  The personal child: `jr_cradle_do {baby: 'child', act}` (journey.action). A shared child or a custody copy:
  `family_child_moment {child, act, rid}` (game/family.py, which checks the child in the database).
* Bế bé đi chơi: client-only (public/js/v4/baby.js, remembered in this browser like the ride toggle): the town, the
  fair and the strolls draw the baby in the character's arms; the live presence carries `bb` (live/babies.py).
* Đồ cho bé never goes on credit (`pay`): cash, the account or the joint fund only; a baby never puts a save in debt.

State (absent in older saves; created on the first moment): journey['cradle'] = {v, day (the life day of `did`),
did ('<baby>:<act>' done that day)}. An older build answers the commands with an unknown-action error and ignores
journey['cradle'] (journey.validate allows extra keys; nothing prunes them).
"""
from __future__ import annotations

import datetime
import random
import re

from . import needs as nd

VERSION = 1
KEYS = {'v', 'day', 'did'}
COMMANDS = ('jr_cradle_do',)
SPIRIT_DAY = 3                     # tinh thần from moments, at most, a life day
DID_MAX = 24
BABY = re.compile(r'child|shared|copy:[1-9][0-9]{0,11}')
# id, name, from (age in days)
GROW = (('so_sinh', 'Sơ sinh', 0), ('biet_bo', 'Biết bò', 7), ('chap_chung', 'Chập chững', 21))
GROW_NAME = {g: n for g, n, _ in GROW}
ACTS = {
    'bu': dict(emoji='🍼', names={'so_sinh': 'Cho bé bú', 'biet_bo': 'Đút bé ăn dặm', 'chap_chung': 'Cùng bé ăn bữa nhỏ'},
               lines=('{n} ăn no căng bụng, cười tít mắt.', '{n} ăn ngoan, lem nhem một chút quanh miệng.',
                      '{n} ăn xong ợ một cái thật to, cả nhà bật cười.')),
    'ru': dict(emoji='🎶', names={'so_sinh': 'Ru bé ngủ', 'biet_bo': 'Ru bé ngủ', 'chap_chung': 'Kể chuyện ru bé ngủ'},
               lines=('Bạn ầu ơ vài câu, {n} lim dim rồi ngủ say.', '{n} ngáp một cái thật to, ngủ ngon trong vòng tay bạn.',
                      'Tiếng ru ầu ơ, {n} thở đều, căn nhà yên ả hẳn.')),
    'choi': dict(emoji='🧸', names={'so_sinh': 'Chơi ú òa', 'biet_bo': 'Tập bò cùng bé', 'chap_chung': 'Dắt bé tập đi'},
                 lines=('{n} cười khanh khách, cả nhà vui lây.', '{n} với tay đòi bạn bế, thương ghê.',
                        '{n} nắm chặt ngón tay bạn, cười toe toét.')),
}
VN = datetime.timezone(datetime.timedelta(hours=7))


def _core():
    from . import engine
    return engine


def grow(age: int) -> str:
    """The stage id for an age in days (sơ sinh, biết bò, chập chững)."""
    out = GROW[0][0]
    for gid, _, start in GROW:
        if age >= start:
            out = gid
    return out


def household_age(j: dict, m: dict) -> int:
    """A personal child's age: life days since it came home."""
    try:
        return max(0, int(j.get('life_day') or 1) - int(m.get('since') or 1))
    except (TypeError, ValueError):
        return 0


def calendar_age(born: str, today: str) -> int:
    """A shared child's age: Vietnam calendar days since it was born (0 while it is awaited)."""
    try:
        return max(0, (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(born)).days)
    except (TypeError, ValueError):
        return 0


def act_name(act: str, stage: str) -> str:
    x = ACTS[act]['names']
    return x.get(stage) or x['so_sinh']


def _today(j: dict) -> list:
    c = j.get('cradle')
    return list(c['did']) if isinstance(c, dict) and c.get('day') == j.get('life_day') and isinstance(c.get('did'), list) else []


def catalog() -> list:
    """The moments as the home room lists them: [{id, emoji, names: {stage: name}}]."""
    return [dict(id=k, emoji=x['emoji'], names=dict(x['names'])) for k, x in ACTS.items()]


def public(s: dict) -> dict | None:
    """journey public 'cradle': what was done today (+ the moments' names when the save has its own child; a shared
    child's come with GET /api/family/baby). Small on purpose: every state carries it. None outside the story."""
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    did = _today(j)
    out = dict(did=did, spirit_left=max(0, SPIRIT_DAY - len(did)))
    if isinstance((j.get('household') or {}).get('child'), dict):
        out['acts'] = catalog()
    return out


def moment(s: dict, baby: str, act: str, name: str, stage: str) -> dict:
    """Record one moment with `baby` today (raises GameError when it is done already). Returns {message, spirit}.
    The caller has checked that the baby exists and is home; it moves the baby's own gắn bó."""
    e = _core()
    need = e.need
    j = s.get('journey')
    need(isinstance(j, dict) and bool(j.get('story')), 'Bé nhà mình chỉ có trong hành trình.', 'locked')
    need(isinstance(baby, str) and BABY.fullmatch(baby), 'Chọn em bé hợp lệ.')
    need(isinstance(act, str) and act in ACTS, 'Chọn một việc nhé.')
    did = _today(j)
    key = f'{baby}:{act}'
    need(key not in did, f'Hôm nay đã {act_name(act, stage).lower()} rồi. Mai mình lại chơi với bé nhé!', 'already_done')
    need(len(did) < DID_MAX, 'Hôm nay bạn đã ở bên bé nhiều rồi. Mai lại chơi nhé!', 'already_done')
    spirit = nd._spirit(s, 1) if len(did) < SPIRIT_DAY else 0
    j['cradle'] = dict(v=VERSION, day=j['life_day'], did=did + [key])
    line = random.Random(f'cradle|{j.get("seed", 0)}|{j["life_day"]}|{key}').choice(ACTS[act]['lines']).format(n=name)
    tail = ['gắn bó +1'] + ([f'tinh thần +{spirit}'] if spirit else [])
    return dict(message=f'{ACTS[act]["emoji"]} {line} ({", ".join(tail)})', spirit=spirit)


def action(s: dict, name: str, p: dict) -> dict:
    """jr_cradle_do {baby: 'child', act}: a moment with the personal child of journey['household']."""
    e = _core()
    need = e.need
    j = s.get('journey')
    need(isinstance(j, dict) and bool(j.get('story')), 'Bé nhà mình chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'baby', 'act'} and p.get('baby', 'child') == 'child', 'Chọn em bé hợp lệ.')
    m = (j.get('household') or {}).get('child')
    need(isinstance(m, dict), 'Nhà mình chưa có em bé.', 'not_found')
    out = moment(s, 'child', p.get('act'), m['name'], grow(household_age(j, m)))
    m['bond'] = min(100, int(m['bond']) + 1)
    return dict(message=out['message'], effects=[])


def pay(s: dict, amount: int, label: str, method='auto') -> dict:
    """A purchase for a baby (bank.pay), never on credit: cash, the current account or the joint fund."""
    from . import bank
    e = _core()
    method = method if method in ('auto', 'cash', 'account', 'joint', 'card') else 'auto'
    e.need(method != 'card', 'Đồ cho bé trả bằng tiền mặt hoặc tài khoản thôi, không quẹt thẻ tín dụng để khỏi mắc nợ.', 'no_credit')
    if method == 'auto' and bank._method(s, amount, 'auto') == 'card':
        method = next((m for m in ('cash', 'account') if bank.can_pay(s, amount, m)), None)
        e.need(method, f'Chưa đủ {amount} xu tiền mặt hoặc trong tài khoản. Đồ cho bé không trả bằng thẻ tín dụng; '
                       'tắm, chơi và đọc truyện cho bé thì luôn miễn phí.', 'not_enough')
    return bank.pay(s, amount, label, method=method, kind='life')


def no_credit(s: dict, amount: int, how) -> str:
    """game/family.py's payment choice for a baby, never the credit card: 'cash' | 'account' | 'auto'.
    Raises MarriageError (no_credit / not_enough) like the rest of family.py."""
    from . import bank, marriage as mr
    how = how if how in ('auto', 'cash', 'account', 'card') else 'auto'
    mr.need(how != 'card', 'Đồ cho bé trả bằng tiền mặt hoặc tài khoản thôi, không quẹt thẻ tín dụng để khỏi mắc nợ.', 'no_credit')
    if how == 'auto' and bank._method(s, amount, 'auto', no_joint=True) == 'card':
        how = next((m for m in ('cash', 'account') if bank.can_pay(s, amount, m, no_joint=True)), None)
        mr.need(how, 'Chưa đủ tiền mặt hoặc tài khoản. Đồ cho bé không trả bằng thẻ tín dụng.', 'not_enough')
    return how


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'cradle' not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu bé nhà mình không hợp lệ.'
    c = j['cradle']
    need(isinstance(c, dict) and set(c) == KEYS and type(c.get('v')) is int and c['v'] == VERSION, bad, 'invalid_save')
    integer(c['day'], 1, 10**6)
    need(c['day'] <= j['life_day'], bad, 'invalid_save')
    did = c['did']
    need(isinstance(did, list) and len(did) <= DID_MAX and len(did) == len(set(did)), bad, 'invalid_save')
    for k in did:
        need(isinstance(k, str) and ':' in k, bad, 'invalid_save')
        baby, _, act = k.rpartition(':')
        need(bool(BABY.fullmatch(baby)) and act in ACTS, bad, 'invalid_save')
