"""Job applications for employed careers (v0.4).

Some jobs are not a shop you open: a teacher or an accountant first has to be
hired. The flow mirrors real life: read the posting → build an honest CV from
what you actually did in the game → cover letter → interview questions →
reference check → offer (negotiate once) → probation → official contract.
Everything is fictional; salaries are game coins.

Work only starts after the interview and a signed offer. The one exception is
luck: sometimes the big boss meets you (right after you apply, or by chance at
the end of a day elsewhere) and offers the job directly. The roll is seeded
from the save, so reloading never rerolls it.

v0.5: the pipeline is data. A posting may list its `stages`; besides CV,
letter and interview there are a licence `exam` (pharmacy, tour guide: pass
mark, retake the next day, the certificate is kept), a situational `test`
(customer care) and a hands-on `trial` with the owner (salon, pet care,
repair, delivery). Postings without `stages` keep the old CV → letter →
interview flow and scoring. Content lives in employment_content.py.

v0.9 (story mode): after a failed interview there are two more ways in.
* 🎓 A certificate (game/certificates.py) for the career's group: below the pass
  score the application still gets a seeded, stored roll at certificates.boosted(0)
  (+50 percentage points). A safety-fatal step or a failed reference check is
  never covered, and a licence exam is never replaced.
* 🚪 Đi cửa sau (`job_backdoor`): pay a small fee from the wallet (one day of the
  posting's starting wage) and a helper "lo giúp": hired at the starting wage, on
  the usual probation. Once per workplace; a colleague's remark on day one.
The re-apply cooldown counts life days in the story (a place you were never hired
at has no days of its own, so a failed interview used to lock it for good).
"""
from __future__ import annotations

import os
import random
import re as _re
import unicodedata as _ud

from . import employment_content as EC
from . import archive as ar

STRENGTHS = [
    dict(id='careful', name='Cẩn thận, tỉ mỉ', emoji='🔍'),
    dict(id='communication', name='Giao tiếp rõ ràng', emoji='💬'),
    dict(id='patience', name='Kiên nhẫn', emoji='🌱'),
    dict(id='numbers', name='Nhạy với số liệu', emoji='🔢'),
    dict(id='teamwork', name='Làm việc nhóm', emoji='🤝'),
    dict(id='creative', name='Sáng tạo', emoji='🎨'),
    dict(id='tech', name='Dùng phần mềm văn phòng', emoji='💻'),
    dict(id='calm', name='Bình tĩnh khi áp lực', emoji='🧘'),
    dict(id='learning', name='Ham học hỏi', emoji='📚'),
]
STRENGTH_IDS = {x['id'] for x in STRENGTHS}

# CV lines must be backed by what really happened in the save (reference check).
CLAIMS = [
    dict(id='fresh', text='Mới vào nghề, sẵn sàng học việc', need=None),
    dict(id='served5', text='Đã hoàn thành ít nhất 5 công việc ở nghề này', need=('served', 5)),
    dict(id='served15', text='Đã hoàn thành ít nhất 15 công việc ở nghề này', need=('served', 15)),
    dict(id='perfect3', text='Ít nhất 3 lần làm việc không sai sót', need=('perfect', 3)),
    dict(id='situations', text='Từng xử lý tình huống phát sinh với khách/phụ huynh', need=('situations', 1)),
    dict(id='replies', text='Có kinh nghiệm phản hồi góp ý của khách', need=('review_replies', 2)),
    dict(id='other', text='Có kinh nghiệm ở một nghề khác trong phố (≥3 việc)', need=('other', 3)),
]
CLAIM_INDEX = {x['id']: x for x in CLAIMS}

LETTER_SLOTS = [
    dict(id='why', title='Vì sao chọn nơi này', options=[
        dict(id='specific', label='Nêu một điều cụ thể về nơi tuyển dụng mà bạn đã tìm hiểu', score=3),
        dict(id='generic', label='“Tôi muốn một môi trường chuyên nghiệp, năng động.”', score=1),
        dict(id='wrong', label='Dán lại thư cũ… vẫn còn tên nơi tuyển dụng khác', score=-2)]),
    dict(id='example', title='Một ví dụ về bản thân', options=[
        dict(id='story', label='Kể một việc cụ thể đã làm và kết quả kiểm chứng được', score=3),
        dict(id='adjectives', label='Liệt kê năm tính từ khen bản thân', score=0),
        dict(id='salary', label='Nói ngay mức lương mong muốn', score=-1)]),
    dict(id='close', title='Lời kết', options=[
        dict(id='available', label='Nói rõ thời gian có thể bắt đầu và cảm ơn', score=2),
        dict(id='demand', label='“Mong nhận phản hồi trong 24 giờ.”', score=-1),
        dict(id='none', label='Không viết lời kết', score=0)]),
]

GENERIC_QUESTIONS = {
    'weakness': dict(text='Điểm bạn còn cần cải thiện là gì?', options=[
        dict(id='honest', label='Nêu một điểm thật và cách mình đang sửa', score=3, note='Người phỏng vấn thấy bạn tự biết mình.'),
        dict(id='perfect', label='“Tôi quá cầu toàn.”', score=1, note='Câu trả lời quen thuộc, không nói được gì.'),
        dict(id='none', label='“Tôi không có điểm yếu.”', score=0, note='Nghe thiếu thật thà.')]),
    'mistake': dict(text='Kể về một lần bạn làm sai và đã xử lý thế nào?', options=[
        dict(id='own', label='Nhận lỗi, sửa, báo người liên quan, rút quy trình', score=3, note='Bạn cho thấy trách nhiệm.'),
        dict(id='blame', label='Kể lỗi là do đồng nghiệp', score=0, note='Người phỏng vấn nhíu mày.'),
        dict(id='hide', label='Nói chưa từng sai', score=1, note='Khó tin.')]),
    'conflict': dict(text='Nếu bạn không đồng ý với quản lý thì sao?', options=[
        dict(id='data', label='Trao đổi riêng, mang dữ kiện, vẫn tôn trọng quyết định cuối', score=3, note='Chín chắn.'),
        dict(id='silent', label='Im lặng làm theo dù thấy sai', score=1, note='An toàn nhưng thiếu đóng góp.'),
        dict(id='public', label='Phản đối ngay giữa cuộc họp', score=0, note='Dễ gây căng thẳng.')]),
}

TEACHER_QUESTIONS = {
    't_parent': dict(text='Một phụ huynh nhắn tin gay gắt lúc 22 giờ. Bạn làm gì?', options=[
        dict(id='boundary', label='Nhắn ngắn hẹn trao đổi trong giờ hành chính, chuẩn bị sổ lớp', score=3, note='Hiệu trưởng gật đầu: ranh giới rõ, không bỏ mặc.'),
        dict(id='argue', label='Trả lời ngay, giải thích tới khuya', score=1, note='Tận tâm nhưng dễ kiệt sức.'),
        dict(id='ignore', label='Không trả lời', score=0, note='Dễ thành chuyện lớn.')]),
    't_diverse': dict(text='Lớp có bạn học nhanh, có bạn học chậm. Bạn tổ chức tiết học thế nào?', options=[
        dict(id='diff', label='Cùng mục tiêu, nhiều cách: hình ảnh, làm thử, kể chuyện; nhóm hỗ trợ', score=3, note='Đúng tinh thần dạy học phân hóa.'),
        dict(id='fast', label='Dạy theo nhóm giỏi để kịp chương trình', score=1, note='Nhóm chậm sẽ bị bỏ lại.'),
        dict(id='slow', label='Dạy thật chậm cho mọi người', score=1, note='Nhóm nhanh sẽ chán.')]),
    't_event': dict(text='Trường giao lớp bạn tổ chức Trung thu. Việc đầu tiên?', options=[
        dict(id='ask', label='Hỏi mong muốn của lớp, kiểm dị ứng và quỹ lớp', score=3, note='Chuẩn bị từ người tham gia.'),
        dict(id='buy', label='Đặt mua bánh và đèn cho nhanh', score=1, note='Nhanh nhưng có thể bỏ sót ai đó.'),
        dict(id='collect', label='Thu thêm tiền phụ huynh cho hoành tráng', score=0, note='Tạo áp lực cho gia đình.')]),
}

POSTINGS = {
    'teacher': [
        dict(id='tch-public', org='Trường Tiểu học Mầm Nắng', kind='public', title='Giáo viên chủ nhiệm lớp 2',
             salary=(55, 75), probation_days=3, wants=['patience', 'communication', 'creative'],
             perks=['Nghỉ hè', 'Đồng nghiệp hỗ trợ', 'Lịch ổn định'], culture='Trường công lập, sĩ số đông, coi trọng nề nếp và phối hợp phụ huynh.',
             questions=['t_diverse', 't_parent', 'mistake'], reference=True),
        dict(id='tch-center', org='Trung tâm Kỹ năng Sao Nhỏ', kind='private', title='Giáo viên lớp kỹ năng cuối tuần',
             salary=(60, 90), probation_days=2, wants=['creative', 'communication', 'calm'],
             perks=['Lương theo buổi cao', 'Lớp nhỏ', 'Phụ huynh kỳ vọng cao'], culture='Tư thục, lớp 8–10 bạn, phụ huynh phản hồi nhiều và nhanh.',
             questions=['t_event', 't_parent', 'conflict'], reference=True),
        dict(id='tch-trial', org='Lớp học cộng đồng Góc Phố', kind='community', title='Tình nguyện viên dạy thử',
             salary=(35, 45), probation_days=1, wants=['patience', 'learning'],
             perks=['Nhận ngay', 'Không phỏng vấn dài', 'Lương thấp'], culture='Lớp học miễn phí cuối tuần do khu phố tổ chức.',
             questions=['t_diverse'], reference=False),
    ],
}
POSTINGS.update(EC.POSTINGS)
QUESTIONS = {**GENERIC_QUESTIONS, **TEACHER_QUESTIONS, **EC.QUESTIONS}
EXAMS = EC.EXAMS

LEGACY_STAGES = ('cv', 'letter', 'interview')
STAGES = ('exam', 'cv', 'letter', 'interview', 'test', 'trial')
STEP_STAGES = {'interview': 'questions', 'test': 'test', 'trial': 'trial'}   # stage → posting key of its step ids
STAGE_NAMES = dict(exam='Thi chứng chỉ', cv='CV', letter='Thư ứng tuyển', interview='Phỏng vấn',
                   test='Bài thử tình huống', trial='Làm thử tại tiệm')
FATAL_CAP = 45
PASS_SCORE = 60            # an application from this score gets an offer
LATER_FIELDS = {'certs', 'backdoor'}   # job fields added after v0.4: older saves may lack them


def stages(post: dict) -> list[str]:
    return list(post.get('stages') or LEGACY_STAGES)


def stage_steps(post: dict, stage: str) -> list[str]:
    key = STEP_STAGES.get(stage)
    return list(post.get(key) or []) if key else []


def all_steps(post: dict) -> list[str]:
    return [q for st in stages(post) for q in stage_steps(post, st)]


def _next_stage(post: dict, stage: str) -> str | None:
    rows = stages(post)
    i = rows.index(stage) if stage in rows else len(rows)
    return rows[i + 1] if i + 1 < len(rows) else None


def exam(career: str) -> dict | None:
    return EXAMS.get(career)


def has_cert(job: dict, career: str) -> bool:
    ex = exam(career)
    return bool(ex) and any(x.get('id') == ex['id'] for x in job.get('certs') or [])


def _needs_exam(job: dict, career: str, post: dict) -> bool:
    return 'exam' in stages(post) and not has_cert(job, career)


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


_PLUGINS: dict | None = None  # game.careers.PLUGINS, looked up once (import cycle)


def _plugin_employment(career: str) -> dict | None:
    global _PLUGINS
    if _PLUGINS is None:
        from .careers import PLUGINS
        _PLUGINS = PLUGINS
    mod = _PLUGINS.get(career)
    return mod.SPEC.get('employment') if mod else None


def postings(career: str) -> list[dict]:
    spec = _plugin_employment(career)
    if spec:
        return spec['postings']
    return POSTINGS.get(career, [])


def question(career: str, qid: str) -> dict | None:
    spec = _plugin_employment(career)
    if spec and qid in spec.get('questions', {}):
        return spec['questions'][qid]
    return QUESTIONS.get(qid)


_REQUIRED: dict = {}  # career -> required(): fixed content, asked for every career on every view


def required(career: str) -> bool:
    got = _REQUIRED.get(career) if type(career) is str else None
    if got is None:
        got = bool(postings(career))
        if type(career) is str and len(_REQUIRED) < 1000:
            _REQUIRED[career] = got
    return got


def initial() -> dict:
    return dict(status='none', employer=None, title=None, salary=0, offer=None, probation=False, probation_left=0, hired_day=0,
                application=None, cooldown_day=0, history=[], days_worked=0, reviews_during_probation=[], extended=False,
                certs=[], backdoor=None)


def hired_record(career: str, posting_id: str | None = None, day: int = 1) -> dict:
    """Used by migration of started careers and by tests: an already-signed contract
    (and, for a licensed job, the certificate that goes with it)."""
    rows = postings(career)
    x = initial()
    if rows:
        p = next((r for r in rows if r['id'] == posting_id), rows[0])
        x.update(status='hired', employer=p['id'], title=p['title'], salary=p['salary'][1], probation=False, hired_day=day)
        ex = exam(career)
        if ex:
            x['certs'] = [dict(id=ex['id'], day=day, score=ex['draw'])]
    return x


def migrate(s: dict) -> None:
    """Engine hook (engine.migrate_state): a workplace you already worked at before
    it started hiring keeps you — signed contract, no probation. Only a job record
    that was never used is touched, so quitting later is never undone."""
    cs = s.get('careers')
    if not isinstance(cs, dict):
        return
    for cid, c in cs.items():
        if not isinstance(c, dict) or not required(cid):
            continue
        job = c.get('job')
        if not isinstance(job, dict) or job.get('status') != 'none' or job.get('application') or job.get('history'):
            continue
        worked = c.get('started') is True or (c.get('metrics') or {}).get('served', 0) > 0
        if not worked:
            continue
        day = c['day'] if type(c.get('day')) is int and c['day'] >= 1 else 1
        c['job'] = hired_record(cid, None, day)
        c['job']['history'] = [dict(day=day, event='migrated', posting=c['job']['employer'])]


def first_day_hire(s: dict, c: dict, career: str) -> dict | None:
    """Onboarding (v0.7): in the story, a first-chapter workplace that hires (delivery)
    takes a brand-new player on at once, on probation, so day one is play and not a CV
    plus a trial. Only a job record that was never used; probation still applies and the
    other postings keep the full pipeline. Returns the line to show, or None."""
    j = s.get('journey') or {}
    if not j.get('story') or not required(career):
        return None
    try:
        from .journey import CH_UNLOCKS
    except ImportError:
        return None
    if career not in CH_UNLOCKS.get(1, ()):
        return None
    job = c.get('job')
    if not isinstance(job, dict) or job.get('status') != 'none' or job.get('application') or job.get('history'):
        return None
    post = postings(career)[0]
    day = c['day'] if type(c.get('day')) is int and c['day'] >= 1 else 1
    job.update(status='hired', employer=post['id'], title=post['title'], salary=post['salary'][0], probation=True,
               probation_left=post['probation_days'], hired_day=day, application=None, offer=None, extended=False,
               reviews_during_probation=[])
    job['history'] = [dict(day=day, event='first_day', posting=post['id'])]
    boss = _cap(_boss(career, post))
    return f'{boss} ở {post["org"]}: “Ngày đầu cứ chạy thử với chị, vừa làm vừa học. Thử việc {post["probation_days"]} ngày nha.”'


def _posting(career: str, pid) -> dict | None:
    return next((p for p in postings(career) if p['id'] == pid), None)


BOSS_APPLY = [
    'Đúng lúc bạn nộp hồ sơ, {boss} {org} đi ngang quầy lễ tân, đọc lướt CV rồi mời bạn vào làm luôn.',
    'Người ngồi cạnh bạn ở phòng chờ hóa ra là {boss} {org}. Hai người nói chuyện mười phút, và bạn được mời nhận việc ngay.',
    'Cô {boss} {org} từng nghe hàng xóm khen bạn. Hồ sơ vừa tới, cô gọi điện mời bạn đi làm, khỏi phỏng vấn.',
]
BOSS_MEET = [
    'Cuối ngày, một vị khách lịch sự nán lại trò chuyện. Hóa ra đó là {boss} {org}, và ông mời bạn về làm {title}.',
    'Bạn giúp một bác lớn tuổi nhặt tập hồ sơ bị rơi. Bác là chủ {org} và muốn mời bạn về làm {title}.',
    'Một chị khách quen để lại danh thiếp: {boss} {org}. Chị nhắn: “Bên chị đang cần {title}, em qua làm luôn nhé.”',
]


def _boss(career: str, post: dict) -> str:
    if post.get('boss'):
        return post['boss']
    if career == 'teacher':
        return 'hiệu trưởng'
    return 'tổng giám đốc' if post.get('kind') in ('corp', 'group') else 'giám đốc'


def _rng(*parts) -> random.Random:
    return random.Random('|'.join(map(str, parts)))


def _boss_chance(s: dict, career: str) -> float:
    """About one in ten, a bit more for people with experience elsewhere."""
    others = sum(1 for k, v in s['careers'].items() if k != career and v.get('metrics', {}).get('served', 0) >= 3)
    return min(.2, .08 + .02 * others)


def _unlocked(s: dict, career: str) -> bool:
    try:
        from . import journey
    except ImportError:
        return True
    check = getattr(journey, 'is_unlocked', None)
    return bool(check(s, career)) if check else True


def _direct_offer(s: dict, c: dict, career: str, post: dict, line: str) -> None:
    from . import engine as e
    low, high = post['salary']
    salary = low + round((high - low) * .5)
    job = c['job']
    job['status'] = 'offer'
    job['application'] = dict(posting=post['id'], stage=stages(post)[-1], strengths=[], claims=[], letter={}, answers={},
                              score=None, honest=None, notes=[], feedback=[line], direct=True)
    job['offer'] = dict(salary=salary, negotiated=False, score=None, day=c['day'], direct=True)
    job['history'] = ar.last(job['history'] + [dict(day=c['day'], event='direct_offer', posting=post['id'])], 40, 'job.history', c)
    e.metric(c, 'job_offers')
    e.log(s, c, 'job', line)


def meet_boss(s: dict, career: str, day: int) -> dict | None:
    """Called when a day ends somewhere: rarely, a boss from an office job you
    haven't got yet invites you in. Returns what happened, for the day summary."""
    rng = _rng('boss-meet', career, day, s.get('seq', 0))
    if rng.random() >= .04:
        return None
    options = [(k, p) for k in sorted(s['careers']) if k != career and required(k) and _unlocked(s, k)   # (a place still needing its exam is not)
               and s['careers'][k].get('job', {}).get('status') in ('none', 'rejected') for p in postings(k)
               if not _needs_exam(s['careers'][k]['job'], k, p)]   # luck never replaces a licence exam
    if not options:
        return None
    k, post = rng.choice(options)
    lines = EC.BOSS_MEET if post.get('boss') else BOSS_MEET
    line = _cap(rng.choice(lines).format(org=post['org'], title=post['title'].lower(), boss=_boss(k, post)))
    _direct_offer(s, s['careers'][k], k, post, line)
    return dict(career=k, org=post['org'], title=post['title'], text=line)


def _claim_ok(s: dict, c: dict, career: str, cid: str) -> bool:
    need = CLAIM_INDEX[cid]['need']
    if not need:
        return True
    metric, goal = need
    if metric == 'other':
        return any(k != career and v['metrics'].get('served', 0) >= goal for k, v in s['careers'].items())
    return c['metrics'].get(metric, 0) >= goal


def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    job = c['job']
    need(required(career), 'Nghề này tự mở tiệm, không cần xin việc.')
    if name == 'job_apply':
        need(job['status'] in ('none', 'rejected'), 'Bạn đang có hồ sơ hoặc đã có việc.')
        need(today(s, c) >= job['cooldown_day'], f'Nơi tuyển dụng hẹn phỏng vấn lại {_dy().when_day(s, job["cooldown_day"], c)}.', 'retry_later')
        post = _posting(career, p.get('posting'))
        need(post, 'Tin tuyển dụng không tồn tại.')
        job['status'] = 'applying'
        first = stages(post)[0]
        if first == 'exam' and has_cert(job, career):
            first = _next_stage(post, 'exam')
        job['application'] = dict(posting=post['id'], stage=first, strengths=[], claims=[], letter={}, answers={}, score=None, honest=None, notes=[])
        if first == 'exam':
            job['application']['exam'] = _draw_exam(career, job, c['day'])
        rng = _rng('boss-apply', career, post['id'], c['day'], len(job['history']))
        if rng.random() < _boss_chance(s, career) and not _needs_exam(job, career, post):
            lines = EC.BOSS_APPLY if post.get('boss') else BOSS_APPLY
            line = _cap(rng.choice(lines).format(org=post['org'], boss=_boss(career, post)))
            _direct_offer(s, c, career, post, line)
            return dict(message=line, celebrate=True, direct_offer=True)
        if first == 'exam':
            ex = exam(career)
            return dict(message=f'Đã mở hồ sơ: {post["title"]} · {post["org"]}. Bước đầu: bài thi “{ex["name"]}”, cần đúng {ex["pass_mark"]}/{ex["draw"]} câu.')
        return dict(message=f'Đã mở hồ sơ ứng tuyển: {post["title"]} · {post["org"]}.')
    if name == 'job_quick':
        # Dev tooling only (browser sweeps): players always go through the interview.
        need(os.environ.get('MNL_DEV') == '1', 'Cần phỏng vấn xong và ký thư mời trước khi đi làm.')
        need(job['status'] in ('none', 'rejected', 'applying'), 'Bạn đã có việc.')
        post = _posting(career, p.get('posting'))
        need(post, 'Tin tuyển dụng không tồn tại.')
        need(p.get('confirm') is True, 'Xác nhận nhận việc thử với mức lương thử việc.')
        job.update(status='hired', employer=post['id'], title=post['title'], salary=post['salary'][0], probation=True,
                   probation_left=post['probation_days'] + 1, hired_day=c['day'], application=None, offer=None, extended=False, reviews_during_probation=[])
        if _needs_exam(job, career, post):
            job['certs'] = list(job.get('certs') or []) + [dict(id=exam(career)['id'], day=c['day'], score=exam(career)['pass_mark'])]
        job['history'] = ar.last(job['history'] + [dict(day=c['day'], event='quick', posting=post['id'])], 40, 'job.history', c)
        e.log(s, c, 'job', f'Nhận việc thử tại {post["org"]}: lương khởi điểm {post["salary"][0]} xu/ngày, thử việc {post["probation_days"] + 1} ngày.')
        return dict(message=f'Bạn bắt đầu thử việc tại {post["org"]}. Làm tốt sẽ được ký chính thức!', celebrate=True)
    if name == 'job_quit':
        need(job['status'] == 'hired', 'Bạn chưa có việc để nghỉ.')
        need(not c['open'], 'Kết thúc ca rồi mới xin nghỉ nhé.')
        need(p.get('confirm') is True, 'Xác nhận nghỉ việc.')
        job['history'] = ar.last(job['history'] + [dict(day=c['day'], event='quit', posting=job['employer'])], 40, 'job.history', c)
        keep, door = job['history'], job.get('backdoor')
        c['job'] = initial()
        c['job'].update(history=keep, backdoor=door)
        return dict(message='Đã bàn giao và nghỉ việc. Bạn có thể ứng tuyển nơi khác.')
    if name == 'job_backdoor':
        return _backdoor(s, c, career, p)
    app = job.get('application')
    need(job['status'] in ('applying', 'offer') and app, 'Chưa có hồ sơ ứng tuyển nào đang mở.')
    post = _posting(career, app['posting'])
    need(post, 'Tin tuyển dụng không còn.')
    if name == 'job_withdraw':
        c['job']['status'] = 'none'
        c['job']['application'] = None
        c['job']['offer'] = None
        return dict(message='Đã rút hồ sơ.')
    if name == 'job_exam':
        need(job['status'] == 'applying' and app['stage'] == 'exam' and isinstance(app.get('exam'), dict), 'Chưa tới bài thi chứng chỉ.')
        ex, sheet = exam(career), app['exam']
        qid = p.get('question')
        need(qid in sheet['qs'] and qid not in sheet['answers'], 'Câu hỏi không hợp lệ hoặc đã trả lời.')
        row = next(x for x in ex['bank'] if x['id'] == qid)
        need(p.get('option') in [o['id'] for o in row['options']], 'Câu trả lời không hợp lệ.')
        sheet['answers'][qid] = p['option']
        if len(sheet['answers']) < len(sheet['qs']):
            return dict(message=f'Đã trả lời câu {len(sheet["answers"])}/{len(sheet["qs"])}.')
        return _grade_exam(s, c, career, post, app)
    if name == 'job_cv':
        need(app['stage'] == 'cv', 'CV đã nộp.')
        strengths = p.get('strengths')
        need(isinstance(strengths, list) and 1 <= len(strengths) <= 3 and len(set(strengths)) == len(strengths) and all(x in STRENGTH_IDS for x in strengths), 'Chọn 1–3 điểm mạnh.')
        claims = p.get('claims')
        need(isinstance(claims, list) and 1 <= len(claims) <= 4 and len(set(claims)) == len(claims) and all(x in CLAIM_INDEX for x in claims), 'Chọn 1–4 dòng kinh nghiệm.')
        app.update(strengths=strengths, claims=claims)
        return _advance(s, c, career, post, app, 'Đã hoàn thiện CV.')
    if name == 'job_letter':
        need(app['stage'] == 'letter', 'Chưa tới bước thư ứng tuyển.')
        parts = p.get('parts')
        need(isinstance(parts, dict) and set(parts) == {x['id'] for x in LETTER_SLOTS}, 'Chọn đủ ba phần của thư.')
        for slot in LETTER_SLOTS:
            need(parts[slot['id']] in [o['id'] for o in slot['options']], 'Nội dung thư không hợp lệ.')
        app['letter'] = dict(parts)
        return _advance(s, c, career, post, app, 'Thư đã gửi.')
    if name == 'job_answer':
        stage = app['stage']
        need(job['status'] == 'applying' and stage in STEP_STAGES, 'Chưa tới buổi phỏng vấn.')
        steps = stage_steps(post, stage)
        qid = p.get('question')
        need(qid in steps and qid not in app['answers'], 'Câu hỏi không hợp lệ hoặc đã trả lời.')
        q = question(career, qid)
        opt = next((o for o in q['options'] if o['id'] == p.get('option')), None)
        need(opt, 'Câu trả lời không hợp lệ.')
        ask = _open_ask(app)
        if ask:
            ask['status'] = 'skipped'   # moving on without answering the follow-up
        app['answers'][qid] = opt['id']
        app['notes'] = ar.last(app['notes'] + [opt['note']], 40, 'job.notes', c)
        remaining = any(x not in app['answers'] for x in steps)
        idx = _after_answer(s, c, career, post, app, stage, qid, opt, remaining)
        if remaining:
            out = dict(message=opt['note'])
        elif _next_stage(post, stage):
            out = _advance(s, c, career, post, app, opt['note'])
        else:
            out = _evaluate(s, c, career, post, app, opt['note'])
        if idx is not None:
            out['talk'] = idx
        return out
    if name == 'job_followup':
        return _followup(s, c, career, post, app, p)
    if name == 'job_negotiate':
        need(job['status'] == 'offer' and job['offer'] and not job['offer']['negotiated'], 'Chỉ thương lượng một lần khi có thư mời.')
        o = job['offer']
        o['negotiated'] = True
        if (o.get('direct') or (app['score'] or 0) >= 80) and o['salary'] < post['salary'][1]:
            o['salary'] = min(post['salary'][1], o['salary'] + max(3, round(o['salary'] * .08)))
            msg = f'{post["org"]} đồng ý nâng lên {o["salary"]} xu/ngày vì hồ sơ của bạn rất tốt.'
        else:
            msg = f'{post["org"]} giữ mức {o["salary"]} xu/ngày và hẹn xét lại sau thử việc.'
        return dict(message=msg)
    if name == 'job_accept':
        need(job['status'] == 'offer' and job['offer'], 'Chưa có thư mời nhận việc.')
        need(p.get('confirm') is True, 'Xác nhận ký hợp đồng thử việc.')
        o = job['offer']
        job.update(status='hired', employer=post['id'], title=post['title'], salary=o['salary'], probation=True, probation_left=post['probation_days'],
                   hired_day=c['day'], application=None, offer=None, extended=False, reviews_during_probation=[])
        job['history'] = ar.last(job['history'] + [dict(day=c['day'], event='hired', posting=post['id'])], 40, 'job.history', c)
        e.metric(c, 'jobs_hired')
        e.log(s, c, 'job', f'Ký hợp đồng thử việc tại {post["org"]}: {o["salary"]} xu/ngày.')
        return dict(message=f'Chào mừng bạn tới {post["org"]}! Thử việc {post["probation_days"]} ngày làm việc.', celebrate=True)
    if name == 'job_decline':
        need(job['status'] == 'offer', 'Chưa có thư mời.')
        c['job']['status'] = 'none'
        c['job']['application'] = None
        c['job']['offer'] = None
        return dict(message='Đã cảm ơn và từ chối thư mời.')
    raise e.GameError('Thao tác ứng tuyển không hợp lệ.')


NEXT_LINE = dict(
    exam='Tiếp theo: bài thi chứng chỉ.', cv='Tiếp theo: CV.', letter='Tiếp theo: thư ứng tuyển.',
    interview='{org} mời bạn phỏng vấn!', test='{Boss} mời bạn làm bài thử tình huống: một vị khách khó tính đang chờ.',
    trial='{Boss} hẹn bạn {trial}.')


def _advance(s: dict, c: dict, career: str, post: dict, app: dict, prefix: str) -> dict:
    nxt = _next_stage(post, app['stage'])
    if nxt is None:
        return _evaluate(s, c, career, post, app, prefix)
    app['stage'] = nxt
    boss = _boss(career, post)
    trial = post.get('trial_title', STAGE_NAMES['trial']).lower()
    return dict(message=prefix + ' ' + NEXT_LINE[nxt].format(org=post['org'], Boss=_cap(boss), trial=trial))


def _draw_exam(career: str, job: dict, day: int) -> dict:
    """Five questions from the bank; a retake (another attempt or day) draws again."""
    ex = exam(career)
    attempt = 1 + sum(1 for h in job.get('history', []) if h.get('event') in ('exam_failed', 'exam_passed'))
    rng = _rng('exam', career, attempt, day)
    qs = rng.sample([q['id'] for q in ex['bank']], ex['draw'])
    return dict(qs=qs, answers={}, score=None, passed=None, attempt=attempt)


def _grade_exam(s: dict, c: dict, career: str, post: dict, app: dict) -> dict:
    from . import engine as e
    job, ex, sheet = c['job'], exam(career), app['exam']
    key = {q['id']: q['answer'] for q in ex['bank']}
    right = sum(1 for q in sheet['qs'] if sheet['answers'].get(q) == key[q])
    passed = right >= ex['pass_mark']
    sheet.update(score=right, passed=passed)
    job['history'] = ar.last(job['history'] + [dict(day=c['day'], event='exam_passed' if passed else 'exam_failed', posting=post['id'], score=right)], 40, 'job.history', c)
    head = f'Bài thi “{ex["name"]}”: đúng {right}/{len(sheet["qs"])} câu (cần {ex["pass_mark"]}).'
    if passed:
        job['certs'] = ar.last(list(job.get('certs') or []) + [dict(id=ex['id'], day=c['day'], score=right)], 10, 'job.certs', c)
        e.metric(c, 'certs')
        e.log(s, c, 'job', f'Đạt {ex["name"]} ({right}/{len(sheet["qs"])}).')
        out = _advance(s, c, career, post, app, head + ' Đạt! Chứng chỉ đã được cấp.')
        out['celebrate'] = True
        out['exam'] = dict(score=right, passed=True)
        return out
    job['status'] = 'rejected'
    job['cooldown_day'] = today(s, c) + 1
    app['stage'] = 'closed'
    again = _dy().when_day(s, job['cooldown_day'], c)
    app['feedback'] = [head, f'Chưa đạt. Xem lại lời giải từng câu; thi lại được {again} với bộ câu hỏi khác.']
    return dict(message=head + f' Chưa đạt, thi lại được {again}.', exam=dict(score=right, passed=False))


def _evaluate(s: dict, c: dict, career: str, post: dict, app: dict, last_note: str) -> dict:
    from . import engine as e
    job = c['job']
    steps = all_steps(post)
    chosen = [next(o for o in question(career, q)['options'] if o['id'] == app['answers'][q]) for q in steps if q in app['answers']]
    qscore = sum(o['score'] for o in chosen)
    qmax = 3 * max(1, len(steps))
    match = len(set(app['strengths']) & set(post['wants']))
    if 'letter' in stages(post):
        letter = sum(next(o['score'] for o in slot['options'] if o['id'] == app['letter'][slot['id']]) for slot in LETTER_SLOTS)
        score = round(55 * qscore / qmax + 25 * max(0, letter) / 8 + 20 * min(match, 2) / 2)
    else:
        score = round(80 * qscore / qmax + 20 * min(match, 2) / 2)
    bonus = talk_bonus(app)
    score = max(0, min(100, score + bonus))
    honest = all(_claim_ok(s, c, career, x) for x in app['claims'])
    app['honest'] = honest
    app['score'] = score
    lines = []
    said = _talk_feedback(app)
    if said:
        lines.append(said)
    if post.get('reference') and not honest:
        bad = [CLAIM_INDEX[x]['text'] for x in app['claims'] if not _claim_ok(s, c, career, x)]
        lines.append('Kiểm tra tham chiếu: CV ghi “' + bad[0] + '” nhưng hồ sơ thực tế chưa có.')
        score = min(score, 40)
        app['score'] = score
    if app['letter'].get('why') == 'wrong':
        lines.append('Thư ứng tuyển còn tên nơi khác — người đọc bật cười nhưng trừ điểm cẩn thận.')
    fatal = [o for o in chosen if o.get('fatal')]
    if fatal:
        what = 'buổi làm thử' if 'trial' in stages(post) else 'bài thử'
        lines.append(f'{_cap(_boss(career, post))} dừng {what} ở lựa chọn “{fatal[0]["label"]}”: một bước không an toàn là chưa thể nhận.')
        score = min(score, FATAL_CAP)
        app['score'] = score
    trial = 'trial' in stages(post)
    chance = None
    if score < PASS_SCORE:
        # 🎓 A matching certificate: one seeded, stored roll (never for an unsafe step or a CV that failed the check).
        chance = _cert_roll(s, c, career, post, bool(fatal), bool(post.get('reference') and not honest))
        if chance:
            app['chance'] = chance
            lines.append(_chance_line(chance))
    lucky = bool(chance and chance['hired'])
    if score >= PASS_SCORE or lucky:
        low, high = post['salary']
        salary = low + round((high - low) * max(0, min(1, (score - PASS_SCORE) / 35)))
        job['status'] = 'offer'
        job['offer'] = dict(salary=salary, negotiated=False, score=score, day=c['day'])
        e.metric(c, 'job_offers')
        cert = _cert_name(chance) if lucky else ''
        if trial and lucky:
            msg = (f'Kết quả làm thử: {score}/100, chưa đủ {PASS_SCORE}. {_cap(_boss(career, post))} vẫn nhận bạn nhờ {cert}: '
                   f'lương cứng {salary} xu/ngày (thử việc {post["probation_days"]} ngày).')
        elif lucky:
            msg = (f'Kết quả: {score}/100, chưa đủ {PASS_SCORE}, nhưng nhờ {cert} (tỷ lệ nhận {chance["pct"]}%), {post["org"]} '
                   f'vẫn gửi thư mời với lương {salary} xu/ngày (thử việc {post["probation_days"]} ngày).')
        elif trial:
            msg = (f'Kết quả làm thử: {score}/100. {_cap(_boss(career, post))} nhận bạn làm {post["title"].lower()}: '
                   f'lương cứng {salary} xu/ngày (thử việc {post["probation_days"]} ngày).')
        else:
            msg = f'Kết quả: {score}/100. {post["org"]} gửi thư mời với lương {salary} xu/ngày (thử việc {post["probation_days"]} ngày).'
    else:
        job['status'] = 'rejected'
        job['cooldown_day'] = today(s, c) + 1
        job['history'] = ar.last(job['history'] + [dict(day=c['day'], event='rejected', posting=post['id'], score=score)], 40, 'job.history', c)
        app['stage'] = 'closed'
        if trial:
            msg = (f'Kết quả làm thử: {score}/100. {_cap(_boss(career, post))} cảm ơn bạn, hẹn tập thêm rồi thử lại '
                   f'{_dy().when_day(s, job["cooldown_day"], c)}.')
        else:
            msg = (f'Kết quả: {score}/100. {post["org"]} cảm ơn bạn và hẹn dịp khác. Bạn có thể ứng tuyển lại '
                   f'{_dy().when_day(s, job["cooldown_day"], c)}.')
    app['feedback'] = lines + [last_note]
    out = dict(message=msg, score=score, celebrate=score >= PASS_SCORE or lucky)
    if chance:
        out['chance'] = dict(chance)
    return out


# ---- two more ways in after a failed interview (v0.9, story mode) -------------------
def today(s: dict, c: dict) -> int:
    """The day the re-apply cooldown counts: life days in the story (a workplace you were
    never hired at has no working days of its own), the career's day elsewhere."""
    j = s.get('journey') or {}
    life = j.get('life_day')
    return life if j.get('story') and type(life) is int else c['day']


def hire_chance(score: int, certified: bool) -> int:
    """Chance (0–100) that an application with this score is hired: sure from PASS_SCORE,
    otherwise nothing, or certificates.boosted(0) with a matching certificate."""
    from . import certificates as ct
    if score >= PASS_SCORE:
        return 100
    return ct.boosted(0) if certified else 0


def _cert_roll(s: dict, c: dict, career: str, post: dict, fatal: bool, dishonest: bool) -> dict | None:
    from . import certificates as ct
    gid = ct.held_for(s, career)
    if not gid:
        return None
    blocked = 'fatal' if fatal else 'reference' if dishonest else None
    pct = 0 if blocked else hire_chance(0, True)
    seed = (s.get('journey') or {}).get('seed', 0)
    roll = _rng('cert-roll', seed, career, post['id'], today(s, c), len(c['job']['history'])).randrange(100)
    return dict(cert=gid, pct=pct, roll=roll, hired=roll < pct, blocked=blocked)


def _cert_name(chance: dict) -> str:
    from . import certificates as ct
    g = ct.INDEX[chance['cert']]
    return f'{g["emoji"]} {g["name"]}'


def _chance_line(chance: dict) -> str:
    name = _cert_name(chance)
    if chance['blocked'] == 'fatal':
        return f'{name} không bù được một bước làm mất an toàn.'
    if chance['blocked'] == 'reference':
        return f'{name} không bù được dòng CV chưa đúng sự thật.'
    if chance['hired']:
        return f'Có {name}: tỷ lệ nhận {chance["pct"]}%, và lần này bạn được nhận.'
    return f'Có {name}: tỷ lệ nhận {chance["pct"]}%, lần này chưa may.'


BACKDOOR_HELPERS = [
    'Cháu trai bà Tám quen {boss} ở {org}, bảo sẽ “lo giúp” một chút.',
    'Anh họ của cô Ba từng làm chung với {boss} ở {org}, bảo cứ để anh “lo giúp”.',
    'Em họ của anh Khoa quen người trong {org}, hứa “lo giúp” cho gọn.',
    'Chị dâu cô Lụa là chỗ quen với {boss} ở {org}, nhận “lo giúp” một suất.',
]
BACKDOOR_REMARKS = [
    'Đồng nghiệp nói nhỏ với nhau: “Nghe đâu vào bằng cửa sau đó…” Làm cho tốt rồi người ta sẽ quên thôi.',
    'Lúc thay đồ, một đồng nghiệp buông một câu: “Có người quen sướng thật ha.” Bạn cười trừ rồi xắn tay áo làm.',
    'Người làm ca trước đưa bạn cái tạp dề, nửa đùa nửa thật: “Người nhà của ai đó hả? Thôi làm đi rồi biết.”',
]


def backdoor_fee(post: dict) -> int:
    """Một số tiền ít: one day of the posting's starting wage, rounded up to 5 xu (at least 10)."""
    return max(10, -(-post['salary'][0] // 5) * 5)


def backdoor_helper(post: dict) -> str:
    """Who "lo giúp" for this posting: fixed per posting, so the confirm and the result agree."""
    i = sum(post['id'].encode()) % len(BACKDOOR_HELPERS)
    return BACKDOOR_HELPERS[i].format(boss=post.get('boss') or 'giám đốc', org=post['org'])


def _backdoor(s: dict, c: dict, career: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    j = s.get('journey') or {}
    job = c['job']
    need(j.get('story'), 'Đi cửa sau chỉ có trong hành trình.')
    app = job.get('application')
    need(job['status'] == 'rejected' and isinstance(app, dict), 'Cửa sau chỉ mở sau một lần trượt phỏng vấn.')
    post = _posting(career, app.get('posting'))
    need(post, 'Tin tuyển dụng không còn.')
    need(not _needs_exam(job, career, post), 'Chứng chỉ hành nghề phải thi thật: không có cửa sau cho bài thi này.')
    need(not job.get('backdoor'), 'Người quen chỉ “lo giúp” được một lần ở mỗi nơi.')
    fee = backdoor_fee(post)
    from . import bank as bk   # 🏦 p['pay']: 'auto' | 'cash' | 'card' | 'joint' (game/bank.py)
    need(j['wallet'] >= fee or bk.can_pay(s, fee, p.get('pay', 'auto')), f'Ví chưa đủ {fee} xu để đi cửa sau.')
    need(p.get('confirm') is True, 'Xác nhận đi cửa sau.')
    bk.pay(s, fee, f'Đi cửa sau · {post["org"]}', method=p.get('pay', 'auto'), kind='backdoor', career=career)
    low = post['salary'][0]
    job.update(status='hired', employer=post['id'], title=post['title'], salary=low, probation=True,
               probation_left=post['probation_days'], hired_day=c['day'], application=None, offer=None, extended=False,
               reviews_during_probation=[])
    job['backdoor'] = dict(posting=post['id'], day=c['day'], life_day=j['life_day'], fee=fee, said=False)
    job['history'] = ar.last(job['history'] + [dict(day=c['day'], event='backdoor', posting=post['id'])], 40, 'job.history', c)
    e.metric(c, 'backdoor_hires')
    e.log(s, c, 'job', f'Vào {post["org"]} bằng cửa sau: {fee} xu cho người quen “lo giúp”. '
                       f'Lương khởi điểm {low} xu/ngày, thử việc {post["probation_days"]} ngày như mọi người.')
    return dict(message=f'{backdoor_helper(post)} Bạn được nhận làm {post["title"].lower()} ở {post["org"]}, '
                        f'thử việc {post["probation_days"]} ngày.', backdoor=True)


def backdoor_remark(s: dict, c: dict, career: str) -> str | None:
    """Day one after a back-door hire: one colleague's remark (seeded), logged once. No other effect."""
    from . import engine as e
    job = c.get('job') or {}
    door = job.get('backdoor')
    if not isinstance(door, dict) or door.get('said') or job.get('status') != 'hired' or job.get('employer') != door.get('posting'):
        return None
    rng = _rng('backdoor-remark', (s.get('journey') or {}).get('seed', 0), career, door['posting'], door['life_day'])
    line = rng.choice(BACKDOOR_REMARKS)
    door['said'] = True
    e.log(s, c, 'job', line)
    return line


def on_close(s: dict, c: dict, career: str) -> dict | None:
    """Pay the day's salary if the employee actually worked; run probation review.
    Any day's end can also bring a lucky meeting with a boss from another job."""
    from . import engine as e
    boss = meet_boss(s, career, c['day'])
    if boss:
        e.log(s, c, 'job', boss['text'])
    job = c['job']
    if job['status'] != 'hired' or c['day_completed'] < 1:
        return dict(boss=boss) if boss else None
    post = _posting(career, job['employer'])
    from .accounting_school import salary_multiplier
    from .accounting_jobs import pay as boosted
    multiplier = salary_multiplier(s,career)   # 💼 ×3 kế toán with its certificate, ×5 on a holiday (game/accounting_jobs.py)
    pay = boosted(round(job['salary'] * (.85 if job['probation'] else 1)), multiplier)
    e.money(s, c, pay, 'Lương ngày ' + str(c['day']) + (' (thử việc 85%)' if job['probation'] else ''), f'salary-{c["day"]}', category='salary')
    job['days_worked'] += 1
    note = dict(salary=pay, probation=job['probation'])
    if multiplier > 1:
        note['multiplier'] = multiplier   # the wallet row says ×3 / ×5 (journey._end_of_day)
    if job['probation']:
        today = [f['stars'] for f in c['feed'] if f.get('stars') and f['day'] == c['day'] and f['kind'] == 'review']
        job['reviews_during_probation'] = ar.last(job['reviews_during_probation'] + today, 40, 'job.probation_reviews', c)
        job['probation_left'] = max(0, job['probation_left'] - 1)
        if job['probation_left'] == 0:
            rows = job['reviews_during_probation']
            avg = sum(rows) / len(rows) if rows else 4
            if avg >= 3.5 or job['extended']:
                job['probation'] = False
                note['result'] = 'official'
                e.log(s, c, 'job', f'Hết thử việc: ký hợp đồng chính thức tại {post["org"] if post else "nơi làm việc"} (đánh giá trung bình {avg:.1f}★).')
                e.metric(c, 'contracts')
            else:
                job['probation_left'] = 2
                job['extended'] = True
                note['result'] = 'extended'
                e.log(s, c, 'job', f'Thử việc được gia hạn 2 ngày: đánh giá trung bình {avg:.1f}★, cần ổn định hơn.')
    if boss:
        note['boss'] = boss
    return note


def _dy():
    from . import days
    return days


def retry_view(s: dict, c: dict) -> dict | None:
    """After a failed interview: the day the place takes an application again, in player days."""
    job = c.get('job') or {}
    if job.get('status') != 'rejected' or not job.get('cooldown_day'):
        return None
    info = _dy().day_info(s, job['cooldown_day'], c)
    info['button'] = 'Phỏng vấn lại' if info['open'] else f'Còn {info["left"]} ngày'
    info['line'] = ('Hôm nay bạn có thể phỏng vấn lại.' if info['open']
                    else f'Phỏng vấn lại được {info["text"]}.')
    return info


def retry_notices(s: dict) -> list[str]:
    """Once per failed interview, on the day the place reopens: 'Hôm nay (Ngày 5) bạn có thể phỏng vấn lại ở …'."""
    lines = []
    for cid, c in (s.get('careers') or {}).items():
        job = c.get('job') or {}
        due = job.get('cooldown_day') or 0
        if job.get('status') != 'rejected' or not due or job.get('retry_told', 0) >= due or today(s, c) < due:
            continue
        job['retry_told'] = due
        app = job.get('application') or {}
        post = _posting(cid, app.get('posting')) if app.get('posting') else None
        post = post or (postings(cid) or [None])[0]
        where = post['org'] if post else cid
        lines.append(f'📅 Hôm nay (Ngày {today(s, c)}) bạn có thể phỏng vấn lại ở {where}.')
    return lines


def public(c: dict, career: str, s: dict | None = None) -> dict:
    job = dict(c['job'])
    job.pop('retry_told', None)
    job['required'] = required(career)
    if s is not None:
        job['retry'] = retry_view(s, c)
        from .accounting_school import salary_multiplier
        job['base_salary'] = job['salary']
        job['salary_multiplier'] = salary_multiplier(s,career)
        from .accounting_jobs import pay as boosted
        job['salary'] = boosted(job['salary'], job['salary_multiplier'])
    job['certs'] = list(job.get('certs') or [])
    ex = exam(career)
    app = job.get('application')
    sheet = app.get('exam') if isinstance(app, dict) else None
    if ex and isinstance(sheet, dict) and sheet.get('score') is not None:
        # The answer key stays on the server until the paper is graded; then it teaches.
        bank = {q['id']: q for q in ex['bank']}
        job['exam_review'] = [dict(id=q, text=bank[q]['text'], picked=sheet['answers'].get(q), answer=bank[q]['answer'],
                                   ok=sheet['answers'].get(q) == bank[q]['answer'], why=bank[q]['why'],
                                   options={o['id']: o['label'] for o in bank[q]['options']}) for q in sheet['qs']]
    return job


def _public_exam(ex: dict) -> dict:
    return dict({k: ex[k] for k in ('id', 'name', 'issuer', 'pass_mark', 'draw', 'emoji', 'intro')},
                questions={q['id']: dict(text=q['text'], options=q['options']) for q in ex['bank']})


def content(career_ids) -> dict:
    ids = [cid for cid in career_ids if postings(cid)]
    return dict(strengths=STRENGTHS, claims=[dict(id=x['id'], text=x['text']) for x in CLAIMS], letter=LETTER_SLOTS,
                postings={cid: [dict(p, stages=stages(p), interviewer=public_interviewer(cid, p),
                                     backdoor=dict(fee=backdoor_fee(p), helper=backdoor_helper(p))) for p in postings(cid)] for cid in ids},
                questions={cid: {q: question(cid, q) for p in postings(cid) for q in all_steps(p)} for cid in ids},
                exams={cid: _public_exam(exam(cid)) for cid in ids if exam(cid)},
                stage_names=STAGE_NAMES, reply_rules={k: dict(points=v[0], label=v[1]) for k, v in REPLY_RULES.items()},
                reply_max=REPLY_MAX, pass_score=PASS_SCORE)


def _validate_app(job: dict, career: str, app: dict) -> None:
    from .engine import need, integer
    need(isinstance(app, dict), 'Hồ sơ ứng tuyển sai.')
    post = _posting(career, app.get('posting'))
    need(post, 'Hồ sơ ứng tuyển sai.')
    need(app.get('stage') in STAGES + ('closed',), 'Bước ứng tuyển sai.')
    if job['status'] == 'applying':
        need(app['stage'] in stages(post), 'Bước ứng tuyển không thuộc quy trình của tin này.')
    need(isinstance(app.get('strengths', []), list) and isinstance(app.get('claims', []), list), 'CV sai.')
    need(all(x in STRENGTH_IDS for x in app.get('strengths', [])) and all(x in CLAIM_INDEX for x in app.get('claims', [])), 'CV sai.')
    answers = app.get('answers', {})
    need(isinstance(answers, dict), 'Câu trả lời sai.')
    steps = all_steps(post)
    for qid, oid in answers.items():
        need(qid in steps, 'Câu trả lời không thuộc tin tuyển dụng.')
        need(oid in [o['id'] for o in question(career, qid)['options']], 'Câu trả lời sai.')
    need(isinstance(app.get('notes', []), list) and len(app.get('notes', [])) <= 60, 'Ghi chú phỏng vấn sai.')
    _validate_talk(career, post, app)
    chance = app.get('chance')
    if chance is not None:
        from . import certificates as ct
        need(isinstance(chance, dict) and set(chance) == {'cert', 'pct', 'roll', 'hired', 'blocked'}, 'Tỷ lệ nhận sai.')
        need(ct.group_of(career) == chance['cert'], 'Chứng chỉ không thuộc nghề này.')
        integer(chance['pct'], 0, 100)
        integer(chance['roll'], 0, 99)
        need(chance['blocked'] in (None, 'fatal', 'reference') and (chance['blocked'] is None or chance['pct'] == 0), 'Tỷ lệ nhận sai.')
        need(chance['pct'] <= ct.boosted(0) and chance['hired'] is (chance['roll'] < chance['pct']), 'Tỷ lệ nhận sai.')
    sheet = app.get('exam')
    if app['stage'] == 'exam':
        need(isinstance(sheet, dict), 'Thiếu bài thi.')
    if sheet is not None:
        ex = exam(career)
        need(ex and 'exam' in stages(post) and isinstance(sheet, dict), 'Bài thi sai.')
        bank = {q['id']: q for q in ex['bank']}
        qs = sheet.get('qs')
        need(isinstance(qs, list) and len(qs) == ex['draw'] and len(set(qs)) == len(qs) and all(q in bank for q in qs), 'Đề thi sai.')
        ans = sheet.get('answers')
        need(isinstance(ans, dict) and set(ans) <= set(qs), 'Bài làm sai.')
        for q, oid in ans.items():
            need(oid in [o['id'] for o in bank[q]['options']], 'Bài làm sai.')
        need(sheet.get('score') is None or integer(sheet['score'], 0, ex['draw']) >= 0, 'Điểm thi sai.')
        need(sheet.get('passed') in (None, True, False), 'Kết quả thi sai.')
        need((sheet.get('score') is None) == (sheet.get('passed') is None), 'Kết quả thi sai.')
        if sheet.get('score') is not None:
            need(len(ans) == len(qs) and sheet['passed'] == (sheet['score'] >= ex['pass_mark']), 'Kết quả thi sai.')
        integer(sheet.get('attempt'), 1, 10**6)


def validate(c: dict, career: str) -> None:
    from .engine import need, integer
    job = c.get('job')
    need(isinstance(job, dict) and set(initial()) - LATER_FIELDS <= set(job), 'Hồ sơ việc làm thiếu dữ liệu.')
    need(job['status'] in ('none', 'applying', 'offer', 'hired', 'rejected'), 'Trạng thái việc làm sai.')
    for k in ('salary', 'probation_left', 'hired_day', 'cooldown_day', 'days_worked'):
        integer(job.get(k), 0, 10**7)
    if 'retry_told' in job:  # the day of the last "phỏng vấn lại được rồi" notice (optional, newer saves)
        integer(job['retry_told'], 0, 10**7)
    need(job['salary'] <= 200, 'Lương vượt trần.')
    need(type(job['probation']) is bool and type(job['extended']) is bool, 'Cờ thử việc sai.')
    need(isinstance(job['history'], list) and len(job['history']) <= 40, 'Lịch sử việc làm sai.')
    need(isinstance(job['reviews_during_probation'], list) and len(job['reviews_during_probation']) <= 40 and all(x in (1, 2, 3, 4, 5) for x in job['reviews_during_probation']), 'Đánh giá thử việc sai.')
    if job['status'] == 'hired':
        post = _posting(career, job['employer'])
        need(post, 'Nơi làm việc không tồn tại.')
        need(post['salary'][0] <= job['salary'] <= post['salary'][1], 'Lương không thuộc khung của tin tuyển dụng.')
    certs = job.get('certs', [])
    ex = exam(career)
    need(isinstance(certs, list) and len(certs) <= 10, 'Chứng chỉ sai.')
    for cert in certs:
        need(ex and isinstance(cert, dict) and cert.get('id') == ex['id'], 'Chứng chỉ không thuộc nghề này.')
        integer(cert.get('day'), 1, 10**7)
        integer(cert.get('score'), 0, ex['draw'])
    door = job.get('backdoor')
    if door is not None:
        need(isinstance(door, dict) and set(door) == {'posting', 'day', 'life_day', 'fee', 'said'} and _posting(career, door['posting']),
             'Hồ sơ cửa sau sai.')
        integer(door['day'], 1, 10**7)
        integer(door['life_day'], 1, 10**7)
        integer(door['fee'], 1, 10**4)
        need(type(door['said']) is bool, 'Hồ sơ cửa sau sai.')
    app = job['application']
    if job['status'] in ('applying', 'offer'):
        need(app is not None, 'Thiếu hồ sơ ứng tuyển.')
    if app is not None:
        _validate_app(job, career, app)
    if job['offer'] is not None:
        o = job['offer']
        need(isinstance(o, dict) and job['status'] == 'offer' and app, 'Thư mời sai.')
        post = _posting(career, app['posting'])
        need(post['salary'][0] <= integer(o.get('salary'), 0, 200) <= post['salary'][1], 'Lương thư mời sai.')
        need(type(o.get('negotiated')) is bool, 'Cờ thương lượng sai.')


# ---- the interviewer talks back (v0.6) ----------------------------------------
# After a scripted interview answer the interviewer may ask ONE short follow-up; the
# player types a short reply or skips. Owners in trials (and chị Mai playing the angry
# customer in the test) react to each step. Lines are stored scripted first; the AI
# (server route /api/ai/interview) may only reword the newest one. The typed reply
# moves the score by transparent word rules below — never by what a model thinks.
# Spec: docs/superpowers/specs/2026-09-29-ai-interviewer-design.md
MAX_ASKS = 2            # follow-ups per interview stage (never after its last question)
TALK_MAX = 16           # talk entries kept per application
REPLY_MAX = 200         # typed reply, characters
LINE_MAX = 600          # stored interviewer line, characters
STEP_BONUS = (-3, 3)    # one reply
TOTAL_BONUS = (-5, 5)   # all replies of one application
REPLY_RULES = dict(     # rule id → (points, label shown to the player)
    example=(2, 'có ví dụ cụ thể'), reason=(1, 'nêu lý do'), short=(0, 'quá ngắn để cộng điểm'),
    overclaim=(-2, 'kể quá những gì hồ sơ có'), blame=(-1, 'đổ lỗi cho người khác'), rude=(-3, 'lời lẽ thiếu tôn trọng'))
_EXAMPLE = _re.compile(r'\d|ví dụ|chẳng hạn|có lần|một lần|lần trước|lần đó|hôm trước|hôm qua|hôm đó|tuần trước|tháng trước|năm ngoái|'
                       r'hồi đó|hồi trước|lúc đó|khi đó|kết quả là|for example|for instance|\bonce\b|last (?:time|week|month|year)', _re.I)
_REASON = _re.compile(r'(?<!\w)(vì|bởi vì|bởi|để|nên|cho nên|vậy nên|nhờ vậy|because|so that|since)(?!\w)', _re.I)
_BOAST = _re.compile(r'nhiều năm|lâu năm|dày dạn|rất nhiều kinh nghiệm|hàng trăm|hàng nghìn|hàng ngàn|chuyên gia|giỏi nhất|'
                     r'chưa bao giờ sai|years of experience|\bexpert\b|hundreds of', _re.I)
_BLAME = _re.compile(r'(?<!\w)(lỗi|tại|do) (của )?(khách|đồng nghiệp|sếp|người khác|họ)(?!\w)|không phải lỗi (của )?(em|con|tôi|mình|cháu)(?!\w)|'
                     r"(their|not my) fault", _re.I)
_RUDE = _re.compile(r'(?<!\w)(ngu|đồ ngu|mặc kệ|kệ nó|kệ khách|liên quan gì|hỏi làm gì|hỏi chi|biến đi|im đi|phiền quá|vô duyên|'
                    r'nhảm|stupid|shut up|whatever|none of your business)(?!\w)', _re.I)
_PROMISE = _re.compile(r'(?<!ghi )(nhận|tuyển) (em|con|cháu|bạn)( vào làm| luôn| rồi| chắc)|được nhận( vào| rồi| luôn|$)|trúng tuyển|đậu rồi|chắc chắn (nhận|đậu|được)|'
                       r'(hứa|cam kết) (với )?(em|con|cháu|bạn)|tăng lương|thưởng thêm|lương (sẽ|là|được)|điểm (của )?(em|con|cháu|bạn)|'
                       r'\b(you\'re hired|you are hired|promise|raise)\b', _re.I)
_CTRL = _re.compile(r'[\x00-\x1f\x7f​-‏ -‮⁦-⁩]')


def _fold(text: str) -> str:
    return _ud.normalize('NFC', text).lower()


def interviewer(s: dict | None, career: str, post: dict) -> dict:
    """Who sits across the table: the posting's own card, the career's, or a neutral one."""
    card = EC.INTERVIEWERS.get(post.get('id')) or EC.INTERVIEWERS.get(career)
    if not card:
        boss = _cap(_boss(career, post))
        card = dict(name=boss, role=f'{boss} · {post["org"]}', self='tôi', you='bạn', style='lịch sự, rõ ràng', face='🧑‍💼',
                    npc=None, region='miền Nam', particles=[], cares=[])
    card = dict(card)
    npc = card.get('npc')
    if npc and s is not None:
        try:
            from .content import NPC_INDEX
            from . import personas
            if npc in NPC_INDEX:
                addr = personas.persona(s, career, npc)['address']
                card.update(self=addr['self'], you=addr['player'])
            else:
                card['npc'] = None
        except (ImportError, KeyError, TypeError):
            card['npc'] = None
    return card


def public_interviewer(career: str, post: dict) -> dict:
    card = interviewer(None, career, post)
    return dict(name=card['name'], role=card['role'], face=card['face'])


def _fill(line: str, who: dict, **more) -> str:
    you = who.get('you') or 'bạn'
    return _cap(line.format(self=who.get('self') or 'tôi', you=you, You=_cap(you), Who=who['name'], **more))


def _talk(app: dict) -> list:
    rows = app.get('talk')
    if not isinstance(rows, list):
        rows = app['talk'] = []
    return rows


def _open_ask(app: dict) -> dict | None:
    rows = app.get('talk') or []
    last = rows[-1] if rows else None
    return last if isinstance(last, dict) and last.get('kind') == 'ask' and last.get('status') == 'open' else None


def _ask_line(s: dict, c: dict, career: str, post: dict, app: dict, qid: str, opt: dict, who: dict) -> str:
    n = sum(1 for x in _talk(app) if x.get('kind') == 'ask' and x.get('stage') == 'interview')
    rng = _rng('ask', post['id'], qid, c['day'], len(c['job']['history']))
    if n == 0:
        pool = EC.ASKS['good' if opt['score'] >= 3 else 'mid' if opt['score'] >= 1 else 'weak']
        return _fill(rng.choice(pool), who, answer=opt['label'])
    claims = [CLAIM_INDEX[x]['text'] for x in app.get('claims', []) if CLAIM_INDEX[x]['need']]
    if claims:
        return _fill(rng.choice(EC.ASKS['claim']), who, claim=claims[0])
    names = [x['name'] for x in STRENGTHS if x['id'] in app.get('strengths', [])]
    if names:
        return _fill(rng.choice(EC.ASKS['strength']), who, strength=names[0])
    return _fill(rng.choice(EC.ASKS['fresh']), who)


def _after_answer(s: dict, c: dict, career: str, post: dict, app: dict, stage: str, qid: str, opt: dict, remaining: bool) -> int | None:
    """Open a follow-up (interview) or record the owner's reaction (trial/test). Returns the talk index."""
    who = interviewer(s, career, post)
    rows = _talk(app)
    asks = sum(1 for x in rows if x.get('kind') == 'ask' and x.get('stage') == 'interview')
    if stage == 'interview' and remaining and asks < MAX_ASKS:
        line = _ask_line(s, c, career, post, app, qid, opt, who)
        rows.append(dict(kind='ask', stage=stage, q=qid, who=who['name'], text=line, mode='scripted', canonical=line,
                         status='open', reply=None, bonus=0, rules=[], react=None, react_mode=None, react_canonical=None))
    elif stage in ('trial', 'test'):
        line = str(opt['note'])[:LINE_MAX]
        rows.append(dict(kind='react', stage=stage, q=qid, who=who['name'], text=line, mode='scripted', canonical=line))
    else:
        return None
    ar.drop_head(rows, TALK_MAX, 'job.talk', c)
    return len(rows) - 1


def score_reply(s: dict, c: dict, career: str, text: str) -> tuple[int, list[str]]:
    """Transparent word rules for a typed follow-up reply → (bonus, rule ids)."""
    folded = _fold(text)
    rules = []
    rude = bool(_RUDE.search(folded))
    if not rude:
        try:
            from .ai import abusive
            rude = abusive(folded)
        except ImportError:
            pass
    if rude:
        rules.append('rude')
    served = max([int((v.get('metrics') or {}).get('served', 0) or 0) for v in (s.get('careers') or {}).values()] or [0])
    if _BOAST.search(folded) and served < 15:
        rules.append('overclaim')
    if _BLAME.search(folded):
        rules.append('blame')
    if len(folded.split()) < 3:
        rules.append('short')
    elif not rules:
        if _EXAMPLE.search(folded):
            rules.append('example')
        if _REASON.search(folded):
            rules.append('reason')
    bonus = sum(REPLY_RULES[r][0] for r in rules)
    return max(STEP_BONUS[0], min(STEP_BONUS[1], bonus)), rules


def _react_line(who: dict, rules: list[str]) -> str:
    key = next((r for r in ('rude', 'overclaim', 'blame', 'example', 'reason', 'short') if r in rules), 'plain')
    return _fill(EC.REACTS[key], who)


def clean_reply_text(text: str) -> str:
    """Player's reply as stored: one line, no control characters, no contact details."""
    text = _re.sub(r'\s+', ' ', _CTRL.sub(' ', _ud.normalize('NFC', text))).strip()[:REPLY_MAX]
    try:
        from .ai import redact
        text = redact(text)[:REPLY_MAX]
    except ImportError:
        pass
    return text


def _followup(s: dict, c: dict, career: str, post: dict, app: dict, p: dict) -> dict:
    from .engine import need
    need(c['job']['status'] == 'applying', 'Buổi phỏng vấn đã kết thúc.')
    ask = _open_ask(app)
    need(ask, 'Không có câu hỏi thêm nào đang chờ.')
    idx = len(app['talk']) - 1
    if p.get('skip') is True:
        ask['status'] = 'skipped'
        return dict(message=f'Bạn bỏ qua câu hỏi thêm của {ask["who"]}.', talk=idx, followup='skipped')
    text = p.get('text')
    need(isinstance(text, str) and text.strip(), 'Gõ vài chữ trả lời, hoặc bấm Bỏ qua.')
    need(len(text.strip()) <= REPLY_MAX, f'Trả lời tối đa {REPLY_MAX} ký tự nhé.')
    reply = clean_reply_text(text)
    need(reply, 'Gõ vài chữ trả lời, hoặc bấm Bỏ qua.')
    bonus, rules = score_reply(s, c, career, reply)
    who = interviewer(s, career, post)
    line = _react_line(who, rules)
    ask.update(status='answered', reply=reply, bonus=bonus, rules=rules, react=line, react_mode='scripted', react_canonical=line)
    return dict(message=line, talk=idx, followup='answered', bonus=bonus)


def talk_bonus(app: dict) -> int:
    total = sum(int(x.get('bonus') or 0) for x in app.get('talk') or [] if isinstance(x, dict) and x.get('status') == 'answered')
    return max(TOTAL_BONUS[0], min(TOTAL_BONUS[1], total))


def _talk_feedback(app: dict) -> str | None:
    rows = [x for x in app.get('talk') or [] if isinstance(x, dict) and x.get('status') == 'answered']
    if not rows:
        return None
    total = talk_bonus(app)
    why = list(dict.fromkeys(f'{REPLY_RULES[r][1]} {REPLY_RULES[r][0]:+d}' for x in rows for r in x.get('rules', []) if REPLY_RULES[r][0]))
    sign = f'+{total}' if total > 0 else str(total)
    return f'Trả lời thêm với {rows[0]["who"]}: {sign} điểm' + (f' ({", ".join(why)}).' if why else '.')


# ---- voicing (called by the server route; pure with respect to the save) ---------
def voice_command(data: dict) -> tuple[str, dict]:
    """Validate the /api/ai/interview body → (action, payload) for Store.command."""
    from .engine import need
    step = data.get('step')
    need(step in ('answer', 'reply', 'skip'), 'Bước phỏng vấn không hợp lệ.')
    if step == 'answer':
        q, o = data.get('question'), data.get('option')
        need(isinstance(q, str) and isinstance(o, str) and 0 < len(q) <= 64 and 0 < len(o) <= 64, 'Câu trả lời không hợp lệ.')
        return 'job_answer', dict(question=q, option=o)
    if step == 'skip':
        return 'job_followup', dict(skip=True)
    text = data.get('text')
    need(isinstance(text, str) and text.strip(), 'Gõ vài chữ trả lời, hoặc bấm Bỏ qua.')
    need(len(text.strip()) <= REPLY_MAX, f'Trả lời tối đa {REPLY_MAX} ký tự nhé.')
    return 'job_followup', dict(text=text)


def pending_voice(s: dict, career: str, idx) -> dict | None:
    """The interviewer line at talk[idx] that is still in its scripted wording, with what
    the model may know: posting facts, the CV, the step, the player's words."""
    c = (s.get('careers') or {}).get(career) or {}
    app = (c.get('job') or {}).get('application')
    rows = app.get('talk') if isinstance(app, dict) else None
    if type(idx) is not int or not isinstance(rows, list) or not 0 <= idx < len(rows):
        return None
    e = rows[idx]
    post = _posting(career, app.get('posting'))
    q = question(career, e.get('q')) if post else None
    if not q:
        return None
    opt = next((o for o in q['options'] if o['id'] == app['answers'].get(e['q'])), None)
    if e['kind'] == 'ask' and e['status'] == 'open' and e['mode'] == 'scripted':
        field, canonical, said = 'text', e['canonical'], (opt or {}).get('label', '')
        goal = ('Hỏi ĐÚNG MỘT câu hỏi phụ ngắn (kết thúc bằng dấu ?), bám theo ý của canonical và câu trả lời/CV của ứng viên. '
                'Có thể mở đầu bằng nửa câu phản ứng với câu trả lời.')
        tone = 'tò mò'
    elif e['kind'] == 'ask' and e['status'] == 'answered' and e['react_mode'] == 'scripted':
        field, canonical, said = 'react', e['react_canonical'], e['reply']
        goal = 'Phản ứng ngắn với câu trả lời thêm của ứng viên, đúng ý của canonical. Không hỏi thêm, không kết luận kết quả.'
        tone = 'chưa hài lòng' if e['bonus'] < 0 else 'hài lòng' if e['bonus'] > 0 else 'trung tính'
    elif e['kind'] == 'react' and e['mode'] == 'scripted':
        field, canonical, said = 'text', e['canonical'], (opt or {}).get('label', '')
        goal = ('Phản ứng ngắn, đúng ý canonical, với việc ứng viên vừa làm trong buổi làm thử.' if e['stage'] == 'trial' else
                'Bạn đang ĐÓNG VAI vị khách khó tính trong bài thử; phản ứng đúng ý canonical với câu ứng viên vừa nói.')
        tone = 'theo canonical'
    else:
        return None
    if not canonical or not said:
        return None
    who = interviewer(s, career, post)
    low, high = post['salary']
    ctx = dict(
        interview=dict(org=post['org'], title=post['title'], stage=STAGE_NAMES.get(e['stage'], e['stage']),
                       wage=f'{low}–{high} xu/ngày (chỉ nói con số này nếu được hỏi)', culture=post.get('culture', ''),
                       interviewer=dict(name=who['name'], role=who['role'], style=who['style'])),
        applicant=dict(strengths=[x['name'] for x in STRENGTHS if x['id'] in app.get('strengths', [])],
                       cv=[CLAIM_INDEX[x]['text'] for x in app.get('claims', []) if x in CLAIM_INDEX]),
        step=dict(question=q['text'], applicant_answer=(opt or {}).get('label', ''), note=(opt or {}).get('note', '')),
        goal=goal, tone=tone,
        rules='Không hứa nhận việc, không nói điểm hay kết quả, không nói mức lương nào ngoài khung trong interview.wage, '
              'không hỏi thông tin cá nhân thật (số điện thoại, địa chỉ, giấy tờ).')
    history = []
    for x in rows[:idx]:
        if x.get('kind') == 'ask':
            history.append(dict(role='npc', text=x.get('text', '')))
            if x.get('reply'):
                history.append(dict(role='user', text=x['reply']))
            if x.get('react'):
                history.append(dict(role='npc', text=x['react']))
    return dict(idx=idx, field=field, canonical=canonical, said=said, context=ctx, history=history[-8:], who=who,
                ask=field == 'text' and e['kind'] == 'ask')


def _local_reply(s: dict, career: str, who: dict, said: str, ctx: dict, canonical: str, history: list) -> dict:
    """Same prompt and guardrails as ai.persona_reply, for interviewers who are not town NPCs."""
    import json
    import os
    from . import ai
    settings = s.get('settings') or {}
    lang = settings.get('lang', 'vi')
    fallback = dict(mode='scripted', text=canonical, reason=None)
    if not settings.get('aiConsent'):
        return dict(fallback, reason='no_consent')
    if not ai.available():
        return dict(fallback, reason='not_configured')
    card = dict(id='interviewer', name=who['name'], role=who['role'], career=career, age='middle', age_label='người lớn',
                temperament='interviewer', temperament_label='người phỏng vấn', style=who['style'], personality=who['style'],
                traits=[], address=dict(self=who['self'], player=who['you']), region=who.get('region') or 'miền Nam',
                particles=list(who.get('particles') or [])[:4], cares=list(who.get('cares') or []), memory={})
    turns = [dict(who='player' if r['role'] == 'user' else 'npc', text=ai.redact(str(r['text'])[:300])) for r in history[-8:]]
    data = json.dumps(dict(persona=card, task=ctx, canonical=canonical, recent_turns=turns, player_says=ai.redact(said)[:300]),
                      ensure_ascii=False)
    name = s.get('name') if isinstance(s.get('name'), str) else ''
    if len(name.strip()) >= 2 and name.strip() != 'Mây':
        data = _re.sub(r'(?<!\w)' + _re.escape(name.strip()) + r'(?!\w)', who['you'], data)
    try:
        timeout = float(os.environ.get('AI_CHAT_TIMEOUT', '9') or 9)
    except ValueError:
        timeout = 9.0
    msgs = [dict(role='system', content=ai._persona_system(card, 'interview', lang)), dict(role='user', content=data)]
    text, reason = ai.chat(msgs, max_tokens=160, temperature=0.85, timeout=timeout)
    if not text:
        return dict(fallback, reason=reason or 'unavailable')
    allowed = ai._numbers(dict(persona=card, task=ctx, canonical=canonical, turns=[t['text'] for t in turns if t['who'] == 'npc']))
    line, why = ai.clean_reply(text, allowed, who['name'])
    if not line:
        return dict(fallback, reason=why)
    return dict(mode='ai', text=line, reason=None)


def voice(s: dict, career: str, pend: dict) -> dict:
    """AI wording for one pending interviewer line → {mode:'ai'|'scripted', text, reason}.
    Reads the save, never writes it; `text` is the scripted canonical unless mode is 'ai'."""
    from . import ai
    canonical = pend['canonical']
    fallback = dict(mode='scripted', text=canonical, reason=None)
    if ai.abusive(pend['said']):
        return dict(fallback, reason='unsafe_request')   # the scripted rude-reply reaction stands
    who = pend['who']
    if who.get('npc'):
        out = ai.persona_reply(s, career, who['npc'], pend['said'], context=pend['context'], canonical=canonical,
                               history=pend['history'], purpose='interview')
    else:
        out = _local_reply(s, career, who, pend['said'], pend['context'], canonical, pend['history'])
    if out.get('mode') != 'ai' or not out.get('text'):
        return dict(fallback, reason=out.get('reason') or ('guard' if out.get('mode') == 'guard' else 'unavailable'))
    line = out['text'][:LINE_MAX]
    if _PROMISE.search(_fold(line)):
        return dict(fallback, reason='promise')
    if pend['ask'] and '?' not in line:
        return dict(fallback, reason='not_a_question')
    return dict(mode='ai', text=line, reason=None)


def apply_voice(raw: dict, career: str, idx: int, field: str, canonical: str, line: str) -> bool:
    """Store the AI wording of talk[idx] only if that line is still the same scripted one."""
    c = (raw.get('careers') or {}).get(career) or {}
    app = (c.get('job') or {}).get('application')
    rows = app.get('talk') if isinstance(app, dict) else None
    if not isinstance(rows, list) or type(idx) is not int or not 0 <= idx < len(rows) or not isinstance(line, str):
        return False
    e = rows[idx]
    line = line.strip()[:LINE_MAX]
    if not line:
        return False
    if field == 'text' and e.get('mode') == 'scripted' and e.get('canonical') == canonical and e.get('text') == canonical:
        if e.get('kind') == 'ask' and e.get('status') != 'open':
            return False
        e.update(text=line, mode='ai')
        return True
    if field == 'react' and e.get('kind') == 'ask' and e.get('react_mode') == 'scripted' and e.get('react_canonical') == canonical:
        e.update(react=line, react_mode='ai')
        return True
    return False


def _validate_talk(career: str, post: dict, app: dict) -> None:
    from .engine import need, integer
    rows = app.get('talk')
    if rows is None:
        return
    need(isinstance(rows, list) and len(rows) <= TALK_MAX, 'Lời phỏng vấn sai.')
    steps = all_steps(post)
    txt = lambda v, n=LINE_MAX: isinstance(v, str) and 0 < len(v) <= n
    for i, e in enumerate(rows):
        need(isinstance(e, dict) and e.get('kind') in ('ask', 'react'), 'Lời phỏng vấn sai.')
        need(e.get('stage') in STEP_STAGES and e.get('q') in steps and e['q'] in app.get('answers', {}), 'Lời phỏng vấn không thuộc buổi này.')
        need(txt(e.get('who'), 60) and txt(e.get('text')) and txt(e.get('canonical')) and e.get('mode') in ('scripted', 'ai'), 'Lời phỏng vấn sai.')
        if e['kind'] == 'react':
            need(set(e) == {'kind', 'stage', 'q', 'who', 'text', 'mode', 'canonical'}, 'Lời phỏng vấn sai.')
            continue
        need(set(e) == {'kind', 'stage', 'q', 'who', 'text', 'mode', 'canonical', 'status', 'reply', 'bonus', 'rules',
                        'react', 'react_mode', 'react_canonical'}, 'Lời phỏng vấn sai.')
        need(e['status'] in ('open', 'answered', 'skipped'), 'Lời phỏng vấn sai.')
        need(e['status'] != 'open' or i == len(rows) - 1, 'Chỉ câu hỏi cuối cùng mới được để ngỏ.')
        integer(e.get('bonus'), STEP_BONUS[0], STEP_BONUS[1])
        need(isinstance(e.get('rules'), list) and len(e['rules']) <= len(REPLY_RULES) and all(r in REPLY_RULES for r in e['rules']), 'Lời phỏng vấn sai.')
        if e['status'] == 'answered':
            need(txt(e.get('reply'), REPLY_MAX) and txt(e.get('react')) and txt(e.get('react_canonical')) and e.get('react_mode') in ('scripted', 'ai'),
                 'Lời phỏng vấn sai.')
        else:
            need(e['reply'] is None and e['react'] is None and e['react_mode'] is None and e['react_canonical'] is None
                 and e['bonus'] == 0 and e['rules'] == [], 'Lời phỏng vấn sai.')
