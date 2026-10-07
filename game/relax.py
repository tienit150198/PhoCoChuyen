"""🏊 Thư giãn ở nhà: a swim in the villa's pool, a lie-down by the water, a soak in the bathtub (story mode).

Player feedback (02/10): "nhà chưa có nhà tắm, biệt thự 60k cũng không có hồ bơi". Since 1.4.11 every home has a
bathroom and the villas a pool deck (game/deco_content.py KITS, drawn by public/js/v4/deco-art.js); this file is the
small daily thing to do there. Like the pagoda's acts and a vehicle's ride out: free (never xu), a little tinh thần,
once per life day per spot, nothing that can go wrong.

* Hồ bơi (a villa you live in, yours or your spouse's): `boi` (bơi một vòng) or `nam` (nằm thư giãn bên hồ), one of
  the two a day. Swimming follows the needs bars (game/needs.py): not on an empty stomach (no bụng under needs.LOW)
  nor half asleep (tỉnh táo under needs.LOW); the cool water wakes you up a little and makes you hungry. Lying in the
  sun is always fine.
* Nhà tắm: `ngam` (ngâm bồn nước ấm) once a day, when a bathtub (deco item `bon_tam`) stands in your bathroom. The
  bathroom itself costs nothing; the tub is an optional piece from the decor shop.

State (absent in older saves; created on the first act): journey['relax'] = {v, day (the life day of `did`), did
(acts done that day), n (acts done in all)}. Command (through journey.action): jr_relax_do {act}. An older build
answers it with 'unknown_action' and ignores journey['relax'] (journey.validate allows extra keys). The acts ride in
deco.public()['relax'] only where they can happen (a page loaded before 1.4.11 ignores the field).
Deterministic: the line of the day is picked by the journey seed and the life day.
"""
from __future__ import annotations

import random

from . import needs as nd

VERSION = 1
KEYS = {'v', 'day', 'did', 'n'}
COMMANDS = ('jr_relax_do',)
SWIM_FULL, SWIM_WAKE = -10, 8      # a swim: hungrier, more awake

# id -> where (a room type of the place), slot (one act per slot a day), tinh thần, the lines (one picked a day).
ACTS = {
    'boi': dict(emoji='🏊', name='Bơi một vòng', room='pool', slot='pool', spirit=3,
                lines=('Bạn bơi chậm mấy vòng quanh hồ. Nước mát lạnh, lên bờ thấy người nhẹ tênh.',
                       'Bạn thả mình xuống hồ, bơi ngửa nhìn mây trôi. Mấy con chuồn chuồn lượn sát mặt nước.',
                       'Bạn bơi một mạch hết hồ rồi bám thành nghỉ, nghe nước vỗ lách tách.')),
    'nam': dict(emoji='🌴', name='Nằm thư giãn bên hồ', room='pool', slot='pool', spirit=2,
                lines=('Bạn nằm ghế cạnh hồ, nghe gió lùa qua tán lá. Suýt nữa thì ngủ quên.',
                       'Bạn ngâm chân xuống hồ, ngồi ngắm bóng nắng lăn tăn trên mặt nước.',
                       'Bạn pha ly nước chanh, ngả lưng bên hồ đọc vài trang sách.')),
    'ngam': dict(emoji='🛁', name='Ngâm bồn nước ấm', room='bath', slot='bath', spirit=2,
                 lines=('Bạn xả một bồn nước ấm, ngâm mình thật lâu. Mệt mỏi cả ngày tan theo hơi nước.',
                        'Bạn thả vài cánh hoa vào bồn, mở nhạc nhỏ, nằm nghe tới khi nước nguội.',
                        'Bạn ngâm bồn, con vịt cao su trôi lững lờ bên cạnh. Bình yên ghê.')),
}
TUB = 'bon_tam'


def _core():
    from . import engine
    return engine


def _dc():
    from . import deco
    return deco


def _today(s: dict) -> list:
    r = s['journey'].get('relax')
    return list(r['did']) if isinstance(r, dict) and r.get('day') == s['journey']['life_day'] else []


def _spots(s: dict, L: dict) -> dict:
    """{room type: room} of the place you live in, for the acts' rooms (a villa's pool, your own bathroom)."""
    if L['place']['where'] not in ('own', 'shared', 'estate'):   # 🏰 'estate': a villa you live in (game/estates.py)
        return {}
    out = {r['type']: r for r in L['rooms'] if r['type'] in ('pool', 'bath')}
    inf = next((r for r in L['rooms'] if r['type'] == 'infinity'), None)   # 🏰 a villa's infinity pool is a pool too
    if inf and 'pool' not in out:
        out['pool'] = inf
    return out


def why_not(s: dict, act: str, L: dict | None = None) -> str:
    """Why `act` cannot be done now ('' = it can)."""
    from . import deco_mate
    L = deco_mate.use_layout(s, L)
    x = ACTS[act]
    room = _spots(s, L).get(x['room'])
    if room is None:
        return 'Nhà này không có hồ bơi' if x['room'] == 'pool' else 'Chỉ ở nhà riêng'
    did = _today(s)
    if act in did:
        return 'Hôm nay làm rồi'
    if any(ACTS[a]['slot'] == x['slot'] for a in did if a in ACTS):
        return 'Hôm nay thư giãn ở đây rồi'
    if act == 'ngam' and not any(L['kinds'].get(u) == TUB and q['r'] == room['id'] for u, q in L['pos'].items()):
        return 'Cần một bồn tắm trong nhà tắm'
    if act == 'boi':
        n = nd.get(s)
        if n and n['full'] < nd.LOW:
            return 'Bụng đói, ăn chút gì đã'
        if n and n['wake'] < nd.LOW:
            return 'Buồn ngủ quá, bơi không an toàn'
    return ''


def view(s: dict, L: dict) -> list:
    """The acts of the place you live in (deco.public 'relax'): [] where there is none."""
    from . import deco_mate
    L = deco_mate.use_layout(s, L)
    spots = _spots(s, L)
    if not spots:
        return []
    did = _today(s)
    out = []
    for k, x in ACTS.items():
        if x['room'] not in spots:
            continue
        why = why_not(s, k, L)
        out.append(dict(id=k, emoji=x['emoji'], name=x['name'], room=spots[x['room']]['id'], spirit=x['spirit'],
                        done=k in did, ok=not why, why=why))
    return out


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s.get('journey')
    need(isinstance(j, dict) and bool(j.get('story')), 'Thư giãn ở nhà chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'act'} and p.get('act') in ACTS, 'Chọn một việc nhé.')
    act = p['act']
    x = ACTS[act]
    why = why_not(s, act)
    need(why not in ('Hôm nay làm rồi', 'Hôm nay thư giãn ở đây rồi'), 'Hôm nay bạn thư giãn ở đây rồi. Mai nhé!', 'already_done')
    need(why not in ('Nhà này không có hồ bơi', 'Chỉ ở nhà riêng'), 'Ở đây chưa có chỗ để làm việc này.', 'not_here')
    need(why != 'Cần một bồn tắm trong nhà tắm', 'Nhà tắm chưa có bồn. Bồn tắm có trong cửa hàng Bày trí phòng.', 'not_here')
    need(why != 'Bụng đói, ăn chút gì đã', 'Bụng đói meo, bơi dễ mệt. Ăn chút gì rồi hãy bơi nhé.', 'too_hungry')
    need(not why, 'Đang buồn ngủ, bơi không an toàn. Nằm nghỉ bên hồ thôi nhé.', 'too_sleepy')
    r = j.get('relax')
    if not isinstance(r, dict) or r.get('day') != j['life_day']:
        r = j['relax'] = dict(v=VERSION, day=j['life_day'], did=[], n=int(r['n']) if isinstance(r, dict) else 0)
    r['did'].append(act)
    r['n'] = min(10**6, r['n'] + 1)
    got = nd._spirit(s, x['spirit'])
    parts = [f'tinh thần +{got}'] if got else []
    if act == 'boi':
        n = nd.ensure(s)
        n['wake'] = nd._clamp(n['wake'] + SWIM_WAKE)
        n['full'] = nd._clamp(n['full'] + SWIM_FULL)
        parts += [f'tỉnh táo {n["wake"]}', f'no bụng {n["full"]}']
    line = random.Random(f'relax|{j.get("seed", 0)}|{j["life_day"]}|{act}').choice(x['lines'])
    tail = f' ({", ".join(parts)})' if parts else ''
    return dict(message=f'{x["emoji"]} {line}{tail}', effects=[])


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'relax' not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu thư giãn ở nhà không hợp lệ.'
    r = j['relax']
    need(isinstance(r, dict) and set(r) == KEYS and r.get('v') == VERSION, bad, 'invalid_save')
    integer(r['day'], 1, 10**6)
    need(r['day'] <= j['life_day'], bad, 'invalid_save')
    did = r['did']
    need(isinstance(did, list) and len(did) <= len(ACTS) and len(did) == len(set(did)) and set(did) <= set(ACTS), bad, 'invalid_save')
    integer(r['n'], 0, 10**6)
    need(r['n'] >= len(did), bad, 'invalid_save')
