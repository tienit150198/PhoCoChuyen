"""Local, fictional business simulation for v0.2.

All amounts are game coins. Tax, police outcomes, grants and insurance are
AUTHORED GAME RULES, never claims about real-world law or public services.
Only this module/engine can change assets or money; dialogue is descriptive.
"""
from __future__ import annotations
import copy
import math
from typing import Any
from .jsoncopy import tree_copy

CAREERS = ('mother_baby', 'pharmacy', 'accounting', 'customer_care', 'teacher', 'tour_guide', 'milk_tea')
RULES = {
    'period_days': 7, 'tax_percent': 5, 'utility_base': 3,
    'training_cost': 18, 'bonus_cost': 8, 'max_staff': 4,
    'security_reward': 18, 'reward_cap_period': 54,
    'insurance_percent': 60, 'insurance_daily': 2,
    'label': 'Quy tắc khu phố • tính bằng xu và theo ngày',
}
PROPERTIES = [
    dict(id='cozy', name='Góc tiệm nhỏ', daily_rent=6, setup=0, staff_cap=1, stock_cap=12, icon='home', description='Vừa một người phụ, ít chi phí, đủ để bắt đầu.'),
    dict(id='sunny', name='Tiệm cửa sổ nắng', daily_rent=11, setup=75, staff_cap=2, stock_cap=18, icon='sun', description='Thêm chỗ làm việc và ghế chờ. Đón hai người phụ.'),
    dict(id='garden', name='Tiệm sân vườn', daily_rent=18, setup=140, staff_cap=4, stock_cap=24, icon='plant', description='Một đội nhỏ, nhiều chỗ chứa và sân ngồi nghỉ.'),
]
PROPERTY_INDEX = {x['id']: x for x in PROPERTIES}
SECURITY_ITEMS = [
    dict(id='bell', name='Chuông cửa nhỏ', price=25, protection=1, icon='sun', description='Có tín hiệu khi khách tới, thêm một điểm phòng ngừa.'),
    dict(id='camera', name='Camera góc quầy', price=70, protection=2, icon='camera', description='Mở nguồn ghi hình trong những vụ phát sinh sau khi lắp.'),
    dict(id='lock', name='Khóa kho chắc chắn', price=45, protection=2, icon='lock', description='Giảm nguy cơ mất đồ ở kho; không thay bước kiểm chứng.'),
    dict(id='light', name='Đèn trước hiên', price=30, protection=1, icon='lamp', description='Hiên sáng hơn và dễ quan sát, hiện trực tiếp trong cảnh.'),
]
SECURITY_INDEX = {x['id']: x for x in SECURITY_ITEMS}
ROLE_NAMES = {'sales':'Phụ bán hàng', 'packing':'Gói quà', 'cashier':'Kiểm quầy', 'stock':'Kiểm kho',
              'inspection':'So phiếu', 'filing':'Phân loại hồ sơ', 'reconcile':'Đối chiếu sơ bộ',
              'chat':'Trợ lý hồ sơ', 'followup':'Theo dõi hẹn', 'patrol':'Trông quầy'}
ROLES = {
    'mother_baby':['sales','packing','cashier','stock','patrol'],
    'pharmacy':['inspection','stock','patrol'],
    'accounting':['filing','reconcile','patrol'],
    'customer_care':['chat','followup','patrol'],
}
PEOPLE = {
    'mother_baby': [('Nhi','sales','Nhẹ nhàng, thích xếp đồ theo màu.',72,83),('Bình','packing','Thích làm quà thủ công, không thích bị giục.',64,91),('Yến','stock','Gọn gàng, hay hỏi lại trước khi làm.',78,86),('Tùng','cashier','Vui tính, thích những phiếu rõ ràng.',85,74)],
    'pharmacy': [('Khoa','inspection','Nhanh nhẹn, đang tập thói quen kiểm hai bước.',82,73),('Ngân','stock','Kiên nhẫn, thích nhãn thật rõ.',68,92),('Diệp','inspection','Thường ghi lại điều đã xác minh.',74,87),('Sơn','patrol','Điềm đạm, không kết luận khi chưa đủ nguồn.',77,82)],
    'accounting': [('Huy','filing','Ham học, thích ví dụ thay vì thuật ngữ.',80,73),('Quỳnh','reconcile','Kỹ tính, luôn muốn đọc bản gốc.',65,94),('Dương','filing','Thích xếp từng hồ sơ thật ngăn nắp.',75,84),('Lê','patrol','Cẩn thận với quyền xem dữ liệu.',72,89)],
    'customer_care': [('Mi','chat','Lắng nghe, ghi lại điều khách thật sự cần.',76,85),('Duy','followup','Nhớ lời hẹn, không hứa kết quả chưa có.',71,90),('Phương','chat','Nói ngắn, thích chứng cứ rõ ràng.',84,77),('Đan','patrol','Nhẹ nhàng nhưng giữ ranh giới khi cần.',70,87)],
}
ROLE_NAMES.update({'teaching':'Trợ giảng','attendance':'Hỗ trợ lớp','guiding':'Phụ dẫn đoàn','coordination':'Điều phối đoàn','brewing':'Phụ pha chế'})
ROLES.update({'teacher':['teaching','attendance','patrol'],'tour_guide':['guiding','coordination','patrol'],'milk_tea':['brewing','stock','patrol']})
PEOPLE.update({
 'teacher':[('Thảo','teaching','Thích hình mẫu, hỏi trước khi hướng dẫn.',75,87),('Sơn','attendance','Ghi nhận rõ việc có mặt, không đoán.',72,90),('My','teaching','Thích chuẩn bị thẻ hoạt động.',80,80),('Hòa','patrol','Giữ góc lớp gọn, bảo vệ sự riêng tư.',74,89)],
 'tour_guide':[('Hải','coordination','Nhớ điểm hẹn và lịch đoàn.',78,87),('Quỳnh','guiding','Thích kể chuyện từ bảng thông tin.',72,93),('Phương','coordination','Kiểm số người trước khi chuyển điểm.',84,78),('An','patrol','Điềm đạm, hỗ trợ khi cần xác minh.',75,88)],
 'milk_tea':[('Nhi','brewing','Nhớ công thức đã chốt với khách.',80,79),('Bình','stock','Thích ghi ngày dùng hết từng mẻ.',70,92),('Hạ','brewing','Thích ly ít đường và quầy gọn.',75,88),('Tâm','patrol','Quan sát cửa, hỏi lại trước khi kết luận.',74,86)],
})

from .careers import PLUGINS as _PLUGINS
from . import archive as ar
CAREER_ROLE_NAMES = {}


def role_name(career, role):
    return CAREER_ROLE_NAMES.get(career, {}).get(role) or ROLE_NAMES.get(role, role)


for _cid, _mod in _PLUGINS.items():
    # Role ids may repeat across careers with different names ('prep',
    # 'cashier'…): names are looked up per career first.
    CAREER_ROLE_NAMES[_cid] = dict(_mod.SPEC.get('roles', {}))
    for _r, _n in _mod.SPEC.get('roles', {}).items():
        ROLE_NAMES.setdefault(_r, _n)
    ROLES[_cid] = list(_mod.SPEC.get('roles', {})) + ['patrol']
    PEOPLE[_cid] = [tuple(x) for x in _mod.SPEC['staff']]
CAREERS = CAREERS + tuple(_PLUGINS)
CANDIDATES = []
for cid, people in PEOPLE.items():
    for i,(name,role,bio,speed,precision) in enumerate(people):
        CANDIDATES.append(dict(id=f'{cid}-staff-{i+1}', career=cid, name=name, role=role, bio=bio,
             speed=speed, precision=precision, friendliness=82+i*3, learning=70+i*5,
             wage=9+i*2, hire_cost=30+i*8, avatar=i, color=['#e9a7b9','#8fc9bf','#b9acdc','#e9c188'][i]))
CANDIDATE_INDEX = {x['id']:x for x in CANDIDATES}
CASE_KINDS = {
    'misplaced': ('Một món chưa tìm thấy', 'Số kiểm nhanh và vị trí hàng đang không khớp. Mình kiểm từng nguồn trước nhé.'),
    'unpaid': ('Một lượt chưa thanh toán', 'Có người đã cầm gói đồ ra cửa; quầy chưa thấy giao dịch tương ứng.'),
    'theft': ('Thiếu tài sản ở quầy', 'Có dấu hiệu một món không còn ở vị trí đã ghi. Chưa kết luận ai trước khi kiểm chứng.'),
    'snatch': ('Giật túi trước hiên', 'Một khách báo bị lấy túi trước cửa. Hỗ trợ khách và báo người phụ trách, không truy đuổi.'),
}
INCIDENT_KINDS = {
    'accident': ('Vỡ chậu cây ở quầy', 'Một chậu cây bị va đổ khi chuyển đồ. Cần kiểm lối đi và nghe người liên quan.'),
    'equipment': ('Máy in thiệp ngừng chạy', 'Có tiếng kẹt giấy, máy in cần được kiểm tra trước khi dùng tiếp.'),
    'wrong_item': ('Khay bị đặt nhầm món', 'Bản nháp giao việc và khay chưa khớp. Chưa có đơn sai nào được bàn giao.'),
    'damage': ('Đồ ở bàn bị hỏng', 'Một vật ở bàn làm việc bị hư. Cần hỏi và kiểm ghi nhận, không suy diễn từ tính cách nhân viên.'),
}


def initial_operations(career: str, balance: int=320, day: int=1) -> dict:
    return dict(version=1, seq=0, rng=7319+sum(map(ord,career)),
        property=dict(tier='cozy',changed_day=0), staff=[], attendance={}, incident=None, incident_history=[],
        equipment=dict(condition=100,label='Bàn và dụng cụ'),
        finance=dict(opening_balance=balance,ledger=[],bills=[],period_start=day,period_days=0,
                     period_revenue=0,period_rent=0,period_tax_adjustments=0,history=[],last_closed=0,grant_used=False),
        security=dict(items=[],insurance=False,cases=[],active=None,last_event_day=0,period_rewards=0,period_claims=0),
        day_staff_incident=0,work_ticks=0,staff_chats={},policy='respectful')


def _core():
    # Lazy import: the engine owns GameError, transaction boundaries and money.
    from . import engine
    return engine


def _id(c:dict, prefix:str) -> str:
    c['ops']['seq']+=1
    return f"{prefix}-{c['ops']['seq']}"


def _random(c:dict, n:int=100) -> int:
    o=c['ops'];o['rng']=(1664525*o['rng']+1013904223)&0xffffffff
    return o['rng']%n


def classify_money(amount:int, reason:str, explicit:str|None=None) -> str:
    if explicit:return explicit
    if reason.startswith('Hoàn thành:'):return 'revenue'
    if reason.startswith('Khép chuyện:'):return 'story_reward'
    if 'nhập' in reason.lower() or 'Đặt' in reason:return 'stock'
    if 'gói' in reason.lower():return 'materials'
    if reason.startswith('Mua'):return 'upgrade'
    return 'other_income' if amount>0 else 'other_cost'


def record_money(c:dict, amount:int, reason:str, ref:str|None=None, category:str|None=None) -> None:
    f=c['ops']['finance'];cat=classify_money(amount,reason,category)
    f['ledger'].append(dict(id=_id(c,'entry'),day=c['day'],turn=c['turn'],amount=amount,category=cat,reason=reason,ref=ref))
    if cat=='revenue' and amount>0:f['period_revenue']+=amount
    trim_ledger(c)


LEDGER_HIGH=200   # past this many rows the oldest move to the archive (game/archive.py),
LEDGER_KEEP=120   # down to this many, but never rows of the last LEDGER_DAYS days
LEDGER_DAYS=8     # (the lãi/lỗ chart reads 7 days), and never more than LEDGER_MAX rows.
LEDGER_MAX=1200

def trim_ledger(c:dict) -> None:
    """Bounded cash book in the save. Rows moved to the archive are summed into the
    opening balance, so opening_balance + the rows in the save == the wallet, and
    the first opening balance + every archived row + the rows in the save == the
    wallet too. Also run once on older saves by engine.migrate_state."""
    f=c['ops']['finance'];rows=f['ledger']
    if len(rows)<=LEDGER_HIGH:return
    cut=len(rows)-LEDGER_KEEP;recent=c['day']-LEDGER_DAYS
    while cut>0 and rows[cut-1]['day']>=recent:cut-=1
    cut=max(cut,len(rows)-LEDGER_MAX)
    if cut<=0:return
    ar.record(rows[:cut],'ledger',c)
    f['opening_balance']+=sum(x['amount'] for x in rows[:cut])
    f['ledger']=rows[cut:]


def bill(c:dict, bid:str, kind:str, label:str, amount:int, due:int, source:str) -> dict|None:
    if amount<=0:return None
    f=c['ops']['finance']
    prior=next((b for b in f['bills'] if b['id']==bid),None)
    if prior:return prior
    row=dict(id=bid,kind=kind,label=label,amount=amount,due=due,created_day=c['day'],status='unpaid',
             source=source,extended=False,paid_day=None)
    f['bills'].append(row)
    # Keep unpaid invoices regardless of age. Trim only completed records.
    if len(f['bills'])>BILLS_HIGH:trim_bills(c)
    return row


BILLS_HIGH=120  # past this many bills the oldest paid ones move to the archive,
BILLS_PAID=40   # down to this many paid ones (the Sổ tiệm lists the last 15); unpaid ones always stay

def trim_bills(c:dict,owner=None) -> None:
    f=c['ops']['finance']
    paid=ar.last([b for b in f['bills'] if b['status']=='paid'], BILLS_PAID, 'bills', c if owner is None else owner)
    f['bills']=paid+[b for b in f['bills'] if b['status']!='paid']


def _attendance(c:dict, employee:dict) -> None:
    day=str(c['day']);a=c['ops']['attendance'].setdefault(day,{})
    a.setdefault(employee['id'],dict(name=employee['name'],wage=employee['wage'],role=employee['role']))


def paused(o:dict, e:dict) -> bool:
    """A real (not practice) incident of this employee is still open: they stop work until it is closed."""
    i=o['incident']
    return bool(i and not i['practice'] and i['status']!='resolved' and i['employee']==e['id'])


def _payroll(c:dict, day:int, staff_id:str|None=None) -> list[dict]:
    created=[]
    for sid,a in c['ops']['attendance'].get(str(day),{}).items():
        if staff_id and sid!=staff_id:continue
        b=bill(c,f'wage-{day}-{sid}','wage',f"Lương {a['name']} · ngày {day}",a['wage'],day+1,sid)
        if b:created.append(b)
    return created


def on_start(s:dict,c:dict,career:str) -> None:
    for e in c['ops']['staff']:
        if e['status']!='hired':continue
        if e['schedule']=='daily':e['on_shift']=True
        elif e['schedule']=='odd':e['on_shift']=c['day']%2==1
        elif e['schedule']=='even':e['on_shift']=c['day']%2==0
        e['fatigue']=max(0,e['fatigue']-25)
        e['rest_until']=0
    # No real-time accrual: nothing happens while the server or game is idle.


def on_close(s:dict,c:dict,career:str) -> dict:
    o=c['ops'];f=o['finance'];eng=_core();day=c['day']
    eng.need(f['last_closed']!=day,'Ngày này đã được kết sổ.')
    invoices=_payroll(c,day)
    present=o['attendance'].get(str(day),{});workers=len(present)
    # The day's summary names what each hired person did: jobs, no shift today, or paused by an open incident.
    team=[dict(name=e['name'],jobs=present[e['id']].get('jobs',0) if e['id'] in present else 0,shift=e['id'] in present,paused=paused(o,e))
          for e in o['staff'] if e['status']=='hired']
    utility=RULES['utility_base']+workers+(1 if 'camera' in o['security']['items'] else 0)
    bill(c,f'utility-{day}','utility',f'Điện nước · ngày {day}',utility,day+1,f'day-{day}')
    if o['security']['insurance']:
        bill(c,f'insurance-{day}','insurance','Phí bảo vệ tài sản',RULES['insurance_daily'],day+1,f'day-{day}')
    f['period_days']+=1;f['period_rent']+=PROPERTY_INDEX[o['property']['tier']]['daily_rent']
    period=None
    if f['period_days']>=RULES['period_days']:
        tax=math.ceil(f['period_revenue']*RULES['tax_percent']/100)
        pid=f"period-{f['period_start']}-{day}"
        bill(c,'rent-'+pid,'rent',f"Mặt bằng · kỳ {f['period_start']}–{day}",f['period_rent'],day+2,pid)
        bill(c,'tax-'+pid,'tax',f'Thuế {RULES["tax_percent"]}% · kỳ kết ngày {day}',tax,day+2,pid)
        period=dict(id=pid,start=f['period_start'],end=day,revenue=f['period_revenue'],tax=tax,rent=f['period_rent'],rate=RULES['tax_percent'])
        f['history'].insert(0,period);f['history']=ar.first(f['history'], 60, 'finance.periods', c)
        f.update(period_start=day+1,period_days=0,period_revenue=0,period_rent=0,period_tax_adjustments=0)
        o['security']['period_rewards']=0;o['security']['period_claims']=0
        eng.log(s,c,'period',f'Kết kỳ: doanh thu {period["revenue"]} xu, thuế {tax} xu, thuê {period["rent"]} xu.',ref=pid)
    f['last_closed']=day
    o['attendance']={k:v for k,v in o['attendance'].items() if int(k)>=day-14}
    return dict(wages=sum(b['amount'] for b in invoices),utilities=utility,rent_accrued=PROPERTY_INDEX[o['property']['tier']]['daily_rent'],
                period=period,unpaid=sum(b['amount'] for b in f['bills'] if b['status']=='unpaid'),staff=team)


def _employee(c:dict,sid:Any) -> dict:
    e=next((x for x in c['ops']['staff'] if x['id']==sid and x['status']=='hired'),None)
    _core().need(e,'Không có nhân viên đang làm việc với mã này.')
    return e


def _case(c:dict,p:dict) -> dict:
    sid=p.get('case') or c['ops']['security']['active']
    row=next((x for x in c['ops']['security']['cases'] if x['id']==sid),None)
    _core().need(row,'Không tìm thấy hồ sơ an ninh này.')
    return row


def spawn_case(s:dict,c:dict,career:str,kind:str,practice:bool=False) -> dict:
    eng=_core();sec=c['ops']['security']
    eng.need(kind in CASE_KINDS,'Tình huống an ninh không tồn tại.')
    active=next((x for x in sec['cases'] if x['id']==sec['active']),None)
    eng.need(not active or active['status']=='closed','Hãy xử lý hoặc cất hồ sơ đang mở trước.')
    title,opening=CASE_KINDS[kind];cid=_id(c,'security')
    truth='misplaced' if kind=='misplaced' else 'forgot_payment' if kind=='unpaid' else 'theft'
    loss=dict(kind='none',item=None,qty=0,value=0,cash=0)
    if truth=='theft':
        from .content import PRODUCT_INDEX,LOT_INDEX
        candidates=[item for item in c['stock'] if eng.available(c,item)>0 and (career!='pharmacy' or (LOT_INDEX[item]['status']=='available' and item not in c['held_lots'] and LOT_INDEX[item]['valid_until']>=c['day']))]
        if kind=='snatch':
            # NPC's fictional bag; never debit the player's wallet for someone else's property.
            loss=dict(kind='npc_property',item=None,qty=1,value=0,cash=0)
        elif candidates:
            item=candidates[_random(c,len(candidates))];product=PRODUCT_INDEX.get(item) or LOT_INDEX.get(item)
            loss=dict(kind='stock',item=item,qty=1,value=product.get('cost',18),cash=0)
            if not practice:c['stock'][item]-=1
        else:
            amount=min(18,c['money'])
            loss=dict(kind='cash',item=None,qty=0,value=amount,cash=amount)
            if amount and not practice:eng.money(s,c,-amount,'Thiệt hại đã ghi nhận',cid,category='theft_loss')
    protection=sum(SECURITY_INDEX[i]['protection'] for i in sec['items'])
    base=[
      dict(id='inventory',title='Đối chiếu kho / tài sản',text='Vật đang ở kệ bên cạnh, số đếm toàn tiệm vẫn đủ.' if truth=='misplaced' else 'Một lượt có gói hàng nhưng chưa thấy bước thanh toán.' if truth=='forgot_payment' else 'Đã đối chiếu: có tài sản bị lấy, không nằm trong hàng giữ hoặc giao dịch hợp lệ.'),
      dict(id='witness',title='Lời người có mặt',text='Nhân viên xác nhận đã chuyển món sang kệ bên cạnh để dọn.' if truth=='misplaced' else 'Khách quay lại nói đã quên thanh toán và đồng ý trả gói chưa mua.' if truth=='forgot_payment' else 'Người có mặt cung cấp mô tả hành vi, thời điểm và hướng di chuyển trong cảnh.'),
    ]
    if 'camera' in sec['items']:
        base.append(dict(id='camera',title='Camera đã lắp trước sự việc',text='Đoạn ghi hình khớp việc chuyển kệ.' if truth=='misplaced' else 'Đoạn ghi hình cho thấy khách bỏ qua quầy thanh toán, rồi quay lại.' if truth=='forgot_payment' else 'Đoạn ghi hình xác nhận diễn biến và thời điểm đã báo. Không công khai hình/phiếu của khách khác.'))
    row=dict(id=cid,kind=kind,title=title,opening=opening,practice=practice,day=c['day'],status='noticed',read=[],evidence=base,
        finding=None,ready_turn=0,reported=False,recovered=False,reward_claimed=False,insurance_claimed=False,
        loss=loss,recovered_value=0,reward=0,protection=protection,insured_at_event=sec['insurance'],
        _truth=truth,_roll=_random(c),timeline=[opening],outcome=None)
    sec['cases'].append(row);sec['active']=cid
    if len(sec['cases'])>100:sec['cases']=[x for x in sec['cases'] if x['status']!='closed']+ar.last([x for x in sec['cases'] if x['status']=='closed'],70,'security.cases',c)
    if not practice:sec['last_event_day']=c['day']
    eng.log(s,c,'security_practice' if practice else 'security',title+(' · diễn tập, không mất/nhận xu' if practice else ''),ref=cid)
    return row


def spawn_incident(s:dict,c:dict,career:str,kind:str='accident',practice:bool=False,employee:dict|None=None) -> dict:
    eng=_core();o=c['ops'];eng.need(kind in INCIDENT_KINDS,'Tình huống nhân viên không tồn tại.')
    eng.need(not o['incident'] or o['incident']['status']=='resolved','Có sự cố nhân viên chưa xử lý xong.')
    title,opening=INCIDENT_KINDS[kind];eid=_id(c,'incident')
    staff=employee or next((e for e in o['staff'] if e['status']=='hired'),None)
    row=dict(id=eid,kind=kind,title=title,opening=opening,practice=practice,day=c['day'],employee=staff['id'] if staff else None,
             employee_name=staff['name'] if staff else 'Bạn phụ việc diễn tập',status='noticed',read=[],choice=None,ready_turn=0,
             evidence=[dict(id='worklog',title='Xem việc đã giao',text='Lối chuyển đồ bị hẹp và nhãn hướng dẫn chưa rõ.' if kind in ('accident','wrong_item') else 'Thiết bị đã được dùng liên tục; nhật ký ghi đúng thời điểm ngừng hoạt động.'),
                       dict(id='listen',title='Nghe người liên quan',text='Mình làm va vào đồ trong lúc chuyển. Mình muốn cùng sửa và tập lại cách làm.' if kind=='accident' else 'Mình đã đập vật xuống bàn lúc bực, làm nó hỏng. Mình nhận lỗi và cần dừng việc để trao đổi.' if kind=='damage' else 'Mình thấy lỗi nên đã dừng bước giao cuối, chưa bàn giao sai cho khách.')],
             timeline=[opening])
    o['incident']=row
    if not practice:
        o['equipment']['condition']=max(35,o['equipment']['condition']-25)
        o['day_staff_incident']=c['day']
        if staff:staff['morale']=max(15,staff['morale']-8);staff['errors']+=1
    eng.log(s,c,'staff_practice' if practice else 'staff_incident',title,ref=eid)
    return row


def _assist(s:dict,c:dict,career:str,e:dict) -> str|None:
    eng=_core();role=e['role']
    if career in _PLUGINS:
        # Plugins own their roles and may help with an empty queue (field,
        # coop, housekeeping…); the built-in branches below are legacy-only.
        t=next((t for t in c['tasks'] if t['id']==c['active_task'] and t['status'] not in ('completed','referred','cancelled')),None)
        mod=_PLUGINS[career]
        try:note=mod.assist(s,c,e,t) if hasattr(mod,'assist') else None
        except eng.GameError:note=None  # a helper never blocks the player's own action
        if note is None and role=='patrol':return 'Đã kiểm một vòng quầy và cửa kho; chưa kết luận về người nào.'
        return note
    if role=='patrol':return 'Đã kiểm một vòng quầy và cửa kho; chưa kết luận về người nào.'
    if role=='stock':
        delivery=next((x for x in c['shipments'] if eng.shipment_here(c,career,x)),None)
        if delivery:
            # Actual received quantity only, once it is at the door on the shop clock; the paid order already exists.
            eng.stock_received(s,c,career,delivery,delivery['actual'])
            eng.metric(c,'restocked');eng.log(s,c,'stock',f"{e['name']} kiểm {delivery['actual']} món thật nhận từ {delivery['id']}.",ref=delivery['id'])
            return 'Đã kiểm số thực nhận và nhập kiện '+delivery['id']+'.'
        return 'Đã kiểm vị trí và số lượng kệ, chưa nhập thêm món nào.'
    t=next((t for t in c['tasks'] if t['id']==c['active_task'] and t['status'] not in ('completed','referred','cancelled')),None)
    if not t:return None
    if t.get('desk'):
        from . import desk
        return desk.assist(s,c,t,role)
    if career=='mother_baby':
        # Advice, first-time-parent kits, returns and party orders need the player's own judgement.
        if not t['known'] or t.get('gift_kind') in ('safety','kit','return','bulk') or (t.get('gift') or {}).get('pick')=='open':return None
        n=t['needs']
        if role=='sales' and t['basket'].get(n['product'],0)<n['qty'] and eng.available(c,n['product'])>0 and sum(t['basket'].values())<6:
            t['basket'][n['product']]=t['basket'].get(n['product'],0)+1;t['checked']=False;t['pack']=None
            return 'Đã lấy một món đúng yêu cầu vào khay; bạn vẫn kiểm trước khi giao.'
        if role=='packing' and n['gift'] and not t['pack'] and t['basket']=={n['product']:n['qty']}:
            t['pack']=dict(paper=n['paper'],ribbon='gold',card='Một món quà nhỏ, gửi thật nhiều niềm vui.');t['checked']=False
            return 'Đã gói theo màu đã xác nhận; chưa thu tiền hay giao hàng.'
        if role=='cashier' and not t['checked']:
            try:eng.ensure_shop(t,c)
            except eng.GameError:return None
            t['checked']=True;return 'Đã kiểm đủ đơn; bạn quyết định thanh toán và bàn giao.'
    elif career=='pharmacy' and role=='inspection' and t['known'] and not t['needs']['referral']:
        from .content import LOT_INDEX
        lid=next((k for k,l in LOT_INDEX.items() if l['product']==t['needs']['product'] and l['status']=='available' and l['valid_until']>=c['day'] and k not in c['held_lots'] and k not in t['inspected']),None)
        if lid:t['inspected'].append(lid);return 'Đã đọc nhãn lô '+lid+'. Bạn vẫn đối chiếu mã, lượng, lô và bàn giao.'
    elif career=='accounting' and role in ('filing','reconcile'):
        doc=next((d for d in t['docs'] if not d.get('missing') and d['id'] not in t['inspected']),None)
        if doc:t['inspected'].append(doc['id']);return 'Đã đưa bản gốc '+doc['id']+' lên bàn. Chưa sửa số hay kết luận thay bạn.'
    elif career=='customer_care':
        if role=='chat' and t['identity']:
            ev=next((v for v in t['evidence'] if v['id'] not in t['inspected']),None)
            if ev:t['inspected'].append(ev['id']);return 'Đã chuyển nguồn '+ev['title']+' tới bàn. Chưa phê duyệt hay đóng vụ.'
        if role=='followup' and t['status'] in ('executing','awaiting_confirmation','handed_over'):
            return 'Đã nhắc đầu mối của vụ '+t['title']+'. Kết quả vẫn cần xác nhận, không tự đóng.'
    elif career in ('teacher','tour_guide','milk_tea'):
        if not t['known']:return None
        if role=='teaching':return 'Đã chuẩn bị thẻ minh họa; bạn chọn phương pháp và phản hồi cho từng học sinh.'
        if role=='attendance':return 'Đã đối chiếu ghế và danh sách; bạn xác nhận từng bạn có mặt.'
        if role=='guiding':return 'Đã mở bảng thông tin ở điểm đến; bạn kể chuyện và chọn góc ảnh.'
        if role=='coordination':return 'Đã nhắc điểm hẹn cho đoàn; bạn vẫn xác nhận từng người trước khi đi.'
        if role=='brewing':return 'Đã đọc lại phiếu trà; bạn vẫn chọn nguyên liệu và kiểm vị trước khi giao.'
    return None


WORK_ACTIONS = {'advance','more_work','ask','order_stock','receive_stock','event_step','event_read','shop_pick','shop_pack','shop_check','shop_deliver','ph_pick','ph_inspect','ph_check','ph_deliver','ph_refer','ac_inspect','ac_correct','ac_match','ac_duplicate','ac_complete','ac_request_source','cs_identity','cs_evidence','cs_propose','cs_execute','cs_confirm','cs_close','cs_handover','desk_flag','desk_check','desk_count','desk_reply','desk_decide'}


def tick(s:dict,c:dict,career:str,action:str) -> list[str]:
    eng=_core();o=c['ops'];notes=[]
    # Viewing menus, chatting and every practice-only action do NOT advance work.
    prefixes=('lesson_','tour_','tea_','inv_order','inv_receive')+((_PLUGINS[career].SPEC['prefix'],) if career in _PLUGINS else ())
    if not c['open'] or (action not in WORK_ACTIONS and not action.startswith(prefixes)):return notes
    o['work_ticks']+=1
    for e in o['staff']:
        if e['status']!='hired' or not e['on_shift']:continue
        # Their own open incident pauses them until it is closed. Checked before the shift is recorded: a paused
        # employee used to be logged present (wage billed, "ca thực làm") and grow tired for days doing nothing.
        if paused(o,e):continue
        if e['rest_until']>c['turn']:
            e['fatigue']=max(0,e['fatigue']-4);continue
        _attendance(c,e);e['fatigue']=min(100,e['fatigue']+1)
        if e['fatigue']>=90:
            e['rest_until']=c['turn']+4;notes.append(e['name']+' đang nghỉ một chút rồi quay lại.');continue
        e['progress']+=1
        interval=3 if e['speed']>=80 else 4
        if e['progress']<interval:continue
        e['progress']=0
        note=_assist(s,c,career,e)
        if note:
            e['jobs']+=1;e['last_work']=note
            row=o['attendance'][str(c['day'])][e['id']];row['jobs']=row.get('jobs',0)+1  # today's count (optional key)
            eng.log(s,c,'staff_work',e['name']+': '+note,ref=e['id'])
            if e['jobs']%4==1:notes.append(e['name']+': '+note)
            risk=max(3,33-e['precision']//3+e['fatigue']//6)
            if e['jobs']>=3 and o['day_staff_incident']!=c['day'] and not (o['incident'] and o['incident']['status']!='resolved') and not (c['event'] and c['event']['stage']!='resolved') and _random(c)<risk:
                # Rare authored misconduct is a separate event, not inferred from appearance.
                choices=['accident','equipment','wrong_item']
                kind='damage' if e['morale']<45 and _random(c,5)==0 else choices[_random(c,3)]
                spawn_incident(s,c,career,kind,False,e)
                notes.append('Có sự cố của '+e['name']+'. Bạn ấy tạm dừng việc tới khi xử lý xong: mở Sổ tiệm → Nhân viên.')
    incident=o['incident']
    if incident and incident['status']=='repairing' and c['turn']>=incident['ready_turn']:
        incident['status']='ready';notes.append('Việc sửa đã về kết quả. Hãy kiểm và xác nhận trong Sổ tiệm.')
    for case in o['security']['cases']:
        if case['status']=='reported' and c['turn']>=case['ready_turn']:
            if case['_truth']!='theft':case['outcome']='not_theft'
            elif case['_roll']<min(97,64+case['protection']*5+len(case['read'])*4):case['outcome']='arrested'
            else:case['outcome']='unrecovered'
            case['status']='result';case['ready_turn']=0
            message={'not_theft':'Đã xác minh: không phải vụ trộm. Cần đóng hồ sơ bằng kết luận đã kiểm.',
                     'arrested':'Công an khu phố đã bắt được người lấy tài sản. Mời kiểm biên bản và nhận lại tài sản.',
                     'unrecovered':'Đã xác minh thiệt hại nhưng chưa thu hồi được tài sản. Có thể xử lý hỗ trợ nếu đủ điều kiện.'}[case['outcome']]
            case['timeline'].append(message);notes.append(message)
    sec=o['security']
    active=next((x for x in sec['cases'] if x['id']==sec['active']),None)
    busy=(active and active['status']!='closed') or (incident and incident['status']!='resolved') or (c['event'] and c['event']['stage']!='resolved')
    if c['day']>=2 and c['day_completed']>=1 and o['work_ticks']>=10 and sec['last_event_day']!=c['day'] and not busy and s['settings'].get('securityEvents',True):
        if c['life']['mode']=='calm':kind='misplaced'
        else:kind=['misplaced','unpaid','theft','snatch'][(c['day']-2)%4]
        protection=sum(SECURITY_INDEX[i]['protection'] for i in sec['items'])+sum(e['role']=='patrol' and e['on_shift'] and e['status']=='hired' for e in o['staff'])*2
        if kind in ('theft','snatch') and _random(c)<min(60,protection*8):
            sec['last_event_day']=c['day'];eng.log(s,c,'security','Đã kiểm quầy trong ca đông. Không phát sinh thiệt hại hôm nay.')
        else:
            spawn_case(s,c,career,kind);notes.append('Có chuyện cần kiểm tra ở quầy. Mở Sổ tiệm → An ninh.')
    return notes


def action(s:dict,c:dict,career:str,name:str,p:dict) -> dict:
    eng=_core();need=eng.need;o=c['ops'];f=o['finance'];sec=o['security'];result=dict(message='Đã cập nhật Sổ tiệm.')
    # Mutations requiring coins/assets always require an explicit confirmation.
    confirm_names={'hire','train','bonus','dismiss','pay_bill','pay_all','move_property','buy_security','incident_choose','report','recover','reward','insurance_claim','grant','insurance_toggle'}
    name=name.removeprefix('ops_')
    if name in confirm_names:need(p.get('confirm') is True,'Cần xác nhận chi phí hoặc hành động trước khi thực hiện.')
    if name=='hire':
        candidate=CANDIDATE_INDEX.get(p.get('candidate'))
        need(candidate and candidate['career']==career,'Ứng viên không thuộc nghề này.')
        need(not any(e['id']==candidate['id'] and e['status']=='hired' for e in o['staff']),'Nhân viên này đã được nhận.')
        need(sum(e['status']=='hired' for e in o['staff'])<PROPERTY_INDEX[o['property']['tier']]['staff_cap'],'Mặt bằng hiện tại chưa đủ chỗ cho thêm nhân viên.')
        eng.money(s,c,-candidate['hire_cost'],'Tuyển '+candidate['name'],candidate['id'],category='recruitment')
        old=next((e for e in o['staff'] if e['id']==candidate['id']),None)
        if old:o['staff'].remove(old)
        employee=dict(candidate,status='hired',hired_day=c['day'],schedule='daily',on_shift=c['open'],morale=85,fatigue=0,
                      progress=0,jobs=old['jobs'] if old else 0,errors=old['errors'] if old else 0,training=old['training'] if old else 0,
                      trained_day=old['trained_day'] if old else 0,bonus_day=old['bonus_day'] if old else 0,rest_until=0,last_work='Chưa bắt đầu công việc.',warnings=old['warnings'] if old else 0)
        if old:employee['precision']=old['precision']
        o['staff'].append(employee);eng.log(s,c,'staff',employee['name']+' gia nhập đội. Lương '+str(employee['wage'])+' xu/ca thực làm.',ref=employee['id'])
        result['message']=employee['name']+' đã có mặt. Bạn có thể giao việc và xếp lịch.'
    elif name in ('assign','shift','schedule','rest','train','bonus','dismiss','warn','staff_talk'):
        e=_employee(c,p.get('employee'))
        if name=='assign':
            need(p.get('role') in ROLES[career],'Vai trò không thuộc nghề.');e['role']=p['role'];e['progress']=0
            result['message']='Đã giao '+role_name(career,e['role'])+' cho '+e['name']+'.'
        elif name=='schedule':
            need(p.get('schedule') in ('daily','odd','even','manual'),'Lịch chưa hợp lệ.');e['schedule']=p['schedule'];result['message']='Lịch mới áp dụng từ lần mở ca tiếp theo.'
        elif name=='shift':
            need(type(p.get('on')) is bool,'Trạng thái ca không hợp lệ.');e['on_shift']=p['on'];result['message']=e['name']+(' đã vào ca.' if e['on_shift'] else ' đã nghỉ ca. Lương đã phát sinh vẫn được giữ.')
        elif name=='rest':
            need(c['open'],'Mở ca trước khi cho nghỉ giữa giờ.');need(e['rest_until']<=c['turn'],'Nhân viên đang nghỉ rồi.')
            e['rest_until']=c['turn']+4;e['morale']=min(100,e['morale']+3);result['message']=e['name']+' nghỉ trong bốn nhịp làm việc.'
        elif name=='train':
            need(e['trained_day']!=c['day'],'Hôm nay đã có một buổi hướng dẫn rồi.');need(e['precision']<99,'Kỹ năng kiểm tra đã đạt mức tối đa.')
            eng.money(s,c,-RULES['training_cost'],'Hướng dẫn '+e['name'],e['id'],category='training')
            e['precision']=min(99,e['precision']+7);e['training']+=1;e['trained_day']=c['day'];e['morale']=min(100,e['morale']+4)
            result['message']='Đã tập kiểm trước khi giao. Độ cẩn thận tăng, rủi ro sai sót giảm.'
        elif name=='bonus':
            need(e['bonus_day']!=c['day'],'Hôm nay đã thưởng cho bạn ấy rồi.');eng.money(s,c,-RULES['bonus_cost'],'Thưởng '+e['name'],e['id'],category='bonus')
            e['bonus_day']=c['day'];e['morale']=min(100,e['morale']+12);result['message']='Đã tặng thưởng và ghi nhận việc của '+e['name']+'.'
        elif name=='dismiss':
            incident=o['incident'];need(not incident or incident['employee']!=e['id'] or incident['status']=='resolved' or incident['practice'],'Bạn ấy còn sự cố đang mở. Vào Sổ tiệm › Nhân viên: kiểm 2 nguồn, chọn cách xử lý, sau 2 nhịp bấm “Kiểm & hoàn tất”, rồi mới cho nghỉ được.')
            _payroll(c,c['day'],e['id']);e['status']='former';e['on_shift']=False
            result['message']='Đã kết thúc hợp tác. Khoản lương đã làm vẫn nằm trong sổ cần trả.'
        elif name=='warn':
            need(p.get('confirm') is True,'Xác nhận lời nhắc có ghi nhận trước nhé.');need(e['warnings']<3,'Đã có ba lần nhắc; hãy xem lại phân công hoặc kết thúc hợp tác.')
            e['warnings']+=1;e['morale']=max(20,e['morale']-5);result['message']='Đã ghi lời nhắc và yêu cầu kiểm trước khi làm. Không tự khấu trừ lương.'
        else:
            text=eng.clean_text(p.get('text'),500);norm=eng.normalize(text)
            if any(x in norm for x in ('da lam','cong viec','lam gi','hom nay')):reply=e['last_work']
            elif any(x in norm for x in ('nghi','met','ca')):reply=f"Mức mệt hiện tại của mình là {e['fatigue']}/100. Bạn có thể cho mình nghỉ hoặc đổi ca trong hồ sơ nhé."
            elif any(x in norm for x in ('hong','vo','pha','sai')):
                i=o['incident'];reply=('Mình muốn cùng kiểm lại: '+i['title']+'. Hãy xem ghi nhận và nghe cả hai phía trước nhé.') if i and i['employee']==e['id'] else 'Chưa có sự cố mở gắn với mình. Mình sẽ kiểm và báo khi có vấn đề.'
            elif any(x in norm for x in ('luong','thuong','tien')):reply=f"Lương ca thực làm của mình là {e['wage']} xu. Việc trả lương cần xác nhận trong Sổ thu chi, lời chat chưa thay đổi số dư."
            else:reply='Mình đang phụ '+role_name(career,e['role']).lower()+'. Bạn có thể hỏi mình đã làm gì, mức mệt hoặc đổi phân công ở hồ sơ.'
            history=o['staff_chats'].setdefault(e['id'],[]);history.extend([dict(role='user',text=text),dict(role='staff',text=reply)])
            o['staff_chats'][e['id']]=ar.last(history,24,'staff.chat:'+e['id'],c);result.update(message=reply,reply=reply)
        if name!='staff_talk':eng.log(s,c,'staff',result['message'],ref=e['id'])
    elif name=='pay_bill':
        b=next((b for b in f['bills'] if b['id']==p.get('bill')),None);need(b,'Không tìm thấy khoản cần trả.');need(b['status']=='unpaid','Khoản này đã được thanh toán rồi.')
        eng.money(s,c,-b['amount'],b['label'],b['id'],category=b['kind']);b['status']='paid';b['paid_day']=c['day'];result['message']='Đã thanh toán '+b['label']+'. Biên nhận chỉ ghi một lần.'
    elif name=='pay_all':
        # "Thanh toán tất cả" (owner, 02/10): every unpaid bill in one tap, overdue first; one that the till cannot
        # cover is skipped (never debt), the rest are still paid. Same receipts as paying each one.
        due=sorted((b for b in f['bills'] if b['status']=='unpaid'),key=lambda b:(b['due'],b['id']))
        need(due,'Không còn khoản nào cần trả.')
        paid=[]
        for b in due:
            if c['money']<b['amount']:continue
            eng.money(s,c,-b['amount'],b['label'],b['id'],category=b['kind']);b['status']='paid';b['paid_day']=c['day'];paid.append(b)
        need(paid,'Chưa đủ xu cho khoản nào. Hoàn thành thêm việc rồi trả nhé.','not_enough')
        left=len(due)-len(paid)
        result['message']=f"Đã thanh toán {len(paid)} khoản, tổng {sum(b['amount'] for b in paid)} xu."+(f' Còn {left} khoản chưa đủ xu.' if left else '')
    elif name=='extend_bill':
        b=next((b for b in f['bills'] if b['id']==p.get('bill')),None);need(b and b['status']=='unpaid','Khoản này không cần gia hạn.');need(not b['extended'],'Mỗi khoản chỉ được gia hạn một lần.')
        b['due']=max(b['due'],c['day'])+3;b['extended']=True;eng.log(s,c,'bill','Gia hạn '+b['label']+' tới ngày '+str(b['due']),ref=b['id'])
        result['message']='Đã gia hạn thêm ba ngày. Không tính thêm lãi hay phạt.'
    elif name=='grant':
        need(not f['grant_used'],'Đã nhận gói hỗ trợ khởi đầu của nghề này.');need(c['money']<60,'Gói hỗ trợ dành lúc số dư dưới 60 xu.')
        f['grant_used']=True;eng.money(s,c,80,'Gói hỗ trợ khởi đầu của khu phố',category='grant');result['message']='Nhận 80 xu hỗ trợ một lần. Không tính vào doanh thu chịu thuế.'
    elif name=='move_property':
        target=PROPERTY_INDEX.get(p.get('tier'));need(target,'Mặt bằng không tồn tại.');need(target['id']!=o['property']['tier'],'Bạn đang ở mặt bằng này.');need(not c['open'],'Khép ca trước khi chuyển mặt bằng.')
        need(sum(e['status']=='hired' for e in o['staff'])<=target['staff_cap'],'Cần sắp xếp lại số nhân viên trước khi chuyển về chỗ nhỏ hơn.')
        # Do not lose goods: returning to a smaller room cannot strand over-capacity stock/orders.
        reserved_incoming={}
        for sh in c['shipments']:
            if sh['status']=='in_transit':reserved_incoming[sh['item']]=reserved_incoming.get(sh['item'],0)+sh['qty']
        limit=max(target['stock_cap'],24 if 'shelf' in c['upgrades'] else 12)
        need(all(q+reserved_incoming.get(item,0)<=limit for item,q in c['stock'].items()),'Kho và hàng đang về vượt sức chứa chỗ mới. Hãy xử lý hàng trước.')
        eng.money(s,c,-target['setup'],'Chuyển sang '+target['name'],target['id'],category='property_setup')
        o['property'].update(tier=target['id'],changed_day=c['day']);result['message']='Đã chuyển sang '+target['name']+'. Tiền thuê mới chỉ tính từ ca tiếp theo.'
    elif name=='buy_security':
        item=SECURITY_INDEX.get(p.get('item'));need(item,'Thiết bị không tồn tại.');need(item['id'] not in sec['items'],'Đã lắp thiết bị này.')
        eng.money(s,c,-item['price'],'Lắp '+item['name'],item['id'],category='security');sec['items'].append(item['id']);result['message']=item['name']+' đã xuất hiện trong cảnh. Chỉ có dữ kiện mới cho vụ phát sinh sau khi lắp.'
    elif name=='insurance_toggle':
        need(type(p.get('enabled')) is bool,'Trạng thái không hợp lệ.');need(sec['insurance']!=p['enabled'],'Thiết lập đã ở trạng thái này.')
        sec['insurance']=p['enabled'];result['message']='Đã '+('bật bảo vệ tài sản: 2 xu mỗi ca đóng; chỉ bảo vệ sự kiện phát sinh sau khi bật.' if sec['insurance'] else 'tắt bảo vệ tài sản cho sự kiện về sau. Quyền ở vụ cũ giữ theo lúc xảy ra.')
    elif name=='case_demo':
        case=spawn_case(s,c,career,p.get('kind'),True);result['message']='Diễn tập: '+case['title']+'. Không mất hàng, không được xu hoặc thưởng.'
    elif name in ('case_read','case_conclude','report','recover','reward','insurance_claim','case_close'):
        case=_case(c,p);need(case['status']!='closed','Hồ sơ này đã đóng.')
        if name=='case_read':
            ev=next((x for x in case['evidence'] if x['id']==p.get('evidence')),None);need(ev,'Nguồn không tồn tại.')
            if ev['id'] not in case['read']:case['read'].append(ev['id'])
            if case['status']=='noticed':case['status']='investigating'
            result['message']=ev['text']
        elif name=='case_conclude':
            need(case['status'] in ('noticed','investigating'),'Hồ sơ đã được gửi hoặc có kết quả.');need(len(case['read'])>=2,'Đọc ít nhất hai nguồn trước khi kết luận.');need(p.get('finding') in ('misplaced','forgot_payment','theft'),'Kết luận không hợp lệ.')
            need(p['finding']==case['_truth'],'Nguồn đang không khớp kết luận này. Kiểm lại kho và lời người có mặt; chưa có cáo buộc hay khoản trừ nào được tạo từ câu trả lời.')
            case['finding']=p['finding']
            if case['finding']!='theft':case['status']='result';case['outcome']='not_theft';case['timeline'].append('Đã đối chiếu: '+('để nhầm vị trí.' if case['finding']=='misplaced' else 'quên thanh toán, đã trả lại gói chưa mua.'))
            result['message']='Đã ghi kết luận từ nguồn. '+('Có thể gửi báo tin cho công an khu phố.' if case['finding']=='theft' else 'Không có tiền thưởng vì đây không phải vụ bắt trộm.')
        elif name=='report':
            need(case['status'] in ('noticed','investigating'),'Báo tin đã gửi hoặc hồ sơ đã có kết quả.');need(len(case['read'])>=2 and case['finding']=='theft','Cần kiểm chứng và ghi kết luận trước khi báo tin.')
            case['reported']=True;case['status']='reported';case['ready_turn']=c['turn']+3
            case['timeline'].append('Công an khu phố đã nhận thông tin. Hẹn cập nhật sau ba nhịp làm việc.')
            result['message']='Đã gửi báo tin. Chọn “Chờ một nhịp” hoặc làm việc khác; chưa nhận tiền hay tài sản.'
        elif name=='recover':
            need(case['status']=='result' and case['outcome']=='arrested','Chưa có biên bản thu hồi.');need(not case['recovered'],'Tài sản đã nhận lại rồi.')
            loss=case['loss']
            if not case['practice']:
                if loss['kind']=='stock':c['stock'][loss['item']]+=loss['qty']
                elif loss['kind']=='cash' and loss['cash']:eng.money(s,c,loss['cash'],'Nhận lại tài sản từ hồ sơ '+case['id'],case['id'],category='recovery')
            case['recovered']=True;case['recovered_value']=loss['value'];case['timeline'].append('Đã nhận tài sản của tiệm hoặc bàn giao túi cho khách đúng biên bản.')
            result['message']='Đã xác nhận thu hồi. Tài sản trả lại không phải doanh thu bán hàng.'+(' Diễn tập không cộng tài sản.' if case['practice'] else '')
        elif name=='reward':
            need(case['outcome']=='arrested' and case['recovered'] and case['reported'],'Chỉ nhận thưởng sau kết quả bắt trộm và bàn giao tài sản.');need(not case['reward_claimed'],'Đã nhận phần thưởng của hồ sơ này.')
            amount=0 if case['practice'] else min(RULES['security_reward'],max(0,RULES['reward_cap_period']-sec['period_rewards']))
            if amount:eng.money(s,c,amount,'Quỹ khu phố thưởng hỗ trợ',case['id'],category='security_reward')
            sec['period_rewards']+=amount;case['reward']=amount;case['reward_claimed']=True
            result['message']=f'Quỹ khu phố đã ghi {amount} xu thưởng.'
        elif name=='insurance_claim':
            need(case['status']=='result' and case['outcome']=='unrecovered','Hỗ trợ chỉ áp dụng khi hồ sơ kết luận chưa thu hồi được tài sản.');need(case['insured_at_event'],'Gói bảo vệ phải được bật trước khi sự việc xảy ra.');need(not case['insurance_claimed'],'Hồ sơ đã nhận hỗ trợ.');need(case['loss']['kind'] in ('cash','stock'),'Đây không phải thiệt hại của tiệm.')
            residual=max(0,case['loss']['value']-case['recovered_value']);amount=0 if case['practice'] else residual*RULES['insurance_percent']//100
            if amount:eng.money(s,c,amount,'Hỗ trợ tài sản',case['id'],category='insurance_recovery')
            case['insurance_claimed']=True;case['recovered_value']+=amount;sec['period_claims']+=amount
            result['message']=f'Đã nhận {amount} xu hỗ trợ phần thiệt hại còn lại. Không được bồi hoàn hai lần.'
        else:
            if not case['practice']:
                need(case['status']=='result','Chưa có kết quả để đóng.');need(case['outcome']!='arrested' or case['recovered'],'Nhận / bàn giao tài sản trước khi đóng.');need(case['outcome']!='arrested' or case['reward_claimed'],'Xác nhận phần thưởng trước khi đóng hồ sơ.')
                need(case['outcome']!='unrecovered' or not case['insured_at_event'] or case['loss']['kind'] not in ('cash','stock') or case['insurance_claimed'],'Còn phần hỗ trợ tài sản đủ điều kiện; nhận trước khi đóng nhé.')
            case['status']='closed';sec['active']=None
            result['message']='Đã cất hồ sơ. '+('Diễn tập không ảnh hưởng tài sản.' if case['practice'] else 'Nhật ký và biên nhận vẫn được giữ lại.')
        eng.log(s,c,'security_practice' if case['practice'] else 'security',result['message'],ref=case['id'])
    elif name=='incident_demo':
        i=spawn_incident(s,c,career,p.get('kind'),True);result['message']='Diễn tập: '+i['title']+'. Không trừ xu, không làm giảm chỉ số nhân viên.'
    elif name in ('incident_read','incident_choose','incident_finish','incident_dismiss'):
        i=o['incident'];need(i,'Không có sự cố đang mở.')
        if name=='incident_read':
            ev=next((e for e in i['evidence'] if e['id']==p.get('evidence')),None);need(ev,'Nguồn không tồn tại.')
            if ev['id'] not in i['read']:i['read'].append(ev['id'])
            result['message']=ev['text']
        elif name=='incident_choose':
            need(i['status']=='noticed','Đã chọn cách xử lý; không trừ chi phí lặp.');need(len(i['read'])==2,'Xem nhật ký và nghe người liên quan trước.');choice=p.get('choice');need(choice in ('coach','repair','reassign','warning'),'Cách xử lý không hợp lệ.')
            cost={'coach':8,'repair':16,'reassign':10,'warning':12}[choice]
            i['choice']=choice;i['status']='repairing';i['ready_turn']=c['turn']+2
            if not i['practice']:bill(c,'repair-'+i['id'],'repair','Sửa dụng cụ · '+i['title'],cost,c['day']+2,i['id'])
            i['timeline'].append('Đã lên việc sửa và '+{'coach':'hướng dẫn lại','repair':'kiểm thiết bị','reassign':'đổi vị trí làm','warning':'nhắc ranh giới, tạm dừng công việc'}[choice]+'. Chưa coi là đã sửa xong.')
            result['message']=f'Đã đặt việc sửa ({0 if i["practice"] else cost} xu, trả trong Sổ thu chi). Sau hai nhịp hãy kiểm kết quả.'
        elif name=='incident_finish':
            need(i['status']=='ready','Chưa có kết quả sửa để kiểm.')
            i['status']='resolved'
            if not i['practice']:
                o['equipment']['condition']=100
                e=next((e for e in o['staff'] if e['id']==i['employee']),None)
                if e:
                    e['morale']=min(100,e['morale']+5);e['fatigue']=max(0,e['fatigue']-15)
                    if i['choice']=='coach':e['precision']=min(99,e['precision']+4)
                    if i['choice']=='reassign':e['role']='patrol';e['progress']=0
                    if i['choice']=='warning':e['warnings']=min(3,e['warnings']+1);e['on_shift']=False
                o['incident_history'].insert(0,copy.deepcopy(i));o['incident_history']=ar.first(o['incident_history'], 60, 'staff.incidents', c);eng.metric(c,'staff_incidents_resolved')
            result['message']='Đã kiểm dụng cụ và khép sự cố. Không khấu trừ lương nhân viên.'
        else:
            need(i['practice'] or i['status']=='resolved','Sự cố thật cần kiểm kết quả trước khi cất.');o['incident']=None;result['message']='Đã cất tình huống nhân viên.'
        eng.log(s,c,'staff_practice' if i['practice'] else 'staff_incident',result['message'],ref=i['id'])
    else:raise eng.GameError('Thao tác Sổ tiệm chưa được hỗ trợ.','unknown_action')
    return result


def public_operations(c:dict) -> dict:
    # Called on public_state's private save: what is only read is shared, what is written below is copied.
    raw=c['ops'];o=dict(raw)
    f=o['finance']=dict(raw['finance']);sec=o['security']=dict(raw['security']);sec['cases']=tree_copy(sec['cases'])
    o['property']=dict(raw['property']);o['incident']=tree_copy(raw['incident'])
    active=next((x for x in sec['cases'] if x['id']==sec['active']),None)
    for case in sec['cases']:
        case.pop('_truth',None);case.pop('_roll',None)
        for ev in case['evidence']:
            if ev['id'] not in case['read']:ev['text']=None
    if o['incident']:
        for e in o['incident']['evidence']:
            if e['id'] not in o['incident']['read']:e['text']=None
    due=[b for b in f['bills'] if b['status']=='unpaid']
    f['unpaid_total']=sum(b['amount'] for b in due);f['due_total']=sum(b['amount'] for b in due if b['due']<=c['day'])
    f['estimate_tax']=math.ceil(f['period_revenue']*RULES['tax_percent']/100)
    f['wallet_check']=f['opening_balance']+sum(x['amount'] for x in f['ledger'])==c['money']
    f['current_wages']=sum(x['wage'] for x in o['attendance'].get(str(c['day']),{}).values())
    f['days_to_period']=RULES['period_days']-f['period_days']
    o['property']['details']=PROPERTY_INDEX[o['property']['tier']]
    o['security']['protection']=sum(SECURITY_INDEX[i]['protection'] for i in sec['items'])
    o['security']['current_case']=active
    o['alerts']=[]
    if f['due_total']:o['alerts'].append(dict(kind='finance',text=f"Có {f['due_total']} xu đến hạn",tab='finance'))
    if o['incident'] and o['incident']['status']!='resolved':o['alerts'].append(dict(kind='staff',text=o['incident']['title'],tab='staff'))
    if active and active['status']!='closed':o['alerts'].append(dict(kind='security',text=active['title'],tab='security'))
    return o


def content() -> dict:
    return dict(rules=RULES,candidates=CANDIDATES,roles=ROLES,role_names=ROLE_NAMES,career_role_names=CAREER_ROLE_NAMES,properties=PROPERTIES,
                security_items=SECURITY_ITEMS,case_kinds=[dict(id=k,title=v[0],description=v[1]) for k,v in CASE_KINDS.items()],
                incident_kinds=[dict(id=k,title=v[0],description=v[1]) for k,v in INCIDENT_KINDS.items()])


def validate(c:dict,career:str) -> None:
    """Validate imported operations data before it can reach a reducer.

    Saves are user-owned single-player backups, not competitive certificates.
    Nonetheless reject corrupt types, cross-career IDs and impossible payouts.
    """
    eng=_core();need=eng.need;integer=eng.integer;txt=eng.clean_text
    o=c.get('ops');need(isinstance(o,dict) and o.get('version')==1,'Thiếu hoặc sai phiên bản Sổ tiệm.')
    template=initial_operations(career);need(set(template)<=set(o),'Bản lưu thiếu dữ liệu Sổ tiệm.')
    for k in ('seq','rng','day_staff_incident','work_ticks'):integer(o.get(k),0,2**40)
    need(isinstance(o['property'],dict) and o['property'].get('tier') in PROPERTY_INDEX,'Mặt bằng không hợp lệ.');integer(o['property'].get('changed_day'),0,10**9)
    need(isinstance(o['staff'],list) and len(o['staff'])<=4,'Danh sách nhân viên không hợp lệ.')
    ids=[]
    for e in o['staff']:
        need(isinstance(e,dict) and e.get('id') in CANDIDATE_INDEX and CANDIDATE_INDEX[e['id']]['career']==career,'Nhân viên sai nghề.')
        base=CANDIDATE_INDEX[e['id']];need(set(base)<=set(e),'Hồ sơ nhân viên thiếu trường.');ids.append(e['id'])
        for k in ('name','career','bio','hire_cost','wage','avatar','color','speed','friendliness','learning'):need(e.get(k)==base[k],'Dữ kiện gốc của nhân viên bị thay đổi: '+k)
        need(e.get('role') in ROLES[career] and e.get('schedule') in ('daily','odd','even','manual') and e.get('status') in ('hired','former'),'Phân công nhân viên không hợp lệ.')
        need(type(e.get('on_shift')) is bool,'Thiếu trạng thái ca.')
        for k in ('precision','morale','fatigue'):integer(e.get(k),0,100)
        for k in ('progress','jobs','errors','training','trained_day','bonus_day','rest_until','warnings','hired_day'):integer(e.get(k),0,10**9)
        txt(e.get('last_work'),2000)
    need(len(ids)==len(set(ids)),'Nhân viên trùng hồ sơ.');need(sum(x['status']=='hired' for x in o['staff'])<=PROPERTY_INDEX[o['property']['tier']]['staff_cap'],'Nhân viên vượt chỗ của mặt bằng.')
    need(isinstance(o['attendance'],dict) and len(o['attendance'])<=30,'Bảng ca không hợp lệ.')
    for day,rows in o['attendance'].items():
        need(isinstance(day,str) and day.isdigit() and isinstance(rows,dict),'Bảng ca sai cấu trúc.')
        for sid,row in rows.items():
            need(sid in CANDIDATE_INDEX and CANDIDATE_INDEX[sid]['career']==career,'Ca sai nhân viên.');need(isinstance(row,dict) and row.get('wage')==CANDIDATE_INDEX[sid]['wage'] and row.get('name')==CANDIDATE_INDEX[sid]['name'] and row.get('role') in ROLES[career],'Dữ kiện ca sai.')
            if 'jobs' in row:integer(row['jobs'],0,10**6)  # 1.4.31+: jobs done that day; absent in older saves
    need(isinstance(o['equipment'],dict),'Thiếu trạng thái dụng cụ.');integer(o['equipment'].get('condition'),0,100);txt(o['equipment'].get('label'),100)
    f=o['finance'];need(isinstance(f,dict) and set(template['finance'])<=set(f),'Sổ thu chi thiếu trường.')
    integer(f['opening_balance'],-10**12,10**12)
    for k in ('period_start','period_days','period_revenue','period_rent','period_tax_adjustments','last_closed'):integer(f[k],0,10**12)
    need(f['period_days']<RULES['period_days'] and type(f['grant_used']) is bool,'Kỳ thu chi không hợp lệ.')
    need(isinstance(f['ledger'],list) and len(f['ledger'])<=2000,'Sổ giao dịch quá lớn.');lids=[]
    for row in f['ledger']:
        need(isinstance(row,dict),'Dòng giao dịch sai.');txt(row.get('id'),100);lids.append(row['id']);integer(row.get('amount'),-10**9,10**9);integer(row.get('day'),1,10**9);integer(row.get('turn'),0,10**9);txt(row.get('reason'),1000);txt(row.get('category'),60)
        need(row.get('ref') is None or isinstance(row['ref'],str),'Nguồn giao dịch sai.')
    need(len(lids)==len(set(lids)),'Giao dịch bị trùng.');need(f['opening_balance']+sum(x['amount'] for x in f['ledger'])==c['money'],'Ví và Sổ thu chi không khớp.')
    need(isinstance(f['bills'],list) and len(f['bills'])<=1500,'Sổ khoản phải trả quá lớn.');bids=[]
    for b in f['bills']:
        need(isinstance(b,dict),'Khoản phải trả sai cấu trúc.');txt(b.get('id'),160);bids.append(b['id'])
        need(b.get('kind') in ('wage','utility','insurance','rent','tax','repair'),'Loại chi phí sai.');txt(b.get('label'),300);txt(b.get('source'),160)
        for k in ('amount','due','created_day'):integer(b.get(k),1,10**9)
        need(b.get('status') in ('paid','unpaid') and type(b.get('extended')) is bool,'Trạng thái khoản phải trả sai.')
        if b['status']=='paid':integer(b.get('paid_day'),1,10**9)
        else:need(b.get('paid_day') is None,'Khoản chưa trả không có ngày trả.')
    need(len(bids)==len(set(bids)),'Khoản phải trả trùng mã.')
    need(isinstance(f['history'],list) and len(f['history'])<=60,'Lịch sử kỳ sai.')
    for h in f['history']:
        need(isinstance(h,dict),'Lịch sử kỳ sai.');txt(h.get('id'),100)
        for k in ('start','end','revenue','tax','rent','rate'):integer(h.get(k),0,10**12)
        need(h['rate']==RULES['tax_percent'] and h['tax']==math.ceil(h['revenue']*h['rate']/100),'Công thức thuế trong bản lưu không đúng.')
    sec=o['security'];need(isinstance(sec,dict) and set(template['security'])<=set(sec),'Sổ an ninh thiếu trường.')
    need(isinstance(sec['items'],list) and all(i in SECURITY_INDEX for i in sec['items']) and len(set(sec['items']))==len(sec['items']),'Thiết bị an ninh sai.')
    need(type(sec['insurance']) is bool,'Trạng thái bảo vệ sai.')
    for k in ('last_event_day','period_rewards','period_claims'):integer(sec[k],0,10**9)
    need(sec['period_rewards']<=RULES['reward_cap_period'],'Thưởng vượt giới hạn kỳ.')
    need(isinstance(sec['cases'],list) and len(sec['cases'])<=120,'Hồ sơ an ninh quá lớn.');caseids=[]
    for case in sec['cases']:
        need(isinstance(case,dict),'Hồ sơ sai.');txt(case.get('id'),100);caseids.append(case['id'])
        need(case.get('kind') in CASE_KINDS and case.get('_truth') in ('misplaced','forgot_payment','theft'),'Thiếu dữ kiện gốc của hồ sơ.')
        expected='misplaced' if case['kind']=='misplaced' else 'forgot_payment' if case['kind']=='unpaid' else 'theft';need(case['_truth']==expected,'Dữ kiện gốc không khớp loại vụ.')
        for k in ('title','opening'):txt(case.get(k),2000)
        for k in ('practice','reported','recovered','reward_claimed','insurance_claimed','insured_at_event'):need(type(case.get(k)) is bool,'Hồ sơ thiếu trạng thái '+k)
        for k in ('day','ready_turn','recovered_value','reward','protection','_roll'):integer(case.get(k),0,10**9)
        need(case['reward']<=RULES['security_reward'] and (not case['practice'] or case['reward']==0),'Thưởng không hợp lệ.')
        need(case.get('status') in ('noticed','investigating','reported','result','closed'),'Bước hồ sơ sai.')
        need(case.get('finding') in (None,'misplaced','forgot_payment','theft') and case.get('outcome') in (None,'not_theft','arrested','unrecovered'),'Kết luận hồ sơ sai.')
        need(isinstance(case.get('read'),list) and isinstance(case.get('evidence'),list) and 2<=len(case['evidence'])<=3,'Chứng cứ hồ sơ sai.')
        for ev in case['evidence']:
            need(isinstance(ev,dict) and ev.get('id') in ('inventory','witness','camera'),'Mã chứng cứ sai.');txt(ev.get('title'),200);txt(ev.get('text'),2000)
        need(all(x in [e['id'] for e in case['evidence']] for x in case['read']) and len(set(case['read']))==len(case['read']),'Nguồn đã đọc sai.')
        loss=case.get('loss');need(isinstance(loss,dict) and loss.get('kind') in ('none','stock','cash','npc_property'),'Tài sản thiệt hại sai.')
        for k in ('qty','value','cash'):integer(loss.get(k),0,10**9)
        need(loss['qty']<=1 and loss['cash']<=18,'Thiệt hại vượt trần.')
        if loss['kind']=='stock':need(loss.get('item') in c['stock'],'Mã hàng mất không tồn tại.')
        else:need(loss.get('item') is None,'Tài sản không phải hàng không được có mã kho.')
        need(case['recovered_value']<=loss['value'],'Đã hoàn nhiều hơn tài sản mất.')
        need(not case['reward_claimed'] or (case['outcome']=='arrested' and case['recovered'] and case['reported']),'Thưởng khi chưa đủ điều kiện.')
        need(not case['insurance_claimed'] or (case['outcome']=='unrecovered' and case['insured_at_event'] and loss['kind'] in ('stock','cash')),'Hỗ trợ sai điều kiện.')
        need(isinstance(case.get('timeline'),list) and len(case['timeline'])<=30,'Nhật ký an ninh sai.')
        for line in case['timeline']:txt(line,2000)
    need(len(caseids)==len(set(caseids)) and (sec['active'] is None or sec['active'] in caseids),'Tham chiếu hồ sơ an ninh sai.')
    need(isinstance(o['incident_history'],list) and len(o['incident_history'])<=60,'Lịch sử sự cố sai.')
    for i in ([o['incident']] if o['incident'] else [])+o['incident_history']:
        need(isinstance(i,dict) and i.get('kind') in INCIDENT_KINDS and i.get('status') in ('noticed','repairing','ready','resolved'),'Sự cố nhân viên sai.')
        for k in ('id','title','opening','employee_name'):txt(i.get(k),2000)
        need(type(i.get('practice')) is bool and (i.get('employee') is None or i['employee'] in ids),'Sự cố sai nhân viên.')
        for k in ('day','ready_turn'):integer(i.get(k),0,10**9)
        need(i.get('choice') in (None,'coach','repair','reassign','warning'),'Cách xử lý sự cố sai.')
        need(isinstance(i.get('read'),list) and all(x in ('worklog','listen') for x in i['read']) and len(set(i['read']))==len(i['read']),'Nguồn sự cố sai.')
        need(isinstance(i.get('evidence'),list) and len(i['evidence'])==2,'Sự cố thiếu nguồn.')
        for ev in i['evidence']:need(ev.get('id') in ('worklog','listen'),'Mã nguồn sai.');txt(ev.get('title'),200);txt(ev.get('text'),2000)
        need(isinstance(i.get('timeline'),list),'Thiếu nhật ký sự cố.')
        for line in i['timeline']:txt(line,2000)
    need(isinstance(o['staff_chats'],dict),'Hội thoại nhân viên sai.')
    for sid,rows in o['staff_chats'].items():
        need(sid in ids and isinstance(rows,list) and len(rows)<=24,'Hội thoại sai nhân viên.')
        for row in rows:need(row.get('role') in ('user','staff'),'Vai hội thoại sai.');txt(row.get('text'),2000)
