"""👮 Công an phường: the beat overlay (design §4.4). New optional steps rolled at task start, never in make_task.

* **Phong bì**: on a lost-and-found, a mediation or a patrol, someone may slip an envelope (rolled once from the task id).
  Từ chối · Lập biên bản hành vi đưa hối lộ (+1 Liêm chính) · Nhận (an accepted bribe: game/org.py bribe).
* **Procedure violations**: read from the task's own grading (consequences slips) after each action and turned into
  ⚠️ cảnh cáo on the org ladder (game/promotion.py violation); the duty book's ghi khống too.

State: ext.data['beat'] = {v, day, offers: [{t: task id, k: offer id, a: answer|None}]} (a new optional key: builds
without it keep and ignore it; it is today's only). Content tuples here are new: no existing pool grows.
"""
from __future__ import annotations

from . import kit

ID = 'police'
CHANCE = .3
OFFERS_MAX = 12
ANSWERS = ('refuse', 'report', 'take')

# kind → offers (id, emoji, who, text). The honest answer is never rewarded with xu; Liêm chính is the reward.
OFFERS = {
    'lost': (('lo_thanks', '💵', 'Người tới nhận', 'Dúi tờ 200 nghìn vào tay bạn: “Cán bộ cầm uống cà phê, trả nhanh giúp em nhé.”'),
             ('lo_gift', '🎁', 'Người tới nhận', 'Đặt hộp bánh kẹp phong bì lên bàn: “Chút lòng thành, khỏi hỏi nhiều cho mệt.”')),
    'dispute': (('dp_side', '✉️', 'Một bên tranh chấp', 'Kéo bạn ra góc: “Phong bì này, cán bộ nghiêng về nhà tôi chút nhé.”'),
                ('dp_dinner', '🍻', 'Một bên tranh chấp', 'Nháy mắt: “Xong vụ này tôi mời cán bộ một bữa, có ‘quà’ mang về.”')),
    'patrol': (('pt_vendor', '☕', 'Chủ sạp lấn chiếm', 'Đẩy ly cà phê kèm phong bì: “Anh bỏ qua cho em vụ lấn vỉa hè nhé.”'),
               ('pt_karaoke', '🎤', 'Chủ quán karaoke', 'Nhét phong bì vào túi áo bạn: “Tối nay anh em mở muộn chút, cán bộ thông cảm.”')),
}
OFFER_INDEX = {o[0]: (k, o) for k, rows in OFFERS.items() for o in rows}
LABELS = {'refuse': '🙅 Từ chối, nói rõ quy định', 'report': '📝 Lập biên bản hành vi đưa hối lộ', 'take': '💵 Nhận'}

# (kind, slip code) → violation code (game/org_content.VIOLATIONS). Conditions that need the task are in detect().
PLAIN = {('desk', 'skim'): 'skip_check', ('desk', 'rush'): 'skip_check', ('desk', 'queue'): 'unfair',
         ('child', 'post'): 'privacy', ('dispute', 'threat'): 'threat', ('calls', 'blind'): 'no_callback'}


def initial() -> dict:
    return dict(v=1, day=0, offers=[])


def state(d: dict, day: int) -> dict:
    b = d.get('beat')
    if not isinstance(b, dict):
        b = d['beat'] = initial()
    if b['day'] != day:
        b.update(day=day, offers=[])
    return b


def roll(t: dict) -> str | None:
    """The task's envelope, if any (pure: from the task id)."""
    rows = OFFERS.get(t.get('kind'))
    if not rows:
        return None
    r = kit.rng(ID, 'beat', t['id'])
    if r.random() >= CHANCE:
        return None
    return rows[r.randrange(len(rows))][0]


def offer_of(b: dict, tid: str) -> dict | None:
    return next((o for o in b['offers'] if o['t'] == tid), None)


def maybe_offer(d: dict, c: dict, t: dict) -> dict | None:
    """After the task's first step: someone may try an envelope (once per task)."""
    if t.get('stage') != 'open' or not t.get('known'):
        return None
    b = state(d, c['day'])
    if offer_of(b, t['id']) or len(b['offers']) >= OFFERS_MAX:
        return None
    k = roll(t)
    if not k:
        return None
    o = dict(t=t['id'], k=k, a=None)
    b['offers'].append(o)
    return o


def detect(t: dict, new: set) -> str | None:
    """The violation the task's new slips amount to (one per action), or None."""
    k = t.get('kind')
    seen = set(t.get('seen') or ())
    for code in sorted(new):
        v = PLAIN.get((k, code))
        if v:
            return v
        if k == 'lost' and code in ('thin', 'wrong_owner') and sum(1 for x in seen if x.startswith('q:')) < 2:
            return 'no_verify'
        if k == 'child' and code in ('thin', 'wrong_adult') and sum(1 for x in seen if x.startswith('v:')) < 2:
            return 'no_verify'
        if k == 'patrol' and code.startswith('unsafe'):
            return 'skip_step'
        if k == 'patrol' and code.startswith('bad'):
            return 'wrong_penalty'
        if k == 'calls' and code.startswith('under') and f'cb:{code[5:]}' not in seen:
            return 'no_callback'
    return None


def public(d: dict, c: dict) -> dict:
    b = d.get('beat')
    if not isinstance(b, dict) or b.get('day') != c.get('day'):
        return dict(offers=[])
    rows = []
    for o in b['offers']:
        kind, x = OFFER_INDEX[o['k']]
        rows.append(dict(t=o['t'], id=o['k'], emoji=x[1], who=x[2], text=x[3], a=o['a'],
                         options=[dict(id=a, label=LABELS[a]) for a in ANSWERS]))
    return dict(offers=rows)


def validate(d: dict) -> None:
    if 'beat' not in d:
        return
    b = d['beat']
    bad = 'Dữ liệu phong bì sai.'
    kit.need(isinstance(b, dict) and set(b) == {'v', 'day', 'offers'} and b['v'] == 1, bad)
    kit.integer(b['day'], 0, 10**9)
    kit.need(isinstance(b['offers'], list) and len(b['offers']) <= OFFERS_MAX, bad)
    ids = set()
    for o in b['offers']:
        kit.need(isinstance(o, dict) and set(o) == {'t', 'k', 'a'} and o['k'] in OFFER_INDEX and (o['a'] is None or o['a'] in ANSWERS), bad)
        kit.text(o['t'], 80)
        ids.add(o['t'])
    kit.need(len(ids) == len(b['offers']), bad)
