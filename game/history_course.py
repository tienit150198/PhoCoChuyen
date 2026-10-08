"""📜 Học lịch sử Việt Nam: an easy, free course beside Học kế toán (feedback #255, 07/10: "học kế toán khó quá
... học lịch sử đi ạ").

Same machinery as game/accounting_school.py, kept small: twelve short lessons (game/history_content.py), each read
then two multiple-choice practice questions (graded on the server, retried freely, a wrong answer points back at the
lesson line to re-read), a final exam of one question per lesson, a certificate, and a small fair reward.

Commands (vs_*, "Việt sử"), each result carrying the course's own view (`history_view`, never in public_state):
* vs_view                      nothing changes, nothing is stored.
* vs_open {lesson}             marks the lesson read.
* vs_answer {lesson, question, option}   a practice question (the lesson must be read first).
* vs_exam_start                every lesson done; one question per lesson, drawn from (journey seed, attempt).
* vs_exam_answer {question, option}      the current question; the last one grades the paper.
* vs_exam_cancel {confirm}     drops the paper (the attempt still counts; progress and certificate stay).

Pass: PASS_RIGHT of DRAW right answers. Retakes are free. The first pass gives the certificate (date, serial)
and, in the story mode, the title 📜 Người kể sử (journey TITLES 'h_history') plus a one-off GIFT xu học bổng to
the wallet (kind 'study'). Nothing here ever costs xu.

Save: s['history_course'] is created by the first command that changes something (vs_open), never by migrate: a
save that never opened the course stays byte for byte what an older build wrote (older builds ignore the block).
  {v: 1,
   lessons: {lesson id: {read: True, solved: [practice question ids], tries: int}},
   attempts: int (exam papers started), best: 0–100,
   active: None | {attempt, qs: [question ids], answers: {qid: option}},     (answers in order, fewer than DRAW)
   last: None | {attempt, qs, answers, score},                              (the last graded paper, all answered)
   cert: None | {date 'YYYY-MM-DD', serial, score, gift: 0 | GIFT}}
"""
from __future__ import annotations

import hashlib
import random
import re

from . import history_content as HC
from .jsoncopy import tree_copy

LESSONS = HC.LESSONS
LESSON_INDEX = {l['id']: l for l in LESSONS}
PRACTICE = {lid: {q['id']: q for q in l['practice']} for lid, l in LESSON_INDEX.items()}
EXAM = {q['id']: dict(q, lesson=l['id']) for l in LESSONS for q in l['exam']}
DRAW = len(LESSONS)          # one exam question per lesson
PASS_RIGHT = 8               # of DRAW (12): two in three, gentler than the accounting exams (80/100)
GIFT = 30                    # xu, once, story mode only: a small học bổng, never a sink
TITLE = 'h_history'          # game/journey.py TITLES
KEYS = {'v', 'lessons', 'attempts', 'best', 'active', 'last', 'cert'}
CERT_ID = 'history'          # the serial's group code: PCC-HIS-…
COURSE_NAME = 'Lịch sử Việt Nam'


def points(right: int) -> int:
    """Right answers → 0–100 points, rounded half up (as game/certificates.py)."""
    return (200 * int(right) + DRAW) // (2 * DRAW)


PASS_POINTS = points(PASS_RIGHT)


def initial() -> dict:
    return dict(v=1, lessons={}, attempts=0, best=0, active=None, last=None, cert=None)


def _block(s: dict) -> dict:
    """Read-only: the block, or an empty one for a save that never opened the course (not stored)."""
    b = s.get('history_course')
    return b if isinstance(b, dict) else initial()


def _need(ok, message):
    from .engine import need
    need(ok, message)


def lesson_done(b: dict, lid: str) -> bool:
    rec = b['lessons'].get(lid)
    return bool(rec and rec['read'] and set(rec['solved']) == set(PRACTICE[lid]))


def course_done(b: dict) -> bool:
    return all(lesson_done(b, l['id']) for l in LESSONS)


def certified(s: dict) -> bool:
    b = s.get('history_course')
    return isinstance(b, dict) and isinstance(b.get('cert'), dict)


def _seed(s: dict) -> int:
    return int((s.get('journey') or {}).get('seed', 0) or 0)


def _draw(seed: int, attempt: int) -> list[str]:
    """One exam question per lesson, in a shuffled order: fixed by (journey seed, attempt)."""
    rng = random.Random(hashlib.sha256(f'history|{seed}|{attempt}'.encode()).hexdigest())
    qs = [rng.choice(sorted(q['id'] for q in l['exam'])) for l in LESSONS]
    rng.shuffle(qs)
    return qs


def _right(paper: dict) -> int:
    return sum(1 for q in paper['qs'] if paper['answers'].get(q) == EXAM[q]['answer'])


# ---------------------------------------------------------------- the hint of a wrong practice answer
_WORD = re.compile(r'\w+', re.UNICODE)
_STOP = {'và', 'là', 'có', 'không', 'của', 'một', 'khi', 'thì', 'được', 'với', 'để', 'các', 'những', 'năm', 'ngày',
         'nào', 'gì', 'đâu', 'ai', 'ở', 'theo', 'sau', 'trước', 'mấy', 'lần', 'nhà', 'quân', 'nước', 'tên'}


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 1 and w not in _STOP}


def hint_line(lesson: dict, q: dict) -> int:
    """Index of the lesson line that best matches the question and its right answer (the line to re-read)."""
    right = next(o['label'] for o in q['options'] if o['id'] == q['answer'])
    want = _words(f"{q['text']} {right} {q['why']}")
    return max(range(len(lesson['body'])), key=lambda i: (len(want & _words(lesson['body'][i])), -i))


# ---------------------------------------------------------------- commands
def action(s: dict, name: str, p: dict) -> dict:
    result = _action(s, name, p)
    view = p.get('view') if isinstance(p.get('view'), dict) else {}
    result['history_view'] = public(s, view.get('lesson'))
    return result


def _action(s: dict, name: str, p: dict) -> dict:
    if name == 'vs_view':
        return dict(message='📜 Lịch sử Việt Nam: đọc bài ngắn, trả lời câu hỏi, thi lấy chứng nhận.')
    lid = p.get('lesson')
    if name == 'vs_open':
        _need(isinstance(lid, str) and lid in LESSON_INDEX, 'Bài học không tồn tại.')
        b = s.setdefault('history_course', initial())
        rec = b['lessons'].setdefault(lid, dict(read=True, solved=[], tries=0))
        rec['read'] = True
        return dict(message=f'{LESSON_INDEX[lid]["emoji"]} {LESSON_INDEX[lid]["title"]}: đọc bài rồi trả lời hai câu hỏi nhé.')
    b = s.get('history_course')
    if name == 'vs_answer':
        lesson = LESSON_INDEX.get(lid) if isinstance(lid, str) else None
        rec = b['lessons'].get(lid) if lesson and isinstance(b, dict) else None
        _need(rec and rec['read'], 'Mở bài và đọc trước khi trả lời nhé.')
        q = PRACTICE[lid].get(p.get('question')) if isinstance(p.get('question'), str) else None
        _need(q, 'Câu hỏi không thuộc bài này.')
        _need(q['id'] not in rec['solved'], 'Câu này bạn đã trả lời đúng rồi.')
        _need(p.get('option') in [o['id'] for o in q['options']], 'Câu trả lời không hợp lệ.')
        rec['tries'] = min(rec['tries'] + 1, 10**6)
        if p['option'] != q['answer']:
            return dict(correct=False, hint=hint_line(lesson, q), message='Chưa đúng. Đọc lại câu được tô vàng trong bài rồi thử lại nhé.')
        rec['solved'].append(q['id'])
        done = lesson_done(b, lid)
        why = q['why']
        return dict(correct=True, lesson_done=done, message=f'Đúng rồi! {why} Bạn đã xong bài này.' if done else f'Đúng rồi! {why}')
    if name == 'vs_exam_start':
        _need(isinstance(b, dict) and course_done(b), 'Học xong cả 12 bài (đúng hết câu hỏi mỗi bài) rồi mới thi nhé.')
        _need(b['active'] is None, 'Bạn đang làm dở một bài thi.')
        b['attempts'] += 1
        b['active'] = dict(attempt=b['attempts'], qs=_draw(_seed(s), b['attempts']), answers={})
        return dict(message=f'Bắt đầu thi: {DRAW} câu, đúng từ {PASS_RIGHT} câu là đạt. Thi lại miễn phí.')
    if name == 'vs_exam_cancel':
        _need(isinstance(b, dict) and b['active'] is not None and p.get('confirm') is True, 'Xác nhận bỏ bài thi đang làm.')
        b['active'] = None
        return dict(message='Đã bỏ bài thi. Bài đã học và chứng nhận (nếu có) vẫn giữ nguyên.')
    if name == 'vs_exam_answer':
        paper = b.get('active') if isinstance(b, dict) else None
        _need(isinstance(paper, dict), 'Bạn chưa bắt đầu bài thi.')
        qid = paper['qs'][len(paper['answers'])]
        _need(p.get('question') == qid, 'Trả lời câu hiện tại; câu đã nộp không sửa lại được.')
        _need(p.get('option') in [o['id'] for o in EXAM[qid]['options']], 'Câu trả lời không hợp lệ.')
        paper['answers'][qid] = p['option']
        if len(paper['answers']) < DRAW:
            return dict(message=f'Đã ghi câu {len(paper["answers"])}/{DRAW}.')
        return _grade(s, b, paper)
    _need(False, 'Thao tác học lịch sử không tồn tại.')


def _grade(s: dict, b: dict, paper: dict) -> dict:
    right = _right(paper)
    score, passed = points(right), right >= PASS_RIGHT
    b['active'] = None
    b['last'] = dict(attempt=paper['attempt'], qs=list(paper['qs']), answers=dict(paper['answers']), score=score)
    b['best'] = max(b['best'], score)
    head = f'Đúng {right}/{DRAW} câu ({score} điểm).'
    out = dict(exam=dict(right=right, draw=DRAW, score=score, passed=passed))
    if not passed:
        out['message'] = f'{head} Cần đúng {PASS_RIGHT} câu. Xem lời giải, đọc lại bài rồi thi lại miễn phí nhé.'
        return out
    if b['cert'] is not None:
        out.update(message=f'{head} Đạt! Điểm cao nhất của bạn: {b["best"]}.', celebrate=score >= b['best'])
        return out
    from . import certificates as ct
    j = s.get('journey') or {}
    story = bool(j.get('story'))
    b['cert'] = dict(date=ct.today_vn(), serial=ct.serial(_seed(s), CERT_ID, paper['attempt']), score=score,
                     gift=GIFT if story else 0)
    if story:
        from . import journey as jr
        jr._wallet(j, GIFT, 'study', f'Học bổng · {COURSE_NAME}')
        if TITLE not in j['titles']:
            j['titles'][TITLE] = j['life_day']
            jr._news(j, 'titles', 'titles', [TITLE])
        out.update(message=f'{head} Đạt! 📜 Chứng nhận Lịch sử Việt Nam đã được cấp, kèm danh hiệu 📜 Người kể sử và học bổng {GIFT} xu vào ví.',
                   celebrate=True, journey=dict(chapters=[], titles=[TITLE]))
    else:
        out.update(message=f'{head} Đạt! 📜 Chứng nhận Lịch sử Việt Nam đã được cấp.', celebrate=True)
    return out


# ---------------------------------------------------------------- views
def _safe(q: dict, solved: bool = False) -> dict:
    """A question without its key; a solved practice question shows its answer and why."""
    view = dict(id=q['id'], text=q['text'], options=tree_copy(q['options']), solved=solved)
    if solved:
        view.update(answer=q['answer'], why=q['why'])
    return view


def summary(s: dict) -> dict:
    b = _block(s)
    return dict(done=sum(lesson_done(b, l['id']) for l in LESSONS), total=len(LESSONS), certified=certified(s))


def public(s: dict, lesson: str | None = None) -> dict:
    """The course's own view: the lesson index, the lesson on screen (`lesson`, if any), the exam in progress
    (its current question, no key), the last graded paper with its review, the certificate."""
    b = _block(s)
    index = []
    for l in LESSONS:
        rec = b['lessons'].get(l['id']) or {}
        index.append(dict(id=l['id'], emoji=l['emoji'], era=l['era'], title=l['title'], read=bool(rec.get('read')),
                          solved=len(rec.get('solved') or []), questions=len(l['practice']), done=lesson_done(b, l['id'])))
    out = dict(name=COURSE_NAME, lessons=index, done=sum(x['done'] for x in index), total=len(LESSONS),
               draw=DRAW, pass_right=PASS_RIGHT, gift=GIFT, attempts=b['attempts'], best=b['best'],
               can_exam=course_done(b) and b['active'] is None, lesson=None, active=None, review=None,
               cert=tree_copy(b['cert']) if b['cert'] else None)
    if isinstance(lesson, str) and lesson in LESSON_INDEX:
        l = LESSON_INDEX[lesson]
        rec = b['lessons'].get(lesson) or {}
        solved = set(rec.get('solved') or [])
        out['lesson'] = dict(id=l['id'], emoji=l['emoji'], era=l['era'], title=l['title'], body=list(l['body']),
                             read=bool(rec.get('read')), done=lesson_done(b, lesson),
                             questions=[_safe(q, q['id'] in solved) for q in l['practice']])
    if b['active']:
        paper = b['active']
        at = len(paper['answers'])
        out['active'] = dict(at=at, total=DRAW, question=_safe(EXAM[paper['qs'][at]]))
    if b['last']:
        last = b['last']
        out['review'] = dict(score=last['score'], right=_right(last), passed=_right(last) >= PASS_RIGHT, questions=[
            dict(_safe(EXAM[q], True), picked=last['answers'][q], ok=last['answers'][q] == EXAM[q]['answer'])
            for q in last['qs']])
    return out


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    if 'history_course' not in s:
        return   # never opened (older saves, new players): nothing stored
    from .engine import integer
    b = s['history_course']
    _need(isinstance(b, dict) and set(b) == KEYS and type(b['v']) is int and b['v'] == 1, 'Tiến độ học lịch sử không hợp lệ.')
    _need(isinstance(b['lessons'], dict) and set(b['lessons']) <= set(LESSON_INDEX), 'Tiến độ có bài học lạ.')
    for lid, rec in b['lessons'].items():
        _need(isinstance(rec, dict) and set(rec) == {'read', 'solved', 'tries'} and rec['read'] is True, 'Dữ liệu bài học không hợp lệ.')
        solved = rec['solved']
        _need(isinstance(solved, list) and len(set(solved)) == len(solved) and all(isinstance(q, str) and q in PRACTICE[lid] for q in solved),
              'Câu đã trả lời không hợp lệ.')
        integer(rec['tries'], len(solved), 10**6)
    integer(b['attempts'], 0, 10**6)
    integer(b['best'], 0, 100)
    seed = _seed(s)

    def paper(x, complete):
        _need(isinstance(x, dict) and set(x) == ({'attempt', 'qs', 'answers', 'score'} if complete else {'attempt', 'qs', 'answers'}),
              'Bài thi lịch sử không hợp lệ.')
        integer(x['attempt'], 1, b['attempts'])
        _need(x['qs'] == _draw(seed, x['attempt']), 'Đề thi lịch sử không khớp lần thi.')
        answers = x['answers']
        _need(isinstance(answers, dict) and set(answers) == set(x['qs'][:len(answers)]), 'Bài làm sai thứ tự.')
        _need(len(answers) == DRAW if complete else len(answers) < DRAW, 'Bài thi chưa đủ hoặc đã hết câu.')
        for q, o in answers.items():
            _need(o in [opt['id'] for opt in EXAM[q]['options']], 'Bài làm không hợp lệ.')
        if complete:
            _need(x['score'] == points(_right(x)), 'Điểm thi lịch sử không khớp bài làm.')

    if b['active'] is not None:
        paper(b['active'], False)
        _need(b['active']['attempt'] == b['attempts'] and course_done(b), 'Bài thi lịch sử chưa đủ điều kiện.')
    if b['last'] is not None:
        paper(b['last'], True)
        _need(b['best'] >= b['last']['score'], 'Điểm cao nhất không khớp.')
    cert = b['cert']
    if cert is not None:
        _need(isinstance(cert, dict) and set(cert) == {'date', 'serial', 'score', 'gift'}, 'Chứng nhận lịch sử không hợp lệ.')
        _need(isinstance(cert['date'], str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', cert['date']) and isinstance(cert['serial'], str)
              and len(cert['serial']) <= 40, 'Chứng nhận lịch sử không hợp lệ.')
        integer(cert['score'], PASS_POINTS, 100)
        _need(cert['gift'] in (0, GIFT) and b['best'] >= cert['score'] and b['attempts'] >= 1 and course_done(b),
              'Chứng nhận lịch sử không hợp lệ.')
