"""🚔 Báo công an: report an NPC's star review to the police (the owner, 09/10: "cho phép người dân báo công an nhé,
báo công an thì sẽ có tỷ lệ được tăng * nếu đánh giá của NPC vô lý, và có khi được cộng tiền nữa nhé").

Vô lý (unreasonable) is judged only from what the server wrote down with the review (feedback.make_review): the
stars shown are below the review's true grade `fb['fair']` (what the job's own criteria earned), and the player did
not cause the drop (no reviewer 'revise_down' after a reply). Fakes, wrong shops, stars tapped by mistake, threats,
demands, a perfect job remembered wrong, a bad-day reviewer shaving a star, an ungrounded gripe: all vô lý. A review
whose stars match the facts (mistakes included) is reasonable: the police say so and nothing changes, at no cost.

For a vô lý review the police confirm with a hidden chance (CONFIRM_PCT): the stars go up to the true grade (the
rating and day averages read the feed, so they follow at once), and sometimes (PAY_PCT of those) a small bồi thường
lands in the wallet (a Sổ ví row). Otherwise "chưa đủ cơ sở": nothing changes. Odds are never shown or sent.

🚔 Tố cáo sai sự thật (owner 09/10: "tố cáo sai thì bị bắt tù 1 ngày trong game"): a report on a review the police
find reasonable (verdict 'fair') sends the reporter to the trại tạm giữ for JAIL_DAYS jail day JAIL_PCT of the time
(jail_roll, seeded from the review like the other rolls; game/jail.py). A vô lý review that is only "chưa đủ cơ sở"
never does. Nothing about the chance is shown or sent.

Once per review, only NPC reviews with a thread, written in the last COP_DAYS days, at most COP_PER_DAY a day. The
rolls are seeded from the review and the outcome is stored in `fb['cop']` = {day, verdict, before, after, pay}, so a
retry never rolls again. Rollback: 1.9.27 (4533ee17) ignores unknown keys of a review's feedback and accepts the
'incident' Sổ ví kind, so these saves still load there (tests/test_review_police.py OldServer).
"""
from __future__ import annotations

# Tunables (never shown to players).
COP_DAYS = 3            # a review written today or in the two days before
COP_PER_DAY = 3         # reports a day at one workplace (its own day counter)
CONFIRM_PCT = 60        # a vô lý review: the police confirm it this often
PAY_PCT = 30            # of the confirmed ones: a bồi thường too
PAY_BASE = 20           # bồi thường: PAY_BASE + PAY_PER_STAR per star given back + 0..PAY_SPREAD×5, at most PAY_MAX
PAY_PER_STAR = 15
PAY_SPREAD = 4
PAY_MAX = 100
JAIL_PCT = 25           # a reasonable review reported anyway: the reporter is held this often (tố cáo sai sự thật)
JAIL_DAYS = 1
NOT_HERE = ('pagoda', 'police')     # the pagoda's visitors write impressions; the police do not report to themselves
VERDICTS = ('raised', 'unproven', 'fair')
WALLET_KIND = 'incident'            # a Sổ ví kind 1.9.27 already accepts (⚖️), the label brings its own 🚔


def _fb():
    from . import feedback
    return feedback


def target(post: dict) -> int | None:
    """The stars a fair review would carry, or None when the review is reasonable (judged from server data only)."""
    fb = post.get('feedback') or {}
    stars, fair = post.get('stars'), fb.get('fair')
    if type(stars) is not int or type(fair) is not int or stars >= fair:
        return None
    if any(r.get('role') == 'customer' and r.get('decision') == 'revise_down' for r in fb.get('thread') or []):
        return None                     # lowered after the player's own reply: that one is on the player
    return fair


def why_not(post: dict, career: str | None, day: int | None) -> str | None:
    """Why this review cannot be reported to the police (None: it can). The daily limit is checked by the action."""
    F = _fb()
    fb = post.get('feedback')
    if not fb or post.get('kind') != 'review' or post.get('npc') == 'player':
        return 'Chỉ báo công an được đánh giá của người khác viết cho bạn.'
    if fb.get('cop'):
        return 'Bạn đã báo công an về đánh giá này rồi.'
    if career in NOT_HERE or fb.get('own') or F._kind(fb) == 'pile_on':
        return 'Đánh giá này không báo công an được.'
    if type(post.get('stars')) is not int:
        return 'Đánh giá này đã được gỡ.'
    if post['stars'] >= 5:
        return 'Đánh giá năm sao rồi, không cần báo công an.'
    if fb.get('status') == 'awaiting':
        return 'Chờ người viết trả lời trước đã.'
    if F.can_police(post):
        return 'Lời đe dọa đòi tiền: lưu bằng chứng và trình báo trước đã.'
    if type(day) is int and type(post.get('day')) is int and post['day'] < day - (COP_DAYS - 1):
        return f'Chỉ báo công an được đánh giá trong {COP_DAYS} ngày gần đây.'
    return None


def today(c: dict) -> int:
    return sum(1 for p in c['feed'] if ((p.get('feedback') or {}).get('cop') or {}).get('day') == c['day'])


def left(c: dict) -> int:
    return max(0, COP_PER_DAY - today(c))


def _roll(post: dict, what: str) -> int:
    fb = post['feedback']
    return _fb()._hash('cop', what, post['id'], fb.get('task', ''), post.get('day', 0)) % 100


def verdict(post: dict) -> tuple[str, int, int]:
    """(verdict, stars after, bồi thường) for this review: seeded, the same on every call."""
    stars, fair = post['stars'], target(post)
    if fair is None:
        return 'fair', stars, 0
    if _roll(post, 'confirm') >= CONFIRM_PCT:
        return 'unproven', stars, 0
    pay = 0
    if _roll(post, 'pay') < PAY_PCT:
        pay = min(PAY_MAX, PAY_BASE + PAY_PER_STAR * (fair - stars) + 5 * (_roll(post, 'amount') % (PAY_SPREAD + 1)))
    return 'raised', fair, pay


def jail_roll(post: dict) -> bool:
    """A reasonable review reported anyway: is the reporter held for tố cáo sai sự thật? Seeded. Tests patch it."""
    return _roll(post, 'jail') < JAIL_PCT


def stars_text(n: int) -> str:
    return '⭐' * n


def action(s: dict, c: dict, career: str, p: dict) -> dict:
    from . import engine as e
    F = _fb()
    need = e.need
    post = next((f for f in c['feed'] if f.get('id') == p.get('post')), None)
    need(post is not None, 'Không thấy đánh giá này.')
    fb = post.get('feedback') or {}
    need(not fb.get('cop'), 'Bạn đã báo công an về đánh giá này rồi.')
    need(today(c) < COP_PER_DAY, f'Hôm nay bạn đã báo công an đủ {COP_PER_DAY} lần rồi. Để mai nhé.')
    why = why_not(post, career, c['day'])
    need(why is None, why or '')
    before = post['stars']
    v, after, pay = verdict(post)
    fb['cop'] = dict(day=c['day'], verdict=v, before=before, after=after, pay=pay)
    e.metric(c, 'reviews_cop')
    who = post.get('author') or 'người viết'
    word = F._cv.term(career, 'review', 'đánh giá') or 'đánh giá'
    if v == 'raised':
        post['stars'] = after
        e.cs_restar(c, post, before, after)  # a customer-care person's card remembers that visit's stars too
        fb['status'] = 'closed'
        fb['pending'] = None
        e.metric(c, 'reviews_cop_raised')
        msg = f'🚔 Công an xác minh: {word} của {who} không đúng sự thật. Đã sửa thành {stars_text(after)} (★{before} → ★{after}).'
        if pay:
            j = s.get('journey')
            label = f'🚔 Bồi thường {word} sai sự thật · {who}'
            if isinstance(j, dict) and type(j.get('wallet')) is int and isinstance(j.get('history'), list):
                from . import journey as jr
                jr._wallet(j, pay, WALLET_KIND, label, career)
            else:
                e.money(s, c, pay, label, post['id'])
            msg += f' +{pay} xu bồi thường vào ví.'
        e.log(s, c, 'feedback', f'Công an xác minh {word} của {who} sai sự thật: ★{before} → ★{after}.', post.get('npc'), post['id'])
    elif v == 'unproven':
        msg = '🚔 Công an đã xem xét, chưa đủ cơ sở để kết luận. Sao giữ nguyên.'
    else:
        msg = f'🚔 Công an đã đối chiếu: {word} này hợp lý, khớp với sổ ghi hôm đó. Sao giữ nguyên.'
        j = s.get('journey')
        if isinstance(j, dict) and j.get('story') and jail_roll(post):
            from . import jail
            days = jail.arrest(j, 'cop', JAIL_DAYS)
            if days:
                msg += f' Tố cáo sai sự thật: bạn bị tạm giữ {days} ngày để làm rõ.'
                e.log(s, c, 'feedback', f'Bị tạm giữ {days} ngày vì tố cáo sai sự thật về {word} của {who}.', post.get('npc'), post['id'])
                return dict(message=msg, cop=v, stars=after, paid=pay, celebrate=False, jail=days)
    return dict(message=msg, cop=v, stars=after, paid=pay, celebrate=v == 'raised')


def public(post: dict, career: str | None, day: int | None) -> dict:
    """What the client sees: can it be reported, and the stored outcome (never a chance)."""
    fb = post['feedback']
    out = dict(can_cop=why_not(post, career, day) is None)
    cop = fb.get('cop')
    if cop:
        out['cop'] = {k: cop.get(k) for k in ('day', 'verdict', 'before', 'after', 'pay')}
    return out


def validate(fb: dict) -> None:
    from .engine import need, integer
    cop = fb.get('cop')
    if cop is None:
        return
    need(isinstance(cop, dict) and set(cop) == {'day', 'verdict', 'before', 'after', 'pay'} and cop['verdict'] in VERDICTS,
         'Hồ sơ báo công an sai.')
    integer(cop['day'], 1, 100000)
    integer(cop['before'], 1, 5)
    integer(cop['after'], 1, 5)
    integer(cop['pay'], 0, PAY_MAX)
    need(cop['after'] >= cop['before'] and (cop['verdict'] == 'raised' or (cop['after'] == cop['before'] and cop['pay'] == 0)),
         'Hồ sơ báo công an sai.')
