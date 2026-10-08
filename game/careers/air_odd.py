"""Chuyện oái oăm: the awkward, pushy, strange demands around the air crew (pilot, flight_attendant).

Rule 6 of the owner (docs/HANDOFF.md §2): every career meets many exasperating people around the job.
Here they come as encounters between hops, kept apart from the generated flights: a task never changes,
so flights made by the live release still validate. Each encounter is a script in
game/careers/air_odd_content.py: who pushes, what they want, how they push again.

The player answers in their own words, not by picking a scripted line:
  * a tone: soft / firm / sharp,
  * one or two things to say (a plain no, the rule, "I'm on duty", another way, ask why, laugh it off,
    "later…", or give in),
  * whom to bring in: nobody, the crew (the captain / the purser), or the company (the safety office, the union),
  * in a bargain (KPI, overtime, the gym, leave): how many of the asked units to accept.
The other side decides by itself from hidden traits rolled from the encounter's id (persistence, mood, give)
and the airline's pressure that day: it backs off, pushes again (three rounds at most), digs in, deals or
hits back. Nothing is random at answer time: the same encounter and the same answers always end the same.

What the game teaches: decline clearly, set a boundary, bring in the crew, report. Giving in to a seduction or
to a cut corner is never rewarded: it costs conduct points, and enough of them stand the crew member down for
the day (đình chỉ bay) or demote them (cách chức). Harassment is never the victim's fault: reporting it is always
legitimate and the company backs it; not reporting only means the harasser may come back. A bargain accepted
beyond the rules pays overtime but tires the crew (fatigue): tired crew earn half the flight bonus, and asking
for rest days is the player's own move from the crew room.

Other careers reuse the engine (oil keeps the air crew's words; railway, nurse, lighthouse, rescue, lifeguard and
police word it their own way). Besides crew, company, union, office, demoted and title, a career's cfg may carry,
each optional (the air crew's line otherwise): labels {kind: {word id: label}}, levels {level id: label},
harass_note, ground_line, demote_line ('{demoted}' is filled in), warn_line, restore_line, tired_line and rest_ok.
The air kit's oddCard/restCard read cfg.kinds and cfg.rest_to.
"""
from __future__ import annotations

from . import kit
from .. import archive as ar

MAX_ROUNDS = 3
LOG_MAX = 40
TONES = ('soft', 'firm', 'sharp')
TONE_W = dict(soft=1, firm=2, sharp=3)
TONE_LABEL = dict(soft='Nhẹ nhàng', firm='Dứt khoát', sharp='Gắt')
CHANNELS = ('self', 'crew', 'company')
KINDS = ('charm', 'harass', 'demand', 'corner', 'bargain')
RANKS = ('pax', 'crew', 'boss', 'kin')
REACTIONS = ('push', 'back', 'report', 'give', 'stuck', 'deal', 'lawful', 'penalty', 'lapse')
# How much each thing said moves the other side, by kind ('yes' is giving in: it ends the encounter).
WORDS = {
    'charm': dict(no=2, duty=1, rule=2, alt=1, joke=-1, later=-3, yes=None),
    'harass': dict(stop=3, no=2, rule=2, duty=1, joke=-2, later=-3, yes=None),
    'demand': dict(no=1, rule=2, alt=2, why=1, joke=0, later=-1, yes=None),
    'corner': dict(speak=3, rule=2, alt=1, joke=-2, yes=None),
    'bargain': dict(rule=0, health=0, alt=0, paper=0, yes=None),
}
LABELS = {
    'charm': dict(no='Em xin phép từ chối.', duty='Em đang trong ca bay.', rule='Hãng không cho tổ bay hẹn khách.',
                  alt='Chúc chị chuyến đi vui nhé.', joke='Cười cười cho qua.', later='Để hôm khác nha…', yes='Nhận lời.'),
    'harass': dict(stop='Dừng lại ngay.', no='Không. Tôi không đồng ý.', rule='Quấy rối tổ bay là vi phạm.',
                   duty='Tôi đang làm việc.', joke='Cười trừ cho qua.', later='Thôi, bỏ qua đi.', yes='Chiều cho xong chuyện.'),
    'demand': dict(no='Dạ không được ạ.', rule='Quy định không cho phép.', alt='Em có cách khác…', why='Mình cần vậy vì sao ạ?',
                   joke='Đùa cho qua.', later='Để em xem đã.', yes='Chiều theo.'),
    'corner': dict(speak='Mình chưa làm đủ bước.', rule='Quy trình bắt buộc mà.', alt='Làm nhanh mà vẫn đủ bước.',
                   joke='Cười xòa cho qua.', yes='Làm theo.'),
    'bargain': dict(rule='Vượt giờ quy định rồi.', health='Sức khỏe em không cho phép.', alt='Em đề xuất cách khác.',
                    paper='Cho em xin văn bản.', yes='Nhận hết.'),
}
REST_WORDS = dict(health='Em mệt thật, cần nghỉ.', rule='Quy định giờ nghỉ tối thiểu.', family='Nhà em có việc.', paper='Em nộp đơn đàng hoàng.')
# Bringing someone in: how much it helps, by the other side's rank (the company ends a charm, harassment or corner cut).
CREW_HELP = dict(pax=3, crew=2, boss=1, kin=0)
COMPANY_HELP = dict(pax=2, crew=2, boss=2, kin=0)
REPORTED = ('charm', 'harass', 'corner')
LEVELS = [(0, 'ok', 'Hồ sơ sạch'), (2, 'note', 'Bị nhắc nhở'), (4, 'warn', 'Bị cảnh cáo'), (6, 'ground', 'Tạm đình chỉ bay'), (8, 'demote', 'Bị cách chức')]
GROUND_AT, DEMOTE_AT, RESTORE_AT, CLEAN_PER_POINT = 6, 8, 3, 3
TIRED, FATIGUE_MAX, CONDUCT_MAX = 3, 9, 20
MOOD_CUE = {0: '🙂 còn nhã nhặn', 1: '', 2: '😤 đang nóng máu'}
# What happens by default, per kind (a script can say it in its own words: back / give / report / stuck).
TEXT = {
    'charm': dict(back='{who} cười gượng rồi thôi. Chuyện dừng ở đó, sạch sẽ.',
                  report='Bạn báo phòng an toàn. Họ ghi nhận và nhắc khéo {who}; hồ sơ bạn thêm dòng “xử lý đúng mực”.',
                  stuck='Chuyện cứ lấp lửng không dứt. Trong hãng bắt đầu có người xì xào.',
                  give='Bạn nhận lời. Chuyện riêng mà ra tới phòng an toàn thì không còn là chuyện riêng.'),
    'harass': dict(back='{who} lẩm bẩm rồi ngồi im. Chị Thu nháy mắt: “Lần sau cứ báo luôn, đó là quyền của em.”',
                   report='Bạn báo tổ trưởng, điền biên bản. Hãng lập biên bản {who} và đưa vào danh sách theo dõi; cả tổ đứng về phía bạn.',
                   stuck='{who} giở giọng tới tận lúc hạ cánh. Không ai ghi lại gì, nên lần sau hắn vẫn dám. Không phải lỗi của bạn: báo là quyền của bạn.',
                   give='Bạn chiều cho xong chuyện. {who} được đà làm tới. Không phải lỗi của bạn, nhưng lần sau cứ báo: hãng có quy trình bảo vệ tổ bay.'),
    'demand': dict(back='{who} càu nhàu nhưng chịu theo cách của bạn.', stuck='{who} khăng khăng tới cuối rồi làm ầm lên với cả tổ.',
                   give='Bạn chiều theo. Chuyện nhỏ thành chuyện to.'),
    'corner': dict(back='{who} thở dài rồi làm lại cho đủ bước.',
                   report='Bạn gửi báo cáo an toàn (người báo không bị phạt). Phòng an toàn cho người khác bay thay; {who} phải bay mô phỏng lại.',
                   stuck='{who} vẫn làm tắt. Chuyến bay qua êm, nhưng bạn biết mình đã im lặng.',
                   give='Bạn làm theo {who}. Trong sổ, chuyện này là của cả hai người.'),
    'bargain': dict(deal='{who}: “Ok, chốt {n} {unit}.”', lawful='{who} hậm hực nhưng không làm gì được: quy định đứng về phía bạn.',
                    penalty='{who}: “Không hợp tác thì tháng này khỏi thưởng.” Bị trừ {cost} xu thưởng chuyên cần.',
                    give='Bạn nhận hết {n} {unit}. {who} cười tươi rói, còn bạn thì mệt rũ.'),
}


# ================================================================ the data
def initial() -> dict:
    return dict(ev=None, last=None, log=[], day=0, fired=0, plan=[], seq=0, marks={},
                conduct=dict(points=0, ground=0, demoted=False, clean=0), fatigue=0, rest=0)


def ensure(d: dict) -> dict:
    """The career's data gains the encounter book (saves from before it start with a clean one)."""
    odd = d.setdefault('odd', initial())
    for k, v in initial().items():
        odd.setdefault(k, v if not isinstance(v, (dict, list)) else type(v)(v))
    for k, v in initial()['conduct'].items():
        odd['conduct'].setdefault(k, v)
    return odd


def script(scripts: list, sid: str) -> dict | None:
    return next((x for x in scripts if x['id'] == sid), None)


def level(points: int) -> tuple:
    return next(x for x in reversed(LEVELS) if points >= x[0])


def channels(x: dict) -> tuple:
    return ('self',) if x['rank'] == 'kin' else ('self', 'company') if x['kind'] == 'bargain' else CHANNELS


def grounded(c: dict, odd: dict) -> bool:
    return odd['conduct']['ground'] == c['day']


def bonus(odd: dict, amount: int) -> int:
    """The flight bonus: none while demoted, half when tired."""
    if odd['conduct']['demoted']:
        return 0
    return amount // 2 if odd['fatigue'] >= TIRED else amount


# ================================================================ when encounters happen
def plan(career: str, day: int) -> list:
    """Today's encounters: 'open' (the morning, before the first hop) and/or after the n-th finished job."""
    if day <= 1:
        return []
    if day <= 3:
        return [1]
    r = kit.rng(career, 'odd-plan', day)
    if day <= 6:
        return list([['open', 2], [1, 3], [1], ['open', 1]][r.randrange(4)])
    return list([['open', 1, 3], [1, 2], ['open', 2], [1, 2, 4]][r.randrange(4)])


def start(c: dict, career: str, odd: dict) -> None:
    """From on_start: a night's sleep takes one point of fatigue, and today's plan."""
    if odd['day'] != c['day']:
        odd['fatigue'] = max(0, odd['fatigue'] - 1)
        odd.update(day=c['day'], fired=0, plan=plan(career, c['day']))


def _pool(c: dict, odd: dict, scripts: list, at: str) -> list:
    rows = [x for x in scripts if x.get('min_day', 2) <= c['day'] and x.get('at', 'between') in (at, 'any')
            and (not x.get('need_mark') or x['need_mark'] in odd['marks']) and not (x.get('no_mark') and x['no_mark'] in odd['marks'])]
    recent = [h['script'] for h in odd['log'][-max(1, min(len(rows) - 1, 16)):]]
    return [x for x in rows if x['id'] not in recent] or rows


def tick(s: dict, c: dict, career: str, odd: dict, scripts: list, busy: bool = False) -> dict | None:
    """After an action (and at the day's start): open the next planned encounter when one is due.
    `busy`: something else holds the player (a desk surprise, the seat-belt sign)."""
    if not c.get('open') or odd['ev'] is not None or busy:
        return None
    due = lambda: [p for p in odd['plan'] if p == 'open' or c['day_completed'] >= p]
    if odd['day'] != c['day']:
        # A day already under way (a save from before the encounters, or a day opened elsewhere): nobody turns up
        # in the middle of a hop; today's plan counts from the next finished job.
        start(c, career, odd)
        odd['fired'] = len(due())
        return None
    due = due()
    if len(due) <= odd['fired']:
        return None
    at = 'open' if due[odd['fired']] == 'open' else 'between'
    pool = _pool(c, odd, scripts, at) or _pool(c, odd, scripts, 'between')
    odd['fired'] += 1
    if not pool:
        return None
    weights = [x.get('weight', 2) for x in pool]
    pick = kit.rng(career, 'odd', c['day'], odd['fired'], len(odd['log'])).random() * sum(weights)
    x = pool[-1]
    for row, w in zip(pool, weights):
        pick -= w
        if pick < 0:
            x = row
            break
    odd['seq'] += 1
    odd['ev'] = dict(id=f'odd-{odd["seq"]}', script=x['id'], day=c['day'], at=at, said=[])
    kit.log(s, c, 'surprise', f'{x["emoji"]} {x["title"]}: {x["text"]}', None, odd['ev']['id'])
    return x


def block(odd: dict, message: str) -> None:
    kit.need(odd['ev'] is None, message, 'surprise_open')


# ================================================================ how the other side decides
def traits(career: str, x: dict, ev: dict) -> dict:
    """Hidden, rolled once from the encounter's id: how long they keep pushing, their mood, how much they give."""
    r = kit.rng(career, 'odd-traits', ev['id'], x['id'])
    lo, hi = x.get('persist', (1, 2))
    persist = r.randint(lo, hi)
    lo, hi = x.get('mood', (0, 1))
    return dict(persist=persist, mood=r.randint(lo, hi), flex=r.randint(0, 1))


def _play(career: str, x: dict, ev: dict, pressure: int) -> dict:
    """Replay every answer so far: the other side's reaction to the last one (deterministic)."""
    tr = traits(career, x, ev)
    kind, rank = x['kind'], x['rank']
    out = dict(how='push', n=None, sour=False, dig=False, later=0, sharp_boss=False)
    if kind == 'bargain':
        ask, limit = x['ask'], x['limit']
        for i, rp in enumerate(ev['said']):
            words = rp['say']
            out['sharp_boss'] = out['sharp_boss'] or rp['tone'] == 'sharp'
            if 'yes' in words:
                return dict(out, how='give', n=ask)
            need = ask - tr['flex'] - i + pressure + x.get('press', 0)
            need -= ('rule' in words or 'health' in words) + ('alt' in words) + (2 if rp['to'] == 'company' else 0)
            if ask > limit and (rp['to'] == 'company' or 'paper' in words):
                need = min(need, limit + (0 if rp['to'] == 'company' else 1))
            if rp['n'] >= max(0, min(ask, need)):
                return dict(out, how='deal', n=rp['n'])
            if i == MAX_ROUNDS - 1:
                lawful = rp['n'] >= min(ask, limit) or rp['to'] == 'company'
                return dict(out, how='lawful' if lawful else 'penalty', n=rp['n'])
        return out
    left = tr['persist'] + 2 + (1 if rank == 'boss' else 0)
    asked = False
    for i, rp in enumerate(ev['said']):
        words, tone, to = rp['say'], rp['tone'], rp['to']
        if 'yes' in words:
            return dict(out, how='give')
        if to == 'company' and kind in REPORTED:
            return dict(out, how='report')
        out['later'] += 'later' in words
        out['sharp_boss'] = out['sharp_boss'] or (tone == 'sharp' and rank == 'boss')
        clear = TONE_W[tone] + sum(WORDS[kind][w] for w in words)
        clear += CREW_HELP[rank] if to == 'crew' else COMPANY_HELP[rank] if to == 'company' else 0
        if asked and 'alt' in words:
            clear += 1                                    # knowing why, the other way fits
        asked = asked or 'why' in words
        if tone == 'sharp' and kind in ('demand', 'charm') and rank in ('pax', 'kin'):
            if tr['mood'] >= 2:
                left += 2
                out['dig'] = True                         # snapping at someone already angry makes them dig in
            elif tr['mood'] == 0:
                out['sour'] = True                        # snapping at someone still polite leaves a sour taste
        left -= clear
        if left <= 0:
            return dict(out, how='back')
        if i == MAX_ROUNDS - 1:
            return dict(out, how='stuck')
    return out


# ================================================================ answering
def _words(p, x: dict) -> list:
    say = p.get('say')
    kit.need(isinstance(say, list) and 1 <= len(say) <= 2 and len(set(say)) == len(say), 'Chọn một hoặc hai ý để nói.')
    for w in say:
        kit.one_of(w, WORDS[x['kind']], 'Ý này không hợp với chuyện đang gặp.')
    return list(say)


def reply(s: dict, c: dict, career: str, odd: dict, scripts: list, p: dict, cfg: dict, pressure: int) -> dict:
    """The player's answer: tone, words, whom to bring in (and in a bargain, how many units). Returns the result."""
    ev = odd['ev']
    kit.need(ev is not None, 'Không có chuyện nào đang chờ trả lời.')
    x = script(scripts, ev['script'])
    kit.need(x, 'Chuyện này không còn nữa.')
    rp = dict(tone=kit.one_of(p.get('tone'), TONES, 'Chọn giọng nói.'), say=_words(p, x),
              to=kit.one_of(p.get('to', 'self'), channels(x), 'Chọn người để báo.'), n=None, r='push')
    if x['kind'] == 'bargain':
        rp['n'] = kit.integer(p.get('n', 0), 0, x['ask'])
    ev['said'].append(rp)
    out = _play(career, x, ev, pressure)
    rp['r'] = out['how']
    if out['how'] == 'push':
        line = x['push'][min(len(ev['said']), len(x['push'])) - 1]
        pre = '😤 ' if out['dig'] else ''
        return dict(message=f'{pre}{x["who"].split(" · ")[0]}: {line}')
    return _resolve(s, c, career, odd, x, out, cfg)


def _say(x: dict, how: str, **kw) -> str:
    text = x.get(how) or TEXT[x['kind']].get(how, '')
    return text.format(who=x['who'].split(' · ')[0], unit=x.get('unit', ''), **kw)


def _resolve(s: dict, c: dict, career: str, odd: dict, x: dict, out: dict, cfg: dict) -> dict:
    ev, how, kind = odd['ev'], out['how'], x['kind']
    notes = []
    good = None
    conduct = 0
    if kind == 'bargain':
        n = out['n'] or 0
        if how in ('deal', 'give'):
            money = n * x.get('pay', 0)
            if money:
                _money(s, c, money, x, ev['id'])
            odd['fatigue'] = min(FATIGUE_MAX, odd['fatigue'] + n * x.get('tire', 0))
            good = False if n > x['limit'] else True if n < x['ask'] else None
            text = _say(x, 'lawful') if how == 'deal' and n == 0 else _say(x, how, n=n)   # they gave up asking
            if n > x['limit']:
                notes.append(f'😮‍💨 Quá sức: mệt thêm {n * x.get("tire", 0)}.' if x.get('tire') else '😮‍💨 Nhận quá mức hợp lý.')
            elif money > 0:
                notes.append(f'💵 +{money} xu làm thêm.')
            elif money < 0:
                notes.append(f'💸 {money} xu.')
        elif how == 'lawful':
            good, text = True, _say(x, 'lawful')
            c['xp'] += 8
        else:
            text = _say(x, 'penalty', cost=x.get('cost', 10))
            _money(s, c, -x.get('cost', 10), x, ev['id'])
            odd['marks']['kpi_black'] = c['day']
            good = False
    else:
        text = _say(x, how)
        if how == 'back':
            good = None if out['sour'] else True
            c['xp'] += 8
            if out['sour'] and x.get('sour'):
                text += ' ' + x['sour']
            elif out['sour']:
                text += ' Nhưng bạn gắt với một người còn đang lịch sự: họ về kể lại với giọng không vui.'
        elif how == 'report':
            good = True
            c['xp'] += 12
            odd['marks'].pop(x.get('follow') or '', None)
        elif how == 'give':
            good = None if kind == 'harass' else False
            conduct += {'charm': 3, 'corner': x.get('severe', 2), 'demand': x.get('breach', 0), 'harass': 0}[kind]
        else:                                   # stuck
            good = None if kind == 'harass' else False
            conduct += {'charm': 1, 'corner': 1}.get(kind, 0)
        if kind == 'charm':
            conduct += out['later']             # “later…” keeps the door ajar: the office reads it that way
        fx = (x.get('fx') or {}).get(how) or ({'patience': -6} if kind == 'demand' and how == 'stuck' else {})
        if fx.get('patience'):
            for t in c['tasks']:
                if t.get('career') == career and t['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in t:
                    t['patience'] = max(25, min(100, t['patience'] + int(fx['patience'])))
        if fx.get('money'):
            _money(s, c, int(fx['money']), x, ev['id'])
        if kind == 'harass' and how != 'report' and x.get('follow'):
            odd['marks'][x['follow']] = c['day']          # unreported, the same man may fly with you again
        if kind == 'harass' and how == 'report':
            notes.append(cfg.get('harass_note') or '🛡️ Báo là đúng: hãng có quy trình bảo vệ tổ bay.')
    if out['sharp_boss']:
        odd['marks']['strained'] = c['day']
    if conduct:
        notes.append(_conduct(c, odd, conduct, cfg))
    outcome = ' '.join([text] + [n for n in notes if n]).strip()[:600]
    odd['last'] = dict(script=x['id'], title=x['title'], emoji=x['emoji'], outcome=outcome, good=good, day=c['day'], how=how)
    odd['log'] = ar.last(odd['log'] + [dict(id=ev['id'], script=x['id'], day=c['day'], how=how, good=good)], LOG_MAX, 'odd.log', c)
    odd['ev'] = None
    kit.metric(c, 'surprises')
    if good is True:
        kit.metric(c, 'surprises_good')
    if x.get('npc') is not None and x.get('review') and how in x['review']:
        stars, line = x['review'][how]
        kit.review(s, c, kit.npc_id(career, x['npc']), stars, line, ev['id'])
    kit.log(s, c, 'surprise', f'{x["title"]}: {outcome}', None, ev['id'])
    result = dict(message=f'{x["emoji"]} {outcome}', celebrate=good is True)
    if good is False:
        result['correct'] = False
    return result


def _money(s: dict, c: dict, amount: int, x: dict, ref: str) -> None:
    if amount < 0:
        amount = -min(-amount, max(0, c['money']))
    if amount:
        kit.money(s, c, amount, x['title'], ref, 'event_income' if amount > 0 else 'event_cost')


def _conduct(c: dict, odd: dict, delta: int, cfg: dict) -> str:
    """Conduct points: reminders, a written warning, stood down for the day, demoted."""
    cd = odd['conduct']
    before = cd['points']
    cd['points'] = min(CONDUCT_MAX, before + delta)
    after = cd['points']
    if after >= DEMOTE_AT and not cd['demoted']:
        cd['demoted'] = True
        cd['ground'] = c['day']
        # A career outside the airline (railway, nurse, lighthouse, rescue, lifeguard, police) words these in its own cfg;
        # '{demoted}' is filled in.
        # The air crew (pilot, flight_attendant, oil) keep the lines they had.
        line = cfg.get('demote_line') or '⚖️ Hội đồng kỷ luật: cách chức xuống {demoted}, tạm đình chỉ bay hôm nay, thưởng chuyến về 0 tới khi hồ sơ sạch lại.'
        return line.format(demoted=cfg['demoted'])
    if before < GROUND_AT <= after:
        cd['ground'] = c['day']
        return cfg.get('ground_line') or '⚖️ Phòng an toàn: tạm đình chỉ bay hết hôm nay, mai lên trình bày.'
    if before < 4 <= after:
        return cfg.get('warn_line') or '⚠️ Cảnh cáo bằng văn bản vào hồ sơ.'
    if before < 2 <= after:
        return '📝 Bị nhắc nhở, ghi vào hồ sơ.'
    return f'📝 Hồ sơ +{delta} điểm vi phạm.'


def penalize(c: dict, odd: dict, delta: int, cfg: dict) -> str:
    """Conduct points for something given in to outside an encounter (the railway's barrier lifted for someone)."""
    return _conduct(c, odd, delta, cfg)


def flown(odd: dict, clean: bool, cfg: dict) -> str:
    """After a finished job: clean work slowly clears the record (and lifts a demotion)."""
    cd = odd['conduct']
    if not clean:
        return ''
    cd['clean'] = min(10 ** 6, cd['clean'] + 1)
    if cd['points'] and cd['clean'] % CLEAN_PER_POINT == 0:
        cd['points'] -= 1
        if cd['demoted'] and cd['points'] <= RESTORE_AT:
            cd['demoted'] = False
            return cfg.get('restore_line') or f'🎖️ Hồ sơ sạch dần: được phục chức {cfg["title"]}.'
    return ''


def close(s: dict, c: dict, odd: dict, scripts: list) -> str | None:
    """At the end of the shift an unanswered encounter lapses."""
    ev = odd['ev']
    if ev is None:
        return None
    x = script(scripts, ev['script'])
    odd['ev'] = None
    if not x:
        return None
    if x['kind'] == 'harass' and x.get('follow'):
        odd['marks'][x['follow']] = c['day']
    odd['last'] = dict(script=x['id'], title=x['title'], emoji=x['emoji'], outcome='Hết ca, chuyện bỏ ngỏ.', good=None, day=c['day'], how='lapse')
    odd['log'] = ar.last(odd['log'] + [dict(id=ev['id'], script=x['id'], day=c['day'], how='lapse', good=None)], LOG_MAX, 'odd.log', c)
    return f'{x["emoji"]} {x["title"]}: hết ca vẫn bỏ ngỏ.'


def day_lines(c: dict, odd: dict, cfg: dict | None = None) -> list:
    """The day summary's lines; a career other than the air crew passes its cfg for its own words (tired_line)."""
    cfg = cfg or {}
    today = [h for h in odd['log'] if h['day'] == c['day'] and h['how'] != 'lapse']
    lines = []
    if today:
        ok = sum(h['good'] is True for h in today)
        lines.append(f'🙄 Gặp {len(today)} chuyện oái oăm, xử lý đẹp {ok}.')
    lv = level(odd['conduct']['points'])
    if lv[1] != 'ok':
        lines.append(f'📁 Hồ sơ: {(cfg.get("levels") or {}).get(lv[1], lv[2]).lower()}.')
    if odd['fatigue'] >= TIRED:
        lines.append(cfg.get('tired_line') or '😮‍💨 Mệt rồi: thưởng chuyến còn một nửa. Xin nghỉ bù ở phòng tổ bay.')
    return lines


# ================================================================ rest days: the player's own request
def rest(s: dict, c: dict, odd: dict, p: dict, pressure: int, cfg: dict) -> dict:
    kit.need(odd['rest'] != c['day'], 'Hôm nay bạn đã xin nghỉ rồi. Mai hỏi lại nhé.')
    n = kit.integer(p.get('n', 1), 1, 2)
    say = p.get('say') or []
    kit.need(isinstance(say, list) and 1 <= len(say) <= 2 and len(set(say)) == len(say) and all(w in REST_WORDS for w in say),
             'Chọn một hoặc hai lý do.')
    to = kit.one_of(p.get('to', 'self'), ('self', 'company'), 'Gửi cho điều phái hay qua công đoàn?')
    tired = odd['fatigue'] >= TIRED
    score = ('health' in say) + ('rule' in say) + ('paper' in say) + ('family' in say and pressure == 0) + (2 if to == 'company' else 0) \
        + tired - pressure - ('strained' in odd['marks'])
    grant = max(0, min(n, score))
    if tired and ('rule' in say or to == 'company'):
        grant = max(grant, 1)                      # the legal minimum rest cannot be refused
    odd['rest'] = c['day']
    before = odd['fatigue']
    odd['fatigue'] = max(0, before - 2 * grant)
    if grant:
        c['xp'] += 4 * grant
        head = f'📝 {cfg["office"]} duyệt {grant} ngày nghỉ bù.' + (' Không đủ như xin, nhưng có còn hơn không.' if grant < n else '')
        tail = (cfg.get('rest_ok') or ' Người bay thay đã xếp xong; bạn thấy nhẹ cả người.') if before else ''
        return dict(message=head + tail, celebrate=True)
    return dict(message=f'📝 {cfg["office"]}: “Cao điểm mà nghỉ gì em, cố lên 💪.” Đơn bị trả về.' + (' Mệt thế này thì nêu quy định giờ nghỉ hoặc nhờ công đoàn.' if tired else ''))


# ================================================================ what the client sees
def public(c: dict, odd: dict, scripts: list, career: str, cfg: dict) -> dict:
    ev = odd.get('ev')
    view = None
    if ev:
        x = script(scripts, ev['script'])
        if x:
            # A career may word the answers its own way (cfg['labels'][kind]); a script's own words come last.
            words = {**LABELS[x['kind']], **(cfg.get('labels') or {}).get(x['kind'], {}), **x.get('words', {})}
            said = ev.get('said', [])
            line = x['text'] if not said else x['push'][min(len(said), len(x['push'])) - 1]
            ch = {'self': 'Tự xử lý', 'crew': cfg['crew'], 'company': cfg['union'] if x['kind'] == 'bargain' else cfg['company']}
            tr = traits(career, x, ev)
            view = dict(id=ev['id'], script=x['id'], kind=x['kind'], rank=x['rank'], title=x['title'], emoji=x['emoji'], who=x['who'],
                        npc=kit.npc_id(career, x['npc']) if x.get('npc') is not None else None, line=line, round=len(said) + 1, rounds=MAX_ROUNDS,
                        cue=MOOD_CUE.get(tr['mood'], ''), words=[dict(id=w, label=words[w]) for w in WORDS[x['kind']]],
                        channels=[dict(id=k, label=ch[k]) for k in channels(x)], tones=[dict(id=k, label=TONE_LABEL[k]) for k in TONES],
                        said=[dict(tone=TONE_LABEL[r['tone']], say=[words[w] for w in r['say']], n=r.get('n')) for r in said])
            if x['kind'] == 'bargain':
                view['bargain'] = dict(ask=x['ask'], limit=x['limit'], unit=x['unit'], pay=x.get('pay', 0))
    cd = odd.get('conduct') or initial()['conduct']
    lv = level(cd['points'])
    log = []
    for h in odd.get('log', [])[-6:]:
        x = script(scripts, h['script'])
        if x:
            log.append(dict(title=x['title'], emoji=x['emoji'], day=h['day'], how=h['how'], good=h['good']))
    return dict(ev=view, last=odd.get('last'), log=log,
                conduct=dict(points=cd['points'], level=lv[1], label=(cfg.get('levels') or {}).get(lv[1], lv[2]), ground=cd['ground'] == c['day'],
                             demoted=cd['demoted']),
                fatigue=odd.get('fatigue', 0), tired=odd.get('fatigue', 0) >= TIRED, rest_today=odd.get('rest') == c['day'],
                rest_words=[dict(id=k, label=v) for k, v in REST_WORDS.items()])


# ================================================================ saves
def validate(odd, scripts: list) -> None:
    kit.need(isinstance(odd, dict) and set(initial()) <= set(odd), 'Sổ chuyện oái oăm thiếu dữ liệu.')
    for k in ('day', 'fired', 'seq', 'rest'):
        kit.integer(odd[k], 0, 10 ** 9)
    kit.integer(odd['fatigue'], 0, FATIGUE_MAX)
    kit.need(isinstance(odd['plan'], list) and len(odd['plan']) <= 6
             and all(p == 'open' or (type(p) is int and 0 <= p <= 12) for p in odd['plan']), 'Lịch chuyện oái oăm sai.')
    kit.need(isinstance(odd['marks'], dict) and len(odd['marks']) <= 40, 'Dấu chuyện cũ sai.')
    for k, v in odd['marks'].items():
        kit.text(k, 40)
        kit.integer(v, 0, 10 ** 7)
    cd = odd['conduct']
    kit.need(isinstance(cd, dict) and set(cd) == set(initial()['conduct']) and type(cd['demoted']) is bool, 'Hồ sơ kỷ luật sai.')
    kit.integer(cd['points'], 0, CONDUCT_MAX)
    kit.integer(cd['ground'], 0, 10 ** 7)
    kit.integer(cd['clean'], 0, 10 ** 6)
    ids = {x['id']: x for x in scripts}
    kit.need(isinstance(odd['log'], list) and len(odd['log']) <= LOG_MAX, 'Lịch sử chuyện oái oăm sai.')
    for h in odd['log']:
        kit.need(isinstance(h, dict) and h.get('script') in ids and h.get('how') in REACTIONS and h.get('good') in (True, False, None),
                 'Lịch sử chuyện oái oăm sai.')
        kit.integer(h.get('day'), 0, 10 ** 7)
    ev = odd['ev']
    if ev is not None:
        kit.need(isinstance(ev, dict) and set(ev) == {'id', 'script', 'day', 'at', 'said'} and ev['script'] in ids
                 and ev['at'] in ('open', 'between'), 'Chuyện oái oăm sai.')
        kit.text(ev['id'], 40)
        kit.integer(ev['day'], 1, 10 ** 7)
        x = ids[ev['script']]
        kit.need(isinstance(ev['said'], list) and len(ev['said']) < MAX_ROUNDS, 'Lượt trả lời sai.')
        for r in ev['said']:
            kit.need(isinstance(r, dict) and set(r) == {'tone', 'say', 'to', 'n', 'r'} and r['tone'] in TONES and r['to'] in channels(x)
                     and r['r'] == 'push' and isinstance(r['say'], list) and 1 <= len(r['say']) <= 2
                     and all(w in WORDS[x['kind']] for w in r['say']), 'Lượt trả lời sai.')
            kit.need(r['n'] is None if x['kind'] != 'bargain' else type(r['n']) is int and 0 <= r['n'] <= x['ask'], 'Lượt trả lời sai.')
    last = odd['last']
    if last is not None:
        kit.need(isinstance(last, dict) and last.get('script') in ids and last.get('good') in (True, False, None)
                 and last.get('how') in REACTIONS, 'Kết quả chuyện oái oăm sai.')
        kit.text(last.get('outcome'), 600, 0)
