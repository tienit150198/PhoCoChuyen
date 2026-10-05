"""Personal salon/nail visits and DIY souvenirs. Optional, paid only on explicit purchase.

Integration: journey routes jr_out_* here, publishes public/content, and validates the
optional journey.outings block. No workplace is opened and no daily bill is created.
"""
from __future__ import annotations
import copy
from . import bank, wardrobe, community_outings, craft_work

SALON_FEE, NAIL_FEE, CRAFT_FEE = 12, 18, 22
MAX_CRAFTS = 24
COLORS = [dict(id='rose',name='Hồng cánh hoa',hex='#de829d'),dict(id='mint',name='Xanh bạc hà',hex='#74bba0'),
          dict(id='lavender',name='Tím oải hương',hex='#a795cf'),dict(id='sun',name='Vàng nắng',hex='#e6b950'),
          dict(id='sky',name='Xanh trời',hex='#79abd4'),dict(id='cream',name='Kem sữa',hex='#eedcc4')]
PATTERNS = [dict(id='plain',name='Trơn',emoji='○'),dict(id='flower',name='Hoa nhỏ',emoji='✿'),
            dict(id='stars',name='Ngôi sao',emoji='✦'),dict(id='waves',name='Lượn sóng',emoji='≈')]
CRAFTS = [dict(id='teddy',name='Gấu bông tự may',emoji='🧸'),dict(id='pot',name='Chậu gốm nhỏ',emoji='🪴'),dict(id='bracelet',name='Vòng tay hạt',emoji='📿'),
          dict(id='card',name='Thiệp thủ công',emoji='💌')]
COLOR_IDS = frozenset(x['id'] for x in COLORS)
PATTERN_IDS = frozenset(x['id'] for x in PATTERNS)
CRAFT_IDS = frozenset(x['id'] for x in CRAFTS)


def _need(ok, message='Thông tin buổi đi chơi không hợp lệ.'):
    from .engine import need
    need(ok, message)


def _fresh():
    return dict(v=1, seq=0, salon=None, nails=None, crafts=[])


def _choice(value, choices):
    _need(isinstance(value,str) and value in choices)
    return value


def _hair(s):
    owned=(s.get('wardrobe') or {}).get('owned',[])
    return [dict(id=x['id'],name=x['name'],owned=not x['price'] or x['id'] in owned,
                 price=SALON_FEE+(wardrobe.price(s,x['id']) if x['price'] and x['id'] not in owned else 0))
            for x in wardrobe.ITEMS if x['slot']=='hair' and not x['need']]


def action(s: dict, name: str, p: dict) -> dict:
    j=s['journey']
    _need(j.get('story'), 'Vào hành trình để đi chơi bằng ví cá nhân.')
    _need(isinstance(p,dict))
    if name=='jr_out_community':return community_outings.action(s,p)
    allowed={'jr_out_salon':{'hair','pay'},'jr_out_nails':{'color','pattern','pay'},
             'jr_out_craft':{'kind','color','pattern','pay','work'}}
    _need(name in allowed and set(p)<=allowed[name])
    method=p.get('pay','auto')
    _choice(method,('auto','cash','account','card','joint'))
    old=j.get('outings') or _fresh()
    day=j['life_day']
    if name=='jr_out_salon':
        hair=_choice(p.get('hair'),{x['id'] for x in _hair(s)})
        offer=next(x for x in _hair(s) if x['id']==hair)
        if old['salon'] and old['salon']['hair']==hair and wardrobe.look_of(s)['hair']==hair:
            return dict(message='Bạn đang giữ kiểu tóc này rồi.',duplicate=True)
        # Preflight the whole displayed quote, then reuse wardrobe ownership/equip rules.
        _need(bank.can_pay(s,offer['price'],method),'Nguồn thanh toán đã chọn chưa đủ cho cả kiểu tóc và phí dịch vụ.')
        if not offer['owned']:
            wardrobe.action(s,'jr_wd_buy',dict(item=hair,wear=True,pay=method))
        else:
            wardrobe.action(s,'jr_wd_wear',dict(look={'hair':hair}))
        bank.pay(s,SALON_FEE,'Ghé salon · '+offer['name'],method=method,kind='life')
        d=j.setdefault('outings',_fresh())
        d['salon']=dict(hair=hair,day=day,cost=offer['price'])
        return dict(message='Đã làm tóc xong. Kiểu tóc mới theo bạn về nhà và ra phố!',celebrate=True)
    color=_choice(p.get('color'),COLOR_IDS)
    pattern=_choice(p.get('pattern'),PATTERN_IDS)
    if name=='jr_out_nails':
        if old['nails'] and all(old['nails'][k]==v for k,v in [('color',color),('pattern',pattern)]):
            return dict(message='Bạn đang giữ bộ móng này rồi.',duplicate=True)
        bank.pay(s,NAIL_FEE,'Ghé tiệm nail · sơn và vẽ móng',method=method,kind='life')
        d=j.setdefault('outings',_fresh())
        d['nails']=dict(color=color,pattern=pattern,day=day,cost=NAIL_FEE)
        return dict(message='Bộ móng mới đã lưu trong góc đi chơi của bạn.',celebrate=True)
    kind=_choice(p.get('kind'),CRAFT_IDS)
    work=p.get('work')
    craft_work.validate(kind,work)
    design=craft_work.identity(kind,color,pattern,work)
    if any(craft_work.identity(x['kind'],x['color'],x['pattern'],x.get('work'))==design for x in old['crafts']):
        return dict(message='Mẫu thủ công này đã có trên kệ kỷ niệm của bạn.',duplicate=True)
    _need(len(old['crafts'])<MAX_CRAFTS,'Kệ đã đủ 24 món. Những món đã làm vẫn được giữ ở đây.')
    bank.pay(s,CRAFT_FEE,'Xưởng DIY · '+next(x['name'] for x in CRAFTS if x['id']==kind),method=method,kind='life')
    d=j.setdefault('outings',_fresh());d['seq']+=1
    item=dict(id=d['seq'],kind=kind,color=color,pattern=pattern,day=day,cost=CRAFT_FEE)
    if work is not None:item['work']=copy.deepcopy(work)
    d['crafts'].append(item)
    return dict(message='Đã làm xong và cất món thủ công lên kệ kỷ niệm!',celebrate=True)


def public(s: dict) -> dict:
    out=copy.deepcopy(s['journey'].get('outings') or _fresh())
    out['hairstyles']=_hair(s)
    out['community']=community_outings.public(s)
    return out


def content() -> dict:
    return copy.deepcopy(dict(colors=COLORS,patterns=PATTERNS,crafts=CRAFTS,salon_fee=SALON_FEE,
                              nail_fee=NAIL_FEE,craft_fee=CRAFT_FEE,max_crafts=MAX_CRAFTS,workshop=craft_work.RECIPES,community=community_outings.PLACES))


def validate(s: dict) -> None:
    community_outings.validate(s)
    if 'outings' not in s['journey']:return
    d=s['journey']['outings'];msg='Kỷ niệm đi chơi không hợp lệ.'
    _need(isinstance(d,dict) and set(d)=={'v','seq','salon','nails','crafts'},msg)
    _need(type(d['v']) is int and d['v']==1 and type(d['seq']) is int and 0<=d['seq']<=MAX_CRAFTS,msg)
    def record(x,keys):
        _need(isinstance(x,dict) and set(x)==keys,msg)
        _need(type(x['day']) is int and 1<=x['day']<=s['journey']['life_day'],msg)
        _need(type(x['cost']) is int and 0<x['cost']<=10000,msg)
    if d['salon'] is not None:
        record(d['salon'],{'hair','day','cost'})
        _choice(d['salon']['hair'],{x['id'] for x in wardrobe.ITEMS if x['slot']=='hair'})
    if d['nails'] is not None:
        record(d['nails'],{'color','pattern','day','cost'})
        _choice(d['nails']['color'],COLOR_IDS);_choice(d['nails']['pattern'],PATTERN_IDS)
        _need(d['nails']['cost']==NAIL_FEE,msg)
    _need(isinstance(d['crafts'],list) and len(d['crafts'])==d['seq'],msg)
    combos=set()
    for index,x in enumerate(d['crafts'],1):
        record(x,{'id','kind','color','pattern','day','cost'}|({'work'} if isinstance(x,dict) and 'work' in x else set()))
        _need(type(x['id']) is int and x['id']==index and x['cost']==CRAFT_FEE,msg)
        _choice(x['kind'],CRAFT_IDS);_choice(x['color'],COLOR_IDS);_choice(x['pattern'],PATTERN_IDS)
        craft_work.validate(x['kind'],x.get('work'))
        combo=craft_work.identity(x['kind'],x['color'],x['pattern'],x.get('work'));_need(combo not in combos,msg);combos.add(combo)
