"""🚔 Trại tạm giữ: a few in-game days behind bars (owner 09/10: "thêm chế độ bắt tù đi, kiểu người ta đánh giá sai, tố
cáo sai thì bị bắt tù 1 ngày trong game, còn chơi cờ bạc bị bắt 3 ngày trong game. có người bảo lãnh thì trừ 30k
tiền. Này là bạn bè mới bảo lãnh được, bị bắt thì thiết kế màn tù riêng, trong đó làm công ích (bạn xem làm gì thì
được), thì sẽ được giảm ngày. tỷ lệ bị bắt thấp tý nhé").

Who goes in
* 🕶️ Chợ đen (game/fair.py _police, game/fair_bm.py): a raided paid round, DAYS_BM (3) jail days.
* 🚔 Tố cáo sai sự thật (game/review_police.py): a police report on an NPC review that was reasonable, sometimes,
  DAYS_COP (1) jail day. Odds are never shown or sent.

A jail day is a life day (journey.life_day). Inside, the owner's rule (09/10: "bị bắt thì k được làm gì khác, chỉ
được ở tù, nhắn tin, làm công ích thôi") is an ALLOWLIST, so whatever is added to the game later is closed by default:
* game commands (gate(), OPEN_COMMANDS): settings, the jail's own commands and the acknowledgements of what is already
  on screen (news, a story beat, a happening, the board's dot, the bank's notices, a life card that is over);
* HTTP routes (route_open(), server.py): the command route (the gate above), the account (sign in/out, delete),
  góp ý, admin, push, privacy settings, popups seen (a gift, a wedding card), friends and blocks, the bail
  requests, the social inbox read, and what others did FOR the player (a transfer in, a work visit's pay);
* live frames (frame_open(), live/protocol.py): the chat (Cả phố, DMs, groups) and keep-alive, plus leaving a room.
Refused: code 'jailed', JAILED. What others do TO a jailed player still lands (a transfer, an admin gift, a friend's
bail) and the passive clocks run as before (staff, rent, interest).
"🌙 Hết một ngày trong trại" (jail_end) ends the jail day: the life day moves on without work, the day's rent or
điện nước is paid as usual (the jail's meals are free: no meals line), the morning hooks run (bank, home, bills…), and
the sentence counts down by one, by two when the day's three công ích tasks are done. A jail day lasts at least
DAY_MIN_S real seconds (a countdown on the button), long enough for the tasks.

Công ích: TASKS_PER_DAY of TASKS a day, chosen from (sentence id, jail day). jail_task_start notes the task and the
time, jail_task_done checks the answer against the task's own seeded puzzle (puzzle()) and that at least TASK_MIN_S
seconds went by (no spam): sweep every leaf pile, dig → plant → water every hole, the right scoops of rice on every
tray, paint every stained panel, the books in order.

Bail (game/marriage.py act → ACTIONS: POST /api/marriage/jail_ask, /api/marriage/jail_bail): the jailed player asks
their friends (one social inbox row of kind 'jail' and the Bạn bè notice each, ASK_GAP_S apart); a FRIEND pays BAIL_XU
from their own wallet (a Sổ ví row), and the jailed save is released at once: both saves in one transaction under
their revision guards (marriage._mutate). Not yourself, not a non-friend, not with a short wallet, not someone already
out (so once per sentence).

Nobody is stuck: past days × SAFE_S real seconds since the arrest the sentence is over by itself (active()), and
MNL_JAIL_OFF=1 releases everybody and jails nobody (settle() drops the block on the next command; tests/__init__.py
sets it, tests/test_jail.py turns it on).

Save: journey['jail'] {v, id, why, days, left, at, day, since, tasks, done, go, ask} (optional, absent when free). It
sits in the journey, which keeps new optional blocks, so an older server (1.9.29) loads the save and simply ignores it
(tests/test_jail.py OldServer). No new table: the bail requests are rows of the social inbox.
"""
from __future__ import annotations

import hashlib
import os
import random
import time

KEY = 'jail'
VERSION = 1
DAYS_BM = 3                    # 🕶️ đánh bạc ở chợ đen
DAYS_COP = 1                   # 🚔 tố cáo sai sự thật
BAIL_XU = 30000                # a friend pays this (shown: it is a price)
TASKS_PER_DAY = 3
TASK_MIN_S = 15                # a công ích task takes at least this long between start and done
DAY_MIN_S = 120                # a jail day lasts at least this long (real seconds) before "Hết ngày"
SAFE_S = 86400                 # the safety release: past days × SAFE_S real seconds since the arrest
ASK_GAP_S = 600                # one bail request to the friends every ten minutes at most
ASK_MAX = 60                   # friends asked at most (the newest friendships first)
ASK_DAYS = 4                   # a request older than this is not shown any more
WHY = ('bm', 'cop')
WHY_TEXT = dict(bm='Đánh bạc ở chợ đen', cop='Tố cáo sai sự thật')
KEYS = {'v', 'id', 'why', 'days', 'left', 'at', 'day', 'since', 'tasks', 'done', 'go', 'ask'}
COMMANDS = ('jail_end', 'jail_task_start', 'jail_task_done')
INBOX = 'jail'                 # the social inbox kind of a bail request (an old client shows its text with a 🔔)
BAIL_LABEL = '🚔 Bảo lãnh cho {name}'
RENT_LABEL = 'Tiền phòng ngày {day} (ở trại, cơm trại miễn phí)'

TASKS = {
    'sweep': dict(emoji='🧹', name='Quét sân trại', hint='Chạm vào từng đống lá cho tới khi sạch.'),
    'plant': dict(emoji='🌱', name='Trồng cây ven đường', hint='Mỗi hố: đào, gieo hạt rồi tưới nước.'),
    'rice': dict(emoji='🍚', name='Phụ bếp chia cơm', hint='Múc đúng số muỗng cơm ghi trên mỗi khay.'),
    'paint': dict(emoji='🎨', name='Sơn lại tường', hint='Quét sơn lên mọi ô tường còn bẩn.'),
    'books': dict(emoji='📚', name='Xếp sách thư viện trại', hint='Chạm vào sách theo số từ nhỏ tới lớn.'),
}
TASK_IDS = tuple(TASKS)
PLANT_STEPS = ('dig', 'seed', 'water')

JAILED = 'Đang ở trại tạm giữ, ra rồi hẵng làm nha.'
NOT_IN = 'Bạn không ở trại tạm giữ.'


def now() -> float:
    return time.time()


def off() -> bool:
    """MNL_JAIL_OFF=1: nobody is jailed, everybody is released (the admin's kill switch; the tests' default)."""
    return os.environ.get('MNL_JAIL_OFF', '') == '1'


def _need(cond, message: str, code: str = 'invalid_action') -> None:
    from .engine import need
    need(cond, message, code)


def block(j) -> dict | None:
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def active(j, t: float | None = None) -> bool:
    """In jail now: a block, the switch on and the safety time not over."""
    b = block(j)
    if not b or off():
        return False
    t = now() if t is None else t
    try:
        return t - int(b['at']) < int(b['days']) * SAFE_S and int(b['left']) > 0
    except (KeyError, TypeError, ValueError):
        return False


def _pick(sid: str, day: int) -> list:
    """The day's công ích: TASKS_PER_DAY of TASKS, fixed by (sentence, jail day)."""
    return random.Random(f'jail|{sid}|{day}').sample(list(TASK_IDS), TASKS_PER_DAY)


def puzzle(sid: str, day: int, task: str) -> dict:
    """A task's seeded layout: what the client draws and what the answer is checked against."""
    r = random.Random(f'jail|{sid}|{day}|{task}')
    if task == 'sweep':
        n = r.randint(6, 8)
        spots = []
        while len(spots) < n:   # a 4 × 3 yard grid, one pile a cell
            c = r.randrange(12)
            if c not in spots:
                spots.append(c)
        return dict(piles=spots)
    if task == 'plant':
        return dict(holes=4)
    if task == 'rice':
        return dict(want=[r.randint(1, 3) for _ in range(5)])
    if task == 'paint':
        return dict(cells=10, dirty=sorted(r.sample(range(10), r.randint(5, 7))))
    nums = r.sample(range(1, 100), 6)
    return dict(nums=nums)


def _right(task: str, pz: dict, ans) -> bool:
    if not isinstance(ans, dict):
        return False
    if task == 'sweep':
        got = ans.get('swept')
        return isinstance(got, list) and len(got) <= 12 and sorted(x for x in got if type(x) is int) == sorted(pz['piles']) \
            and len(set(got)) == len(got)
    if task == 'plant':
        got = ans.get('steps')
        return isinstance(got, list) and len(got) == pz['holes'] and all(isinstance(x, list) and tuple(x) == PLANT_STEPS for x in got)
    if task == 'rice':
        got = ans.get('scoops')
        return isinstance(got, list) and all(type(x) is int for x in got) and got == pz['want']
    if task == 'paint':
        got = ans.get('cells')
        return isinstance(got, list) and all(type(x) is int for x in got) and len(got) <= pz['cells'] \
            and len(set(got)) == len(got) and set(got) == set(pz['dirty'])
    got = ans.get('order')
    nums = pz['nums']
    return isinstance(got, list) and len(got) == len(nums) and all(type(x) is int and 0 <= x < len(nums) for x in got) \
        and len(set(got)) == len(got) and [nums[i] for i in got] == sorted(nums)


def arrest(j: dict, why: str, days: int, t: float | None = None) -> int:
    """Put the player in the trại tạm giữ for `days` jail days (a story save only). Returns the days to serve now
    (0: not jailed: the switch is off or not a story save). Already inside: the longer sentence stays."""
    if off() or not isinstance(j, dict) or not j.get('story') or why not in WHY:
        return 0
    t = now() if t is None else t
    if active(j, t):
        return int(j[KEY]['left'])
    sid = hashlib.sha256(f'{j.get("seed", 0)}|{j.get("life_day", 1)}|{int(t)}|{why}'.encode()).hexdigest()[:10]
    j[KEY] = dict(v=VERSION, id=sid, why=why, days=int(days), left=int(days), at=int(t), day=1, since=int(t),
                  tasks=_pick(sid, 1), done=[], go=None, ask=0)
    return int(days)


def release(j: dict) -> None:
    j.pop(KEY, None)


def settle(s: dict, t: float | None = None) -> bool:
    """Every command: a block whose time is over (the safety release) or the switch: gone. True when it went."""
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict) or KEY not in j or active(j, t):
        return False
    release(j)
    return True


# What a jailed player may still do (everything else: JAILED). Internal (server) commands always run.
OPEN_COMMANDS = frozenset({'settings', *COMMANDS,
                           'jr_seen', 'st_seen', 'hap_ack', 'bd_seen', 'jr_bk_read', 'lf_close'})   # acknowledgements
# HTTP POST routes (server.py _post) open while jailed. GET only reads.
OPEN_ROUTES = frozenset({'/api/command', '/api/feedback', '/api/leaderboard/visibility', '/api/live/effects',
                         '/api/gift/seen', '/api/wedinvite/seen', '/api/push/subscribe', '/api/push/unsubscribe',
                         '/api/bank/xfer/receive', '/api/work-visits/receive', '/api/social/inbox_read',
                         '/api/social/block', '/api/social/unblock', '/api/social/report', '/api/social/delete_post'})
OPEN_PREFIXES = ('/api/admin/', '/api/account/')
OPEN_MARRIAGE = frozenset({'jail_ask', 'jail_bail', 'seen', 'lookup', 'block', 'unblock', 'settings', 'moments_seen',
                           'friend_search', 'friend_request', 'friend_respond', 'friend_cancel', 'friend_remove',
                           'friend_block', 'friend_settings'})
# Live frames (live/protocol.py): every frame of these features, and leaving a room of any other one.
OPEN_FEATURES = frozenset({'core', 'chat'})
OPEN_FRAMES = frozenset({'booth_out', 'booth_cancel', 'date_leave', 'fair_out', 'home_out', 'kara_out', 'walk_out',
                         'town_out', 'visit_out'})


def allowed(action: str) -> bool:
    return action in OPEN_COMMANDS


def route_open(route: str) -> bool:
    """A POST route a jailed player may use (server.py)."""
    if route in OPEN_ROUTES or route.startswith(OPEN_PREFIXES):
        return True
    return route.startswith('/api/marriage/') and route[len('/api/marriage/'):] in OPEN_MARRIAGE


def frame_open(feature: str, kind: str) -> bool:
    """A live frame a jailed player may send (live/protocol.py)."""
    return feature in OPEN_FEATURES or kind in OPEN_FRAMES


def jailed(s, t: float | None = None) -> bool:
    """A save that is in the camp now."""
    j = s.get('journey') if isinstance(s, dict) else None
    return active(j, t)


def gate(s: dict, action: str, internal: bool = False, t: float | None = None) -> None:
    """Before any command: refuse what a jailed player cannot do (code 'jailed')."""
    if internal or allowed(action):
        return
    if jailed(s, t):
        _need(False, JAILED, 'jailed')


# ---------------------------------------------------------------- the jail's own commands
def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _morning(s: dict) -> None:
    """The jail's breakfast and a night on the bunk: the needs bars start the new life day (game/needs.py)."""
    n = (s['journey'].get('needs'))
    if isinstance(n, dict):
        n.update(day=s['journey']['life_day'], full=max(int(n.get('full', 0)), 70), wake=85, worked=0, seen=None,
                 lunch=None, low=[], finish=None, eve=None)


def _end(s: dict, p: dict, t: float, result: dict) -> None:
    from . import journey as jr
    j = s['journey']
    b = j[KEY]
    _need(set(p) <= {'day'} and p.get('day', b['day']) == b['day'], 'Ngày trong trại này đã qua rồi. Tải lại trang nhé.', 'jail_stale')
    wait = b['since'] + DAY_MIN_S - int(t)
    _need(wait <= 0, f'Còn {wait // 60}:{wait % 60:02d} nữa mới hết ngày trong trại. Làm công ích cho nhanh nha.', 'jail_wait')
    full = len(b['done']) >= len(b['tasks'])
    day = j['life_day']
    cost = jr.living_cost(j)
    rent = max(0, int(cost['rent']))
    if rent:
        jr._wallet(j, -rent, 'living', RENT_LABEL.format(day=day))
        j['stats']['living_paid'] += rent
    notes = [f'🌙 Hết ngày sống {day} trong trại' + (f': tiền phòng {rent} xu, cơm trại miễn phí.' if rent else ', cơm trại miễn phí.')]
    if day == 1:   # a new player's first day still ends with Bà Tám's welcome
        jr._wallet(j, jr.WELCOME_GIFT, 'life', jr.WELCOME_LABEL)
        notes.append(f'🎁 Bà Tám gửi quà chào hàng xóm mới: +{jr.WELCOME_GIFT} xu vào ví.')
    j['clean_days'] = j['clean_days'] + 1 if j['wallet'] >= 0 else 0
    j['life_day'] += 1
    _morning(s)
    cut = 2 if full else 1
    b['left'] = max(0, b['left'] - cut)
    if full:
        notes.append('🧹 Làm đủ công ích hôm nay: được giảm thêm một ngày.')
    if b['left'] <= 0:
        release(j)
        result['message'] = '🎉 Hết hạn tạm giữ. Bạn được về nhà rồi, sống tử tế nha!'
        result['jail'] = dict(free=True)
    else:
        b.update(day=b['day'] + 1, since=int(t), tasks=_pick(b['id'], b['day'] + 1), done=[], go=None)
        result['message'] = f'Còn {b["left"]} ngày trong trại. Sáng nay có việc công ích mới.'
        result['jail'] = dict(free=False, left=b['left'])
    if j['wallet'] < 0:
        notes.append(f'Ví đang nợ {-j["wallet"]} xu. Ra trại rồi rút tiền từ nơi làm việc để trả nhé.')
    result['effects'].extend(notes)


def _task_start(s: dict, p: dict, t: float, result: dict) -> None:
    b = s['journey'][KEY]
    task = p.get('task')
    _need(set(p) == {'task'} and task in b['tasks'], 'Việc công ích này không có trong hôm nay.')
    _need(task not in b['done'], 'Việc này làm xong rồi.', 'already_done')
    if not (isinstance(b['go'], dict) and b['go'].get('t') == task):
        b['go'] = dict(t=task, at=int(t))
    result['message'] = ''
    result['jail'] = dict(task=task, pz=puzzle(b['id'], b['day'], task), ready=b['go']['at'] + TASK_MIN_S)


def _task_done(s: dict, p: dict, t: float, result: dict) -> None:
    b = s['journey'][KEY]
    task = p.get('task')
    _need(set(p) == {'task', 'ans'} and task in b['tasks'], 'Việc công ích này không có trong hôm nay.')
    if task in b['done']:   # a retry, another tab
        result.update(message='', jail=dict(task=task, ok=True, again=True))
        return
    go = b['go']
    _need(isinstance(go, dict) and go.get('t') == task, 'Bắt đầu việc này trước đã nhé.', 'jail_not_started')
    _need(int(t) - go['at'] >= TASK_MIN_S, 'Làm từ từ cho kỹ nha, cán bộ đang xem đó.', 'jail_fast')
    _need(_right(task, puzzle(b['id'], b['day'], task), p.get('ans')), 'Chưa xong đâu, làm lại cho đúng nha.', 'jail_wrong')
    b['done'].append(task)
    b['go'] = None
    all_done = len(b['done']) >= len(b['tasks'])
    result['message'] = (f'{TASKS[task]["emoji"]} Xong: {TASKS[task]["name"].lower()}.'
                         + (' Đủ công ích hôm nay: hết ngày này được tính hai ngày.' if all_done and b['left'] > 1 else ''))
    result['jail'] = dict(task=task, ok=True, all=all_done)


def action(s: dict, name: str, p: dict) -> tuple[dict, dict]:
    """jail_end, jail_task_start, jail_task_done (engine._apply_action)."""
    from . import engine as e
    from . import journey as jr
    from . import invest as iv
    _need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    j = s['journey']
    t = now()
    _need(j.get('story') and active(j, t), NOT_IN, 'jail_none')
    result = dict(message='', effects=[])
    if name == 'jail_end':
        _end(s, p, t, result)
        jr.after(s, None, name, p, result)   # the morning: bank, home, bills, counters, titles (game/journey.py)
        iv.on_life_day(s, result)
    elif name == 'jail_task_start':
        _task_start(s, p, t, result)
    else:
        _task_done(s, p, t, result)
    e.validate_state(s)
    return s, result


def public(s: dict) -> dict | None:
    """api.state.jail (None when free): days, today's tasks and their puzzles, when the day may end. No odds."""
    j = s.get('journey') if isinstance(s, dict) else None
    t = now()
    if not active(j, t):
        return None
    b = j[KEY]
    go = b['go'] if isinstance(b['go'], dict) else None
    tasks = [dict(id=x, **TASKS[x], done=x in b['done'], pz=puzzle(b['id'], b['day'], x)) for x in b['tasks']]
    return dict(id=b['id'], why=b['why'], why_text=WHY_TEXT[b['why']], days=b['days'], left=b['left'], day=b['day'],
                tasks=tasks, go=go['t'] if go else None, task_ready=go['at'] + TASK_MIN_S if go else 0,
                ready=b['since'] + DAY_MIN_S, ask_next=b['ask'] + ASK_GAP_S if b['ask'] else 0, bail=BAIL_XU, now=int(t))


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    from .engine import need, integer
    bad = 'Dữ liệu trại tạm giữ không hợp lệ.'
    b = j[KEY]
    need(isinstance(b, dict) and set(b) == KEYS and b['v'] == VERSION and b['why'] in WHY, bad, 'invalid_save')
    need(isinstance(b['id'], str) and 1 <= len(b['id']) <= 16 and b['id'].isalnum(), bad, 'invalid_save')
    integer(b['days'], 1, 30)
    integer(b['left'], 0, b['days'])
    integer(b['day'], 1, 60)
    for k in ('at', 'since', 'ask'):
        integer(b[k], 0, 2 ** 40)
    need(isinstance(b['tasks'], list) and len(b['tasks']) == TASKS_PER_DAY and len(set(b['tasks'])) == TASKS_PER_DAY
         and set(b['tasks']) <= set(TASK_IDS), bad, 'invalid_save')
    need(isinstance(b['done'], list) and len(set(b['done'])) == len(b['done']) and set(b['done']) <= set(b['tasks']), bad, 'invalid_save')
    go = b['go']
    need(go is None or (isinstance(go, dict) and set(go) == {'t', 'at'} and go['t'] in b['tasks'] and type(go['at']) is int
                        and 0 <= go['at'] <= 2 ** 40), bad, 'invalid_save')


# ---------------------------------------------------------------- bail: cross-player (game/marriage.py act)
def _mr():
    from . import marriage as mr
    return mr


def _ref(code: str) -> str:
    return f'jail:{code}'


def _push(store, sid: str, text: str) -> None:
    """A phone notification (game/push.py), best effort, after the write."""
    from . import push
    try:
        store.transaction(lambda db: push.queue(db, sid, 'jail', text, '/'), 250)
    except Exception:  # noqa: BLE001 - no push tables (tests, a dev database), a busy moment
        pass


def _inbox(db, sid: str, text: str, ref: str | None, kind: str = INBOX) -> None:
    from .social import pid_of
    db.execute('INSERT INTO inbox(pid,kind,text,ref,at) VALUES(?,?,?,?,?)', (pid_of(sid), kind, text[:300], ref, _mr().now()))


def ask(store, sid: str, display: str, d: dict) -> dict:
    """POST /api/marriage/jail_ask: the jailed player asks every friend to bail them out."""
    mr = _mr()
    loaded = mr._read_state(store, sid)
    mr.need(loaded and active((loaded[0] or {}).get('journey'), now()), NOT_IN, 'jail_none', 409)
    with store.connect() as db:
        friends = [r['friend'] for r in db.execute('SELECT friend FROM friends WHERE sid=? ORDER BY since DESC LIMIT ?', (sid, ASK_MAX)).fetchall()
                   if not mr._blocked(db, sid, r['friend'])]
        code = (mr._row(db, 'SELECT code FROM marriage_people WHERE sid=?', (sid,)) or {}).get('code')
    mr.need(friends, 'Bạn chưa có bạn bè nào để nhờ bảo lãnh. Kết bạn ở mục Bạn bè nhé.', 'no_friends', 409)
    mr.need(code, 'Chưa có mã người chơi. Tải lại trang nhé.', 'busy', 409)
    t = now()
    text = f'🚔 {display} đang ở trại tạm giữ, nhờ bạn bảo lãnh {_fmt(BAIL_XU)} xu. Mở mục Bạn bè để bảo lãnh nhé.'

    def fn(s):
        j = s['journey']
        mr.need(active(j, t), NOT_IN, 'jail_none', 409)
        b = j[KEY]
        wait = b['ask'] + ASK_GAP_S - int(t) if b['ask'] else 0
        mr.need(wait <= 0, f'Bạn vừa nhờ bạn bè rồi. {max(1, -(-wait // 60))} phút nữa nhờ lại được nhé.', 'jail_asked', 429)
        b['ask'] = int(t)

    def ops(db):
        db.execute('DELETE FROM inbox WHERE kind=? AND ref=?', (INBOX, _ref(code)))
        for f in friends:
            _inbox(db, f, text, _ref(code))
            mr._notice(db, f, text)
    mr._mutate_retry(store, {sid: fn}, ops)
    for f in friends[:20]:
        _push(store, f, text)
    return dict(message=f'Đã nhờ {len(friends)} người bạn bảo lãnh. Ai bảo lãnh, bạn được về ngay.', changed=True, quiet=True)


def bail(store, sid: str, display: str, d: dict) -> dict:
    """POST /api/marriage/jail_bail {code}: a friend pays BAIL_XU and the jailed player is out at once."""
    mr = _mr()
    from . import friends as fr
    code = d.get('code')
    mr.need(isinstance(code, str) and code.strip(), 'Chọn người bạn cần bảo lãnh nhé.', 'not_found', 404)
    code = mr.clean_code(code)
    with store.connect() as db:
        p = mr._find(db, code)
        mr.need(p, 'Không tìm thấy người này.', 'not_found', 404)
        other = p['sid']
        mr.need(other != sid, 'Bạn không tự bảo lãnh cho mình được. Nhờ bạn bè nhé.', 'self', 409)
        mr.need(fr.are_friends(db, sid, other) and not mr._blocked(db, sid, other), 'Chỉ bạn bè mới bảo lãnh được cho nhau.', 'not_friend', 403)
        name = mr._display(db, other)
    t = now()

    def gone(db):
        db.execute('DELETE FROM inbox WHERE kind=? AND ref=?', (INBOX, _ref(code)))

    def free(s):
        j = s['journey']
        mr.need(active(j, t), f'{name} đã ra trại rồi, không cần bảo lãnh nữa.', 'jail_gone', 409)
        release(j)

    def pay(s):
        j = s['journey']
        mr.need(j.get('story'), 'Bảo lãnh chỉ có trong hành trình.', 'not_story', 409)
        mr.need(not active(j, t), 'Bạn đang ở trại, chưa bảo lãnh cho ai được.', 'jailed', 409)
        mr.need(j['wallet'] >= BAIL_XU, f'Ví cần {_fmt(BAIL_XU)} xu để bảo lãnh (ví đang có {_fmt(max(0, j["wallet"]))} xu).',
                'not_enough', 409)
        from . import journey as jr
        jr._wallet(j, -BAIL_XU, mr.KIND, BAIL_LABEL.format(name=name))

    def ops(db):
        mr.need(fr.are_friends(db, sid, other), 'Chỉ bạn bè mới bảo lãnh được cho nhau.', 'not_friend', 403)
        gone(db)
        out = f'🤝 {display} đã bảo lãnh cho bạn ({_fmt(BAIL_XU)} xu). Bạn được về rồi, nhớ cảm ơn bạn ấy nha!'
        mr._notice(db, other, out)
        _inbox(db, other, out, None, 'jail_out')
        mine = f'🚔 Bạn đã bảo lãnh cho {name} ({_fmt(BAIL_XU)} xu). Bạn ấy được về rồi.'
        mr._notice(db, sid, mine)
        _inbox(db, sid, mine, None, 'jail_out')
    try:
        mr._mutate_retry(store, {other: free, sid: pay}, ops)
    except mr.MarriageError as x:
        if x.code == 'jail_gone':
            store.transaction(gone, 250)
        raise
    _push(store, other, f'🤝 {display} đã bảo lãnh cho bạn. Bạn được về rồi!')
    return dict(message=f'Đã bảo lãnh cho {name}: −{_fmt(BAIL_XU)} xu. Bạn ấy được về rồi.', changed=True)


ACTIONS = dict(jail_ask=ask, jail_bail=bail)


def requests(db, sid: str) -> list:
    """The friends who asked this player to bail them out (the Bạn bè screen): [{code, name, at, bail}], newest first."""
    from .social import pid_of
    mr = _mr()
    out, seen = [], set()
    try:
        rows = db.execute('SELECT ref,at FROM inbox WHERE pid=? AND kind=? AND at>? ORDER BY id DESC LIMIT 20',
                          (pid_of(sid), INBOX, mr.now() - ASK_DAYS * 86400)).fetchall()
    except Exception:  # noqa: BLE001 - a database without the social tables
        return out
    for r in rows:
        ref = str(r['ref'] or '')
        if not ref.startswith('jail:') or ref in seen:
            continue
        seen.add(ref)
        p = mr._find(db, ref[5:])
        if not p or not db.execute('SELECT 1 FROM friends WHERE sid=? AND friend=?', (sid, p['sid'])).fetchone():
            continue
        out.append(dict(code=ref[5:], name=mr._display(db, p['sid']), at=int(r['at']), bail=BAIL_XU))
    return out


def command_commit(db, sid: str, action: str, result: dict | None) -> None:
    """Storage, in the command's transaction: out of jail by its days, the friends' requests go."""
    if action != 'jail_end' or not ((result or {}).get('jail') or {}).get('free'):
        return
    r = db.execute('SELECT code FROM marriage_people WHERE sid=?', (sid,)).fetchone()
    if r:
        db.execute('DELETE FROM inbox WHERE kind=? AND ref=?', (INBOX, _ref(r['code'])))
