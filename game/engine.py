"""Server-authoritative game rules.

UI and dialogue can propose actions; only this reducer mutates money, inventory,
evidence, workflow, relationships, or quests. The storage layer executes it in
an atomic SQLite transaction with revision checking and command receipts.
"""
from __future__ import annotations
import base64
import copy
import math
import re
import unicodedata
from typing import Any
from .content import (CAREERS,CAREER_META,NPCS,NPC_INDEX,PRODUCTS,PRODUCT_INDEX,PAPERS,RIBBONS,
    LOT_INDEX,UPGRADE_INDEX,QUESTS,QUEST_INDEX,make_task,initial_career)
from .events import SCRIPTS,instantiate,event_view
from . import operations as ops
from . import experiences as life
from . import extra_content as extra
from . import feedback as fbk
from . import situations as sit
from . import inventory as inv
from . import employment as emp
from .careers import PLUGINS
from . import journey as jr
from . import invest as iv
from . import career_stories as cst
from . import desk as dk
from . import giftshop as gifts
from . import incidents as incs
from . import happenings as haps

ORIGINAL=("mother_baby","pharmacy","accounting","customer_care")
UI_THEMES=("kem","tra_xanh","dem","bien","keo")
SETTING_CHOICES={"lang":("vi","en"),"uiTheme":UI_THEMES,"musicTrack":("auto","calm","bright","off")}

class GameError(ValueError):
    def __init__(self, message: str, code: str="invalid_action"):
        super().__init__(message)
        self.message=message
        self.code=code

def need(condition: Any, message: str, code: str="invalid_action") -> None:
    if not condition: raise GameError(message,code)

def integer(value: Any, low: int=0, high: int=999999) -> int:
    need(type(value) is int and low<=value<=high,"Số lượng không hợp lệ.")
    return value

def clean_text(value: Any, max_length: int=500, minimum: int=1) -> str:
    need(isinstance(value,str),"Nội dung cần là văn bản.")
    text="".join(c for c in value.strip() if c in "\n\t" or ord(c)>=32)
    need(minimum<=len(text)<=max_length,f"Nội dung cần từ {minimum} đến {max_length} ký tự.")
    return text

def normalize(s: str) -> str:
    s=unicodedata.normalize("NFD",s.lower()).replace("đ","d")
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

def new_state() -> dict:
    return dict(schema=4,name="Mây",current=None,seq=0,
        settings=default_settings(),
        careers={cid:initial_career(cid) for cid in CAREERS},journey=jr.initial(),stories=cst.initial())

def default_settings() -> dict:
    return dict(mode="everyday",sound=True,music=False,reduceMotion=False,largeText=False,aiConsent=True,aiAsked=True,aiNoticeSeen=False,securityEvents=True,
        lang="vi",uiTheme="kem",musicTrack="auto",musicVolume=45,sfxVolume=70,notify=False,publicProfile=False)

def migrate_state(state:dict) -> dict:
    """Upgrade v1 locally without replaying wages, rent, tax or past incidents."""
    need(isinstance(state,dict),"Bản lưu cần là một đối tượng.","invalid_save")
    s=copy.deepcopy(state)
    # AI characters are on by default: saves that never went through that change get it once.
    ai_unasked=not isinstance(s.get('settings'),dict) or 'aiAsked' not in s['settings']
    need(s.get("schema") in (1,2,3,4),"Phiên bản bản lưu chưa được hỗ trợ.","invalid_save")
    if s["schema"]==1:
        need(isinstance(s.get("careers"),dict),"Bản lưu thiếu các nghề.","invalid_save")
        for cid,c in s["careers"].items():
            need(cid in CAREERS and isinstance(c,dict),"Nghề bản lưu không hợp lệ.")
            integer(c.get("money"),0,10**9);integer(c.get("day"),1,10**9)
            c["ops"]=ops.initial_operations(cid,c["money"],c["day"])
            c.setdefault("theme","boba")
            # The old one-off helper remains an owned tool, not a hired worker.
        s.setdefault("settings",{})["securityEvents"]=True
        s["schema"]=2
    if s['schema']==2:
        need(isinstance(s.get('careers'),dict), 'Bản lưu thiếu nghề.')
        for cid in extra.NEW_CAREERS:
            s['careers'].setdefault(cid,initial_career(cid))
        for cid,c in s['careers'].items():
            need(cid in CAREERS and isinstance(c,dict),'Nghề không hợp lệ.')
            c.setdefault('life',life.initial(cid))
        s['schema']=3
    if s['schema']==3:
        need(isinstance(s.get('careers'),dict) and isinstance(s.get('settings'),dict),'Bản lưu thiếu nghề.','invalid_save')
        for cid in CAREERS:
            s['careers'].setdefault(cid,initial_career(cid))
        for cid,c in s['careers'].items():
            need(cid in CAREERS and isinstance(c,dict),'Nghề không hợp lệ.','invalid_save')
            base=initial_career(cid)
            c.setdefault('ext',base['ext'])
            if 'job' not in c:
                # A career already played before v0.4 keeps working: treat it as already hired.
                c['job']=emp.hired_record(cid,None,c.get('day',1)) if c.get('started') and emp.required(cid) else base['job']
        for k,v in default_settings().items():s['settings'].setdefault(k,v)
        s['schema']=4
    # Careers added in later releases join existing saves untouched.
    if isinstance(s.get('careers'),dict):
        for cid in CAREERS:
            if cid not in s['careers']:s['careers'][cid]=initial_career(cid)
        # One character's journey: older saves join the story where their progress already is.
        if 'journey' not in s:jr.migrate(s)
        elif isinstance(s['journey'],dict):jr.upgrade(s['journey'])
        iv.migrate(s)  # đầu tư: savings, Mây Coin, scam offers under journey.invest
        life.upgrade_save(s)
        dk.migrate(s)  # paperwork desks: desk memory + refreshed wording of older tasks
        incs.migrate(s)  # chuyện đời: an empty incident book per workplace
        haps.migrate(s)  # chuyện bất ngờ trong ca: live happenings in the scene
        cst.migrate(s)  # truyện nghề: an empty story book for older saves
        emp.migrate(s)  # xin việc: nơi đã làm trước khi cần tuyển dụng thì coi như đã ký hợp đồng
        inv.migrate(s)  # kho: đơn nhập cũ theo nhịp → giờ giao dự kiến
    if isinstance(s.get('settings'),dict):
        if ai_unasked:s['settings'].update(aiConsent=True,aiAsked=True)
        s['settings'].setdefault('aiNoticeSeen',False)
    return s


def needs_migration(state:dict) -> bool:
    return state.get('schema')!=4 or not isinstance(state.get('careers'),dict) or set(state['careers'])!=set(CAREERS) or 'journey' not in state or 'stories' not in state or 'aiAsked' not in (state.get('settings') or {})


def metric(c: dict,key: str,value: int=1) -> None:
    c["metrics"][key]=c["metrics"].get(key,0)+value

def log(s:dict,c:dict,kind:str,text:str,npc:str|None=None,ref:str|None=None) -> str:
    s["seq"]+=1
    lid=f"log-{s['seq']}"
    c["journal"].append(dict(id=lid,kind=kind,text=text,npc=npc,ref=ref,day=c["day"],turn=c["turn"]))
    # Keep a bounded display history. Every memory embeds its own source snapshot.
    if len(c["journal"])>1200: c["journal"]=c["journal"][-1200:]
    return lid

def remember(s:dict,c:dict,npc:str,text:str,ref:str|None=None) -> None:
    lid=log(s,c,"memory",text,npc,ref)
    c["memories"].append(dict(id=lid,npc=npc,text=text,source=ref or lid,day=c["day"]))
    c["memories"]=c["memories"][-120:]
    c["relationships"][npc]=min(100,c["relationships"].get(npc,0)+4)

def money(s:dict,c:dict,amount:int,reason:str,ref:str|None=None,category:str|None=None) -> None:
    need(type(amount) is int,"Giao dịch không hợp lệ.")
    need(c["money"]+amount>=0,"Chưa đủ xu. Chọn phương án không tốn xu hoặc hoàn thành thêm một việc nhé.")
    c["money"]+=amount
    ops.record_money(c,amount,reason,ref,category)
    c["earnings"]+=max(amount,0)
    c["costs"]+=max(-amount,0)
    log(s,c,"money",f'{"+" if amount>=0 else ""}{amount} xu · {reason}',ref=ref)

def current_task(c:dict,tid:Any=None,allow_done:bool=False) -> dict:
    tid=tid or c["active_task"]
    t=next((t for t in c["tasks"] if t["id"]==tid),None)
    need(t,"Không tìm thấy công việc này.")
    if not allow_done: need(t["status"] not in ("completed","referred","cancelled"),"Công việc này đã hoàn tất. Không thể nhận thưởng hai lần.","already_completed")
    return t

def next_active(c:dict) -> None:
    unfinished=[t for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled") and not t["deferred"]]
    c["active_task"]=unfinished[0]["id"] if unfinished else None

def add_feed(s:dict,c:dict,npc:str,text:str,source:str,stars:int|None=None,kind:str="post") -> dict:
    s["seq"]+=1
    post=dict(id=f"post-{s['seq']}",npc=npc,author=NPC_INDEX[npc]["display_name"] if npc in NPC_INDEX else s["name"],
        text=text,day=c["day"],source=source,stars=stars,kind=kind,comments=[],liked=False,npc_only=npc!="player")
    c["feed"].insert(0,post)
    c["feed"]=c["feed"][:100]
    return post

def available(c:dict,item:str) -> int:
    held=sum(t.get("basket",{}).get(item,0) for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled"))
    return c["stock"].get(item,0)-held

def task_done(s:dict,c:dict,t:dict,reward:int,narrative:str,status:str="completed") -> None:
    need(t["id"] not in c["completed_ids"],"Công việc đã nhận kết quả.","already_completed")
    t["status"]=status
    t["completed_turn"]=c["turn"]
    c["completed_ids"].append(t["id"])
    c["day_completed"]+=1
    metric(c,"served"); metric(c,f"served:{t['npc']}")
    c["xp"]+=30
    if reward: money(s,c,reward,"Hoàn thành: "+t["title"],t["id"])
    remember(s,c,t["npc"],narrative,t["id"])
    made=fbk.make_review(s,c,t,status)
    review=made["text"];stars=made["stars"]
    if t['mistakes']==0 and status=='completed' and not made["feedback"].get("unfair") and made.get("aside",True):
        mod=PLUGINS.get(t['career'])
        remarks=mod.SPEC.get('review_asides',[]) if mod else extra.REVIEW_ASIDES.get(t['career'],[])
        if remarks:review+=' '+remarks[(c['day']+c['day_completed']-2)%len(remarks)]
    post=add_feed(s,c,t["npc"],review,t["id"],stars,"review")
    fbk.attach(post,made)
    if t['career']=='teacher' and t.get('students'):
        kid=t['students'][(c['day']+c['day_completed'])%len(t['students'])]['name']
        post['author']=('Mẹ của ' if (c['day']+len(kid))%2 else 'Bố của ')+kid
    metric(c,"reviews_"+str(stars))
    c["pending"].append(dict(kind="return_note",day=c["day"]+1,turn=0,npc=t["npc"],ref=t["id"],text="Lần trước bạn đã giúp mình: "+t["title"]+". Hôm nay mình ghé chào một chút nhé."))
    life.after_task(s,c,t)
    next_active(c)


def reveal_needs(s:dict,c:dict,t:dict) -> str:
    if t["career"] in PLUGINS or t["career"] in extra.NEW_CAREERS:
        reply=life.known_request(c,t)
    elif t.get("desk"):
        reply=dk.known_request(t)
    elif t["career"]=="mother_baby" and t.get("gen"):
        reply=gifts.request_text(c,t)
    elif t["career"]=="mother_baby":
        n=t["needs"];p=PRODUCT_INDEX[n["product"]]
        paper=next(p["name"] for p in PAPERS if p["id"]==n["paper"])
        reply=f'Mình cần {n["qty"]} × {p["name"]}, tối đa {n["budget"]} xu. '+(f'Gói giấy {paper.lower()} giúp mình nhé.' if n["gift"] else "Không cần gói quà nhé.")
    elif t["career"]=="pharmacy":
        n=t["needs"]
        reply="Yêu cầu này cần chuyển cô Thu. Mình không có đủ thông tin trong phiếu." if n["referral"] else f'Phiếu đã bổ sung: mã {n["product"]}, số lượng {n["qty"]}. Chỉ giao lô còn hợp lệ và không tạm giữ nhé.'
        if not t["known"] and n["missing"]:metric(c,"clarified")
    elif t["career"]=="accounting":
        reply="Mình cần bạn mở bản gốc, ghép phiếu với giao dịch, rồi giải thích số cuối cùng. Đừng sửa số chỉ để cho khớp nhé."
    else:reply="Bạn hãy xác minh mã của mình, xem hồ sơ rồi cho mình biết bước xử lý thực tế nhé."
    if not t["known"]:
        t["known"]=True;t["status"]="understood"
        log(s,c,"fact",reply,t["npc"],t["id"])
    return reply


def ensure_shop(t:dict,c:dict,pack_check:bool=True) -> None:
    if t.get("gen"):return gifts.ensure(t,c,pack_check)
    need(t["known"],"Hỏi nhu cầu khách trước để biết ngân sách và món cần tìm.")
    n=t["needs"]
    need(t["basket"]=={n["product"]:n["qty"]},"Giỏ chưa đúng yêu cầu. Kiểm mã món và số lượng trên lời nhắn của khách nhé.")
    total=sum(life.price(c,k,PRODUCT_INDEX[k]["price"])*v for k,v in t["basket"].items())
    need(total<=n["budget"],"Giỏ vượt ngân sách đã xác nhận.")
    if pack_check and n["gift"]:need(t["pack"],"Món này cần gói quà. Ghé bàn gói trước khi thu tiền nhé.")
    if pack_check and t["pack"]:need(t["pack"]["paper"]==n["paper"],"Màu giấy chưa đúng điều khách đã chọn. Bạn có thể đổi lại miễn phí trước khi giao.")
    for k,v in t["basket"].items():need(c["stock"].get(k,0)>=v,"Hàng trong kho không đủ; cần kiểm nhập thêm.")


def ensure_pharmacy(t:dict,c:dict) -> None:
    need(t["known"],"Phiếu chưa đủ thông tin, cần hỏi lại hoặc chuyển người phụ trách.")
    need(not t["needs"]["referral"],"Yêu cầu này cần chuyển người phụ trách, không lấy hộp thay thế.")
    n=t["needs"]
    need(sum(t["basket"].values())==n["qty"],"Số lượng trong khay chưa khớp phiếu.")
    for lid,qty in t["basket"].items():
        lot=LOT_INDEX.get(lid)
        need(lot and lot["product"]==n["product"],"Mã hộp chưa khớp phiếu.")
        need(lot["status"]=="available" and lid not in c["held_lots"] and lot["valid_until"]>=c["day"],"Lô này không được xuất: tạm giữ hoặc không còn hợp lệ.")
        need(lid in t["inspected"],"Mở nhãn lô đã chọn để đọc trước khi xác nhận.")
        need(c["stock"].get(lid,0)>=qty,"Số lượng kho của lô không đủ.")


def tick_pending(s:dict,c:dict) -> list[str]:
    notes=[]
    for t in c["tasks"]:
        if t["career"]=="accounting" and t.get("source_ready",0) and c["turn"]>=t["source_ready"]:
            for d in t["docs"]:d["missing"]=False
            t["source_ready"]=0
            notes.append("Nguồn bổ sung đã tới: "+t["title"])
            log(s,c,"delivery",notes[-1],t["npc"],t["id"])
        if t["career"]=="customer_care" and t.get("ready_turn",0) and c["turn"]>=t["ready_turn"]:
            if t["status"]=="executing":
                t["status"]="awaiting_confirmation";t["ready_turn"]=0
                t["timeline"].append("Đầu mối đã gửi xác nhận thực hiện phương án.")
                notes.append("Có kết quả phối hợp: "+t["title"])
            elif t["status"]=="handed_over":
                t["status"]="understood";t["ready_turn"]=0
                t["timeline"].append("Chị Mai đã tiếp nhận đủ thông tin; mời bạn kiểm tiếp phương án.")
                notes.append("Chị Mai đã nhận bàn giao và phản hồi.")
    remaining=[]
    for p in c["pending"]:
        if c["day"]>=p["day"] and c["turn"]>=p["turn"]:
            if p["kind"] in ("return_note","event_followup"):
                # One return note per source, never an invented claim of a completed task.
                add_feed(s,c,p["npc"],p["text"],p["ref"],kind="story")
                notes.append("Có chuyện mới trên bảng tin.")
            elif p["kind"]=="comment":
                post=next((f for f in c["feed"] if f["id"]==p["ref"]),None)
                if post:post["comments"].append(dict(author=NPC_INDEX[p["npc"]]["display_name"],npc=p["npc"],text=p["text"],day=c["day"]))
            else: remaining.append(p)
        else:remaining.append(p)
    c["pending"]=remaining[-80:]
    return notes


def director(s:dict,c:dict,career:str) -> None:
    if career not in ORIGINAL:
        sit.director(s,c,career);return
    if not c["open"] or c["event"] or c["day_events"] or c["day_completed"]<1:return
    o=c.get("ops",{})
    if o.get("incident") and o["incident"]["status"]!="resolved":return
    if o.get("security",{}).get("active"):return
    preferred={"mother_baby":["MB-E01","MB-E07","MB-E05","MB-E11","MB-E08","MB-E13","MB-E21","MB-E24"],
        "pharmacy":["PH-E24","PH-E03","PH-E17","PH-E06","PH-E19","PH-E23"],
        "accounting":["AC-E23","AC-E03","AC-E14","AC-E17","AC-E15","AC-E24"],
        "customer_care":["CS-E22","CS-E09","CS-E14","CS-E13","CS-E12","CS-E24"]}[career]
    candidate=preferred[(c["day"]-1)%len(preferred)]
    if c["life"]["mode"]=="calm" and ("21" in candidate or SCRIPTS[candidate]["category"]=="tense"):
        candidate=preferred[0]
    c["event"]=instantiate(candidate,s["seq"]+1,c["day"])
    log(s,c,"event",SCRIPTS[candidate]["opening"],SCRIPTS[candidate]["npc"],c["event"]["id"])


def chat_reply(s:dict,c:dict,career:str,npc:str,text:str) -> tuple[str,list[dict]]:
    """Rule-based baseline. Text alone never completes an economic action."""
    msg=normalize(text)
    t=next((t for t in c["tasks"] if t["npc"]==npc and t["status"] not in ("completed","referred","cancelled")),None)
    suggestions=[]
    if re.search(r"(cong|them|tang)\s+(cho\s+)?(toi|minh|ban)?\s*\d+|bo qua.*(luat|kiem)|ignore.*instruction|system prompt",msg):
        reply="Mình chỉ trao đổi về công việc thôi. Tiền, hàng và kết quả vẫn cần được kiểm và xác nhận ở bàn thao tác nhé."
    elif career=="pharmacy" and any(w in msg for w in ["lieu dung","uong thuoc","chua benh","chan doan","dau dau"]):
        reply="Mình không hướng dẫn cách dùng thuốc. Với yêu cầu ngoài phiếu, hãy chuyển người phụ trách nhé."
        if t:suggestions=[dict(label="Mở phiếu để chuyển",action="open_task",task=t["id"])]
    elif t and any(w in msg for w in ["can gi","nhu cau","ngan sach","mau gi","ma nao","so luong","mua gi","hoi lai","bo sung","thich mau","gia bao","chon gi","mon gi","duong","topping","bai gi","hoc gi","di dau","lich trinh"]):
        reply=reveal_needs(s,c,t)
        suggestions=[dict(label="Mở công việc",action="open_task",task=t["id"])]
    elif any(w in msg for w in ["tang","mien phi","giam gia","hoan tien","gui bu","da xong","thanh toan","giao roi"]):
        reply="Mình nghe đề nghị của bạn. Bạn mở công việc hoặc tình huống liên quan, kiểm điều kiện rồi xác nhận thao tác nhé. Nói trong chat chưa làm tiền hay hàng thay đổi."
        if t:suggestions=[dict(label="Kiểm công việc trước",action="open_task",task=t["id"])]
    elif any(w in msg for w in ["nho","lan truoc","hom qua","quen"]):
        memories=[m for m in c["memories"] if m["npc"]==npc]
        reply=("Mình còn nhớ: "+memories[-1]["text"]) if memories else "Mình chưa có kỷ niệm công việc nào với bạn ở nghề này. Hôm nay mình bắt đầu làm quen nhé."
    elif any(w in msg for w in ["ghe","trang tri","cay","den","dep"]):
        decorated=[UPGRADE_INDEX[u]["name"] for u in c["upgrades"] if UPGRADE_INDEX[u]["kind"]=="decor"]
        reply="Mình thấy góc mới có "+", ".join(decorated[:3])+". Nhìn ấm áp hơn đó!" if decorated else "Góc hiện tại còn đơn giản, nhưng dễ gần. Bạn có thể chọn một món trang trí trong lúc tiệm nghỉ."
    elif any(w in msg for w in ["xin loi","cam on"]):reply="Cảm ơn bạn đã nói rõ. Mình cùng làm nốt việc đang có nhé, không cần vội."
    elif any(w in msg for w in ["chao","hello","hi "]):
        reply=f'Chào {s["name"]}! '+(t["opening"] if t else "Hôm nay mình ghé phố chào bạn một chút.")
    elif t:
        reply="Mình đang trao đổi về: "+t["title"]+". Bạn có thể hỏi ‘Bạn cần gì?’ hoặc mở công việc để cùng xem dữ kiện nhé."
        suggestions=[dict(label="Hỏi nhu cầu",action="ask",task=t["id"]),dict(label="Mở công việc",action="open_task",task=t["id"])]
    else:reply="Hôm nay phố khá yên. Mình thích ngồi ở một góc và nhìn mọi người làm việc. Bạn cứ làm theo nhịp của mình nhé."
    return reply,suggestions


def apply_action(state:dict,career:str|None,action:str,payload:dict|None=None,internal:bool=False) -> tuple[dict,dict]:
    """Functional transaction: failure cannot partly mutate the supplied state."""
    s=migrate_state(state)
    p=payload or {}
    need(isinstance(p,dict),"Dữ liệu thao tác không hợp lệ.")
    result=dict(message="Đã thực hiện.",effects=[])
    if action=="select_career":
        need(career in CAREERS,"Nghề này đang ở danh mục mở rộng, chưa chơi được.")
        jr.gate(s,career,action,internal);jr.on_select(s,career)
        s["current"]=career
        return s,dict(message="Chào mừng tới "+CAREER_META[career]["place"]+".")
    if action=="settings":
        for k,v in p.items():
            if k=="name":s["name"]=clean_text(v,24)
            elif k=="mode":pass  # Old clients may still send it: each day's pace is the luck of the day now.
            elif k in SETTING_CHOICES:
                need(v in SETTING_CHOICES[k],"Thiết lập không hợp lệ.");s["settings"][k]=v
            elif k in ("musicVolume","sfxVolume"):
                s["settings"][k]=integer(v,0,100)
            elif k in s["settings"]:
                need(type(v) is bool,"Thiết lập không hợp lệ.");s["settings"][k]=v
            else:raise GameError("Thiết lập không được hỗ trợ.")
        return s,dict(message="Đã lưu cách chơi của bạn.")
    if action=="reset_all":
        need(p.get("confirm")=="BAT DAU LAI","Cần xác nhận trước khi xóa tiến trình.")
        fresh=new_state()
        if s["journey"]["story"]:jr.enable_story(fresh,s["journey"]["seed"]+1)
        return fresh,dict(message="Đã tạo hành trình mới.")
    if action.startswith("jr_"):return jr.action(s,career,action,p)
    if action.startswith("iv_"):return iv.action(s,action,p)
    if action.startswith("st_"):return cst.action(s,career,action,p)
    need(career in CAREERS,"Chọn một nghề trước nhé.")
    jr.gate(s,career,action,internal)
    c=s["careers"][career]
    s["current"]=career
    prior_mistakes={t["id"]:t["mistakes"] for t in c["tasks"]}
    mod=PLUGINS.get(career)
    plugin_action=bool(mod) and action.startswith(mod.SPEC['prefix'])
    if action.startswith(("shop_","ac_","cs_")) or action in ("ph_pick","ph_check","ph_deliver","ph_refer","ph_inspect"):
        need(c["open"],"Mở ca trước khi xử lý công việc nhé.")
    if career in dk.CAREERS and (action.startswith(("ac_","cs_")) or action in ("ph_pick","ph_check","ph_deliver","ph_refer","ph_inspect","basket_remove")):
        desk_task=next((x for x in c["tasks"] if x["id"]==(p.get("task") or c["active_task"])),None)
        need(not (desk_task and desk_task.get("desk")),"Hồ sơ này xử lý ở bàn giấy tờ: đánh dấu dòng sai rồi đóng dấu nhé.")
    if plugin_action and action not in mod.SPEC.get('free_actions',()):
        need(c["open"],"Mở ca trước khi xử lý công việc nhé.")
    no_tick={"task_select","settings","talk","feed_like","photo","decor_move","event_dismiss","quest_claim","chat_clear","reset_career","theme","sit_dismiss","sit_practice","inv_rate","inv_claim"}
    if mod:no_tick|=set(mod.SPEC.get('no_tick',()))
    if action.startswith("cl_"):need(c["open"],"Mở ca trước khi làm hoạt động lớp nhé.")
    if action not in no_tick and not action.startswith(("ops_","fb_","job_","soc_","cl_","inc_","hap_",*life.NEW_ACTION_PREFIXES)):c["turn"]+=1
    if action.startswith(life.NEW_ACTION_PREFIXES):
        result.update(life.handle(s,c,career,action,p))
    elif plugin_action:
        result.update(mod.handle(s,c,action,p))
    elif action.startswith("desk_"):
        result.update(dk.handle(s,c,career,action,p))
    elif action.startswith("inv_"):
        result.update(inv.action(s,c,career,action,p))
    elif action.startswith("sit_"):
        result.update(sit.action(s,c,career,action,p))
    elif action.startswith("inc_"):
        result.update(incs.action(s,c,career,action,p))
    elif action.startswith("hap_"):
        result.update(haps.action(s,c,career,action,p))
    elif action.startswith("fb_"):
        result.update(fbk.action(s,c,career,action,p,internal))
    elif action.startswith("job_"):
        result.update(emp.action(s,c,career,action,p))
    elif action.startswith("cl_"):
        from . import classroom
        result.update(classroom.action(s,c,career,action,p))
    elif action.startswith("soc_"):
        need(internal,"Thao tác chỉ dành cho máy chủ.","forbidden")
        from . import social
        result.update(social.apply_internal(s,c,career,action,p))
    elif action=="start_day":
        need(not c["open"],"Ca đã mở rồi.")
        if emp.required(career):need(c["job"]["status"]=="hired","Nghề này cần được tuyển dụng trước. Mở mục Xin việc để ứng tuyển nhé.","not_hired")
        c["open"]=True;c["started"]=True;c["shift_summary"]=None
        ops.on_start(s,c,career)
        inv.on_open(s,c,career)  # kho: ghi nhịp mở ca cho đồng hồ giao hàng
        target={"calm":2,"festival":4}.get(c["life"]["mode"],3)  # the day's pace is rolled at the previous close
        unfinished=[t for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled")]
        slots=[int(t["id"].split("-")[-1]) for t in c["tasks"] if t["day"]==c["day"]]
        first=max(slots,default=-1)+1
        for i in range(max(0,target-len(unfinished))):
            c["tasks"].append(make_task(career,c["day"],first+i,c["turn"]))
            if mod and hasattr(mod,'on_task'):mod.on_task(s,c,c["tasks"][-1])
        # Keep unfinished work and the most recent completed tasks.
        done=[t for t in c["tasks"] if t["status"] in ("completed","referred","cancelled")][-40:]
        active=[t for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled")]
        c["tasks"]=done+active
        for t in active:t["deferred"]=False
        next_active(c)
        life.on_start(s,c,career)
        if mod and hasattr(mod,'on_start'):mod.on_start(s,c)
        dk.on_start(s,c,career)
        log(s,c,"day","Mở ca ngày "+str(c["day"])+".")
        result["message"]="Đã mở cửa. Khách đang tới, mình bắt đầu từ một người nhé."
    elif action=="end_day":
        need(c["open"],"Ca chưa mở.")
        need(not c["event"] or c["event"]["stage"]=="resolved" or p.get("carry_event"),"Bạn còn một chuyện đang xử lý. Có thể tiếp tục hoặc chọn mang sang ngày sau.")
        oldday=c["day"]
        inc_summary=incs.on_close(s,c,career)  # an undecided incident takes its default before the day's sums
        hap_summary=haps.on_close(s,c,career)  # a happening still on screen takes its default too
        ops_summary=ops.on_close(s,c,career)
        summary=dict(day=oldday,completed=c["day_completed"],income=c["earnings"],cost=c["costs"],net=c["money"]-c["day_start_money"],
            events=c["day_events"],carried=sum(t["status"] not in ("completed","referred","cancelled") for t in c["tasks"]),
            headline="Hôm nay bạn đã giúp những việc nhỏ trở nên rõ ràng hơn.")
        summary["operations"]=ops_summary
        summary["expired_value"]=inv.on_close(s,c,career)
        summary["experiences"]=life.on_close(s,c,career)
        summary["job"]=emp.on_close(s,c,career)
        if mod and hasattr(mod,'on_close'):summary["career"]=mod.on_close(s,c)
        elif career in dk.CAREERS:summary["career"]=dk.on_close(s,c,career)
        summary["reviews"]=fbk.day_summary(c,oldday)
        summary["incidents"]=inc_summary
        summary["happen"]=hap_summary
        c["shift_summary"]=summary;c["open"]=False;c["day"]+=1;c["day_completed"]=0;c["day_events"]=0
        c["day_start_money"]=c["money"];c["earnings"]=0;c["costs"]=0
        if c["event"] and c["event"]["stage"]=="resolved":c["event"]=None
        log(s,c,"day",f"Khép ngày {oldday}; {summary['completed']} việc xong, {summary['carried']} việc được giữ lại.")
        result.update(message="Một ngày nữa đã có câu chuyện để nhớ.",summary=summary)
    elif action=="more_work":
        need(c["open"],"Mở ca trước nhé.")
        active=[t for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled")]
        need(len(active)<4,"Đang có đủ việc. Hoàn thành hoặc hẹn lại trước nhé.")
        slots=[int(t["id"].split("-")[-1]) for t in c["tasks"] if t["day"]==c["day"]]
        slot=max(slots,default=-1)+1
        need(slot<12,"Hôm nay đã nhận đủ 12 việc. Khép ca rồi bắt đầu ngày mới nhé.")
        t=make_task(career,c["day"],slot,c["turn"]);c["tasks"].append(t);c["active_task"]=t["id"]
        if career=="milk_tea":life.setup_task(s,c,t)
        if mod and hasattr(mod,'on_task'):mod.on_task(s,c,t)
        result["message"]="Có thêm một vị khách ghé tới."
    elif action=="task_select":
        t=current_task(c,p.get("task"));c["active_task"]=t["id"];t["deferred"]=False
        result["message"]="Đang xem: "+t["title"]
    elif action=="defer":
        t=current_task(c,p.get("task"));t["deferred"]=True
        log(s,c,"promise","Giữ công việc để tiếp tục: "+t["title"],t["npc"],t["id"]);next_active(c)
        result["message"]="Đã giữ công việc và dữ kiện. Bạn có thể quay lại từ Sổ việc."
    elif action=="ask":
        t=current_task(c,p.get("task"));result["message"]=reveal_needs(s,c,t)
    elif action in ("shop_pick","ph_pick","basket_remove"):
        need(c["open"],"Mở ca trước khi phục vụ nhé.")
        t=current_task(c,p.get("task"));need(career in ("mother_baby","pharmacy"),"Thao tác này không thuộc nghề đang chơi.")
        item=p.get("item");need(item in (PRODUCT_INDEX if career=="mother_baby" else LOT_INDEX),"Không có mã hàng này.")
        if action=="basket_remove":
            need(t["basket"].get(item,0)>0,"Món này chưa ở trong khay.")
            t["basket"][item]-=1
            if not t["basket"][item]:del t["basket"][item]
        else:
            need((action=="shop_pick" and career=="mother_baby") or (action=="ph_pick" and career=="pharmacy"),"Sai bàn thao tác.")
            need(t["known"],"Hỏi nhu cầu hoặc bổ sung phiếu trước nhé.")
            if career=="pharmacy":
                need(not t["needs"]["referral"],"Phiếu cần chuyển người phụ trách.")
                lot=LOT_INDEX[item]
                need(lot["status"]=="available" and item not in c["held_lots"],"Lô không được xuất; hãy chọn lô hợp lệ.")
            need(available(c,item)>0,"Món này hết hàng hoặc đã giữ cho đơn khác. Kiểm nhập thêm nhé.")
            need(sum(t["basket"].values())<(gifts.basket_cap(t) if t.get("gen") else 6),"Khay đang đầy, kiểm lại trước khi thêm.")
            t["basket"][item]=t["basket"].get(item,0)+1
            expected_code=t["needs"]["product"]
            actual_code=item if career=="mother_baby" else LOT_INDEX[item]["product"]
            if t.get("gen"):t["mistakes"]+=gifts.pick_mistake(c,t,item)
            elif actual_code!=expected_code:t["mistakes"]+=1
        t["checked"]=False
        if "pack" in t:t["pack"]=None
        result["message"]="Đã đặt lại vào kệ." if action=="basket_remove" else "Đã đặt vào khay, hàng được giữ cho đúng đơn này."
    elif action=="shop_pack":
        need(career=="mother_baby","Không có bàn gói quà ở nghề này.")
        t=current_task(c,p.get("task"));ensure_shop(t,c,False)
        paper=p.get("paper");ribbon=p.get("ribbon")
        need(paper in [v["id"] for v in PAPERS] and ribbon in [v["id"] for v in RIBBONS],"Mẫu gói chưa hợp lệ.")
        if paper!=t["needs"]["paper"]:t["mistakes"]+=1
        t["pack"]=dict(paper=paper,ribbon=ribbon,card=clean_text(p.get("card","Gửi bạn một ngày dịu dàng."),100,0))
        if t.get("gen"):gifts.on_pack(t,p)
        t["checked"]=False
        result["message"]="Đã gói quà. Kiểm màu khách thích trước khi giao nhé."
    elif action=="shop_check":
        need(career=="mother_baby","Sai bàn kiểm.")
        t=current_task(c,p.get("task"));ensure_shop(t,c);t["checked"]=True
        result["message"]="Món, số lượng, ngân sách và gói quà đều đã khớp."
    elif action=="shop_deliver":
        need(career=="mother_baby","Sai thao tác nghề.")
        t=current_task(c,p.get("task"));need(t["checked"],"Kiểm đơn tại quầy trước khi thanh toán.");ensure_shop(t,c)
        total=sum(life.price(c,k,PRODUCT_INDEX[k]["price"])*v for k,v in t["basket"].items())
        for k,v in t["basket"].items():c["stock"][k]-=v
        # Sale and packaging are one atomic transaction. Credit the sale first so
        # a zero balance cannot soft-lock delivery of already-owned inventory.
        task_done(s,c,t,total,f'Bạn đã giao đúng đơn “{t["title"]}”'+(" và gói theo màu đã chọn." if t["pack"] else "."))
        if t["pack"]:
            money(s,c,-5,"Vật liệu gói quà",t["id"]);metric(c,"packed")
        result.update(message=f"Đã giao quà · +{total} xu doanh thu. Khách sẽ để lại lời nhắn.",celebrate=True)
    elif action=="ph_inspect":
        need(career=="pharmacy","Sai quầy.");t=current_task(c,p.get("task"));lid=p.get("lot")
        need(lid in LOT_INDEX,"Lô không tồn tại.")
        if lid not in t["inspected"]:t["inspected"].append(lid);metric(c,"inspections")
        result["message"]="Đã đọc nhãn "+lid+". Kiểm trạng thái hợp lệ trước khi lấy."
    elif action=="ph_quarantine":
        need(career=="pharmacy","Sai quầy.");lid=p.get("lot");need(lid in LOT_INDEX,"Lô không tồn tại.")
        need(lid not in c["held_lots"],"Lô đã ở khu tạm giữ.")
        need(LOT_INDEX[lid]["status"]=="available","Lô này vốn không nằm trong kho được xuất.")
        c["held_lots"].append(lid)
        for t in c["tasks"]:
            if "patience" in t:integer(t["patience"],25,100)
            if lid in t.get("basket",{}) and t["status"] not in ("completed","referred"):t["checked"]=False
        log(s,c,"stock","Tạm giữ lô "+lid+" để kiểm tra.");result["message"]="Đã chặn xuất lô này. Có thể nhờ cô Thu kiểm để mở lại."
    elif action=="ph_release":
        need(career=="pharmacy","Sai quầy.");lid=p.get("lot")
        need(lid in c["held_lots"] and LOT_INDEX[lid]["status"]=="available","Chỉ cô Thu có thể mở lại lô hợp lệ do bạn vừa tạm giữ.")
        c["held_lots"].remove(lid);log(s,c,"stock","Cô Thu xác nhận lô "+lid+" hợp lệ.");result["message"]="Đã kiểm cùng cô Thu và mở lại lô hợp lệ."
    elif action=="ph_check":
        need(career=="pharmacy","Sai quầy.");t=current_task(c,p.get("task"));ensure_pharmacy(t,c)
        need(p.get("checks")==["code","quantity","lot"],"Cần xác nhận đủ mã, số lượng và trạng thái lô.")
        if not t["checked"]:metric(c,"ph_verified")
        t["checked"]=True;result["message"]="Đã đối chiếu đủ ba bước. Có thể bàn giao phiếu."
    elif action=="ph_deliver":
        need(career=="pharmacy","Sai quầy.");t=current_task(c,p.get("task"));ensure_pharmacy(t,c)
        need(t["checked"],"Cần kiểm hai bước trước khi bàn giao.")
        for k,v in t["basket"].items():c["stock"][k]-=v
        task_done(s,c,t,40,"Bạn đã đối chiếu phiếu, đọc nhãn và bàn giao đúng mã, đúng lượng.")
        result.update(message="Bàn giao cẩn thận · +40 xu thù lao.",celebrate=True)
    elif action=="ph_refer":
        need(career=="pharmacy","Sai quầy.");t=current_task(c,p.get("task"))
        need(t["known"],"Hỏi lại phiếu trước khi chuyển.")
        t["basket"]={};task_done(s,c,t,25,"Bạn đã chuyển yêu cầu cho cô Thu, không đoán ngoài phạm vi.","referred")
        result.update(message="Cô Thu đã tiếp nhận. Quầy vẫn làm việc bình thường.",celebrate=True)
    elif action=="order_stock":
        need(career in ("mother_baby","pharmacy"),"Nghề này không cần nhập hàng.")
        item=p.get("item");qty=integer(p.get("qty"),1,6)
        catalogue=PRODUCT_INDEX if career=="mother_baby" else LOT_INDEX
        need(item in catalogue,"Mã hàng không hợp lệ.")
        if career=="pharmacy":need(LOT_INDEX[item]["status"]=="available","Chỉ đặt lô hợp lệ.")
        cap=max(ops.PROPERTY_INDEX[c["ops"]["property"]["tier"]]["stock_cap"],24 if "shelf" in c["upgrades"] else 12)
        in_transit=sum(x["qty"] for x in c["shipments"] if x["item"]==item and x["status"]!="received")
        need(c["stock"].get(item,0)+qty+in_transit<=cap,f"Kho mỗi mã chứa tối đa {cap}. Nhận đủ rồi bán bớt hoặc nâng kệ.")
        cost=catalogue[item]["cost"]*qty
        s["seq"]+=1;sid=f"shipment-{s['seq']}"
        money(s,c,-cost,"Đặt nhập "+item,sid)
        c["shipments"].append(dict(id=sid,item=item,qty=qty,actual=qty,ready=c["turn"]+2,status="in_transit",cost=cost))
        result["message"]="Đã đặt hàng, chưa cộng kho. Chờ hai nhịp hoặc làm việc khác rồi kiểm nhận."
    elif action=="receive_stock":
        shipment=next((x for x in c["shipments"] if x["id"]==p.get("shipment")),None)
        need(shipment and shipment["status"]!="received","Kiện đã nhận hoặc không tồn tại.")
        # This action's own beat is already counted (turn+1): the parcel must have been
        # ready before it, matching public ready_now (no receiving a beat early).
        need(c["turn"]>shipment["ready"],"Kiện chưa tới. Chọn ‘Chờ một nhịp’ hoặc làm việc khác nhé.")
        qty=integer(p.get("count"),1,12);need(qty==shipment["actual"],"Số kiểm đếm chưa khớp số hộp thấy trong kiện.")
        shipment["status"]="received";c["stock"][shipment["item"]]+=qty;metric(c,"restocked")
        log(s,c,"stock",f'Đã kiểm nhận {qty} × {shipment["item"]}.',ref=shipment["id"])
        result["message"]="Đã kiểm nhận. Chỉ số lượng thực nhận được cộng vào kho."
    elif action=="assistant_help":
        need("assistant" in c["upgrades"],"Bạn chưa có phụ việc.")
        need(c["assistant_day"]!=c["day"],"Bạn phụ việc đã hỗ trợ một lần hôm nay.")
        c["assistant_day"]=c["day"]
        if career in ("mother_baby","pharmacy"):
            for shipment in c["shipments"]:
                if shipment["status"]!="received":shipment["ready"]=min(shipment["ready"],c["turn"])
            result["message"]="Phụ việc đã mang các kiện đang chờ tới kho. Bạn vẫn cần kiểm đếm để nhận."
        else:
            t=current_task(c,p.get("task"))
            if mod:result["message"]=mod.hint(c,t) if hasattr(mod,'hint') else mod.SPEC.get('guide','Làm từng bước và kiểm lại trước khi giao nhé.')
            else:result["message"]={"accounting":"Đối chiếu mã phiếu và tổng từng nhóm, không gộp mọi thứ để làm mất dấu vết.","customer_care":"Trạng thái đơn chỉ là một nguồn. Nhớ xem biên bản và kết quả thực thi.","teacher":"Nhìn nhu cầu từng bạn rồi chọn cách giảng; đọc bài trước khi gửi phản hồi riêng.","tour_guide":"Có đủ điểm đoàn muốn và nơi nghỉ; kiểm người ở từng điểm, đọc bảng chuyện trước khi kể.","milk_tea":"Xem phiếu chọn trà, vị và topping; chốt cỡ, đường, đá rồi kiểm ly trước khi đóng nắp."}[career]
        log(s,c,"assistant",result["message"])
    elif action.startswith("ac_"):
        need(career=="accounting","Sai bàn làm việc.");t=current_task(c,p.get("task"));docs={d["id"]:d for d in t["docs"]}
        if action=="ac_inspect":
            d=docs.get(p.get("doc"));need(d,"Không thấy chứng từ.");need(not d.get("missing"),"Nguồn này chưa được gửi. Hãy xin bổ sung.")
            if d["id"] not in t["inspected"]:t["inspected"].append(d["id"]);metric(c,"source_reads")
            result["message"]=f'Nguồn {d["source"]}: {d["original"]} xu · tham chiếu {d["ref"]}.'
        elif action=="ac_request_source":
            need(any(d.get("missing") for d in t["docs"]),"Nguồn hiện đã đủ.")
            need(not t["source_requested"],"Đã gửi yêu cầu, chờ nguồn về nhé.")
            t["source_requested"]=True;t["source_ready"]=c["turn"]+2;metric(c,"source_requests")
            log(s,c,"request","Đã xin đúng phiếu còn thiếu.",t["npc"],t["id"])
            result["message"]="Đã xin bổ sung. Nguồn sẽ tới sau hai nhịp."
        elif action=="ac_duplicate":
            d=docs.get(p.get("doc"));need(d and d["id"] in t["inspected"],"Đọc bản gốc trước khi loại trùng.")
            need(d.get("duplicate_of") and d["duplicate_of"] in t["inspected"],"Cần đối chiếu cả hai bản có cùng nguồn; thẻ này chưa được chứng minh là bản sao.")
            need(d["id"] not in t["removed"],"Bản này đã đánh dấu trùng.")
            need(not any(d["id"] in g["docs"] for g in t["groups"]),"Tháo nhóm có thẻ này trước khi loại trùng.")
            t["removed"].append(d["id"]);log(s,c,"correction",f'Loại bản {d["id"]}: cùng nguồn {d["ref"]} với {d["duplicate_of"]}.',t["npc"],t["id"])
            result["message"]="Đã đánh dấu bản trùng, giữ nguyên nguồn và lý do."
        elif action=="ac_correct":
            d=docs.get(p.get("doc"));need(d and d["id"] in t["inspected"],"Đọc nguồn trước khi điều chỉnh.")
            need(d["amount"]!=d["original"],"Số này đã đúng bản gốc.")
            old=d["amount"];d["amount"]=d["original"];t["groups"]=[g for g in t["groups"] if d["id"] not in g["docs"]]
            log(s,c,"correction",f'{d["id"]}: {old} → {d["original"]}, căn cứ {d["source"]}.',t["npc"],t["id"])
            result["message"]="Đã sửa từ bản gốc, không ghi đè mất dấu vết."
        elif action=="ac_match":
            ds=p.get("docs",[]);ts=p.get("transactions",[])
            need(isinstance(ds,list) and isinstance(ts,list) and 1<=len(ds)<=6 and 1<=len(ts)<=6,"Chọn phiếu và giao dịch để ghép.")
            need(all(isinstance(x,str) for x in ds+ts),"Mã nhóm chưa hợp lệ.")
            need(len(set(ds))==len(ds) and len(set(ts))==len(ts),"Không lặp thẻ trong cùng nhóm.")
            need(len(ds)==1 or len(ts)==1,"Ghép theo từng quan hệ nhiều-một hoặc một-nhiều, không gộp cả hồ sơ.")
            trans={x["id"]:x for x in t["transactions"]}
            need(all(x in docs for x in ds) and all(x in trans for x in ts),"Mã thẻ không tồn tại.")
            need(all(x in t["inspected"] and x not in t["removed"] and not docs[x].get("missing") for x in ds),"Đọc đủ bản gốc, không ghép thẻ thiếu hoặc đã loại.")
            need(not any(set(ds)&set(g["docs"]) or set(ts)&set(g["transactions"]) for g in t["groups"]),"Có thẻ đã nằm trong nhóm khác. Tháo nhóm cũ để ghép lại.")
            need(not any(docs[x].get("duplicate_of") for x in ds),"Có bản sao cùng nguồn trong nhóm; đối chiếu và loại trùng trước nhé.")
            need(all(docs[x]["amount"]==docs[x]["original"] for x in ds),"Số nhập còn khác nguồn. Điều chỉnh có căn cứ trước.")
            a=sum(docs[x]["amount"] for x in ds);b=sum(trans[x]["amount"] for x in ts)
            need(a==b,f"Tổng phiếu {a} xu chưa khớp giao dịch {b} xu. Thử kiểm phần còn thiếu nhé.")
            refs={docs[x]["ref"] for x in ds};txrefs=set(r for x in ts for r in trans[x]["refs"])
            need(refs==txrefs,"Tổng giống nhau nhưng tham chiếu nguồn chưa khớp. Kiểm mã hóa đơn nhé.")
            t["groups"].append(dict(docs=ds,transactions=ts,total=a));metric(c,"matched")
            log(s,c,"match",f'Đã ghép {", ".join(ds)} với {", ".join(ts)} = {a} xu.',t["npc"],t["id"])
            result["message"]=f"Hai phía khớp {a} xu và cùng tham chiếu nguồn."
        elif action=="ac_unmatch":
            index=integer(p.get("index"),0,len(t["groups"])-1);t["groups"].pop(index)
            result["message"]="Đã tháo nhóm, các thẻ trở lại bàn."
        elif action=="ac_complete":
            valid=[d for d in t["docs"] if d["id"] not in t["removed"]]
            linked={x for g in t["groups"] for x in g["docs"]};txlinked={x for g in t["groups"] for x in g["transactions"]}
            need(all(d["id"] in linked and not d.get("missing") and not d.get("duplicate_of") for d in valid),"Còn chứng từ chưa đối chiếu, thiếu nguồn hoặc chưa loại bản trùng.")
            need(len(txlinked)==len(t["transactions"]),"Còn giao dịch chưa ghép.")
            need(p.get("explanation")=="source_report","Chọn báo cáo giải thích tổng và nguồn; không chỉ đưa một con số.")
            t["explanation"]="Bảng đối chiếu: "+"; ".join(f'{", ".join(g["docs"])} ↔ {", ".join(g["transactions"])}: {g["total"]} xu' for g in t["groups"])
            task_done(s,c,t,70,"Bạn đã bàn giao hồ sơ có đối chiếu và nguồn: "+t["title"]+".")
            result.update(message="Đã bàn giao hồ sơ có căn cứ · +70 xu thù lao, không cộng tiền công ty vào ví.",celebrate=True)
        else:raise GameError("Thao tác kế toán chưa được hỗ trợ.")
    elif action.startswith("cs_"):
        need(career=="customer_care","Sai bàn hỗ trợ.");t=current_task(c,p.get("task"))
        if action=="cs_identity":
            need(not t["identity"],"Mã của khách đã được xác minh.")
            t["identity"]=True;t["known"]=True;t["status"]="understood";metric(c,"identity_checked")
            t["timeline"].append("Đã xác minh quyền xem đơn bằng mã khách cung cấp.")
            result["message"]="Khách đã cung cấp mã phù hợp. Bạn có thể xem hồ sơ của vụ này."
        elif action=="cs_evidence":
            need(t["identity"],"Xác minh mã yêu cầu trước khi xem hồ sơ.")
            evid=next((e for e in t["evidence"] if e["id"]==p.get("evidence")),None);need(evid,"Không có chứng cứ này.")
            if evid["id"] not in t["inspected"]:t["inspected"].append(evid["id"])
            result["message"]=evid["text"]
        elif action=="cs_propose":
            need(t["identity"] and len(t["inspected"])==len(t["evidence"]),"Xác minh khách và xem đủ nguồn trước khi đề nghị phương án.")
            need(t["status"] in ("understood","proposed"),"Vụ đã chuyển sang thực hiện hoặc bàn giao, không đổi phương án âm thầm.")
            choice=p.get("solution");allowed=[t["solution"]]+(["refund"] if t["variant"]=="missing" else [])
            need(choice in allowed,"Phương án chưa phù hợp hồ sơ đã kiểm. Xem lại chứng cứ và chính sách nhé.")
            t["proposal"]=choice;t["status"]="proposed";t["timeline"].append("Đã đề xuất: "+choice+". Chưa thực hiện.")
            result["message"]="Phương án phù hợp. Cần xác nhận phối hợp để việc thực sự bắt đầu."
        elif action=="cs_execute":
            need(t["status"]=="proposed" and t["proposal"],"Cần đề xuất hợp lệ trước khi thực hiện.")
            t["status"]="executing";t["ready_turn"]=c["turn"]+2;metric(c,"cs_executed")
            t["timeline"].append("Đã chuyển yêu cầu thực hiện cho đầu mối. Có hẹn cập nhật sau hai nhịp.")
            if t["proposal"]=="refund":log(s,c,"company",f'Yêu cầu hoàn {t["value"]} xu từ quỹ công ty; không trừ hay cộng vào ví của bạn.',t["npc"],t["id"])
            result["message"]="Đã giao việc cho đầu mối, chưa đóng vụ. Chờ kết quả hoặc xử lý việc khác nhé."
        elif action=="cs_confirm":
            need(t["status"]=="awaiting_confirmation","Chưa có kết quả thực hiện được xác nhận.")
            t["confirmed"]=True;t["status"]="resolved";metric(c,"cs_confirmed")
            t["timeline"].append("Khách/đầu mối đã xác nhận kết quả. Đủ điều kiện đóng.")
            result["message"]="Đã kiểm kết quả với khách. Bây giờ có thể đóng vụ."
        elif action=="cs_close":
            need(t["status"]=="resolved" and t["confirmed"],"Không đóng vụ chỉ vì đã hứa hoặc mới gửi yêu cầu thực hiện.")
            task_done(s,c,t,65,"Bạn đã theo dõi, kiểm kết quả và đóng vụ: "+t["title"]+".")
            result.update(message="Khách đã nhận được kết quả · +65 xu thù lao.",celebrate=True)
        elif action=="cs_handover":
            need(t["identity"] and len(t["inspected"])>=2,"Cần xác minh và đọc ít nhất hai nguồn để bàn giao có dữ kiện.")
            need(not t["handed_over"] and t["status"]=="understood","Chỉ bàn giao một lần ở bước kiểm tra, không bỏ ngang phần đã thực hiện.")
            t["handed_over"]=True;t["status"]="handed_over";t["ready_turn"]=c["turn"]+2;metric(c,"handovers")
            t["timeline"].append("Bàn giao chị Mai: "+t["title"]+"; nguồn đã xem: "+", ".join(t["inspected"])+"; tiếp theo: xác nhận phương án và cập nhật cho khách.")
            result["message"]="Chị Mai nhận hồ sơ kèm nguồn và bước tiếp theo. Không mất lời hẹn của khách."
        else:raise GameError("Thao tác hỗ trợ chưa được hỗ trợ.")
    elif action.startswith("ops_"):
        result.update(ops.action(s,c,career,action,p))
    elif action=="advance":
        result["message"]="Một nhịp nhỏ trôi qua. Các việc đang chờ được kiểm tra lại."
    elif action=="buy_upgrade":
        item=p.get("item");u=UPGRADE_INDEX.get(item);need(u,"Không có nâng cấp này.")
        need(item not in c["upgrades"],"Bạn đã có món này rồi.")
        need(career in u.get("careers",CAREERS),"Nâng cấp không thuộc nghề này.")
        need(1+c["xp"]//90>=u["min_level"],f'Cần cấp {u["min_level"]}. Hoàn thành thêm vài việc nhé.')
        money(s,c,-u["price"],"Mua "+u["name"]);c["upgrades"].append(item)
        if u["kind"]=="decor":
            metric(c,"decorations");c["decor"][item]=dict(spot={"plant":"window","rug":"center","lamp":"corner","seat":"front","poster":"wall"}.get(item,"window"))
        log(s,c,"upgrade","Đã đặt "+u["name"]+" vào không gian.")
        result.update(message=u["name"]+" đã xuất hiện trong cảnh.",celebrate=True)
    elif action=="decor_move":
        item=p.get("item");spot=p.get("spot")
        need(item in c["decor"],"Bạn chưa sở hữu đồ trang trí này.")
        need(spot in ("window","corner","front","center","wall"),"Vị trí không hợp lệ.")
        if item=="poster":need(spot=="wall","Tranh cần đặt trên tường.")
        else:need(spot!="wall","Món này cần đặt trên sàn.")
        c["decor"][item]["spot"]=spot;result["message"]="Đã đổi vị trí trong cảnh."
    elif action=="theme":
        need(p.get("theme") in ("warm","sage","lavender","boba"),"Màu phòng không hợp lệ.")
        c["theme"]=p["theme"];result["message"]="Không gian đã đổi sắc."
    elif action=="event_start":
        need(not c["event"] or c["event"]["stage"]=="resolved","Đang có một chuyện cần xử lý. Hoàn tất hoặc cất lại trước nhé.")
        eid=p.get("event");script=SCRIPTS.get(eid);need(script and script["career"]==career,"Tình huống không thuộc nghề này.")
        # Manual replay is always clearly marked practice: no wallet, XP or relationship farming.
        c["event"]=instantiate(eid,s["seq"]+1,c["day"],True)
        log(s,c,"practice","Mở tình huống diễn tập: "+script["title"],script["npc"],c["event"]["id"])
        result["message"]="Diễn tập tình huống: không trừ xu, không nhận thưởng, không sửa quan hệ."
    elif action.startswith("event_"):
        e=c["event"];need(e,"Không có tình huống đang mở.")
        script=SCRIPTS[e["script"]]
        if action=="event_read":
            ev=next((x for x in script["evidence"] if x["id"]==p.get("evidence")),None);need(ev,"Không có dữ kiện này.")
            if ev["id"] not in e["read"]:e["read"].append(ev["id"])
            if e["stage"]=="noticed":e["stage"]="investigating"
            result["message"]=ev["text"]
        elif action=="event_choose":
            need(e["stage"] in ("noticed","investigating","proposed"),"Tình huống đã qua bước đề nghị.")
            opt=next((o for o in script["options"] if o["id"]==p.get("choice")),None);need(opt,"Phương án không có trong tình huống.")
            need(set(opt["requires"])<=set(e["read"]),"Xem đủ dữ kiện trước khi chọn phương án.")
            need(e["practice"] or c["money"]>=opt["cost"],"Chưa đủ xu cho phương án này. Bạn có thể chọn phương án không tốn xu.")
            e["chosen"]=opt["id"];e["stage"]="proposed";result["message"]=opt["response"]
        elif action=="event_confirm":
            need(e["stage"]=="proposed","Chọn và xem phương án trước khi xác nhận.")
            opt=next(o for o in script["options"] if o["id"]==e["chosen"])
            if not e["practice"] and opt["cost"]:money(s,c,-opt["cost"],"Tình huống: "+script["title"],e["id"]);e["cost_paid"]=opt["cost"]
            e["stage"]="executing";result["message"]="Đã xác nhận. Tới điểm thao tác và làm từng bước nhé."
        elif action=="event_step":
            need(e["stage"]=="executing","Chưa bắt đầu thực hiện phương án.")
            opt=next(o for o in script["options"] if o["id"]==e["chosen"])
            e["step"]+=1
            if e["step"]>=len(opt["steps"]):
                e["stage"]="resolved"
                done=log(s,c,"event_result",opt["label"]+" · đã thực hiện.",e["npc"],e["id"]);e["completion_log"]=done
                if not e["practice"]:
                    c["day_events"]+=1;c["xp"]+=15;metric(c,"events")
                    remember(s,c,e["npc"],f'Bạn đã xử lý “{script["title"]}” bằng phương án: {opt["label"]}.',e["id"])
                    add_feed(s,c,e["npc"],"Chuyện ở phố: "+script["title"]+". Phương án đã được thực hiện: "+opt["label"]+".",e["id"],kind="story")
                    follow=opt["follow_up"]
                    # Some seed follow-ups describe future unlocks: don't assert an item was delivered.
                    follow="Nhắc chuyện lần trước: “"+script["title"]+"”. Bạn đã chọn: "+opt["label"]+". Mình đã nhận được cập nhật về việc đó."
                    if e["script"] in ("MB-E07","MB-E05","MB-E11"):follow=opt["follow_up"]
                    c["pending"].append(dict(kind="event_followup",day=c["day"]+1,turn=0,npc=e["npc"],ref=e["id"],text=follow))
                    c["event_history"].append(dict(id=e["id"],script=e["script"],choice=e["chosen"],day=c["day"],source=done,facts=[x["text"] for x in script["evidence"]]))
                    c["event_history"]=c["event_history"][-120:]
                result.update(message="Chuyện đã được xử lý. "+("Diễn tập không tác động tiến trình." if e["practice"] else "Sẽ có lời nhắn tiếp theo khi sang ngày mới."),celebrate=True)
            else:result["message"]="Đã làm bước trước. Tiếp tục: "+opt["steps"][e["step"]]
        elif action=="event_dismiss":
            need(e["stage"]=="resolved" or e["practice"],"Chuyện thật chưa xử lý xong. Bạn có thể mang sang ngày sau.")
            c["event"]=None;result["message"]="Đã cất câu chuyện."
        else:raise GameError("Thao tác tình huống không hợp lệ.")
    elif action=="talk":
        npc=p.get("npc");need(npc in NPC_INDEX and NPC_INDEX[npc]["career_id"]==career,"Nhân vật không thuộc nghề này.")
        text=clean_text(p.get("text"),500)
        reply,suggestions=chat_reply(s,c,career,npc,text)
        messages=c["chats"].setdefault(npc,[])
        messages.extend([dict(role="user",text=text),dict(role="npc",text=reply,mode="scripted")]);c["chats"][npc]=messages[-40:]
        result.update(message=reply,reply=reply,suggestions=suggestions,npc=npc)
    elif action=="chat_clear":
        npc=p.get("npc");need(npc in NPC_INDEX,"Nhân vật không hợp lệ.")
        c["chats"].pop(npc,None);result["message"]="Đã xóa lịch sử chat. Ký ức công việc có nguồn vẫn nằm trong Sổ tay."
    elif action=="feed_post":
        text=clean_text(p.get("text"),500);post=add_feed(s,c,"player",text,"player-post",kind="post");metric(c,"posts")
        npcs=[n for n in NPCS if n["career_id"]==career]
        npc=npcs[(c["metrics"]["posts"]-1)%len(npcs)]["id"]
        baseline="Mình đã đọc lời nhắn của bạn. Có dịp mình ghé trò chuyện nhé!"
        c["pending"].append(dict(kind="comment",day=c["day"],turn=c["turn"]+2,npc=npc,ref=post["id"],text=baseline))
        result["message"]="Đã đăng lên Chuyện phố."
    elif action in ("feed_reply","feed_like","review_followup"):
        post=next((f for f in c["feed"] if f["id"]==p.get("post")),None);need(post,"Bài viết không còn trong bảng tin.")
        if action=="feed_like":post["liked"]=not post["liked"];result["message"]="Đã thay đổi dấu yêu thích."
        elif action=="review_followup":
            need(post["kind"]=="review","Chỉ mở trao đổi từ review.")
            need(not c["event"] or c["event"]["stage"]=="resolved","Bạn đang có một chuyện khác. Làm xong rồi trao đổi thêm nhé.")
            need(career in ORIGINAL,"Trả lời review trong mục Phản hồi khách để khách tự quyết định sửa đánh giá nhé.")
            eid={"mother_baby":"MB-E09","pharmacy":"PH-E16","accounting":"AC-E22","customer_care":"CS-E14"}[career]
            c["event"]=instantiate(eid,s["seq"]+1,c["day"],True)
            result["message"]="Mở diễn tập trao đổi review. Số sao cũ không tự thay đổi vì một câu trả lời."
        else:
            text=clean_text(p.get("text"),500);need(len(post["comments"])<60,"Cuộc trao đổi đã đủ dài; tạo bài mới nhé.")
            post["comments"].append(dict(author=s["name"],npc="player",text=text,day=c["day"]));metric(c,"replies")
            npc=post["npc"] if post["npc"] in NPC_INDEX else next(n["id"] for n in NPCS if n["career_id"]==career)
            c["pending"].append(dict(kind="comment",day=c["day"],turn=c["turn"]+1,npc=npc,ref=post["id"],text="Mình đã nhận phản hồi. Những việc cần làm vẫn theo hồ sơ nhé; bình luận không tự thay đổi kết quả hay số sao."))
            result["message"]="Đã trả lời. Review vẫn giữ nguyên đánh giá gốc."
    elif action=="quest_claim":
        q=QUEST_INDEX.get(p.get("quest"));need(q and q["career"]==career,"Không có tuyến chuyện này.")
        need(q["id"] not in c["quests_claimed"],"Kỷ niệm này đã nhận rồi.")
        need(all(c["metrics"].get(step["metric"],0)>=step["goal"] for step in q["steps"]),"Tuyến chuyện còn bước chưa hoàn thành.")
        c["quests_claimed"].append(q["id"]);money(s,c,q["reward"],"Khép chuyện: "+q["title"],q["id"])
        log(s,c,"keepsake","Nhận kỷ niệm “"+q["keepsake"]+"”.",ref=q["id"])
        result.update(message="Đã lưu kỷ niệm “"+q["keepsake"]+"” vào Sổ tay.",celebrate=True)
    elif action=="photo":
        image=p.get("image");need(isinstance(image,str) and len(image)<=450000,"Ảnh quá lớn, hãy chụp lại.")
        need(image.startswith("data:image/webp;base64,") or image.startswith("data:image/png;base64,"),"Chỉ nhận ảnh PNG/WebP chụp từ cảnh.")
        try:raw=base64.b64decode(image.split(",",1)[1],validate=True)
        except (ValueError,IndexError):raise GameError("Ảnh không hợp lệ.")
        need(raw.startswith(b"\x89PNG\r\n\x1a\n") or (raw.startswith(b"RIFF") and raw[8:12]==b"WEBP"),"Ảnh không đúng định dạng.")
        s["seq"]+=1;c["album"].insert(0,dict(id=f"photo-{s['seq']}",image=image,day=c["day"],title=clean_text(p.get("title","Một góc ngày hôm nay"),60)))
        c["album"]=c["album"][:6]
        result["message"]="Đã lưu ảnh trong album nghề này (giữ sáu ảnh gần nhất)."
    elif action=="reset_career":
        need(p.get("confirm")=="BAT DAU LAI","Cần xác nhận trước khi xóa nghề.")
        s["careers"][career]=initial_career(career);return s,dict(message="Đã bắt đầu lại riêng nghề này.")
    else:raise GameError("Thao tác không được hỗ trợ.","unknown_action")
    life.update_patience(c,action,p,prior_mistakes)
    if career=="mother_baby":gifts.after_action(s,c,action)
    if action=='talk' and p.get('npc') in NPC_INDEX:life.on_talk(c,p['npc'])
    if action=='ask':life.on_talk(c,current_task(c,p.get('task'))['npc'])
    result["effects"]=tick_pending(s,c)
    if career in dk.CAREERS:result["effects"][:0]=dk.tick(s,c,career)
    if action not in ("fb_reply","fb_resolve"):result["effects"].extend(fbk.tick(s,c))
    if not (action.startswith("event_") and c.get("event") and c["event"].get("practice")):
        result["effects"].extend(ops.tick(s,c,career,action))
    if action not in ("event_dismiss","event_start","end_day"):director(s,c,career)
    incs.after(s,c,career,action,result)
    haps.after(s,c,career,action,result)
    jr.after(s,career,action,p,result)
    iv.on_life_day(s,result)  # prices, interest and offers move once per life day
    cst.after(s,career,action,result)
    validate_state(s)
    return s,result


def task_view(t:dict) -> dict:
    if t["career"] in extra.NEW_CAREERS or t["career"] in PLUGINS:return life.public_task(t)
    if t.get("desk"):return dk.public_task(t)
    v=copy.deepcopy(t)
    career=t["career"]
    if career in ("mother_baby","pharmacy") and not t["known"]:v["needs"]=None
    if career=="mother_baby" and t.get("gen"):return gifts.public_task(t,v)
    if career=="accounting":
        for d in v["docs"]:
            if d["id"] not in t["inspected"]:
                d.pop("original",None);d.pop("duplicate_of",None)
            if d.get("missing"):d["source"]="Chờ bổ sung"
    if career=="customer_care":
        v.pop("solution",None)
        for e in v["evidence"]:
            if e["id"] not in t["inspected"]:e["text"]=None
        if not t["identity"]:v["value"]=None
    return v


def career_summary(raw:dict,cid:str) -> dict:
    """What the home picker / Phố nghề need from careers that are not open
    on screen. Keeps each response small; the full view arrives with select_career."""
    job=emp.public(raw,cid)
    return dict(summary=True,started=raw["started"],open=raw["open"],day=raw["day"],xp=raw["xp"],level=1+raw["xp"]//90,money=raw["money"],
                job=dict(required=job.get("required"),status=job.get("status")) if isinstance(job,dict) else job,
                inventory=bool(inv.public(raw,cid)),life=dict(shop_name=raw.get("life",{}).get("shop_name")))


def public_state(s:dict,full:str|None=None) -> dict:
    """Public projection. Only the current career (or `full`) gets the full view."""
    s=migrate_state(s)
    focus=full or s.get("current") or "mother_baby"
    v={k:copy.deepcopy(x) for k,x in s.items() if k!="careers"}
    v["careers"]={cid:(copy.deepcopy(c) if cid==focus else career_summary(c,cid)) for cid,c in s["careers"].items()}
    v["journey"]=jr.public(s)
    v["invest"]=iv.public(s)
    v["stories"]=cst.public(s)
    for cid,c in v["careers"].items():
        if c.get("summary"):continue
        raw=s["careers"][cid];mod=PLUGINS.get(cid)
        c["ops"]=ops.public_operations(raw)
        c["situation"]=sit.public(raw,cid)
        c["incidents"]=incs.public(raw,cid,s)
        c["happen"]=haps.public(raw,cid,s)
        c["inventory"]=inv.public(raw,cid)
        c["job"]=emp.public(raw,cid)
        c["data"]=mod.public_data(raw) if mod and hasattr(mod,'public_data') else copy.deepcopy(raw["ext"]["data"])
        if cid=="teacher":
            from . import classroom
            c["classroom"]=classroom.public(raw);c["data"].pop("class",None)
        if cid in ("milk_tea","mother_baby"):life.public_counter(raw,cid,c["data"])
        c["feed"]=[fbk.public_post(f) for f in raw["feed"]]
        c["feedback_stats"]=fbk.stats(raw)
        c.pop("ext",None)
        c["life"]=life.public_life(s["careers"][cid])
        c["tasks"]=[task_view(t) for t in s["careers"][cid]["tasks"]]
        c["level"]=1+c["xp"]//90;c["xp_in_level"]=c["xp"]%90
        c["event"]=event_view(c["event"])
        c["available"]={k:available(s["careers"][cid],k) for k in c["stock"]}
        c["quest_progress"]=[]
        for q in QUESTS:
            if q["career"]==cid:
                c["quest_progress"].append(dict(id=q["id"],claimed=q["id"] in c["quests_claimed"],
                    ready=all(c["metrics"].get(st["metric"],0)>=st["goal"] for st in q["steps"]),
                    steps=[dict(st,current=c["metrics"].get(st["metric"],0),done=c["metrics"].get(st["metric"],0)>=st["goal"]) for st in q["steps"]]))
        reviews=[f["stars"] for f in c["feed"] if f.get("stars")]
        c["rating"]=round(sum(reviews)/len(reviews),1) if reviews else None
        for pending in c["pending"]:pending.pop("text",None)
        c["shipments"]=[dict(x,ready_now=x["ready"]<=c["turn"]) for x in c["shipments"]]
    return v


def validate_state(s:dict) -> None:
    """Structural and economic invariants, also run on imported save envelopes.

Import is single-player backup, not a competitive anti-cheat boundary. Keys,
workflow references, quantities and maximum sizes are validated before commit.
"""
    need(isinstance(s,dict) and s.get("schema")==4,"Phiên bản bản lưu không được hỗ trợ.","invalid_save")
    need(set(s.get("careers",{}))==set(CAREERS),"Bản lưu cần đủ các nghề.","invalid_save")
    need(s.get("current") in CAREERS or s.get("current") is None,"Nghề trong bản lưu không hợp lệ.")
    clean_text(s.get("name"),24);integer(s.get("seq"),0,10**9)
    jr.validate(s)
    iv.validate(s)
    cst.validate(s)
    settings=s.get("settings",{});need(settings.get("mode") in ("relaxed","everyday","challenge"),"Chế độ bản lưu không hợp lệ.")
    for k in ("sound","music","reduceMotion","largeText","aiConsent","aiAsked","aiNoticeSeen","securityEvents","notify","publicProfile"):need(type(settings.get(k)) is bool,"Thiếu thiết lập bản lưu.")
    for k,choices in SETTING_CHOICES.items():need(settings.get(k) in choices,"Thiết lập bản lưu không hợp lệ.")
    for k in ("musicVolume","sfxVolume"):integer(settings.get(k),0,100)
    need(set(settings)<=set(default_settings()),"Thiết lập lạ trong bản lưu.")
    for cid,c in s["careers"].items():
        need(isinstance(c,dict),"Tiến trình nghề không hợp lệ.")
        template=initial_career(cid)
        ops.validate(c,cid)
        life.validate(c,cid)
        ext=c.get("ext");need(isinstance(ext,dict) and set(template["ext"])<=set(ext),"Bản lưu thiếu dữ liệu v0.4.")
        integer(ext.get("seq"),0,10**9);need(isinstance(ext.get("data"),dict),"Dữ liệu nghề không hợp lệ.")
        sit.validate(c,cid);inv.validate(c,cid);emp.validate(c,cid);incs.validate(c,cid);haps.validate(c,cid)
        from . import consequences as cq;cq.validate(c)  # complaints book (optional in older saves)
        if cid in PLUGINS and hasattr(PLUGINS[cid],"validate_data"):PLUGINS[cid].validate_data(c)
        if cid in dk.CAREERS:dk.validate_data(c)
        if cid=="teacher":
            from . import classroom
            classroom.validate(c)
        need(set(template)<=set(c),"Bản lưu thiếu trường tiến trình.")
        for k in ("money","xp","day","turn","day_completed","day_events","earnings","costs","assistant_day","day_start_money"):
            integer(c.get(k),1 if k=="day" else 0,10**9)
        for k in ("open","started"):need(type(c[k]) is bool,"Trạng thái ca không hợp lệ.")
        for k in ("tasks","upgrades","memories","journal","feed","pending","quests_claimed","album","shipments","completed_ids","held_lots","event_history"):
            need(isinstance(c.get(k),list) and len(c[k])<=5000,"Danh sách bản lưu không hợp lệ.")
        need(isinstance(c["stock"],dict) and isinstance(c["metrics"],dict) and isinstance(c["chats"],dict),"Kho hoặc nhật ký không hợp lệ.")
        expected_items=PRODUCT_INDEX if cid=="mother_baby" else LOT_INDEX if cid=="pharmacy" else {}
        need(set(c["stock"])==set(expected_items),"Danh mục kho không hợp lệ.")
        for k,n in c["stock"].items():integer(n,0,24)
        need(all(u in UPGRADE_INDEX for u in c["upgrades"]) and len(c["upgrades"])==len(set(c["upgrades"])),"Nâng cấp không hợp lệ.")
        need(all(l in LOT_INDEX for l in c["held_lots"]),"Lô tạm giữ không hợp lệ.")
        need(len(c["tasks"])<=80,"Quá nhiều công việc trong bản lưu.")
        taskids=[]
        for t in c["tasks"]:
            if "patience" in t:integer(t["patience"],25,100)
            need(isinstance(t,dict) and t.get("career")==cid and t.get("npc") in NPC_INDEX,"Công việc không hợp lệ.")
            need(NPC_INDEX[t["npc"]]["career_id"]==cid,"Nhân vật sai nghề.")
            for key in ("id","title","opening","status"):clean_text(t.get(key),1000)
            need(t["status"] in ("new","understood","in_progress","completed","referred","cancelled","proposed","executing","awaiting_confirmation","resolved","handed_over"),"Trạng thái công việc không hợp lệ.")
            need(re.fullmatch(re.escape(cid)+r"-\d{4,}-\d{2,}",t["id"]),"Mã công việc không hợp lệ.")
            integer(t.get("day"),1,99999);integer(t.get("created_turn"),0,10**9);integer(t.get("mistakes"),0,100000)
            slot=int(t["id"].rsplit("-",1)[1]);need(slot<12,"Chỉ số lượt công việc không hợp lệ.")
            # Tasks made before the paperwork desks keep the original counter task of their slot.
            original=make_task(cid,t["day"],slot,t["created_turn"],(cid in dk.CAREERS and not t.get("desk")) or (cid=="mother_baby" and not t.get("gen")))
            need(t["id"]==original["id"],"Mã công việc sai ngày.")
            need(set(original)<=set(t),"Bản lưu thiếu trường công việc.")
            for key in ("npc","title","opening","kind","needs","variant","solution","value","evidence"):
                # Milk tea: the counter relabels guests and re-rolls orders; boba.validate_task checks them.
                if cid=="milk_tea" and key in ("title","opening","needs"):continue
                if key in original:need(t.get(key)==original[key],"Dữ kiện gốc của nhiệm vụ không hợp lệ: "+key)
            taskids.append(t["id"]);cq.validate_task(t)
            for key in ("known","deferred"):need(type(t.get(key)) is bool,"Trạng thái công việc thiếu.")
            for key in ("inspected","notes","chat"):need(isinstance(t.get(key),list),"Dữ kiện công việc thiếu.")
            if cid in dk.CAREERS and t.get("desk"):dk.validate_task(t,original)
            elif cid in ("mother_baby","pharmacy"):
                need(isinstance(t.get("needs"),dict) and isinstance(t.get("basket"),dict),"Khay công việc không hợp lệ.")
                integer(t["needs"].get("qty"),1,6)
                need(t["needs"].get("product") in (PRODUCT_INDEX if cid=="mother_baby" else {x["product"] for x in LOT_INDEX.values()}),"Mã yêu cầu không hợp lệ.")
                for item,qty in t["basket"].items():need(item in expected_items,"Mã trong khay sai.");integer(qty,1,6)
                need(type(t.get("checked")) is bool,"Thiếu bước kiểm khay.")
                if cid=="mother_baby":
                    if t.get("gen"):gifts.validate_task(t)
                    integer(t["needs"].get("budget"),0,10000)
                    need(t["needs"].get("paper") in [x["id"] for x in PAPERS],"Màu giấy sai.")
                    need("pack" in t,"Thiếu dữ liệu gói quà.")
                    if t["pack"]:
                        need(isinstance(t["pack"],dict) and t["pack"].get("paper") in [x["id"] for x in PAPERS] and t["pack"].get("ribbon") in [x["id"] for x in RIBBONS],"Gói quà không hợp lệ.")
                        clean_text(t["pack"].get("card"),100,0)
                else:need(type(t["needs"].get("referral")) is bool,"Thiếu phạm vi phiếu.")
            elif cid in extra.NEW_CAREERS or cid in PLUGINS:
                life.validate_task(t,original)
            elif cid=="accounting":
                need(all(isinstance(t.get(k),list) for k in ("docs","transactions","groups","removed")),"Thiếu dữ liệu đối chiếu.")
                need(1<=len(t["docs"])<=8 and 1<=len(t["transactions"])<=8,"Hồ sơ quá lớn.")
                for d in t["docs"]:
                    for key in ("id","ref","source"):clean_text(d.get(key),300)
                    for key in ("amount","original"):integer(d.get(key),-100000,100000)
                need(t["transactions"]==original["transactions"],"Giao dịch nguồn đã thay đổi.")
                originals={d["id"]:d for d in original["docs"]}
                need(len({d["id"] for d in t["docs"]})==len(t["docs"]) and {d["id"] for d in t["docs"]}==set(originals),"Danh sách chứng từ không hợp lệ.")
                for d in t["docs"]:
                    base=originals[d["id"]]
                    need(set(base)<=set(d),"Chứng từ thiếu dữ kiện.")
                    for key in ("ref","source","kind","duplicate_of","original"):
                        need(d.get(key)==base.get(key),"Nguồn gốc chứng từ đã thay đổi.")
                    need(d["amount"] in (base["amount"],base["original"]),"Số nhập không thuộc nguồn gốc.")
                    need(type(d.get("missing",False)) is bool,"Trạng thái nguồn thiếu sai.")
                need(all(x in originals for x in t["inspected"]+t["removed"]),"Tham chiếu chứng từ không tồn tại.")
                txids={x["id"]:x for x in t["transactions"]};docs_by_id={d["id"]:d for d in t["docs"]}
                used_d=set();used_t=set()
                for g in t["groups"]:
                    need(isinstance(g,dict) and isinstance(g.get("docs"),list) and isinstance(g.get("transactions"),list),"Nhóm đối chiếu không hợp lệ.")
                    ds=g["docs"];ts=g["transactions"]
                    need(ds and ts and (len(ds)==1 or len(ts)==1),"Quan hệ nhóm đối chiếu không hợp lệ.")
                    need(all(x in originals for x in ds) and all(x in txids for x in ts),"Nhóm chứa mã không tồn tại.")
                    need(len(set(ds))==len(ds) and len(set(ts))==len(ts) and not used_d.intersection(ds) and not used_t.intersection(ts),"Nhóm dùng thẻ lặp.")
                    need(all(x in t["inspected"] and x not in t["removed"] and not docs_by_id[x].get("missing",False) and not docs_by_id[x].get("duplicate_of") for x in ds),"Nhóm chưa đủ nguồn.")
                    total=sum(docs_by_id[x]["amount"] for x in ds)
                    need(total==g.get("total")==sum(txids[x]["amount"] for x in ts),"Tổng nhóm không đúng.")
                    need({docs_by_id[x]["ref"] for x in ds}=={r for x in ts for r in txids[x]["refs"]},"Nhóm sai nguồn tham chiếu.")
                    used_d.update(ds);used_t.update(ts)
                for tx in t["transactions"]:
                    clean_text(tx.get("id"),80);integer(tx.get("amount"),-100000,100000)
                    need(isinstance(tx.get("refs"),list) and all(isinstance(r,str) for r in tx["refs"]),"Tham chiếu giao dịch không hợp lệ.")
            else:
                need(isinstance(t.get("evidence"),list) and len(t["evidence"])==3,"Thiếu hồ sơ hỗ trợ.")
                need(t.get("solution") in ("reship","trace","exchange","refund","guide"),"Phương án hỗ trợ sai.")
                for e in t["evidence"]:
                    for key in ("id","title","text"):clean_text(e.get(key),2000)
                need(isinstance(t.get("timeline"),list),"Thiếu lịch sử phối hợp.")
                integer(t.get("ready_turn"),0,10**9)
                for key in ("identity","confirmed","handed_over"):need(type(t.get(key)) is bool,"Trạng thái xử lý thiếu.")
                need(t.get("proposal") in (None,"reship","trace","exchange","refund","guide"),"Phương án đề nghị không hợp lệ.")
        need(len(taskids)==len(set(taskids)),"Công việc bị trùng mã.")
        need(c["active_task"] is None or c["active_task"] in taskids,"Công việc đang chọn không tồn tại.")
        for k in c["stock"]:need(available(c,k)>=0,"Hàng đã giữ nhiều hơn tồn kho.")
        if c["event"]:
            e=c["event"];need(e.get("script") in SCRIPTS and SCRIPTS[e["script"]]["career"]==cid,"Tình huống bản lưu không hợp lệ.")
            need(e.get("stage") in ("noticed","investigating","proposed","executing","resolved"),"Bước sự kiện sai.")
            need(e.get("chosen") in (None,"a","b") and isinstance(e.get("read"),list) and type(e.get("practice")) is bool,"Dữ liệu sự kiện thiếu.")
            integer(e.get("step"),0,2)
        for f in c["feed"]:
            need(isinstance(f,dict) and f.get("npc") in ["player",*NPC_INDEX] and isinstance(f.get("comments"),list),"Bài đăng không hợp lệ.")
            clean_text(f.get("text"),3000);clean_text(f.get("id"),100)
            need(f.get("stars") in (None,1,2,3,4,5),"Số sao không hợp lệ.")
            fbk.validate_post(f)
        for npc,chat in c["chats"].items():
            need(npc in NPC_INDEX and isinstance(chat,list) and len(chat)<=40,"Chat bản lưu không hợp lệ.")
            for row in chat:need(row.get("role") in ("user","npc"),"Vai chat không hợp lệ.");clean_text(row.get("text"),2000)
        need(isinstance(c["relationships"],dict) and isinstance(c["decor"],dict),"Dữ liệu quan hệ/trang trí không hợp lệ.")
        for key,value in c["relationships"].items():need(key in NPC_INDEX and NPC_INDEX[key]["career_id"]==cid,"Quan hệ sai nghề.");integer(value,0,100)
        for key,value in c["metrics"].items():clean_text(key,150);integer(value,0,10**9)
        for item,position in c["decor"].items():
            need(item in c["upgrades"] and UPGRADE_INDEX[item]["kind"]=="decor" and isinstance(position,dict),"Món trang trí chưa sở hữu.")
            need(position.get("spot") in ("window","corner","front","center","wall"),"Vị trí trang trí không hợp lệ.")
        for shipment in c["shipments"]:
            need(isinstance(shipment,dict) and shipment.get("item") in expected_items,"Kiện hàng sai mã.")
            clean_text(shipment.get("id"),100);integer(shipment.get("qty"),1,6);integer(shipment.get("actual"),1,6);integer(shipment.get("ready"),0,10**9);integer(shipment.get("cost"),0,10000)
            need(shipment.get("status") in ("in_transit","received"),"Trạng thái kiện sai.")
        for pending in c["pending"]:
            need(isinstance(pending,dict) and pending.get("kind") in ("return_note","event_followup","comment"),"Thông báo chờ không hợp lệ.")
            integer(pending.get("day"),1,999999);integer(pending.get("turn"),0,10**9);clean_text(pending.get("ref"),200);clean_text(pending.get("text"),3000)
            need(pending.get("npc") in NPC_INDEX,"Thông báo thiếu nhân vật.")
        for memory in c["memories"]:
            need(isinstance(memory,dict) and memory.get("npc") in NPC_INDEX,"Ký ức sai nhân vật.")
            clean_text(memory.get("text"),3000);clean_text(memory.get("source"),200)
        for row in c["journal"]:
            for key in ("id","kind","text"):clean_text(row.get(key),4000)
            integer(row.get("day"),1,999999);integer(row.get("turn"),0,10**9)
        for post in c["feed"]:
            for key in ("author","source","kind"):clean_text(post.get(key),200)
            integer(post.get("day"),1,999999);need(type(post.get("liked")) is bool,"Trạng thái bài đăng thiếu.")
            for comment in post["comments"]:
                clean_text(comment.get("author"),100);clean_text(comment.get("text"),3000);integer(comment.get("day"),1,999999)
                need(comment.get("npc") in ("player",*NPC_INDEX),"Người bình luận không hợp lệ.")
        need(len(c["album"])<=6,"Album quá lớn.")
        for photo in c["album"]:
            need(isinstance(photo.get("image"),str) and len(photo["image"])<=450000 and photo["image"].startswith(("data:image/webp;base64,","data:image/png;base64,")),"Ảnh lưu không hợp lệ.")
    # Reject non-finite numbers anywhere; no NaN/Infinity in imported state.
    def finite(obj):
        if isinstance(obj,float):need(math.isfinite(obj),"Bản lưu chứa số không hữu hạn.")
        elif isinstance(obj,dict):
            for value in obj.values():finite(value)
        elif isinstance(obj,list):
            for value in obj:finite(value)
    finite(s)
