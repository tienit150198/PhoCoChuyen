"""🎓 Thi chứng chỉ: study for a certificate and sit its exam (story mode).

A certificate belongs to the player (s['journey']), not to one workplace: each
group covers related hired jobs (certificate_content.GROUPS). Holding it raises
the hire chance for those jobs (employment._evaluate reads `boosted`).

Flow, on the journey clock (life days):
* `jr_cert_enrol` {cert, mode, career?}: one course at a time. `class` = evening
  class, tuition from the wallet (a retake or a higher-score attempt costs half
  of it, rounded up), exam opens CLASS_DAYS later; `self` = free self-study,
  SELF_DAYS later. Nobody is soft-locked by a thin wallet.
* While studying: lesson notes and a practice quiz (browser only, separate bank).
* `jr_cert_answer` {question, option}: the exam paper (DRAW questions drawn at
  enrolment, seeded) opens on `ready`; the last answer grades it. PASS_MARK right
  answers earn the certificate. A retake means studying again (that is the
  cooldown) and draws a new paper.
* `jr_cert_drop` {confirm}: leave the course (no refund).

Save shape (stable; the leaderboard reads `certificates`):
  journey.certificates = {group_id: {score, best, earned_day, attempts}}
      score/best: points 0–100 of the last / best exam (right answers × 100 ÷ DRAW,
      rounded half up); earned_day: life day of the first pass, or None;
      attempts: exams sat (≥ 1: a row exists only after a sitting).
  journey.study = None | {cert, mode, start, ready, fee, career, paper:{qs, answers, attempt}}
  journey.cert_paper = None | {cert, qs, answers, right, score, passed, day, attempt}  (last graded paper)
"""
from __future__ import annotations

from .jsoncopy import tree_copy
import random
import re

from . import certificate_content as CC
from . import days as days_

GROUPS = CC.GROUPS
INDEX = {g['id']: g for g in GROUPS}
# Hired jobs only: a craft certificate (hire=False, e.g. Chứng chỉ làm kem) gives its `perk` instead of the hire bonus.
BY_CAREER = {cid: g['id'] for g in GROUPS if g.get('hire', True) for cid in g['careers']}
KEY = {g['id']: {q['id']: q for q in g['bank']} for g in GROUPS}

# The owner: "có chứng chỉ thì tỷ lệ đậu tăng 50%". Read as +50 percentage points on the
# hire chance of a matching job, capped so a little luck always remains (see `boosted`).
CERT_BONUS_PP = 50
CERT_CAP_PCT = 95
# The owner: "thi chứng chỉ cho nhẹ nhàng, gợi ý dễ". A short open-book paper with a free
# 💡 hint on every question (content(): one wrong option greyed out + the lesson line to recall).
CLASS_DAYS = 0          # crash class (paid): study and sit the exam the same day
SELF_DAYS = 1           # free self-study: the exam opens the next life day
DRAW = 6                # exam questions per paper
PASS_MARK = 4           # right answers needed
MODES = ('class', 'self')
REC_KEYS = {'score', 'best', 'earned_day', 'attempts'}
STUDY_KEYS = {'cert', 'mode', 'start', 'ready', 'fee', 'career', 'paper'}
PAPER_KEYS = {'cert', 'qs', 'answers', 'right', 'score', 'passed', 'day', 'attempt'}


def boosted(base_pct: int) -> int:
    """Hire chance (0–100) of a matching job when the player holds the certificate:
    +CERT_BONUS_PP percentage points, capped at CERT_CAP_PCT, never below the base
    (a sure hire stays sure). Change this one function to switch to ×1.5."""
    base_pct = max(0, min(100, int(base_pct)))
    if base_pct >= 100:
        return 100
    return max(base_pct, min(CERT_CAP_PCT, base_pct + CERT_BONUS_PP))


def points(right: int, draw: int = DRAW) -> int:
    """Right answers → 0–100 points, rounded half up."""
    return (200 * int(right) + draw) // (2 * draw)


PASS_POINTS = points(PASS_MARK)


def group_of(career: str | None) -> str | None:
    return BY_CAREER.get(career)


def earned(j: dict | None, gid: str | None) -> bool:
    rec = ((j or {}).get('certificates') or {}).get(gid) if gid else None
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def held_for(s: dict, career: str) -> str | None:
    """The certificate id that raises the hire chance for `career`, if the player holds it."""
    gid = group_of(career)
    return gid if gid and earned(s.get('journey'), gid) else None


def tuition(gid: str) -> int:
    return int(INDEX[gid]['fee'])


def retake_fee(gid: str) -> int:
    """A review class before a retake (or a try for a higher score): half the tuition, rounded up."""
    return (int(INDEX[gid]['fee']) + 1) // 2


def fee(j: dict, gid: str, mode: str) -> int:
    if mode == 'self':
        return 0
    rec = (j.get('certificates') or {}).get(gid)
    return retake_fee(gid) if rec and rec.get('attempts') else tuition(gid)


def _core():
    from . import engine
    return engine


def _places(gid: str) -> str:
    from .content import CAREER_META
    return ', '.join(CAREER_META.get(cid, {}).get('place', cid) for cid in INDEX[gid]['careers'])


def _draw(j: dict, gid: str, attempt: int) -> list[str]:
    rng = random.Random(f"cert|{j.get('seed', 0)}|{gid}|{attempt}|{j.get('life_day', 1)}")
    return rng.sample(sorted(KEY[gid]), DRAW)


# ---------------------------------------------------------------- actions (jr_cert_*)
def action(s: dict, name: str, p: dict) -> dict:
    from .content import CAREERS
    e = _core()
    need = e.need
    j = s['journey']
    need(j['story'], 'Thi chứng chỉ có trong hành trình.')
    if name == 'jr_cert_enrol':
        gid = p.get('cert')
        need(gid in INDEX, 'Chứng chỉ không tồn tại.')
        g = INDEX[gid]
        mode = p.get('mode')
        need(mode in MODES, 'Chọn học lớp buổi tối hoặc tự học.')
        study = j['study']
        need(study is None, f'Bạn đang học {INDEX[study["cert"]]["name"]}. Thi xong hoặc bỏ khóa đó trước nhé.' if study else '')
        rec = j['certificates'].get(gid)
        need(not (rec and rec['best'] >= 100), f'Bạn đã đạt điểm tối đa ở {g["name"]} rồi.')
        cost = fee(j, gid, mode)
        from . import bank as bk   # 🏦 p['pay']: 'auto' | 'cash' | 'card' | 'joint' (game/bank.py)
        need(j['wallet'] >= cost or (cost and bk.can_pay(s, cost, p.get('pay', 'auto'))),
             f'Ví chưa đủ {cost} xu học phí. Tự học thì miễn phí, chỉ chậm hơn một ngày.')
        career = p.get('career') if p.get('career') in CAREERS else None
        paid = bk.pay(s, cost, f'Học phí · {g["name"]}', method=p.get('pay', 'auto'), kind='study', career=career) if cost else None
        days = CLASS_DAYS if mode == 'class' else SELF_DAYS
        attempt = (rec['attempts'] if rec else 0) + 1
        j['study'] = dict(cert=gid, mode=mode, start=j['life_day'], ready=j['life_day'] + days, fee=cost, career=career,
                          paper=dict(qs=_draw(j, gid, attempt), answers={}, attempt=attempt))
        how = (f'Đã quẹt thẻ {cost} xu học phí lớp cấp tốc' if paid and paid['method'] != 'cash' else
               f'Đã đóng {cost} xu học phí lớp cấp tốc') if cost else 'Bạn mượn sách về tự học'
        if not days:
            return dict(message=f'{how} · {g["name"]}. Đọc lướt bài học rồi vào thi luôn nhé: được mở sách, câu nào phân vân thì bấm 💡 Gợi ý.')
        return dict(message=f'{how} · {g["name"]}. Bài thi mở {days_.when_day(s, j["life_day"] + days)}; '
                            f'trong lúc chờ, đọc bài và làm thử vài câu nhé.')
    if name == 'jr_cert_drop':
        study = j['study']
        need(study, 'Bạn không có khóa học nào đang mở.')
        need(p.get('confirm') is True, 'Xác nhận bỏ khóa học.')
        j['study'] = None
        return dict(message=f'Đã bỏ khóa {INDEX[study["cert"]]["name"]}. Học phí đã đóng không được hoàn.')
    if name == 'jr_cert_answer':
        study = j['study']
        need(study, 'Bạn chưa đăng ký khóa học nào.')
        need(j['life_day'] >= study['ready'], f'Bài thi mở {days_.when_day(s, study["ready"])}. Làm một ngày ở đâu đó rồi quay lại nhé.')
        paper, bank = study['paper'], KEY[study['cert']]
        qid = p.get('question')
        need(qid in paper['qs'] and qid not in paper['answers'], 'Câu hỏi không hợp lệ hoặc đã trả lời.')
        need(p.get('option') in [o['id'] for o in bank[qid]['options']], 'Câu trả lời không hợp lệ.')
        paper['answers'][qid] = p['option']
        if len(paper['answers']) < len(paper['qs']):
            return dict(message=f'Đã trả lời câu {len(paper["answers"])}/{len(paper["qs"])}.')
        return _grade(s, j, study)
    raise e.GameError('Thao tác thi chứng chỉ không hợp lệ.', 'unknown_action')


def _grade(s: dict, j: dict, study: dict) -> dict:
    gid, paper = study['cert'], study['paper']
    g, bank = INDEX[gid], KEY[gid]
    right = sum(1 for q in paper['qs'] if paper['answers'].get(q) == bank[q]['answer'])
    score, passed = points(right), right >= PASS_MARK
    rec = j['certificates'].get(gid)
    first = not earned(j, gid)
    if rec is None:
        rec = j['certificates'][gid] = dict(score=0, best=0, earned_day=None, attempts=0)
    rec['attempts'] += 1
    rec['score'] = score
    rec['best'] = max(rec['best'], score)
    if passed and rec['earned_day'] is None:
        rec['earned_day'] = j['life_day']
    j['cert_paper'] = dict(cert=gid, qs=list(paper['qs']), answers=dict(paper['answers']), right=right, score=score, passed=passed,
                           day=j['life_day'], attempt=paper['attempt'])
    j['study'] = None
    head = f'{g["name"]}: đúng {right}/{DRAW} câu ({score} điểm).'
    out = dict(cert=dict(id=gid, right=right, draw=DRAW, score=score, passed=passed, earned_now=passed and first))
    if passed and first:
        gain = g['perk'] if g.get('perk') else f'tỷ lệ được nhận +{CERT_BONUS_PP}% ở {_places(gid)}.'
        out.update(message=f'{head} Đạt! {g["emoji"]} Chứng chỉ đã được cấp: {gain}', celebrate=True)
    elif passed:
        out.update(message=f'{head} Điểm cao nhất của bạn: {rec["best"]}.', celebrate=score >= rec['best'])
    else:
        out['message'] = (f'{head} Cần {PASS_MARK}/{DRAW} câu. Xem lời giải rồi thi lại: lớp ôn {retake_fee(gid)} xu '
                          f'(thi lại ngay hôm nay) hoặc tự học miễn phí (thi {days_.when_day(s, j["life_day"] + SELF_DAYS)}).')
    return out


# ---------------------------------------------------------------- views
def public(s: dict) -> dict:
    j = s['journey']
    study = j.get('study')
    view = None
    if isinstance(study, dict):
        view = tree_copy(study)
        view.update(ready_now=j['life_day'] >= study['ready'], days_left=max(0, study['ready'] - j['life_day']))
    paper = j.get('cert_paper')
    last = None
    if isinstance(paper, dict) and paper.get('cert') in KEY:
        bank = KEY[paper['cert']]
        last = {k: tree_copy(paper[k]) for k in ('cert', 'right', 'score', 'passed', 'day', 'attempt')}
        # The key stays on the server until a paper is graded; then it teaches.
        last['review'] = [dict(id=q, text=bank[q]['text'], picked=paper['answers'].get(q), answer=bank[q]['answer'],
                               ok=paper['answers'].get(q) == bank[q]['answer'], why=bank[q]['why'],
                               options={o['id']: o['label'] for o in bank[q]['options']}) for q in paper['qs']]
    return dict(certificates=tree_copy(j.get('certificates') or {}), study=view, cert_paper=last)


_WORD = re.compile(r'\w+', re.UNICODE)
_STOP = {'và', 'là', 'có', 'không', 'cho', 'của', 'một', 'khi', 'thì', 'rồi', 'bạn', 'khách', 'được', 'với', 'để',
         'các', 'những', 'trước', 'sau', 'đã', 'phải', 'ra', 'vào', 'lên', 'này', 'đó', 'nào', 'gì', 'hay', 'xu'}


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 1 and w not in _STOP and not w.isdigit()}


def hint(g: dict, q: dict) -> dict:
    """💡 The free hint for one exam question: `off` = one wrong option to grey out (fixed per
    question), `note` = index of the lesson line that best matches the question and its right
    answer. Shown only when the player taps 💡, never costs points."""
    wrong = sorted(o['id'] for o in q['options'] if o['id'] != q['answer'])
    off = wrong[sum(map(ord, q['id'])) % len(wrong)]
    right = next(o['label'] for o in q['options'] if o['id'] == q['answer'])
    want = _words(f"{q['text']} {right} {q['why']}")
    best = max(range(len(g['notes'])), key=lambda i: (len(want & _words(g['notes'][i])), -i))
    return dict(off=off, note=best)


def content() -> dict:
    """Static catalogue for the client: notes, practice (with answers: it is a separate
    bank), exam questions without their key."""
    return dict(
        bonus=CERT_BONUS_PP, cap=CERT_CAP_PCT, draw=DRAW, pass_mark=PASS_MARK, pass_points=PASS_POINTS,
        class_days=CLASS_DAYS, self_days=SELF_DAYS, by_career=dict(BY_CAREER),
        groups=[dict({k: g[k] for k in ('id', 'emoji', 'name', 'short', 'issuer', 'intro', 'notes', 'practice')},
                     careers=list(g['careers']), fee=tuition(g['id']), retake_fee=retake_fee(g['id']),
                     hire=g.get('hire', True), perk=g.get('perk', ''),
                     questions={q['id']: dict(text=q['text'], options=q['options'], hint=hint(g, q)) for q in g['bank']})
                for g in GROUPS])


def validate(s: dict) -> None:
    from .content import CAREERS
    e = _core()
    need, integer = e.need, e.integer
    j = s['journey']
    life_day = j['life_day']
    certs = j.get('certificates')
    need(isinstance(certs, dict) and set(certs) <= set(INDEX), 'Chứng chỉ không hợp lệ.')
    for gid, rec in certs.items():
        need(isinstance(rec, dict) and set(rec) == REC_KEYS, 'Chứng chỉ không hợp lệ.')
        integer(rec['score'], 0, 100)
        integer(rec['best'], rec['score'], 100)
        integer(rec['attempts'], 1, 10**6)
        if rec['earned_day'] is not None:
            integer(rec['earned_day'], 1, life_day)
            need(rec['best'] >= PASS_POINTS, 'Chứng chỉ chưa đủ điểm đạt.')
    study = j.get('study')
    if study is not None:
        need(isinstance(study, dict) and set(study) == STUDY_KEYS and study.get('cert') in INDEX and study.get('mode') in MODES,
             'Khóa học không hợp lệ.')
        integer(study['start'], 1, life_day)
        need(type(study['ready']) is int and study['ready'] == study['start'] + (CLASS_DAYS if study['mode'] == 'class' else SELF_DAYS),
             'Khóa học không hợp lệ.')
        integer(study['fee'], 0, 10**4)
        need(study['mode'] == 'class' or study['fee'] == 0, 'Tự học thì không có học phí.')
        need(study['career'] is None or study['career'] in CAREERS, 'Khóa học không hợp lệ.')
        paper = study['paper']
        need(isinstance(paper, dict) and set(paper) == {'qs', 'answers', 'attempt'}, 'Bài thi không hợp lệ.')
        _check_sheet(study['cert'], paper['qs'], paper['answers'])
        need(len(paper['answers']) < DRAW, 'Bài thi đã làm xong phải được chấm.')
        integer(paper['attempt'], 1, 10**6)
    last = j.get('cert_paper')
    if last is not None:
        need(isinstance(last, dict) and set(last) == PAPER_KEYS and last.get('cert') in INDEX, 'Bài thi đã chấm không hợp lệ.')
        _check_sheet(last['cert'], last['qs'], last['answers'])
        bank = KEY[last['cert']]
        right = sum(1 for q in last['qs'] if last['answers'].get(q) == bank[q]['answer'])
        need(len(last['answers']) == DRAW and last['right'] == right and last['score'] == points(right)
             and last['passed'] is (right >= PASS_MARK), 'Bài thi đã chấm không hợp lệ.')
        integer(last['day'], 1, life_day)
        integer(last['attempt'], 1, 10**6)
        need(last['cert'] in certs, 'Bài thi đã chấm không khớp chứng chỉ.')


def _check_sheet(gid: str, qs, answers) -> None:
    need = _core().need
    bank = KEY[gid]
    need(isinstance(qs, list) and len(qs) == DRAW and len(set(qs)) == DRAW and all(isinstance(q, str) and q in bank for q in qs),
         'Đề thi không hợp lệ.')
    need(isinstance(answers, dict) and set(answers) <= set(qs), 'Bài làm không hợp lệ.')
    for q, oid in answers.items():
        need(oid in [o['id'] for o in bank[q]['options']], 'Bài làm không hợp lệ.')
