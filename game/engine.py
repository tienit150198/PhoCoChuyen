"""Server-authoritative game rules.

UI and dialogue can propose actions; only this reducer mutates money, inventory,
evidence, workflow, relationships, or quests. The storage layer executes it in
an atomic PostgreSQL transaction with revision checking and command receipts.
"""
from __future__ import annotations
import base64
import contextvars
import copy
import hashlib
import math
import os
import secrets
import random
import re
import unicodedata
from typing import Any
from .content import (CAREERS,CAREER_META,NPCS,NPC_INDEX,PRODUCTS,PRODUCT_INDEX,PAPERS,RIBBONS,
    LOT_INDEX,UPGRADE_INDEX,QUESTS,QUEST_INDEX,REVIEW_FOLLOWUP,make_task,initial_career)
from .events import SCRIPTS,instantiate,event_view
from . import operations as ops
from . import business
from . import player_service_tasks as player_services
from . import experiences as life
from . import extra_content as extra
from . import feedback as fbk
from . import situations as sit
from . import inventory as inv
from . import employment as emp
from .careers import PLUGINS
from . import journey as jr
from . import invest as iv
from . import board as bd
from . import life as doi
from . import career_stories as cst
from . import desk as dk
from . import desk_can as dcan  # the classic desks' guards, also run as the view's `can` (UI wave 5)
from . import giftshop as gifts
from . import incidents as incs
from . import happenings as haps
from . import archive as ar
from . import bank_speaker
from . import whats_new as wn
from . import closeness as qn
from . import abandon as ab
from . import dayclock as dc
from . import wardrobe as wd
from . import avatar as avt
from . import patience as pt
from . import system_gift as sg
from . import live_effects as lfx
from . import fair as fh  # 🏮 Hội chợ dân gian
from . import jail as jl  # 🚔 Trại tạm giữ (game/jail.py)
from . import x3_week as x3w  # 🔥 Nghề x3 trong tuần
from . import staff_market as staff_market_  # 📈 staff orders: market multiplier, 🔥 hot career of the day
from . import overtime as ovt  # ⏱️ Tăng ca ×2, ⚡ thưởng năng suất
from . import needs as nd  # 🍚 No bụng, 😴 Tỉnh táo
from . import chua as cg  # 🛕 Đi chùa
from . import promotion as pm  # 🎖️ Thăng tiến, 🧑‍💼 Ca quản lý
from . import rui as rui_  # 🛡️ Rủi ro & bảo hiểm
from . import vang as vang_  # 💰 Tiệm vàng

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

_CONTROL=re.compile(r"[\x00-\x08\x0b-\x1f]")  # control characters except tab and newline

def clean_text(value: Any, max_length: int=500, minimum: int=1) -> str:
    need(isinstance(value,str),"Nội dung cần là văn bản.")
    text=value.strip()
    if _CONTROL.search(text):text=_CONTROL.sub("",text)
    need(minimum<=len(text)<=max_length,f"Nội dung cần từ {minimum} đến {max_length} ký tự.")
    return text

def normalize(s: str) -> str:
    s=unicodedata.normalize("NFD",s.lower()).replace("đ","d")
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

from . import accounting_school as accounting_school_
from . import history_course as history_course_  # 📜 Học lịch sử Việt Nam (vs_*): its block is created on first use

def new_state() -> dict:
    return dict(schema=4,name="Mây",current=None,seq=0,
        settings=dict(default_settings(),whatsNewSeen=""),  # "Có gì mới" is server-wide: new players see it too
        careers={cid:initial_career(cid) for cid in CAREERS},journey=jr.initial(),stories=cst.initial())

def notes_seen(v) -> str:
    """Comma list of announcement ids the player has seen (tutorial helper)."""
    need(isinstance(v,str) and len(v)<=320,"Thiết lập không hợp lệ.")
    ids=[x for x in v.split(",") if x]
    need(len(ids)<=12 and all(re.fullmatch(r"[a-z0-9-]{1,24}",x) for x in ids),"Thiết lập không hợp lệ.")
    return ",".join(ids)

def default_settings() -> dict:
    return dict(mode="everyday",sound=True,music=False,reduceMotion=False,largeText=False,aiConsent=True,aiAsked=True,aiNoticeSeen=False,securityEvents=True,
        lang="vi",uiTheme="kem",musicTrack="auto",musicVolume=45,sfxVolume=70,notify=False,publicProfile=False,
        tutorialDone=False,notesSeen="",whatsNewSeen="",  # whatsNewSeen: last "Có gì mới" release read (game/whats_new.py); older saves start at ""
        npcVoices=True,detailSfx=True,bankVoice=True,  # Cài đặt → Âm thanh: giọng nhân vật, âm thanh chi tiết, giọng đọc số tiền
        moneyTing=True)  # tiếng "ting ting" khi nhận tiền (public/js/v4/sounds.js)

from .jsoncopy import tree_copy,_SCALARS  # noqa: F401 (re-exported)

def _build_id() -> str:
    """Fingerprint of the code that migrates and validates saves (game/build_id.py: every game
    module engine can import, the career list and SAVE_EPOCH). The storage layer stamps it on
    a save (state["check"]["build"]) once the save has been migrated and fully validated by
    this code; a stamped save skips migrate_state, and commands on it only re-validate what
    they changed (see Store._compute). A deploy that changes any of that code gives a new
    build: every save is migrated and fully validated again."""
    from .build_id import build_id
    return build_id(CAREERS)

BUILD=_build_id()

def stamped(state:dict) -> bool:
    """The save was migrated and fully validated by this build (see _build_id)."""
    check=state.get("check")
    return type(check) is dict and check.get("build")==BUILD

def migrate_state(state:dict,owned:bool=False) -> dict:
    """Upgrade v1 locally without replaying wages, rent, tax or past incidents.
    `owned`: the caller hands over a private copy (freshly parsed JSON) that may be
    upgraded in place; otherwise the supplied state is never mutated.
    A save stamped with this BUILD already went through every step below, and they
    are idempotent on what the reducer produces: it is returned as it is."""
    need(isinstance(state,dict),"Bản lưu cần là một đối tượng.","invalid_save")
    if stamped(state) and not needs_migration(state):return state if owned else tree_copy(state)
    s=state if owned else tree_copy(state)
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
        bd.migrate(s)  # nhóm cư dân phố: the neighbourhood group board under journey.board
        doi.migrate(s)  # chuyện đời thường & tình làng nghĩa xóm: journey.life
        qn.migrate(s)  # điểm thân quen: journey.closeness (after life: reads its bonds)
        life.upgrade_save(s)
        dk.migrate(s)  # paperwork desks: desk memory + refreshed wording of older tasks
        incs.migrate(s)  # chuyện đời: an empty incident book per workplace
        haps.migrate(s)  # chuyện bất ngờ trong ca: live happenings in the scene
        cst.migrate(s)  # truyện nghề: an empty story book for older saves
        wd.migrate(s)  # tủ đồ: the look older saves were drawn with (game/wardrobe.py)
        avt.migrate(s)  # ảnh đại diện: a block a newer build wrote keeps what this build knows (game/avatar.py)
        emp.migrate(s)  # xin việc: nơi đã làm trước khi cần tuyển dụng thì coi như đã ký hợp đồng
        inv.migrate(s)  # kho: đơn nhập cũ theo nhịp → giờ giao dự kiến
        _trim_histories(s)  # v0.8.1: journal, cash book and day recaps beyond the new caps move to the archive
        for _cid in ("mother_baby","pharmacy"):  # kho cũ của hai nghề gốc: kiện theo nhịp → giờ giao
            _c=s['careers'].get(_cid)
            if isinstance(_c,dict) and isinstance(_c.get('shipments'),list) and type(_c.get('day')) is int and type(_c.get('turn')) is int:_upgrade_shipments(_c,_cid)
        # Việc dở mà bản cũ để kẹt (không còn bước nào) nhận lời đáp theo luật hiện hành, vd. đơn sỉ tạp hóa kẹt ở mức bớt sâu nhất (góp ý #57).
        for _cid,_mod in PLUGINS.items():
            _c=s['careers'].get(_cid)
            if isinstance(_c,dict) and hasattr(_mod,'heal_save'):_mod.heal_save(s,_c)
    if isinstance(s.get('settings'),dict):
        if ai_unasked:s['settings'].update(aiConsent=True,aiAsked=True)
        for k,v in default_settings().items():s['settings'].setdefault(k,v)
    return s


def _trim_histories(s:dict) -> None:
    """Older saves kept longer lists than log(), ops.record_money, life.on_close, start_day,
    mark_done and ops.bill keep now (v0.8.1: 1200 journal rows, 1500 cash-book rows, 30 day
    recaps; v0.9.5: 300 journal rows, 400 cash-book rows, 10 recaps, 40 finished jobs, every
    finished-job id, up to 900 bills): the overflow moves to the archive once (game/archive.py;
    written with the save by the storage layer). Board posts: board.migrate."""
    for cid,c in s["careers"].items():
        if not isinstance(c,dict):continue
        if isinstance(c.get("journal"),list) and len(c["journal"])>JOURNAL_KEPT:c["journal"]=ar.last(c["journal"],JOURNAL_KEPT,"journal",cid)
        f=(c.get("ops") or {}).get("finance") if isinstance(c.get("ops"),dict) else None
        if (isinstance(f,dict) and isinstance(f.get("ledger"),list) and len(f["ledger"])>ops.LEDGER_HIGH and type(c.get("day")) is int
                and type(f.get("opening_balance")) is int
                and all(isinstance(x,dict) and type(x.get("day")) is int and type(x.get("amount")) is int for x in f["ledger"])):
            ops.trim_ledger(c)
        x=c.get("life")
        if isinstance(x,dict) and isinstance(x.get("goals_history"),list) and len(x["goals_history"])>life.GOALS_KEPT:
            x["goals_history"]=ar.last(x["goals_history"],life.GOALS_KEPT,"life.goals_history",cid)
        # v0.9.5: finished jobs beyond yesterday's (at least DONE_KEPT), finished-job ids beyond COMPLETED_IDS_KEPT.
        if isinstance(c.get("tasks"),list) and type(c.get("day")) is int:trim_done_tasks(c,cid)
        if isinstance(c.get("completed_ids"),list) and len(c["completed_ids"])>COMPLETED_IDS_KEPT:
            c["completed_ids"]=ar.last(c["completed_ids"],COMPLETED_IDS_KEPT,"completed_ids",cid)
        if (isinstance(f,dict) and isinstance(f.get("bills"),list) and len(f["bills"])>ops.BILLS_HIGH
                and all(isinstance(b,dict) and isinstance(b.get("status"),str) for b in f["bills"])):ops.trim_bills(c,cid)


def needs_migration(state:dict) -> bool:
    return state.get('schema')!=4 or not isinstance(state.get('careers'),dict) or set(state['careers'])!=set(CAREERS) or 'journey' not in state or 'stories' not in state or 'aiAsked' not in (state.get('settings') or {})


def metric(c: dict,key: str,value: int=1) -> None:
    c["metrics"][key]=c["metrics"].get(key,0)+value

JOURNAL_KEPT=100  # rows kept in the save (the Sổ tay shows 80, "Xem cũ hơn" pages the archive)
FEED_KEPT=100  # posts kept in the save: the rating and review follow-ups read them all

def log(s:dict,c:dict,kind:str,text:str,npc:str|None=None,ref:str|None=None) -> str:
    s["seq"]+=1
    lid=f"log-{s['seq']}"
    c["journal"].append(dict(id=lid,kind=kind,text=text,npc=npc,ref=ref,day=c["day"],turn=c["turn"]))
    # Keep a bounded display history (older rows go to the archive). Every memory embeds its own source snapshot.
    if len(c["journal"])>JOURNAL_KEPT: c["journal"]=ar.last(c["journal"],JOURNAL_KEPT,"journal",c)
    return lid

def remember(s:dict,c:dict,npc:str,text:str,ref:str|None=None) -> None:
    lid=log(s,c,"memory",text,npc,ref)
    c["memories"].append(dict(id=lid,npc=npc,text=text,source=ref or lid,day=c["day"]))
    c["memories"]=ar.last(c["memories"],120,"memories",c)
    c["relationships"][npc]=min(100,c["relationships"].get(npc,0)+4)

def money(s:dict,c:dict,amount:int,reason:str,ref:str|None=None,category:str|None=None) -> None:
    need(type(amount) is int,"Giao dịch không hợp lệ.")
    if player_services.suppress_money(c,amount,ref):return
    need(c["money"]+amount>=0,"Chưa đủ xu. Chọn phương án không tốn xu hoặc hoàn thành thêm một việc nhé.")
    c["money"]+=amount
    ops.record_money(c,amount,reason,ref,category)
    c["earnings"]+=max(amount,0)
    c["costs"]+=max(-amount,0)
    log(s,c,"money",f'{"+" if amount>=0 else ""}{amount} xu · {reason}',ref=ref)

MORE_ACTIVE=4  # at most this many customers in hand (unfinished, deferred included)
MORE_DAY=12  # at most this many customers dealt per day

def _next_slot(c:dict) -> int:
    return max((int(t["id"].split("-")[-1]) for t in c["tasks"] if t["day"]==c["day"]),default=-1)+1

def more_gate(c:dict,career:str,ahead:int=0) -> dict|None:
    """Why `more_work` refuses a new customer now (None: it would take one). The action and the public view
    (`ahead=1`: the clock as the press will see it, after its own tick) share this one rule, so the client never
    offers "Đón thêm khách" when the press is certain to fail: it offers the next real step instead."""
    if not c["open"]:return dict(why="closed",error="Mở ca trước nhé.")
    if dc.past_close(dict(c,turn=c["turn"]+ahead) if ahead else c,career):
        return dict(why="closing",code="closing_time",error="Đến giờ đóng cửa rồi: không đón thêm khách. Làm nốt việc dở rồi khép ca nhé.")
    active=sum(t["status"] not in ("completed","referred","cancelled") for t in c["tasks"])
    if active>=MORE_ACTIVE:return dict(why="full",active=active,error="Đang có đủ việc. Hoàn thành hoặc hẹn lại trước nhé.")
    if _next_slot(c)>=MORE_DAY:return dict(why="cap",cap=MORE_DAY,error=f"Hôm nay đã nhận đủ {MORE_DAY} việc. Khép ca rồi bắt đầu ngày mới nhé.")
    return None

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
    c["feed"]=ar.first(c["feed"],FEED_KEPT,"feed",c)
    return post

def available(c:dict,item:str) -> int:
    held=sum(t.get("basket",{}).get(item,0) for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled"))
    return c["stock"].get(item,0)-held

DONE_KEPT=8  # finished jobs always kept in the save (the AI's "past visits" read a customer's last 3)
DONE_MAX=40  # and never more: older finished jobs move to the archive at the next start_day
COMPLETED_IDS_KEPT=100  # ids of finished jobs (a guard against paying twice): more than DONE_MAX

def done_kept(c:dict,done:list) -> int:
    """How many finished jobs stay in the save: all of yesterday's and today's (the scene, the
    day's lãi/lỗ, the "việc vừa xong" sheet and today's slot numbers read them), at least
    DONE_KEPT, at most DONE_MAX. `done`: the finished jobs, oldest first."""
    recent=sum(1 for t in done if isinstance(t,dict) and type(t.get("day")) is int and t["day"]>=c["day"]-1)
    return max(DONE_KEPT,min(DONE_MAX,recent))

def trim_done_tasks(c:dict,cid:Any=None) -> None:
    """Finished jobs beyond done_kept go to the archive; the order of the rest is kept."""
    done=[t for t in c["tasks"] if isinstance(t,dict) and t.get("status") in ("completed","referred","cancelled")]
    n=done_kept(c,done)
    if len(done)<=n:return
    gone=done[:-n];ids={id(t) for t in gone}
    ar.record(gone,"tasks",c if cid is None else cid)
    c["tasks"]=[t for t in c["tasks"] if id(t) not in ids]

def mark_done(c:dict,tid:str) -> None:
    """Remember a finished job's id (paid once); the oldest ids go to the archive."""
    if tid not in c["completed_ids"]:c["completed_ids"].append(tid)
    if len(c["completed_ids"])>COMPLETED_IDS_KEPT:c["completed_ids"]=ar.last(c["completed_ids"],COMPLETED_IDS_KEPT,"completed_ids",c)

def task_done(s:dict,c:dict,t:dict,reward:int,narrative:str,status:str="completed") -> None:
    need(t["id"] not in c["completed_ids"],"Công việc đã nhận kết quả.","already_completed")
    t["status"]=status
    t["completed_turn"]=c["turn"]
    mark_done(c,t["id"])
    c["day_completed"]+=1
    metric(c,"served"); metric(c,f"served:{t['npc']}")
    c["xp"]+=30
    if t.get('player_order'):
        player_services.complete(s,c,t,narrative)
        return
    if reward: money(s,c,reward,"Hoàn thành: "+t["title"],t["id"])
    remember(s,c,t["npc"],narrative,t["id"])
    made=fbk.make_review(s,c,t,status)
    review=made["text"];stars=made["stars"]
    ovt.on_job(s,c,t,reward,status,(made.get("feedback") or {}).get("fair",stars))  # ⏱️ Tăng ca ×2 past the normal day (game/overtime.py)
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
    if t["career"]=="customer_care":_cs_after_task(s,c,t,status)


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
    dcan.ph_ready(t,c)  # game/desk_can.py: the same rules are the view's can.ph_check


def tick_pending(s:dict,c:dict) -> list[str]:
    notes=[]
    for t in c["tasks"]:
        if t["career"]=="accounting" and ((t.get("source_ready",0) and c["turn"]>=t["source_ready"]) or (t.get("source_at") and _now(c,"accounting")>=t["source_at"])):
            for d in t["docs"]:d["missing"]=False
            t["source_ready"]=0;t["source_at"]=None
            notes.append("Nguồn bổ sung đã tới: "+t["title"])
            log(s,c,"delivery",notes[-1],t["npc"],t["id"])
        if t["career"]=="customer_care" and ((t.get("ready_turn",0) and c["turn"]>=t["ready_turn"]) or (t.get("ready_at") and _now(c,"customer_care")>=t["ready_at"])):
            if t["status"]=="executing":
                t["status"]="awaiting_confirmation";t["ready_turn"]=0;t["ready_at"]=None
                t["timeline"].append({"kho":"Kho báo hàng đã tới tay khách; chờ khách xác nhận.","vc":"Đơn vị vận chuyển gửi kết quả đối soát.","ketoan":"Kế toán báo đã duyệt khoản hoàn."}.get(t.get("wait"),"Đầu mối đã gửi xác nhận thực hiện phương án."))
                notes.append("Có kết quả phối hợp: "+t["title"])
            elif t["status"]=="handed_over":
                t["status"]="understood";t["ready_turn"]=0;t["ready_at"]=None
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
    c["pending"]=ar.last(remaining,80,"pending",c)
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
    from . import voices, spice  # voice-flavoured small talk; archetype attitude for hints (Vietnamese saves)
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
        reply=spice.scripted(s,career,npc,"offer") or "Mình nghe đề nghị của bạn. Bạn mở công việc hoặc tình huống liên quan, kiểm điều kiện rồi xác nhận thao tác nhé. Nói trong chat chưa làm tiền hay hàng thay đổi."
        if t:suggestions=[dict(label="Kiểm công việc trước",action="open_task",task=t["id"])]
    elif any(w in msg for w in ["nho","lan truoc","hom qua","quen"]):
        memories=[m for m in c["memories"] if m["npc"]==npc]
        reply=("Mình còn nhớ: "+memories[-1]["text"]) if memories else "Mình chưa có kỷ niệm công việc nào với bạn ở nghề này. Hôm nay mình bắt đầu làm quen nhé."
    elif any(w in msg for w in ["ghe","trang tri","cay","den","dep"]):
        decorated=[UPGRADE_INDEX[u]["name"] for u in c["upgrades"] if UPGRADE_INDEX[u]["kind"]=="decor"]
        reply="Mình thấy góc mới có "+", ".join(decorated[:3])+". Nhìn ấm áp hơn đó!" if decorated else "Góc hiện tại còn đơn giản, nhưng dễ gần. Bạn có thể chọn một món trang trí trong lúc tiệm nghỉ."
    elif any(w in msg for w in ["xin loi","cam on"]):reply=spice.scripted(s,career,npc,"kind") or "Cảm ơn bạn đã nói rõ. Mình cùng làm nốt việc đang có nhé, không cần vội."
    elif any(w in msg for w in ["chao","hello","hi "]):
        reply=f'Chào {s["name"]}! '+(t["opening"] if t else "Hôm nay mình ghé phố chào bạn một chút.")
        # Each character greets in their own voice (game/voices.py); English keeps the line above.
        if s["settings"].get("lang")!="en":reply=(voices.scripted(s,career,npc,"greet",f'Chào {s["name"]}!')+" "+(t["opening"] if t else voices.scripted(s,career,npc,"idle",""))).strip()
    elif t:
        reply=spice.scripted(s,career,npc,"task",t["title"]) or "Mình đang trao đổi về: "+t["title"]+". Bạn có thể hỏi ‘Bạn cần gì?’ hoặc mở công việc để cùng xem dữ kiện nhé."
        suggestions=[dict(label="Hỏi nhu cầu",action="ask",task=t["id"]),dict(label="Mở công việc",action="open_task",task=t["id"])]
    else:reply=voices.scripted(s,career,npc,"idle","Hôm nay phố khá yên. Mình thích ngồi ở một góc và nhìn mọi người làm việc. Bạn cứ làm theo nhịp của mình nhé.")
    return reply,suggestions


LEARNING_TASKS=2  # onboarding: while a career's first jobs are done, waiting costs no patience
# How long customers put up with waiting afterwards: PATIENCE_FACTOR in game/patience.py.

# Set by apply_action(scoped=True): validate_state leaves the careers to the storage layer.
_SCOPED=contextvars.ContextVar("scoped_validation",default=False)

def apply_action(state:dict,career:str|None,action:str,payload:dict|None=None,internal:bool=False,owned:bool=False,scoped:bool=False) -> tuple[dict,dict]:
    """Functional transaction: failure cannot partly mutate the supplied state.
    `owned=True` (the storage layer, with a freshly parsed save it throws away on
    failure) skips the defensive copy: the state is changed in place.
    `scoped=True` (the storage layer, on a save this build already validated):
    validate_state checks only what lies outside the careers; the caller must run
    validate_career on every career the command changed before storing."""
    acting=ar.acting(career if career in CAREERS else None)  # whose rows cut lists archive by default
    # bank_speaker: transfers into the shop's account during the command ride along as result['bank'].
    token=_SCOPED.set(True) if scoped else None
    def run():
        with player_services.command(state,career,action,payload):
            out,result=_apply_action(state,career,action,payload,internal,owned)
        if business.reconcile(out):validate_state(out)
        return out,result
    try:return bank_speaker.collect(run)
    finally:
        if token is not None:_SCOPED.reset(token)
        ar.done_acting(acting)

def _apply_action(state:dict,career:str|None,action:str,payload:dict|None,internal:bool,owned:bool) -> tuple[dict,dict]:
    s=migrate_state(state,owned=owned)
    if business.settle(s):validate_state(s)
    fh.settle(s)  # 💸 a vay nóng of a fair that has closed is collected (game/fair_cash.py)
    p=payload or {}
    need(isinstance(p,dict),"Dữ liệu thao tác không hợp lệ.")
    jl.settle(s)  # 🚔 a sentence whose safety time is over (or MNL_JAIL_OFF): out of the trại tạm giữ
    jl.gate(s,action,internal)  # 🚔 inside: no work, no Chợ đen, no shopping or trips (game/jail.py FREE: what stays open)
    result=dict(message="Đã thực hiện.",effects=[])
    care_notes=[]
    if action==business.ACTION:
        need(internal,"Thao tác chỉ dành cho máy chủ.","forbidden")
        return s,dict(message="Đã cập nhật hoạt động các tiệm.")
    if action=="select_career":
        need(career in CAREERS,"Nghề này đang ở danh mục mở rộng, chưa chơi được.")
        jr.gate(s,career,action,internal,p)
        left=ab.check(s,career,p,internal)  # bỏ dở việc: work in progress at the place you leave (confirm + penalty)
        jr.on_select(s,career)
        s["current"]=career
        hired=emp.first_day_hire(s,s["careers"][career],career)  # story day one: no CV/trial for a first-chapter job
        return s,dict(message=hired or "Chào mừng tới "+CAREER_META[career]["place"]+".",hired=bool(hired),**({"abandon":left} if left else {}))
    if action=="settings":
        for k,v in p.items():
            if k=="name":from .accounts import character_name;s["name"]=character_name(v,s.get("name"))  # moderation #13: display-name rules
            elif k=="mode":pass  # Old clients may still send it: each day's pace is the luck of the day now.
            elif k in SETTING_CHOICES:
                need(v in SETTING_CHOICES[k],"Thiết lập không hợp lệ.");s["settings"][k]=v
            elif k in ("musicVolume","sfxVolume"):
                s["settings"][k]=integer(v,0,100)
            elif k=="tutorialDone":  # first-run tour seen (follows the account across devices)
                need(type(v) is bool,"Thiết lập không hợp lệ.");s["settings"][k]=v
            elif k=="notesSeen":s["settings"][k]=notes_seen(v)  # announcements already shown ("guide-v1,…")
            elif k=="whatsNewSeen":  # "Có gì mới" read up to this release; never goes back down
                need(wn.valid_seen(v),"Thiết lập không hợp lệ.");s["settings"][k]=wn.newer(s["settings"].get(k,""),v)
            elif k in s["settings"]:
                need(type(v) is bool,"Thiết lập không hợp lệ.");s["settings"][k]=v
            else:raise GameError("Thiết lập không được hỗ trợ.")
        return s,dict(message="Đã lưu cách chơi của bạn.")
    if action=="reset_all":
        need(p.get("confirm")=="BAT DAU LAI","Cần xác nhận trước khi xóa tiến trình.")
        fresh=new_state()
        if s["journey"]["story"]:jr.enable_story(fresh,s["journey"]["seed"]+1)
        ar.record([s],"reset_all",ar.JOURNEY)  # the whole previous journey stays in the archive
        return fresh,dict(message="Đã tạo hành trình mới.")
    if action.startswith("jr_"):return jr.action(s,career,action,p)
    if action.startswith('as_'):  # Học kế toán (game/accounting_school.py): its block is created on first use
        result=accounting_school_.action(s,action,p)
        validate_state(s)
        if _SCOPED.get():accounting_school_.validate(s)  # validate_state skips it when scoped
        return s,result
    if action.startswith('vs_'):  # 📜 Học lịch sử Việt Nam (game/history_course.py): free, its block is created on first use
        result=history_course_.action(s,action,p)
        validate_state(s)
        return s,result
    if action.startswith("iv_"):return iv.action(s,action,p)
    if action.startswith("bd_"):return bd.action(s,career,action,p,internal)
    if action.startswith("lf_"):return doi.action(s,action,p)
    if action.startswith("qn_"):return qn.action(s,career,action,p)  # điểm thân quen: chat, gifts, thanks, invites
    if action.startswith("st_"):return cst.action(s,career,action,p)
    if action.startswith("fair_"):return fh.action(s,action,p)  # 🏮 Hội chợ dân gian (game/fair.py): bầu cua, lô tô, chiếu trong
    if action.startswith("jail_"):return jl.action(s,action,p)  # 🚔 Trại tạm giữ: hết ngày, công ích (game/jail.py)
    if action==sg.ACTION:  # 🎁 Quà từ Phố Có Chuyện (game/system_gift.py): the server pays a gift into the wallet
        need(internal,"Thao tác chỉ dành cho máy chủ.","forbidden")
        return sg.apply(s,p)
    if action==lfx.ACTION:  # 🧧 live rewards (game/live_effects.py): the server pays what the live service granted
        need(internal,"Thao tác chỉ dành cho máy chủ.","forbidden")
        return lfx.apply(s,p)
    need(career in CAREERS,"Chọn một nghề trước nhé.")
    jr.gate(s,career,action,internal,p)
    if career!=s.get("current"):ab.check(s,career,{},internal)  # leaving work in progress only through select_career
    c=s["careers"][career]
    # A plugin's repeat of a step already done (florist: Cắm on a bench already arranged, B8 07/10): a quiet OK with
    # nothing changed, no beat and no ticks. mod.repeat answers None for anything else (the command runs as before).
    if career==s.get("current") and hasattr(PLUGINS.get(career),"repeat") and action.startswith(PLUGINS[career].SPEC["prefix"]):
        same=PLUGINS[career].repeat(s,c,action,p)
        if same is not None:return s,same
    s["current"]=career
    clock_before=dc.minute_now(c,career) if action!="start_day" else None  # giờ trong ngày: closing warnings below
    prior_mistakes={t["id"]:t["mistakes"] for t in c["tasks"]}
    # Story players learning a place (its first LEARNING_TASKS jobs): customers wait kindly, patience never drops.
    learning=s.get("journey",{}).get("story") and c["metrics"].get("served",0)<LEARNING_TASKS
    prior_patience={t["id"]:t.get("patience",100) for t in c["tasks"]} if learning else None  # no field yet = full
    mod=PLUGINS.get(career)
    plugin_action=bool(mod) and action.startswith(mod.SPEC['prefix'])
    if action.startswith(("shop_","ac_","cs_")) or action in ("ph_pick","ph_check","ph_deliver","ph_refer","ph_inspect"):
        need(c["open"],"Mở ca trước khi xử lý công việc nhé.")
    if career in dk.CAREERS and action not in CARE_ACTIONS and (action.startswith(("ac_","cs_")) or action in ("ph_pick","ph_check","ph_deliver","ph_refer","ph_inspect","basket_remove")):
        desk_task=next((x for x in c["tasks"] if x["id"]==(p.get("task") or c["active_task"])),None)
        need(not (desk_task and desk_task.get("desk")),"Hồ sơ này xử lý ở bàn giấy tờ: đánh dấu dòng sai rồi đóng dấu nhé.")
    if plugin_action and action not in mod.SPEC.get('free_actions',()):
        need(c["open"],"Mở ca trước khi xử lý công việc nhé.")
    no_tick={"task_select","settings","talk","feed_like","photo","decor_move","event_dismiss","quest_claim","chat_clear","reset_career","theme","sit_dismiss","sit_practice","inv_rate","inv_claim","inv_cart","inv_haggle","inv_cancel"}
    if mod:no_tick|=set(mod.SPEC.get('no_tick',()))
    no_tick|=CARE_FREE
    if action.startswith("cl_"):need(c["open"],"Mở ca trước khi làm hoạt động lớp nhé.")
    no_tick|={"pm_answer","pm_ask","pm_close","pm_of_plan","pm_of_hr","pm_of_inbox","pm_of_insp","pm_org_aim","pm_org_own"}  # (pm_org_*, pm_of_insp: the org ladder, game/org.py) 🎖️ the review, closing the board and the 🏢 office take no time; a manager's moves do
    if action not in no_tick and not action.startswith(("ops_","fb_","job_","soc_","cl_","inc_","hap_",*life.NEW_ACTION_PREFIXES)):c["turn"]+=1
    if action.startswith(life.NEW_ACTION_PREFIXES):
        result.update(life.handle(s,c,career,action,p))
    elif plugin_action:
        result.update(mod.handle(s,c,action,p))
    elif action in CARE_ACTIONS:
        result.update(care_action(s,c,career,action,p))
    elif action.startswith("desk_"):
        result.update(dk.handle(s,c,career,action,p))
    elif action.startswith("inv_"):
        result.update(inv.action(s,c,career,action,p))
        if mod and hasattr(mod,"on_stock"):mod.on_stock(s,c,action)  # e.g. a rush queue sees the goods just shelved
    elif action.startswith("sit_"):
        result.update(sit.action(s,c,career,action,p))
    elif action.startswith("inc_"):
        result.update(incs.action(s,c,career,action,p))
    elif action.startswith("hap_"):
        result.update(haps.action(s,c,career,action,p))
    elif action.startswith("fb_"):
        result.update(fbk.action(s,c,career,action,p,internal))
    elif action.startswith("job_"):
        was=c["job"].get("status") if isinstance(c.get("job"),dict) else None
        result.update(emp.action(s,c,career,action,p))
        if was!="hired" and isinstance(c.get("job"),dict) and c["job"].get("status")=="hired":
            from . import certificates as ct_
            tip=ct_.hire_nudge(s,career)  # 🎓 F#267: hired without the place's certificate → say where the exam is
            if tip:result["message"]=f'{result.get("message") or ""} {tip}'.strip()
    elif action.startswith("pm_"):  # 🎖️ the review, 🧑‍💼 the manager's board (game/promotion.py)
        result.update(pm.action(s,c,career,action,p))
    elif action.startswith("cl_"):
        from . import classroom
        result.update(classroom.action(s,c,career,action,p))
    elif action.startswith("soc_"):
        need(internal,"Thao tác chỉ dành cho máy chủ.","forbidden")
        from . import social
        result.update(social.apply_internal(s,c,career,action,p))
    elif action=="start_day":
        need(not c["open"],"Ca đã mở rồi.")
        if emp.required(career):
            emp.first_day_hire(s,c,career)
            need(c["job"]["status"]=="hired","Nghề này cần được tuyển dụng trước. Mở mục Xin việc để ứng tuyển nhé.","not_hired")
        manager=pm.check_start(s,c,career,p)  # 🧑‍💼 {manager: true}: the team takes the day's customers
        c["open"]=True;c["started"]=True;c["shift_summary"]=None
        ops.on_start(s,c,career)
        inv.on_open(s,c,career)  # kho: ghi nhịp mở ca cho đồng hồ giao hàng
        target=0 if manager else {"calm":2,"festival":4}.get(c["life"]["mode"],3)  # the day's pace is rolled at the previous close
        if not manager and mod and hasattr(mod, 'daily_task_count'):
            target=mod.daily_task_count(c['day'])
        unfinished=[t for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled")]
        slots=[int(t["id"].split("-")[-1]) for t in c["tasks"] if t["day"]==c["day"]]
        first=max(slots,default=-1)+1
        for i in range(max(0,target-len(unfinished))):
            c["tasks"].append(make_task(career,c["day"],first+i,c["turn"]))
            if mod and hasattr(mod,'on_task'):mod.on_task(s,c,c["tasks"][-1])
        # Keep unfinished work and the most recent completed tasks.
        done=[t for t in c["tasks"] if t["status"] in ("completed","referred","cancelled")]
        done=ar.last(done,done_kept(c,done),"tasks",c)
        active=[t for t in c["tasks"] if t["status"] not in ("completed","referred","cancelled")]
        c["tasks"]=done+active
        for t in active:t["deferred"]=False
        next_active(c)
        life.on_start(s,c,career)
        if mod and hasattr(mod,'on_start'):mod.on_start(s,c)
        dk.on_start(s,c,career)
        log(s,c,"day","Mở ca ngày "+str(c["day"])+".")
        care_notes+=care_start(s,c,career)
        # A career may word its own opening (SPEC['open_line']: the air crew report for duty, no shop door).
        result["message"]=(mod.SPEC.get("open_line") if mod else None) or "Đã mở cửa. Khách đang tới, mình bắt đầu từ một người nhé."
        line=pm.on_start(s,c,career,p)
        if line:result["message"]=line
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
        summary["clock"]=dc.close_summary(c,career,s)  # what time the day ended; tomorrow's opening
        summary["expired_value"]=inv.on_close(s,c,career)
        summary["experiences"]=life.on_close(s,c,career)
        summary["job"]=emp.on_close(s,c,career)
        if mod and hasattr(mod,'on_close'):summary["career"]=mod.on_close(s,c)
        elif career in dk.CAREERS:summary["career"]=dk.on_close(s,c,career)
        if career in CARE_CAREERS:
            care_lines=care_close(s,c,career)
            if care_lines:summary["career"]=dict(summary.get("career") or {},lines=list((summary.get("career") or {}).get("lines") or [])+care_lines)
        summary["reviews"]=fbk.day_summary(c,oldday)
        summary["incidents"]=inc_summary
        summary["happen"]=hap_summary
        left=ab.on_close(s,c,career,oldday)
        if left:summary["abandon"]=left
        promo=pm.on_close(s,c,career,summary)  # 🎖️ a good day counts; a manager shift still open closes (its pay is in the net)
        if promo:summary["promo"]=promo
        ot=ovt.on_close(s,c,career)  # ⚡ the busy tier's bonus; the day's ⏱️ overtime for the summary (journey: not in the x3 net)
        if ot:summary["ot"]=ot
        # The day's figures once everything has closed: the salary and the career's own closing are in, and
        # owner transfers are not (journey._transfer keeps them out of earnings/costs). The fund's change since the
        # morning is not used: a withdrawal larger than the morning fund clamps day_start_money at 0 and lost the
        # profit above it, which shorted the 🔥 x3 bonus (journey._end_of_day pays on this net).
        summary.update(income=c["earnings"],cost=c["costs"],net=c["earnings"]-c["costs"])
        c["shift_summary"]=summary;c["open"]=False;c["day"]+=1;c["day_completed"]=0;c["day_events"]=0
        c["day_start_money"]=c["money"];c["earnings"]=0;c["costs"]=0
        if c["event"] and c["event"]["stage"]=="resolved":c["event"]=None
        log(s,c,"day",f"Khép ngày {oldday}; {summary['completed']} việc xong, {summary['carried']} việc được giữ lại.")
        result.update(message="Một ngày nữa đã có câu chuyện để nhớ.",summary=summary)
    elif action=="more_work":
        need(not pm.managing(s,c,career),"Hôm nay bạn làm quản lý: giao việc cho đội nhé.","manager_shift")
        gate=more_gate(c,career)
        if gate:raise GameError(gate["error"],gate.get("code","invalid_action"))
        slot=_next_slot(c)
        t=make_task(career,c["day"],slot,c["turn"]);c["tasks"].append(t);c["active_task"]=t["id"]
        if career=="milk_tea":life.setup_task(s,c,t)
        if mod and hasattr(mod,'on_task'):mod.on_task(s,c,t)
        if career=="customer_care":_cs_task_hook(c,t)
        result["message"]=(mod.SPEC.get("more_line") if mod else None) or "Có thêm một vị khách ghé tới."
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
                block=ph_shelf_block(c,item);need(not block,block or "")
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
        # One item (`item`, `qty`) or a merged order (`lines`: [{item, qty}], F#194): one payment, one van,
        # one shipment row per line with the same supplier promise, so saved shipments keep their shape.
        need(career in ("mother_baby","pharmacy"),"Nghề này không cần nhập hàng.")
        catalogue=PRODUCT_INDEX if career=="mother_baby" else LOT_INDEX
        raw=p.get("lines") if p.get("lines") is not None else [dict(item=p.get("item"),qty=p.get("qty"))]
        need(isinstance(raw,list) and 1<=len(raw)<=STOCK_LINES,f"Một đơn gộp tối đa {STOCK_LINES} mã hàng.")
        want={}
        for w in raw:
            need(isinstance(w,dict),"Danh sách hàng không hợp lệ.")
            item=w.get("item");qty=integer(w.get("qty"),1,6)
            need(item in catalogue,"Mã hàng không hợp lệ.")
            need(item not in want,"Mỗi mã chỉ một dòng trong đơn gộp.")
            if career=="pharmacy":need(LOT_INDEX[item]["status"]=="available","Chỉ đặt lô hợp lệ.")
            want[item]=qty
        sup=_stock_supplier(career,p.get("supplier",STOCK_DEFAULT));need(sup,"Nhà cung cấp không tồn tại.")
        cap=max(ops.PROPERTY_INDEX[c["ops"]["property"]["tier"]]["stock_cap"],24 if "shelf" in c["upgrades"] else 12)
        for item,qty in want.items():
            in_transit=sum(x["qty"] for x in c["shipments"] if x["item"]==item and x["status"]!="received")
            need(c["stock"].get(item,0)+qty+in_transit<=cap,f"Kho mỗi mã chứa tối đa {cap}"+(f" ({catalogue[item]['name']})" if len(want)>1 else "")+". Nhận đủ rồi bán bớt hoặc nâng kệ.")
        need(stock_vans(c)<STOCK_VANS,"Đang có nhiều kiện chờ giao. Nhận bớt rồi đặt tiếp nhé.")
        costs={item:max(1,math.ceil(catalogue[item]["cost"]*qty*sup["factor"])) for item,qty in want.items()}
        ids=[f"shipment-{s['seq']+k+1}" for k in range(len(want))]
        names=[catalogue[item]["name"] for item in want]
        what=f'{want[next(iter(want))]} × {names[0]}' if len(want)==1 else f'gộp {len(want)} mã'
        money(s,c,-sum(costs.values()),("Đặt nhập "+next(iter(want)) if len(want)==1 else f"Đặt nhập gộp {len(want)} mã")+" · "+sup["name"],ids[0])
        s["seq"]+=len(want)
        clk=_clock(c,career)
        when_=inv._schedule(sup,career,clk["abs"],f"{career}:{c['day']}:{ids[0]}:{next(iter(want))}:{sup['id']}")
        for sid,(item,qty) in zip(ids,want.items()):
            c["shipments"].append(dict(id=sid,item=item,qty=qty,actual=qty,supplier=sup["id"],cost=costs[item],status="in_transit",day=c["day"],**when_))
        x=c["shipments"][-len(want)]
        eta=inv._eta(x,clk["abs"],c,career,clk)
        promise=eta["window"] if x["lo"]!=x["hi"] else eta["arrives_time"]
        result.update(message=f'Đã đặt {what} · {sum(costs.values())} xu. {sup["name"]} giao {eta["eta_label"][0].lower()+eta["eta_label"][1:]} ({promise}){" trong một chuyến" if len(want)>1 else ""}; kiện tới rồi mới đếm và nhập kho.',
                      eta=dict(eta,shipment=ids[0],shipments=ids))
    elif action=="receive_stock":
        shipment=next((x for x in c["shipments"] if x["id"]==p.get("shipment")),None)
        need(shipment and shipment["status"]!="received","Kiện đã nhận hoặc không tồn tại.")
        # This action's own 20 minutes are already on the clock: what is at the door is
        # what had arrived before it, matching the public ready_now (never a moment early).
        if "at" in shipment:
            door=_clock(c,career,c["turn"]-1)
            if door["abs"]<shipment["at"]:
                eta=inv._eta(shipment,door["abs"],c,career,door)
                need(False,f'Kiện chưa tới. Dự kiến {eta["eta_label"]} ({eta["left_label"]}) — làm việc khác trong lúc chờ nhé.')
        else:need(c["turn"]>shipment["ready"],"Kiện chưa tới. Làm việc khác trong lúc chờ nhé.")
        qty=integer(p.get("count"),1,12);need(qty==shipment["actual"],"Số kiểm đếm chưa khớp số hộp thấy trong kiện.")
        stock_received(s,c,career,shipment,qty);metric(c,"restocked")
        log(s,c,"stock",f'Đã kiểm nhận {qty} × {shipment["item"]}.',ref=shipment["id"])
        result["message"]="Đã kiểm nhận. Chỉ số lượng thực nhận được cộng vào kho."
    elif action=="assistant_help":
        need("assistant" in c["upgrades"],"Bạn chưa có phụ việc.")
        need(c["assistant_day"]!=c["day"],"Bạn phụ việc đã hỗ trợ một lần hôm nay.")
        c["assistant_day"]=c["day"]
        if career in ("mother_baby","pharmacy"):
            now=_now(c,career)
            for shipment in c["shipments"]:
                if shipment["status"]!="received":
                    if "at" in shipment:shipment.update(at=min(shipment["at"],max(now,shipment["placed"])),late=None)
                    else:shipment["ready"]=min(shipment["ready"],c["turn"])
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
            now=_now(c,"accounting");op=inv.hours("accounting")[0]
            t["source_requested"]=True;t["source_at"]=now+40 if c["day"]<=2 else _day_at(c["day"]+1,op+30);metric(c,"source_requests")
            log(s,c,"request","Đã xin đúng phiếu còn thiếu.",t["npc"],t["id"])
            result["message"]=f'Đã xin bổ sung. Người gửi hẹn gửi lúc ~{inv.hm(t["source_at"])}.' if c["day"]<=2 else "Đã xin bổ sung. Người gửi hẹn chụp gửi sáng mai (~"+inv.hm(t["source_at"])+"). Làm việc khác trong lúc chờ nhé."
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
            dcan.ac_match_rules(t,ds,ts)  # game/desk_can.py: the same rules are the view's can.ac_match
            a=sum(docs[x]["amount"] for x in ds)
            t["groups"].append(dict(docs=ds,transactions=ts,total=a));metric(c,"matched")
            log(s,c,"match",f'Đã ghép {", ".join(ds)} với {", ".join(ts)} = {a} xu.',t["npc"],t["id"])
            result["message"]=f"Hai phía khớp {a} xu và cùng tham chiếu nguồn."
        elif action=="ac_unmatch":
            index=integer(p.get("index"),0,len(t["groups"])-1);t["groups"].pop(index)
            result["message"]="Đã tháo nhóm, các thẻ trở lại bàn."
        elif action=="ac_complete":
            dcan.ac_complete_rules(t)  # game/desk_can.py: also the view's can.ac_complete
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
            _cs_fields(t)
            if t["sla_at"] and t["sla"] is None:t["sla"]="ok" if _now(c,career)<=t["sla_at"] else "late"
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
            need(choice in allowed,_cs_reject(t,choice))
            t["proposal"]=choice;t["status"]="proposed";t["timeline"].append("Đã đề xuất: "+choice+". Chưa thực hiện.")
            result["message"]="Phương án phù hợp. Cần xác nhận phối hợp để việc thực sự bắt đầu."
        elif action=="cs_execute":
            need(t["status"]=="proposed" and t["proposal"],"Cần đề xuất hợp lệ trước khi thực hiện.")
            _cs_fields(t);t["ready_at"],t["wait"]=_cs_wait(c,t)
            t["status"]="executing";t["ready_turn"]=0;metric(c,"cs_executed")
            eta=_cs_eta(c,t);days=t["ready_at"]//inv.DAY_MIN-c["day"]
            t["timeline"].append(f'Đã chuyển yêu cầu cho {CS_WAIT_LABEL[t["wait"]]}. Dự kiến có kết quả: {eta}.')
            if t["proposal"]=="refund":log(s,c,"company",f'Yêu cầu hoàn {t["value"]} xu từ quỹ công ty; không trừ hay cộng vào ví của bạn.',t["npc"],t["id"])
            result["message"]=f'Đã giao việc cho {CS_WAIT_LABEL[t["wait"]]}, chưa đóng vụ. Dự kiến có kết quả {eta.lower()}'+(" · vụ sẽ mở qua đêm, sáng mai nhớ gọi cập nhật cho khách." if days>=1 else ". Làm việc khác trong lúc chờ nhé.")
        elif action=="cs_confirm":
            need(t["status"]=="awaiting_confirmation","Chưa có kết quả thực hiện được xác nhận.")
            t["confirmed"]=True;t["status"]="resolved";metric(c,"cs_confirmed")
            t["timeline"].append("Khách/đầu mối đã xác nhận kết quả. Đủ điều kiện đóng.")
            result["message"]="Đã kiểm kết quả với khách. Bây giờ có thể đóng vụ."
        elif action=="cs_close":
            need(t["status"]=="resolved" and t["confirmed"],"Không đóng vụ chỉ vì đã hứa hoặc mới gửi yêu cầu thực hiện.")
            if t.get("promised"):
                t["mistakes"]+=1;t["timeline"].append("Lời hứa quá chắc trong cuộc gọi làm khách kỳ vọng nhiều hơn kết quả thật.")
            task_done(s,c,t,65,"Bạn đã theo dõi, kiểm kết quả và đóng vụ: "+t["title"]+".")
            result.update(message="Khách đã nhận được kết quả · +65 xu thù lao.",celebrate=True)
        elif action=="cs_handover":
            need(t["identity"] and len(t["inspected"])>=2,"Cần xác minh và đọc ít nhất hai nguồn để bàn giao có dữ kiện.")
            need(not t["handed_over"] and t["status"]=="understood","Chỉ bàn giao một lần ở bước kiểm tra, không bỏ ngang phần đã thực hiện.")
            _cs_fields(t);t["handed_over"]=True;t["status"]="handed_over";t["ready_turn"]=0;t["ready_at"]=_now(c,career)+40;t["wait"]="chi_mai";metric(c,"handovers")
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
        need(not u.get('requires') or u['requires'] in c['upgrades'],"Lắp bậc trước rồi nâng tiếp nhé.")
        need(1+c["xp"]//90>=u["min_level"],f'Cần cấp {u["min_level"]}. Hoàn thành thêm vài việc nhé.')
        money(s,c,-u["price"],"Mua "+u["name"]);c["upgrades"].append(item)
        if u["kind"]=="decor":
            metric(c,"decorations");c["decor"][item]=dict(spot={"plant":"window","rug":"center","lamp":"corner","seat":"front","poster":"wall"}.get(item,"window"))
        log(s,c,"upgrade","Đã đặt "+u["name"]+" vào không gian.")
        result.update(message=u["name"]+(" đã lắp, áp dụng cho lượt làm tiếp theo." if u['kind']=='equipment' else " đã xuất hiện trong cảnh."),celebrate=True)
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
                    c["event_history"]=ar.last(c["event_history"],120,"event_history",c)
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
        messages.extend([dict(role="user",text=text),dict(role="npc",text=reply,mode="scripted")]);c["chats"][npc]=ar.last(messages,40,"chat:"+npc,c)
        result.update(message=reply,reply=reply,suggestions=suggestions,npc=npc)
    elif action=="chat_clear":
        npc=p.get("npc");need(npc in NPC_INDEX,"Nhân vật không hợp lệ.")
        c["chats"].pop(npc,None);ar.forget("chat:"+npc,c);result["message"]="Đã xóa lịch sử chat. Ký ức công việc có nguồn vẫn nằm trong Sổ tay."
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
            need(career in REVIEW_FOLLOWUP,"Trả lời review trong mục Phản hồi khách để khách tự quyết định sửa đánh giá nhé.")
            eid=REVIEW_FOLLOWUP[career]
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
        need(image.startswith(("data:image/webp;base64,","data:image/png;base64,","data:image/jpeg;base64,")),"Chỉ nhận ảnh PNG/WebP/JPEG chụp từ cảnh.")  # JPEG: Safari cannot encode WebP (🎓 v4/diploma.js)
        try:raw=base64.b64decode(image.split(",",1)[1],validate=True)
        except (ValueError,IndexError):raise GameError("Ảnh không hợp lệ.")
        need(raw.startswith(b"\x89PNG\r\n\x1a\n") or (raw.startswith(b"RIFF") and raw[8:12]==b"WEBP") or raw.startswith(b"\xff\xd8\xff"),"Ảnh không đúng định dạng.")
        s["seq"]+=1;c["album"].insert(0,dict(id=f"photo-{s['seq']}",image=image,day=c["day"],title=clean_text(p.get("title","Một góc ngày hôm nay"),60)))
        c["album"]=ar.first(c["album"],6,"album",c)
        result["message"]="Đã lưu ảnh trong album nghề này (giữ sáu ảnh gần nhất)."
    elif action=="reset_career":
        need(p.get("confirm")=="BAT DAU LAI","Cần xác nhận trước khi xóa nghề.")
        ar.record([s["careers"][career]],"reset",career)  # the previous record stays in the archive
        pm.forget(s,career)  # 🎖️ the place's steps start again too
        old=s["careers"][career]["money"]
        s["careers"][career]=fresh=initial_career(career)
        if (s.get("journey") or {}).get("story"):
            # The workplace fund carries over (never above the 320 a new place starts with): a reset is no way to
            # refill it after drawing it into the wallet (09/10: reset → start → jr_withdraw 240, again and again).
            fresh["money"]=fresh["day_start_money"]=fresh["ops"]["finance"]["opening_balance"]=min(fresh["money"],old)
        return s,dict(message="Đã bắt đầu lại riêng nghề này.")
    else:raise GameError("Thao tác không được hỗ trợ.","unknown_action")
    life.update_patience(c,action,p,prior_mistakes)
    if career=="mother_baby":gifts.after_action(s,c,action)
    if action=='talk' and p.get('npc') in NPC_INDEX:life.on_talk(c,p['npc'])
    if action=='ask':life.on_talk(c,current_task(c,p.get('task'))['npc'])
    result["effects"]=tick_pending(s,c)
    if career in dk.CAREERS:result["effects"][:0]=dk.tick(s,c,career)
    result["effects"][:0]=care_notes
    result["effects"].extend(care_tick(s,c,career))
    if action not in ("fb_reply","fb_resolve"):result["effects"].extend(fbk.tick(s,c))
    if not (action.startswith("event_") and c.get("event") and c["event"].get("practice")):
        result["effects"].extend(ops.tick(s,c,career,action))
    if action not in ("event_dismiss","event_start","end_day"):director(s,c,career)
    incs.after(s,c,career,action,result)
    haps.after(s,c,career,action,result)
    jr.after(s,career,action,p,result)
    iv.on_life_day(s,result)  # prices, interest and offers move once per life day
    if clock_before is not None and s["careers"][career].get("open"):
        warn=dc.warning(clock_before,dc.minute_now(s["careers"][career],career),s["careers"][career],career)
        if warn:result["clock"]=warn
    result.setdefault("effects",[]).extend(emp.retry_notices(s))  # "Hôm nay (Ngày 5) bạn có thể phỏng vấn lại ở …", once
    bd.after(s,career,action,result)  # nhóm cư dân phố: one beat of neighbourhood posts
    nd.after(s,career,action,result)  # 🍚 no bụng, 😴 tỉnh táo: the shop clock, lunch, the evening, the morning (game/needs.py); before life's day turn so its summary counts the change
    doi.after(s,career,action,result)  # tinh thần, hard days, neighbours (after invest: sees its scam losses)
    cst.after(s,career,action,result)
    qn.after(s,career,action,p,result)  # điểm thân quen: chats, reviews, gifts to you, invites
    if prior_patience is not None:
        for t in s["careers"][career]["tasks"]:
            was=prior_patience.get(t["id"])
            if isinstance(was,int) and isinstance(t.get("patience"),int) and t["patience"]<was:t["patience"]=was
    validate_state(s)
    return s,result


def task_view(t:dict) -> dict:
    return player_services.project(t,_task_view(t))


def _task_view(t:dict) -> dict:
    if t["career"] in extra.NEW_CAREERS or t["career"] in PLUGINS:return life.public_task(t)
    if t.get("desk"):return dk.public_task(t)
    v=tree_copy(t)
    career=t["career"]
    if career in ("mother_baby","pharmacy") and not t["known"]:v["needs"]=None
    if career=="mother_baby" and t.get("gen"):return gifts.public_task(t,v)
    if career=="accounting":
        can=dcan.ac_view(t)  # view only, never saved
        if can:v["can"]=can
        for d in v["docs"]:
            if d["id"] not in t["inspected"]:
                d.pop("original",None);d.pop("duplicate_of",None)
            if d.get("missing"):d["source"]="Chờ bổ sung"
    if career=="customer_care":
        v.pop("solution",None)
        for e in v["evidence"]:
            e["title"]=dk.shown(e.get("title"))  # "Chính sách đổi trả" reads "Chính sách thiếu hàng" (desk.SHOWN_TEXT, never stored)
            if e["id"] not in t["inspected"]:e["text"]=None
        if not t["identity"]:v["value"]=None
    return v


def career_summary(raw:dict,cid:str) -> dict:
    """What the home picker / Phố nghề need from careers that are not open
    on screen. Keeps each response small; the full view arrives with select_career.
    Same values as emp.public(...)["required"/"status"] and bool(inv.public(...))
    (a stock room's view is never empty), without building those full views."""
    return dict(summary=True,started=raw["started"],open=raw["open"],day=raw["day"],xp=raw["xp"],level=1+raw["xp"]//90,money=raw["money"],
                job=dict(required=emp.required(cid),status=raw["job"].get("status")),
                business_running=raw.get('ops',{}).get('business',{}).get('reason')=='working' or player_services.staff_working(raw),
                inventory=raw.get("ext",{}).get("inv") is not None,life=dict(shop_name=raw.get("life",{}).get("shop_name")))


# public_state rebuilds these from the save (None keeps each one's place in the key order).
_PUBLIC_OWN=frozenset(("journey","invest","board","life","stories","closeness","abandon"))
_FOCUS_OWN=frozenset(("ops","situation","incidents","happen","inventory","job","feed","ext","life","day_clock","tasks","event","pending"))

def public_state(s:dict,full:str|None=None,migrated:bool=False) -> dict:
    """Public projection. Only the current career (or `full`) gets the full view.
    `migrated=True`: `s` is a disposable state that apply_action just returned
    (already upgraded), so the defensive migrate copy is skipped.

    Either way `s` here is a private, throw-away save (the caller's, handed over, or
    migrate_state's copy): what the view shows unchanged is not copied again, the view
    holds those very lists and dicts, so nothing below may change them (the view's own
    parts are built fresh or copied before they are edited)."""
    if not migrated:s=migrate_state(s)
    focus=full or s.get("current") or jr.default_career(s)
    v={k:(None if k in _PUBLIC_OWN else x) for k,x in s.items() if k not in ("careers","check")}
    v["careers"]={cid:({k:(None if k in _FOCUS_OWN else x) for k,x in c.items()} if cid==focus else career_summary(c,cid)) for cid,c in s["careers"].items()}
    v["focus"]=focus
    v["journey"]=jr.public(s)
    v["invest"]=iv.public(s)
    v["board"]=bd.summary(s)
    v["life"]=doi.public(s)
    v["needs"]=nd.public(s,focus)  # 🍚😴 (game/needs.py)
    v["chua"]=cg.public(s)  # 🛕 Đi chùa (game/chua.py)
    v["stories"]=cst.public(s)
    v["closeness"]=qn.public(s,focus)
    v["abandon"]=ab.public(s)
    v["fair"]=fh.public(s)  # 🏮 Hội chợ dân gian (game/fair.py)
    v["jail"]=jl.public(s)  # 🚔 Trại tạm giữ (game/jail.py): None when free
    v["x3"]=x3w.public()  # 🔥 Nghề x3 trong tuần (game/x3_week.py)
    v["market"]=staff_market_.public()  # 📈 lãi nhân viên theo thị trường + 🔥 nghề hot hôm nay (game/staff_market.py)
    v["rui"]=rui_.public(s)  # 🛡️ Rủi ro & bảo hiểm (game/rui.py): the warning, the card, the policies
    v["vang"]=vang_.public(s)  # 💰 Tiệm vàng (game/vang.py): today's price, the chart, the gold held
    v['accounting_school']=accounting_school_.summary(s)  # small: the school's own view rides on as_* results
    for cid,c in v["careers"].items():
        if c.get("summary"):continue
        raw=s["careers"][cid];mod=PLUGINS.get(cid)
        c["ops"]=ops.public_operations(raw,cid)
        c["situation"]=sit.public(raw,cid)
        c["incidents"]=incs.public(raw,cid,s)
        c["happen"]=haps.public(raw,cid,s)
        c["inventory"]=inv.public(raw,cid)
        c["job"]=emp.public(raw,cid,s)
        c["promo"]=pm.public(s,raw,cid)  # 🎖️ Thăng tiến; the 🧑‍💼 board while a manager shift runs

        c["data"]=mod.public_data(raw) if mod and hasattr(mod,'public_data') else tree_copy(raw["ext"]["data"])
        if cid in CARE_CAREERS:
            cp=care_public(raw,cid)
            if cp is None:c["data"].pop("care",None)
            else:c["data"]["care"]=cp
        if cid=="teacher":
            from . import classroom
            c["classroom"]=classroom.public(raw);c["data"].pop("class",None);c["data"].pop("homeroom",None)
        if cid in ("milk_tea","mother_baby"):life.public_counter(raw,cid,c["data"])
        c["feed"]=[fbk.public_post(f,cid,raw.get("day")) for f in raw["feed"]]
        c["feedback_stats"]=fbk.stats(raw)
        c.pop("ext",None)
        c["life"]=life.public_life(s["careers"][cid])
        c["day_clock"]=dc.view(raw,cid)  # giờ trong ngày: HUD clock, closing warnings, the scene's light
        c["ot"]=None if pm.managing(s,raw,cid) else ovt.public(raw,cid)  # ⏱️ the work screen's overtime chip (view only)
        gate=more_gate(raw,cid,1) if raw.get("open") else None
        if raw.get("open") and pm.managing(s,raw,cid):gate=dict(why="manager",error="Hôm nay bạn làm quản lý: giao việc cho đội nhé.")  # 🧑‍💼 no "Đón thêm khách"
        c["more_gate"]={k:v for k,v in gate.items() if k!="error"} if gate else None  # "Đón thêm khách" or the next real step
        c["tasks"]=[task_view(t) for t in s["careers"][cid]["tasks"]]
        if cid=="teacher":
            from . import teach_lesson as tl_,teach_grades as tg_
            hg=tg_.homeroom(raw)  # 🏫 lớp 2–5: periods not started yet show the homeroom's lesson (view only)
            for tv,t in zip(c["tasks"],raw["tasks"]):tl_.preview(t,tv,hg)
        if cid=="pharmacy":
            for tv,t in zip(c["tasks"],raw["tasks"]):
                can=dcan.ph_view(t,raw)  # can.ph_check: the tray against the slip (view only, never saved)
                if can:tv["can"]=can
        if cid in CARE_CAREERS:
            care_lines=care_notices(raw,cid)
            for tv,t in zip(c["tasks"],raw["tasks"]):
                if t.get("desk") and care_lines and t["status"] not in ("completed","referred","cancelled") and isinstance(tv.get("bulletin"),list):tv["bulletin"]=care_lines+tv["bulletin"]
                if cid=="customer_care" and _cs_classic(t):cs_task_public(raw,t,tv)
        c["level"]=1+c["xp"]//90;c["xp_in_level"]=c["xp"]%90
        c["event"]=event_view(raw["event"])
        c["available"]={k:available(s["careers"][cid],k) for k in c["stock"]}
        c["quest_progress"]=[]
        for q in QUESTS:
            if q["career"]==cid:
                c["quest_progress"].append(dict(id=q["id"],claimed=q["id"] in c["quests_claimed"],
                    ready=all(c["metrics"].get(st["metric"],0)>=st["goal"] for st in q["steps"]),
                    steps=[dict(st,current=c["metrics"].get(st["metric"],0),done=c["metrics"].get(st["metric"],0)>=st["goal"]) for st in q["steps"]]))
        reviews=[f["stars"] for f in c["feed"] if f.get("stars")]
        c["rating"]=round(sum(reviews)/len(reviews),1) if reviews else None
        c["pending"]=[{k:x for k,x in pending.items() if k!="text"} for pending in raw["pending"]]
        if cid in ("mother_baby","pharmacy"):c["shipments"],c["stock_desk"]=_stock_view(raw,cid)
    return v


_TEMPLATE_KEYS:dict={}

def _template_keys(cid:str) -> tuple[frozenset,frozenset]:
    """Keys every career record (and its `ext`) must have: those of initial_career."""
    keys=_TEMPLATE_KEYS.get(cid)
    if keys is None:
        template=initial_career(cid)
        keys=_TEMPLATE_KEYS[cid]=(frozenset(template),frozenset(template["ext"]))
    return keys

_LEAVES=(str,int,bool,type(None))

def _finite(obj) -> None:
    """No NaN/Infinity anywhere (plain leaves are skipped without a call)."""
    if isinstance(obj,float):need(math.isfinite(obj),"Bản lưu chứa số không hữu hạn.")
    elif isinstance(obj,dict):
        for value in obj.values():
            if type(value) not in _LEAVES:_finite(value)
    elif isinstance(obj,list):
        for value in obj:
            if type(value) not in _LEAVES:_finite(value)

# Display-only fields added to generated tasks in a later release. A task made before that release
# lacks them, and must still match its regenerated original (0.9.6 added "ask" and "told" to clothing lines).
LATE_TASK_KEYS=frozenset({"ask","told"})

def _without_late_keys(original,stored):
    """`original` minus the LATE_TASK_KEYS that `stored` does not have, at every level."""
    if isinstance(original,dict) and isinstance(stored,dict):
        return {k:_without_late_keys(v,stored.get(k)) for k,v in original.items() if not (k in LATE_TASK_KEYS and k not in stored)}
    if isinstance(original,list) and isinstance(stored,list) and len(original)==len(stored):
        return [_without_late_keys(a,b) for a,b in zip(original,stored)]
    return original

def validate_state(s:dict) -> None:
    """Structural and economic invariants, also run on imported save envelopes.

Import is single-player backup, not a competitive anti-cheat boundary. Keys,
workflow references, quantities and maximum sizes are validated before commit.

Inside apply_action(scoped=True) (the storage layer, on a save this build already
validated) only what lies outside the careers is checked here: the storage layer
then runs validate_career on every career the command changed (see Store._compute).
"""
    need(isinstance(s,dict) and s.get("schema")==4,"Phiên bản bản lưu không được hỗ trợ.","invalid_save")
    need(set(s.get("careers",{}))==set(CAREERS),"Bản lưu cần đủ các nghề.","invalid_save")
    need(s.get("current") in CAREERS or s.get("current") is None,"Nghề trong bản lưu không hợp lệ.")
    clean_text(s.get("name"),24);integer(s.get("seq"),0,10**9)
    jr.validate(s)
    if _SCOPED.get() is not True:accounting_school_.validate(s)  # scoped commands: only as_* commands change it (they validate it themselves)
    history_course_.validate(s)  # small (12 lessons, one paper): checked on every command, scoped or not
    iv.validate(s)
    bd.validate(s)
    doi.validate(s)
    cst.validate(s)
    qn.validate(s)
    ab.validate(s)
    settings=s.get("settings",{});need(settings.get("mode") in ("relaxed","everyday","challenge"),"Chế độ bản lưu không hợp lệ.")
    for k in ("sound","music","reduceMotion","largeText","aiConsent","aiAsked","aiNoticeSeen","securityEvents","notify","publicProfile"):need(type(settings.get(k)) is bool,"Thiếu thiết lập bản lưu.")
    for k,choices in SETTING_CHOICES.items():need(settings.get(k) in choices,"Thiết lập bản lưu không hợp lệ.")
    for k in ("musicVolume","sfxVolume"):integer(settings.get(k),0,100)
    for k in ("npcVoices","detailSfx","bankVoice","moneyTing"):need(type(settings.get(k,True)) is bool,"Thiết lập bản lưu không hợp lệ.")
    need(set(settings)<=set(default_settings()),"Thiết lập lạ trong bản lưu.")
    need(type(settings.get("tutorialDone",False)) is bool,"Thiết lập bản lưu không hợp lệ.");notes_seen(settings.get("notesSeen",""))
    need(wn.valid_seen(settings.get("whatsNewSeen","")),"Thiết lập bản lưu không hợp lệ.")
    if _SCOPED.get():
        for k,value in s.items():
            if k!="careers":_finite(value)
        return
    for cid,c in s["careers"].items():validate_career(c,cid,finite=False)
    _finite(s)  # no NaN/Infinity anywhere


def scoped_validation(s:dict) -> None:
    """validate_state of everything outside the careers, the accounting school's block included,
    for a writer outside apply_action on a save stamped by this build (marriage._mutate): it
    then validates each career it changed (storage.serialize_bytes(known=...)); the others are
    byte for byte records that passed."""
    token=_SCOPED.set("outside_careers")
    try:validate_state(s)
    finally:_SCOPED.reset(token)


def _feed_author(value) -> bool:
    # Large histories must not rebuild and linearly scan the entire NPC catalogue
    # for every post/comment. Keep malformed JSON values on the GameError path.
    return isinstance(value,str) and (value=="player" or value in NPC_INDEX)


def validate_career(c:dict,cid:str,finite:bool=True,same:frozenset=frozenset()) -> None:
    """Every check of one career record. It reads only that record and the fixed
    content, so a record equal to one that passed with this build still passes.

    `same` (game/settle_scope.py): keys of c, and "ops.<key>" of c["ops"], whose value is
    byte for byte (JSON) the value of the stored record that passed these checks with this
    build. A group of checks that reads only such values passes again and is skipped: the
    per-task regeneration, the long lists (reviews, chats, journal, memories, album, ...) and
    the cash book's rows. Everything else runs, in the same order, so a record that fails
    fails with the same message. Empty (the default): every check runs."""
    from . import consequences as cq
    from . import classroom
    need(isinstance(c,dict),"Tiến trình nghề không hợp lệ.")
    player_services.validate_staff(c,cid)
    template_keys,ext_keys=_template_keys(cid)
    ops.validate(c,cid,same)
    life.validate(c,cid)
    ext=c.get("ext");need(isinstance(ext,dict) and ext_keys<=set(ext),"Bản lưu thiếu dữ liệu v0.4.")
    integer(ext.get("seq"),0,10**9);need(isinstance(ext.get("data"),dict),"Dữ liệu nghề không hợp lệ.")
    sit.validate(c,cid);inv.validate(c,cid);emp.validate(c,cid);incs.validate(c,cid);haps.validate(c,cid)
    cq.validate(c)  # complaints book (optional in older saves)
    fbk._ra.validate_recent(c)  # recent review aspects (optional in older saves)
    if cid in PLUGINS and hasattr(PLUGINS[cid],"validate_data"):PLUGINS[cid].validate_data(c)
    if cid in dk.CAREERS:dk.validate_data(c)
    care_validate(c,cid)  # nhiều ngày: sổ khách quen, sổ lô, tủ hồ sơ, bảng theo dõi, kiện theo giờ
    if cid=="teacher":classroom.validate(c)
    need(template_keys<=set(c),"Bản lưu thiếu trường tiến trình.")
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
    need(all(cid in UPGRADE_INDEX[u].get('careers',CAREERS) for u in c['upgrades'] if UPGRADE_INDEX[u].get('kind')=='equipment'),"Thiết bị không thuộc nghề này.")
    need(all(not UPGRADE_INDEX[u].get('requires') or UPGRADE_INDEX[u]['requires'] in c['upgrades'] for u in c['upgrades']),"Thiết bị thiếu bậc trước.")
    need(all(l in LOT_INDEX for l in c["held_lots"]),"Lô tạm giữ không hợp lệ.")
    need(len(c["tasks"])<=80,"Quá nhiều công việc trong bản lưu.")
    taskids=[]
    for t in (() if "tasks" in same else c["tasks"]):  # same tasks: the regeneration below passes again
        player_services.validate(t)
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
        if cid == 'cafe_bakery':
            # Expanded menu applies to new orders; old tickets keep their recipe.
            original = PLUGINS[cid].make_task(t['day'], slot, t['created_turn'], legacy=t.get('gen', 1) < 3)
        need(t["id"]==original["id"],"Mã công việc sai ngày.")
        need(set(original)<=set(t),"Bản lưu thiếu trường công việc.")
        for key in ("npc","title","opening","kind","needs","variant","solution","value","evidence"):
            # Milk tea: the counter relabels guests and re-rolls orders; boba.validate_task checks them.
            if cid=="milk_tea" and key in ("title","opening","needs"):continue
            if key in original:need(t.get(key)==original[key] or t.get(key)==_without_late_keys(original[key],t.get(key)),"Dữ kiện gốc của nhiệm vụ không hợp lệ: "+key)
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
    if "tasks" in same:taskids=[t["id"] for t in c["tasks"]]
    need(len(taskids)==len(set(taskids)),"Công việc bị trùng mã.")
    need(c["active_task"] is None or c["active_task"] in taskids,"Công việc đang chọn không tồn tại.")
    for k in c["stock"]:need(available(c,k)>=0,"Hàng đã giữ nhiều hơn tồn kho.")
    if c["event"]:
        e=c["event"];need(e.get("script") in SCRIPTS and SCRIPTS[e["script"]]["career"]==cid,"Tình huống bản lưu không hợp lệ.")
        need(e.get("stage") in ("noticed","investigating","proposed","executing","resolved"),"Bước sự kiện sai.")
        need(e.get("chosen") in (None,"a","b") and isinstance(e.get("read"),list) and type(e.get("practice")) is bool,"Dữ liệu sự kiện thiếu.")
        integer(e.get("step"),0,2)
    for f in (() if "feed" in same else c["feed"]):
        need(isinstance(f,dict) and _feed_author(f.get("npc")) and isinstance(f.get("comments"),list),"Bài đăng không hợp lệ.")
        clean_text(f.get("text"),3000);clean_text(f.get("id"),100)
        need(f.get("stars") in (None,1,2,3,4,5),"Số sao không hợp lệ.")
        fbk.validate_post(f)
    for npc,chat in (() if "chats" in same else c["chats"].items()):
        need(npc in NPC_INDEX and isinstance(chat,list) and len(chat)<=40,"Chat bản lưu không hợp lệ.")
        for row in chat:need(row.get("role") in ("user","npc"),"Vai chat không hợp lệ.");clean_text(row.get("text"),2000)
    need(isinstance(c["relationships"],dict) and isinstance(c["decor"],dict),"Dữ liệu quan hệ/trang trí không hợp lệ.")
    for key,value in c["relationships"].items():need(key in NPC_INDEX and NPC_INDEX[key]["career_id"]==cid,"Quan hệ sai nghề.");integer(value,0,100)
    for key,value in c["metrics"].items():clean_text(key,150);integer(value,0,10**9)
    for item,position in c["decor"].items():
        need(item in c["upgrades"] and UPGRADE_INDEX[item]["kind"]=="decor" and isinstance(position,dict),"Món trang trí chưa sở hữu.")
        need(position.get("spot") in ("window","corner","front","center","wall"),"Vị trí trang trí không hợp lệ.")
    for shipment in (() if "shipments" in same else c["shipments"]):
        need(isinstance(shipment,dict) and shipment.get("item") in expected_items,"Kiện hàng sai mã.")
        clean_text(shipment.get("id"),100);integer(shipment.get("qty"),1,6);integer(shipment.get("actual"),1,6);integer(shipment.get("cost"),0,10000)
        if "at" not in shipment:integer(shipment.get("ready"),0,10**9)
        need(shipment.get("status") in ("in_transit","received"),"Trạng thái kiện sai.")
    for pending in (() if "pending" in same else c["pending"]):
        need(isinstance(pending,dict) and pending.get("kind") in ("return_note","event_followup","comment"),"Thông báo chờ không hợp lệ.")
        integer(pending.get("day"),1,999999);integer(pending.get("turn"),0,10**9);clean_text(pending.get("ref"),200);clean_text(pending.get("text"),3000)
        need(pending.get("npc") in NPC_INDEX,"Thông báo thiếu nhân vật.")
    for memory in (() if "memories" in same else c["memories"]):
        need(isinstance(memory,dict) and memory.get("npc") in NPC_INDEX,"Ký ức sai nhân vật.")
        clean_text(memory.get("text"),3000);clean_text(memory.get("source"),200)
    for row in (() if "journal" in same else c["journal"]):
        for key in ("id","kind","text"):clean_text(row.get(key),4000)
        integer(row.get("day"),1,999999);integer(row.get("turn"),0,10**9)
    for post in (() if "feed" in same else c["feed"]):
        for key in ("author","source","kind"):clean_text(post.get(key),200)
        integer(post.get("day"),1,999999);need(type(post.get("liked")) is bool,"Trạng thái bài đăng thiếu.")
        for comment in post["comments"]:
            clean_text(comment.get("author"),100);clean_text(comment.get("text"),3000);integer(comment.get("day"),1,999999)
            need(_feed_author(comment.get("npc")),"Người bình luận không hợp lệ.")
    need(len(c["album"])<=6,"Album quá lớn.")
    for photo in (() if "album" in same else c["album"]):
        need(isinstance(photo.get("image"),str) and len(photo["image"])<=450000 and photo["image"].startswith(("data:image/webp;base64,","data:image/png;base64,","data:image/jpeg;base64,")),"Ảnh lưu không hợp lệ.")
    nullfree=getattr(same,"nullfree",None)
    if finite and nullfree:  # values whose JSON has no null cannot hold NaN/Infinity (orjson writes them as null)
        for k,value in c.items():
            if k in nullfree or type(value) in _LEAVES:continue
            if k=="ops" and type(value) is dict:  # its values are pieces too ("ops.<key>")
                for x,y in value.items():
                    if "ops."+x not in nullfree and type(y) not in _LEAVES:_finite(y)
            else:_finite(value)
    elif finite:_finite(c)  # no NaN/Infinity


# =====================================================================================
# The three original desk careers over several days, and the legacy stock on the shop
# clock. Pharmacy: regulars' refills, lot use-by/recall rotation, the fridge log,
# twice-daily distributor runs. Bookkeeping: client books every month with a client file
# and close deadlines. Support: cases that wait days for the warehouse/carrier, SLA
# timers, caller history, satisfaction trend, yesterday's handover and AI-voiced calls.
# Everything is server-side and seeded from ids/days; the raw record holds no secrets.
# See docs/superpowers/specs/2026-09-29-desk-careers-care-ai-design.md.
# =====================================================================================
CARE_CAREERS=("pharmacy","accounting","customer_care")
CARE_ACTIONS={"ph_care_call","ph_care_hand","ph_fridge_log","ph_fridge_fix","ph_lot_pull",
    "ac_book_open","ac_book_check","ac_book_chase","ac_book_close","cs_call","cs_handover_read"}
CARE_FREE={"cs_call","cs_handover_read"}  # a call ticks the clock itself (first line of the day only)


def _key(v:Any)->str|None:
    """Ids from a payload are plain strings; anything else matches nothing."""
    return v if isinstance(v,str) and len(v)<=80 else None


def _rng(*parts)->random.Random:
    return random.Random("|".join(str(p) for p in parts))


def _clock(c:dict,career:str,turn:int|None=None)->dict:
    """inventory.clock, anchored on the day's first dealt task when the 'Mở ca' row is missing."""
    clk=inv.clock(c,career,turn)
    if clk["is_open"] and inv._turn0(c) is None:
        op,cl=inv.day_hours(c,career)
        t=c["turn"] if turn is None else turn
        dealt=[x["created_turn"] for x in c.get("tasks",[]) if isinstance(x,dict) and x.get("day")==c["day"] and type(x.get("created_turn")) is int]
        t0=min(dealt) if dealt else t
        minute=max(op,min(cl,op+max(0,t-t0)*inv.STEP))
        clk.update(minute=minute,abs=clk["day"]*inv.DAY_MIN+minute)
    return clk


def _now(c:dict,career:str)->int:
    return _clock(c,career)["abs"]


def _day_at(day:int,minute:int)->int:
    return day*inv.DAY_MIN+minute


def _left(minutes:int)->str:
    minutes=max(0,int(minutes))
    if minutes<60:return f"{minutes} phút"
    h,m=divmod(minutes,60)
    return f"{h} giờ"+(f" {m} phút" if m else "")


def _clock_view(c:dict,career:str)->dict:
    clk=_clock(c,career)
    return dict(day=clk["day"],minute=clk["minute"],abs=clk["abs"],time=inv.hm(clk["minute"]),open=inv.hm(clk["open"]),close=inv.hm(clk["close"]),is_open=clk["is_open"],
        label=f'Bây giờ {inv.hm(clk["minute"])}' if clk["is_open"] else f'Đã đóng cửa · mở lại {inv.hm(clk["open"])}')


def _care(c:dict)->dict|None:
    d=(c.get("ext") or {}).get("data")
    return d.get("care") if isinstance(d,dict) else None


def _risk(c:dict,n:int)->None:
    """Care slips feed the desk inspection (every few days) like a hasty stamp would."""
    if n>0 and c["ext"]["data"].get("desk") is not None:
        d=dk.data(c);d["risk"]=min(99,d["risk"]+n)


def _care_log(care:dict,day:int,text:str)->None:
    care["log"]=ar.last(care["log"]+[dict(day=day,text=text[:300])],30,"care.log")


# ---------------------------------------------------------------- legacy stock on the shop clock
STOCK_SUPPLIERS={
    "mother_baby":[
        dict(inv.MARKET,name="Chợ sỉ đồ sơ sinh",emoji="🧺",short=0,
             note="Rẻ nhất (×0,85). Đặt trước 13:00, hàng tới chiều nay; đặt sau, hàng tới sáng mai trước giờ mở cửa."),
        dict(inv.PARTNER,short=0,note="Giá niêm yết. Bốn chuyến mỗi ngày: đặt trước 09:00, 12:00, 15:00 hoặc 18:00, hàng tới sau đó khoảng một tiếng."),
        dict(inv.EXPRESS,short=0,note="Đắt nhất (×1,35) nhưng tới trong 15–30 phút."),
    ],
    "pharmacy":[
        dict(inv.PARTNER,name="Nhà phân phối Thiện Tâm",emoji="🚚",short=0,
             voice=dict(inv.V_PARTNER,late="Xe Thiện Tâm kẹt ở cầu Mây, bên em báo trễ chừng nửa tiếng tới một tiếng ạ."),
             note="Xe phân phối chạy bốn chuyến mỗi ngày: đặt trước 09:00, 12:00, 15:00 hoặc 18:00, hàng tới sau đó khoảng một tiếng. Giá niêm yết."),
        dict(inv.MARKET,id="depot",name="Kho tổng Bình An",emoji="🏬",factor=0.85,short=0,late=6,
             voice=dict(inv.V_FAR,late="Xe của kho tổng về trễ, hàng tới muộn hơn hẹn."),
             note="Rẻ hơn (×0,85). Đặt trước 13:00, xe kho giao chiều nay; đặt sau, xe đêm giao trước giờ mở cửa sáng mai."),
    ],
}
STOCK_DEFAULT="partner"
STOCK_LINES=12   # lines (one per item) in one merged order_stock
STOCK_VANS=8     # deliveries on the way: the lines of one merged order share a van


def stock_vans(c:dict)->int:
    """Deliveries on the way. Lines of a merged order share placed time, arrival and supplier: one van."""
    return len({(x.get("supplier"),x["placed"],x["at"]) if "at" in x else x["id"] for x in c["shipments"] if x["status"]=="in_transit"})


def stock_suppliers(career:str)->list[dict]:
    return STOCK_SUPPLIERS.get(career,[])


def _stock_supplier(career:str,sid:Any)->dict|None:
    return next((x for x in stock_suppliers(career) if x["id"]==sid),None)


def shipment_here(c:dict,career:str,x:dict,turn:int|None=None)->bool:
    """A parcel can be counted once the shop clock has reached its arrival."""
    if x.get("status")!="in_transit":return False
    if "at" not in x:return type(x.get("ready"))is int and x["ready"]<c["turn"]
    return _clock(c,career,turn)["abs"]>=x["at"]


def _upgrade_shipments(c:dict,career:str)->None:
    """Parcels from before the shop clock carry `ready` (a turn): turn the beats still
    to wait into shop minutes from now (after closing → the next morning)."""
    now=None
    for x in c.get("shipments") or []:
        if not isinstance(x,dict) or "at" in x or type(x.get("ready")) is not int:continue
        if now is None:now=_now(c,career)
        ready=x.pop("ready")
        left=max(0,ready-c["turn"]) if x.get("status")=="in_transit" else 0
        at=inv._after_hours(now+left*inv.STEP,career) if left else now
        x.update(supplier=x.get("supplier") or STOCK_DEFAULT,placed=now,lo=at,hi=at,at=at,late=None,day=x.get("day") if type(x.get("day")) is int else c["day"])


def _stock_view(c:dict,career:str)->tuple[list,dict]:
    clk=_clock(c,career);now=clk["abs"]
    rows=[]
    for x in c["shipments"]:
        v=dict(x);sup=_stock_supplier(career,x.get("supplier")) or inv.PARTNER
        v.update(supplier_name=sup["name"],supplier_emoji=sup.get("emoji","🚚"))
        if "at" in x:
            v.update(inv._eta(x,now,c,career,clk))
            v["ready_now"]=x["status"]=="in_transit" and now>=x["at"]
            if x["status"]=="in_transit":
                if not v["ready_now"]:v.pop("at",None);v["actual"]=None
                v.pop("late",None)
        else:v["ready_now"]=shipment_here(c,career,x)
        rows.append(v)
    placing=_clock(c,career,c["turn"]+1)["abs"]
    sups=[dict({k:v for k,v in sp.items() if k not in ("runs","mins","at","days","cutoff","day_run","delay","voice")},window=inv._window_label(sp,career),quote=inv.quote(sp,career,placing))
          for sp in stock_suppliers(career)]
    return rows,dict(clock=_clock_view(c,career),suppliers=sups,default=STOCK_DEFAULT)


def stock_received(s:dict,c:dict,career:str,x:dict,qty:int)->None:
    """Counted goods go on the shelf; pharmacy boxes get their own use-by date."""
    x["status"]="received";c["stock"][x["item"]]+=qty
    if career=="pharmacy" and qty and _care(c) is not None:
        care=_care(c)
        _ph_batch(care,x["item"],qty,c["day"]+_rng("ph-exp",x["id"]).randint(8,14),c["day"])
        _ph_sync(c,care)
    received=[y for y in c["shipments"] if y.get("status")=="received"]
    if len(received)>40:
        ar.record(received[:len(received)-40],"shipments",c)
        drop={id(y) for y in received[:len(received)-40]}
        c["shipments"]=[y for y in c["shipments"] if id(y) not in drop]


def _stock_tick(s:dict,c:dict,career:str)->list[str]:
    """Say once when a parcel reaches the door."""
    notes=[]
    for x in c["shipments"]:
        if x.get("status")=="in_transit" and "at" in x and not x.get("told") and shipment_here(c,career,x):
            x["told"]=True
            name=PRODUCT_INDEX[x["item"]]["name"] if x["item"] in PRODUCT_INDEX else x["item"]
            notes.append(f'📦 Kiện {x["qty"]} × {name} đã tới cửa kho. Mở Kho để đếm và nhập.')
    return notes


# ---------------------------------------------------------------- pharmacy: Quầy Bình An
PH_REGULARS=(
    dict(id="nam",name="Bác Năm",npc="pharmacy_npc_02",emoji="👴",product="P-02",qty=1,every=5,first=1,note="Phiếu lặp lại của phòng khám: một Hộp Lá mỗi đợt."),
    dict(id="tu",name="Bà Tư",npc=None,emoji="👵",product="P-03",qty=2,every=4,first=2,note="Hai Hộp Mây xanh mỗi đợt; bà hay quên lịch."),
    dict(id="man",name="Chị Mận",npc=None,emoji="👩",product="P-05",qty=1,every=6,first=3,note="Hộp Nắng để tủ mát; chị ghé sau giờ làm."),
    dict(id="loc",name="Chú Lộc",npc=None,emoji="🧔",product="P-06",qty=1,every=7,first=4,note="Bộ vật dụng thay băng theo phiếu của trạm y tế."),
)
PH_REG={r["id"]:r for r in PH_REGULARS}
PH_COLD=("P-05",)
PH_PAY=30
PH_SHELF_RISK_CAP=2  # risk points a day for bad boxes left on the shelf at close (#273)
PH_UNIT=8
FRIDGE_SLOTS={"am":dict(label="Sáng",until=12*60,since=None),"pm":dict(label="Chiều",until=None,since=14*60)}
FRIDGE_FIX={"door":"Đóng kín cửa tủ, dán lại ron, đo lại sau một giờ","move":"Chuyển hộp lạnh sang tủ dự phòng, gọi thợ điện (15 xu)"}
FRIDGE_CLUE={"door":"Cửa tủ khép chưa kín, ron cao su bong một góc; máy vẫn chạy êm.",
             "power":"Đèn trong tủ tắt, không nghe tiếng máy nén; ổ cắm lỏng sau cơn mưa."}
RECALL_EVERY=6
RECALL_WHY=("Nhà sản xuất báo in sai số lô trên vỏ hộp.","Kho tổng báo lô này bị ẩm trong lúc vận chuyển.","Nhà phân phối thu hồi để kiểm lại tem niêm phong.")


def _ph_fresh(day:int)->dict:
    start=max(2,day)
    return dict(v=1,start=start,seq=0,batches=[],
        regulars={r["id"]:dict(due=start+r["first"],called=False,trust=2,visits=0,missed=0,last=None,hist=[]) for r in PH_REGULARS},
        fridge=dict(day=0,logs={}),flog=[],notices=[],recalls=[],waste=0,log=[])


def _ph_batch(care:dict,lot:str,qty:int,exp:int,got:int)->dict:
    care["seq"]+=1
    b=dict(id=f'L{care["seq"]:03d}',lot=lot,qty=qty,exp=exp,got=got,recalled=None,warm=False)
    care["batches"].append(b)
    return b


def _ph_open_lots()->list[str]:
    return [lid for lid,l in LOT_INDEX.items() if l["status"]=="available"]


def _ph_sync(c:dict,care:dict)->None:
    """Batches (use-by dates) always add up to the shelf count of each valid lot. Stock
    that left through other doors (a helper, a loss) goes first-expiry-first-out."""
    for lid in _ph_open_lots():
        have=c["stock"].get(lid,0);rows=sorted((b for b in care["batches"] if b["lot"]==lid),key=lambda b:(b["exp"],b["got"],b["id"]))
        total=sum(b["qty"] for b in rows)
        if total<have:
            _ph_batch(care,lid,have-total,c["day"]+10,c["day"])
        extra=total-have
        for b in rows:
            if extra<=0:break
            used=min(extra,b["qty"]);b["qty"]-=used;extra-=used
    care["batches"]=ar.last([b for b in care["batches"] if b["qty"]>0],80,"care.batches",c)


def _ph_init(c:dict)->dict:
    care=_ph_fresh(c["day"])
    for lid in _ph_open_lots():
        have=c["stock"].get(lid,0)
        if not have:continue
        r=_rng("ph-open",lid)
        if LOT_INDEX[lid]["product"] in ("P-02","P-05") and have>2:
            _ph_batch(care,lid,2,c["day"]+2,c["day"]);have-=2
        _ph_batch(care,lid,have,c["day"]+r.randint(8,12),c["day"])
    c["ext"]["data"]["care"]=care
    return care


def ph_care(c:dict,create:bool=True)->dict|None:
    care=_care(c)
    if care is None and create:care=_ph_init(c)
    return care


def _ph_flag(b:dict,day:int)->str|None:
    if b["recalled"]:return "recalled"
    if b["warm"]:return "warm"
    if b["exp"]<day:return "expired"
    return None


def ph_shelf_block(c:dict,lid:str)->str|None:
    """Nothing leaves a lot while a box on that shelf is out of date, recalled or warmed."""
    care=_care(c)
    if not care or LOT_INDEX.get(lid,{}).get("status")!="available":return None
    bad=[b for b in care["batches"] if b["lot"]==lid and b["qty"]>0 and _ph_flag(b,c["day"])]
    if not bad:return None
    why={"expired":"quá hạn dùng","recalled":"bị thu hồi","warm":"hỏng do tủ mát ấm"}
    n=sum(b["qty"] for b in bad)
    return f'Kệ {lid} còn {n} hộp {why[_ph_flag(bad[0],c["day"])]} ({bad[0]["id"]}). Rút khỏi kệ trước: Kho → Sổ lô.'


def _ph_here(r:dict,day:int)->bool:
    return (r["called"] and r["due"]<=day<=r["due"]+1) or day==r["due"]+1


def _ph_fridge_today(care:dict,day:int)->dict:
    if care["fridge"]["day"]!=day:care["fridge"]=dict(day=day,logs={})
    return care["fridge"]


def _fridge_reading(day:int,slot:str)->tuple[int,str|None]:
    """About one day in four (from day 3) one of the two readings is above 8°C."""
    r=_rng("fridge",day,slot);temp=r.randint(30,72);cause=None
    d=_rng("fridge-day",day)
    if day>=3 and d.random()<0.25 and d.choice(tuple(FRIDGE_SLOTS))==slot:
        temp=r.randint(86,104);cause=d.choice(("door","power"))
    return temp,cause


def _deg(t:int)->str:
    return f'{t//10},{t%10}°C'


def _ph_action(s:dict,c:dict,action:str,p:dict)->dict:
    care=ph_care(c);_ph_sync(c,care);day=c["day"]
    if action=="ph_care_call":
        r=care["regulars"].get(_key(p.get("who")));need(r,"Không có khách quen này.");spec=PH_REG[p["who"]]
        need(r["due"]-1<=day<=r["due"],"Chưa tới lịch nhắc. Gọi nhắc từ hôm trước ngày hẹn tới đúng ngày hẹn.")
        need(not r["called"],"Đã gọi nhắc đợt này rồi.")
        r["called"]=True;metric(c,"refill_calls")
        when="hôm nay" if r["due"]<=day else "mai"
        _care_log(care,day,f'Gọi nhắc {spec["name"]} lấy phiếu lặp lại ({spec["product"]} × {spec["qty"]}).')
        return dict(message=f'Đã gọi nhắc {spec["name"]}: {"sẽ ghé " + when}. Nhớ để sẵn {spec["qty"]} × {spec["product"]} trên kệ.')
    if action=="ph_care_hand":
        r=care["regulars"].get(_key(p.get("who")));need(r,"Không có khách quen này.");spec=PH_REG[p["who"]]
        need(_ph_here(r,day),"Khách chưa tới quầy. Gọi nhắc đúng lịch, khách sẽ ghé trong ngày hẹn." if day<r["due"]+1 else "Khách chưa tới.")
        need(p.get("confirm") is True,"Xác nhận giao phiếu lặp lại trước nhé.")
        lid=spec["product"]+"-A"
        need(lid not in c["held_lots"],f"Lô {lid} đang tạm giữ. Cô Thu kiểm lại trước khi xuất.")
        block=ph_shelf_block(c,lid);need(not block,block or "")
        need(available(c,lid)>=spec["qty"],f'Kệ {lid} chỉ còn {max(0,available(c,lid))} hộp sẵn xuất, khách cần {spec["qty"]}. Đặt chuyến phân phối nhé.')
        c["stock"][lid]-=spec["qty"];_ph_sync(c,care)
        on_time=r["called"] and day<=r["due"]
        r["trust"]=min(5,r["trust"]+1) if on_time else r["trust"]
        r.update(visits=r["visits"]+1,last=day,due=day+spec["every"],called=False)
        r["hist"]=ar.last(r["hist"]+[[day,"ok" if on_time else "late"]],6,"care.regular."+str(p["who"]),c)
        pay=PH_PAY+(5 if on_time and r["trust"]>=3 else 0)
        money(s,c,pay,"Phiếu lặp lại · "+spec["name"],"refill-"+spec["id"],"revenue")
        metric(c,"refills");c["xp"]+=6
        _care_log(care,day,f'Giao {spec["qty"]} × {lid} cho {spec["name"]}'+(" đúng hẹn." if on_time else " (khách quên lịch, tới trễ)."))
        return dict(message=f'Đã giao {spec["qty"]} × {lid} cho {spec["name"]} · +{pay} xu. Hẹn đợt sau ngày {r["due"]}.',celebrate=on_time)
    if action=="ph_lot_pull" and p.get("all") is True:
        # #273 (1.9.21): "Rút hết" in Sổ lô: every out-of-date, recalled or warmed box that is free on the shelf, in one
        # tap. Each batch goes exactly as a single pull would; boxes sitting in a slip's tray stay until put back.
        bad=[b for b in care["batches"] if _ph_flag(b,day)]
        need(bad,"Kệ không còn hộp quá hạn, thu hồi hay hỏng lạnh nào.")
        free=[];left={}
        for b in sorted(bad,key=lambda x:(x["lot"],x["exp"],x["id"])):
            room=left.setdefault(b["lot"],available(c,b["lot"]))
            if room>=b["qty"]:free.append(b);left[b["lot"]]=room-b["qty"]
        need(free,"Các hộp cần rút đang nằm trong khay một phiếu. Trả về kệ trước.")
        boxes=refund=loss=0
        for b in free:
            flag=_ph_flag(b,day);value=b["qty"]*PH_UNIT
            c["stock"][b["lot"]]-=b["qty"];care["batches"]=[x for x in care["batches"] if x["id"]!=b["id"]];metric(c,"lots_pulled")
            if flag=="recalled":
                money(s,c,value,f'Nhà phân phối hoàn lô thu hồi {b["id"]}',b["id"],"refund");refund+=value
            else:
                care["waste"]=min(10**7,care["waste"]+value);loss+=value
            boxes+=b["qty"]
        parts=[f'Đã rút {boxes} hộp khỏi kệ']+([f'nhà phân phối hoàn {refund} xu'] if refund else [])+([f'ghi hao hụt {loss} xu'] if loss else [])
        msg=" · ".join(parts)+"."
        if len(free)<len(bad):msg=f'Đã rút {boxes} hộp khỏi kệ. Còn hộp nằm trong khay một phiếu: trả về kệ rồi rút nốt.'
        _care_log(care,day,msg)
        return dict(message=msg)
    if action=="ph_lot_pull":
        b=next((x for x in care["batches"] if x["id"]==p.get("batch")),None);need(b,"Không thấy lô hàng này trên kệ.")
        flag=_ph_flag(b,day);need(flag,"Chỉ rút hộp quá hạn, bị thu hồi hoặc hỏng do tủ mát.")
        need(available(c,b["lot"])>=b["qty"],"Có hộp của lô này đang nằm trong khay một phiếu. Trả về kệ trước.")
        c["stock"][b["lot"]]-=b["qty"];care["batches"]=[x for x in care["batches"] if x["id"]!=b["id"]]
        value=b["qty"]*PH_UNIT;metric(c,"lots_pulled")
        if flag=="recalled":
            money(s,c,value,f'Nhà phân phối hoàn lô thu hồi {b["id"]}',b["id"],"refund")
            msg=f'Đã rút {b["qty"]} hộp {b["lot"]} ({b["id"]}) bị thu hồi · nhà phân phối hoàn {value} xu.'
        else:
            care["waste"]=min(10**7,care["waste"]+value)
            msg=f'Đã rút {b["qty"]} hộp {b["lot"]} ({b["id"]}) khỏi kệ · ghi hao hụt {value} xu.'
        _care_log(care,day,msg)
        return dict(message=msg)
    if action=="ph_fridge_log":
        slot=_key(p.get("slot"));spec=FRIDGE_SLOTS.get(slot);need(spec,"Chọn lượt đo sáng hoặc chiều.")
        f=_ph_fridge_today(care,day);need(slot not in f["logs"],"Lượt đo này đã ghi rồi.")
        minute=_clock(c,"pharmacy")["minute"]
        if spec["until"] is not None:need(minute<spec["until"],f'Lượt đo sáng ghi trước {inv.hm(spec["until"])}. Giờ ghi lượt chiều nhé.')
        if spec["since"] is not None:need(minute>=spec["since"],f'Lượt đo chiều ghi từ {inv.hm(spec["since"])}. Bây giờ mới {inv.hm(minute)}.')
        temp,cause=_fridge_reading(day,slot)
        f["logs"][slot]=dict(temp=temp,cause=cause,at=inv.hm(minute),fix=None,ok=None if cause else True)
        metric(c,"fridge_logs")
        if cause:return dict(message=f'Tủ mát {_deg(temp)}: vượt 8°C! {FRIDGE_CLUE[cause]} Chọn cách xử lý ngay.')
        return dict(message=f'Tủ mát {_deg(temp)} · trong khoảng 2–8°C. Đã ký sổ lượt {spec["label"].lower()}.')
    if action=="ph_fridge_fix":
        f=_ph_fridge_today(care,day);row=f["logs"].get(_key(p.get("slot")))
        need(row and row["cause"],"Lượt đo này không có gì cần xử lý.")
        need(row["fix"] is None,"Đã xử lý lần vượt nhiệt này.")
        fix=_key(p.get("fix"));need(fix in FRIDGE_FIX,"Chọn một cách xử lý.")
        if fix=="move":need(p.get("confirm") is True,"Xác nhận gọi thợ (15 xu) trước nhé.")
        if fix=="move":money(s,c,-15,"Thợ điện kiểm tủ mát","fridge-"+str(day),"repair")
        ok=fix=="move" or row["cause"]=="door"
        row.update(fix=fix,ok=ok)
        if not ok:
            warmed=[b for b in care["batches"] if LOT_INDEX[b["lot"]]["product"] in PH_COLD and not b["warm"]]
            for b in warmed:b["warm"]=True
            _risk(c,1)
            msg="Đóng cửa tủ không đủ: tủ vẫn không chạy. Hộp lạnh trong tủ đã ấm quá lâu, phải rút khỏi kệ."
        elif fix=="move":msg="Đã chuyển hộp lạnh sang tủ dự phòng và gọi thợ. Hộp lạnh an toàn."
        else:msg="Đã đóng kín cửa và dán ron. Đo lại sau một giờ: tủ về 5°C."
        _care_log(care,day,"Tủ mát: "+msg)
        return dict(message=msg)
    raise GameError("Thao tác quầy chưa được hỗ trợ.","unknown_action")


def _ph_start(s:dict,c:dict)->list[str]:
    care=ph_care(c);_ph_sync(c,care);day=c["day"];notes=[]
    for rid,r in care["regulars"].items():
        while r["due"]+1<day:  # a long break: they bought elsewhere meanwhile, no blame
            r["due"]+=PH_REG[rid]["every"];r["called"]=False
    since=day-care["start"]-3
    if since>=0 and since%RECALL_EVERY==0 and day not in care["recalls"]:
        care["recalls"]=ar.last(care["recalls"]+[day],10,"care.recalls",c)
        soon={PH_REG[k]["product"] for k,r in care["regulars"].items() if r["due"]<=day+3}
        pool=[b for b in care["batches"] if b["qty"]>0 and not b["recalled"] and b["exp"]>=day]
        if pool:
            rnd=_rng("ph-recall",day)
            weighted=[b for b in pool for _ in range(3 if LOT_INDEX[b["lot"]]["product"] in soon else 1)]
            b=rnd.choice(weighted);b["recalled"]=RECALL_WHY[rnd.randrange(len(RECALL_WHY))]
            text=f'Thông báo thu hồi: lô {b["id"]} ({b["lot"]}, HSD ngày {b["exp"]}). {b["recalled"]}'
            care["notices"]=ar.last(care["notices"]+[dict(day=day,text=text)],10,"care.notices",c)
            notes.append("📢 "+text+" Rút khỏi kệ để được hoàn tiền.")
    due=[PH_REG[k]["name"] for k,r in care["regulars"].items() if r["due"]-1<=day<=r["due"] and not r["called"]]
    if due:notes.append("📞 Tới lịch nhắc lấy phiếu lặp lại: "+", ".join(due)+".")
    notes+=_ph_date_warnings(care,day)
    return notes


def _ph_date_warnings(care:dict,day:int)->list[str]:
    """#273: use-by dates count the counter's own days (ngày N ở quầy), not the town's. Morning reminders, before
    anything costs a point: what is already out of date on the shelf, and what goes out of date tonight."""
    out=[]
    bad=sum(b["qty"] for b in care["batches"] if b["qty"]>0 and _ph_flag(b,day)=="expired")
    if bad:out.append(f'⚠️ Hôm nay là ngày {day} ở quầy: kệ có {bad} hộp đã quá hạn dùng. Kho → Sổ lô → Rút hết, kẻo đoàn kiểm tra ghi lỗi.')
    last=sum(b["qty"] for b in care["batches"] if b["qty"]>0 and b["exp"]==day and not _ph_flag(b,day))
    if last:out.append(f'⏳ {last} hộp hết hạn sau hôm nay (HSD ngày {day}): bán trước, mai nhớ rút.')
    return out


def _ph_close(s:dict,c:dict)->list[str]:
    care=ph_care(c);_ph_sync(c,care);day=c["day"];lines=[];risk=0
    for rid,r in care["regulars"].items():
        spec=PH_REG[rid]
        if day>=r["due"]+1:
            r["trust"]=max(0,r["trust"]-1);r["missed"]+=1;r["hist"]=ar.last(r["hist"]+[[day,"missed"]],6,"care.regular."+rid,c)
            r.update(due=r["due"]+spec["every"],called=False)
            lines.append(f'{spec["name"]} không lấy được phiếu lặp lại đợt này (mua nơi khác). Hẹn đợt sau ngày {r["due"]}.')
    f=_ph_fridge_today(care,day);pts=0;notes=[]
    minute=_clock(c,"pharmacy")["minute"] if c["open"] else 20*60
    if "am" in f["logs"]:pts+=1
    else:notes.append("thiếu lượt sáng");risk+=1
    if "pm" in f["logs"] or minute<FRIDGE_SLOTS["pm"]["since"]:pts+=1
    else:notes.append("thiếu lượt chiều");risk+=1
    bad=[slot for slot,row in f["logs"].items() if row["cause"] and not row["ok"]]
    for slot in bad:
        row=f["logs"][slot]
        if row["fix"] is None:
            row.update(fix="none",ok=False)
            for b in care["batches"]:
                if LOT_INDEX[b["lot"]]["product"] in PH_COLD:b["warm"]=True
            risk+=1
    if not bad:pts+=1
    else:notes.append("vượt nhiệt chưa xử lý đúng")
    care["flog"]=ar.last(care["flog"]+[dict(day=day,pts=pts,note=", ".join(notes))],7,"care.fridge",c)
    lines.append(f"Sổ nhiệt độ tủ mát: {pts}/3"+(" · "+", ".join(notes) if notes else " · đủ hai lượt đo."))
    flagged=[b for b in care["batches"] if _ph_flag(b,day)]
    if flagged:
        # #273 (1.9.21): at most 2 points a day for the shelf (it was one per batch), and the line says what they cost.
        pts_shelf=min(PH_SHELF_RISK_CAP,len(flagged));risk+=pts_shelf
        lines.append("Còn trên kệ: "+", ".join(f'{b["id"]} ({b["lot"]} × {b["qty"]})' for b in flagged[:4])+f" cần rút · +{pts_shelf} điểm rủi ro cho đợt kiểm tra.")
    soon=[b for b in care["batches"] if b["exp"]==day and not _ph_flag(b,day)]
    if soon:lines.append("Hết hạn sau hôm nay: "+", ".join(f'{b["lot"]} × {b["qty"]}' for b in soon[:4])+" (mai phải rút).")
    tomorrow=[(PH_REG[k],r) for k,r in care["regulars"].items() if r["due"]<=day+1<=r["due"]+1]
    for spec,r in tomorrow:
        lid=spec["product"]+"-A";onway=sum(x["qty"] for x in c["shipments"] if x["item"]==lid and x["status"]=="in_transit")
        lines.append(f'Mai: {spec["name"]} hẹn lấy {spec["qty"]} × {lid} · kệ có {c["stock"].get(lid,0)}'+(f', đang về {onway}' if onway else "")+".")
    _risk(c,risk)
    return lines


def _ph_notices(c:dict)->list[str]:
    care=_care(c)
    if not care or "regulars" not in care:return []
    day=c["day"];out=[]
    here=[PH_REG[k]["name"] for k,r in care["regulars"].items() if _ph_here(r,day)]
    if here:out.append("💊 Khách quen đang chờ phiếu lặp lại: "+", ".join(here)+" (Kho → Khách quen).")
    call=[PH_REG[k]["name"] for k,r in care["regulars"].items() if r["due"]-1<=day<=r["due"] and not r["called"]]
    if call:out.append("📞 Tới lịch gọi nhắc: "+", ".join(call)+".")
    if c["open"]:
        f=care["fridge"] if care["fridge"]["day"]==day else dict(logs={})
        minute=_clock(c,"pharmacy")["minute"]
        if "am" not in f["logs"] and minute<12*60:out.append("🧊 Chưa ghi nhiệt độ tủ mát lượt sáng (trước 12:00).")
        elif "pm" not in f["logs"] and minute>=14*60:out.append("🧊 Chưa ghi nhiệt độ tủ mát lượt chiều.")
        if any(r["cause"] and r["fix"] is None for r in f["logs"].values()):out.append("🌡️ Tủ mát đang vượt 8°C, cần xử lý.")
    n=sum(b["qty"] for b in care["batches"] if _ph_flag(b,day))
    if n:out.append(f"⚠️ Kệ còn {n} hộp quá hạn/thu hồi cần rút.")
    last=sum(b["qty"] for b in care["batches"] if b["qty"]>0 and b["exp"]==day and not _ph_flag(b,day))
    if last:out.append(f"⏳ {last} hộp hết hạn sau hôm nay (ngày {day} ở quầy).")
    return out


def _ph_public(c:dict,care:dict)->dict:
    v=tree_copy(care);day=c["day"]
    for b in v["batches"]:
        b["flag"]=_ph_flag(b,day);b["days_left"]=b["exp"]-day
    v["batches"].sort(key=lambda b:(b["lot"],b["exp"],b["got"]))
    regs=[]
    for spec in PH_REGULARS:
        r=care["regulars"][spec["id"]];lid=spec["product"]+"-A"
        state="here" if _ph_here(r,day) else "call" if r["due"]-1<=day<=r["due"] and not r["called"] else "called" if r["called"] else "later"
        regs.append(dict(spec,**r,lot=lid,state=state,shelf=c["stock"].get(lid,0),block=ph_shelf_block(c,lid),
            window=f'ngày {r["due"]}–{r["due"]+1}',in_days=r["due"]-day))
    v["regulars"]=regs
    f=care["fridge"] if care["fridge"]["day"]==day else dict(day=day,logs={})
    clk=_clock(c,"pharmacy");minute=clk["minute"]
    slots=[]
    for sid,spec in FRIDGE_SLOTS.items():
        row=f["logs"].get(sid)
        open_now=clk["is_open"] and (spec["until"] is None or minute<spec["until"]) and (spec["since"] is None or minute>=spec["since"])
        slots.append(dict(id=sid,label=spec["label"],row=dict(row,temp_label=_deg(row["temp"]),clue=FRIDGE_CLUE.get(row["cause"]) if row["cause"] else None) if row else None,
            can_log=bool(open_now and not row),hint=("trước "+inv.hm(spec["until"])) if spec["until"] else ("từ "+inv.hm(spec["since"]))))
    v["fridge"]=dict(day=day,slots=slots,fixes=[dict(id=k,label=t) for k,t in FRIDGE_FIX.items()])
    days=care["flog"][-7:];pts=sum(x["pts"] for x in days)+2*(7-len(days))
    v["fridge_score"]=round(pts*100/21)
    v["notices"]=care["notices"][-3:]
    v["clock"]=_clock_view(c,"pharmacy")
    v["alerts"]=_ph_notices(c)
    return v


def _ph_validate(care:dict)->None:
    need(set(care)=={"v","start","seq","batches","regulars","fridge","flog","notices","recalls","waste","log"},"Sổ quầy thuốc không hợp lệ.")
    integer(care["v"],1,1);integer(care["start"],1,10**7);integer(care["seq"],0,10**7);integer(care["waste"],0,10**7)
    need(isinstance(care["batches"],list) and len(care["batches"])<=80,"Sổ lô không hợp lệ.")
    seen=set()
    for b in care["batches"]:
        need(isinstance(b,dict) and set(b)=={"id","lot","qty","exp","got","recalled","warm"},"Lô hàng không hợp lệ.")
        need(re.fullmatch(r"L\d{3,7}",str(b["id"])) and b["id"] not in seen,"Mã lô không hợp lệ.");seen.add(b["id"])
        need(b["lot"] in LOT_INDEX and LOT_INDEX[b["lot"]]["status"]=="available","Lô không thuộc kệ xuất.")
        integer(b["qty"],1,24);integer(b["exp"],0,10**7);integer(b["got"],1,10**7)
        need(b["recalled"] is None or b["recalled"] in RECALL_WHY,"Lý do thu hồi không hợp lệ.")
        need(type(b["warm"]) is bool,"Trạng thái tủ mát không hợp lệ.")
    need(isinstance(care["regulars"],dict) and set(care["regulars"])==set(PH_REG),"Sổ khách quen không hợp lệ.")
    for r in care["regulars"].values():
        need(isinstance(r,dict) and set(r)=={"due","called","trust","visits","missed","last","hist"},"Khách quen không hợp lệ.")
        integer(r["due"],1,10**7);integer(r["trust"],0,5);integer(r["visits"],0,10**6);integer(r["missed"],0,10**6)
        need(type(r["called"]) is bool and (r["last"] is None or type(r["last"]) is int),"Khách quen không hợp lệ.")
        need(isinstance(r["hist"],list) and len(r["hist"])<=6 and all(isinstance(h,list) and len(h)==2 and type(h[0]) is int and h[1] in ("ok","late","missed") for h in r["hist"]),"Lịch sử phiếu không hợp lệ.")
    f=care["fridge"];need(isinstance(f,dict) and set(f)=={"day","logs"} and isinstance(f["logs"],dict) and set(f["logs"])<=set(FRIDGE_SLOTS),"Sổ tủ mát không hợp lệ.")
    integer(f["day"],0,10**7)
    for row in f["logs"].values():
        need(isinstance(row,dict) and set(row)=={"temp","cause","at","fix","ok"},"Lượt đo không hợp lệ.")
        integer(row["temp"],0,200);need(row["cause"] in (None,"door","power") and row["fix"] in (None,"none",*FRIDGE_FIX) and row["ok"] in (None,True,False),"Lượt đo không hợp lệ.")
        clean_text(row["at"],5)
    need(isinstance(care["flog"],list) and len(care["flog"])<=7,"Sổ nhiệt độ không hợp lệ.")
    for x in care["flog"]:
        need(isinstance(x,dict) and set(x)=={"day","pts","note"},"Sổ nhiệt độ không hợp lệ.");integer(x["day"],1,10**7);integer(x["pts"],0,3);clean_text(x["note"],200,0)
    need(isinstance(care["recalls"],list) and len(care["recalls"])<=10 and all(type(x) is int for x in care["recalls"]),"Lịch thu hồi không hợp lệ.")
    _validate_lines(care["notices"],10);_validate_lines(care["log"],30)


def _validate_lines(rows:Any,cap:int)->None:
    need(isinstance(rows,list) and len(rows)<=cap,"Nhật ký không hợp lệ.")
    for x in rows:
        need(isinstance(x,dict) and set(x)=={"day","text"},"Nhật ký không hợp lệ.");integer(x["day"],1,10**7);clean_text(x["text"],300)


# ---------------------------------------------------------------- bookkeeping: Góc Sổ Xinh
AC_MONTH=5  # one bookkeeping month of a small shop = five days at the desk
AC_GRACE=1  # the day after the deadline the owner takes the box back
AC_CLIENTS=(
    dict(id="hoa",name="Quán cơm cô Hoa",owner="Cô Hoa",npc="accounting_npc_03",emoji="🍚",habits=("cash","personal"),offset=0,fee=80),
    dict(id="na",name="Tiệm bánh Na",owner="Chị Na",npc=None,emoji="🥐",habits=("dup","round"),offset=1,fee=70),
    dict(id="sau",name="Tạp hóa bà Sáu",owner="Bà Sáu",npc=None,emoji="🛒",habits=("late","cash"),offset=2,fee=75),
    dict(id="tam",name="Sửa xe chú Tám",owner="Chú Tám",npc=None,emoji="🛵",habits=("personal","dup"),offset=3,fee=85),
)
AC_CLIENT={x["id"]:x for x in AC_CLIENTS}
AC_CHECKS={"dup":("Soát hóa đơn chụp trùng","📑"),"personal":("Tách chi tiêu nhà khỏi sổ quán","🏠"),
           "round":("Đối số lẻ với sao kê","🔢"),"cash":("Khớp phiếu chi tiền mặt","💵")}
AC_HABITS={"dup":"Hay chụp một hóa đơn hai lần.","personal":"Hay lẫn tiền chợ nhà vào sổ quán.","round":"Hay làm tròn số khi ghi tay.",
           "cash":"Hay quên ghi phiếu chi tiền mặt.","late":"Hẹn gửi phiếu thiếu rồi quên: cần gọi nhắc lại đúng hẹn."}
AC_SHARE={"perfect":100,"good":75,"rough":40,"lost":0}
AC_GRADE={"perfect":"Sổ sạch","good":"Đạt · có ghi chú","rough":"Còn sót lỗi","lost":"Khách lấy sổ về"}


def _ac_fresh(day:int)->dict:
    return dict(v=1,start=max(2,day),clients={x["id"]:dict(trust=2,known=[],months=[]) for x in AC_CLIENTS},log=[])


def ac_care(c:dict,create:bool=True)->dict|None:
    care=_care(c)
    if care is None and create:
        care=_ac_fresh(c["day"]);c["ext"]["data"]["care"]=care
    return care


def _ac_case(client:dict,m:int)->dict:
    r=_rng("acbook",client["id"],m);out={}
    for k in AC_CHECKS:
        if k in client["habits"]:out[k]=r.choice((1,1,2)) if r.random()<0.85 else 0
        else:out[k]=1 if r.random()<0.12 else 0
    missing=r.randint(1,2) if "late" in client["habits"] else (1 if r.random()<0.45 else 0)
    return dict(issues=out,missing=missing,receipts=r.randint(12,20))


def _ac_book(rec:dict)->dict|None:
    b=rec["months"][-1] if rec["months"] else None
    return b if b and b["closed"] is None else None


def _ac_arrivals(c:dict,care:dict)->list[str]:
    day=c["day"];notes=[]
    for spec in AC_CLIENTS:
        rec=care["clients"][spec["id"]];first=care["start"]+spec["offset"]
        if day<first:continue
        m=(day-first)//AC_MONTH;arrive=first+AC_MONTH*m
        if rec["months"] and rec["months"][-1]["m"]>=m:continue
        if _ac_book(rec):continue
        rec["months"]=ar.last(rec["months"]+[dict(m=m,arrive=arrive,due=arrive+3,opened=False,checks=[],chase=0,promise=None,source=False,late=False,closed=None)],4,"care.client."+spec["id"],c)
        notes.append(f'📚 {spec["owner"]} mang sổ tháng {m+1} của {spec["name"]} tới · hạn khóa sổ ngày {arrive+3}.')
    for spec in AC_CLIENTS:
        b=_ac_book(care["clients"][spec["id"]])
        if b and b["promise"] and not b["source"] and day>=b["promise"] and "late" not in spec["habits"]:
            b["source"]=True;n=_ac_case(spec,b["m"])["missing"]
            notes.append(f'📎 {spec["owner"]} đã gửi {n} phiếu còn thiếu cho sổ tháng {b["m"]+1}.')
    return notes


def _ac_action(s:dict,c:dict,action:str,p:dict)->dict:
    care=ac_care(c);day=c["day"];_ac_arrivals(c,care)
    spec=AC_CLIENT.get(_key(p.get("client")));need(spec,"Không có khách hàng này trong tủ hồ sơ.")
    rec=care["clients"][spec["id"]];b=_ac_book(rec);need(b,f'{spec["name"]} chưa gửi sổ tháng này.')
    case=_ac_case(spec,b["m"])
    if action=="ac_book_open":
        need(not b["opened"],"Sổ đã mở trên bàn.")
        b["opened"]=True;metric(c,"books_opened")
        miss=f' Sao kê có {case["missing"]} khoản chưa thấy phiếu.' if case["missing"] else " Sao kê khớp đủ phiếu."
        return dict(message=f'Mở hộp sổ {spec["name"]}: {case["receipts"]} phiếu.{miss}')
    need(b["opened"],"Mở hộp sổ trước đã.")
    if action=="ac_book_check":
        k=_key(p.get("check"));need(k in AC_CHECKS,"Chọn một bước soát.")
        need(k not in b["checks"],"Bước soát này đã làm rồi.")
        b["checks"].append(k);n=case["issues"][k];metric(c,"source_reads")
        if n and k in spec["habits"] and k not in rec["known"]:
            rec["known"].append(k)
            learned=" Đã ghi vào hồ sơ khách: "+AC_HABITS[k]
        else:learned=""
        label=AC_CHECKS[k][0]
        return dict(message=(f"{label}: tìm thấy {n} chỗ sai, đã sửa có ghi chú." if n else f"{label}: không có sai sót.")+learned)
    if action=="ac_book_chase":
        need(case["missing"]>0,"Sổ tháng này không thiếu phiếu nào.")
        need(not b["source"],"Khách đã gửi đủ phiếu rồi.")
        if b["chase"]==0:
            lag=2 if "late" in spec["habits"] else 1
            b.update(chase=1,promise=day+lag);metric(c,"source_requests")
            return dict(message=f'{spec["owner"]} hẹn gửi {case["missing"]} phiếu còn thiếu vào ngày {day+lag}.')
        need(day>=b["promise"],f'{spec["owner"]} hẹn gửi vào ngày {b["promise"]}. Tới hẹn mà chưa có thì gọi nhắc lại nhé.')
        b.update(chase=2,source=True);metric(c,"source_requests")
        if "late" not in rec["known"]:rec["known"].append("late")
        return dict(message=f'Gọi nhắc lại: {spec["owner"]} chụp gửi ngay {case["missing"]} phiếu còn thiếu. Đã ghi vào hồ sơ khách: hay quên hẹn.')
    if action=="ac_book_close":
        need(p.get("confirm") is True,"Xác nhận khóa sổ tháng trước nhé.")
        gap=case["missing"]>0 and not b["source"]
        note=_key(p.get("note","full"));need(note in ("full","missing_note"),"Chọn cách khóa sổ.")
        need(not gap or note=="missing_note",f'Còn thiếu {case["missing"]} phiếu: chờ khách gửi, hoặc khóa kèm ghi chú thiếu chứng từ.')
        left=sum(n for k,n in case["issues"].items() if k not in b["checks"])
        grade="rough" if left else "good" if gap else "perfect"
        late=day>b["due"]
        fee=max(0,spec["fee"]*AC_SHARE[grade]//100-(15 if late else 0))
        tip=10 if grade=="perfect" and not late and rec["trust"]>=4 else 0
        rec["trust"]=max(0,min(5,rec["trust"]+(1 if grade=="perfect" and not late else -1 if grade=="rough" else 0)))
        b["closed"]=dict(day=day,grade=grade,fee=fee+tip,left=left,note=note if gap else "full")
        if fee+tip:money(s,c,fee+tip,f'Khóa sổ tháng {b["m"]+1} · {spec["name"]}',f'book-{spec["id"]}-{b["m"]}',"revenue")
        metric(c,"books_closed")
        if grade=="perfect":metric(c,"books_perfect");c["xp"]+=10
        if grade=="rough":_risk(c,1)
        text={"perfect":"Sổ sạch, đúng hạn.","good":"Khóa sổ kèm ghi chú thiếu chứng từ, khách gửi bổ sung tháng sau.","rough":f"Còn {left} chỗ sai chưa soát, tháng sau khách phải sửa lại."}[grade]
        _care_log(care,day,f'{spec["name"]} · tháng {b["m"]+1}: {text}')
        return dict(message=f'{AC_GRADE[grade]} · +{fee+tip} xu. {text}'+(" (trễ hạn −15 xu)" if late else ""),celebrate=grade=="perfect")
    raise GameError("Thao tác sổ khách chưa được hỗ trợ.","unknown_action")


def _ac_close(s:dict,c:dict)->list[str]:
    care=ac_care(c);day=c["day"];lines=[]
    for spec in AC_CLIENTS:
        rec=care["clients"][spec["id"]];b=_ac_book(rec)
        if not b:continue
        if day>=b["due"]+AC_GRACE:
            b["closed"]=dict(day=day,grade="lost",fee=0,left=0,note="full")
            rec["trust"]=max(0,rec["trust"]-1);_risk(c,1)
            lines.append(f'{spec["owner"]} lấy sổ tháng {b["m"]+1} về vì quá hạn khóa sổ.')
        elif day>=b["due"] and not b["late"]:
            b["late"]=True;rec["trust"]=max(0,rec["trust"]-1)
            lines.append(f'Trễ hạn khóa sổ {spec["name"]}: khóa trong ngày mai, bị trừ 15 xu.')
        elif b["due"]-day==1:lines.append(f'Mai là hạn khóa sổ {spec["name"]}.')
        if b["promise"] and not b["source"] and day>=b["promise"] and "late" in spec["habits"]:
            lines.append(f'{spec["owner"]} hẹn gửi phiếu thiếu mà chưa gửi: gọi nhắc lại.')
    return lines


def _ac_notices(c:dict)->list[str]:
    care=_care(c)
    if not care or "clients" not in care:return []
    day=c["day"];out=[]
    for spec in AC_CLIENTS:
        b=_ac_book(care["clients"][spec["id"]])
        if not b:continue
        if day>=b["due"]:out.append(f'⏰ Sổ {spec["name"]} tới hạn khóa hôm nay'+(" (đã trễ)" if b["late"] else "")+".")
        elif not b["opened"]:out.append(f'📚 Sổ tháng {b["m"]+1} của {spec["name"]} đang chờ mở (hạn ngày {b["due"]}).')
        if b["promise"] and not b["source"] and day>=b["promise"]:out.append(f'📎 {spec["owner"]} hẹn gửi phiếu thiếu hôm nay.')
    return out[:4]


def _ac_public(c:dict,care:dict)->dict:
    day=c["day"];rows=[]
    for spec in AC_CLIENTS:
        rec=care["clients"][spec["id"]];b=_ac_book(rec);book=None
        if b:
            case=_ac_case(spec,b["m"])
            book=dict(b,days_left=b["due"]-day,receipts=case["receipts"] if b["opened"] else None,missing=case["missing"] if b["opened"] else None,
                found={k:case["issues"][k] for k in b["checks"]},
                checks_all=[dict(id=k,label=v[0],emoji=v[1],done=k in b["checks"],hint=k in rec["known"]) for k,v in AC_CHECKS.items()],
                can_follow=bool(b["promise"] and not b["source"] and day>=b["promise"]),
                gap=bool(b["opened"] and case["missing"] and not b["source"]))
        first=care["start"]+spec["offset"]
        nxt=first if day<first else first+AC_MONTH*((day-first)//AC_MONTH+1)
        rows.append(dict(id=spec["id"],name=spec["name"],owner=spec["owner"],npc=spec["npc"],emoji=spec["emoji"],fee=spec["fee"],trust=rec["trust"],
            known=[dict(id=k,text=AC_HABITS[k]) for k in rec["known"]],unknown=len([h for h in spec["habits"] if h not in rec["known"]]),
            book=book,months=[dict(m=x["m"],arrive=x["arrive"],due=x["due"],closed=x["closed"]) for x in rec["months"] if x["closed"]][-3:],
            next_arrive=None if book else nxt))
    return dict(v=1,start=care["start"],month=AC_MONTH,clients=rows,log=care["log"][-6:],alerts=_ac_notices(c),clock=_clock_view(c,"accounting"),grades=AC_GRADE)


def _ac_validate(care:dict)->None:
    need(set(care)=={"v","start","clients","log"},"Tủ hồ sơ khách không hợp lệ.")
    integer(care["v"],1,1);integer(care["start"],1,10**7)
    need(isinstance(care["clients"],dict) and set(care["clients"])==set(AC_CLIENT),"Tủ hồ sơ khách không hợp lệ.")
    for cid,rec in care["clients"].items():
        need(isinstance(rec,dict) and set(rec)=={"trust","known","months"},"Hồ sơ khách không hợp lệ.")
        integer(rec["trust"],0,5)
        need(isinstance(rec["known"],list) and len(set(rec["known"]))==len(rec["known"]) and set(rec["known"])<=set(AC_CLIENT[cid]["habits"]),"Thói quen khách không hợp lệ.")
        need(isinstance(rec["months"],list) and len(rec["months"])<=4,"Sổ tháng không hợp lệ.")
        prev=-1
        for b in rec["months"]:
            need(isinstance(b,dict) and set(b)=={"m","arrive","due","opened","checks","chase","promise","source","late","closed"},"Sổ tháng không hợp lệ.")
            integer(b["m"],0,10**6);need(b["m"]>prev,"Thứ tự sổ tháng sai.");prev=b["m"]
            integer(b["arrive"],1,10**7);need(b["due"]==b["arrive"]+3,"Hạn khóa sổ sai.");integer(b["chase"],0,2)
            need(type(b["opened"]) is bool and type(b["source"]) is bool and type(b["late"]) is bool,"Sổ tháng không hợp lệ.")
            need(isinstance(b["checks"],list) and len(set(b["checks"]))==len(b["checks"]) and set(b["checks"])<=set(AC_CHECKS),"Bước soát không hợp lệ.")
            need(b["promise"] is None or type(b["promise"]) is int,"Hẹn gửi phiếu không hợp lệ.")
            if b["closed"] is not None:
                x=b["closed"];need(isinstance(x,dict) and set(x)=={"day","grade","fee","left","note"} and x["grade"] in AC_SHARE and x["note"] in ("full","missing_note"),"Kết quả khóa sổ không hợp lệ.")
                integer(x["day"],1,10**7);integer(x["fee"],0,1000);integer(x["left"],0,20)
        need(sum(b["closed"] is None for b in rec["months"])<=1 and all(b["closed"] is not None for b in rec["months"][:-1]),"Chỉ một sổ tháng mở cùng lúc.")
    _validate_lines(care["log"],30)


# ---------------------------------------------------------------- support: Trạm Lắng Nghe
CS_TONES=("vui","binh","lo","buc")
CS_TONE_LABEL={"vui":"vui vẻ","binh":"bình tĩnh","lo":"lo lắng","buc":"bực bội"}
CS_START_TONE={"missing":"lo","delivered":"buc","delay":"lo","wrong":"lo","refund":"binh","guide":"binh"}
CS_WAIT_LABEL={"dau_moi":"đầu mối xác nhận","kho":"kho gửi hàng","vc":"đơn vị vận chuyển đối soát","ketoan":"kế toán duyệt hoàn","chi_mai":"chị Mai phản hồi"}
CS_SLA_FIRST=pt.longer(120)  # minutes to the first contact on a new case (from day 3), PATIENCE_FACTOR applied
CS_UPDATE_BY=12*60  # a waiting case gets its daily update call before noon
CS_PICKS={"update":"Báo tình trạng thật của đơn","sorry":"Xin lỗi và hẹn giờ cập nhật","ask":"Hỏi khách thêm thông tin","bye":"Cảm ơn và chào khách"}
CS_CALL_MAX=8
# The source line that names the fix of each case (shown as "📌 Căn cứ" once every source is read); a wrong pick quotes it.
CS_BASIS={"missing":2,"delivered":2,"delay":1,"wrong":2,"refund":0,"guide":1}
CS_SOL_LABEL={"reship":"Gửi bù món thiếu","trace":"Đối soát giao nhận","exchange":"Đổi đúng món","refund":"Thực hiện hoàn","guide":"Hướng dẫn khách"}
CS_SOL_WHEN={"reship":"kiện thiếu món","trace":"cần đầu mối kiểm lại chặng giao","exchange":"khách nhận sai mã, sai màu (không phải thiếu món)","refund":"hồ sơ có yêu cầu hoàn hoặc chính sách cho hoàn","guide":"đơn không lỗi, khách chỉ cần cách làm"}
CS_FACT={"missing":"Mình nhận có 2 món thôi, đơn ghi 3 món.","delivered":"Mình ở nhà cả ngày mà chẳng ai gọi giao hàng.",
         "delay":"Lần cuối mình thấy kiện nằm ở điểm trung chuyển.","wrong":"Mình đặt hộp xanh mà nhận hộp hồng.",
         "refund":"Yêu cầu hoàn đó mình tạo mấy hôm trước rồi.","guide":"Mình mở ứng dụng mà không thấy mục đơn đâu."}
CS_WORDS=dict(
    rude=("ngu","im di","ke ban","mac ke","tu di ma","phien qua","lam gi ke","noi hoai","di cho khuat","do dien","vo duyen","dung lam phien"),
    promise=("chac chan","cam ket","dam bao","bao dam","100%","ngay lap tuc","hoan tien ngay","tang ban","tang chi","tang anh","den bu","boi thuong","mien phi","giam gia"),
    sorry=("xin loi","thanh that","thong cam","rat tiec","lam phien ban cho"),
    update=("dang","du kien","cap nhat","kho","van chuyen","giao","hom nay","ngay mai","sang mai","chieu nay","tien do","trang thai","doi soat","xuat bu","da gui"),
    bye=("tam biet","chao ban","chao anh","chao chi","het roi","vay nhe","hen gap"),
)


def _cs_classic(t:dict)->bool:
    return t.get("career")=="customer_care" and not t.get("desk") and isinstance(t.get("evidence"),list)


def _cs_basis(t:dict)->dict|None:
    ev=t.get("evidence") or [];i=CS_BASIS.get(t.get("variant"))
    return ev[i] if i is not None and i<len(ev) else None


def _cs_reject(t:dict,choice:Any)->str:
    """A wrong fix names when that fix applies and quotes the source line that decides this case (not stored)."""
    e=_cs_basis(t)
    if not e or choice not in CS_SOL_LABEL:return "Phương án chưa phù hợp hồ sơ đã kiểm. Xem lại chứng cứ và chính sách nhé."
    # The 📌 line first: the source decides the case, the wrong pick's rule follows (players stopped at the first words).
    return f'📌 {dk.shown(e["title"])}: “{e["text"]}” «{CS_SOL_LABEL[choice]}» chỉ dùng khi {CS_SOL_WHEN[choice]}.'


def cs_care(c:dict,create:bool=True)->dict|None:
    care=_care(c)
    if care is None and create:
        care=dict(v=1,people={},trend=[],handover=None,log=[]);c["ext"]["data"]["care"]=care
    return care


def _cs_fields(t:dict)->None:
    for k,v in (("ready_at",None),("wait",None),("sla_at",None),("sla",None),("upd",None),("call",[]),("tone",CS_START_TONE.get(t.get("variant"),"binh")),("promised",False),("call_day",0),("call_n",0)):
        t.setdefault(k,v)


def _cs_wait(c:dict,t:dict)->tuple[int,str]:
    """When the coordinator, warehouse or carrier answers, on the shop clock."""
    now=_now(c,"customer_care");day=c["day"];sol=t.get("proposal");op,cl=inv.hours("customer_care")
    r=_rng("cs-wait",t["id"])
    if day<=2 or sol=="guide":return now+40,"dau_moi"
    if sol=="refund":
        at=now+120
        return (at if at%inv.DAY_MIN<=cl else _day_at(day+1,op+30)),"ketoan"
    if sol=="reship":return _day_at(day+1,10*60+20*r.randrange(13)),"kho"
    if sol=="exchange":return _day_at(day+2,11*60+20*r.randrange(10)),"kho"
    slow=bool(dk.dc.slow_zone(day))
    return _day_at(day+(2 if slow else 1),15*60+20*r.randrange(7)),"vc"


def _cs_eta(c:dict,t:dict)->str|None:
    if not t.get("ready_at"):return None
    return inv.when(t["ready_at"],_now(c,"customer_care"))


def _cs_classify(text:str)->str:
    msg=normalize(text)
    for intent in ("rude","promise","sorry","update","bye"):
        if any(re.search(r"(?<!\w)"+re.escape(w)+r"(?!\w)",msg) for w in CS_WORDS[intent]):return intent
    return "ask" if "?" in text else "other"


def _cs_step(tone:str,d:int)->str:
    return CS_TONES[max(0,min(len(CS_TONES)-1,CS_TONES.index(tone)+d))]


def _cs_status(c:dict,t:dict)->tuple[str,str]:
    """(what the player can truthfully say, what the customer still needs)."""
    st=t["status"];eta=_cs_eta(c,t)
    if st in ("new","understood"):return "mình đang kiểm hồ sơ đơn của bạn","Vậy bên bạn định xử lý đơn của mình thế nào?"
    if st=="proposed":return "mình đã chọn phương án và sắp chuyển cho đầu mối","Phương án đó ổn, khi nào bắt đầu làm vậy?"
    if st=="handed_over":return "chị Mai trưởng ca đang xem hồ sơ của bạn","Vậy chị trưởng ca xem xong thì ai báo mình?"
    if st=="executing":
        w=CS_WAIT_LABEL.get(t.get("wait") or "dau_moi","đầu mối xác nhận")
        return f"đang chờ {w}, dự kiến {eta.lower() if eta else 'trong hôm nay'}",("Kho gửi rồi thì khi nào tới tay mình?" if t.get("wait")=="kho" else "Bên vận chuyển kiểm xong chưa, mình lo mất hàng quá." if t.get("wait")=="vc" else "Mình chờ thêm chút cũng được, có tin thì báo mình nha.")
    if st=="awaiting_confirmation":return "đã có kết quả, mình đang kiểm lại cho chắc","Mình thấy có tin rồi, bạn kiểm giúp mình cho chắc nhé."
    return "việc đã xong và đã kiểm","Ổn rồi, cảm ơn bạn đã theo tới cùng."


def _cs_customer_line(c:dict,t:dict,intent:str,tone:str)->str:
    player,need_line=_cs_status(c,t);eta=_cs_eta(c,t)
    opener={"buc":"Mình gọi mấy lần rồi đó. ","lo":"Mình hơi lo. ","binh":"","vui":""}[tone]
    if intent=="update":
        react=f"À, vậy là {eta.lower()}. Mình ghi lại rồi." if t["status"]=="executing" and eta else "Vậy là đang có người lo rồi, mình yên tâm hơn."
        return (opener if tone=="buc" else "")+react
    if intent=="sorry":return ("Xin lỗi thì mình nghe rồi. " if tone=="buc" else "Ừ, mình hiểu mà. ")+need_line
    if intent=="promise":return "Bạn nói chắc vậy thì mình tin, đừng để mình chờ uổng nha."
    if intent=="rude":return "Sao bạn nói vậy? Mình chỉ muốn biết đơn của mình thôi."
    if intent=="ask":return opener+CS_FACT.get(t.get("variant"),"Mình kể hết rồi đó.")
    if intent=="bye":return "Cảm ơn bạn, có tin gì nhắn mình nhé." if tone in ("vui","binh") else "Ừ, nhớ báo mình sớm đó."
    return opener+need_line


def _cs_player_line(c:dict,t:dict,pick:str)->str:
    player,_=_cs_status(c,t)
    return {"update":f"Mình cập nhật: {player}.","sorry":"Mình xin lỗi vì bạn phải chờ. Có tin mới mình gọi lại ngay.",
            "ask":"Bạn kể thêm giúp mình tình trạng đơn lúc nhận nhé?","bye":"Cảm ơn bạn đã chờ. Có tin mình báo liền nhé."}[pick]


def _cs_call(s:dict,c:dict,p:dict)->dict:
    """One line of a phone call. The customer's words are scripted from the case facts
    (an AI may reword them later); only these rules change tone, SLA and satisfaction."""
    t=current_task(c,p.get("task"));need(_cs_classic(t),"Cuộc gọi dùng cho vụ hỗ trợ đang theo dõi.")
    need(c["open"],"Mở ca trước khi gọi khách nhé.")
    _cs_fields(t);need(t["identity"],"Xác minh mã đơn của khách trước khi trao đổi về đơn.")
    day=c["day"]
    if t["call_day"]!=day:t.update(call_day=day,call_n=0)
    need(t["call_n"]<CS_CALL_MAX,"Cuộc gọi hôm nay đã khá dài. Hẹn khách lần sau nhé.")
    pick=p.get("pick");text=p.get("text")
    if pick is not None:
        need(_key(pick) in CS_PICKS and text is None,"Chọn một câu trả lời.")
        said=_cs_player_line(c,t,pick);intent=pick
    else:
        said=clean_text(text,200);intent=_cs_classify(said)
    if t["call_n"]==0:c["turn"]+=1  # picking up the phone takes the shop clock on (20 minutes)
    t["call_n"]+=1;metric(c,"cs_calls")
    tone=t["tone"];upset_before=CS_TONES.index(tone)
    helps=t["status"] in ("proposed","executing","awaiting_confirmation","resolved","handed_over")
    if intent=="sorry":tone=_cs_step(tone,-1)
    elif intent=="update" and helps:tone=_cs_step(tone,-1)
    elif intent=="promise":tone=_cs_step(tone,-1);t["promised"]=True
    elif intent=="rude":tone=_cs_step(tone,2);t["mistakes"]+=1;t["patience"]=max(25,t.get("patience",100)-10)
    t["tone"]=tone
    kept=None
    if t["upd"] and not t["upd"]["done"] and intent in ("update","sorry") and _now(c,"customer_care")<=t["upd"]["by"]:
        t["upd"]["done"]=True;kept="Đã gọi cập nhật đúng hẹn trước 12:00."
    reply=_cs_customer_line(c,t,intent,tone)
    t["call"]=ar.last(t["call"]+[dict(who="player",text=said),dict(who="npc",text=reply,mode="scripted",tone=tone)],20,"call:"+t["id"],c)
    t["timeline"].append(f'Gọi khách lúc {inv.hm(_clock(c,"customer_care")["minute"])}: {CS_PICKS.get(intent,"trao đổi")}.' if intent in CS_PICKS else f'Gọi khách lúc {inv.hm(_clock(c,"customer_care")["minute"])}.')
    t["timeline"]=ar.last(t["timeline"],30,"timeline:"+t["id"],c)
    moved="dịu hơn" if CS_TONES.index(tone)<upset_before else "căng hơn" if CS_TONES.index(tone)>upset_before else None
    msg=f'{NPC_INDEX[t["npc"]]["display_name"]}: “{reply}”'
    return dict(message=msg,reply=reply,npc=t["npc"],intent=intent,tone=tone,tone_label=CS_TONE_LABEL[tone],tone_moved=moved,kept=kept)


def cs_call_context(state:dict,task_id:Any)->dict|None:
    """Facts for an AI-worded customer line: only what the save says about the case."""
    c=state["careers"]["customer_care"]
    t=next((x for x in c["tasks"] if x.get("id")==task_id),None)
    if not t or not _cs_classic(t):return None
    player,need_line=_cs_status(c,t)
    ctx=dict(case=t["title"],customer_opening=t["opening"],status=player,customer_needs=need_line,
        mood=CS_TONE_LABEL.get(t.get("tone"),"bình tĩnh"),customer_knows=CS_FACT.get(t.get("variant")),
        order_value_xu=t["value"] if t["identity"] else None,eta=_cs_eta(c,t),waiting_for=CS_WAIT_LABEL.get(t.get("wait")) if t["status"]=="executing" else None,
        rule="Khách không tự quyết định hoàn tiền hay đổi hàng; chỉ phản ứng với lời nhân viên.")
    hist=[dict(role="user" if x["who"]=="player" else "npc",text=x["text"]) for x in (t.get("call") or [])]
    return dict(npc=t["npc"],context=ctx,history=hist)


def _cs_task_hook(c:dict,t:dict)->None:
    if not _cs_classic(t):return
    _cs_fields(t)
    if t["day"]>=3 and t["sla_at"] is None and not t["identity"]:t["sla_at"]=_now(c,"customer_care")+CS_SLA_FIRST


def _cs_start(s:dict,c:dict)->list[str]:
    care=cs_care(c);day=c["day"];notes=[]
    op=_day_at(day,inv.hours("customer_care")[0])
    rows=[];night=[]
    for t in c["tasks"]:
        if t.get("career")!="customer_care" or t["status"] in ("completed","referred","cancelled"):continue
        if _cs_classic(t):
            _cs_fields(t)
            if t["day"]==day:_cs_task_hook(c,t)
            if t["status"]=="executing" and t["ready_at"] and t["ready_at"]>_day_at(day,CS_UPDATE_BY):
                t["upd"]=dict(day=day,by=_day_at(day,CS_UPDATE_BY),done=False,late=False)
            elif t["upd"] and t["upd"]["day"]!=day:t["upd"]=None
        if t["day"]>=day:continue
        name=NPC_INDEX[t["npc"]]["display_name"]
        if _cs_classic(t) and (t["status"]=="awaiting_confirmation" or (t["status"]=="executing" and t["ready_at"] and t["ready_at"]<=op)):
            night.append(f'Tin mới đầu ca: {CS_WAIT_LABEL.get(t["wait"],"đầu mối xác nhận")} đã có kết quả cho vụ “{t["title"]}” của {name}. Kiểm rồi đóng vụ.')
        nxt=("Gọi cập nhật trước 12:00" if t.get("upd") else "Chờ kết quả") if t["status"]=="executing" else {"awaiting_confirmation":"Kiểm kết quả rồi đóng vụ","resolved":"Đóng vụ","proposed":"Gửi việc cho đầu mối","handed_over":"Chờ chị Mai"}.get(t["status"],"Tiếp tục xử lý")
        rows.append(dict(task=t["id"],title=t["title"],npc=t["npc"],name=name,status=t["status"],next=nxt,eta=_cs_eta(c,t) if _cs_classic(t) and t["status"]=="executing" else None,desk=bool(t.get("desk"))))
    if day>=2 and (rows or night):
        care["handover"]=dict(day=day,read=False,rows=rows[:6],night=night[:4])
        notes.append(f'🗂️ Ca hôm qua bàn giao {len(rows)} vụ còn mở'+(f", {len(night)} tin trong đêm" if night else "")+". Xem Bảng theo dõi.")
    elif care["handover"] and care["handover"]["day"]!=day:care["handover"]=None
    return notes


def _cs_tick(s:dict,c:dict)->list[str]:
    notes=[];now=_now(c,"customer_care")
    if not c["open"]:return notes
    for t in c["tasks"]:
        if not _cs_classic(t) or t["status"] in ("completed","referred","cancelled"):continue
        _cs_fields(t);name=NPC_INDEX[t["npc"]]["display_name"]
        if t["day"]==c["day"]:_cs_task_hook(c,t)
        if t["sla_at"] and t["sla"] is None and not t["identity"] and now>t["sla_at"]:
            t["sla"]="late";t["mistakes"]+=1;t["patience"]=max(25,t.get("patience",100)-15);t["tone"]=_cs_step(t["tone"],1)
            notes.append(f'⏰ Quá hạn phản hồi đầu: {name} chờ lâu rồi ({t["title"]}).')
        u=t["upd"]
        if u and not u["done"] and not u["late"] and now>u["by"]:
            u["late"]=True;t["mistakes"]+=1;t["patience"]=max(25,t.get("patience",100)-10);t["tone"]=_cs_step(t["tone"],1)
            notes.append(f'📞 {name} phải tự gọi lên hỏi tiến độ vì chưa ai gọi cập nhật trước 12:00.')
    return notes


def _cs_after_task(s:dict,c:dict,t:dict,status:str)->None:
    care=cs_care(c);row=care["people"].setdefault(t["npc"],dict(n=0,last=[]))
    post=next((f for f in c["feed"] if f.get("source")==t["id"] and f.get("kind")=="review"),None)
    if _cs_classic(t):
        outcome={"reship":"gửi bù","trace":"đối soát giao nhận","exchange":"đổi đúng món","refund":"hoàn tiền","guide":"hướng dẫn"}.get(t.get("proposal") or t.get("solution"),"đã xử lý")
        days=max(0,c["day"]-t["day"])
        note=outcome+(f" · theo {days} ngày" if days else "")+(" · trễ hẹn" if t.get("sla")=="late" or (t.get("upd") or {}).get("late") else "")
    else:
        note={"perfect":"xử lý chuẩn","good":"đã xử lý","wrong":"xử lý chưa đúng"}.get(t.get("grade"),"đã xử lý")
    row["n"]+=1
    row["last"]=ar.last(row["last"]+[dict(day=c["day"],title=t["title"][:120],note=note[:80],stars=post["stars"] if post and post.get("stars") else None)],4,"care.person."+t["npc"],c)


def cs_restar(c:dict,post:dict,before:int,after:int)->bool:
    """A review's stars changed after the visit (🚔 the police raised them, game/review_police.py): the person's card
    keeps a snapshot of each visit's stars (_cs_after_task), so that visit follows. Matched by the person, the day, the
    job title and the stars it had; the values stay 1–5 as before. True when a visit was updated."""
    care=_care(c);row=(care.get("people") or {}).get(post.get("npc")) if isinstance(care,dict) else None
    if not isinstance(row,dict) or not isinstance(row.get("last"),list):return False
    title=str((post.get("feedback") or {}).get("title") or "")[:120]
    for x in reversed(row["last"]):
        if isinstance(x,dict) and x.get("day")==post.get("day") and x.get("title")==title and x.get("stars")==before:
            x["stars"]=after;return True
    return False


def _cs_close(s:dict,c:dict)->list[str]:
    care=cs_care(c);day=c["day"];lines=[]
    stars=[f["stars"] for f in c["feed"] if f.get("kind")=="review" and f.get("day")==day and f.get("stars") and f.get("npc") in NPC_INDEX and NPC_INDEX[f["npc"]]["career_id"]=="customer_care"]
    if stars:
        care["trend"]=ar.last(care["trend"]+[dict(day=day,avg10=round(sum(stars)*10/len(stars)),n=len(stars))],7,"care.trend",c)
        prev=care["trend"][-2]["avg10"] if len(care["trend"])>=2 else None
        now10=care["trend"][-1]["avg10"]
        arrow="" if prev is None else " ↑" if now10>prev else " ↓" if now10<prev else " ="
        lines.append(f"Mức hài lòng hôm nay: {now10/10:.1f}★ từ {len(stars)} đánh giá{arrow}.".replace(".",",",1))
    waiting=[t for t in c["tasks"] if _cs_classic(t) and t["status"]=="executing" and t.get("ready_at") and t["ready_at"]//inv.DAY_MIN>day]
    for t in waiting[:3]:
        lines.append(f'Mang sang mai: “{t["title"]}” chờ {CS_WAIT_LABEL.get(t["wait"],"đầu mối")} · {inv.when(t["ready_at"],_day_at(day,inv.hours("customer_care")[1]))}. Sáng mai gọi cập nhật trước 12:00.')
    return lines


def _cs_notices(c:dict)->list[str]:
    care=_care(c)
    if not care or "people" not in care:return []
    out=[];now=_now(c,"customer_care")
    h=care.get("handover")
    if h and not h["read"] and h["day"]==c["day"]:out.append(f'🗂️ Bàn giao từ ca hôm qua: {len(h["rows"])} vụ còn mở.')
    for t in c["tasks"]:
        if not _cs_classic(t) or t["status"] in ("completed","referred","cancelled"):continue
        u=t.get("upd")
        if u and not u["done"] and not u["late"]:out.append(f'📞 Gọi cập nhật cho {NPC_INDEX[t["npc"]]["display_name"]} trước 12:00 ({t["title"]}).')
        if t.get("sla_at") and t.get("sla") is None and not t["identity"] and now<=t["sla_at"]:
            out.append(f'⏳ {NPC_INDEX[t["npc"]]["display_name"]} chờ phản hồi đầu, còn {_left(t["sla_at"]-now)}.')
    return out[:4]


def cs_task_public(c:dict,t:dict,v:dict)->None:
    """Derived timers for one classic support case (public view)."""
    _cs_fields(v)
    now=_now(c,"customer_care")
    v["eta"]=_cs_eta(c,t) if t.get("ready_at") and t["status"] in ("executing","handed_over") else None
    v["wait_label"]=CS_WAIT_LABEL.get(t.get("wait")) if t["status"] in ("executing","handed_over") else None
    v["days_open"]=max(0,c["day"]-t["day"])
    v["sla_left"]=max(0,t["sla_at"]-now) if t.get("sla_at") and t.get("sla") is None and not t["identity"] else None
    v["sla_label"]=_left(v["sla_left"]) if v["sla_left"] is not None else None
    u=t.get("upd");v["upd_label"]=("đã gọi" if u["done"] else "trễ hẹn" if u["late"] else f'trước 12:00 · còn {_left(u["by"]-now)}') if u else None
    v["tone_label"]=CS_TONE_LABEL.get(v["tone"],"bình tĩnh")
    v["picks"]=[dict(id=k,label=l) for k,l in CS_PICKS.items()]
    v["call_left"]=CS_CALL_MAX-(t.get("call_n",0) if t.get("call_day")==c["day"] else 0)
    e=_cs_basis(t);v["basis"]=e["id"] if e and t["identity"] and len(t["inspected"])>=len(t["evidence"]) else None  # 📌 the line to choose by, once every source is read


def _cs_public(c:dict,care:dict)->dict:
    v=tree_copy(care);now=_now(c,"customer_care")
    people=[]
    for npc,row in care["people"].items():
        if npc in NPC_INDEX:people.append(dict(row,npc=npc,name=NPC_INDEX[npc]["display_name"],open=sum(1 for t in c["tasks"] if t.get("npc")==npc and t["status"] not in ("completed","referred","cancelled"))))
    people.sort(key=lambda x:(-x["open"],-x["n"]))
    v["people"]=people
    board=[]
    for t in c["tasks"]:
        if t.get("career")!="customer_care" or t["status"] in ("completed","referred","cancelled"):continue
        row=dict(task=t["id"],title=t["title"],npc=t["npc"],name=NPC_INDEX[t["npc"]]["display_name"],status=t["status"],desk=bool(t.get("desk")),days_open=max(0,c["day"]-t["day"]),
                 repeat=care["people"].get(t["npc"],{}).get("n",0))
        if _cs_classic(t):
            tmp=dict(t);cs_task_public(c,t,tmp)
            row.update(eta=tmp["eta"],wait_label=tmp["wait_label"],sla_label=tmp["sla_label"],upd_label=tmp["upd_label"],tone_label=tmp["tone_label"],late=t.get("sla")=="late" or bool((t.get("upd") or {}).get("late")))
        board.append(row)
    v["board"]=board
    v["alerts"]=_cs_notices(c)
    v["clock"]=_clock_view(c,"customer_care")
    return v


def _cs_validate(care:dict)->None:
    need(set(care)=={"v","people","trend","handover","log"},"Bảng theo dõi không hợp lệ.")
    integer(care["v"],1,1)
    need(isinstance(care["people"],dict) and len(care["people"])<=40,"Thẻ khách không hợp lệ.")
    for npc,row in care["people"].items():
        need(npc in NPC_INDEX and NPC_INDEX[npc]["career_id"]=="customer_care","Thẻ khách sai nghề.")
        need(isinstance(row,dict) and set(row)=={"n","last"},"Thẻ khách không hợp lệ.");integer(row["n"],0,10**6)
        need(isinstance(row["last"],list) and len(row["last"])<=4,"Thẻ khách không hợp lệ.")
        for x in row["last"]:
            need(isinstance(x,dict) and set(x)=={"day","title","note","stars"},"Thẻ khách không hợp lệ.")
            integer(x["day"],1,10**7);clean_text(x["title"],120);clean_text(x["note"],80);need(x["stars"] in (None,1,2,3,4,5),"Sao không hợp lệ.")
    need(isinstance(care["trend"],list) and len(care["trend"])<=7,"Xu hướng hài lòng không hợp lệ.")
    for x in care["trend"]:
        need(isinstance(x,dict) and set(x)=={"day","avg10","n"},"Xu hướng hài lòng không hợp lệ.");integer(x["day"],1,10**7);integer(x["avg10"],10,50);integer(x["n"],1,1000)
    h=care["handover"]
    if h is not None:
        need(isinstance(h,dict) and set(h)=={"day","read","rows","night"} and type(h["read"]) is bool,"Bàn giao không hợp lệ.")
        integer(h["day"],1,10**7)
        need(isinstance(h["rows"],list) and len(h["rows"])<=6 and isinstance(h["night"],list) and len(h["night"])<=4,"Bàn giao không hợp lệ.")
        for r in h["rows"]:
            need(isinstance(r,dict) and set(r)=={"task","title","npc","name","status","next","eta","desk"},"Bàn giao không hợp lệ.")
            for k in ("task","title","name","status","next"):clean_text(r[k],200)
            need(r["npc"] in NPC_INDEX and (r["eta"] is None or isinstance(r["eta"],str)) and type(r["desk"]) is bool,"Bàn giao không hợp lệ.")
        for line in h["night"]:clean_text(line,300)
    _validate_lines(care["log"],30)


def _cs_validate_task(t:dict)->None:
    """Extra fields of a classic support case (all optional on older saves)."""
    for k in ("ready_at","sla_at"):
        if t.get(k) is not None:integer(t[k],0,10**9)
    need(t.get("wait") in (None,*CS_WAIT_LABEL),"Bên đang chờ không hợp lệ.")
    need(t.get("sla") in (None,"ok","late"),"Hạn phản hồi không hợp lệ.")
    u=t.get("upd")
    if u is not None:
        need(isinstance(u,dict) and set(u)=={"day","by","done","late"} and type(u["done"]) is bool and type(u["late"]) is bool,"Hẹn cập nhật không hợp lệ.")
        integer(u["day"],1,10**7);integer(u["by"],0,10**9)
    need(t.get("tone",CS_TONES[1]) in CS_TONES,"Giọng khách không hợp lệ.")
    need(type(t.get("promised",False)) is bool,"Trạng thái cuộc gọi không hợp lệ.")
    integer(t.get("call_day",0),0,10**7);integer(t.get("call_n",0),0,CS_CALL_MAX)
    call=t.get("call",[])
    need(isinstance(call,list) and len(call)<=20,"Cuộc gọi không hợp lệ.")
    for x in call:
        need(isinstance(x,dict) and x.get("who") in ("player","npc"),"Cuộc gọi không hợp lệ.")
        clean_text(x.get("text"),600)
        if x["who"]=="npc":
            need(x.get("mode") in ("scripted","ai","guard") and x.get("tone") in CS_TONES,"Cuộc gọi không hợp lệ.")
            if "canonical" in x:clean_text(x["canonical"],600)
        need(set(x)<={"who","text","mode","tone","canonical"},"Cuộc gọi không hợp lệ.")


# ---------------------------------------------------------------- dispatch and hooks
def care_action(s:dict,c:dict,career:str,action:str,p:dict)->dict:
    need(c["open"],"Mở ca trước khi làm việc nhé.")
    if action.startswith("ph_"):
        need(career=="pharmacy","Thao tác này thuộc quầy thuốc.");return _ph_action(s,c,action,p)
    if action.startswith("ac_"):
        need(career=="accounting","Thao tác này thuộc bàn sổ sách.");return _ac_action(s,c,action,p)
    need(career=="customer_care","Thao tác này thuộc trạm hỗ trợ.")
    if action=="cs_call":return _cs_call(s,c,p)
    care=cs_care(c);h=care["handover"];need(h and h["day"]==c["day"],"Hôm nay không có bàn giao nào.")
    h["read"]=True
    return dict(message="Đã đọc bàn giao. Các vụ còn mở nằm trên Bảng theo dõi.")


def care_start(s:dict,c:dict,career:str)->list[str]:
    if career=="pharmacy":return _ph_start(s,c)
    if career=="accounting":
        care=ac_care(c)
        return _ac_arrivals(c,care)
    if career=="customer_care":return _cs_start(s,c)
    return []


def care_tick(s:dict,c:dict,career:str)->list[str]:
    notes=[]
    if career in ("mother_baby","pharmacy"):notes+=_stock_tick(s,c,career)
    if career=="pharmacy" and (c["open"] or _care(c) is not None):_ph_sync(c,ph_care(c))  # older saves start their lot book mid-shift
    if career=="accounting" and c["open"]:notes+=_ac_arrivals(c,ac_care(c))
    if career=="customer_care" and c["open"]:
        cs_care(c)
        notes+=_cs_tick(s,c)
    return notes


def care_close(s:dict,c:dict,career:str)->list[str]:
    if career=="pharmacy":return _ph_close(s,c)
    if career=="accounting":return _ac_close(s,c)
    if career=="customer_care":return _cs_close(s,c)
    return []


def care_notices(c:dict,career:str)->list[str]:
    return {"pharmacy":_ph_notices,"accounting":_ac_notices,"customer_care":_cs_notices}[career](c) if career in CARE_CAREERS else []


def care_public(c:dict,career:str)->dict|None:
    care=_care(c)
    if care is None:return None
    if career=="pharmacy":
        # _ph_sync writes to the care book only: that is copied, the rest of the career is read as it is.
        cp=tree_copy(care);tmp=dict(c,ext=dict(c["ext"],data=dict(c["ext"]["data"],care=cp)));_ph_sync(tmp,cp)
        return _ph_public(tmp,cp)
    if career=="accounting":return _ac_public(c,care)
    return _cs_public(c,care)


def care_validate(c:dict,cid:str)->None:
    care=_care(c)
    if cid in ("mother_baby","pharmacy"):
        known={x["id"] for x in stock_suppliers(cid)}|{"partner"}
        for x in c["shipments"]:
            if "at" not in x:continue
            need(set(x)<={"id","item","qty","actual","supplier","cost","status","placed","lo","hi","at","late","day","told"},"Kiện hàng có trường lạ.")
            need(x.get("supplier") in known,"Nhà cung cấp của kiện không hợp lệ.")
            for k in ("placed","lo","hi","at"):integer(x.get(k),0,10**9)
            need(x["placed"]<=x["lo"]<=x["hi"] and x["at"]>=x["placed"],"Giờ giao của kiện không hợp lệ.")
            need(x.get("late") is None or (isinstance(x["late"],str) and len(x["late"])<=300),"Lý do trễ không hợp lệ.")
            integer(x.get("day"),1,10**7);need(type(x.get("told",False)) is bool,"Kiện hàng không hợp lệ.")
    if cid not in CARE_CAREERS:return
    if cid=="customer_care":
        for t in c["tasks"]:
            if _cs_classic(t):_cs_validate_task(t)
    if care is None:return
    need(isinstance(care,dict),"Dữ liệu chăm sóc không hợp lệ.")
    {"pharmacy":_ph_validate,"accounting":_ac_validate,"customer_care":_cs_validate}[cid](care)
