"""Server-authoritative accounting courses, original exams and game certificates."""
from __future__ import annotations

import hashlib
import random
import re
from . import accounting_company as company
from . import accounting_hints as hints
from . import procedures
from .jsoncopy import tree_copy

COURSE_IDS = ('basic', 'vn_business')
PASS_MARK = 80
DRAW = {'basic': 24, 'vn_business': 40}


def _content():
    from . import accounting_content
    return accounting_content


def course(cid): return next((c for c in _content().COURSES if c['id']==cid), None)


def _lessons(cid):
    c = course(cid)
    return [l for ch in c['chapters'] for l in ch['lessons']] if c else []


def exam_question(cid, qid):
    return next((q for q in _content().EXAM_BANK.get(cid,[]) if q['id']==qid),None)


def initial():
    return dict(v=1,selected=None,progress={},exams={},active_exam=None,company=None)


def migrate(s):
    """The school's block is created on first use (an as_* command), never by migrate_state: saves that never
    opened it stay byte for byte what an older build wrote (rolling release, rollback)."""
    if 'accounting_school' not in s: s['accounting_school']=initial()


def _school(s):
    """Read-only: the block, or an empty one for a save that never opened the school (not stored)."""
    a=s.get('accounting_school')
    return a if isinstance(a,dict) else initial()


def _need(ok,message):
    from .engine import need
    need(ok,message)


def _check(q, answer):
    if q['kind']=='entry' and q['_key'] and isinstance(q['_key'][0],dict):
        q=dict(q,_key=[(x['debit'],x['credit'],x['amount']) for x in q['_key']])
    return _shape(q,answer) and procedures.check(q,answer)


def _shape(q,answer):
    if not procedures.shape_ok(q,answer):return False
    return q['kind']!='entry' or all(set(row)=={'debit','credit','amount'} for row in answer)


def lesson_done(s,lid):
    lesson=_content().LESSONS.get(lid)
    rec=_school(s)['progress'].get(lid)
    return bool(lesson and rec and rec.get('read') and len(rec['answers'])==len(lesson['questions']))


def course_done(s,cid): return all(lesson_done(s,l['id']) for l in _lessons(cid)) and bool(course(cid))


def certified(s,cid):
    school=s.get('accounting_school')
    exams=school.get('exams') if isinstance(school,dict) else None
    rec=exams.get(cid) if isinstance(exams,dict) else None
    cert=rec.get('certificate') if isinstance(rec,dict) else None
    return isinstance(cert,dict) and cert.get('id')=='pcc-accounting-'+cid


def salary_multiplier(s,career): return 3 if career=='corp_accounting' and certified(s,'vn_business') else 1


def _draw(s,cid,attempt):
    seed=(s.get('journey') or {}).get('seed',0)
    rng=random.Random(hashlib.sha256(f'accounting|{seed}|{cid}|{attempt}'.encode()).hexdigest())
    bank=list(_content().EXAM_BANK[cid]); rng.shuffle(bank)
    chosen=[]
    for ch in course(cid)['chapters']:
        q=next((q for q in bank if q.get('chapter_id')==ch['id']),None)
        if q: chosen.append(q['id'])
    chosen += [q['id'] for q in bank if q['id'] not in chosen][:max(0,min(DRAW[cid],len(bank))-len(chosen))]
    rng.shuffle(chosen)
    return chosen


def _grade(cid,paper):
    right=sum(_check(exam_question(cid,qid),paper['answers'][qid]) for qid in paper['qs'])
    return (200*right+len(paper['qs']))//(2*len(paper['qs']))


def _safe_question(q,answer=None,solved=False,lesson=None):
    """A question without its key. `lesson`: a practice question, which carries hints 1–2 while unsolved
    (exam questions never do)."""
    view={k:tree_copy(v) for k,v in q.items() if not k.startswith('_') and k not in ('explain','hint','hints')}
    view['solved']=solved
    if solved:
        view.update(answer=tree_copy(answer),explain=q.get('explain','Chính xác.'))
        view.pop('accounts',None)  # the account picker (~90 rows): a solved entry only shows its codes
    elif lesson is not None: view['help']=hints.lesson_help(q,lesson)
    return view


def action(s,name,p):
    """One as_* command. Its result carries the school's own view (`accounting_view`), shaped by the optional
    p['view'] (tab, company sub-tab, course, glossary): public_state only carries summary()."""
    result=_action(s,name,p)
    result['accounting_view']=view(s,p.get('view'))
    return result


def _action(s,name,p):
    migrate(s); a=s['accounting_school']
    if name=='as_view': return dict(message='Học kế toán: chọn khóa hoặc tiếp tục bài đang học.')
    if name=='as_open':
        lid=p.get('lesson'); lesson=_content().LESSONS.get(lid) if isinstance(lid,str) else None
        _need(lesson,'Bài học không tồn tại.')
        a['selected']=lid
        a['progress'].setdefault(lid,dict(read=True,answers={},attempts=0))['read']=True
        return dict(message='Đã mở '+lesson['title']+'. Đọc ví dụ rồi tự làm bài tập.')
    if name=='as_answer':
        lid=p.get('lesson'); lesson=_content().LESSONS.get(lid) if isinstance(lid,str) else None
        rec=a['progress'].get(lid) if lesson else None
        _need(rec and rec['read'],'Mở bài và đọc ví dụ trước khi làm bài tập.')
        q=next((q for q in lesson['questions'] if q['id']==p.get('question')),None)
        _need(q,'Câu hỏi không thuộc bài này.')
        _need(q['id'] not in rec['answers'],'Bài tập này đã được chấm đúng.')
        answer=p.get('answer')
        _need(_shape(q,answer),'Câu trả lời chưa đúng định dạng.')
        rec['attempts']+=1
        if not _check(q,answer):
            return dict(correct=False,message=hints.wrong(q,answer))
        rec['answers'][q['id']]=tree_copy(answer)
        return dict(correct=True,message=q.get('explain','Chính xác.'),lesson_done=lesson_done(s,lid))
    if name=='as_exam_start':
        cid=p.get('course'); _need(cid in COURSE_IDS,'Khóa học không tồn tại.')
        _need(a['active_exam'] is None,'Hoàn thành hoặc hủy bài thi đang làm trước.')
        _need(course_done(s,cid),'Hoàn thành tất cả bài tập của khóa trước khi thi.')
        _need(cid!='vn_business' or certified(s,'basic'),'Thi đạt khóa Kế toán cơ bản trước khi thi khóa doanh nghiệp.')
        rec=a['exams'].setdefault(cid,dict(attempts=0,score=0,best=0,certificate=None,last=None))
        rec['attempts']+=1
        a['active_exam']=dict(course=cid,attempt=rec['attempts'],qs=_draw(s,cid,rec['attempts']),answers={})
        return dict(message='Bắt đầu bài thi. Kết quả và lời giải xuất hiện sau khi nộp đủ bài.')
    if name=='as_exam_cancel':
        _need(a['active_exam'] is not None and p.get('confirm') is True,'Xác nhận hủy bài thi đang làm.')
        a['active_exam']=None
        return dict(message='Đã hủy bài thi. Tiến độ học và chứng chỉ đã có được giữ nguyên.')
    if name=='as_exam_answer':
        paper=a['active_exam']; _need(isinstance(paper,dict),'Bạn chưa bắt đầu bài thi.')
        qid=paper['qs'][len(paper['answers'])]
        _need(p.get('question')==qid,'Nộp câu hiện tại; câu đã nộp không được nộp lại.')
        q=exam_question(paper['course'],qid); answer=p.get('answer')
        _need(_shape(q,answer),'Câu trả lời chưa đúng định dạng.')
        paper['answers'][qid]=tree_copy(answer)
        if len(paper['answers'])<len(paper['qs']): return dict(message='Đã ghi nhận câu trả lời. Tiếp tục câu kế tiếp.')
        cid=paper['course']; rec=a['exams'][cid]; score=_grade(cid,paper); passed=score>=PASS_MARK
        rec.update(score=score,best=max(rec['best'],score),last=tree_copy(paper))
        if passed and rec['certificate'] is None:
            from . import certificates as ct
            seed=(s.get('journey') or {}).get('seed',0)
            rec['certificate']=dict(id='pcc-accounting-'+cid,course=cid,score=score,date=ct.today_vn(),
                                    serial=ct.serial(seed,cid,rec['attempts']),proof=tree_copy(paper))
        a['active_exam']=None
        return dict(message=f'Kết quả {score}/100. '+('Đạt chứng chỉ trong game.' if passed else 'Chưa đạt 80 điểm; xem bài chữa và thi lại miễn phí.'),
                    exam=dict(course=cid,score=score,passed=passed),celebrate=passed)
    if name.startswith('as_company_'):
        _need(certified(s,'vn_business'),'Thi đạt chứng chỉ Kế toán doanh nghiệp Việt Nam trước khi vào làm.')
        from . import employment as emp
        _need('corp_accounting' in s['careers'],'Nghề kế toán doanh nghiệp chưa được bật trên máy chủ này.')
        c=s['careers']['corp_accounting']
        if name=='as_company_join':
            _need(c['job']['status']!='applying','Hoàn thành hoặc hủy hồ sơ ứng tuyển kế toán đang làm trước.')
            if c['job']['status']!='hired':
                _need(not c.get('open'),'Khép ca kế toán hiện tại trước khi nhận việc.')
                c['job']=emp.hired_record('corp_accounting','ca-hq',c['day'])
            if a['company'] is None: a['company']=company.initial()
            return dict(message='Nhận việc thực hành tại Mây Tre Xanh. Lương kế toán doanh nghiệp ×3; mở chứng từ và ghi sổ bằng VND.')
        book=a['company']; _need(isinstance(book,dict),'Nhận việc doanh nghiệp trước khi làm hồ sơ.')
        _need(c['job']['status']=='hired','Nhận lại việc kế toán trước khi tiếp tục doanh nghiệp.')
        if name=='as_company_inspect':
            company.inspect(book,p.get('task')); return dict(message='Đã mở chứng từ gốc. Đối chiếu trước khi ghi.')
        if name=='as_company_answer': return company.submit(book,p.get('task'),p.get('answer'))
        if name=='as_company_finish':
            _need(book['at']==len(company.tasks(book)),'Hoàn thành sổ và bốn báo cáo trước khi nhận lương ca thực hành.')
            _need(not book['paid'],'Lương ca này đã nhận; không thể nhận lần hai.')
            from . import engine as e
            pay=round(c['job']['salary']*(.85 if c['job']['probation'] else 1))*salary_multiplier(s,'corp_accounting')
            e.money(s,c,pay,f'Lương ca thực hành TT99 · tháng {book["period"]}',f'tt99-salary-{book["period"]}',category='salary')
            from . import journey
            if s['journey']['story']:
                journey._transfer(s,c,-pay,'Lương thực hành chuyển về ví','salary_to_wallet')
                journey._wallet(s['journey'],pay,'salary',f'Lương ca TT99 tháng {book["period"]}','corp_accounting')
                s['journey']['stats']['salary']+=pay
            book['paid']=True; c['job']['days_worked']+=1
            return dict(message=f'Bộ sổ và báo cáo đã khớp. Nhận lương ca thực hành {pay} xu'+(' (lương hợp đồng ×3).' if salary_multiplier(s,'corp_accounting')==3 else '.'),salary=pay,celebrate=True)
        if name=='as_company_next':
            _need(book['paid'],'Nhận lương và xem tổng kết trước khi mở kỳ kế tiếp.')
            company.next_period(book); return dict(message='Mở kỳ tiếp theo; số dư cuối kỳ trước chuyển thành số dư đầu kỳ này.')
    _need(False,'Thao tác học kế toán không tồn tại.')


TABS = ('learn', 'exam', 'company')


def summary(s):
    """What public_state carries on every command: a few numbers (the curriculum and the books ride on as_*
    results only, see view). A save that never opened the school gets the same shape, nothing is stored."""
    a=_school(s); m=salary_multiplier(s,'corp_accounting')
    c=s['careers'].get('corp_accounting'); base=c['job']['salary'] if isinstance(c,dict) and isinstance(c.get('job'),dict) else 0
    book=a.get('company')
    return dict(salary_multiplier=m,base_salary=base,effective_salary=base*m,
                certified=[cid for cid in COURSE_IDS if certified(s,cid)],exam=a.get('active_exam') is not None,
                company=dict(period=book['period'],at=book['at'],paid=book['paid']) if isinstance(book,dict) else None)


def _spec(raw):
    """p['view'] from the client: {tab, sub, course, glossary}. Anything else falls back to defaults."""
    raw=raw if isinstance(raw,dict) else {}
    pick=lambda k,allowed,default:raw.get(k) if isinstance(raw.get(k),str) and raw.get(k) in allowed else default
    return dict(tab=pick('tab',TABS,None),sub=pick('sub',company.SECTIONS,'documents'),
                course=pick('course',COURSE_IDS,None),glossary=raw.get('glossary') is True)


def view(s,raw=None):
    """The school's own view, for one tab (raw: see _spec); raw=None: every part (tests, tools)."""
    spec=_spec(raw) if raw is not None else dict(tab=None,sub=None,course=None,glossary=True)
    tab=spec['tab'];a=_school(s);courses=[]
    for cid in COURSE_IDS:
        c=course(cid); chapters=[];total=0;done=0
        for ch in c['chapters']:
            lessons=[]
            for l in ch['lessons']:
                rec=a['progress'].get(l['id'],{}); completed=lesson_done(s,l['id'])
                total+=1;done+=completed
                lessons.append(dict(id=l['id'],title=l['title'],done=completed,read=bool(rec.get('read')),
                                    solved=len(rec.get('answers',{})),questions=len(l['questions']),minutes=l.get('minutes',15)))
            chapters.append(dict(id=ch['id'],title=ch['title'],lessons=lessons))
        reason='Hoàn thành tất cả bài tập của khóa.' if done<total else 'Thi đạt khóa cơ bản trước.' if cid=='vn_business' and not certified(s,'basic') else 'Hoàn thành bài thi đang làm.' if a['active_exam'] else ''
        rec=a['exams'].get(cid,{}); cert=rec.get('certificate')
        full=tab is None or (tab=='learn' and spec['course'] in (None,cid))  # the lesson index of the course on screen
        courses.append(dict(id=cid,name=c['name'],description=c['description'],chapters=chapters if full else None,total=total,done=done,
                            can_exam=not reason,exam_reason=reason,pass_mark=PASS_MARK,exam_count=min(DRAW[cid],len(_content().EXAM_BANK[cid])),
                            attempts=rec.get('attempts',0),best=rec.get('best',0),score=rec.get('score',0),
                            certificate={k:v for k,v in cert.items() if k!='proof'} if cert else None))
    lesson=None; lid=a['selected']
    if lid and tab in (None,'learn'):
        l=_content().LESSONS[lid]; rec=a['progress'][lid]
        lesson={k:tree_copy(v) for k,v in l.items() if k!='questions' and not k.startswith('_')}
        lesson['questions']=[_safe_question(q,rec['answers'].get(q['id']),q['id'] in rec['answers'],l) for q in l['questions']]
        lesson['done']=lesson_done(s,lid)
    exam=None;paper=a['active_exam']
    if paper:
        at=len(paper['answers']);q=exam_question(paper['course'],paper['qs'][at])
        exam=dict(course=paper['course'],name=course(paper['course'])['name'],at=at,total=len(paper['qs']),
                  question=_safe_question(q) if tab in (None,'exam') else None)
    review={}
    for cid,rec in a['exams'].items():
        last=rec.get('last')
        if last and (tab is None or (tab=='exam' and spec['course'] in (None,cid))):
            review[cid]=dict(score=rec['score'],passed=rec['score']>=PASS_MARK,questions=[dict(question=_safe_question(exam_question(cid,qid),last['answers'][qid],True),
                            correct=_check(exam_question(cid,qid),last['answers'][qid])) for qid in last['qs']])
    book=a['company']
    out=dict(summary(s),courses=courses,selected=lid,lesson=lesson,active_exam=exam,review=review,
             company_unlocked=certified(s,'vn_business'),
             company=company.public(book,spec['sub']) if book and tab in (None,'company') else None,
             certificate_label='Chứng nhận hoàn thành trong Phố Có Chuyện',
             reference=dict(label='Thông tư 99/2025/TT-BTC chính thức',url=company.SOURCE),tab=tab)
    if spec['glossary']:out['glossary']=hints.glossary()
    return out


public=view  # every part: tests and tools


def validate(s):
    from .engine import integer
    if 'accounting_school' not in s: return  # never opened (older saves, new players): nothing stored yet
    a=s['accounting_school']
    _need(isinstance(a,dict) and set(a)==set(initial()) and type(a['v']) is int and a['v']==1,'Tiến độ học kế toán không hợp lệ.')
    lessons=_content().LESSONS
    _need(a['selected'] is None or (isinstance(a['selected'],str) and a['selected'] in lessons),'Bài học đang mở không tồn tại.')
    _need(isinstance(a['progress'],dict) and set(a['progress'])<=set(lessons),'Tiến độ có bài học lạ.')
    for lid,rec in a['progress'].items():
        _need(isinstance(rec,dict) and set(rec)=={'read','answers','attempts'} and type(rec['read']) is bool,'Dữ liệu bài học không hợp lệ.')
        integer(rec['attempts'],0,10**6)
        qs={q['id']:q for q in lessons[lid]['questions']}
        _need(isinstance(rec['answers'],dict) and set(rec['answers'])<=set(qs) and rec['attempts']>=len(rec['answers']),'Đáp án bài học không hợp lệ.')
        for qid,answer in rec['answers'].items(): _need(_check(qs[qid],answer),'Đáp án đã lưu chưa được chấm đúng.')
    _need(a['selected'] is None or a['selected'] in a['progress'],'Bài đang mở chưa được đọc.')
    _need(isinstance(a['exams'],dict) and set(a['exams'])<=set(COURSE_IDS),'Kết quả thi có khóa lạ.')
    def check_paper(cid,paper,complete):
        _need(isinstance(paper,dict) and set(paper)=={'course','attempt','qs','answers'} and paper['course']==cid,'Bài thi không hợp lệ.')
        integer(paper['attempt'],1,10**6)
        qs=paper['qs']; bank={q['id']:q for q in _content().EXAM_BANK[cid]}
        _need(isinstance(qs,list) and len(qs)==min(DRAW[cid],len(bank)) and all(type(x) is str for x in qs) and len(set(qs))==len(qs) and set(qs)<=set(bank),'Đề thi không hợp lệ.')
        _need(qs==_draw(s,cid,paper['attempt']),'Đề thi không khớp lần thi đã mở.')
        answers=paper['answers'];_need(isinstance(answers,dict) and set(answers)==set(qs[:len(answers)]) and len(answers)<=len(qs),'Tiến độ đề thi sai thứ tự.')
        _need((not complete and len(answers)<len(qs)) or (complete and len(answers)==len(qs)),'Bài thi chưa đủ hoặc đã hết câu.')
        for qid,answer in answers.items(): _need(_shape(bank[qid],answer),'Đáp án thi sai định dạng.')
    for cid,rec in a['exams'].items():
        _need(isinstance(rec,dict) and set(rec)=={'attempts','score','best','certificate','last'},'Kết quả thi không hợp lệ.')
        integer(rec['attempts'],1,10**6);integer(rec['score'],0,100);integer(rec['best'],rec['score'],100)
        if rec['last'] is not None:
            check_paper(cid,rec['last'],True)
            _need(rec['last']['attempt']<=rec['attempts'] and rec['score']==_grade(cid,rec['last']),'Điểm thi không khớp bài làm.')
        cert=rec['certificate']
        if cert is not None:
            _need(isinstance(cert,dict) and set(cert)=={'id','course','score','date','serial','proof'} and cert['id']=='pcc-accounting-'+cid and cert['course']==cid,'Chứng nhận sai khóa.')
            check_paper(cid,cert['proof'],True)
            _need(cert['score']==_grade(cid,cert['proof'])>=PASS_MARK and rec['best']>=cert['score'] and cert['proof']['attempt']<=rec['attempts'] and course_done(s,cid),'Chứng nhận không có bài thi đạt hợp lệ.')
            _need(isinstance(cert['date'],str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',cert['date']) and isinstance(cert['serial'],str) and len(cert['serial'])<=40,'Thông tin chứng nhận không hợp lệ.')
    if certified(s,'vn_business'): _need(certified(s,'basic'),'Chứng nhận doanh nghiệp cần chứng nhận cơ bản.')
    if a['active_exam'] is not None:
        paper=a['active_exam'];_need(isinstance(paper,dict),'Bài thi đang làm không hợp lệ.')
        cid=paper.get('course');_need(cid in COURSE_IDS,'Khóa đang thi không tồn tại.')
        check_paper(cid,paper,False)
        _need(cid in a['exams'] and paper['attempt']==a['exams'][cid]['attempts'] and course_done(s,cid),'Bài thi chưa đủ điều kiện.')
        _need(cid!='vn_business' or certified(s,'basic'),'Bài thi doanh nghiệp cần chứng nhận cơ bản.')
    if a['company'] is not None:
        _need(certified(s,'vn_business'),'Doanh nghiệp chưa có chứng nhận hợp lệ.')
        company.validate(a['company'])
