"""v0.3 experience rules: 3 new jobs, prep, puzzles, stories, collections.
Server authoritative, offline, atomic through the existing reducer/storage.
All places, budgets and lessons are fictional. No wall-clock expiry or penalties.
"""
from __future__ import annotations
import copy
import random
from . import extra_content as data
from . import teach_lesson, tour_trip
from .careers import PLUGINS
from .jsoncopy import tree_copy
from . import archive as ar

GOALS_KEPT=10  # day recaps kept in the save (nothing reads older ones; the rest is archived)

NEW_ACTION_PREFIXES=('life_','lesson_','tour_','tea_','gift_')
DONE=('completed','referred','cancelled')

def core():
 from . import engine
 return engine

def initial(career:str)->dict:
 pantry=[];mod=PLUGINS.get(career)
 if career=='milk_tea':
  pantry=[dict(id='opening-'+x['id'],item=x['id'],qty=8,unit_cost=0,expires=x['life'],received=1) for x in data.INGREDIENTS if x.get('level',1)==1]
 return dict(version=1,seq=0,shop_name=data.META.get(career,{}).get('place',''),mode='normal',day_metrics={},goals_claimed=[],
  pantry=pantry,prices=dict(mod.SPEC.get('prices',{})) if mod else {'milk':30,'black':25,'matcha':35} if career=='milk_tea' else {},price_history=[],
  streak=0,best_streak=0,tips=0,staff_tips=0,consumed_cost=0,waste=[],day_waste=0,activity=None,activity_rewards=[],activity_history=[],
  activity_best={},badges=[],stickers=[],chapters={},visits=[],festival=False,festival_claimed=False,goals_history=[],
  day_guests=[],title_style='milk',onboarding=False,served_sources=[],day_talked=[],recap=None,**({'tour':tour_trip.fresh_care()} if career=='tour_guide' else {}))

def _id(c:dict,prefix:str)->str:
 c['life']['seq']+=1
 return f"{prefix}-{c['life']['seq']}"

def _metric(c:dict,key:str,n:int=1):
 core().metric(c,key,n);x=c['life'];x['day_metrics'][key]=x['day_metrics'].get(key,0)+n

def _sticker(c:dict,key:str,title:str,emoji:str):
 if not any(x['id']==key for x in c['life']['stickers']):
  c['life']['stickers'].append(dict(id=key,title=title,emoji=emoji,day=c['day']))

def price(c:dict,item:str,default:int)->int:
 return c['life']['prices'].get(item,default)

def tea_price(c:dict,needs:dict)->int:
 from . import boba
 return boba.price(c,needs)

def setup_task(s:dict,c:dict,t:dict):
 # A fresh milk-tea customer rolls the real order once (level, day modifier, notebook).
 if t['career']=='milk_tea':
  from . import boba
  boba.setup_task(s,c,t)

def on_start(s:dict,c:dict,career:str):
 # Daily counters were reset at close. Resuming the same open day does nothing.
 x=c['life'];x['festival']=x['mode']=='festival';x['onboarding']=True
 for t in c['tasks']:
  if t['career']=='milk_tea' and t.get('quoted_price') is None:setup_task(s,c,t)
 if career=='milk_tea':
  from . import boba
  boba.on_start(s,c)
 if career=='mother_baby':
  from . import giftshop
  giftshop.on_start(s,c)
 if career=='tour_guide':tour_trip.on_start(s,c)  # multi-day group's morning, featured booking, today's leg
 if x['festival']:
  core().log(s,c,'festival','Ngày hội khu phố: hoàn thành 3 việc và 1 trò nhỏ để chuẩn bị góc của nghề mình.')

def after_task(s:dict,c:dict,t:dict):
 x=c['life'];ref=t['id']
 if ref in x['served_sources']:return
 mod=PLUGINS.get(t['career'])
 x['served_sources'].append(ref);x['served_sources']=ar.last(x['served_sources'], 240, 'life.served', c)
 x['day_metrics']['served']=x['day_metrics'].get('served',0)+1
 if t['mistakes']==0:
  _metric(c,'perfect');x['streak']+=1;x['best_streak']=max(x['best_streak'],x['streak'])
 else:x['streak']=0
 # Reward on the third accurate service only once per game day; no menu farming.
 if x['streak']==3 and not x['day_metrics'].get('combo_reward'):
  core().money(s,c,8,'Ba việc liền mạch',f"combo-{c['day']}",category='skill_reward');x['day_metrics']['combo_reward']=1
 tip=(mod.SPEC.get('tip',0) if mod else 2 if t['career'] in ('mother_baby','milk_tea','tour_guide') else 0) if t['mistakes']==0 and not t.get('combo') and (t.get('reaction') or {}).get('kind') not in ('refuse','walkout') else 0
 if tip:
  active=[e for e in c['ops']['staff'] if e['status']=='hired' and e['on_shift'] and e['jobs']>0]
  if active:
   x['staff_tips']+=tip
   core().log(s,c,'staff_tip',f"Khách tặng đội {tip} xu trực tiếp; không đi qua két tiệm.",ref=ref)
  else:
   core().money(s,c,tip,'Tip tự nguyện của khách',ref,category='tip');x['tips']+=tip
 _sticker(c,'first-service','Một việc được làm đến nơi','🌱')
 if t['career']=='mother_baby':
  from . import giftshop
  giftshop.after_task(s,c,t)

def on_close(s:dict,c:dict,career:str)->dict:
 x=c['life'];waste=0;counter=None
 if career=='milk_tea':
  from . import boba
  counter=boba.on_close(s,c)
  for lot in x['pantry']:
   if lot['expires']<=c['day'] and lot['qty']:
    lost=lot['qty'];value=lost*lot['unit_cost'];waste+=value
    x['waste'].append(dict(day=c['day'],item=lot['item'],qty=lost,value=value,reason='Hết hạn sử dụng'));lot['qty']=0
  for t in c['tasks']:
   if t['status'] not in DONE and t['cup']['items']:
    value=t['cup']['cost'];waste+=value
    x['waste'].append(dict(day=c['day'],item='cup',qty=1,value=value,reason='Ly đang làm được bỏ khi khép ca'))
    t['cup']=boba.new_cup();t['stage']='order'
  x['pantry']=ar.last([lot for lot in x['pantry'] if lot['qty']>0], 250, 'life.pantry', c)
 if career=='mother_baby':
  from . import giftshop
  counter=giftshop.on_close(s,c)
 if career=='tour_guide':tour_trip.on_close(s,c)
 x['day_waste']+=waste;x['waste']=ar.last(x['waste'], 120, 'life.waste', c)
 _metric(c,'days_closed')
 recap=dict(day=c['day'],served=x['day_metrics'].get('served',0),perfect=x['day_metrics'].get('perfect',0),activities=x['day_metrics'].get('activities',0),tips=x['tips'],staff_tips=x['staff_tips'],waste_value=x['day_waste'],consumed_cost=x['consumed_cost'],streak=x['best_streak'],goals=goals(c),festival=x['festival'],note='Chi phí hàng đã trả khi nhập; hao hụt chỉ ghi giá trị, không trừ két lần nữa.',counter=counter)
 x['recap']=recap;x['goals_history']=ar.last(x['goals_history']+[recap], GOALS_KEPT, 'life.goals_history', c)
 x['day_metrics']={};x['goals_claimed']=[];x['day_talked']=[];x['activity_rewards']=[]
 x['tips']=0;x['staff_tips']=0;x['consumed_cost']=0;x['day_waste']=0;x['streak']=0;x['festival_claimed']=False
 return recap

def goals(c:dict)->list:
 x=c['life'];rows=[('serve','served',2,'Giúp xong 2 công việc',20),('play','activities',1,'Hoàn thành 1 trò nhỏ',12),('talk','day_talked',2,'Trò chuyện với 2 người',8)]
 return [dict(id=k,title=title,goal=n,current=(len(x['day_talked']) if metric=='day_talked' else x['day_metrics'].get(metric,0)),reward=reward,claimed=k in x['goals_claimed']) for k,metric,n,title,reward in rows]

def known_request(c:dict,t:dict)->str:
 mod=PLUGINS.get(t['career'])
 if mod:return mod.known_request(c,t) if hasattr(mod,'known_request') else t.get('request',t['opening'])
 if t['career']=='teacher' and ('room' in t or teach_lesson.eligible(t)):return teach_lesson.known_request(t)
 if t['career']=='tour_guide' and ('trip' in t or tour_trip.eligible(t)):return tour_trip.known_request(t)
 if t['career']=='teacher':return 'Mục tiêu tiết học: '+t['lesson']['prompt']+' Chuẩn bị ví dụ, luyện tập, câu hỏi cuối tiết; giúp từng bạn theo điều bạn ấy cần.'
 if t['career']=='tour_guide':return 'Đoàn muốn ghé '+', '.join(data.PLACE_INDEX[k]['name'] for k in t['required'])+' và nghỉ tại Hiên Trà. Tối đa '+str(t['limit'])+' phút; vé không quá '+str(t['budget'])+' xu.'
 from . import boba
 return boba.order_text(t)

def stock(c:dict)->dict:
 return {k:sum(l['qty'] for l in c['life']['pantry'] if l['item']==k and l['expires']>=c['day']) for k in data.INGREDIENT_INDEX}

def _use(c:dict,item:str)->int:
 e=core();need=e.need
 need(item in data.INGREDIENT_INDEX,'Không có nguyên liệu này.');need(stock(c)[item]>0,'Hết nguyên liệu hợp lệ. Mở Chuẩn bị để nhập một mẻ nhỏ nhé.')
 lot=min((l for l in c['life']['pantry'] if l['item']==item and l['expires']>=c['day'] and l['qty']>0),key=lambda l:(l['expires'],l['received']))
 lot['qty']-=1
 return lot['unit_cost']

def _new_activity(c:dict,spec:dict,practice:bool)->dict:
 seed=c['day']*131+sum(map(ord,spec['id']));rng=random.Random(seed)
 a=dict(id=_id(c,'activity'),spec=spec['id'],kind=spec['type'],practice=practice,day=c['day'],status='playing',mistakes=0,moves=0,selected=None,assignments={},sequence=[],found=[],flipped=[],matched=[],reward=0)
 labels=[r[0] for r in spec['cards']]
 if spec['type']=='pairs':
  values=(labels+['Mặt trời','Mèo ngủ'])*2;rng.shuffle(values)
  a['cards']=[dict(id=str(i),value=v) for i,v in enumerate(values)]
 elif spec['type']=='sort':
  cards=[dict(id=str(i),label=label,bin=b) for i,(label,b) in enumerate(spec['cards'])];rng.shuffle(cards);a['cards']=cards;a['bins']=list(dict.fromkeys(b for _,b in spec['cards']))
 elif spec['type']=='sequence':
  a['cards']=[dict(id=str(i),label=label,rank=i) for i,label in enumerate(spec['steps'])];rng.shuffle(a['cards'])
 else:
  a['cards']=[dict(id=str(i),label=label,target=b+' · '+str(i+1)) for i,(label,b) in enumerate(spec['cards'])]
  a['right']=[dict(id=str(i),label=b+' · '+str(i+1),hint=label) for i,(label,b) in enumerate(spec['cards'])];rng.shuffle(a['right']);rng.shuffle(a['cards'])
 return a

def _activity_finish(s:dict,c:dict,a:dict):
 x=c['life'];a['status']='completed';score=max(30,100-a['mistakes']*8);a['score']=score
 if not a['practice'] and a['spec'] not in x['activity_rewards']:
  a['reward']=12;core().money(s,c,12,'Trò nhỏ: '+data.ACTIVITY_INDEX[a['spec']]['title'],a['id'],category='activity_reward')
  c['xp']+=10;x['activity_rewards'].append(a['spec']);_metric(c,'activities')
  _sticker(c,a['spec'],data.ACTIVITY_INDEX[a['spec']]['title'],data.ACTIVITY_INDEX[a['spec']]['emoji'])
 x['activity_best'][a['spec']]=max(score,x['activity_best'].get(a['spec'],0))
 x['activity_history']=ar.last(x['activity_history']+[dict(id=a['id'],spec=a['spec'],day=c['day'],score=score,practice=a['practice'],reward=a['reward'])], 100, 'life.activities', c)

def _activity_action(s,c,name,p):
 e=core();x=c['life'];need=e.need;a=x['activity'];r=dict(message='Đã thử một bước.')
 if name=='activity_start':
  spec=data.ACTIVITY_INDEX.get(p.get('spec'));need(spec and spec['career']==s['current'],'Trò nhỏ không thuộc nghề đang chơi.')
  practice=p.get('practice',False);need(type(practice) is bool,'Chế độ diễn tập cần đúng/sai.')
  need(not a or a['status']=='completed' or p.get('replace') is True,'Đang có một trò dở. Tiếp tục hoặc xác nhận đổi trò.')
  x['activity']=_new_activity(c,spec,practice);return dict(message='Bắt đầu: '+spec['title'])
 need(a and a['status']=='playing','Mở một trò nhỏ đang chơi trước nhé.')
 a['moves']+=1
 if name=='activity_assign':
  need(a['kind'] in ('sort','match'),'Thao tác không thuộc trò này.')
  card=next((v for v in a['cards'] if v['id']==p.get('card')),None);need(card,'Thẻ không tồn tại.')
  target=p.get('target');valid=a['bins'] if a['kind']=='sort' else [z['id'] for z in a['right']];need(target in valid,'Đích không tồn tại.')
  need(card['id'] not in a['assignments'],'Thẻ này đã ghép đúng.')
  ok=target==card['bin'] if a['kind']=='sort' else target==card['id']
  if ok:a['assignments'][card['id']]=target;r['message']='Đúng rồi! Thẻ đã vào vị trí.'
  else:a['mistakes']+=1;r['message']='Chưa khớp dấu hiệu. Bạn vẫn có thể thử lại, không mất xu.'
  if len(a['assignments'])==len(a['cards']):_activity_finish(s,c,a)
 elif name=='activity_step':
  need(a['kind']=='sequence','Đây không phải trò xếp bước.')
  key=p.get('card');need(key in [v['id'] for v in a['cards']] and key not in a['sequence'],'Bước không hợp lệ hoặc đã được chọn.')
  a['sequence'].append(key)
 elif name=='activity_undo':
  need(a['kind']=='sequence' and a['sequence'],'Chưa có bước để hoàn tác.');a['sequence'].pop()
 elif name=='activity_check':
  need(a['kind']=='sequence' and len(a['sequence'])==len(a['cards']),'Chọn đủ các bước trước khi kiểm.')
  if a['sequence']==[str(i) for i in range(len(a['cards']))]:_activity_finish(s,c,a)
  else:a['mistakes']+=1;a['sequence']=[];r['message']='Một bước chưa đúng nhịp. Xem gợi ý quy trình và thử lại nhé.'
 elif name=='activity_flip':
  need(a['kind']=='pairs','Đây không phải trò lật thẻ.');key=p.get('card');ids=[v['id'] for v in a['cards']];need(key in ids and key not in a['matched'],'Thẻ không hợp lệ hoặc đã ghép.')
  if len(a['flipped'])==2:a['flipped']=[]
  need(key not in a['flipped'],'Thẻ đã mở.');a['flipped'].append(key)
  if len(a['flipped'])==2:
   va=[next(v['value'] for v in a['cards'] if v['id']==k) for k in a['flipped']]
   if va[0]==va[1]:a['matched'].extend(a['flipped']);a['flipped']=[];r['message']='Tìm được một cặp!'
   else:a['mistakes']+=1;r['message']='Hai nhãn khác nhau. Ghi nhớ vị trí rồi chọn một thẻ khác.'
   if len(a['matched'])==len(a['cards']):_activity_finish(s,c,a)
 else:raise e.GameError('Thao tác trò nhỏ chưa được hỗ trợ.')
 if a['status']=='completed':r.update(message=f"Hoàn thành · {a['score']} điểm cá nhân · +{a['reward']} xu.",celebrate=True)
 return r

def handle(s:dict,c:dict,career:str,action:str,p:dict)->dict:
 e=core();need=e.need;x=c['life'];r=dict(message='Đã cập nhật trải nghiệm.')
 if action.startswith('life_'):
  name=action[5:]
  if name.startswith('activity_'):return _activity_action(s,c,name,p)
  if name=='rename':x['shop_name']=e.clean_text(p.get('name'),36);r['message']='Biển tên mới đã được treo lên.'
  elif name=='mode':
   need(not c['open'],'Chọn nhịp ngày trước khi mở ca.');need(p.get('mode') in [m['id'] for m in data.MODES],'Nhịp ngày không hợp lệ.');x['mode']=p['mode']
  elif name=='goal':
   g=next((v for v in goals(c) if v['id']==p.get('goal')),None);need(g and not g['claimed'] and g['current']>=g['goal'],'Mục tiêu chưa xong hoặc đã nhận.')
   x['goals_claimed'].append(g['id']);e.money(s,c,g['reward'],'Mục tiêu: '+g['title'],f"goal-{c['day']}-{g['id']}",category='goal_reward');c['xp']+=10;r.update(message='Đã nhận thưởng mục tiêu ngày.',celebrate=True)
  elif name=='badge':
   b=next((v for v in data.ACHIEVEMENTS if v['id']==p.get('badge')),None);need(b and b['id'] not in x['badges'],'Huy hiệu không tồn tại hoặc đã nhận.');need(c['metrics'].get(b['metric'],0)>=b['goal'],'Chưa đủ dấu mốc.')
   x['badges'].append(b['id']);_sticker(c,'badge-'+b['id'],b['title'],b['emoji']);c['xp']+=15;r.update(message='Thêm huy hiệu '+b['title']+' vào hộ chiếu nghề.',celebrate=True)
  elif name=='price':
   need(not c['open'],'Chỉ đổi giá trước ca; không sửa giá đơn khách đã nhận.');item=p.get('item');value=e.integer(p.get('price'),1,1000)
   if career=='mother_baby':
    from .content import PRODUCT_INDEX
    need(item in PRODUCT_INDEX,'Món không tồn tại.');base=PRODUCT_INDEX[item]['price']
   elif career=='milk_tea':
    from .boba import BASE_PRICE
    need(item in BASE_PRICE,'Chỉ chỉnh giá trà nền.');base=BASE_PRICE[item]
   elif career in PLUGINS and PLUGINS[career].SPEC.get('prices'):need(item in PLUGINS[career].SPEC['prices'],'Món không có trong bảng giá.');base=PLUGINS[career].SPEC['prices'][item]
   else:raise e.GameError('Nghề này nhận thù lao công việc, không bán sản phẩm để đổi giá.')
   need(round(base*.75)<=value<=round(base*1.25),'Giá thử nghiệm trong khoảng 75%–125% giá gốc để giữ khả năng hoàn tất đơn.')
   if career=='mother_baby':need(not any(t['status'] not in DONE and t['needs'].get('product')==item for t in c['tasks']),'Món này còn trong đơn được giữ từ ca trước; hoàn thành đơn trước khi đổi giá.')
   x['prices'][item]=value;x['price_history']=ar.last(x['price_history']+[dict(day=c['day'],item=item,price=value)], 100, 'life.prices', c);r['message']='Đã cập nhật bảng giá cho đơn mới.'
  elif name=='reply_edit':
   post=next((f for f in c['feed'] if f['id']==p.get('post')),None);need(post,'Không thấy bài đăng.');index=e.integer(p.get('index'),0,59);need(index<len(post['comments']) and post['comments'][index]['npc']=='player','Chỉ sửa phản hồi của bạn.')
   comment=post['comments'][index];comment['text']=e.clean_text(p.get('text'),500);comment['edited']=True;r['message']='Đã sửa phản hồi của bạn; đánh giá gốc vẫn được giữ.'
  elif name=='town':
   place=next((z for z in data.TOWN if z['id']==p.get('place')),None);need(place,'Không có điểm này trên bản đồ.')
   if place['id'] not in x['visits']:x['visits'].append(place['id']);_metric(c,'town_visits');_sticker(c,'town-'+place['id'],place['name'],place['emoji'])
   r['message']=place['name']+': '+place['description']
  elif name=='festival':
   need(c['open'] and x['festival'],'Chọn Ngày hội trước khi mở ca.');need(not x['festival_claimed'],'Ngày hội này đã hoàn tất.');need(x['day_metrics'].get('served',0)>=3 and x['day_metrics'].get('activities',0)>=1,'Chuẩn bị 3 công việc hoàn tất và 1 trò nhỏ trước nhé.')
   x['festival_claimed']=True;_metric(c,'festivals');e.money(s,c,30,'Hoạt động ngày hội',f"festival-{c['day']}",category='festival_reward');_sticker(c,'festival','Một góc ngày hội','🎏')
   e.add_feed(s,c,next(n['id'] for n in e.NPCS if n['career_id']==career),'Góc hoạt động hôm nay đã sẵn sàng. Cảm ơn bạn đã chuẩn bị thật chu đáo!',f"festival-{c['day']}",kind='story');r.update(message='Ngày hội đã có một góc mang dấu ấn của bạn!',celebrate=True)
  elif name=='chapter':
   story=data.STORY_INDEX.get(p.get('story'));need(story and story['career']==career,'Câu chuyện không thuộc nghề.')
   ch=x['chapters'].setdefault(story['id'],dict(step=0,choices=[],baseline=0,completed=False));need(not ch['completed'],'Câu chuyện đã được ghi vào album.')
   need(c['metrics'].get('served',0)>=story['goal'],'Cần làm quen nghề thêm một chút để mở câu chuyện này.')
   if ch['step']==1:need(c['metrics'].get('served',0)>ch['baseline'],'Hãy hoàn thành một công việc mới sau lời hẹn, rồi quay lại chia sẻ.')
   beat=story['beats'][ch['step']];choice=p.get('choice');need(choice in [a['id'] for a in beat['choices']],'Lựa chọn không thuộc cuộc trò chuyện.')
   ch['choices'].append(choice);ch['step']+=1
   if ch['step']==1:ch['baseline']=c['metrics'].get('served',0)
   if ch['step']==3:
    ch['completed']=True;_metric(c,'chapters');e.money(s,c,story['reward'],'Khép chương: '+story['title'],story['id'],category='story_reward');_sticker(c,story['id'],story['title'],'💌')
    person=next(n['id'] for n in e.NPCS if n['career_id']==career)
    e.remember(s,c,person,'Đã cùng khép chuyện: '+story['title'],story['id'])
    if choice=='share':e.add_feed(s,c,person,'Chuyện “'+story['title']+'” đã có kết quả. Mình thích cách bạn làm việc đến nơi.',story['id'],kind='story')
    r.update(message='Một tấm thiệp mới đã vào bộ sưu tập.',celebrate=True)
   else:r['message']='Cuộc trò chuyện đã được giữ lại. '+('Lời hẹn chờ một công việc thực hiện tiếp theo.' if ch['step']==1 else 'Cùng chọn một cách lưu kỷ niệm nhé.')
  else:raise e.GameError('Chưa có thao tác trải nghiệm này.')
  return r
 if action.startswith('tea_'):
  need(career=='milk_tea','Đây là quầy pha chế trà sữa.')
  from . import boba
  return boba.handle(s,c,action,p)
 if action.startswith('gift_'):
  need(career=='mother_baby','Đây là quầy của tiệm quà mẹ & bé.')
  from . import giftshop
  return giftshop.handle(s,c,action,p)
 if action.startswith('tour_') and action[5:] in tour_trip.CARE_ACTIONS:
  need(career=='tour_guide','Đây là công việc dẫn đoàn.');return tour_trip.care_action(s,c,action[5:],p)  # partners and kit: no task
 need(c['open'],'Mở ca trước khi thao tác công việc nhé.');t=e.current_task(c,p.get('task'));need(t['career']==career,'Sai nghề công việc.');c['turn']+=1
 if action.startswith('lesson_'):
  need(career=='teacher','Đây là tiết học.');name=action[7:]
  if 'room' in t or (name=='roll' and teach_lesson.eligible(t)):r.update(teach_lesson.handle(s,c,t,name,p));return r
  if name=='plan':
   need(t['stage']=='plan','Tiết đã bắt đầu.');steps=p.get('steps');need(isinstance(steps,list) and steps==['demo','practice','reflect'],'Thử nhịp: ví dụ → luyện tập → câu hỏi cuối tiết.');t['plan']=steps;t['stage']='attendance';t['known']=True;t['status']='understood';r['message']='Giáo án sẵn sàng. Cùng điểm danh theo những bạn đang có mặt.'
  elif name=='attendance':
   need(t['stage']=='attendance','Điểm danh ở đầu tiết.');student=next((v for v in t['students'] if v['id']==p.get('student')),None);need(student,'Không có bạn này.');present=p.get('present');need(type(present) is bool,'Trạng thái có mặt không hợp lệ.')
   if present!=student['present']:r['message']='Đối chiếu ghế và thông báo nghỉ rồi đánh dấu lại nhé.';t['mistakes']+=1
   else:t['attendance'][student['id']]=present;r['message']='Đã ghi nhận '+student['name']+'.'
   if len(t['attendance'])==len(t['students']):t['stage']='teach'
  elif name=='teach':
   need(t['stage']=='teach','Hoàn thành điểm danh trước.');student=next((v for v in t['students'] if v['id']==p.get('student')),None);need(student and student['present'],'Bạn này không có mặt trong tiết.');need(student['id'] not in t['taught'],'Bạn này đã được hướng dẫn.');method=p.get('method');need(method in [m['id'] for m in data.METHODS],'Cách hướng dẫn không tồn tại.')
   if method!=student['method']:t['mistakes']+=1;r['message']=student['name']+': '+student['need']+' Thử một cách khác nhé.'
   else:t['taught'][student['id']]=method;r['message']=student['name']+' đã thử được theo cách phù hợp. '+t['lesson']['fact']
   if len(t['taught'])==sum(v['present'] for v in t['students']):t['stage']='grade'
  elif name=='grade':
   need(t['stage']=='grade','Hướng dẫn các bạn trước khi xem phiếu cuối tiết.');st=next((v for v in t['students'] if v['id']==p.get('student')),None);need(st and st['id'] in t['taught'],'Phiếu không thuộc bạn đang học.');need(st['id'] not in t['grades'],'Phiếu đã phản hồi.');correct=p.get('correct');need(type(correct) is bool,'Chọn nhận xét đúng hoặc cần thử lại.');feedback=p.get('feedback');need(feedback in ('specific','retry','encourage'),'Chọn một phản hồi cụ thể.')
   actual=st['submission']==t['lesson']['answer']
   if correct!=actual:t['mistakes']+=1;r['message']='Đọc lại ví dụ trên bảng và câu trả lời của bạn ấy; không cần đoán.'
   else:t['grades'][st['id']]=correct;t['feedback'][st['id']]=feedback;r['message']='Đã gửi phản hồi riêng cho '+st['name']+'.'
   if len(t['grades'])==len(t['taught']):t['stage']='ready'
  elif name=='complete':
   need(t['stage']=='ready','Còn bạn chưa nhận phản hồi cuối tiết.');need(p.get('confirm') is True,'Xác nhận khép tiết trước nhé.')
   e.task_done(s,c,t,65,'Đã hoàn thành tiết '+t['lesson']['title']+' với phản hồi riêng cho các bạn.');r.update(message='Tiết học hoàn thành. Cả lớp có thêm một điều hiểu rõ!',celebrate=True)
  else:raise e.GameError('Thao tác tiết học không hợp lệ.')
 elif action.startswith('tour_'):
  need(career=='tour_guide','Đây là công việc dẫn đoàn.');name=action[5:]
  if 'trip' in t or (name=='plan' and p.get('v')==2 and tour_trip.eligible(t)) or (name=='care' and tour_trip.eligible(t)):r.update(tour_trip.handle(s,c,t,name,p));return r
  if name=='plan':
   need(t['stage']=='plan','Đoàn đã khởi hành; không sửa vé đã dùng.');route=p.get('route');need(isinstance(route,list) and 3<=len(route)<=5 and len(route)==len(set(route)) and all(k in data.PLACE_INDEX and k!='gate' for k in route),'Chọn 3–5 điểm khác nhau, không gồm bến xuất phát.')
   need(set(t['required']+['cafe'])<=set(route),'Cần có các điểm khách muốn và Hiên Trà nghỉ chân.');need(t['weather']!='rain' or 'river' not in route,'Lối Bờ Mây đóng khi mưa; chọn đường khác.')
   fee=sum(data.PLACE_INDEX[k]['fee'] for k in route);duration=sum(data.PLACE_INDEX[k]['minutes']+5 for k in route);need(fee<=t['budget'] and duration<=t['limit'],'Lộ trình vượt tiền vé hoặc thời gian đã chốt.')
   t.update(route=route,plan_cost=fee,stage='gather',known=True,status='understood');r['message']='Đã chốt lộ trình. Kiểm đủ đoàn trước khi xuất phát.'
  elif name=='count':
   need(t['stage'] in ('gather','stop'),'Chưa tới bước kiểm đoàn.');vid=p.get('visitor');need(vid in [v['id'] for v in t['visitors']],'Người này không nằm trong danh sách đoàn.');need(vid not in t['counted'],'Bạn đã xác nhận người này.')
   need(not (t['at']==1 and t['day']%2==0 and vid=='nam' and not t['located']),'Nam đang hỏi ở quầy thông tin. Cần liên hệ điểm hẹn trước, chưa đánh dấu có mặt.')
   t['counted'].append(vid);r['message']=f"Đã kiểm {len(t['counted'])}/{len(t['visitors'])} người."
  elif name=='locate':
   need(t['stage']=='stop' and t['at']==1 and t['day']%2==0,'Đoàn chưa có người tách ở điểm này.');need(p.get('location')=='info','Theo lời nhắn: hỏi tại quầy thông tin, không cho đoàn tự tản đi.');t['located']=True;r['message']='Nam đã về điểm hẹn cùng điều phối. Bây giờ có thể xác nhận có mặt.'
  elif name=='depart':
   need(t['stage']=='gather' and len(t['counted'])==len(t['visitors']),'Cần kiểm đủ người trước khi đi.');need(p.get('confirm') is True,'Xác nhận tiền vé trước khi khởi hành.')
   e.money(s,c,-t['plan_cost'],'Vé tham quan',t['id'],category='tour_cost');t.update(stage='stop',at=0,counted=[],quiz_done=False,photo_done=False,located=False);r['message']='Đoàn đã đến '+data.PLACE_INDEX[t['route'][0]]['name']+'.'
  elif name=='tell':
   need(t['stage']=='stop','Đến một điểm trước.');place=data.PLACE_INDEX[t['route'][t['at']]];answer=p.get('answer');need(answer in place['answers'],'Câu trả lời không thuộc bảng thông tin.')
   if answer!=place['answer']:t['mistakes']+=1;r['message']='Thử xem bảng thông tin của điểm đến, đừng tự bịa một chi tiết.'
   else:t['quiz_done']=True;r['message']='Bạn đã kể đúng chi tiết của câu chuyện địa phương.'
  elif name=='photo':
   need(t['stage']=='stop','Đến một điểm để chụp.');place=data.PLACE_INDEX[t['route'][t['at']]]
   if p.get('object')!=place['target']:t['mistakes']+=1;r['message']='Khung này chưa đúng chủ thể trên phiếu ảnh. Tìm chi tiết được nhắc nhé.'
   else:t['photo_done']=True;r['message']='Đã chụp đúng chủ thể. Tấm bưu thiếp sẽ được lưu khi rời điểm.'
  elif name=='next':
   need(t['stage']=='stop' and t['quiz_done'] and t['photo_done'],'Cần kể chuyện và chụp ảnh trước khi chuyển điểm.');need(len(t['counted'])==len(t['visitors']),'Cần kiểm đủ đoàn trước khi di chuyển.')
   place=data.PLACE_INDEX[t['route'][t['at']]];t['stamps'].append(place['id']);_sticker(c,'place-'+place['id'],place['name'],place['emoji'])
   if t['at']+1==len(t['route']):t['stage']='ready';r['message']='Đã tới đủ các điểm. Cùng khép chuyến và gửi kỷ niệm.'
   else:t['at']+=1;t.update(counted=[],quiz_done=False,photo_done=False,located=False);r['message']='Đoàn đã đến '+data.PLACE_INDEX[t['route'][t['at']]]['name']+'.'
  elif name=='complete':
   need(t['stage']=='ready' and set(t['route'])==set(t['stamps']),'Lộ trình chưa hoàn thành.');need(p.get('confirm') is True,'Xác nhận khép chuyến.')
   e.task_done(s,c,t,90,'Đã đi cùng đoàn qua '+str(len(t['stamps']))+' điểm, kiểm đủ người và lưu bưu thiếp.');r.update(message='Một chuyến đi có người, có chuyện và có kỷ niệm!',celebrate=True)
  else:raise e.GameError('Thao tác dẫn đoàn không hợp lệ.')
 else:raise e.GameError('Thao tác trải nghiệm chưa được hỗ trợ.')
 return r

def update_patience(c:dict,action:str,payload:dict,before:dict):
 """Soft, turn-based waiting. No wall-clock/offline or reading penalty."""
 if not c['open'] or c['life']['mode']=='calm':return
 # The milk-tea counter keeps its own beat-based queue (game/boba.py).
 if c['tasks'] and c['tasks'][-1]['career']=='milk_tea':return
 physical={'shop_pick','shop_pack','shop_deliver','ph_pick','ph_deliver','ac_match','ac_complete','cs_execute','cs_close','tea_add','tea_serve','tea_discard','lesson_teach','lesson_grade','tour_next','lesson_next','lesson_help','tour_depart','gift_advise','gift_ask','gift_book','gift_inspect','gift_resolve'}
 for mod in PLUGINS.values():physical|=set(mod.SPEC.get('physical',()))
 active=payload.get('task') or c.get('active_task')
 for task in c['tasks']:
  if task['status'] in DONE:continue
  loss=0
  if action in physical and task['id']!=active and not task.get('deferred'):loss=1
  loss+=max(0,task['mistakes']-before.get(task['id'],task['mistakes']))*4
  if loss:task['patience']=max(25,task.get('patience',100)-loss)

def on_talk(c:dict,npc:str):
 if npc not in c['life']['day_talked']:c['life']['day_talked'].append(npc)

def public_life(c:dict)->dict:
 x=tree_copy(c['life']);x['goals']=goals(c);x['stock']=stock(c);x['weather']=data.WEATHERS[(c['day']-1)%3];x['forecast']={'calm':2,'normal':3,'festival':4}[x['mode']]
 if 'tour' in x:x['tour']=tour_trip.public_care(c)  # tour guide: the group, partners, kit, notebook, reviews
 x['badges_view']=[dict(b,current=c['metrics'].get(b['metric'],0),claimed=b['id'] in x['badges']) for b in data.ACHIEVEMENTS]
 a=x['activity']
 if a:
  for v in a['cards']:
   if a['kind']=='pairs' and v['id'] not in a['flipped']+a['matched']:v['value']=None
   v.pop('rank',None);v.pop('bin',None);v.pop('target',None)
 return x

def _strip(v):
 if isinstance(v,dict):return {k:_strip(x) for k,x in v.items() if not k.startswith('_')}
 if isinstance(v,list):return [_strip(x) for x in v]
 return v

def public_task(t:dict)->dict:
 mod=PLUGINS.get(t['career'])
 if mod:return mod.public_task(t) if hasattr(mod,'public_task') else _strip(tree_copy(t))
 v=tree_copy(t)
 if t['career']=='teacher':
  v['lesson'].pop('answer',None)
  for st in v['students']:
   st.pop('method',None)
   if st['id'] not in t['taught']:st['submission']=None
  v.pop('room',None)
  if 'room' in t or teach_lesson.eligible(t):v['room']=teach_lesson.public(t)
 elif t['career']=='tour_guide':
  v.pop('trip',None)
  if 'trip' in t or tour_trip.eligible(t):v['trip']=tour_trip.public(t)
 elif t['career']=='milk_tea':
  from . import boba
  return boba.public_task(t)
 return v

def validate(c:dict,career:str):
 e=core();need=e.need;x=c.get('life');need(isinstance(x,dict) and set(initial(career))<=set(x),'Bản lưu thiếu trải nghiệm v0.3.')
 need(x.get('version')==1,'Phiên bản trải nghiệm không hợp lệ.');e.clean_text(x.get('shop_name'),36,0);need(x['mode'] in [m['id'] for m in data.MODES],'Nhịp ngày không hợp lệ.')
 for k in ('seq','streak','best_streak','tips','staff_tips','consumed_cost','day_waste'):e.integer(x.get(k),0,10**9)
 for k in ('festival','festival_claimed','onboarding'):need(type(x.get(k)) is bool,'Cờ trải nghiệm không hợp lệ.')
 for k in ('goals_claimed','pantry','price_history','waste','activity_rewards','activity_history','badges','stickers','visits','goals_history','day_guests','served_sources','day_talked'):
  need(isinstance(x.get(k),list) and len(x[k])<=600,'Danh sách trải nghiệm quá lớn hoặc không hợp lệ.')
 for k in ('day_metrics','prices','activity_best','chapters'):need(isinstance(x.get(k),dict) and len(x[k])<=200,'Dữ liệu trải nghiệm không hợp lệ.')
 for k,v in x['day_metrics'].items():e.clean_text(k,100);e.integer(v,0,10**9)
 for k,v in x['prices'].items():
  need(k in (set(PLUGINS[career].SPEC.get('prices',{})) if career in PLUGINS else _price_keys(career)),'Mã bảng giá không hợp lệ.');e.integer(v,1,1000)
 for lot in x['pantry']:
  need(isinstance(lot,dict) and set(('id','item','qty','unit_cost','expires','received'))<=set(lot),'Lô nguyên liệu thiếu dữ liệu.');need(lot['item'] in data.INGREDIENT_INDEX,'Nguyên liệu lạ.');e.clean_text(lot['id'],100);e.integer(lot['qty'],0,60);e.integer(lot['unit_cost'],0,20);e.integer(lot['expires'],1,999999);e.integer(lot['received'],1,999999)
 need(len({l['id'] for l in x['pantry']})==len(x['pantry']),'Trùng lô nguyên liệu.')
 for k,qty in stock(c).items():need(qty<=60,'Tồn vượt sức chứa.')
 if career=='milk_tea':
  from . import boba
  boba.validate(c)
 if career=='mother_baby':
  from . import giftshop
  giftshop.validate(c)
 if career=='tour_guide':tour_trip.validate_care(c)
 need(all(k in {'serve','play','talk'} for k in x['goals_claimed']),'Mục tiêu không hợp lệ.')
 need(all(k in [b['id'] for b in data.ACHIEVEMENTS] for k in x['badges']) and len(x['badges'])==len(set(x['badges'])),'Huy hiệu không hợp lệ.')
 for key,ch in x['chapters'].items():
  need(key in data.STORY_INDEX and data.STORY_INDEX[key]['career']==career and isinstance(ch,dict),'Câu chuyện không hợp lệ.');e.integer(ch.get('step'),0,3);e.integer(ch.get('baseline'),0,10**9);need(isinstance(ch.get('choices'),list) and len(ch['choices'])==ch['step'] and type(ch.get('completed')) is bool,'Bước câu chuyện sai.');need(ch['completed']==(ch['step']==3),'Kết quả câu chuyện sai.')
  for i,choice in enumerate(ch['choices']):need(choice in [z['id'] for z in data.STORY_INDEX[key]['beats'][i]['choices']],'Lựa chọn câu chuyện sai.')
 for st in x['stickers']:
  need(isinstance(st,dict),'Thiệp không hợp lệ.')
  for k in ('id','title','emoji'):e.clean_text(st.get(k),200)
  e.integer(st.get('day'),1,999999)
 for row in x['waste']:
  allowed=('cup',*data.INGREDIENT_INDEX)
  if career in PLUGINS:allowed=(*allowed,*[i['id'] for i in (PLUGINS[career].SPEC.get('inventory') or {}).get('items',[])],*PLUGINS[career].SPEC.get('waste_items',()))
  need(isinstance(row,dict) and row.get('item') in allowed,'Hao hụt không hợp lệ.');e.integer(row.get('qty'),0,60);e.integer(row.get('value'),0,10000);e.integer(row.get('day'),1,999999);e.clean_text(row.get('reason'),500)
 for k in x['activity_rewards']:need(k in data.ACTIVITY_INDEX and data.ACTIVITY_INDEX[k]['career']==career,'Thưởng trò nhỏ sai nghề.')
 a=x['activity']
 if a:
  need(isinstance(a,dict) and a.get('spec') in data.ACTIVITY_INDEX and data.ACTIVITY_INDEX[a['spec']]['career']==career,'Trò nhỏ không hợp lệ.')
  need(a.get('kind')==data.ACTIVITY_INDEX[a['spec']]['type'] and a.get('status') in ('playing','completed') and type(a.get('practice')) is bool,'Trạng thái trò nhỏ sai.')
  for k in ('day','moves','mistakes','reward'):e.integer(a.get(k),1 if k=='day' else 0,10**9)
  # Regenerate fixed cards with the session day to protect the underlying solution.
  fake={'day':a['day'],'life':{'seq':0}};base=_new_activity(fake,data.ACTIVITY_INDEX[a['spec']],a['practice'])
  need(a.get('cards')==base['cards'],'Thẻ gốc của trò nhỏ bị thay đổi.')
  ids={v['id'] for v in a['cards']}
  for k in ('sequence','found','flipped','matched'):need(isinstance(a.get(k),list) and len(a[k])<=len(ids) and len(a[k])==len(set(a[k])) and all(v in ids for v in a[k]),'Danh sách thẻ sai.')
  need(isinstance(a.get('assignments'),dict) and all(k in ids for k in a['assignments']),'Ghép thẻ sai.')
  if a['kind']=='sort':need(a.get('bins')==base['bins'] and all(v in a['bins'] for v in a['assignments'].values()),'Ngăn thẻ sai.')
  if a['kind']=='match':need(a.get('right')==base['right'] and all(v in ids for v in a['assignments'].values()),'Nhãn đích sai.')
  if a['kind']=='pairs':need(len(a['flipped'])<=2,'Chỉ lật hai thẻ cùng lúc.')

def _price_keys(career:str)->set:
 if career=='milk_tea':
  from .boba import BASE_PRICE
  return set(BASE_PRICE)
 if career=='mother_baby':
  from .content import PRODUCT_INDEX
  return set(PRODUCT_INDEX)
 return set()

def upgrade_task(t:dict):
 """Old saves: give earlier milk-tea tasks the fields the counter now reads."""
 if t.get('career')=='milk_tea':
  for k,v in (('walkin',None),('changes',[]),('usual',False),('beats',0),('discount',0),('vip',False),('office',False),('combo',False),('group',None),('app',None)):t.setdefault(k,copy.deepcopy(v))
  if 'src' not in t and isinstance(t.get('needs'),dict):t['src']=dict(fixed=copy.deepcopy(t['needs']))
  cup=t.get('cup')
  if isinstance(cup,dict):
   cup.setdefault('placed',bool(cup.get('items')));cup.setdefault('dome',False);cup.setdefault('seal_t',None)
   cup.setdefault('seal_q','ok' if cup.get('sealed') else None)

def upgrade_save(s:dict):
 """Called at the end of engine.migrate_state: cheap, idempotent setdefaults."""
 for cid in ('milk_tea','mother_baby'):
  c=s['careers'].get(cid)
  if not isinstance(c,dict) or not isinstance(c.get('tasks'),list):continue
  if cid=='milk_tea':
   for t in c['tasks']:
    if isinstance(t,dict):upgrade_task(t)
  else:
   from . import giftshop
   giftshop.upgrade(c)
 c=s['careers'].get('tour_guide')
 if isinstance(c,dict):tour_trip.upgrade(c)  # tour guide: an empty care record (life.tour)

def public_counter(raw:dict,cid:str,out:dict):
 """Public view of the counter state (hidden rolls stay on the server)."""
 if cid=='milk_tea':
  from . import boba
  out['boba']=boba.public(raw)
 else:
  from . import giftshop
  out['gift']=giftshop.public(raw)

def validate_task(t:dict,original:dict):
 e=core();need=e.need;cid=t['career']
 if cid=='milk_tea':
  from . import boba
  boba.validate_task(t);return
 need(set(original)<=set(t),'Công việc mới thiếu dữ liệu.')
 mod=PLUGINS.get(cid)
 if mod:
  for k in mod.FIXED:need(t.get(k)==original.get(k),'Dữ kiện gốc công việc bị thay đổi: '+k)
  if 'patience' in t:e.integer(t['patience'],25,100)
  mod.validate_task(t,original);return
 fixed={'teacher':['lesson','students'],'tour_guide':['required','budget','limit','visitors','weather']}[cid]
 for k in fixed:need(t[k]==original[k],'Dữ kiện gốc công việc bị thay đổi: '+k)
 if cid=='teacher':
  need(t['stage'] in ('plan','attendance','teach','grade','ready'),'Bước tiết học sai.')
  need(t['plan'] in ([],['demo','practice','reflect']),'Giáo án sai.')
  ids={st['id']:st for st in t['students']}
  for k in ('attendance','taught','grades','feedback'):need(isinstance(t[k],dict) and all(v in ids for v in t[k]),'Danh sách lớp sai.')
  for v in t['attendance'].values():need(type(v) is bool,'Điểm danh sai.')
  for k,v in t['taught'].items():need(v in [m['id'] for m in data.METHODS] and ids[k]['present'],'Phương pháp sai.')
  for v in t['grades'].values():need(type(v) is bool,'Nhận xét sai.')
  for v in t['feedback'].values():need(v in ('specific','retry','encourage'),'Phản hồi sai.')
  if 'room' in t:
   need(t['stage']=='plan' and not t['plan'] and not t['taught'] and not t['grades'],'Tiết học trộn hai cách chơi.');need(not t['attendance'] or t['status']=='completed','Điểm danh sai.')
   teach_lesson.validate(t)
 elif cid=='tour_guide':
  need(t['stage'] in ('plan','gather','stop','ready'),'Bước dẫn đoàn sai.')
  for k in ('route','stamps','counted'):need(isinstance(t[k],list) and len(t[k])<=6 and len(t[k])==len(set(t[k])),'Lộ trình trùng/sai.')
  need(all(k in data.PLACE_INDEX and k!='gate' for k in t['route']+t['stamps']),'Điểm đến sai.');need(all(k in [v['id'] for v in t['visitors']] for k in t['counted']),'Thành viên sai.')
  e.integer(t['at'],-1,4);e.integer(t['plan_cost'],0,100)
  if t['route']:need(t['plan_cost']==sum(data.PLACE_INDEX[k]['fee'] for k in t['route']),'Vé không khớp.');need(t['at']<len(t['route']),'Điểm đang tới không có trên lộ trình.')
  for k in ('located','quiz_done','photo_done'):need(type(t[k]) is bool,'Trạng thái dẫn đoàn sai.')
  if 'trip' in t:
   need(t['stage']=='plan' and not t['route'] and not t['stamps'] and not t['counted'] and t['at']==-1,'Chuyến đi trộn hai cách chơi.')
   tour_trip.validate(t)

