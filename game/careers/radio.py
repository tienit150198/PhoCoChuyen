"""📻 Đài phát thanh Sóng Mây: a salaried shift at the ward radio station, as Phát thanh viên (news) or, after probation, DJ.

🎙️ Phát thanh viên. Everyone starts here: the ward bulletin (which items may be read, in which order, how long it runs, a
correction a minute before air), the sponsor's spot (only the newest script the editor signed, cut the claims the station
never reads, its length, the sponsor's last-minute demand) and the listeners' wishes (which ones may not be read, in the order
they came, a name written without its tone marks, a slip on air). After PROBATION good shifts the player may also be the
🎧 DJ of the evening show: a caller's song nobody has heard of, a song the station may not air, the talk-over that ends on the
hour, callers who swear or sell things on air, the show's running order and a guest who turns up late or drunk.

Every shift opens with the studio check (an ordered checklist, required before the first step on air). On some days from day 2
the power goes out after the first finished job ("mất điện giữa sóng"): the outage checklist blocks the work until it is done;
OUTAGE_SLIPS wrong steps on it leave the air dead too long (a 2★ review). A job is a pure function of (day, slot, role) like the
banquet's, the answers stay on the server and a wrong step stays open to fix (quality −WRONG_COST, the bonus follows it).

Player-to-player services (📢 a shop's ad and 🎵 a song with a message on the town ticker) live in game/radio_station.py; this
module is the career only and keeps no state outside its own career data.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from . import kit
from . import radio_content as rc
from .. import consequences as cq

ID = 'radio'
GEN = 1
PEOPLE = rc.PEOPLE
ROLES = tuple(rc.ROLES)
JOB_IDS = tuple(rc.JOBS)
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('rd_step', 'rd_shift')
FREE = ('rd_intro', 'rd_role')
NO_TICK = ('rd_intro', 'rd_role', 'rd_desk')
LINES = 24
LETTERS = 'abcdefgh'


# ---------------------------------------------------------------- task building
def _step(job, name, typ, title, evidence, options=None, unit=''):
    st = dict(id=f'{job}.{name}', type=typ, title=title, evidence=evidence)
    if options is not None:
        st['options'] = options
    if unit:
        st['unit'] = unit
    return st


def _lettered(r, rows):
    """Shuffle (key, label) rows and give them neutral ids a, b, c…: an option's id never says whether it is the answer.
    Returns (options, {key: letter})."""
    rows = list(rows)
    r.shuffle(rows)
    opts = [dict(id=LETTERS[i], label=label) for i, (_, label) in enumerate(rows)]
    return opts, {k: LETTERS[i] for i, (k, _) in enumerate(rows)}


def _scenario(r, job, name, title, rows):
    """A choice step from one (situation, right, wrongs) row: (step, the right letter)."""
    text, right, wrongs = r.choice(rows)
    opts, ids = _lettered(r, [('right', right)] + [(f'w{i}', w) for i, w in enumerate(wrongs)])
    return _step(job, name, 'choice', title, text, opts), ids['right']


def mmss(sec: int) -> str:
    return f'{sec // 60}:{sec % 60:02d}'


def _bulletin(r, day, slot):
    picked = {k: r.choice(rc.NEWS[k]) for k in rc.READ_ORDER}
    junk = [r.choice(rc.NEWS[k]) for k in r.choice((('rumor',), ('ad',), ('rumor', 'ad')))]
    opts, ids = _lettered(r, [(x[0], x[1]) for x in list(picked.values()) + junk])
    keep = [picked[k][0] for k in rc.READ_ORDER]
    order_opts, order_ids = _lettered(r, [(picked[k][0], picked[k][1]) for k in rc.READ_ORDER])
    j, p, s = r.choice(rc.JINGLE), r.choice(rc.PER_ITEM), r.choice(rc.SIGN_OFF)
    tonight = {x[0] for x in picked.values()}   # the last-minute trouble is about an item this bulletin carries
    fix, fix_key = _scenario(r, 'bulletin', 'fix', 'Xử lý chuyện phút chót', [x[1:] for x in rc.BULLETIN_FIX if x[0] is None or x[0] in tonight])
    steps = [
        _step('bulletin', 'pick', 'multi', 'Chọn những tin được đọc',
              f'Bà Tư và chị Hoa gom {len(opts)} mẩu tin. Bản tin phường chỉ đọc tin của phường đã kiểm chứng.', opts),
        _step('bulletin', 'order', 'order', 'Xếp thứ tự đọc', 'Bấm lần lượt các tin theo đúng thứ tự đọc của đài.', order_opts),
        _step('bulletin', 'secs', 'number', 'Tính thời lượng bản tin',
              f'Nhạc hiệu {j} giây, mỗi tin đọc khoảng {p} giây, lời chào cuối {s} giây. Bản tin {len(keep)} tin dài bao nhiêu giây?', unit='giây'),
        fix,
    ]
    key = {'bulletin.pick': sorted(ids[k] for k in keep), 'bulletin.order': [order_ids[k] for k in keep],
           'bulletin.secs': j + len(keep) * p + s, 'bulletin.fix': fix_key}
    brief = dict(steps=steps)
    return brief, key, 'Bản tin phường', 'Chị Hoa đặt xấp tin lên bàn: “Mười phút nữa lên sóng. Đọc tin nào, đọc trước tin nào, em tự lo.”', 6


def _spot(r, day, slot):
    sid, sponsor, product = r.choice(rc.SPONSORS)
    times = sorted(r.sample(('8:42', '9:05', '9:18', '9:31', '9:44', '9:52', '9:57'), 4), key=lambda t: (len(t), t))
    approved = [r.random() < 0.55 for _ in times]
    if r.random() < 0.7:
        approved[-1] = False          # the trap: the newest one came by text a minute ago, nobody signed it
    if not any(approved):
        approved[r.randrange(len(times) - 1)] = True
    rows = [(f'v{i}', f'Bản {i + 1} · gửi lúc {t} · ' + ('chị Hoa đã ký duyệt' if ok else 'gửi qua tin nhắn, chưa duyệt'))
            for i, (t, ok) in enumerate(zip(times, approved))]
    rows.append(('phone', 'Bản nhà tài trợ đọc qua điện thoại lúc 9:59, chưa có giấy'))   # any sponsor: never "ông" for bà Năm
    vopts, vids = _lettered(r, rows)
    latest = max(i for i, ok in enumerate(approved) if ok)
    good = r.sample(rc.SPOT_OK, 3)
    bad = r.sample(rc.SPOT_BAD, r.choice((1, 2)))
    lopts, lids = _lettered(r, [(f'ok{i}', x) for i, x in enumerate(good)] + [(f'bad{i}', x) for i, x in enumerate(bad)])
    words, rate, jingle = r.randint(48, 96), r.choice(rc.WORDS_PER_S), r.choice(rc.SPONSOR_JINGLE)
    demand, demand_key = _scenario(r, 'spot', 'demand', 'Yêu cầu phút chót của nhà tài trợ', rc.SPOT_DEMANDS)
    steps = [
        _step('spot', 'version', 'choice', 'Chọn đúng bản kịch bản',
              f'{sponsor} gửi tới {len(times)} bản kịch bản quảng cáo {product} trong buổi sáng, nhà tài trợ còn đọc thêm một bản qua điện thoại.', vopts),
        _step('spot', 'cut', 'multi', 'Gạch những câu không được đọc', f'Các câu trong bản duyệt của {sponsor}. Chọn mọi câu đài không đọc.', lopts),
        _step('spot', 'secs', 'number', 'Tính độ dài spot',
              f'Bản đọc còn {words} chữ. Đài đọc {rate} chữ mỗi giây (làm tròn lên), cộng {jingle} giây nhạc hiệu nhà tài trợ. Spot dài bao nhiêu giây?', unit='giây'),
        demand,
    ]
    key = {'spot.version': vids[f'v{latest}'], 'spot.cut': sorted(lids[f'bad{i}'] for i in range(len(bad))),
           'spot.secs': math.ceil(words / rate) + jingle, 'spot.demand': demand_key}
    brief = dict(sponsor=sponsor, steps=steps)
    return brief, key, f'Quảng cáo {sponsor}', f'Chín giờ năm mươi chín, {sponsor} lại gửi kịch bản mới. Chị Hoa dặn: “Chỉ đọc bản chị đã ký.”', rc.SPONSOR_NPC[sid]


def _wishes(r, day, slot):
    good = r.sample(rc.WISH_OK, 3)
    bad = r.sample(rc.WISH_BAD, r.choice((1, 2)))
    times = sorted(r.sample(rc.WISH_TIMES, len(good) + len(bad)))
    r.shuffle(times)
    at = {x[0]: t for x, t in zip(good + bad, times)}
    sopts, sids = _lettered(r, [(x[0], f'{at[x[0]]} · {x[1]}') for x in good + bad])
    ordered = sorted((x[0] for x in good), key=lambda k: at[k])
    oopts, oids = _lettered(r, [(x[0], f'{at[x[0]]} · {x[1]}') for x in good])
    raw, (right, w1, w2) = r.choice(rc.NAME_ASK)
    nopts, nids = _lettered(r, [('ask', 'Gọi lại người gửi hỏi đúng dấu rồi mới đọc'), ('w1', f'Đọc đại là “{right}”'),
                                ('w2', f'Đọc là “{w1}” cho nhanh'), ('w3', 'Đánh vần từng chữ không dấu trên sóng')])
    box = {x[0] for x in good}   # the slip is on a wish read tonight
    slip, slip_key = _scenario(r, 'wishes', 'slip', 'Lỡ đọc sai trên sóng', [x[1:] for x in rc.WISH_SLIPS if x[0] in box])
    steps = [
        _step('wishes', 'skip', 'multi', 'Chọn những lời KHÔNG được đọc', f'Hộp thư lời chúc tối nay có {len(sopts)} lời. Chọn mọi lời đài không đọc.', sopts),
        _step('wishes', 'order', 'order', 'Đọc theo giờ gửi tới', 'Bấm lần lượt các lời chúc theo thứ tự đài nhận được.', oopts),
        _step('wishes', 'name', 'choice', 'Tên viết không dấu', f'Một lời chúc gửi tới “{raw}”, viết không dấu, không ghi rõ tên nào.', nopts),
        slip,
    ]
    key = {'wishes.skip': sorted(sids[x[0]] for x in bad), 'wishes.order': [oids[k] for k in ordered], 'wishes.name': nids['ask'],
           'wishes.slip': slip_key}
    brief = dict(steps=steps)
    return brief, key, 'Lời chúc thính giả', 'Hộp thư lời chúc đầy ắp. Chị Hoa dặn: “Đọc cho đúng tên, đúng người, đừng để ai bị bêu lên sóng.”', 3


def _song(sid):
    return next(s for s in rc.SONGS if s[0] == sid)


def _request(r, day, slot):
    asked = sorted(rc.SONG_ASKS)[r.randrange(len(rc.SONG_ASKS))]
    song = _song(asked)
    others = r.sample([s for s in rc.SONGS if s[6] and s[0] != asked], 3)
    fopts, fids = _lettered(r, [(s[0], f'{s[1]} · {s[2]} · {s[3]} · {mmss(s[4])}') for s in [song] + others])
    rights, rights_key = _scenario(r, 'request', 'rights', 'Bài không được phát', rc.NO_AIR)
    left = r.choice(rc.SHOW_LEFT)
    odd, odd_key = _scenario(r, 'request', 'odd', 'Yêu cầu oái oăm', rc.REQUEST_ODD)
    caller = r.choice((3, 4, 5))
    steps = [
        _step('request', 'find', 'choice', 'Tìm đúng bài trong kho', f'{rc.PEOPLE[caller][0]} gọi vào: “{rc.SONG_ASKS[asked]}.”', fopts),
        rights,
        _step('request', 'talk', 'number', 'Canh lời dẫn cho kịp bản tin',
              f'Còn {mmss(left)} tới bản tin đầu giờ. Bài “{song[1]}” dài {mmss(song[4])}. Lời dẫn tối đa bao nhiêu giây để bài hết đúng lúc vào bản tin?',
              unit='giây'),
        odd,
    ]
    key = {'request.find': fids[asked], 'request.rights': rights_key, 'request.talk': left - song[4], 'request.odd': odd_key}
    brief = dict(steps=steps)
    return brief, key, 'Khách gọi xin bài', 'Đường dây nóng của chương trình “Đêm Sóng Mây” sáng đèn liên tục. Ai cũng xin bài, bài nào cũng lạ.', caller


def _callin(r, day, slot):
    first, first_key = _scenario(r, 'callin', 'first', 'Cuộc gọi đầu tiên', rc.CALL_FIRST)
    gripe, gripe_key = _scenario(r, 'callin', 'gripe', 'Thính giả chê', rc.CALL_GRIPES)
    off, off_key = _scenario(r, 'callin', 'off', 'Cuộc gọi lạc đề', rc.CALL_OFFTOPIC)
    lopts, lids = _lettered(r, [(x[0], x[1]) for x in rc.CALL_LOG])
    steps = [first, gripe, off,
             _step('callin', 'log', 'multi', 'Ghi sổ cuộc gọi', 'Cuối giờ, ghi sổ các cuộc gọi vào sóng. Chọn mọi việc phải làm.', lopts)]
    key = {'callin.first': first_key, 'callin.gripe': gripe_key, 'callin.off': off_key,
           'callin.log': sorted(lids[x[0]] for x in rc.CALL_LOG if x[2])}
    brief = dict(steps=steps)
    return brief, key, 'Thính giả gọi vào sóng', 'Chương trình “Alo Sóng Mây” mở đường dây cho thính giả. Đài trễ 7 giây, tay bạn đặt sẵn trên nút XÓA TRỄ.', 5


def _playlist(r, day, slot):
    fine = r.sample([s for s in rc.SONGS if s[6]], 4)
    banned = r.sample([s for s in rc.SONGS if not s[6]], r.choice((1, 2)))
    dopts, dids = _lettered(r, [(s[0], f'{s[1]} · {s[2]} · {mmss(s[4])}') for s in fine + banned])
    sopts, sids = _lettered(r, rc.SEGMENTS)
    total = r.choice(rc.SHOW_MIN)
    three = fine[:3]
    guest, guest_key = _scenario(r, 'playlist', 'guest', 'Khách mời oái oăm', rc.GUEST_ODD)
    listing = ', '.join(f'“{s[1]}” {mmss(s[4])}' for s in three)
    steps = [
        _step('playlist', 'drop', 'multi', 'Bỏ những bài không được phát', 'Danh sách bài chị Hoa gửi cho chương trình tối nay. Chọn mọi bài phải bỏ.', dopts),
        _step('playlist', 'order', 'order', 'Xếp thứ tự chương trình', 'Bấm lần lượt các phần theo đúng khung chương trình của đài.', sopts),
        _step('playlist', 'fill', 'number', 'Tính thời gian lời dẫn',
              f'Chương trình {total} phút. Ba bài đã chốt: {listing}; hai lần quảng cáo, mỗi lần 30 giây. Còn bao nhiêu giây cho lời dẫn?', unit='giây'),
        guest,
    ]
    key = {'playlist.drop': sorted(dids[s[0]] for s in banned), 'playlist.order': [sids[k] for k, _ in rc.SEGMENTS],
           'playlist.fill': total * 60 - sum(s[4] for s in three) - rc.ADS_S, 'playlist.guest': guest_key}
    brief = dict(steps=steps)
    return brief, key, 'Xếp chương trình ca nhạc', 'Chị Hoa giao: “Tối nay em dựng chương trình. Bài nào được phát, phần nào trước, lời dẫn bao lâu, em tính.”', 0


BUILD = dict(bulletin=_bulletin, spot=_spot, wishes=_wishes, request=_request, callin=_callin, playlist=_playlist)


def job_of(day: int, slot: int, role: str) -> str:
    """The job of (day, slot) for `role`: each role rotates through its own jobs."""
    jobs = rc.ROLE_JOBS[role]
    return jobs[(day - 1 + slot) % len(jobs)]


def brief(day: int, slot: int, role: str) -> tuple:
    """(brief with its steps, steps, answer key, title, opening, npc index, job) of (day, slot) for `role`. Pure."""
    job = job_of(day, slot, role)
    b, key, title, opening, npc = BUILD[job](kit.rng(ID, job, day, slot), day, slot)
    return b, b['steps'], key, title, opening, npc, job


def make_task(day: int, slot: int, serial: int) -> dict:
    """The stored slip is the same for every role (the role is chosen when the shift starts): its brief is built on read."""
    return kit.base_task(ID, day, slot, serial, rc.MANAGER, 'Phiếu việc của đài', 'Chị Hoa đưa phiếu việc của ca.',
                         gen=GEN, kind='shift', needs={}, _key={}, role='news',
                         at=0, work={}, errors=[], wrong=0, quality=100, paid=0, lines=[], stage='work')


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def _role(t: dict) -> str:
    return t.get('role') if t.get('role') in ROLES else 'news'


def _active(t: dict) -> tuple:
    b, steps, key, *_ = brief(t['day'], _slot(t), _role(t))
    return b, steps, key


def _job(t: dict) -> str:
    return job_of(t['day'], _slot(t), _role(t))


def _quality(wrong: int) -> int:
    return max(rc.QUALITY_FLOOR, 100 - rc.WRONG_COST * wrong)


HOW = {
    'bulletin.secs': 'Nhạc hiệu cộng số tin nhân giây mỗi tin, cộng lời chào cuối.',
    'spot.secs': 'Lấy số chữ chia tốc độ đọc, có lẻ thì làm tròn lên, rồi cộng giây nhạc hiệu.',
    'request.talk': 'Đổi cả hai ra giây (phút × 60 + giây) rồi lấy thời gian còn lại trừ độ dài bài.',
    'playlist.fill': 'Số phút × 60, trừ tổng giây của ba bài, trừ 60 giây quảng cáo.',
}


def _bonus(t: dict) -> int:
    return max(3, round(rc.BONUS[_job(t)] * t['quality'] / 100))


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ---------------------------------------------------------------- shift checklists (pure by day)
def shift_steps(day: int, part: str) -> tuple:
    """The studio check ('open') or the outage drill ('outage') of `day`: (steps, key). Pure."""
    r = kit.rng(ID, 'shift', part, day)
    if part == 'open':
        opts, ids = _lettered(r, rc.OPEN_STEPS)
        return ([_step('open', 'studio', 'order', 'Kiểm phòng thu đầu ca',
                       'Bấm các việc theo đúng thứ tự dán cạnh bàn trộn âm. Chưa kiểm xong thì chưa mở mic.', opts)],
                {'open.studio': [ids[k] for k, _ in rc.OPEN_STEPS]})
    opts, ids = _lettered(r, rc.OUTAGE_STEPS)
    return ([_step('outage', 'drill', 'order', 'Mất điện giữa sóng', r.choice(rc.OUTAGE_CAUSES) + ' Bấm các việc theo đúng thứ tự sổ sự cố.', opts)],
            {'outage.drill': [ids[k] for k, _ in rc.OUTAGE_STEPS]})


def outage_day(day: int) -> bool:
    return day >= 2 and kit.rng(ID, 'outage', day).random() < rc.OUTAGE_CHANCE


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0, counted=0, aired=0, news_good=0, open_at=0, out=0, out_at=0, out_slips=0, slips=0)


def initial() -> dict:
    return dict(intro=False, role='news', promoted=False, today=_today(0), last_active_day=0, last_news_day=0,
                stats=dict(jobs=0, good=0, active_days=0, bonus=0, news_days=0, outages=0, restored=0, dead_air=0,
                           roles={k: 0 for k in ROLES}),
                desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _open_done(today: dict) -> bool:
    return today['open_at'] >= len(shift_steps(today['day'], 'open')[0])


def _out_done(today: dict) -> bool:
    return today['out_at'] >= len(shift_steps(today['day'], 'outage')[0])


# ---------------------------------------------------------------- actions
def _value(st: dict, value):
    typ = st['type']
    if typ == 'choice':
        return kit.one_of(value, [o['id'] for o in st['options']])
    if typ == 'number':
        return kit.integer(value, 0, 100000)
    ids = [o['id'] for o in st['options']]
    got = kit.id_list(value, ids, len(ids))
    if typ == 'order':
        kit.need(len(got) == len(ids), 'Xếp đủ mọi việc theo thứ tự nhé.')
        return list(got)
    return sorted(got)


def _restamp(c: dict, role: str) -> int:
    """Today's unread slips follow the role just chosen; a slip already read keeps its own."""
    n = 0
    for t in c['tasks']:
        if t.get('career') == ID and t.get('status') == 'new' and not t.get('known') and t.get('at') == 0 and t.get('role') != role:
            t['role'] = role
            n += 1
    return n


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('rd_intro', 'rd_role', 'rd_step', 'rd_shift', 'rd_desk'), 'Thao tác ở đài không hợp lệ.')
    d = _data(c)
    if name == 'rd_intro':
        d['intro'] = True
        return dict(message='Chị Hoa đưa tai nghe: kiểm phòng thu xong là lên sóng nhé!')
    if name == 'rd_role':
        role = kit.one_of(p.get('role'), ROLES, 'Vị trí không hợp lệ.')
        kit.need(role != 'dj' or d['promoted'], f'Làm phát thanh viên đủ {rc.PROBATION} ca đạt rồi mới làm DJ nhé.')
        d['role'] = role
        n = _restamp(c, role)
        return dict(message=f'Ca này bạn làm {rc.ROLES[role][0].lower()}.' + (f' {n} phiếu chưa đọc chuyển theo vị trí mới.' if n and c.get('open') else ''))
    desk = d['desk']
    if name == 'rd_desk':
        return kit.desk_choose(s, c, ID, desk, rc.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện cần quyết ở đài, quyết xong rồi làm tiếp nhé.')
    if name == 'rd_shift':
        return _shift(s, c, d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc phiếu việc trước khi làm nhé.')
    _, steps, key = _active(t)
    kit.need(t['at'] < len(steps), 'Việc này đã xong.')
    today = d['today']
    kit.need(_open_done(today), 'Kiểm phòng thu đầu ca trước khi lên sóng nhé.')
    kit.need(today['out'] != 1, '⚡ Đài đang mất điện! Xử lý sự cố trước rồi mới lên sóng tiếp.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = _value(st, p.get('value'))
    kit.start_work(t)
    today['aired'] = 1
    if not _same(value, key[st['id']]):
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], 1, 'Phải làm lại: ' + st['title'])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = _quality(t['wrong'])
        again = 'Tính lại cho kỹ nhé.' if st['type'] == 'number' else 'Đọc lại phiếu và sổ tay của đài rồi làm lại bước này.'
        message = f'Chưa đúng: {st["title"].lower()}. {kit.step_help(t, st, key[st["id"]], HOW.get(st["id"], ""), again, "Chị Hoa")}'
        t['lines'] = (t['lines'] + [message[:480]])[-LINES:]
        result = dict(message=message, correct=False)
        _after(s, c, d, result)
        return result
    t['work'][st['id']] = value
    t['at'] += 1
    t['lines'] = (t['lines'] + [f'✓ {st["title"]}.'])[-LINES:]
    if t['at'] < len(steps):
        result = dict(message='Đúng rồi. Tiếp: ' + steps[t['at']]['title'].lower() + '.', correct=True)
        _after(s, c, d, result)
        return result
    bonus = _bonus(t)
    t['paid'] = bonus
    t['stage'] = 'done'
    good = t['quality'] >= 90
    role = _role(t)
    for bucket in (today, d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['bonus'] += bonus
    if good:
        d['stats']['roles'][role] += 1
        if role == 'news':
            today['news_good'] = 1
    job = rc.JOBS[_job(t)]
    kit.complete(s, c, t, bonus, f'Xong việc {job[0].lower()}, chất lượng {t["quality"]}%.')
    result = dict(message=f'Xong: {job[0].lower()}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.', correct=good, celebrate=good)
    _blackout(s, c, d, t, result)
    _after(s, c, d, result)
    return result


def _shift(s: dict, c: dict, d: dict, p: dict) -> dict:
    """One step of the studio check or of the outage drill."""
    today = d['today']
    part = kit.one_of(p.get('part'), ('open', 'outage'), 'Chọn việc đầu ca hay xử lý sự cố nhé.')
    steps, key = shift_steps(today['day'], part)
    field = 'open_at' if part == 'open' else 'out_at'
    if part == 'outage':
        kit.need(today['out'] == 1, 'Đài không mất điện.')
    at = today[field]
    kit.need(at < len(steps), 'Phòng thu đã kiểm xong.' if part == 'open' else 'Sự cố đã xử lý xong.')
    st = steps[at]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở nhé.')
    value = _value(st, p.get('value'))
    if not _same(value, key[st['id']]):
        today['slips'] = min(today['slips'] + 1, 999)
        if part == 'outage':
            today['out_slips'] = min(today['out_slips'] + 1, 999)
            return dict(message='Chưa đúng thứ tự xử lý sự cố. Sóng vẫn đang câm, xem lại sổ sự cố rồi làm lại nhé.', correct=False)
        return dict(message='Chưa đúng thứ tự kiểm phòng thu. Xem lại tờ dán cạnh bàn trộn âm nhé.', correct=False)
    today[field] = at + 1
    if today[field] < len(steps):
        return dict(message='Đúng rồi. Tiếp: ' + steps[today[field]]['title'].lower() + '.', correct=True)
    if part == 'open':
        return dict(message='🎙️ Bàn trộn, mic, tai nghe, đường truyền ổn; đèn ĐANG PHÁT SÓNG đã sáng. Lên sóng thôi!', correct=True)
    today['out'] = 2
    if today['out_slips'] >= rc.OUTAGE_SLIPS:
        d['stats']['dead_air'] += 1
        kit.review(s, c, kit.npc_id(ID, 5), 2, 'Đang nghe đài thì mất sóng cả buổi, chẳng ai nói gì.', f'outage-{c["day"]}')
        return dict(message='🔌 Có điện lại, đài lên sóng tiếp. Nhưng sóng câm quá lâu, thính giả đã phàn nàn.', correct=True)
    d['stats']['restored'] += 1
    c['xp'] += 6
    return dict(message='🔌 Có điện lại! Bạn xử lý gọn, thính giả chỉ nghe băng dự phòng một lát.', correct=True, celebrate=True)


def _blackout(s: dict, c: dict, d: dict, t: dict, result: dict) -> None:
    """⚡ On an outage day the power goes out after the first finished job of the shift."""
    today = d['today']
    if today['out'] or today['jobs'] != 1 or not outage_day(c['day']):
        return
    today['out'] = 1
    d['stats']['outages'] += 1
    line = '⚡ Mất điện giữa sóng! Đài im bặt. Xử lý sự cố theo sổ ngay.'
    kit.log(s, c, 'surprise', line, kit.npc_id(ID, rc.TECH), t['id'])
    result['message'] = f'{result.get("message", "")} {line}'.strip()
    result['outage'] = True


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, rc.DESK, None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(rc.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    """A new slip takes the role chosen for the shift."""
    if t.get('career') == ID and t.get('status') == 'new' and t.get('at') == 0:
        d = _data(c)
        t['role'] = d['role'] if d['role'] in ROLES and (d['role'] != 'dj' or d['promoted']) else 'news'


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    kit.desk_start(s, c, ID, d['desk'], rc.DESK, None, c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], rc.DESK)
    lines = [f'Sóng Mây: {today["jobs"]} việc xong, {today["good"]} việc đạt từ 90%. Thưởng chất lượng: {today["bonus"]} xu.']
    if today['good'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1
        today['counted'] = 1
        d['last_active_day'] = c['day']
    if today['aired'] or today['open_at']:
        lines.append('🎙️ Đầu ca đã kiểm phòng thu.' if _open_done(today) else '🎙️ Ca này chưa kiểm xong phòng thu.')
    if today['out'] == 1:
        today['out'] = 2
        today['out_slips'] = max(today['out_slips'], rc.OUTAGE_SLIPS)
        d['stats']['dead_air'] += 1
        kit.review(s, c, kit.npc_id(ID, 5), 2, 'Đài mất sóng tới tối, chẳng ai lên tiếng xin lỗi.', f'outage-{c["day"]}')
        lines.append('⚡ Mất điện mà chưa xử lý: đài câm tới cuối ca, thính giả phàn nàn.')
    # 🎙️ Probation: a good Phát thanh viên shift counts once a day (the studio check, a good news job, no dead air).
    dead = today['out'] == 2 and today['out_slips'] >= rc.OUTAGE_SLIPS
    if today['news_good'] and _open_done(today) and not dead and d['last_news_day'] < c['day'] and not d['promoted']:
        d['stats']['news_days'] += 1
        d['last_news_day'] = c['day']
        left = rc.PROBATION - d['stats']['news_days']
        if left <= 0:
            d['promoted'] = True
            c['xp'] += 10
            lines.append('🎧 Hết thử việc! Chị Hoa giao chương trình “Đêm Sóng Mây”: từ ca sau bạn có thể làm DJ ca nhạc.')
        else:
            lines.append(f'🎙️ Một ca phát thanh viên đạt. Còn {left} ca nữa là làm được DJ.')
    if note:
        lines.append(note)
    return dict(lines=lines, note='Lương ca do hợp đồng chi trả. Ngày có việc đạt từ 90% mới ghi vào hành trình nghề.')


def known_request(c: dict, t: dict) -> str:
    _, _, _, title, opening, _, job = brief(t['day'], _slot(t), _role(t))
    j = rc.JOBS[job]
    return f'{j[1]} {j[0]}: {opening}'


def hint(c: dict, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc phiếu việc để biết việc của ca.'
    _, steps, _ = _active(t)
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Việc đã xong; nhận việc tiếp theo.'


def feedback(c: dict, t: dict) -> dict:
    _, steps, _ = _active(t)
    n = len(t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='care', label='Chất lượng phát sóng', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    b, _, _, title, opening, npc, job = brief(t['day'], _slot(t), _role(t))
    v['title'] = title
    v['opening'] = opening
    v['needs'] = deepcopy(b) if t['known'] else None
    j = rc.JOBS[job]
    r = rc.ROLES[_role(t)]
    v['job'] = dict(id=job, label=j[0], emoji=j[1])
    v['role_info'] = dict(id=_role(t), label=r[0], emoji=r[1])
    v['client_npc'] = kit.npc_id(ID, npc)
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    stats = d['stats']
    roles = sum(1 for k in ROLES if stats['roles'].get(k, 0) > 0)
    milestones = [dict(m, achieved=stats['good'] >= m['jobs'] and stats['active_days'] >= m['days'] and roles >= m['roles']) for m in rc.MILESTONES]
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones, roles=roles,
                         probation=rc.PROBATION, news_days=min(stats['news_days'], rc.PROBATION))
    d['desk'] = kit.desk_public(d['desk'], rc.DESK, ID, c)
    today = d['today'] if d['today']['day'] == c['day'] else _today(c['day'])
    steps, _ = shift_steps(c['day'], 'open')
    shift = dict(open=dict(at=today['open_at'], total=len(steps), done=today['open_at'] >= len(steps),
                           step=deepcopy(steps[today['open_at']]) if today['open_at'] < len(steps) else None))
    steps, _ = shift_steps(c['day'], 'outage')
    shift['outage'] = dict(state=('', 'cut', 'back')[today['out']], at=today['out_at'], total=len(steps), slips=today['out_slips'],
                           limit=rc.OUTAGE_SLIPS, step=deepcopy(steps[today['out_at']]) if today['out'] == 1 and today['out_at'] < len(steps) else None)
    d['shift'] = shift
    return d


def content() -> dict:
    return dict(
        notebook=rc.NOTEBOOK,
        roles=[dict(id=k, label=v[0], emoji=v[1], work=v[2]) for k, v in rc.ROLES.items()],
        jobs=[dict(id=k, label=v[0], emoji=v[1], role=v[2]) for k, v in rc.JOBS.items()],
        probation=rc.PROBATION, outage=dict(chance=round(rc.OUTAGE_CHANCE * 100), slips=rc.OUTAGE_SLIPS),
        intro=dict(title='Một ca ở Đài phát thanh Sóng Mây',
                   lead='Đài phát thanh của phường, FM 99,9. Đầu ca kiểm phòng thu rồi mới mở mic. Mới vào là phát thanh viên thử việc: '
                        f'bản tin, quảng cáo, lời chúc; đủ {rc.PROBATION} ca đạt thì làm DJ chương trình ca nhạc buổi tối. Lương ca theo hợp đồng, thưởng chất lượng nhỏ.',
                   work=[['📰', 'Bản tin phường: tin nào đọc, đọc trước tin nào'], ['📢', 'Quảng cáo: chỉ đọc bản đã duyệt'],
                         ['💌', 'Lời chúc: đúng tên, đúng giờ gửi'], ['🎧', 'DJ: bài lạ, người gọi chửi, khách mời trễ']],
                   meet=[['🎙️', 'Chị Hoa trưởng đài'], ['🔧', 'Anh Tuấn kỹ thuật'], ['📺', 'Ông Lực nhà tài trợ']],
                   stars=[['🎚️', 'Đầu ca kiểm phòng thu đúng thứ tự'],
                          ['⚡', 'Mất điện giữa sóng: xử lý theo sổ sự cố, sai nhiều bước là thính giả chê']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    for k in FIXED:
        kit.need(_same(t.get(k), original.get(k)), 'Dữ kiện phiếu của đài bị thay đổi: ' + k)
    kit.need(t.get('role') in ROLES, 'Vị trí của phiếu đài không hợp lệ.')
    _, steps, key = _active(t)
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình phiếu đài sai.')
    kit.need(at == 0 or t['known'], 'Chưa đọc phiếu việc.')
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(ids[:at]), 'Các bước đã làm không liên tục.')
    kit.need(all(_same(work[sid], key[sid]) for sid in ids[:at]), 'Kết quả bước của đài sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), 'Nhật ký lỗi của đài sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), 'Nhật ký lỗi của đài sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần làm lại sai.')
    kit.need(t.get('quality') == _quality(wrong), 'Điểm chất lượng của đài không khớp.')
    kit.need(type(t.get('paid')) is int and t['paid'] == (_bonus(t) if at == len(steps) else 0), 'Tiền thưởng của đài không khớp.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             'Nhật ký của đài sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), 'Phiếu của đài chưa xong mà đã hoàn tất.')
    kit.need(at == 0 or t.get('status') != 'new', 'Phiếu của đài sai trạng thái.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ của đài sai.')
    kit.need(type(d['intro']) is bool and type(d['promoted']) is bool, 'Sổ của đài sai.')
    kit.need(d['role'] in ROLES and (d['role'] != 'dj' or d['promoted']), 'Vị trí trong ca sai.')
    kit.integer(d['last_active_day'], 0, 10**7)
    kit.integer(d['last_news_day'], 0, 10**7)
    today = d['today']
    kit.need(isinstance(today, dict) and set(today) == set(base['today']), 'Số liệu của đài sai.')
    for v in today.values():
        kit.integer(v, 0, 10**9)
    for k in ('counted', 'aired', 'news_good'):
        kit.integer(today[k], 0, 1)
    kit.integer(today['out'], 0, 2)
    kit.integer(today['slips'], 0, 999)
    kit.integer(today['out_slips'], 0, 999)
    kit.integer(today['open_at'], 0, len(shift_steps(today['day'], 'open')[0]))
    kit.integer(today['out_at'], 0, len(shift_steps(today['day'], 'outage')[0]))
    kit.need(today['out_at'] == 0 or today['out'] >= 1, 'Sự cố của đài sai.')
    kit.need(today['good'] <= today['jobs'] and today['news_good'] <= today['good'] and today['out_slips'] <= today['slips'] + rc.OUTAGE_SLIPS,
             'Số việc đạt chuẩn sai.')
    st = d['stats']
    kit.need(isinstance(st, dict) and set(st) == set(base['stats']), 'Số liệu của đài sai.')
    for k, v in st.items():
        if k != 'roles':
            kit.integer(v, 0, 10**9)
    kit.need(isinstance(st['roles'], dict) and set(st['roles']) == set(ROLES), 'Số liệu vị trí của đài sai.')
    for v in st['roles'].values():
        kit.integer(v, 0, 10**9)
    kit.need(st['good'] <= st['jobs'] and sum(st['roles'].values()) == st['good'] and st['active_days'] <= st['good']
             and st['news_days'] <= st['roles']['news'] and st['restored'] + st['dead_air'] <= st['outages'],
             'Tiến trình nghề ở đài sai.')
    kit.need(d['promoted'] == (st['news_days'] >= rc.PROBATION), 'Thử việc phát thanh viên sai.')
    kit.need(all(t.get('role') != 'dj' or d['promoted'] for t in c.get('tasks', []) if t.get('career') == ID), 'Phiếu DJ khi chưa hết thử việc.')
    kit.desk_validate(d['desk'], rc.DESK)


SPEC = dict(
    id=ID, prefix='rd_', category='service', people=PEOPLE,
    meta=dict(short='Đài phát thanh', place='Đài phát thanh Sóng Mây', tagline='Đúng tin, đúng tên, đúng giờ lên sóng.', icon='music',
              color='#3f6fb0', light='#e4eefb', weather='Tiếng loa phường vang đầu hẻm', work='Phiếu việc', station='Phòng thu & phòng máy',
              greeting='Chị Hoa treo lịch phát sóng: kiểm phòng thu trước, rồi bản tin, quảng cáo, lời chúc. DJ thì đợi hết thử việc.',
              caption='Một phòng thu, cả phố cùng nghe', map_label='ĐÀI PHÁT THANH SÓNG MÂY'),
    staff=[('Chị Hoa', 'studio', 'Trưởng đài, duyệt từng chữ trước khi lên sóng.', 84, 90), ('Anh Tuấn', 'tech', 'Kỹ thuật viên, giữ chìa khóa máy phát.', 80, 88)],
    roles={'studio': 'Phòng thu', 'tech': 'Phòng máy'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('📻', 'Một ca ở Sóng Mây', [('Đầu ca', 'Kiểm phòng thu'), ('Bản tin', 'Tin khẩn trước'), ('Quảng cáo', 'Chỉ bản đã duyệt'),
                                       ('Mất điện', 'Theo sổ sự cố')],
              ['Kiểm phòng thu đầu ca', 'Đọc phiếu việc', 'Làm từng bước theo phiếu', 'Mất điện thì xử lý theo sổ']),
    stories=[('Chiếc micro cũ của chị Hoa', ('Chiếc micro bọc mút xanh đã sờn, dán băng keo ở chân.', 'Bạn kéo cần gạt về 0, nói thử “một, hai, ba”.',
                                             'Chị Hoa gật đầu: “Cả phố đang nghe, đọc chậm thôi em.”'))],
    review_asides=['Bản tin rõ ràng, dễ nghe.', 'Đài đọc đúng tên cháu tôi.', 'Nhạc theo yêu cầu mở đúng bài.'], situations=[],
    more_line='Chị Hoa vừa giao thêm một phiếu việc.', open_line='Chị Hoa đã mở phòng thu; lịch phát sóng và sổ sự cố treo cạnh bàn trộn âm.',
    guide='Đầu ca kiểm phòng thu đúng thứ tự rồi mới lên sóng. Phát thanh viên: bản tin, quảng cáo nhà tài trợ, lời chúc; DJ sau thử việc. '
          'Làm từng bước theo phiếu; sai thì sửa ngay, thưởng giảm theo chất lượng. Mất điện giữa sóng thì xử lý theo sổ sự cố.',
    employment=dict(postings=[dict(id='radio-songmay', org='Đài phát thanh Sóng Mây', kind='company', title='Phát thanh viên (sau thử việc làm DJ)',
                                   salary=(50, 64), probation_days=3, wants=['careful', 'patience', 'teamwork'],
                                   perks=['Chị Hoa kèm những ca đầu', 'Thưởng chất lượng nhỏ', 'Lương ca theo hợp đồng'],
                                   culture='Đọc đúng tin, đúng tên; chỉ đọc bản đã duyệt; mất điện thì bình tĩnh theo sổ.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
