from game.engine import new_state,apply_action,validate_state
from game.content import make_task

class Journey:
    def __init__(self,career='mother_baby',slot=None,day=1):
        from game.careers import ORDER,PLUGINS
        if career in ORDER and career not in PLUGINS:
            import unittest
            raise unittest.SkipTest(career+' is filtered out by MNL_CAREERS')
        self.career=career;self.state=new_state()
        # Employed careers (teacher, accountants) start with a signed contract in tests.
        from game.employment import hired_record,required
        if required(career):self.state['careers'][career]['job']=hired_record(career)
        self.act('select_career')
        if slot is None:self.act('start_day')
        else:
            c=self.state['careers'][career];c.update(day=day,open=True,started=True,turn=1)
            t=make_task(career,day,slot,1);c['tasks']=[t];c['active_task']=t['id']
            mod=PLUGINS.get(career)
            if mod and hasattr(mod,'on_task'):mod.on_task(self.state,c,t)
            validate_state(self.state)
    @property
    def c(self):return self.state['careers'][self.career]
    @property
    def task(self):return next(t for t in self.c['tasks'] if t['id']==self.c['active_task'])
    def get(self,tid):return next(t for t in self.c['tasks'] if t['id']==tid)
    def act(self,action,**payload):
        self.state,result=apply_action(self.state,self.career,action,payload);return result
    def solve(self,tid=None):
        t=self.get(tid) if tid else self.task;tid=t['id'];self.act('ask',task=tid);t=self.get(tid)
        if self.career=='mother_baby' and t.get('gen'):
            from game.giftshop import next_move
            for _ in range(80):
                if self.get(tid)['status'] in ('completed','cancelled'):break
                action,payload=next_move(self.c,self.get(tid));self.act(action,**payload)
        elif self.career=='mother_baby':
            n=t['needs']
            for _ in range(n['qty']):self.act('shop_pick',task=tid,item=n['product'])
            if n['gift']:self.act('shop_pack',task=tid,paper=n['paper'],ribbon='gold',card='Một ngày thật vui!')
            self.act('shop_check',task=tid);self.act('shop_deliver',task=tid)
        elif self.career=='pharmacy':
            n=t['needs']
            if n['referral']:self.act('ph_refer',task=tid)
            else:
                lid=n['product']+'-A';self.act('ph_inspect',task=tid,lot=lid)
                for _ in range(n['qty']):self.act('ph_pick',task=tid,item=lid)
                self.act('ph_check',task=tid,checks=['code','quantity','lot']);self.act('ph_deliver',task=tid)
        elif self.career=='accounting':
            if any(d.get('missing',False) for d in t['docs']):
                self.act('ac_request_source',task=tid);self.act('advance');self.act('advance')
            for d in self.get(tid)['docs']:
                self.act('ac_inspect',task=tid,doc=d['id'])
                if d['amount']!=d['original']:self.act('ac_correct',task=tid,doc=d['id'])
            for d in self.get(tid)['docs']:
                if d.get('duplicate_of'):self.act('ac_duplicate',task=tid,doc=d['id'])
            t=self.get(tid);docs=[d for d in t['docs'] if not d.get('duplicate_of')];done=set()
            for tx in t['transactions']:
                if tx['id'] in done:continue
                ds=[d['id'] for d in docs if d['ref'] in tx['refs']]
                txs=[x['id'] for x in t['transactions'] if x['refs']==tx['refs']]
                self.act('ac_match',task=tid,docs=ds,transactions=txs);done.update(txs)
            self.act('ac_complete',task=tid,explanation='source_report')
        else:
            self.act('cs_identity',task=tid)
            for e in self.get(tid)['evidence']:self.act('cs_evidence',task=tid,evidence=e['id'])
            self.act('cs_propose',task=tid,solution=t['solution']);self.act('cs_execute',task=tid)
            self.act('advance');self.act('advance');self.act('cs_confirm',task=tid);self.act('cs_close',task=tid)
        return self.get(tid)
    def solve_event(self,choice='a'):
        for ev in ('observe','record'):self.act('event_read',evidence=ev)
        self.act('event_choose',choice=choice);self.act('event_confirm')
        self.act('event_step');self.act('event_step')

# v0.3 handlers are explicit; old test journeys still exercise old rules unchanged.
_old_solve=Journey.solve
def solve_desk(j,tid=None,verdict=None):
    """Paperwork desks (pharmacy/accounting/support): the careful path, or a chosen stamp."""
    from game import desk
    t=j.get(tid) if tid else j.task;tid=t['id'];case=desk.secrets(t)
    if t['career']=='customer_care' and t['reply'] is None:
        j.act('desk_reply',task=tid,reply=next(k for k,v in desk.reply_grades(t).items() if v=='best'))
    j.act('ask',task=tid)
    for chk in t['checks']:
        if chk['id']=='count':j.act('desk_count',task=tid,total=case['cash'])
        else:j.act('desk_check',task=tid,check=chk['id'])
    for _ in range(4):
        if not j.get(tid)['pending']:break
        j.act('advance')
    for i in case['issues']:j.act('desk_flag',task=tid,field=i['fields'][0],rule=i['rule'])
    verdict=verdict or next(v for v,k in case['accept'].items() if k=='best')
    j.last=j.act('desk_decide',task=tid,verdict=verdict,confirm=True)
    return j.get(tid)
def _extended_solve(self,tid=None):
    if (self.get(tid) if tid else self.task).get('desk'):return solve_desk(self,tid)
    if self.career not in ('teacher','tour_guide','milk_tea'):return _old_solve(self,tid)
    t=self.get(tid) if tid else self.task;tid=t['id'];self.act('ask',task=tid)
    if self.career=='teacher':
        self.act('lesson_plan',task=tid,steps=['demo','practice','reflect'])
        for st in t['students']:self.act('lesson_attendance',task=tid,student=st['id'],present=st['present'])
        for st in t['students']:
            if st['present']:self.act('lesson_teach',task=tid,student=st['id'],method=st['method'])
        for st in t['students']:
            if st['present']:
                correct=st['submission']==t['lesson']['answer']
                self.act('lesson_grade',task=tid,student=st['id'],correct=correct,feedback='specific' if correct else 'retry')
        self.act('lesson_complete',task=tid,confirm=True)
    elif self.career=='tour_guide':
        from game.extra_content import PLACE_INDEX
        route=list(dict.fromkeys(t['required']+['cafe']))
        self.act('tour_plan',task=tid,route=route)
        for v in t['visitors']:self.act('tour_count',task=tid,visitor=v['id'])
        self.act('tour_depart',task=tid,confirm=True)
        for ix,loc in enumerate(route):
            if ix==1 and t['day']%2==0:self.act('tour_locate',task=tid,location='info')
            for v in t['visitors']:self.act('tour_count',task=tid,visitor=v['id'])
            place=PLACE_INDEX[loc]
            self.act('tour_tell',task=tid,answer=place['answer'])
            self.act('tour_photo',task=tid,object=place['target'])
            self.act('tour_next',task=tid)
        self.act('tour_complete',task=tid,confirm=True)
    else:
        from game.boba import next_move
        for _ in range(60):
            if self.get(tid)['status'] in ('completed','cancelled'):break
            action,payload=next_move(self.c,self.get(tid));self.act(action,**payload)
    return self.get(tid)
Journey.solve=_extended_solve

def solve_activity(j,spec,practice=False):
    j.act('life_activity_start',spec=spec,practice=practice,replace=True)
    a=j.c['life']['activity']
    if a['kind']=='pairs':
        groups={}
        for card in a['cards']:groups.setdefault(card['value'],[]).append(card['id'])
        for ids in groups.values():
            for cid in ids:j.act('life_activity_flip',card=cid)
    elif a['kind']=='sequence':
        for card in sorted(a['cards'],key=lambda c:c['rank']):j.act('life_activity_step',card=card['id'])
        j.act('life_activity_check')
    else:
        for card in a['cards']:j.act('life_activity_assign',card=card['id'],target=card['bin'] if a['kind']=='sort' else card['id'])
    return j.c['life']['activity']
