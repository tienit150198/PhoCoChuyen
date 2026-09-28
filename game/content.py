"""Authored content and deterministic task factories. No network dependencies.

The reference directory is the user's design baseline, not executable code.
Runtime scripts live in game/events.py and are intentionally separate.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from . import operations
from . import extra_content as extra
from . import experiences as life
from . import inventory
from . import employment
from . import situations
from . import incidents
from . import happenings
from . import desk
from .careers import PLUGINS

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference" / "data"

def load_reference(name: str):
    return json.loads((REFERENCE / name).read_text(encoding="utf-8"))

CATALOG = load_reference("catalog_16_careers.json")
NPCS = load_reference("npcs_24.json") + extra.NPCS
NPC_INDEX = {n["id"]: n for n in NPCS}
EVENT_SEEDS = load_reference("events_96.json")
QUEST_SEEDS = load_reference("quests_12.json")
CAREERS = ("mother_baby", "pharmacy", "accounting", "customer_care") + extra.NEW_CAREERS + tuple(PLUGINS)
CAREER_META = {
    "mother_baby": dict(short="Tiệm mẹ & bé", place="Tiệm Mây Nhỏ", tagline="Gói một món quà. Giữ một niềm vui.", icon="gift", color="#bc6589", light="#ffe7ef", weather="Nắng dịu", work="Đơn hàng", station="Quầy thu ngân", greeting="Khách đầu tiên đang chờ bạn. Chạm vào khách để làm quen nhé.", caption="Một tiệm nhỏ, rất nhiều câu chuyện", map_label="01 · GÓC PHỐ ẤM ÁP"),
    "pharmacy": dict(short="Nhà thuốc nhỏ", place="Quầy Bình An", tagline="Chậm một nhịp. Đúng từng chi tiết.", icon="cross", color="#398b83", light="#dff4ec", weather="Trời trong", work="Phiếu", station="Khay kiểm tra", greeting="Chạm vào khách, đọc phiếu và lấy đúng mã hộp.", caption="Sự cẩn thận cũng có câu chuyện của nó", map_label="02 · QUẦY BÌNH AN"),
    "accounting": dict(short="Một ngày làm kế toán", place="Góc Sổ Xinh", tagline="Mỗi con số đều có một câu chuyện.", icon="book", color="#8d76bb", light="#eee5fa", weather="Mây nhẹ", work="Hồ sơ", station="Bàn đối chiếu", greeting="Huy mang tới một hồ sơ. Hãy mở bản gốc trước khi đối chiếu.", caption="Những câu đố nhỏ trên bàn làm việc", map_label="03 · GÓC SỔ XINH"),
    "customer_care": dict(short="Chăm sóc khách hàng", place="Trạm Lắng Nghe", tagline="Lắng nghe thật. Giải quyết tới nơi.", icon="headphones", color="#538eb0", light="#e1f0fa", weather="Gió mát", work="Yêu cầu", station="Bàn hỗ trợ", greeting="Có một khách cần bạn giúp. Chạm vào chuông hoặc khách để bắt đầu.", caption="Biến một lời phàn nàn thành một việc đã xong", map_label="04 · TRẠM LẮNG NGHE"),
}
CAREER_META.update(extra.META)
CATALOG.extend(extra.CATALOG)
for _cid, _mod in PLUGINS.items():
    _meta = dict(_mod.SPEC['meta'])
    CAREER_META[_cid] = _meta
    _row = next((x for x in CATALOG if x['id'] == _cid), None)
    if _row is None:
        CATALOG.append(dict(id=_cid, title=_meta['short'], name=_meta['short'], core_loop=_meta['tagline'], status='playable', **_meta))
    else:
        _row.update(_meta, status='playable')
    _row = next(x for x in CATALOG if x['id'] == _cid)
    _row['category'] = _mod.SPEC.get('category', 'shop')

PRODUCTS = [
    dict(id="bunny", name="Thỏ bông Mây", category="toy", icon="bunny", color="cream", price=75, cost=36, description="Thỏ vải mềm màu kem, nơ nhỏ màu lá."),
    dict(id="bear", name="Gấu Mật Ong", category="toy", icon="bear", color="brown", price=95, cost=48, description="Gấu bông tròn, mặc áo sọc nhỏ."),
    dict(id="cat_bag", name="Túi vải Mèo", category="bag", icon="bag", color="cream", price=85, cost=40, description="Túi màu kem có mặt mèo thêu."),
    dict(id="cloud_shirt", name="Áo Mây xanh", category="clothes", icon="shirt", color="blue", price=65, cost=30, description="Áo xanh hình đám mây · cỡ M."),
    dict(id="rose_shirt", name="Áo Mây hồng", category="clothes", icon="shirt", color="rose", price=65, cost=30, description="Áo hồng hình đám mây · cỡ M."),
    dict(id="towel", name="Khăn Lá mềm", category="cloth", icon="cloth", color="mint", price=35, cost=16, description="Khăn xanh lá, gấp thành một chiếc nơ."),
    dict(id="blocks", name="Khối ghép gỗ", category="puzzle", icon="blocks", color="blue", price=110, cost=55, description="Bộ khối gỗ trong hộp xanh, hình ngôi nhà."),
    dict(id="card", name="Thiệp Nắng", category="card", icon="card", color="cream", price=10, cost=4, description="Một chiếc thiệp nhỏ có chỗ viết lời chúc."),
]
from . import giftshop as _gift  # mother_baby v2: new shelf items and the age/safety label printed on each box
PRODUCTS += copy.deepcopy(_gift.NEW_PRODUCTS)
for _p in PRODUCTS:_p.update(copy.deepcopy(_gift.LABELS[_p["id"]]))
PRODUCT_INDEX = {p["id"]: p for p in PRODUCTS}
PAPERS = [dict(id="cream", name="Kem ấm", color="#ecd9af"), dict(id="blue", name="Xanh trời", color="#a5c6db"), dict(id="rose", name="Hồng phấn", color="#dfabb6"), dict(id="mint", name="Xanh lá", color="#b6cbaa"), dict(id="red", name="Đỏ Tết", color="#c9443b")]
RIBBONS = [dict(id="gold",name="Nơ vàng",color="#c19444"),dict(id="rust",name="Nơ cam đất",color="#b66f57"),dict(id="green",name="Nơ xanh",color="#63856b")]
PH_PRODUCTS = [dict(id=f"P-{i:02d}", name=name, icon="box", color=color) for i,name,color in [
    (1,"Hộp Mây trắng","cream"),(2,"Hộp Lá","mint"),
    (3,"Hộp Mây xanh","blue"),(4,"Hộp Sao","blue"),
    (5,"Hộp Nắng","rose"),(6,"Bộ vật dụng","cream")]]
LOT_INDEX = {}
for p in PH_PRODUCTS:
    for suffix,status,day in [("A","available",99999),("B","held",99999),("C","expired",0)]:
        lid = f'{p["id"]}-{suffix}'
        LOT_INDEX[lid] = dict(id=lid,product=p["id"],name=p["name"],color=p["color"],status=status,valid_until=day, cost=8)

UPGRADES = [
    dict(id="plant",name="Cây bên cửa sổ",icon="plant",price=45,kind="decor",description="Một góc xanh. Khách có thể nhận ra cây mới.",min_level=1),
    dict(id="rug",name="Thảm sợi ấm",icon="rug",price=60,kind="decor",description="Đổi tấm thảm giữa phòng. Có thể chọn vị trí.",min_level=1),
    dict(id="lamp",name="Đèn sàn dịu",icon="lamp",price=80,kind="decor",description="Một vệt sáng ấm trong góc tiệm.",min_level=1),
    dict(id="seat",name="Ghế khách quen",icon="chair",price=90,kind="decor",description="Khách ghé nghỉ. Mở thêm một góc trang trí.",min_level=1),
    dict(id="shelf",name="Kệ mở rộng",icon="shelf",price=120,kind="tool",description="Tăng sức chứa mỗi mã hàng từ 12 lên 24; thêm kệ trong cảnh.",min_level=2,careers=["mother_baby","pharmacy"]),
    dict(id="workbench",name="Bàn kiểm hai bước",icon="check",price=100,kind="tool",description="Mở gợi ý so sánh trên bàn thao tác; vẫn cần tự kiểm và xác nhận.",min_level=2),
    dict(id="board",name="Bảng ghim lời hẹn",icon="board",price=110,kind="tool",description="Thêm bảng trong cảnh và nhắc các việc đang chờ khi mở ngày.",min_level=2),
    dict(id="assistant",name="Bạn phụ việc",icon="people",price=160,kind="tool",description="Một bạn phụ việc có mặt ở tiệm; mỗi ngày hỗ trợ một đơn nhập hoặc một gợi ý nghiệp vụ.",min_level=3),
    dict(id="poster",name="Tranh khu phố",icon="image",price=70,kind="decor",description="Một bức tranh nho nhỏ trên tường.",min_level=1),
]
UPGRADE_INDEX={u["id"]:u for u in UPGRADES}

# Concrete milestone conditions; story text comes from the authored baseline.
QUEST_RULES = {
    "MB-Q01":[("served",1,"Phục vụ vị khách đầu tiên"),("packed",2,"Gói hai món quà"),("served:mother_baby_npc_02",1,"Giúp bác Tư chọn quà")],
    "MB-Q02":[("events",1,"Giải quyết một chuyện ở tiệm"),("replies",1,"Trả lời một bình luận"),("events",3,"Theo dõi thêm chuyện trong phố")],
    "MB-Q03":[("decorations",1,"Chăm chút một góc tiệm"),("posts",1,"Đăng lời mời trên Chuyện phố"),("served",6,"Phục vụ sáu lượt khách")],
    "PH-Q01":[("clarified",1,"Hỏi lại một phiếu chưa đủ"),("ph_verified",2,"Đối chiếu hai phiếu"),("served:pharmacy_npc_03",1,"Hoàn tất phiếu của Lan")],
    "PH-Q02":[("ph_verified",1,"Tự kiểm phiếu đầu tiên"),("inspections",3,"Kiểm ba nhãn lô"),("served",5,"Hoàn tất năm lượt phục vụ")],
    "PH-Q03":[("events",1,"Giải quyết một chuyện ở quầy"),("decorations",1,"Bố trí một góc thân thiện"),("posts",1,"Chia sẻ chuyện phục vụ cẩn thận")],
    "AC-Q01":[("source_reads",2,"Đọc hai bản gốc"),("matched",2,"Nối hai nhóm đúng"),("served:accounting_npc_01",1,"Bàn giao một hồ sơ cho Huy")],
    "AC-Q02":[("served",2,"Giải xong hai hồ sơ"),("source_requests",1,"Xin một nguồn bổ sung"),("served:accounting_npc_03",1,"Giải thích sổ của cô Hoa")],
    "AC-Q03":[("events",1,"Xử lý một tình huống văn phòng"),("served",5,"Hoàn thành năm hồ sơ có căn cứ"),("replies",1,"Phản hồi một lời góp ý")],
    "CS-Q01":[("identity_checked",1,"Xác minh đúng yêu cầu"),("cs_executed",1,"Phối hợp thực hiện một phương án"),("served",2,"Theo dõi và đóng hai vụ")],
    "CS-Q02":[("handovers",1,"Bàn giao đủ thông tin"),("cs_confirmed",1,"Nhận kết quả đã kiểm chứng"),("served",4,"Giải quyết bốn yêu cầu")],
    "CS-Q03":[("replies",1,"Trả lời review có nguồn"),("events",2,"Xử lý hai chuyện tại trạm"),("served",6,"Hoàn tất sáu vụ")],
}
QUESTS=[]
for q in QUEST_SEEDS:
    rules=QUEST_RULES[q["id"]]
    QUESTS.append(dict(id=q["id"],career=q["career_id"],title=q["title"],story=q["story_outline"],
        steps=[dict(metric=m,goal=g,title=t) for m,g,t in rules],reward=75,keepsake=q["title"]))
QUEST_INDEX={q["id"]:q for q in QUESTS}


def task_id(career: str, day: int, slot: int) -> str:
    return f"{career}-{day:04d}-{slot:02d}"


def make_task(career: str, day: int, slot: int, serial: int, classic: bool=False) -> dict:
    """Fixed by game day/slot. Looking at evidence never changes the truth.
    `classic` rebuilds the pre-desk task of a slot, for saves made before the paperwork desks."""
    if career in extra.NEW_CAREERS:return extra.make_task(career,day,slot,serial)
    if career in PLUGINS:return PLUGINS[career].make_task(day,slot,serial)
    n = (day - 1) * 3 + slot
    base=dict(id=task_id(career,day,slot),career=career,day=day,status="new",created_turn=serial,
              known=False, inspected=[], notes=[], mistakes=0, chat=[], kind=career, deferred=False)
    if career in desk.CAREERS and not classic:
        paper=desk.make_task(career,day,slot,serial,base)
        if paper:return paper
    if career=="mother_baby" and not classic and day>=_gift.GEN_FROM_DAY:
        base.update(_gift.make_fields(day,slot))
    elif career=="mother_baby":
        plans=[
            (1,"Một món quà nhỏ","Mình cần quà tặng chị gái. Bạn giúp mình chọn nhé?","cat_bag",1,150,"cream",True),
            (2,"Quà của bác Tư","Bác muốn chọn một bạn thú bông dễ thương.","bunny",1,120,"blue",True),
            (3,"Chiếc áo xanh","Mình cần một chiếc áo Mây xanh, lấy nhanh giúp mình nhé.","cloud_shirt",1,90,"blue",False),
            (1,"Một đôi khăn Lá","Mình muốn mua hai khăn Lá, gói chung được không?","towel",2,100,"mint",True),
            (2,"Hộp ghép hình","Bác tìm bộ khối gỗ màu xanh cho cháu.","blocks",1,140,"cream",True),
            (3,"Gấu Mật Ong","Mình muốn tặng một chú gấu nâu, kèm lời chúc.","bear",1,130,"rose",True),
            (1,"Chiếc áo màu hồng","Mình lấy áo Mây hồng, không cần gói quà nhé.","rose_shirt",1,90,"rose",False),
            (2,"Một lời cảm ơn","Bác muốn mua hai thiệp Nắng để gửi hàng xóm.","card",2,35,"cream",False),
        ]
        who,title,opening,pid,qty,budget,paper,gift=plans[n%len(plans)]
        base.update(npc=f"{career}_npc_{who:02d}", title=title, opening=opening,
            needs=dict(product=pid,qty=qty,budget=budget,paper=paper,gift=gift),basket={},pack=None,checked=False)
    elif career=="pharmacy":
        who=[2,3,2,3,4,2][n%6]
        product=PH_PRODUCTS[[0,2,3,1,4,5][n%6]]["id"]
        missing=n%3==1
        base.update(npc=f"{career}_npc_{who:02d}",title=["Phiếu đầu tiên","Người mua hộ","Hai hộp gần giống","Phiếu cần kiểm lô","Kiểm đúng số lượng","Bộ vật dụng khu phố"][n%6],
            opening="Mình mua hộ, chỉ nhớ hộp màu xanh. Bạn giúp mình kiểm lại nhé." if missing else "Mình có phiếu của phòng khám đây, nhờ bạn lấy đúng mã và số lượng.",
            needs=dict(product=product,qty=1+n%2,missing=missing,referral=n%9==8),basket={},checks=[],checked=False)
    elif career=="accounting":
        who=[1,3,2,4,5,6][n%6]
        variant=["duplicate","typo","many_one","missing","one_many","refund"][n%6]
        offset=(day-1)*10
        d1,d2,d3=120+offset,180+offset,250+offset
        docs=[dict(id="CT-01",ref="HD-101",amount=d1,original=d1,source="Phiếu gốc HD-101",kind="thu"),
              dict(id="CT-02",ref="HD-102",amount=d2,original=d2,source="Phiếu gốc HD-102",kind="thu"),
              dict(id="CT-03",ref="HD-103",amount=d3,original=d3,source="Phiếu gốc HD-103",kind="thu")]
        tx=[dict(id="GD-01",amount=d1+d2,refs=["HD-101","HD-102"],note="Thanh toán chung HD-101 và HD-102"),
            dict(id="GD-02",amount=d3,refs=["HD-103"],note="Thanh toán HD-103")]
        if variant=="duplicate":
            docs.append(dict(id="CT-04",ref="HD-103",amount=d3,original=d3,source="Bản sao cùng phiếu HD-103",kind="thu",duplicate_of="CT-03"))
        elif variant=="typo": docs[1]["amount"]=d2+90
        elif variant=="missing": docs[1]["missing"]=True
        elif variant=="one_many":
            tx=[dict(id="GD-01",amount=d1,refs=["HD-101"],note="Thanh toán HD-101"),dict(id="GD-02",amount=d2,refs=["HD-102"],note="Thanh toán HD-102"),
                dict(id="GD-03",amount=100,refs=["HD-103"],note="HD-103 · trả lần 1"),dict(id="GD-04",amount=d3-100,refs=["HD-103"],note="HD-103 · trả lần 2")]
        elif variant=="refund":
            docs[2].update(amount=-50,original=-50,kind="hoàn")
            tx[1].update(amount=-50,note="Hoàn một phần HD-103")
        title={"duplicate":"Tổng dư 250 xu?","typo":"Một chữ số đi lạc","many_one":"Hai phiếu, một lần trả","missing":"Chờ phiếu còn thiếu","one_many":"Một phiếu, hai lần trả","refund":"Khoản hoàn không phải thu mới"}[variant]
        if day>1 and variant=="duplicate":title="Có một bản tính lặp"
        base.update(npc=f"{career}_npc_{who:02d}",title=title,opening="Bạn giúp mình đối chiếu bộ hồ sơ này nhé. Mình cần biết số nào có căn cứ, phần nào còn thiếu.",
            variant=variant,docs=docs,transactions=tx,removed=[],groups=[],source_requested=False,source_ready=0,explanation="")
    else:
        variants=[
            (1,"missing","Đơn thiếu một món","Mình nhận được hai món nhưng đơn có ba món. Bạn kiểm tra giúp mình nhé.","reship",180),
            (2,"delivered","Đã giao nhưng chưa nhận","Mình chưa nhận hàng. Sao hệ thống ghi đã giao rồi?","trace",240),
            (3,"delay","Một lời hẹn cần giữ","Hàng của mình đang ở đâu? Mình cần biết mốc cập nhật tiếp theo.","trace",160),
            (1,"wrong","Màu nhận được khác đơn","Mình đặt hộp xanh nhưng nhận hộp hồng.","exchange",200),
            (2,"refund","Tiền hoàn đang ở đâu?","Mình thấy có yêu cầu hoàn nhưng chưa có kết quả.","refund",120),
            (3,"guide","Khách chỉ cần hướng dẫn","Mình muốn biết cách xem đơn trong ứng dụng của cửa hàng.","guide",0),
        ]
        who,variant,title,opening,solution,value=variants[n%6]
        evidence={
            "missing":[("Đơn gốc","Đơn đã xác minh có 3 món."),("Biên bản đóng gói","Ca đóng gói ghi nhận mới có 2 món trong kiện."),("Chính sách đổi trả","Được gửi bù phần thiếu hoặc hoàn phần thiếu sau xác minh.")],
            "delivered":[("Trạng thái giao","Màn vận chuyển đang ghi Đã giao."),("Chứng cứ giao","Biên bản có mã điểm giao khác mã điểm nhận của đơn."),("Quy trình đối soát","Cần đầu mối giao nhận kiểm tra; chưa thể kết luận khách đã nhận.")],
            "delay":[("Trạng thái giao","Kiện đang ở điểm trung chuyển, chưa có xác nhận giao."),("Phản hồi đầu mối","Có thể mở kiểm tra chặng và hẹn cập nhật ở nhịp tiếp theo."),("Quy định cập nhật","Không được báo đã giao khi chưa có kết quả.")],
            "wrong":[("Đơn gốc","Mã màu đã chốt là XANH."),("Biên bản nhận","Mã màu trên kiện nhận là HỒNG."),("Chính sách đổi","Tạo yêu cầu đổi đúng mã; theo dõi trước khi đóng.")],
            "refund":[("Yêu cầu hoàn","Có yêu cầu hoàn 120 xu từ quỹ công ty."),("Nhật ký thực hiện","Yêu cầu mới tạo, chưa có mã xác nhận hoàn thành."),("Phê duyệt","Khoản này nằm trong quyền xử lý; phải thực thi và kiểm kết quả.")],
            "guide":[("Mục tiêu khách","Khách chỉ cần xem trạng thái đơn trong ứng dụng của cửa hàng."),("Hướng dẫn đã duyệt","Mở Điện thoại → Đơn của tôi → chọn đúng mã."),("Điều kiện đóng","Khách xác nhận đã làm được bước hướng dẫn.")],
        }
        base.update(npc=f"{career}_npc_{who:02d}",title=title,opening=opening,variant=variant,
            identity=False,evidence=[dict(id=f"BC-{i+1}",title=t,text=d) for i,(t,d) in enumerate(evidence[variant])],
            solution=solution,value=value,proposal=None,ready_turn=0,confirmed=False,handed_over=False,timeline=[])
    return base


def initial_career(career: str) -> dict:
    stock={p["id"]:6 for p in PRODUCTS} if career=="mother_baby" else {k:(6 if v["status"]=="available" else 2) for k,v in LOT_INDEX.items()} if career=="pharmacy" else {}
    return dict(day=1,open=False,started=False,turn=0,money=320,xp=0,stock=stock,held_lots=[],tasks=[],active_task=None,metrics={},
        upgrades=[],decor={},relationships={},memories=[],journal=[],feed=[],chats={},event=None,event_history=[],pending=[],
        quests_claimed=[],album=[],earnings=0,costs=0,day_start_money=320,day_completed=0,day_events=0,assistant_day=0,
        shipments=[],post_likes=[],completed_ids=[],weather_index=0,shift_summary=None,theme="boba",ops=operations.initial_operations(career),life=life.initial(career),
        ext=dict(seq=0,inv=inventory.initial(career),data=PLUGINS[career].initial() if career in PLUGINS else desk.initial(career),**situations.initial()),job=employment.initial(),incidents=incidents.initial(),happen=happenings.initial())


def public_content() -> dict:
    from . import journey  # the story layer imports this module; keep the import lazy
    catalogue=copy.deepcopy(CATALOG)
    for c in catalogue:
        c.update(CAREER_META.get(c["id"], {}))
    return dict(version="0.5.0",experiences=extra.public_content(),inventory=inventory.content(),employment=employment.content(CAREERS),
                situations={cid:situations.catalogue(cid) for cid in CAREERS},
                careers={cid:(PLUGINS[cid].content() if hasattr(PLUGINS[cid],'content') else {}) for cid in PLUGINS},operations=operations.content(),catalogue=catalogue,npcs=NPCS,products=PRODUCTS,ph_products=PH_PRODUCTS,lots=list(LOT_INDEX.values()),
                papers=PAPERS,ribbons=RIBBONS,upgrades=UPGRADES,quests=QUESTS,
                event_catalogue=[dict(id=e["id"],career=e["career_id"],title=e["title"],category=e["category"],min_day=e["min_game_day"]) for e in EVENT_SEEDS],
                journey=journey.content())
