"""🏖️ Chơi trên đảo: beach activities and the daily island chest, for anyone on an island trip (story mode).

Owner 23/10: "nhà ở với đảo chưa ổn lắm, tăng tương tác hơn". On an island (game/island_trips.py: the owner, a friend
aboard, a visitor of an island open to everyone) the scene (public/js/v4/island-scene.js) had walking, emotes, chat and
the leisure buildings' tinh thần (game/island_build.py jr_isle_use). This adds, on every island, built or not:

* ACTS, each once a Vietnamese day (the trips are real time, like jr_isle_use): 🏊 bơi biển, 🎣 câu cá (a seeded
  catch, put back or grilled), 🍢 nướng BBQ, 🔥 đốt lửa trại, 🌅 chụp ảnh hoàng hôn, 🐚 nhặt vỏ sò. The first
  SPIRIT_MAX of a day add 1 tinh thần each; the rest are the moment and its line. Never xu.
* 🎁 Rương báu trên đảo (jr_beach_chest), once a Vietnamese day: a few xu (CHEST_XU, seeded) and 1 tinh thần.
  At most CHEST_XU[1] xu a day: a visit's small treat, nothing to farm.

Where the player is cannot be read from the save (trips live in PostgreSQL): like jr_isle_use, the command names the
trip, the reducer records it (`trip`) and command_commit (game/storage.py, in the save's own transaction) checks with
island_trips.ACCESS_SQL that this player is on that trip now; otherwise the whole command rolls back (nothing given).

State journey['beach'] (absent until the first act; an older build ignores it): {v, d (Vietnamese day of `did`), did
[acts that day], chest (0|1 that day), trip (the trip of the last command), n (acts in all)}.
Commands: jr_beach_do {trip, act}, jr_beach_chest {trip}.
"""
from __future__ import annotations

import random
import re
import time

VERSION = 1
KEYS = frozenset({'v', 'd', 'did', 'chest', 'trip', 'n'})
COMMANDS = ('jr_beach_do', 'jr_beach_chest')
TRIP_RE = re.compile(r'[0-9a-f]{16}')
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
SPIRIT_MAX = 3
CHEST_XU = (10, 25)
KIND, LABEL = 'life', '🎁 Rương báu trên đảo'

ACTS = {
    'boi': dict(emoji='🏊', name='Bơi biển', pose='swim',
                lines=('Bạn sải tay ra xa bờ, nước biển trong veo nhìn thấy cả cát dưới chân.',
                       'Sóng nhẹ đẩy bạn dập dềnh. Nằm ngửa trên mặt nước, trời xanh ngắt.',
                       'Bạn bơi tới phao rồi quay vào, lên bờ người mằn mặn mà khoan khoái.')),
    'cau_ca': dict(emoji='🎣', name='Câu cá', pose='sit',
                   lines=('Bạn ngồi đầu cầu tàu thả câu. Phao giật mạnh: {catch}!',
                          'Gió hiu hiu, phao lững lờ. Đợi một lúc thì dính {catch}.',
                          'Bạn quăng cần thật xa, cuộn chậm. Lên một mẻ: {catch}.')),
    'bbq': dict(emoji='🍢', name='Nướng BBQ', pose='stand',
                lines=('Mực nướng sa tế xèo xèo, mùi thơm bay khắp bãi.',
                       'Bạn nướng bắp, nướng tôm, chấm muối ớt xanh. Ngon hết sẩy.',
                       'Bếp than hồng rực, mọi người xúm lại chờ xiên thịt chín.')),
    'lua_trai': dict(emoji='🔥', name='Đốt lửa trại', pose='sit',
                     lines=('Lửa bập bùng, ai đó đàn ghi-ta, cả bãi hát theo.',
                            'Bạn ngồi sát đống lửa, ngắm tàn lửa bay lên lẫn với sao trời.',
                            'Lửa tí tách, bạn kể chuyện ma, ai cũng giật mình rồi cười phá lên.')),
    'hoang_hon': dict(emoji='🌅', name='Chụp ảnh hoàng hôn', pose='stand',
                      lines=('Mặt trời đỏ au chìm dần xuống biển. Bạn bấm máy: một tấm để đời.',
                             'Trời chuyển cam rồi tím, bạn chụp liền mấy tấm, tấm nào cũng đẹp.',
                             'Bóng dừa in trên nền trời hồng. Bạn chụp xong, ngồi lặng ngắm thêm chút nữa.')),
    'vo_so': dict(emoji='🐚', name='Nhặt vỏ sò', pose='stand',
                  lines=('Bạn nhặt được một vỏ ốc xoắn màu hồng, áp tai nghe tiếng sóng.',
                         'Dọc mép nước toàn vỏ sò trắng muốt. Bạn chọn mấy cái đẹp nhất làm kỷ niệm.',
                         'Một chú cua nhỏ chui ra từ vỏ ốc bạn vừa nhặt. Bạn thả nó về cát.')),
}
CATCH = ('một con cá thu bạc', 'một chú cá mú đỏ', 'một con ghẹ xanh', 'một con mực ống', 'một chiếc dép lạc trôi',
         'một bé cá hề (thả lại biển)')
CHEST_LINES = ('Dưới gốc dừa có chiếc rương gỗ nhỏ, bên trong lấp lánh mấy đồng xu.',
               'Sóng đánh dạt vào bờ một chiếc hộp thiếc. Mở ra: xu và một vỏ ốc xà cừ.',
               'Bạn đào cát xây lâu đài, đụng trúng rương báu ai giấu từ lâu.')
# A spot of the island's map (public/js/island-layout.js SPOTS) -> the activity it starts (the scene sends it).
SPOT_ACT = {'lan': 'boi', 'san_ho': 'boi', 'ho_boi': 'boi', 'suoi': 'boi', 'lua': 'lua_trai', 'bar': 'bbq',
            'nha_san': 'cau_ca', 'hai_dang': 'hoang_hon', 'dai': 'hoang_hon'}


def now() -> float:
    return time.time()


def vn_day(t: float | None = None) -> int:
    from .wealth_fee import today
    return today(t)


def _core():
    from . import engine
    return engine


def get(s: dict) -> dict | None:
    b = s['journey'].get('beach')
    return b if isinstance(b, dict) else None


def _day_block(s: dict, day: int) -> dict:
    j = s['journey']
    b = get(s)
    if b is None:
        b = j['beach'] = dict(v=VERSION, d=day, did=[], chest=0, trip='', n=0)
    if b['d'] != day:
        b['d'], b['did'], b['chest'] = day, [], 0
    return b


def public(s: dict) -> dict | None:
    """What is done today (journey.public 'homelife.beach'; absent when nothing is, for state size)."""
    b = get(s)
    if not b or b['d'] != vn_day(now()) or not (b['did'] or b['chest']):
        return None
    return dict(did=list(b['did']), **({'chest': True} if b['chest'] else {}))


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s.get('journey')
    need(isinstance(j, dict) and bool(j.get('story')), 'Chơi trên đảo chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and isinstance(p.get('trip'), str) and TRIP_RE.fullmatch(p['trip']) is not None,
         'Bạn không ở trên hòn đảo này.', 'no_island')
    day = vn_day(now())
    from . import needs as nd
    if name == 'jr_beach_chest':
        need(set(p) == {'trip'}, 'Thông tin không hợp lệ.')
        b = get(s)
        if b and b['d'] == day and b['chest']:
            return dict(message='Rương báu hôm nay mở rồi. Mai ra đảo tìm tiếp nhé!', duplicate=True)
        b = _day_block(s, day)
        b['chest'], b['trip'] = 1, p['trip']
        rnd = random.Random(f'beach|{j.get("seed", 0)}|{day}|chest')
        xu = rnd.randint(*CHEST_XU)
        from . import journey as jr
        jr._wallet(j, xu, KIND, LABEL)
        got = nd._spirit(s, 1)
        eff = [f'💰 +{xu} xu'] + ([f'😊 Tinh thần +{got}'] if got else [])
        return dict(message=f'🎁 {rnd.choice(CHEST_LINES)}', effects=eff, beach=dict(chest=True, xu=xu))
    need(set(p) == {'trip', 'act'} and p.get('act') in ACTS, 'Chọn một trò để chơi nhé.')
    act = p['act']
    x = ACTS[act]
    b = get(s)
    if b and b['d'] == day and act in b['did']:
        return dict(message=f'{x["emoji"]} Hôm nay bạn {x["name"].lower()} rồi. Thử trò khác nhé!', duplicate=True)
    b = _day_block(s, day)
    b['did'].append(act)
    b['trip'] = p['trip']
    b['n'] = min(10**6, b['n'] + 1)
    got = nd._spirit(s, 1) if len(b['did']) <= SPIRIT_MAX else 0
    rnd = random.Random(f'beach|{j.get("seed", 0)}|{day}|{act}')
    line = rnd.choice(x['lines']).format(catch=rnd.choice(CATCH))
    return dict(message=f'{x["emoji"]} {line}', effects=[f'😊 Tinh thần +{got}'] if got else [],
                beach=dict(act=act, spirit=got, left=max(0, SPIRIT_MAX - len(b['did']))))


# ---------------------------------------------------------------- PostgreSQL (game/storage.py, in the save's transaction)
def command_commit(db, sid: str, action: str, after, result=None) -> None:
    """A GameError here rolls the whole command back: the player must be on the trip the command named. A tap on
    something already done today changed nothing: nothing to check."""
    if action not in COMMANDS or (isinstance(result, dict) and result.get('duplicate')):
        return
    b = get(after) if isinstance(after, dict) and isinstance(after.get('journey'), dict) else None
    need = _core().need
    need(b and TRIP_RE.fullmatch(b.get('trip') or ''), 'Bạn không ở trên hòn đảo này.', 'no_island')
    from . import island_trips as it
    row = db.execute(it.ACCESS_SQL, (sid, b['trip'])).fetchone()
    need(it.access_for(row, sid, now()), 'Bạn không ở trên hòn đảo này.', 'no_island')


# ---------------------------------------------------------------- saves
def _ok(b) -> bool:
    return (isinstance(b, dict) and set(b) == KEYS and b['v'] == VERSION and type(b['d']) is int and 0 <= b['d'] <= 10**7
            and b['chest'] in (0, 1) and type(b['chest']) is int and isinstance(b['trip'], str)
            and (b['trip'] == '' or TRIP_RE.fullmatch(b['trip']) is not None) and type(b['n']) is int and 0 <= b['n'] <= 10**6
            and isinstance(b['did'], list) and len(b['did']) <= 16 and len(set(b['did'])) == len(b['did'])
            and all(isinstance(a, str) and ID_RE.fullmatch(a) for a in b['did']))


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'beach' not in j:
        return
    _core().need(_ok(j['beach']), 'Dữ liệu chơi trên đảo không hợp lệ.', 'invalid_save')


def upgrade(j: dict) -> None:
    if isinstance(j, dict) and 'beach' in j and not _ok(j['beach']):
        j.pop('beach')
