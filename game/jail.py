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
the sentence counts down by one, by two when all the day's công ích tasks are done. Owner 09/10: "bị giam cần lâu hơn
nhé, hiện tại đang rất nhanh, 1 ngày làm nhiều việc và đa dạng hơn": a jail day lasts at least DAY_MIN_S (20 minutes)
of real time (a countdown on the button) and has DAY_TASKS (8) tasks of the 14 TASKS, no repeats, chosen from
(sentence id, jail day). jail_task_start notes the task and the time, jail_task_done checks the answer against the
task's own seeded puzzle (puzzle()) and that at least TASK_MIN_S seconds went by (no spam): sweep every leaf pile,
dig → plant → water every hole, the right scoops of rice on every tray, paint every stained panel, the books in order,
hang each piece of laundry on the peg of its colour, mop each tile as many times as it is dirty, sort the trash into
its bin, pick only the yellow leaves, scrape → soap → rinse → rack every bowl, give each chicken the food it wants,
hit each nail as many times as it sticks out, count the storeroom's shelf into the ledger, fold each blanket as its
card says. The camp map (public/js/scenes/jail-place.js TASK_SPOT) has a corner for each.

Save (rollback-safe, tests/test_jail.py OldServer against 1.9.29, 1.9.32 and 1.9.33):
* journey['jail'] keeps the shape older servers check to the letter: {v, id, why, days, left, at, day, since, tasks,
  done, go, ask} with `tasks` the day's TASKS_PER_DAY (3) of OLD_TASK_IDS (_pick, as before) and `done` / `go` their
  mirror: an older server sees a day of its own three tasks.
* journey['jail2'] {v, id, day, tasks, done, go, old} (optional; KEY2) holds the day as played here: the DAY_TASKS
  tasks (the three above among them), what is done, the task going on. Older servers keep it untouched and ignore it.
* A day this server did not start (no jail2, or one of another sentence or day: a day begun or ended on an older
  server) is adopted as it is, by its old rules to the end of that day: its three tasks (what is done and going on
  carried over), OLD_DAY_MIN_S and OLD_TASK_MIN_S, the old puzzle sizes. The next day starts on the new rules.
  Rolled back mid-day, the older server carries on with the day's three tasks and its own timings; coming back, the
  day of jail2 picks up what the older server did there.
* settle() writes the adopted / merged jail2 on every command and drops a jail2 left without a sentence.

Bail (game/marriage.py act → ACTIONS: POST /api/marriage/jail_ask, /api/marriage/jail_bail): the jailed player asks
their friends (one social inbox row of kind 'jail' and the Bạn bè notice each, ASK_GAP_S apart); a FRIEND pays BAIL_XU
from their own wallet (a Sổ ví row), and the jailed save is released at once: both saves in one transaction under
their revision guards (marriage._mutate). Not yourself, not a non-friend, not with a short wallet, not someone already
out (so once per sentence).

Nobody is stuck: past days × SAFE_S real seconds since the arrest the sentence is over by itself (active()), and
MNL_JAIL_OFF=1 releases everybody and jails nobody (settle() drops the block on the next command; tests/__init__.py
sets it, tests/test_jail.py turns it on).

Both blocks (above) are optional and absent when free; they sit in the journey, which keeps new optional blocks, so
older servers load the save (tests/test_jail.py OldServer). The bail requests are rows of the social inbox.

The mark (table jail_marks, game/pg_schema.py SCHEMA_VERSION 33: sid, until): one tiny row per jailed save, so the
live server (live/protocol.py) and the light HTTP routes (server.py) tell a free player from one primary-key lookup
instead of reading the save (saves run to megabytes). It follows the save in the save's own transaction
(mark_commit(): storage commands, marriage._mutate such as the bail): upserted while jailed after a write (until =
the safety release; a sentence begun on an older build gets its mark at its next command here), deleted when a
sentence block went (served, the safety release, MNL_JAIL_OFF, a bail). No row: free. A row whose until is past: free. A row: the save is read to
confirm, at most once per MARK_CHECK_S, and a stale row (an older server let the player out) is deleted. Older builds
ignore the table; nothing about it is in the save.
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
TASKS_PER_DAY = 3              # journey['jail'].tasks: the older servers' view of the day (they check exactly 3)
DAY_TASKS = 8                  # the day's công ích here (journey['jail2'].tasks); all done: the day counts two
TASK_MIN_S = 45                # a công ích task takes at least this long between start and done
DAY_MIN_S = 1200               # a jail day lasts at least this long (real seconds) before "Hết ngày"
OLD_TASK_MIN_S = 15            # a day begun on an older server keeps its rules to its end (adopted)
OLD_DAY_MIN_S = 120
SAFE_S = 86400                 # the safety release: past days × SAFE_S real seconds since the arrest
ASK_GAP_S = 600                # one bail request to the friends every ten minutes at most
ASK_MAX = 60                   # friends asked at most (the newest friendships first)
ASK_DAYS = 4                   # a request older than this is not shown any more
WHY = ('bm', 'cop')
WHY_TEXT = dict(bm='Đánh bạc ở chợ đen', cop='Tố cáo sai sự thật')
KEYS = {'v', 'id', 'why', 'days', 'left', 'at', 'day', 'since', 'tasks', 'done', 'go', 'ask'}
KEY2 = 'jail2'
VERSION2 = 1
KEYS2 = {'v', 'id', 'day', 'tasks', 'done', 'go', 'old'}
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
    'laundry': dict(emoji='👕', name='Phơi đồ', hint='Chọn một món đồ rồi kẹp nó lên cái kẹp cùng màu.'),
    'mop': dict(emoji='🧽', name='Lau sàn buồng giam', hint='Ô sàn bẩn mấy vệt thì lau bấy nhiêu lần, đừng lau dư.'),
    'trash': dict(emoji='🗑️', name='Phân loại rác', hint='Bỏ mỗi món vào đúng thùng: giấy, nhựa hay rác hữu cơ.'),
    'veg': dict(emoji='🥬', name='Nhặt rau muống', hint='Chỉ ngắt những lá vàng, giữ lại lá xanh.'),
    'dishes': dict(emoji='🍜', name='Rửa chén bát', hint='Mỗi cái chén: cạo thức ăn, rửa xà phòng, tráng nước rồi úp lên giá.'),
    'chicken': dict(emoji='🐔', name='Cho gà ăn', hint='Con gà nghĩ tới món gì thì rắc đúng món đó.'),
    'fix': dict(emoji='🔨', name='Sửa ghế gãy', hint='Đinh nhô lên mấy nấc thì gõ bấy nhiêu cái, gõ dư là cong đinh.'),
    'ledger': dict(emoji='📒', name='Kiểm kho', hint='Đếm từng loại đồ trên kệ rồi ghi đúng số vào sổ.'),
    'fold': dict(emoji='🛏️', name='Gấp chăn màn', hint='Gấp từng tấm chăn theo đúng thứ tự trên thẻ hướng dẫn.'),
}
TASK_IDS = tuple(TASKS)
OLD_TASK_IDS = ('sweep', 'plant', 'rice', 'paint', 'books')   # the only tasks older servers know (journey['jail'])
PLANT_STEPS = ('dig', 'seed', 'water')
DISH_STEPS = ('scrape', 'soap', 'rinse', 'rack')
COLORS = ('do', 'cam', 'vang', 'la', 'duong', 'tim', 'hong', 'nau')             # 👕 the pegs and the clothes
CLOTHES = ('ao', 'quan', 'khan', 'vo', 'mu', 'ao_khoac', 'yem')
TRASH = {'bao_cu': 'giay', 'hop_giay': 'giay', 'vo_cu': 'giay', 'ly_giay': 'giay', 'thung_carton': 'giay',
         'chai_nhua': 'nhua', 'tui_ni_long': 'nhua', 'hop_xop': 'nhua', 'ong_hut': 'nhua', 'nap_chai': 'nhua',
         'vo_chuoi': 'huu_co', 'xuong_ca': 'huu_co', 'la_kho': 'huu_co', 'com_thua': 'huu_co', 'vo_trung': 'huu_co'}
BINS = ('giay', 'nhua', 'huu_co')
FEED = ('thoc', 'ngo', 'rau')                  # 🐔 what a chicken may want
STOCK = ('xa_phong', 'khan', 'ban_chai', 'chen', 'dep', 'giay_ve_sinh')       # 📒 the storeroom shelf
FOLDS = ('trai', 'phai', 'tren', 'duoi')       # 🛏️ fold the left / right / top / bottom edge in

MARK_CHECK_S = 60.0            # a marked player's save is read to confirm the mark at most this often (marked())
MARK_GET = 'SELECT until FROM jail_marks WHERE sid=?'
MARK_SAVE = ("SELECT CASE WHEN left(state, 1) = '{' AND strpos(state, '\"jail\"') > 0 "
             "THEN state::json #>> '{journey,jail}' END AS j FROM sessions WHERE sid=?")

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
    """journey['jail'].tasks: TASKS_PER_DAY of the old tasks, fixed by (sentence, jail day) (as on older servers)."""
    return random.Random(f'jail|{sid}|{day}').sample(list(OLD_TASK_IDS), TASKS_PER_DAY)


def _pick_day(sid: str, day: int) -> list:
    """The day's DAY_TASKS of TASKS, no repeats, fixed by (sentence, jail day); the three of _pick among them."""
    r = random.Random(f'jail2|{sid}|{day}')
    old = _pick(sid, day)
    out = old + r.sample([t for t in TASK_IDS if t not in old], DAY_TASKS - len(old))
    r.shuffle(out)
    return out


def _cells(r: random.Random, n: int, lo: int, hi: int) -> list:
    """lo..hi distinct cells of n, in a random order."""
    return r.sample(range(n), r.randint(lo, hi))


def puzzle(sid: str, day: int, task: str, old: bool = False) -> dict:
    """A task's seeded layout: what the client draws and what the answer is checked against. `old`: a day adopted
    from an older server keeps that server's sizes (the same layouts, so an answer means the same on both)."""
    r = random.Random(f'jail|{sid}|{day}|{task}')
    if task == 'sweep':
        if old:
            n = r.randint(6, 8)
            spots = []
            while len(spots) < n:   # a 4 × 3 yard grid, one pile a cell
                c = r.randrange(12)
                if c not in spots:
                    spots.append(c)
            return dict(piles=spots)
        return dict(cells=16, piles=_cells(r, 16, 10, 12))   # a 4 × 4 yard
    if task == 'plant':
        return dict(holes=4 if old else 6)
    if task == 'rice':
        return dict(want=[r.randint(1, 3) for _ in range(5)]) if old else dict(want=[r.randint(2, 4) for _ in range(8)])
    if task == 'paint':
        if old:
            return dict(cells=10, dirty=sorted(r.sample(range(10), r.randint(5, 7))))
        return dict(cells=15, dirty=sorted(r.sample(range(15), r.randint(10, 13))))
    if task == 'books':
        return dict(nums=r.sample(range(1, 100), 6 if old else 9))
    if task == 'laundry':
        colors = r.sample(COLORS, 7)
        kinds = [r.choice(CLOTHES) for _ in colors]
        items = [dict(k=k, c=c) for k, c in zip(kinds, colors)]
        r.shuffle(items)
        return dict(items=items, pegs=r.sample(colors, len(colors)))
    if task == 'mop':
        dirt = [0] * 12
        for c in _cells(r, 12, 8, 10):
            dirt[c] = r.randint(1, 3)
        return dict(dirt=dirt)
    if task == 'trash':
        items = [x for b in BINS for x in r.sample([k for k, v in TRASH.items() if v == b], 3)]
        items += [r.choice([k for k in TRASH if k not in items])]
        r.shuffle(items)
        return dict(items=items)
    if task == 'veg':
        return dict(leaves=20, yellow=sorted(_cells(r, 20, 9, 12)))
    if task == 'dishes':
        return dict(bowls=5)
    if task == 'chicken':
        want = [r.choice(FEED) for _ in range(7)]
        want[r.randrange(7)] = FEED[0]
        return dict(want=want)
    if task == 'fix':
        return dict(nails=[r.randint(1, 4) for _ in range(7)])
    if task == 'ledger':
        kinds = r.sample(STOCK, 4)
        pile = [k for k in kinds for _ in range(r.randint(2, 7))]
        r.shuffle(pile)
        return dict(kinds=kinds, pile=pile)
    if task == 'fold':
        return dict(cards=[r.sample(FOLDS, 4) for _ in range(3)])
    raise ValueError(task)


def _ints(got, n: int | None = None, lo: int = 0, hi: int = 99) -> bool:
    return isinstance(got, list) and (n is None or len(got) == n) and all(type(x) is int and lo <= x <= hi for x in got)


def _right(task: str, pz: dict, ans) -> bool:
    if not isinstance(ans, dict):
        return False
    if task == 'sweep':
        got = ans.get('swept')
        return _ints(got, None, 0, pz.get('cells', 12) - 1) and len(got) <= pz.get('cells', 12) \
            and sorted(got) == sorted(pz['piles']) and len(set(got)) == len(got)
    if task == 'plant':
        got = ans.get('steps')
        return isinstance(got, list) and len(got) == pz['holes'] and all(isinstance(x, list) and tuple(x) == PLANT_STEPS for x in got)
    if task == 'rice':
        got = ans.get('scoops')
        return _ints(got, len(pz['want'])) and got == pz['want']
    if task == 'paint':
        got = ans.get('cells')
        return _ints(got, None, 0, pz['cells'] - 1) and len(got) <= pz['cells'] \
            and len(set(got)) == len(got) and set(got) == set(pz['dirty'])
    if task == 'books':
        got = ans.get('order')
        nums = pz['nums']
        return _ints(got, len(nums), 0, len(nums) - 1) and len(set(got)) == len(got) and [nums[i] for i in got] == sorted(nums)
    if task == 'laundry':
        got = ans.get('hang')
        items, pegs = pz['items'], pz['pegs']
        return _ints(got, len(items), 0, len(pegs) - 1) and len(set(got)) == len(got) \
            and all(pegs[g] == it['c'] for g, it in zip(got, items))
    if task == 'mop':
        got = ans.get('wipes')
        return _ints(got, len(pz['dirt']), 0, 9) and got == pz['dirt']
    if task == 'trash':
        got = ans.get('bins')
        return isinstance(got, list) and len(got) == len(pz['items']) and all(isinstance(x, str) for x in got) \
            and got == [TRASH[x] for x in pz['items']]
    if task == 'veg':
        got = ans.get('picked')
        return _ints(got, None, 0, pz['leaves'] - 1) and len(set(got)) == len(got) and set(got) == set(pz['yellow'])
    if task == 'dishes':
        got = ans.get('steps')
        return isinstance(got, list) and len(got) == pz['bowls'] and all(isinstance(x, list) and tuple(x) == DISH_STEPS for x in got)
    if task == 'chicken':
        got = ans.get('fed')
        return isinstance(got, list) and all(isinstance(x, str) for x in got) and got == pz['want']
    if task == 'fix':
        got = ans.get('hits')
        return _ints(got, len(pz['nails']), 0, 9) and got == pz['nails']
    if task == 'ledger':
        got = ans.get('counts')
        want = {k: pz['pile'].count(k) for k in pz['kinds']}
        return isinstance(got, dict) and set(got) == set(want) and all(type(got[k]) is int and got[k] == n for k, n in want.items())
    if task == 'fold':
        got = ans.get('folds')
        return isinstance(got, list) and len(got) == len(pz['cards']) \
            and all(isinstance(x, list) and all(isinstance(y, str) for y in x) and x == c for x, c in zip(got, pz['cards']))
    return False


def _new_day(sid: str, day: int) -> dict:
    """journey['jail2'] for a day this server starts: the new rules."""
    return dict(v=VERSION2, id=sid, day=day, tasks=_pick_day(sid, day), done=[], go=None, old=False)


def day_of(j: dict) -> dict | None:
    """The day as it is played here (pure): journey['jail2'] when it is this sentence's day, with what an older server
    did meanwhile carried over; else that day adopted from journey['jail'] by its old rules. None when free."""
    b = block(j)
    if not b:
        return None
    d = j.get(KEY2)
    if isinstance(d, dict) and d.get('id') == b['id'] and d.get('day') == b['day'] and isinstance(d.get('tasks'), list):
        done = list(d['done']) + [x for x in b['done'] if x in d['tasks'] and x not in d['done']]
        go = d['go']
        if not go and isinstance(b['go'], dict) and b['go'].get('t') in d['tasks']:   # started there meanwhile
            go = dict(b['go'])
        if go and go.get('t') in done:
            go = None
        return dict(d, done=done, go=go)
    return dict(v=VERSION2, id=b['id'], day=b['day'], tasks=list(b['tasks']), done=list(b['done']),
                go=dict(b['go']) if isinstance(b['go'], dict) else None, old=True)


def _rules(d: dict) -> tuple[int, int]:
    """(task min, day min) seconds of a day."""
    return (OLD_TASK_MIN_S, OLD_DAY_MIN_S) if d['old'] else (TASK_MIN_S, DAY_MIN_S)


def _mirror(b: dict, d: dict) -> None:
    """journey['jail'] follows the day for older servers: its three tasks' done and going on."""
    b['done'] = [x for x in b['tasks'] if x in d['done']]
    go = d['go']
    b['go'] = dict(go) if go and go['t'] in b['tasks'] else None


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
    j[KEY2] = _new_day(sid, 1)
    return int(days)


def release(j: dict) -> None:
    j.pop(KEY, None)
    j.pop(KEY2, None)


def settle(s: dict, t: float | None = None) -> bool:
    """Every command: a block whose time is over (the safety release) or the switch: gone (True when it went). Inside:
    the day as played here is written (adopted, or merged with an older server's work); a jail2 alone goes."""
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict):
        return False
    if KEY not in j:
        j.pop(KEY2, None)
        return False
    if not active(j, t):
        release(j)
        return True
    if block(j):
        j[KEY2] = day_of(j)
    return False


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


# ---------------------------------------------------------------- the mark (jail_marks)
def mark_until(j, t: float | None = None) -> int | None:
    """The safety release time of a sentence going on (the mark's `until`), None when free."""
    if not active(j, t):
        return None
    b = j[KEY]
    return int(b['at']) + int(b['days']) * SAFE_S


def mark_commit(db, sid: str, before, after, t: float | None = None) -> None:
    """In the save's own transaction (storage commands, the bail): the mark follows the save. `before` may be
    storage._commit_before's projection (journey.jail: a flag)."""
    ja = after.get('journey') if isinstance(after, dict) else None
    u = mark_until(ja, t)
    if u is not None:
        db.execute('INSERT INTO jail_marks(sid,until) VALUES(?,?) ON CONFLICT(sid) DO UPDATE SET until=excluded.until '
                   'WHERE jail_marks.until<>excluded.until', (sid, u))
        return
    jb = before.get('journey') if isinstance(before, dict) else None
    if isinstance(jb, dict) and jb.get(KEY):
        db.execute('DELETE FROM jail_marks WHERE sid=?', (sid,))


def marked_token(store, token: str) -> bool:
    """server.py, a light route (the save not read): jailed now, from the mark (marked())."""
    with store.connect() as db:
        sid = store._resolve(db, store.digest(token))[0]
        return marked(db, sid)


def unmark(db, sid: str) -> None:
    db.execute('DELETE FROM jail_marks WHERE sid=?', (sid,))


MARK_STALE = 'DELETE FROM jail_marks WHERE sid=? AND until=?'


def mark_answer(u: float | None, seen: dict | None, t: float) -> bool | None:
    """The mark's `until` read (None: no row): free (False), the memo's answer, or None: read the save (MARK_SAVE)."""
    if u is None or u <= t:
        return False
    if seen is not None and seen.get('until') == u and t - seen.get('at', 0) < MARK_CHECK_S:
        return seen['inside']
    return None


def mark_note(seen: dict | None, u: float, t: float, inside: bool) -> None:
    if seen is not None:
        seen.update(until=u, at=t, inside=inside)


def marked(db, sid: str, seen: dict | None = None, t: float | None = None) -> bool:
    """Jailed now, from the mark: no row (the common case) or a row past its until: free, one primary-key read. A row:
    the save confirms it, at most once per MARK_CHECK_S (`seen`: the caller's per-player memo); a stale row (an older
    server let the player out) goes. Synchronous (game.db, autocommit); live/protocol.py does the same with await."""
    if off() or not sid:
        return False
    t = now() if t is None else t
    row = db.execute(MARK_GET, (sid,)).fetchone()
    u = float(row['until']) if row else None
    inside = mark_answer(u, seen, t)
    if inside is None:
        inside = from_save(db.execute(MARK_SAVE, (sid,)).fetchone(), t)
        if not inside:
            db.execute(MARK_STALE, (sid, u))
        mark_note(seen, u, t, inside)
    return inside


def from_save(row, t: float | None = None) -> bool:
    """A MARK_SAVE row: is that save in the camp now."""
    import json
    try:
        b = json.loads(row['j']) if row and row['j'] else None
    except (TypeError, ValueError):
        b = None
    return active({KEY: b}, t) if isinstance(b, dict) else False


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
    b, d = j[KEY], j[KEY2]
    _need(set(p) <= {'day'} and p.get('day', b['day']) == b['day'], 'Ngày trong trại này đã qua rồi. Tải lại trang nhé.', 'jail_stale')
    wait = b['since'] + _rules(d)[1] - int(t)
    _need(wait <= 0, f'Còn {wait // 60}:{wait % 60:02d} nữa mới hết ngày trong trại. Làm công ích cho nhanh nha.', 'jail_wait')
    full = len(d['done']) >= len(d['tasks'])
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
        j[KEY2] = _new_day(b['id'], b['day'])
        result['message'] = f'Còn {b["left"]} ngày trong trại. Sáng nay có việc công ích mới.'
        result['jail'] = dict(free=False, left=b['left'])
    if j['wallet'] < 0:
        notes.append(f'Ví đang nợ {-j["wallet"]} xu. Ra trại rồi rút tiền từ nơi làm việc để trả nhé.')
    result['effects'].extend(notes)


def _task_start(s: dict, p: dict, t: float, result: dict) -> None:
    j = s['journey']
    b, d = j[KEY], j[KEY2]
    task = p.get('task')
    _need(set(p) == {'task'} and task in d['tasks'], 'Việc công ích này không có trong hôm nay.')
    _need(task not in d['done'], 'Việc này làm xong rồi.', 'already_done')
    if not (isinstance(d['go'], dict) and d['go'].get('t') == task):
        d['go'] = dict(t=task, at=int(t))
    _mirror(b, d)
    result['message'] = ''
    result['jail'] = dict(task=task, pz=puzzle(b['id'], b['day'], task, d['old']), ready=d['go']['at'] + _rules(d)[0])


def _task_done(s: dict, p: dict, t: float, result: dict) -> None:
    j = s['journey']
    b, d = j[KEY], j[KEY2]
    task = p.get('task')
    _need(set(p) == {'task', 'ans'} and task in d['tasks'], 'Việc công ích này không có trong hôm nay.')
    if task in d['done']:   # a retry, another tab
        result.update(message='', jail=dict(task=task, ok=True, again=True))
        return
    go = d['go']
    _need(isinstance(go, dict) and go.get('t') == task, 'Bắt đầu việc này trước đã nhé.', 'jail_not_started')
    _need(int(t) - go['at'] >= _rules(d)[0], 'Làm từ từ cho kỹ nha, cán bộ đang xem đó.', 'jail_fast')
    _need(_right(task, puzzle(b['id'], b['day'], task, d['old']), p.get('ans')), 'Chưa xong đâu, làm lại cho đúng nha.', 'jail_wrong')
    d['done'].append(task)
    d['go'] = None
    _mirror(b, d)
    all_done = len(d['done']) >= len(d['tasks'])
    left = len(d['tasks']) - len(d['done'])
    result['message'] = (f'{TASKS[task]["emoji"]} Xong: {TASKS[task]["name"].lower()}.'
                         + (' Đủ công ích hôm nay: hết ngày này được tính hai ngày.' if all_done and b['left'] > 1
                            else f' Còn {left} việc nữa hôm nay.' if left else ''))
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
    d = day_of(j)
    task_min, day_min = _rules(d)
    go = d['go'] if isinstance(d['go'], dict) else None
    tasks = [dict(id=x, **TASKS[x], done=x in d['done'], pz=puzzle(b['id'], b['day'], x, d['old'])) for x in d['tasks']]
    return dict(id=b['id'], why=b['why'], why_text=WHY_TEXT[b['why']], days=b['days'], left=b['left'], day=b['day'],
                tasks=tasks, go=go['t'] if go else None, task_ready=go['at'] + task_min if go else 0,
                ready=b['since'] + day_min, ask_next=b['ask'] + ASK_GAP_S if b['ask'] else 0, bail=BAIL_XU, now=int(t))


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict):
        return
    from .engine import need, integer
    bad = 'Dữ liệu trại tạm giữ không hợp lệ.'
    if KEY2 in j:   # the day as played here (alone after an older server let the player out: dropped by settle())
        d = j[KEY2]
        need(isinstance(d, dict) and set(d) == KEYS2 and d['v'] == VERSION2 and type(d['old']) is bool, bad, 'invalid_save')
        need(isinstance(d['id'], str) and 1 <= len(d['id']) <= 16 and d['id'].isalnum(), bad, 'invalid_save')
        integer(d['day'], 1, 60)
        need(isinstance(d['tasks'], list) and 1 <= len(d['tasks']) <= DAY_TASKS and len(set(d['tasks'])) == len(d['tasks'])
             and set(d['tasks']) <= set(TASK_IDS), bad, 'invalid_save')
        need(isinstance(d['done'], list) and len(set(d['done'])) == len(d['done']) and set(d['done']) <= set(d['tasks']), bad, 'invalid_save')
        go = d['go']
        need(go is None or (isinstance(go, dict) and set(go) == {'t', 'at'} and go['t'] in d['tasks'] and type(go['at']) is int
                            and 0 <= go['at'] <= 2 ** 40), bad, 'invalid_save')
    if KEY not in j:
        return
    b = j[KEY]
    need(isinstance(b, dict) and set(b) == KEYS and b['v'] == VERSION and b['why'] in WHY, bad, 'invalid_save')
    need(isinstance(b['id'], str) and 1 <= len(b['id']) <= 16 and b['id'].isalnum(), bad, 'invalid_save')
    integer(b['days'], 1, 30)
    integer(b['left'], 0, b['days'])
    integer(b['day'], 1, 60)
    for k in ('at', 'since', 'ask'):
        integer(b[k], 0, 2 ** 40)
    need(isinstance(b['tasks'], list) and len(b['tasks']) == TASKS_PER_DAY and len(set(b['tasks'])) == TASKS_PER_DAY
         and set(b['tasks']) <= set(OLD_TASK_IDS), bad, 'invalid_save')
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
        gone(db)   # the mark goes with the save (marriage._mutate → mark_commit)
        out = f'🤝 {display} đã bảo lãnh cho bạn ({_fmt(BAIL_XU)} xu). Bạn được về rồi, nhớ cảm ơn bạn ấy nha!'
        mr._notice(db, other, out)
        _inbox(db, other, out, None, 'jail_out')
        mine = f'🚔 Bạn đã bảo lãnh cho {name} ({_fmt(BAIL_XU)} xu). Bạn ấy được về rồi.'
        mr._notice(db, sid, mine)
        _inbox(db, sid, mine, None, 'jail_out')
    try:
        mr._mutate_retry(store, {other: free, sid: pay}, ops)
    except mr.MarriageError as x:
        if x.code == 'jail_gone':   # already out (served, or let out by an older server): a mark left goes too
            store.transaction(lambda db: (gone(db), unmark(db, other)), 250)
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
