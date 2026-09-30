"""Giao Nhanh Mây Chiều — an evening motorbike courier shift (plugin career).

Real work of the job: accept orders on the app, plan a route across the
neighbourhood (every ride costs minutes and fuel, rain makes both worse), pick
parcels up at the hub and weigh/inspect them (the declared weight is sometimes
wrong, a box may have a split seam), pack what the goods need (bubble wrap for
fragile, tape for a split seam, a rain bag on rainy days, a cold pack for
yoghurt, a strap for bulky items), respect the bike's load limit, wait for food
that is still cooking and check the bag against the bill, call customers when the
address is incomplete or they are out, count change for cash-on-delivery, and
hand the COD cash in at the hub.

Real consequences instead of walls: an unpadded glass vase breaks on the road and
the customer refuses it at the door (the courier pays half the value); a soaked
parcel or a missing soup bag is a complaint; wrong change is either a complaint
or money out of the courier's own pocket at settlement. Real refusals: the bike
does not carry more than 20 kg, registered mail is never left with a guard, and
COD cash above the carrying limit must be handed in before collecting more.

v0.5 — the road answers back:
* Road board of the day (deterministic): school-run or market-day jams in a time
  window, road works that force a 2-block detour, flooded alleys in heavy rain.
  Every leg can go by the main road or by the bumpy alley shortcut (one block
  shorter, dodges jams and works, but spills broth, wears the tyre twice as fast
  and stalls the engine in a flooded alley).
* Bike upkeep: the tyre wears with every block; below 40% a leg can end in a flat
  (a surprise with real choices); a tune-up at the petrol station resets it.
* Courier score: a rolling star rating (4.7★+ earns a priority bonus per order),
  a clean-delivery streak bonus and a daily "deliver N orders" target bonus.
* Surprises on the road (kit desk framework): checkpoint, sudden storm, a shop
  asking you to advance money, errands, a flat phone, an urgent medicine run, a
  scrape at a crossing, a customer threatening one star, a petrol station power cut;
  and order-bound ones: a dog at the gate, a COD customer who refuses the parcel
  ("bom hàng"), a customer who moved to another address.
Old saves: tasks made before v0.5 keep their generator (legacy serial band) and
all new data is added with setdefault.

Care (sub-project 3, docs/superpowers/specs/2026-09-29-delivery-care-design.md):
* Five scooter parts wear day after day (tyre, brakes, oil, chain, raincoat); each
  one has a single clear consequence below its line and is fixed at Chú Bảy's
  garage (`dl_fix`). A chain worn to 0 % slips off (DE-CHAIN).
* Regular customers keep a notes card (call first, gate code, carry it in for an
  elderly lady…) learned by delivering to them; honouring a note at the door
  (`dl_call` / `dl_care`) builds the bond, which pays a small thank-you.
* Neighbourhood knowledge: after working at a stop a few times its alley shortcut
  is smooth, later a local cut saves another block.
* The next shift's weather and road board are forecast with concrete advice.
"""
from __future__ import annotations
import copy
from . import kit
from . import till
from .. import consequences as cq
from .. import archive as ar
from .. import compensation as cf
from .. import patience as pt

ID = 'delivery'
DONE = ('completed', 'referred', 'cancelled')
START_FUEL = 60
LOAD_LIMIT = 200          # tenths of a kilogram (20 kg)
COD_CAP = 250             # cash a courier may carry before handing in
GRACE = pt.longer(25)     # minutes after the promised time before a food order is cancelled (PATIENCE_FACTOR)
MPU = {'sun': 3, 'rain': 5}          # minutes per map block
FUEL_RATE = {'sun': 2, 'rain': 3}    # % of tank per map block
FUEL_STEP = 5                        # fuel is sold in 5% steps
FUEL_PRICE = {'gas': 1, 'bottle': 2} # xu per step
BOTTLE_MAX = 20
NOTES = (50, 20, 10, 5, 2, 1)
STAIRS = {'apt': 4}
LATE_FEE = 4

NODES = {
    'hub': dict(name='Bưu cục Mây Chiều', emoji='📮', x=1, y=2, note='Nhận hàng, cân hàng, nộp tiền COD.'),
    'gas': dict(name='Cây xăng Gió Lộng', emoji='⛽', x=3, y=0, note='Xăng giá niêm yết.'),
    'com': dict(name='Cơm tấm Cô Ba', emoji='🍛', x=0, y=4, note='Quán đông, ra món nhanh.'),
    'bun': dict(name='Bún bò Dì Năm', emoji='🍜', x=4, y=1, note='Giờ cao điểm hay phải chờ.'),
    'tra': dict(name='Trà sữa Mây Hồng', emoji='🧋', x=2, y=3, note='Đơn online nhiều như mây.'),
    'apt': dict(name='Chung cư Mây Xanh', emoji='🏢', x=6, y=3, note='6 tầng, không thang máy.'),
    'alley': dict(name='Hẻm Ốc Bươu', emoji='🏘️', x=0, y=1, note='Số nhà nhảy lung tung.'),
    'school': dict(name='Trường Bồ Câu', emoji='🏫', x=2, y=0, note='Tan trường là kẹt xe.'),
    'market': dict(name='Chợ Chiều', emoji='🧺', x=3, y=2, note='Sạp hàng gửi đơn tại chợ.'),
    'office': dict(name='Tòa văn phòng Cỏ May', emoji='🏬', x=6, y=0, note='Lễ tân nhận hàng ở sảnh.'),
    'villa': dict(name='Nhà vườn Sứ Trắng', emoji='🏡', x=5, y=4, note='Cổng xa, có chòi bảo vệ.'),
    'vet': dict(name='Phòng khám thú y Mèo Mướp', emoji='🐾', x=4, y=4, note='Mèo nhiều hơn khách.'),
    'garage': dict(name='Tiệm sửa xe Chú Bảy', emoji='🔧', x=5, y=2, note='Thay nhớt, sên, má phanh, lốp, áo mưa.'),
}

ITEMS = [
    dict(id='bubble', name='Màng xốp hơi', emoji='🫧', group='pack', unit='cuộn nhỏ', cost=2, start=6),
    dict(id='tape', name='Băng keo dán thùng', emoji='🩹', group='pack', unit='đoạn', cost=1, start=10),
    dict(id='rainbag', name='Túi nilon chống nước', emoji='🛍️', group='pack', unit='túi', cost=1, start=8),
    dict(id='coldpack', name='Túi giữ lạnh + đá gel', emoji='🧊', group='pack', unit='bộ', cost=3, start=3),
    dict(id='strap', name='Dây ràng hàng cồng kềnh', emoji='🪢', group='pack', unit='sợi', cost=2, start=2, unlock=2),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}

PEOPLE = [
    ('Chị Mận', 'Chủ tiệm gốm online', 'Hàng nào cũng dặn “bọc kỹ giúp chị”.', 'picky'),
    ('Anh Tùng', 'Trưởng phòng dự án', 'Gọi ba cuộc liền nếu trễ một phút.', 'bossy'),
    ('Bé Vy', 'Sinh viên ở chung cư', 'Đặt trà sữa như uống nước lọc.', 'genz'),
    ('Bà Út', 'Chủ tạp hóa trong hẻm', 'Hay dúi cho shipper cái bánh.', 'warm'),
    ('Chú Hòa', 'Làm vườn ở Nhà vườn Sứ Trắng', 'Ít nói, nghe máy chậm.', 'quiet'),
    ('Cô Lệ', 'Bác sĩ thú y', 'Soi hàng kỹ như soi mèo bệnh.', 'sour'),
    ('Chị Hạnh', 'Điều phối viên bưu cục', 'Giọng qua bộ đàm lúc nào cũng bình tĩnh.', 'warm'),
]

_F = dict(kind='food', fragile=False, cold=False, paper=False, size='S', seam=False, away=0, unit=None,
          cod=0, cash=0, safe=False, by=None, missing=None)
_P = dict(kind='parcel', fragile=False, cold=False, paper=False, size='S', seam=False, away=0, unit=None,
          cod=0, cash=0, safe=False, by=None, missing=None, prep=0)

ORDERS = [
    dict(_F, key='F1', npc=1, item='Cơm tấm sườn bì chả ×2', emoji='🍛', pickup='com', dest='office', w=12, real=12, prep=8,
         missing='2 bịch canh rong biển', address='Sảnh lễ tân, Tòa văn phòng Cỏ May', value=14, min_day=1,
         opening='Hai phần cơm tấm cho phòng dự án, cả phòng đang đói meo!',
         note='Anh họp tới 18 giờ, giao sảnh lễ tân giúp anh. Nhớ đủ canh nhé!'),
    dict(_F, key='F2', npc=2, item='Trà sữa khoai môn size L ×3', emoji='🧋', pickup='tra', dest='apt', w=20, real=20, prep=5,
         unit='Phòng 402 — lầu 4', address='Chung cư Mây Xanh (quên ghi số phòng)', value=12, min_day=1,
         opening='Ba ly trà sữa cứu cả nhóm đang chạy deadline 🥲',
         note='Ship lên giúp em nha, cả nhóm đang làm bài không xuống được.'),
    dict(_F, key='F3', npc=5, item='Bún bò giò heo, thêm huyết', emoji='🍜', pickup='bun', dest='vet', w=10, real=10, prep=15,
         missing='bịch rau sống', cod=24, cash=50, address='Quầy tiếp đón, Phòng khám thú y Mèo Mướp', value=10, min_day=2,
         opening='Tô bún bò cho ca trực tối, trả tiền mặt.',
         note='Nước lèo để riêng, nguội là tôi trả lại đấy.'),
    dict(_F, key='F4', npc=3, item='Cháo gà ×2 (ít hành)', emoji='🥣', pickup='com', dest='alley', w=14, real=14, prep=10,
         cod=18, cash=20, address='Nhà số 7, Hẻm Ốc Bươu (cạnh cây khế)', value=9, min_day=1,
         opening='Hai tô cháo gà cho ông nhà đang cảm, bà trả tiền mặt nghe con.',
         note='Bà nấu không nổi, cháu mang giúp bà hai tô cháo nóng.'),
    dict(_F, key='F5', npc=4, item='Cơm gà xối mỡ', emoji='🍗', pickup='com', dest='villa', w=7, real=7, prep=6,
         missing='đũa và muỗng', safe=True, address='Chòi bảo vệ, Nhà vườn Sứ Trắng', value=8, min_day=2,
         opening='Một phần cơm gà, gửi chòi bảo vệ giúp chú.',
         note='Để ở chòi bảo vệ là được, cảm ơn con.'),
    dict(_F, key='F6', npc=0, item='Bún bò đặc biệt, nước riêng', emoji='🍜', pickup='bun', dest='office', w=12, real=12, prep=12,
         address='Tầng trệt, Tòa văn phòng Cỏ May', value=11, min_day=3,
         opening='Tô bún bò đặc biệt cho buổi tăng ca, nước lèo để riêng nha.',
         note='Nước lèo phải còn nóng nha em, chị chụp ảnh review đó.'),
    dict(_P, key='P1', npc=0, item='Bộ chén gốm men lam', emoji='🍵', pickup='hub', dest='villa', w=30, real=30, fragile=True,
         address='Nhà vườn Sứ Trắng, cổng số 2', value=40, min_day=1,
         opening='Bộ chén chị tự tay vẽ, gửi khách quen ở nhà vườn.',
         note='Chén mỏng lắm, bọc kỹ giúp chị nha.'),
    dict(_P, key='P2', npc=2, item='Váy dự tiệc tốt nghiệp', emoji='👗', pickup='hub', dest='apt', w=8, real=8, cod=137, cash=200,
         away=40, unit='Phòng 504 — lầu 5', address='Chung cư Mây Xanh (thiếu số phòng)', value=137, min_day=1,
         opening='Cái váy tối nay em mặc đi tiệc, trả tiền mặt khi nhận nha!',
         note='Gọi em trước khi tới nha, em hay chạy ra tiệm làm tóc.'),
    dict(_P, key='P3', npc=3, item='Thùng mì gói 30 gói', emoji='📦', pickup='hub', dest='alley', w=50, real=80, cod=95, cash=100,
         address='Tạp hóa Bà Út, Hẻm Ốc Bươu', value=95, min_day=1,
         opening='Thùng mì về cho tiệm tạp hóa, bà trả tiền mặt.',
         note='Shop khai 5 ký, cháu cứ cân lại cho đúng.'),
    dict(_P, key='P4', npc=4, item='Phụ tùng máy bơm nước', emoji='⚙️', pickup='hub', dest='villa', w=40, real=40, seam=True, safe=True,
         address='Chòi bảo vệ, Nhà vườn Sứ Trắng', value=60, min_day=1,
         opening='Bộ phụ tùng máy bơm, chú đã trả tiền online.',
         note='Chú ra vườn cả chiều, cứ gửi chòi bảo vệ.'),
    dict(_P, key='P5', npc=5, item='Gương trang điểm có đèn', emoji='🪞', pickup='hub', dest='vet', w=25, real=25, fragile=True,
         cod=58, cash=100, address='Phòng khám thú y Mèo Mướp', value=58, min_day=2,
         opening='Cái gương đèn tôi đặt tuần trước, trả tiền khi nhận.',
         note='Vỡ là tôi không nhận đâu nhé.'),
    dict(_P, key='P6', npc=1, item='Bao phân bón hữu cơ', emoji='🌱', pickup='hub', dest='villa', w=180, real=260,
         address='Nhà vườn Sứ Trắng', value=30, min_day=2,
         opening='Gửi tặng chú Hòa bao phân bón, quà tân gia vườn mới.',
         note='Có 18 ký thôi mà, xe máy chở được hết.'),
    dict(_P, key='P7', npc=1, item='Hồ sơ dự thầu (bản gốc)', emoji='📑', pickup='hub', dest='office', w=10, real=10, paper=True, by=60,
         unit='Phòng kế hoạch — tầng 3', address='Tòa văn phòng Cỏ May (chưa ghi phòng)', value=50, min_day=3,
         opening='Bộ hồ sơ thầu bản gốc, hạn nộp 18 giờ!',
         note='Trễ một phút là mất gói thầu. Giấy tờ gốc, đừng để ướt.'),
    dict(_P, key='P8', npc=0, item='Bình hoa thủy tinh', emoji='🏺', pickup='market', dest='villa', w=20, real=20, fragile=True,
         address='Nhà vườn Sứ Trắng, cổng số 2', value=45, min_day=3,
         opening='Chị đặt bình hoa ở sạp gốm Chợ Chiều, em lấy giúp chị.',
         note='Thủy tinh mỏng, bọc xốp giúp chị nhé.'),
    dict(_P, key='P9', npc=3, item='Sữa chua nếp cẩm ×20 hũ', emoji='🥛', pickup='market', dest='alley', w=40, real=40, cold=True,
         cod=36, cash=50, address='Tạp hóa Bà Út, Hẻm Ốc Bươu', value=36, min_day=2,
         opening='Hai chục hũ sữa chua lấy ở chợ về bán, bà trả tiền mặt.',
         note='Để lạnh giúp bà, chảy là hỏng hết.'),
    dict(_P, key='P10', npc=4, item='Ổ khóa cửa vân tay', emoji='🔐', pickup='hub', dest='villa', w=30, real=30, seam=True,
         cod=120, cash=200, away=45, address='Nhà vườn Sứ Trắng, nhà chính', value=120, min_day=3,
         opening='Ổ khóa vân tay, chú trả tiền mặt khi nhận.',
         note='Chú phải tự ký nhận và trả tiền, đừng gửi bảo vệ nha.'),
    dict(_P, key='P11', npc=5, item='Tủ vải lắp ghép', emoji='🗄️', pickup='hub', dest='apt', w=120, real=120, size='L',
         unit='Phòng 601 — lầu 6', address='Chung cư Mây Xanh (chưa ghi phòng)', value=70, min_day=3,
         opening='Cái tủ vải tôi đặt, đã trả tiền online.',
         note='Mang lên tận phòng giùm, lầu 6 thôi mà.'),
    dict(_P, key='P12', npc=2, item='Son & kem chống nắng', emoji='💄', pickup='hub', dest='apt', w=5, real=5, cod=64, cash=100,
         unit='Phòng 402 — lầu 4', address='Chung cư Mây Xanh (quên ghi phòng)', value=64, min_day=2,
         opening='Đơn son săn sale nè, em trả tiền mặt!',
         note='Em ở nhà cả chiều, gọi là em chạy xuống liền.'),
    dict(_P, key='P13', npc=4, item='Thư bảo đảm', emoji='✉️', pickup='hub', dest='villa', w=2, real=2, paper=True,
         address='Nhà vườn Sứ Trắng, nhà chính', value=20, min_day=2,
         opening='Thư bảo đảm gửi chú Hòa, phải ký nhận tận tay.',
         note='Thư bảo đảm: đúng người nhận ký, không gửi hộ.'),
]
ORDER_INDEX = {o['key']: o for o in ORDERS}

# --- v0.5 ------------------------------------------------------------------------
GEN = 2
TYRE_FLAT_AT = 40         # below this tyre level a leg may end with a flat
SERVICE_COST = 10         # tune-up at the petrol station: new inner tube, oil, chain
RIM_COST = 10             # extra when the rim was ridden flat
STREAK_EVERY = 3
STREAK_BONUS = 5
RATING_KEEP = 10
TOP_RATING = 47           # tenths of a star: 4.7★ over the last orders
TOP_MIN = 5               # rated orders needed before the priority bonus counts
TOP_BONUS = 2
REDIRECT_FEE = 4
DISCOUNT = 10             # what "bớt cho khách chịu nhận" costs the courier
SOUP = ('F3', 'F4', 'F6')                 # orders with broth that spills on a bumpy alley
DOG_NODES = ('villa', 'alley')
MOVE_TO = {'apt': ('office', 'tra'), 'office': ('apt', 'market'), 'villa': ('vet', 'apt'), 'alley': ('com', 'market'),
           'vet': ('villa', 'apt')}
WORKS = ('apt', 'office', 'vet', 'villa', 'com', 'bun', 'tra')
MODS = [
    dict(id='normal', emoji='🌤️', name='Chiều êm', text='Đường thông thoáng, đơn đều tay.', weight=3),
    dict(id='school', emoji='🏫', name='Tan trường sớm', weight=2, min_day=2,
         text='17:00–17:40 quanh Trường Bồ Câu kẹt cứng: đường chính chậm gấp đôi. Hẻm tắt vẫn lách được.'),
    dict(id='market', emoji='🧺', name='Chợ phiên', weight=2, min_day=2,
         text='17:20–18:20 quanh Chợ Chiều đông nghẹt: đường chính chậm gấp đôi.'),
    dict(id='works', emoji='🚧', name='Đào đường', weight=2, min_day=3,
         text='Đường chính vào {node} đang đào cống: đi vòng thêm 2 ô phố. Hẻm tắt thì không vướng.'),
    dict(id='sale', emoji='🛍️', name='Ngày săn sale', weight=2, min_day=3,
         text='Sàn giảm giá lớn: nhiều đơn thu hộ, coi chừng khách “bom hàng”.'),
]
RAINY = dict(id='rain', emoji='🌧️', name='Mưa dầm', text='Đường trơn, chạy chậm. Nhớ túi chống nước cho hàng.')
STORM = dict(id='storm', emoji='⛈️', name='Mưa to, ngập hẻm',
             text='{flood} ngập: đường chính lội chậm thêm 3 phút, chạy hẻm tắt vào đó là chết máy.')
MOD_INDEX = {m['id']: m for m in MODS + [RAINY, STORM]}
WAYS = ('main', 'short')

# --- care (sub-project 3) -------------------------------------------------------
PARTS = ('tyre', 'brake', 'oil', 'chain', 'coat')
PART_INFO = {
    'tyre': dict(name='Lốp & ruột', emoji='🛞', price=SERVICE_COST, low=TYRE_FLAT_AT,
                 effect=f'Dưới {TYRE_FLAT_AT}% dễ xẹp bánh giữa đường.'),
    'brake': dict(name='Má phanh', emoji='🛑', price=8, low=30, effect='Dưới 30%: không được chạy hẻm tắt (dốc, cua gắt).'),
    'oil': dict(name='Nhớt máy', emoji='🛢️', price=6, low=30, effect='Dưới 30%: máy nóng, mỗi chặng hao thêm 1% xăng.'),
    'chain': dict(name='Sên xe', emoji='⛓️', price=6, low=30, effect='Dưới 30%: xe ì, mỗi chặng chậm 1 phút. Về 0% là tuột sên.'),
    'coat': dict(name='Áo mưa', emoji='🧥', price=8, low=30, effect='Dưới 30%: ngày mưa mỗi chặng chậm 1 phút vì ướt lạnh.'),
}
FIX_MIN = 3               # minutes per part at the garage
CARE_KINDS = {'carry': dict(minutes=3, label='Xách vào tận nơi', emoji='🤲'),
              'photo': dict(minutes=1, label='Chụp ảnh gửi khách', emoji='📸'),
              'check': dict(minutes=2, label='Đồng kiểm trước mặt khách', emoji='🔍')}
NOTE_KINDS = ('call', 'gate') + tuple(CARE_KINDS)
NOTE_AT = (1, 3)          # a customer tells you note 1 after the 1st delivery, note 2 after the 3rd
BOND_MAX = 10
BOND_TIP = ((6, 4, 'khách ruột'), (3, 2, 'khách quen'))
AREA_SMOOTH = 2           # jobs at a stop before its alley shortcut is smooth
AREA_LOCAL = 5            # … before the locals' cut saves one more block
REGULARS = {
    0: [dict(id='man-photo', kind='photo', text='Chụp ảnh kiện hàng lúc giao gửi chị — chị báo khách yên tâm.'),
        dict(id='man-call', kind='call', text='Gọi trước khi tới để người nhận ra lấy, khách của chị hay đi vắng.')],
    1: [dict(id='tung-call', kind='call', text='Gọi trước 5 phút để anh xuống sảnh — anh ghét phải chờ.'),
        dict(id='tung-photo', kind='photo', text='Chụp ảnh lúc gửi lễ tân, anh cần làm bằng chứng với sếp.')],
    2: [dict(id='vy-call', kind='call', text='Gọi trước khi tới — Vy hay chạy ra tiệm làm tóc.'),
        dict(id='vy-carry', kind='carry', text='Mang lên tận cửa phòng giúp — cả nhóm đang chạy deadline.')],
    3: [dict(id='ut-carry', kind='carry', text='Bà lớn tuổi, lưng yếu: xách hàng vào tận trong tiệm giúp bà.'),
        dict(id='ut-call', kind='call', text='Gọi bà ra mở cửa, bà nghe chuông không rõ.')],
    4: [dict(id='hoa-call', kind='call', text='Chú nghe máy chậm — gọi trước để chú ra cổng.'),
        dict(id='hoa-gate', kind='gate', text='Mã cổng phụ 1975: đi cổng phụ là tránh được con chó vện ở cổng trước.')],
    5: [dict(id='le-check', kind='check', text='Mở hộp đồng kiểm ngay trước mặt cô, cô mới yên tâm ký nhận.'),
        dict(id='le-call', kind='call', text='Gọi trước khi tới, cô đang khám thì cần vài phút mới ra được.')],
}
NOTE_INDEX = {x['id']: dict(x, who=i) for i, rows in REGULARS.items() for x in rows}
REGULAR_IDS = tuple(kit.npc_id(ID, i) for i in REGULARS)


# --- small helpers --------------------------------------------------------------
def weather(day: int) -> str:
    return 'rain' if day % 3 == 0 else 'sun'


def dist(a: str, b: str) -> int:
    return abs(NODES[a]['x'] - NODES[b]['x']) + abs(NODES[a]['y'] - NODES[b]['y'])


def hm(minute: int) -> str:
    total = 17 * 60 + int(minute)
    return f'{(total // 60) % 24:02d}:{total % 60:02d}'


def kg(w: int) -> str:
    return f'{w / 10:g}'.replace('.', ',') + ' kg'


def _window(o: dict, day: int) -> int:
    """Promised minutes for a food order: fair from the hub, tight if you dawdle."""
    mpu = MPU[weather(day)]
    need = max(o['prep'], dist('hub', o['pickup']) * mpu) + dist(o['pickup'], o['dest']) * mpu + 4 + STAIRS.get(o['dest'], 0) + 10
    return -(-need // 5) * 5


RUN_V2 = dict(dog=None, dest=None, spilled=False, discount=0, bomb=None, moved=None)
RUN_V3 = dict(care=[], kept=[], missed=[])      # care at the door; regulars' notes kept / forgotten
# Cash at the door (game/careers/till.py): times a careful customer asked for the rest of the change,
# excess change given back, change the customer waved off as a tip.
RUN_V4 = dict(asked=0, returned=False, tip=0)


def _empty_run() -> dict:
    return dict(day=0, t0=0, checked=False, w=None, seam=None, missing=None, packed=[], loaded=False, reported=False,
                called=False, unit=None, back=None, knocks=0, wet=False, burst=False, melted=False, _broken=False,
                broken_seen=False, change=None, short=0, over=0, outcome=None, fee=None, late=0, expired=False, comp=0,
                **copy.deepcopy(RUN_V2), **copy.deepcopy(RUN_V3), **RUN_V4)


def mod_of(day: int) -> dict:
    """Road conditions of the day, on top of the fixed sun/rain rhythm."""
    if weather(day) == 'rain':
        return STORM if day >= 3 and kit.rng(ID, 'storm', day).random() < 0.3 + 0.1 * kit.tier(day) else RAINY
    return kit.daily(ID, day, MODS)


def hazards(day: int) -> dict:
    m = mod_of(day)['id']
    h = dict(jams=[], works=None, flood=[])
    if m == 'school':
        h['jams'].append(dict(node='school', start=0, end=40))
    elif m == 'market':
        h['jams'].append(dict(node='market', start=20, end=80))
    elif m == 'works':
        h['works'] = WORKS[kit.rng(ID, 'works', day).randrange(len(WORKS))]
    elif m == 'storm':
        h['flood'] = ['alley'] + (['villa'] if kit.tier(day) >= 2 else [])
    return h


def _today(c: dict) -> dict:
    return kit.data(c).get('today') or dict(day=0, mod='normal')


def _live_hazards(c: dict) -> dict:
    """Hazards only count on a shift opened under v0.5 (old saves finish their day as before)."""
    if _today(c).get('day') != c['day']:
        return dict(jams=[], works=None, flood=[])
    return hazards(c['day'])


def _mod_text(day: int) -> str:
    m, h = mod_of(day), hazards(day)
    if m['id'] == 'works':
        return m['text'].format(node=NODES[h['works']]['name'])
    if m['id'] == 'storm':
        return m['text'].format(flood=' và '.join(NODES[x]['name'] for x in h['flood']))
    return m['text']


def _leg(c: dict, a: str, b: str, clock: int, way: str = 'main') -> dict:
    """One ride between two stops: blocks, minutes, fuel, tyre wear and what happens on it."""
    wx = weather(c['day'])
    h = _live_hazards(c)
    base = dist(a, b)
    touch = (a, b)
    notes = []
    raw = kit.data(c)
    know = (raw.get('areas') or {}).get(b, 0)
    smooth = way == 'short' and know >= AREA_SMOOTH
    local = way == 'short' and know >= AREA_LOCAL and base >= 3
    if way == 'short':
        blocks = max(1, base - (2 if local else 1))
        if local:
            notes.append('🗺️ lối tắt dân địa phương')
        elif smooth:
            notes.append('🗺️ thuộc hẻm, chạy êm')
    else:
        blocks = base
        if h['works'] in touch:
            blocks += 2
            notes.append('🚧 đi vòng công trình +2 ô')
    minutes = blocks * MPU[wx]
    if way == 'main':
        for j in h['jams']:
            if j['node'] in touch and j['start'] <= clock < j['end']:
                minutes += blocks * MPU[wx]
                notes.append(f'🚦 kẹt xe quanh {NODES[j["node"]]["name"]}')
                break
    stall = False
    if any(x in touch for x in h['flood']):
        if way == 'short':
            stall = True
            minutes += 15
            notes.append('🌊 hẻm ngập, xe chết máy')
        else:
            minutes += 3
            notes.append('🌊 lội nước chậm')
    fuel = blocks * FUEL_RATE[wx] + (8 if stall else 0)
    wear = blocks * (2 if way == 'short' and not smooth else 1) + (1 if wx == 'rain' else 0)
    # A neglected scooter: each worn part costs a little on every leg until it is fixed.
    parts = raw.get('parts') or {}
    if parts.get('oil', 100) < PART_INFO['oil']['low']:
        fuel += 1
        notes.append('🛢️ nhớt cạn +1% xăng')
    if parts.get('chain', 100) < PART_INFO['chain']['low']:
        minutes += 1
        notes.append('⛓️ sên chùng +1 phút')
    if wx == 'rain' and parts.get('coat', 100) < PART_INFO['coat']['low']:
        minutes += 1
        notes.append('🧥 áo mưa rách +1 phút')
    return dict(node=b, way=way, blocks=blocks, minutes=minutes, fuel=fuel, wear=wear, stall=stall, notes=notes,
                smooth=smooth, local=local)


def _dest(t: dict) -> str:
    return t['run'].get('dest') or t['needs']['dest']


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        return _make_v1(day, slot, serial)
    return _make_v2(day, slot, serial)


def _make_v1(day: int, slot: int, serial: int) -> dict:
    pool = [o for o in ORDERS if o['min_day'] <= day]
    order = list(pool)
    kit.rng(ID, day, slot // len(pool)).shuffle(order)
    o = order[slot % len(order)]
    needs = dict(kind=o['kind'], order=o['key'], item=o['item'], emoji=o['emoji'], pickup=o['pickup'], dest=o['dest'],
                 address=o['address'], w=o['w'], size=o['size'], fragile=o['fragile'], cold=o['cold'], paper=o['paper'],
                 cod=o['cod'], cash=o['cash'], safe_drop=o['safe'], by=o['by'], prep=o['prep'],
                 window=_window(o, day) if o['kind'] == 'food' else None, value=o['value'], note=o['note'],
                 unit_missing=bool(o['unit']))
    title = f'{o["emoji"]} {NODES[o["pickup"]]["name"]} → {NODES[o["dest"]]["name"]}'
    run = _empty_run()
    run['day'] = day
    return kit.base_task(ID, day, slot, serial, o['npc'], title, o['opening'], needs=needs, run=run,
                         _w=o['real'], _seam=o['seam'], _unit=o['unit'], _away=o['away'], _missing=o['missing'],
                         _value=o['value'])


def _make_v2(day: int, slot: int, serial: int) -> dict:
    t = _make_v1(day, slot, serial)
    o = ORDER_INDEX[t['needs']['order']]
    m = mod_of(day)['id']
    n = t['needs']
    if o['kind'] == 'food':
        slack = 5 if m in ('school', 'market', 'works', 'storm') else 0
        n['window'] = _window(o, day) + slack
        n['soup'] = o['key'] in SOUP
    else:
        n['soup'] = False
    rng = kit.rng(ID, 'v2', day, slot)
    tier = kit.tier(day)
    roll = rng.random()
    dog = 0.25 + 0.05 * tier if day >= 3 and o['dest'] in DOG_NODES else 0
    bomb = (0.4 if m == 'sale' else 0.1 + 0.04 * tier) if day >= 3 and o['cod'] and o['kind'] == 'parcel' else 0
    moved = 0.07 + 0.02 * tier if day >= 4 and not o['paper'] and o['dest'] in MOVE_TO else 0
    t['_dog'] = roll < dog
    t['_bomb'] = dog <= roll < dog + bomb
    t['_moved'] = MOVE_TO[o['dest']][rng.randrange(2)] if dog + bomb <= roll < dog + bomb + moved else None
    t['gen'] = GEN
    return t


FIXED = ('needs', '_w', '_seam', '_unit', '_away', '_missing', '_dog', '_bomb', '_moved')


STAT_KEYS = ('flats', 'services', 'shortcuts', 'stalls', 'bombs', 'dogs', 'moved', 'streak_bonus', 'quest_bonus', 'top_bonus',
             'repairs', 'chains', 'cares', 'gates', 'regular_tips')


def initial() -> dict:
    return _extend(dict(at='hub', clock=0, fuel=START_FUEL, bag=0, owed=0, cod=[], route=[], km=0,
                        delivered=0, failed=0, refused=0, settled=0, shortage=0,
                        day_delivered=0, day_failed=0, day_refused=0, day_km=0, day_fees=0))


def _extend(d: dict) -> dict:
    """v0.5 keys, added to old saves with setdefault."""
    d.setdefault('desk', kit.desk_initial())
    d.setdefault('today', dict(day=0, mod='normal'))
    d.setdefault('tyre', 100)
    d.setdefault('streak', 0)
    d.setdefault('best', 0)
    d.setdefault('stars', [])
    d.setdefault('quest', dict(day=0, goal=0, done=0, paid=False, bonus=0))
    stats = d.setdefault('stats', {})
    for k in STAT_KEYS:
        stats.setdefault(k, 0)
    # care (sub-project 3): parts other than the tyre, regulars' notes cards, known stops
    parts = d.setdefault('parts', {})
    for k in PARTS[1:]:
        parts.setdefault(k, 100)
    d.setdefault('regulars', {})
    d.setdefault('areas', {})
    return d


def _data(c: dict) -> dict:
    return _extend(kit.data(c))


# --- care helpers -------------------------------------------------------------------
def part(d: dict, k: str) -> int:
    return d['tyre'] if k == 'tyre' else d['parts'][k]


def _set_part(d: dict, k: str, v: int) -> None:
    v = max(0, min(100, int(v)))
    if k == 'tyre':
        d['tyre'] = v
    else:
        d['parts'][k] = v


def _wear(c: dict, d: dict, leg: dict, km_before: int) -> list[str]:
    """Parts other than the tyre wear with the odometer and the rain (exact, no dice).
    Returns warnings for parts that just dropped below their line."""
    rain = weather(c['day']) == 'rain'
    km = km_before + leg['blocks']
    before = {k: part(d, k) for k in PARTS[1:]}
    p = d['parts']
    p['brake'] = max(0, p['brake'] - (km // 4 - km_before // 4) - (1 if rain else 0))
    p['oil'] = max(0, p['oil'] - (km // 3 - km_before // 3))
    p['chain'] = max(0, p['chain'] - (km // 2 - km_before // 2) - (1 if rain else 0))
    if rain:
        p['coat'] = max(0, p['coat'] - 3)
    out = []
    for k in PARTS[1:]:
        low = PART_INFO[k]['low']
        if before[k] >= low > p[k]:
            out.append(f'{PART_INFO[k]["emoji"]} {PART_INFO[k]["name"]} còn {p[k]}% — {PART_INFO[k]["effect"].split(": ", 1)[-1]}')
    return out


def _npc_index(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


def _regular(d: dict, t: dict) -> dict | None:
    if _npc_index(t) not in REGULARS:
        return None
    return d['regulars'].setdefault(t['npc'], dict(visits=0, bond=0, notes=[]))


def _known_notes(d: dict, t: dict) -> list[dict]:
    reg = d['regulars'].get(t['npc'])
    return [NOTE_INDEX[x] for x in reg['notes']] if reg else []


def _note_kept(t: dict, note: dict) -> bool:
    r = t['run']
    if note['kind'] == 'call':
        return r['called']
    if note['kind'] == 'gate':
        return True
    return note['kind'] in r['care']


def _care_record(c: dict, t: dict) -> None:
    """At the hand-over: which of the customer's known wishes were kept (before the review is written)."""
    d = _data(c)
    notes = [x for x in _known_notes(d, t) if x['kind'] != 'gate']
    t['run']['kept'] = [x['id'] for x in notes if _note_kept(t, x)]
    t['run']['missed'] = [x['id'] for x in notes if not _note_kept(t, x)]


def _care_after(s: dict, c: dict, t: dict, clean: bool) -> str:
    """After a successful hand-over: the regular remembers you (bond, thank-you, a new note)."""
    d = _data(c)
    reg = _regular(d, t)
    if reg is None:
        return ''
    who, r = _who(t), t['run']
    reg['visits'] += 1
    out = ''
    good = clean and not r['missed']
    if r['missed']:
        out += f' 📒 {who} hơi buồn: bạn quên lời dặn “{NOTE_INDEX[r["missed"][0]]["text"]}”'
    elif good and reg['bond'] < BOND_MAX:
        reg['bond'] += 1
        out += f' 💛 {who} quý bạn hơn (thân thiết {reg["bond"]}/{BOND_MAX}).'
    if good and not t.get('tip_given'):      # a regular who already left the change does not tip twice
        for at, amount, label in BOND_TIP:
            if reg['bond'] >= at:
                kit.money(s, c, amount, f'{who} ({label}) gửi tiền cà phê', t['id'], 'tip')
                t['tip_given'] = t.get('tip_given', 0) + amount     # one tip per job: the random tip skips it
                d['stats']['regular_tips'] += amount
                out += f' ☕ {who} ({label}) gửi {amount} xu tiền cà phê.'
                break
    rows = REGULARS[_npc_index(t)]
    for k, at in enumerate(NOTE_AT):
        if k < len(rows) and reg['visits'] >= at and rows[k]['id'] not in reg['notes']:
            reg['notes'].append(rows[k]['id'])
            out += f' 📒 {who} dặn: “{rows[k]["text"]}” — đã ghi vào sổ tay khách quen.'
    return out


def _bond_hurt(c: dict, t: dict) -> str:
    reg = _regular(_data(c), t)
    if not reg or not reg['bond']:
        return ''
    reg['bond'] -= 1
    return f' 💔 {_who(t)} bớt tin bạn (thân thiết {reg["bond"]}/{BOND_MAX}).'


def _area(d: dict, node: str) -> str:
    n = d['areas'][node] = min(10**6, d['areas'].get(node, 0) + 1)
    name = NODES[node]['name']
    if n == AREA_SMOOTH:
        return f' 🗺️ Đã thuộc hẻm quanh {name}: hẻm tắt vào đây chạy êm, không xóc đổ, không mòn lốp thêm.'
    if n == AREA_LOCAL:
        return f' 🗺️ Biết lối tắt của dân quanh {name}: hẻm tắt vào đây bớt thêm 1 ô (quãng từ 3 ô).'
    return ''


def _gate(c: dict, d: dict, t: dict) -> str:
    """Chú Hòa's side-gate code: the dog at the main gate no longer blocks you."""
    r = t['run']
    if not (t.get('_dog') and r['dog'] is None and r['loaded'] and d['at'] == _dest(t) == 'villa'
            and not r['expired'] and not r['broken_seen']):
        return ''
    due = _due(t)
    if t['needs']['kind'] == 'food' and d['clock'] > due + GRACE:
        return ''
    if not any(x['kind'] == 'gate' for x in _known_notes(d, t)):
        return ''
    r['dog'] = 'ok'
    d['stats']['gates'] += 1
    return '🔢 Bấm mã cổng phụ theo sổ tay — con chó vện ở cổng trước chỉ sủa vọng theo. '


def _forecast(raw: dict, d: dict) -> dict:
    """The next shift's weather and road board (both fixed per day) with advice from the courier's own state."""
    day = raw['day'] + (1 if raw.get('open') else 0)
    wx, m, h = weather(day), mod_of(day), hazards(day)
    advice = []
    if wx == 'rain':
        want = _goal(day)[0] + 1
        have = kit.stock(raw, 'rainbag')
        advice.append(f'🛍️ Túi chống nước: kho còn {have}, ca mưa nên có ít nhất {want}' +
                      (' — đặt thêm ngay hôm nay cho kịp hàng về.' if have < want else ' — đủ dùng.'))
        if d['parts']['coat'] < 50:
            advice.append(f'🧥 Áo mưa còn {d["parts"]["coat"]}% — thay ở tiệm Chú Bảy trước khi mưa.')
        if d['parts']['brake'] < 50:
            advice.append(f'🛑 Đường trơn mà má phanh còn {d["parts"]["brake"]}% — nên thay sớm.')
    if h['flood']:
        advice.append('🌊 Hẻm ngập ở ' + ' và '.join(NODES[x]['name'] for x in h['flood']) + ': đừng chạy hẻm tắt vào đó.')
    if h['works']:
        advice.append(f'🚧 Đào đường trước {NODES[h["works"]]["name"]}: đường chính vòng thêm 2 ô, hẻm tắt thì không vướng.')
    for j in h['jams']:
        advice.append(f'🚦 {NODES[j["node"]]["name"]} kẹt {hm(j["start"])}–{hm(j["end"])}: tránh giờ đó hoặc đi hẻm.')
    if m['id'] == 'sale':
        advice.append(f'💵 Ngày săn sale: nhiều đơn thu hộ — nộp COD sớm, đừng để túi chạm {COD_CAP} xu.')
    if d['tyre'] < 50:
        advice.append(f'🛞 Lốp còn {d["tyre"]}% — thay ruột ở cây xăng hoặc tiệm Chú Bảy.')
    for k in ('oil', 'chain'):
        if d['parts'][k] < 40:
            advice.append(f'{PART_INFO[k]["emoji"]} {PART_INFO[k]["name"]} còn {d["parts"][k]}% — ghé tiệm Chú Bảy.')
    if not advice:
        advice.append('✅ Xe ổn, đường êm — cứ thế mà chạy.')
    return dict(day=day, label='Ngày mai' if raw.get('open') else 'Ca tới', weather=wx, id=m['id'], emoji=m['emoji'],
                name=m['name'], text=_mod_text(day), advice=advice)


def _goal(day: int) -> tuple[int, int]:
    tier = kit.tier(day)
    goal = 3 + (1 if tier >= 1 else 0) + (1 if tier >= 3 else 0)
    bonus = 10 + 5 * tier + (5 if weather(day) == 'rain' else 0)
    return goal, bonus


def rating(d: dict) -> int | None:
    """Average of the last rated orders in tenths of a star (None until there are a few)."""
    stars = d.get('stars') or []
    return round(sum(stars) * 10 / len(stars)) if len(stars) >= TOP_MIN else None


def _due(t: dict) -> int | None:
    n = t['needs']
    if n['kind'] == 'food':
        return t['run']['t0'] + n['window']
    if n['by']:
        return t['run']['t0'] + n['by']
    return None


def _ready(t: dict) -> int:
    return t['run']['t0'] + t['needs']['prep']


def _open(c: dict) -> list[dict]:
    return [t for t in c['tasks'] if t['career'] == ID and t['status'] not in DONE]


def _load(c: dict) -> int:
    return sum(t['_w'] for t in _open(c) if t['run']['loaded'])


def _ruined(t: dict) -> bool:
    return t['run']['_broken']


def _needs_pack(t: dict, day: int) -> list[str]:
    n = t['needs']
    if n['kind'] != 'parcel':
        return []
    rows = []
    if n['fragile']:
        rows.append('bubble')
    if t['run']['seam']:
        rows.append('tape')
    if weather(day) == 'rain':
        rows.append('rainbag')
    if n['cold']:
        rows.append('coldpack')
    if n['size'] == 'L':
        rows.append('strap')
    return rows


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    # Day 1 is forgiving: an order's clock (cooking, promised time, customer out) starts when the
    # courier accepts it, so a new player who takes the orders one by one is never cancelled for it.
    if c['day'] <= 1 and not t['known'] and not t['run']['loaded']:
        t['run']['t0'] = max(t['run']['t0'], kit.data(c)['clock'])
    parts = [f'Lấy tại {NODES[n["pickup"]]["name"]} → giao {n["address"]}', f'{n["item"]} (khai {kg(n["w"])})']
    parts.append(f'Thu hộ COD {n["cod"]} xu — khách chuẩn bị tờ {n["cash"]} xu' if n['cod'] else 'Đã thanh toán online')
    tags = [x for x, on in (('dễ vỡ', n['fragile']), ('giữ lạnh', n['cold']), ('giấy tờ gốc', n['paper']),
                            ('hàng cồng kềnh', n['size'] == 'L'), ('có nước lèo — tránh hẻm xóc', n.get('soup'))) if on]
    if tags:
        parts.append('Lưu ý: ' + ', '.join(tags))
    if n['kind'] == 'food':
        parts.append(f'Quán báo xong món lúc {hm(_ready(t))}, hẹn khách trước {hm(_due(t))}')
    elif n['by']:
        parts.append(f'Phải tới trước {hm(_due(t))}')
    if n['safe_drop']:
        parts.append('Khách cho phép gửi bảo vệ')
    return ' · '.join(parts) + '. “' + n['note'] + '”'


# --- actions --------------------------------------------------------------------
def _clock(d: dict, minutes: int) -> None:
    d['clock'] = min(1999, d['clock'] + minutes)


def _order(c: dict, p: dict) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Đơn này không thuộc Giao Nhanh Mây Chiều.')
    kit.need(t['known'], 'Nhận đơn trên app trước (bấm “Nhận đơn”) để xem địa chỉ và yêu cầu.')
    return t


def _at(d: dict, node: str, what: str) -> None:
    kit.need(d['at'] == node, f'Bạn đang ở {NODES[d["at"]]["name"]}. {what} ở {NODES[node]["name"]} — lên lộ trình và chạy tới đó.')


def _fee(c: dict, t: dict) -> int:
    n, r = t['needs'], t['run']
    fee = (8 if n['kind'] == 'food' else 10) + 2 * dist(n['pickup'], n['dest'])
    if weather(c['day']) == 'rain':
        fee += 5
    if r['reported']:
        fee += 3
    if n['fragile']:
        fee += 2
    if r['late'] > 0:
        fee -= LATE_FEE
    if r.get('moved') == 'accept':
        fee += REDIRECT_FEE
    if t.get('gen') and (rating(kit.data(c)) or 0) >= TOP_RATING:
        fee += TOP_BONUS
    return max(4, fee)


def _condition_notes(t: dict) -> list[str]:
    r, n = t['run'], t['needs']
    out = []
    if r['wet']:
        out.append('thùng hàng ướt nhẹp')
    if r['burst']:
        out.append('mép thùng bung keo, hàng suýt rơi')
    if r['melted']:
        out.append('sữa chua chảy nước vì không giữ lạnh')
    if n['kind'] == 'food' and t['_missing'] and r['missing'] is None:
        out.append(f'thiếu {t["_missing"]} (chưa kiểm món ở quán)')
    if r.get('spilled'):
        out.append('nước lèo đổ ra túi' if n.get('soup') else 'túi đồ ăn móp méo, đổ tháo')
    return out


def _slips(t: dict) -> None:
    """What the customer finds at the door, in their own words (recorded at the hand-over only)."""
    r, n = t['run'], t['needs']
    if r.get('spilled'):
        cq.slip(t, 'spilled', 2, 'Nước lèo đổ ra hết túi, tới nơi còn chưa được nửa tô.' if n.get('soup') else 'Túi đồ ăn móp méo, đổ tháo hết cả ra.',
                'nước lèo đổ ra túi' if n.get('soup') else 'đồ ăn đổ tháo')
    if n['kind'] == 'food' and t['_missing'] and r['missing'] is None:
        cq.slip(t, 'missing', 2, f'Thiếu {t["_missing"]}, shipper không kiểm túi ở quán.', f'thiếu {t["_missing"]}')
    if r['melted']:
        cq.slip(t, 'melted', 2, 'Hàng cần giữ lạnh mà tới nơi đã chảy nước hết.', 'hàng giữ lạnh bị chảy')
    if r['wet']:
        cq.slip(t, 'wet', 1, 'Thùng hàng ướt nhẹp, không bọc túi chống nước gì hết.', 'thùng hàng bị ướt')
    if r['burst']:
        cq.slip(t, 'burst', 1, 'Thùng bung mép keo, hàng suýt rơi ra ngoài.', 'thùng bung keo')
    if r['late']:
        food = n['kind'] == 'food'
        cq.slip(t, 'late', 1 if r['late'] <= 15 else 2,
                f'Hẹn giờ mà trễ {r["late"]} phút, đồ ăn nguội hết.' if food else f'Dặn giao trước giờ hẹn mà trễ {r["late"]} phút.',
                f'trễ {r["late"]} phút')


def _finish(s: dict, c: dict, t: dict, how: str) -> dict:
    d = kit.data(c)
    r, n = t['run'], t['needs']
    notes = _condition_notes(t)
    t['mistakes'] += len(notes)
    due = _due(t)
    r['late'] = max(0, d['clock'] - due) if due is not None else 0
    r['outcome'] = how
    fee = _fee(c, t)
    late, r['late'] = r['late'], 0
    base = _fee(c, t)            # the fee before the app's flat late deduction
    r['late'] = late
    _care_record(c, t)
    _slips(t)
    react = cq.react(s, c, t, base, who=_who(t))
    # A customer who complains takes their cut instead of the flat late deduction, never both.
    fee = react['pay'] if react['cut'] else fee
    r['fee'] = fee
    cash = ''
    if n['cod'] and r['asked']:
        till.asked_slip(t)
    if n['cod'] and r['short'] and r['outcome'] == 'delivered':
        cash = till.found_at_home(s, c, t, r['short'])
    elif n['cod'] and r['change'] == n['cash'] - n['cod'] + r['discount'] and not r['over']:
        r['tip'], cash = till.keep_change(s, c, t, r['change'], react, _who(t))
        if r['tip']:
            r['change'] = 0          # the change stays in the courier's pocket as the tip
    d['delivered'] += 1
    d['day_delivered'] += 1
    d['day_fees'] += fee
    kit.metric(c, 'deliveries_done')
    if not notes and not r['late']:
        kit.metric(c, 'deliveries_clean')
    _clock(d, 1)
    where = 'gửi chòi bảo vệ, chụp ảnh làm bằng chứng' if how == 'safedrop' else 'giao tận tay'
    kit.complete(s, c, t, fee, f'Đã {where}: {n["item"]} tới {_where(t)}.')
    msg = f'{"📸 Đã gửi bảo vệ và chụp ảnh" if how == "safedrop" else "✅ Giao thành công"} lúc {hm(d["clock"])} · phí ship +{fee} xu.'
    if r['late']:
        msg += f' Trễ {r["late"]} phút so với hẹn' + ('.' if react['cut'] else f' (−{LATE_FEE} xu).')
    if notes:
        msg += ' Khách phàn nàn: ' + '; '.join(notes) + '.'
    if react['message']:
        msg += ' ' + react['message']
    if cash:
        msg += ' ' + cash
    clean = not notes and not r['late'] and not cq.slips(t)
    msg += _score(s, c, t, clean=clean)
    msg += _care_after(s, c, t, clean)
    msg += _area(_data(c), _dest(t))
    if d['owed'] and d['at'] != 'hub':
        msg += f' Túi COD đang giữ {d["owed"]} xu của bưu cục.'
    return dict(message=msg, celebrate=not notes and not r['late'])


def _where(t: dict) -> str:
    return NODES[_dest(t)]['name'] if t['run'].get('dest') else t['needs']['address']


def _stars(c: dict, t: dict) -> int:
    fb = feedback(c, t)
    scores = [x['score'] for x in fb['criteria']] or [3]
    return max(1, min(fb.get('cap', 5), cq.star_cap(t), round(sum(scores) / len(scores))))


def _score(s: dict, c: dict, t: dict, clean: bool | None) -> str:
    """Courier score after an order ends: stars, clean streak, daily target (v0.5 orders)."""
    if not t.get('gen'):
        return ''
    d = _data(c)
    d['stars'] = ar.last(d['stars'] + [_stars(c, t)], RATING_KEEP, 'delivery.stars', c)
    out = ''
    if clean:
        d['streak'] += 1
        d['best'] = max(d['best'], d['streak'])
        if d['streak'] % STREAK_EVERY == 0:
            kit.money(s, c, STREAK_BONUS, f'Thưởng chuỗi {d["streak"]} đơn sạch', t['id'], 'revenue')
            d['stats']['streak_bonus'] += STREAK_BONUS
            out += f' 🔥 Chuỗi {d["streak"]} đơn sạch: +{STREAK_BONUS} xu.'
    elif clean is False or clean is None:
        if d['streak']:
            out += f' Chuỗi {d["streak"]} đơn sạch dừng lại.'
        d['streak'] = 0
    q = d['quest']
    if clean is not None and q['day'] == c['day'] and t['run']['outcome'] in ('delivered', 'safedrop'):
        q['done'] += 1
        if q['done'] >= q['goal'] and not q['paid']:
            q['paid'] = True
            kit.money(s, c, q['bonus'], f'Thưởng mốc ca: giao đủ {q["goal"]} đơn', t['id'], 'revenue')
            d['stats']['quest_bonus'] += q['bonus']
            out += f' 🎯 Đạt mốc {q["goal"]} đơn trong ca: +{q["bonus"]} xu.'
    return out


def _ride_effects(c: dict, blocks: int, leg: dict | None = None) -> list[str]:
    if blocks <= 0:
        return []
    rain = weather(c['day']) == 'rain'
    out = []
    for t in _open(c):
        r, n = t['run'], t['needs']
        if (leg and leg['way'] == 'short' and not leg.get('smooth') and r['loaded'] and n['kind'] == 'food'
                and n.get('soup') and not r['spilled']):
            r['spilled'] = True
            out.append(f'hẻm xóc làm đổ nước lèo của {n["item"].lower()}')
        if leg and leg['stall'] and r['loaded'] and n['kind'] == 'parcel' and 'rainbag' not in r['packed'] and not r['wet']:
            r['wet'] = True
            if n['paper']:
                r['_broken'] = True
            out.append(f'{n["item"]} ngấm nước khi dắt xe qua hẻm ngập')
        if not r['loaded'] or n['kind'] != 'parcel':
            continue
        if n['fragile'] and 'bubble' not in r['packed']:
            r['_broken'] = True
        if rain and 'rainbag' not in r['packed'] and not r['wet']:
            r['wet'] = True
            if n['paper']:
                r['_broken'] = True
            out.append(f'{n["item"]} bị mưa tạt ướt')
        if t['_seam'] and 'tape' not in r['packed'] and not r['burst']:
            r['burst'] = True
            out.append(f'thùng {n["item"].lower()} bung mép keo')
        if n['cold'] and 'coldpack' not in r['packed'] and not r['melted']:
            r['melted'] = True
            out.append(f'{n["item"].lower()} bắt đầu chảy nước')
    return out


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'dl_decide':
        return _decide(s, c, p)
    if name != 'dl_plan':
        kit.desk_block(d['desk'], 'Có chuyện dọc đường — quyết xong rồi chạy tiếp nhé.')
    out = _handle(s, c, name, p)
    if name != 'dl_plan':
        before = d['desk']['ev']
        kit.desk_tick(s, c, ID, d['desk'], EVENTS, _mod_id(c))
        ev = d['desk']['ev']
        if ev is not None and ev is not before:
            x = kit.desk_script(EVENTS, ev['script'])
            out['message'] = (out.get('message') or '') + f' {x["emoji"]} {x["title"]}!'
    return out


def _mod_id(c: dict) -> str | None:
    return _today(c).get('mod') if _today(c).get('day') == c['day'] else None


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    wx = weather(c['day'])
    if name == 'dl_plan':
        route = p.get('route')
        kit.need(isinstance(route, list) and 1 <= len(route) <= 10 and all(isinstance(x, str) and x in NODES for x in route),
                 'Lộ trình không hợp lệ (1–10 điểm dừng trên bản đồ).')
        kit.need(route[0] != d['at'], 'Điểm đầu tiên đang là chỗ bạn đứng rồi.')
        kit.need(all(a != b for a, b in zip(route, route[1:])), 'Hai điểm dừng liền nhau bị trùng.')
        d['route'] = list(route)
        rows = _eta(c, d)
        total = sum(x['blocks'] for x in rows)
        msg = f'Đã chốt lộ trình {len(route)} điểm, {total} ô phố, về tới điểm cuối khoảng {hm(rows[-1]["at"])}.'
        if rows[-1]['fuel'] < 0:
            msg += ' ⚠️ Xăng không đủ cho cả tuyến — nhớ ghé cây xăng.'
        return dict(message=msg)
    if name == 'dl_ride':
        kit.need(d['route'], 'Chưa có lộ trình. Chọn điểm dừng rồi bấm “Chốt lộ trình”.')
        way = p.get('way', 'main')
        kit.need(way in WAYS, 'Chọn đường chính hoặc hẻm tắt.')
        nxt = d['route'][0]
        kit.need(way == 'main' or dist(d['at'], nxt) >= 2, 'Quãng này ngắn quá, không có hẻm tắt nào.')
        brake = d['parts']['brake']
        kit.need(way == 'main' or brake >= PART_INFO['brake']['low'],
                 f'Má phanh mòn còn {brake}% — hẻm tắt dốc, cua gắt, chạy vậy không an toàn. '
                 'Đi đường chính, hoặc thay má phanh ở tiệm Chú Bảy.', 'brake')
        if d['parts']['chain'] <= 0:
            d['stats']['chains'] += 1
            _fire(s, c, 'DE-CHAIN')
            return dict(message='⛓️ Sên tuột khỏi nhông, xe không chạy được — xử lý sên trước đã!')
        leg = _leg(c, d['at'], nxt, d['clock'], way)
        blocks, use = leg['blocks'], leg['fuel']
        kit.need(d['fuel'] >= use, f'Không đủ xăng tới {NODES[nxt]["name"]} (cần {use}%, còn {d["fuel"]}%). '
                 f'Ghé cây xăng hoặc mua xăng chai ven đường.', 'fuel')
        d['route'].pop(0)
        d['fuel'] -= use
        worn = _wear(c, d, leg, d['km'])
        d['km'] += blocks
        d['day_km'] += blocks
        _clock(d, leg['minutes'])
        d['at'] = nxt
        d['tyre'] = max(0, d['tyre'] - leg['wear'])
        if way == 'short':
            d['stats']['shortcuts'] += 1
        if leg['stall']:
            d['stats']['stalls'] += 1
        hurt = _ride_effects(c, blocks, leg)
        here = NODES[nxt]
        msg = (f'🛵 Tới {here["emoji"]} {here["name"]} lúc {hm(d["clock"])} ({"hẻm tắt, " if way == "short" else ""}'
               f'{blocks} ô phố, {leg["minutes"]} phút, −{use}% xăng).')
        if leg['notes']:
            msg += ' ' + ' · '.join(leg['notes']) + '.'
        picks = [t['needs']['item'] for t in _open(c) if t['known'] and not t['run']['loaded'] and t['needs']['pickup'] == nxt]
        drops = [t['needs']['item'] for t in _open(c) if t['run']['loaded'] and _dest(t) == nxt]
        if picks:
            msg += ' Lấy: ' + ', '.join(picks) + '.'
        if drops:
            msg += ' Giao: ' + ', '.join(drops) + '.'
        if hurt:
            msg += ' ⚠️ Trên đường: ' + '; '.join(hurt) + '.'
        if worn:
            msg += ' 🔧 ' + '; '.join(worn) + '. Ghé tiệm Chú Bảy.'
        if _flat(c, d):
            d['stats']['flats'] += 1
            _fire(s, c, 'DE-FLAT')
            msg += f' 💥 Bánh sau xẹp lép (lốp còn {d["tyre"]}%)!'
        elif d['parts']['chain'] <= 0:
            d['stats']['chains'] += 1
            _fire(s, c, 'DE-CHAIN')
            msg += ' ⛓️ Sên mòn chùng quá, tuột khỏi nhông!'
        elif d['tyre'] < TYRE_FLAT_AT:
            msg += f' Lốp mòn còn {d["tyre"]}% — thay ruột ở cây xăng hoặc tiệm Chú Bảy kẻo xẹp bánh.'
        return dict(message=msg)
    if name == 'dl_service':
        _at(d, 'gas', 'Thay ruột xe')
        kit.need(d['tyre'] < 100 or 'rim' in d['desk']['marks'], 'Lốp đang ngon lành, chưa cần thay ruột.')
        cost = SERVICE_COST + (RIM_COST if 'rim' in d['desk']['marks'] else 0)
        kit.confirm(p, f'Thay ruột mới, bơm lốp{", nắn vành" if "rim" in d["desk"]["marks"] else ""} hết {cost} xu?')
        kit.money(s, c, -cost, 'Thay ruột xe ở cây xăng', None, 'repair')
        d['tyre'] = 100
        d['desk']['marks'].pop('rim', None)
        d['stats']['services'] += 1
        _clock(d, 6)
        return dict(message=f'🔧 Thợ cây xăng thay ruột mới, bơm lốp ({cost} xu, 6 phút). Lốp 100%. '
                            'Nhớt, sên, má phanh thì phải ghé tiệm Chú Bảy.')
    if name == 'dl_fix':
        _at(d, 'garage', 'Sửa xe')
        parts = kit.id_list(p.get('parts'), PARTS, len(PARTS), 'Chọn bộ phận cần sửa trong danh sách.')
        kit.need(parts, 'Chọn ít nhất một bộ phận cần sửa.')
        rim = 'rim' in d['desk']['marks']
        for k in parts:
            kit.need(part(d, k) < 100 or (k == 'tyre' and rim), f'{PART_INFO[k]["name"]} còn tốt, chưa cần thay.')
        cost = sum(PART_INFO[k]['price'] for k in parts) + (RIM_COST if 'tyre' in parts and rim else 0)
        names = ', '.join(PART_INFO[k]['name'].lower() for k in parts)
        kit.confirm(p, f'Sửa {names} hết {cost} xu?')
        kit.need(c['money'] >= cost, f'Chưa đủ {cost} xu. Bỏ bớt, sửa bộ phận gấp nhất trước.', 'money')
        kit.money(s, c, -cost, f'Sửa xe ở tiệm Chú Bảy: {names}', None, 'repair')
        for k in parts:
            _set_part(d, k, 100)
        if 'tyre' in parts:
            d['desk']['marks'].pop('rim', None)
        d['stats']['repairs'] += 1
        _clock(d, FIX_MIN * len(parts))
        return dict(message=f'🔧 Chú Bảy làm xong {names} ({cost} xu, {FIX_MIN * len(parts)} phút): “Chạy êm rồi đó con, '
                            'nhớ ghé thường xuyên nha.”')
    if name == 'dl_wait':
        _clock(d, 5)
        return dict(message=f'⏳ Đứng chờ 5 phút… bây giờ là {hm(d["clock"])}.')
    if name == 'dl_refuel':
        amount = kit.integer(p.get('amount'), FUEL_STEP, 100)
        kit.need(amount % FUEL_STEP == 0, f'Đổ theo bước {FUEL_STEP}%.')
        kit.need(d['fuel'] + amount <= 100, f'Bình chỉ còn chỗ cho {100 - d["fuel"]}% nữa.')
        at_gas = d['at'] == 'gas'
        if at_gas:
            kit.need(not (d['desk']['marks'].get('nogas') == c['day'] and d['clock'] < 60),
                     'Cây xăng Gió Lộng mất điện tới 18:00, bơm không chạy. Mua xăng chai ven đường hoặc quay lại sau.')
        if not at_gas:
            kit.need(amount <= BOTTLE_MAX, f'Xăng chai ven đường chỉ mua tối đa {BOTTLE_MAX}%. Ghé cây xăng để đổ nhiều hơn.')
        price = amount // FUEL_STEP * FUEL_PRICE['gas' if at_gas else 'bottle']
        kit.confirm(p, f'Đổ {amount}% xăng hết {price} xu?')
        kit.money(s, c, -price, 'Đổ xăng' if at_gas else 'Mua xăng chai ven đường')
        d['fuel'] += amount
        _clock(d, 3 if at_gas else 2)
        return dict(message=f'⛽ Đã đổ {amount}% ({price} xu). Bình còn {d["fuel"]}%.' +
                    ('' if at_gas else ' Xăng chai đắt gấp đôi — lần sau canh ghé cây xăng.'))
    if name == 'dl_settle':
        _at(d, 'hub', 'Nộp tiền COD')
        kit.need(d['owed'] > 0, 'Không có khoản COD nào cần nộp.')
        amount = kit.integer(p.get('amount'), 0, 100000)
        kit.need(amount == d['owed'], 'Số tiền nộp không khớp bảng kê COD. Cộng lại từng dòng rồi đếm đúng số đó.')
        kit.confirm(p, f'Nộp {amount} xu COD cho kế toán bưu cục?')
        short = max(0, d['owed'] - d['bag'])
        if short:
            kit.money(s, c, -short, 'Bù thiếu tiền COD')
            d['shortage'] += short
        d['settled'] += 1
        d['bag'] = d['owed'] = 0
        d['cod'] = []
        kit.metric(c, 'cod_settled')
        _clock(d, 2)
        return dict(message=f'💵 Đã nộp {amount} xu, kế toán ký bảng kê.' +
                    (f' Túi COD thiếu {short} xu so với bảng kê — bạn tự bù từ ví.' if short else ' Khớp từng đồng!'))
    t = _order(c, p)
    n, r = t['needs'], t['run']
    kit.need(r['outcome'] is None, 'Đơn này đã xong.')
    if name == 'dl_call':
        kit.need(not r['called'], 'Đã gọi khách rồi.')
        r['called'] = True
        _clock(d, 2)
        msg = '📞 '
        if t['_unit']:
            r['unit'] = t['_unit']
            msg += f'Khách đọc số phòng: {t["_unit"]}. '
        if t.get('_moved') and r['moved'] is None:
            _fire(s, c, 'DE-MOVED', t)
            return dict(message=msg + f'{_who(t)}: “Ủa quên báo, mình mới chuyển qua {NODES[t["_moved"]]["name"]} rồi!”')
        if t['_away'] and d['clock'] < r['t0'] + t['_away']:
            r['back'] = r['t0'] + t['_away']
            msg += f'{_who(t)} đang ra ngoài: “Khoảng {hm(r["back"])} mới về tới, giao sau giờ đó nha.”'
        elif n['kind'] == 'food':
            msg += f'{_who(t)}: “Dạ, mình chờ nha!”'
        else:
            msg += f'{_who(t)}: “Có nhà, cứ tới nha.”'
        return dict(message=msg.strip())
    if name == 'dl_care':
        kind = kit.one_of(p.get('kind'), CARE_KINDS, 'Việc chăm khách không hợp lệ.')
        _at(d, _dest(t), 'Chăm khách tận cửa')
        kit.need(r['loaded'], 'Hàng chưa lên xe.')
        kit.need(not r['expired'] and not r['broken_seen'], 'Đơn này không giao được nữa — báo giao thất bại.')
        note = next((x for x in _known_notes(d, t) if x['kind'] == kind), None)
        kit.need(note, f'{_who(t)} chưa dặn việc này. Xem sổ tay khách quen để biết khách cần gì.')
        kit.need(kind not in r['care'], 'Việc này làm rồi.')
        r['care'].append(kind)
        d['stats']['cares'] += 1
        _clock(d, CARE_KINDS[kind]['minutes'])
        lines = {'carry': f'🤲 Bạn xách {n["item"].lower()} vào tận nơi cho {_who(t)}.',
                 'photo': f'📸 Chụp ảnh kiện hàng ở cửa, gửi {_who(t)} qua app.',
                 'check': f'🔍 Mở hộp đồng kiểm {n["item"].lower()} ngay trước mặt {_who(t)}.'}
        return dict(message=lines[kind] + f' (+{CARE_KINDS[kind]["minutes"]} phút) Nhớ đúng lời dặn trong sổ tay.')
    if name == 'dl_check':
        _at(d, n['pickup'], 'Kiểm hàng')
        kit.need(not r['loaded'], 'Hàng đã lên xe.')
        kit.need(not r['checked'], 'Đã kiểm rồi.')
        if n['kind'] == 'food':
            kit.need(d['clock'] >= _ready(t), f'Quán còn đang làm, khoảng {hm(_ready(t))} mới xong. Chờ quán một chút.', 'not_ready')
            r['checked'] = True
            if t['_missing']:
                r['missing'] = t['_missing']
                _clock(d, 3)
                return dict(message=f'🧾 So túi với bill: thiếu {t["_missing"]}! Quán xin lỗi, bỏ thêm vào túi.')
            r['missing'] = ''
            _clock(d, 1)
            return dict(message='🧾 So túi với bill: đủ món, đủ muỗng đũa.')
        r['checked'] = True
        r['w'] = t['_w']
        r['seam'] = t['_seam']
        _clock(d, 1)
        msg = f'⚖️ Cân: {kg(t["_w"])} (shop khai {kg(n["w"])}).'
        if t['_w'] != n['w']:
            msg += ' Lệch cân — cần báo để tính đúng phí.'
        if t['_w'] > LOAD_LIMIT:
            msg += f' Vượt {kg(LOAD_LIMIT)}: xe máy không chở an toàn.'
        if t['_seam']:
            msg += ' Mép thùng hở keo một đường.'
        return dict(message=msg)
    if name == 'dl_pack':
        kit.need(n['kind'] == 'parcel', 'Đồ ăn nằm trong thùng giữ nhiệt, không cần gói thêm.')
        item = kit.one_of(p.get('item'), ITEM_INDEX, 'Vật tư đóng gói không hợp lệ.')
        kit.need(item not in r['packed'], 'Đã dùng vật tư này cho đơn rồi.')
        if r['loaded']:
            kit.need(item == 'rainbag', 'Hàng đã buộc trên xe — dọc đường chỉ kịp trùm túi chống nước.')
        else:
            _at(d, n['pickup'], 'Đóng gói')
        unlock = ITEM_INDEX[item].get('unlock', 1)
        kit.need(unlock <= kit.level(c), f'{ITEM_INDEX[item]["name"]} mở khóa ở cấp {unlock}.')
        kit.take(c, item, 1)
        r['packed'].append(item)
        _clock(d, 1)
        return dict(message=f'{ITEM_INDEX[item]["emoji"]} Đã dùng {ITEM_INDEX[item]["name"].lower()} cho {n["item"].lower()}.')
    if name == 'dl_load':
        _at(d, n['pickup'], 'Lấy hàng')
        kit.need(not r['loaded'], 'Hàng đã lên xe.')
        report = p.get('report', False)
        kit.need(type(report) is bool, 'Mục báo lệch cân không hợp lệ.')
        if n['kind'] == 'food':
            kit.need(d['clock'] >= _ready(t), f'Món chưa xong (khoảng {hm(_ready(t))}). Chờ quán nhé.', 'not_ready')
        else:
            kit.need(r['checked'], 'Cân và kiểm hàng trước khi nhận lên xe.')
            kit.need(t['_w'] <= LOAD_LIMIT, f'Hàng {kg(t["_w"])} vượt tải {kg(LOAD_LIMIT)} của xe máy. Từ chối nhận, báo bưu cục chuyển xe tải.')
            if n['size'] == 'L':
                kit.need('strap' in r['packed'], 'Hàng cồng kềnh phải ràng dây chắc chắn mới được chở.')
        kit.need(_load(c) + t['_w'] <= LOAD_LIMIT,
                 f'Xe đang chở {kg(_load(c))}, thêm {kg(t["_w"])} là quá {kg(LOAD_LIMIT)}. Giao bớt rồi quay lại.')
        r['loaded'] = True
        kit.start_work(t)
        _clock(d, 1)
        msg = f'📦 Đã chằng {n["item"].lower()} lên xe.'
        if n['kind'] == 'parcel' and t['_w'] != n['w']:
            if report:
                r['reported'] = True
                msg += f' Đã báo lệch cân ({kg(t["_w"])}), app cộng phụ phí.'
            else:
                t['mistakes'] += 1
                msg += ' Không báo lệch cân — bưu cục thu thiếu cước, sổ sách lệch.'
        missing = [x for x in _needs_pack(t, c['day']) if x not in r['packed']]
        if missing:
            msg += ' ⚠️ Chưa có: ' + ', '.join(ITEM_INDEX[x]['name'].lower() for x in missing) + '.'
        if n['kind'] == 'food' and not r['checked']:
            msg += ' (Chưa so túi với bill.)'
        msg += _area(d, n['pickup'])
        return dict(message=msg)
    if name == 'dl_refuse':
        _at(d, n['pickup'], 'Từ chối nhận')
        kit.need(n['kind'] == 'parcel' and not r['loaded'] and r['checked'], 'Cân, kiểm hàng rồi mới quyết định từ chối.')
        over = t['_w'] > LOAD_LIMIT
        no_strap = n['size'] == 'L' and 'strap' not in r['packed'] and (
            ITEM_INDEX['strap'].get('unlock', 1) > kit.level(c) or kit.stock(c, 'strap') == 0)
        kit.need(over or no_strap, 'Hàng này xe chở được — không có lý do từ chối.')
        kit.confirm(p, 'Từ chối nhận đơn và báo bưu cục chuyển phương án khác?')
        r['outcome'] = 'refused'
        d['refused'] += 1
        d['day_refused'] += 1
        kit.metric(c, 'deliveries_refused_safely')
        reason = f'nặng {kg(t["_w"])}, vượt tải xe máy' if over else 'hàng cồng kềnh mà không có dây ràng'
        kit.complete(s, c, t, 0, f'Từ chối nhận {n["item"].lower()} vì {reason}; bưu cục chuyển xe tải.', status='referred')
        return dict(message=f'🚫 Đã từ chối: {reason}. Chị Hạnh chuyển đơn cho xe tải, cảm ơn bạn đã cân kỹ.')
    if name in ('dl_deliver', 'dl_safedrop'):
        gate = _gate(c, d, t)
        out = _deliver(s, c, d, t, name, p)
        if gate:
            out['message'] = gate + out['message']
        return out
    if name == 'dl_fail':
        kit.confirm(p, 'Báo giao thất bại cho đơn này?')
        due = _due(t)
        if n['kind'] == 'food' and (r['expired'] or d['clock'] > due + GRACE):
            r['expired'] = True
            r['outcome'] = 'failed'
            if r['loaded']:
                kit.waste(c, 'food', 1, n['value'], 'Đồ ăn giao trễ, khách hủy')
            msg = f'⌛ Đơn {n["item"].lower()} bị hủy vì trễ quá hẹn {hm(due)}.'
            fee = 0
        elif r['broken_seen']:
            _at(d, _dest(t), 'Làm biên bản')
            comp = min(c['money'], cf.comp(n['value'] // 2))   # half the value, then the tiền đền factor
            if comp:
                kit.money(s, c, -comp, 'Đền một phần giá trị hàng hỏng (bảo hiểm trả phần còn lại)')
            r['comp'] = comp
            r['outcome'] = 'failed'
            msg = f'📝 Lập biên bản hàng hỏng. Bạn đền {comp} xu, bảo hiểm trả phần còn lại.'
            fee = 0
        elif r['knocks'] and d['at'] == _dest(t) and t['_away'] and d['clock'] < r['t0'] + t['_away']:
            r['outcome'] = 'failed'
            fee = 4 if r['called'] else 0
            if not r['called']:
                t['mistakes'] += 1
            msg = '📦 Hoàn hàng về bưu cục, hẹn giao lại lần sau.' + ('' if r['called'] else ' (Chưa gọi khách lần nào — bưu cục nhắc nhở.)')
        else:
            kit.need(False, 'Khách vẫn đang chờ nhận — chưa có lý do báo thất bại.')
        d['failed'] += 1
        d['day_failed'] += 1
        kit.metric(c, 'deliveries_failed')
        if r['expired']:
            cq.slip(t, 'too_late', 3, 'Chờ gần cả tiếng không thấy đồ ăn đâu, tôi đành hủy đơn.', 'trễ tới mức khách hủy đơn')
        elif r['broken_seen']:
            cq.slip(t, 'broken', 3, 'Hàng tới nơi đã hỏng vì đóng gói sơ sài, tôi không nhận được.', 'hàng hỏng vì đóng gói thiếu')
        elif not r['called']:
            cq.slip(t, 'no_call', 2, 'Không gọi trước cho tôi một cuộc, tới lúc tôi đi vắng là hoàn hàng luôn.', 'không gọi mà hoàn hàng')
        story = f'Đơn {n["item"].lower()} giao không thành. ' + msg
        react = cq.react(s, c, t, fee, who=_who(t))
        fee = react['pay']
        if react['message']:
            msg += ' ' + react['message']
        kit.complete(s, c, t, fee, story, status='cancelled')
        msg += _score(s, c, t, clean=None)
        if r['expired'] or r['broken_seen']:
            msg += _bond_hurt(c, t)
        return dict(message=msg + (f' Phí giao lần đầu +{fee} xu.' if fee else ''))
    raise kit.eng().GameError('Thao tác giao hàng không hợp lệ.')


def _deliver(s: dict, c: dict, d: dict, t: dict, name: str, p: dict) -> dict:
    n, r = t['needs'], t['run']
    _at(d, _dest(t), 'Giao hàng')
    kit.need(r['loaded'], 'Hàng chưa lên xe.')
    kit.need(not r['expired'], 'Đơn đã bị hủy — báo giao thất bại.')
    kit.need(not r['broken_seen'], 'Khách đã từ chối vì hàng hỏng — báo giao thất bại.')
    due = _due(t)
    if n['kind'] == 'food' and d['clock'] > due + GRACE:
        r['expired'] = True
        return dict(message=f'⌛ Khách đã hủy đơn trên app vì chờ quá lâu (hẹn {hm(due)}). Báo giao thất bại.')
    if t.get('_dog') and r['dog'] is None:
        _clock(d, 1)
        d['stats']['dogs'] += 1
        _fire(s, c, 'DE-DOG', t)
        return dict(message='🐕 Một con chó vện to đùng lao ra sủa ầm ở cổng, không cho ai bước vào!')
    if t.get('_moved') and r['moved'] is None:
        _clock(d, 2)
        _fire(s, c, 'DE-MOVED', t)
        return dict(message=f'🚪 Bấm chuông không ai mở. Hàng xóm nói: “Người đó mới chuyển qua {NODES[t["_moved"]]["name"]} rồi.” '
                            'Gọi trước thì đỡ một chuyến!')
    if t.get('_bomb') and n['cod'] and r['bomb'] is None:
        _clock(d, 3)
        d['stats']['bombs'] += 1
        _fire(s, c, 'DE-BOMB', t)
        return dict(message=f'📵 Gọi {_who(t)} ba cuộc không bắt máy. Người nhà ra cửa: “Không đặt gì hết, không nhận!”')
    if name == 'dl_safedrop':
        kit.need(n['safe_drop'] or not n['paper'], 'Thư bảo đảm phải đúng người nhận ký, không gửi hộ được.')
        kit.need(not n['cod'], 'Đơn thu tiền hộ không được gửi bảo vệ.')
        kit.confirm(p, 'Gửi hàng ở chòi bảo vệ và chụp ảnh làm bằng chứng?')
        if _ruined(t):
            r['broken_seen'] = True
            t['mistakes'] += 1
            return dict(message='📸 Chú bảo vệ mở ra kiểm: hàng đã vỡ/hỏng trên đường. Không gửi được — báo giao thất bại.')
        if not n['safe_drop']:
            t['mistakes'] += 1
            cq.slip(t, 'handed_over', 2, 'Tôi dặn giao tận tay mà shipper gửi người khác nhận hộ, suýt thất lạc.', 'gửi người khác nhận hộ khi khách chưa cho phép')
        return _finish(s, c, t, 'safedrop')
    if n['cod']:
        kit.need(d['owed'] + n['cod'] <= COD_CAP, f'Túi COD sẽ vượt hạn mức {COD_CAP} xu — app khóa thu tiền. Về bưu cục nộp tiền trước.')
        change = kit.integer(p.get('change'), 0, 1000)
    at_door = r.get('asked', 0) > 0       # already at the door, counting the change again
    astray = bool(t['_unit']) and not r['unit']   # no room number: knock along the corridors and ask the neighbours
    if not at_door:
        _clock(d, STAIRS.get(n['dest'], 0) + (8 if astray else 0))
    back = r['t0'] + t['_away']
    if t['_away'] and d['clock'] < back:
        r['knocks'] += 1
        _clock(d, 2)
        return dict(message='🚪 Bấm chuông mãi không ai mở. ' + ('Khách hẹn ' + hm(back) + ' mới về — chờ hoặc đi giao đơn khác.' if r['called'] else 'Gọi hỏi khách xem sao.'))
    if _ruined(t):
        r['broken_seen'] = True
        t['mistakes'] += 1
        what = 'giấy tờ ướt nhòe mực' if n['paper'] else 'hàng bên trong đã vỡ'
        return dict(message=f'💔 Đồng kiểm với khách: {what}. Khách từ chối nhận. Báo giao thất bại và làm biên bản.')
    if astray and not at_door:
        t['mistakes'] += 1
        cq.slip(t, 'no_room', 2, 'Không gọi hỏi số phòng, shipper gõ cửa lung tung cả dãy, hỏi hàng xóm mới tìm ra tôi.', 'không hỏi số phòng, gõ nhầm cửa')
    if n['cod']:
        right = n['cash'] - (n['cod'] - r['discount'])   # a promised discount comes off what they pay
        extra = ''
        if change < right:
            short = right - change
            if at_door or till.careful(c, t, short, right):
                # They count it on the spot: nothing is handed over until the courier gives the rest.
                r['asked'] = min(9, r.get('asked', 0) + 1)
                return dict(message='💵 ' + till.ask_rest(t, short, _who(t)), refused=True)
            r['short'] = short            # nobody counted: found at home (after the reaction, in _finish)
        elif change > right:
            r['over'] = change - right
            back, extra = till.excess(c, t, change - right, _who(t))
            extra = ' ' + extra
            if back:
                r['returned'] = True
                change = right
            else:
                extra += ' Cuối ca túi COD sẽ thiếu đúng chừng đó.'
        r['change'] = change
        # Short-changed cash nobody noticed is not the post office's COD money: the bag only holds what is due.
        d['bag'] += max(0, min(n['cash'] - change, n['cod'] - r['discount']))
        d['owed'] += n['cod']
        d['cod'].append(dict(task=t['id'], item=n['item'], cod=n['cod'], day=c['day']))
        out = _finish(s, c, t, 'delivered')
        cut = f' Bớt cho khách {r["discount"]} xu từ túi mình.' if r['discount'] else ''
        out['message'] = f'💵 Thu {n["cash"]} xu, thối {change} xu.{extra}{cut} ' + out['message']
        return out
    kit.need(p.get('change') in (None, 0), 'Đơn đã thanh toán online, không thu tiền.')
    return _finish(s, c, t, 'delivered')


def _eta(c: dict, d: dict) -> list[dict]:
    """Main-road estimate for the planned route, with the alley shortcut of each leg beside it."""
    at, clock, fuel, rows = d['at'], d['clock'], d['fuel'], []
    for node in d['route']:
        leg = _leg(c, at, node, clock, 'main')
        alt = _leg(c, at, node, clock, 'short') if dist(at, node) >= 2 else None
        clock += leg['minutes']
        fuel -= leg['fuel']
        rows.append(dict(node=node, blocks=leg['blocks'], at=clock, fuel=fuel, minutes=leg['minutes'], notes=leg['notes'],
                         short=dict(blocks=alt['blocks'], minutes=alt['minutes'], fuel=alt['fuel'], notes=alt['notes'],
                                    stall=alt['stall'], smooth=alt['smooth'], local=alt['local'],
                                    brake=(d.get('parts') or {}).get('brake', 100) < PART_INFO['brake']['low']) if alt else None))
        at = node
    return rows


# --- review ---------------------------------------------------------------------
def feedback(c: dict, t: dict) -> dict:
    n, r = t['needs'], t['run']
    rows = []
    needed_call = bool(t['_unit']) or bool(t['_away'])
    if r['outcome'] == 'refused':
        rows.append(dict(key='judgement', label='Quyết định an toàn', score=5, note='cân kỹ, từ chối đúng quy định tải trọng'))
        rows.append(dict(key='contact', label='Báo cho khách', score=4, note='bưu cục chuyển xe khác, khách chờ thêm'))
        return dict(criteria=rows)
    if r['outcome'] == 'failed' and r.get('bomb') in ('return', 'refuse'):
        if r['bomb'] == 'return':
            rows.append(dict(key='honesty', label='Thủ tục hoàn hàng', score=5, note='gọi đủ, chụp ảnh, ghi lý do rõ ràng'))
            return dict(criteria=rows, cap=4)
        rows.append(dict(key='contact', label='Cư xử ở cửa', score=1, note='đứng lì ép khách nhận hàng'))
        return dict(criteria=rows, cap=1)
    if r['outcome'] == 'failed' and r.get('moved') == 'refuse':
        rows.append(dict(key='contact', label='Linh hoạt', score=2, note='khách đổi địa chỉ gần mà không nhận giao'))
        return dict(criteria=rows, cap=2)
    if r['outcome'] == 'failed':
        if r['expired']:
            rows.append(dict(key='time', label='Thời gian', score=1, note='trễ tới mức khách hủy đơn'))
            return dict(criteria=rows, cap=1)
        if r['broken_seen']:
            rows.append(dict(key='condition', label='Tình trạng hàng', score=1, note='hàng hỏng trên đường vì đóng gói thiếu'))
            rows.append(dict(key='honesty', label='Minh bạch', score=4, note='đồng kiểm, lập biên bản, đền bù rõ ràng'))
            return dict(criteria=rows, cap=2)
        rows.append(dict(key='contact', label='Liên lạc', score=4 if r['called'] else 2,
                         note='đã gọi, hẹn giao lại' if r['called'] else 'không gọi mà hoàn hàng luôn'))
        rows.append(dict(key='time', label='Thời gian', score=3, note='chưa nhận được hàng'))
        return dict(criteria=rows, cap=3)
    due = _due(t)
    if due is not None:
        late = r['late']
        rows.append(dict(key='time', label='Đúng giờ', score=5 if not late else 4 if late <= 5 else 3 if late <= 15 else 2,
                         note=f'tới trước {hm(due)}' if not late else f'trễ {late} phút'))
    else:
        rows.append(dict(key='time', label='Tốc độ', score=5, note='giao trong ca'))
    issues = _condition_notes(t)
    rows.append(dict(key='condition', label='Tình trạng hàng', score=max(2, 5 - len(issues)),
                     note='nguyên vẹn, khô ráo, đủ món' if not issues else '; '.join(issues)))
    if n['cod']:
        rows.append(dict(key='cash', label='Tiền thu hộ', score=2 if r['short'] else 4 if r.get('asked') or r['over'] else 5,
                         note='thối thiếu, về nhà mới thấy' if r['short'] else 'thối thiếu, khách phải nhắc' if r.get('asked')
                         else 'thối dư, khách trả lại' if r.get('returned') else 'thối nhầm tiền' if r['over'] else 'thối tiền chính xác'))
    if needed_call or r['outcome'] == 'safedrop':
        ok = r['called'] or r['outcome'] == 'safedrop'
        rows.append(dict(key='contact', label='Liên lạc', score=5 if ok and not r['knocks'] else 4 if ok else 3,
                         note='gọi trước, giao đúng chỗ' if ok and not r['knocks'] else 'phải bấm chuông mấy lần' if r['knocks'] else 'không gọi trước'))
    if n['kind'] == 'parcel' and t['_w'] != n['w']:
        rows.append(dict(key='accuracy', label='Cân & khai báo', score=5 if r['reported'] else 3,
                         note='báo đúng cân nặng thực tế' if r['reported'] else 'nhận hàng lệch cân mà không báo'))
    if r.get('moved') in ('accept', 'meet', 'nofee'):
        rows.append(dict(key='flex', label='Đổi địa chỉ', score=5 if r['moved'] != 'nofee' else 4,
                         note='nhận đổi địa chỉ, giao tới nơi mới' if r['moved'] != 'meet' else 'hẹn khách ra nhận ở chỗ cũ'))
    if r.get('dog') == 'bite':
        rows.append(dict(key='care', label='Cẩn thận', score=2, note='liều vào cổng có chó dữ, té xe'))
    if r.get('kept') or r.get('missed'):
        rows.append(dict(key='wishes', label='Nhớ lời dặn', score=3 if r['missed'] else 5,
                         note='quên lời dặn: ' + NOTE_INDEX[r['missed'][0]]['text'].split(' — ')[0].split(':')[0].lower()
                         if r['missed'] else 'nhớ đúng thói quen của khách quen'))
    return dict(criteria=rows)


# --- projections & validation -----------------------------------------------------
def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not k.startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def public_task(t: dict) -> dict:
    v = _strip(copy.deepcopy(t))
    if not t['known']:
        v['needs'] = None
        v['preview'] = dict(pickup=t['needs']['pickup'], dest=t['needs']['dest'], kind=t['needs']['kind'], emoji=t['needs']['emoji'])
        return v
    v['due'] = _due(t)
    v['ready'] = _ready(t) if t['needs']['kind'] == 'food' else None
    v['dest'] = _dest(t)
    return v


def public_data(raw: dict) -> dict:
    d = _extend(copy.deepcopy(raw['ext']['data']))
    wx = weather(raw['day'])
    d.update(weather=wx, mpu=MPU[wx], rate=FUEL_RATE[wx], load=_load(raw), limit=LOAD_LIMIT, cap=COD_CAP,
             eta=_eta(raw, raw['ext']['data']), clock_text=hm(d['clock']))
    live = _today(raw).get('day') == raw['day']
    m = mod_of(raw['day'])
    h = _live_hazards(raw)
    signs = [dict(kind='jam', node=j['node'], text=f'🚦 {NODES[j["node"]]["name"]} kẹt xe {hm(j["start"])}–{hm(j["end"])}',
                  now=j['start'] <= d['clock'] < j['end']) for j in h['jams']]
    if h['works']:
        signs.append(dict(kind='works', node=h['works'], text=f'🚧 Đào đường trước {NODES[h["works"]]["name"]}: đường chính vòng +2 ô', now=True))
    signs += [dict(kind='flood', node=x, text=f'🌊 {NODES[x]["name"]} ngập: hẻm tắt chết máy', now=True) for x in h['flood']]
    d['road'] = dict(live=live, mod=dict(id=m['id'], emoji=m['emoji'], name=m['name'], text=_mod_text(raw['day'])), signs=signs)
    score = rating(d)
    q = d['quest']
    d['score'] = dict(rating=score, top=score is not None and score >= TOP_RATING, top_at=TOP_RATING, top_bonus=TOP_BONUS,
                      streak=d['streak'], best=d['best'], every=STREAK_EVERY, streak_bonus=STREAK_BONUS, rated=len(d['stars']),
                      quest=dict(goal=q['goal'], done=q['done'], paid=q['paid'], bonus=q['bonus']) if q['day'] == raw['day'] else None)
    marks = d['desk'].get('marks', {})
    rim = 'rim' in marks
    parts = [dict(id=k, name=PART_INFO[k]['name'], emoji=PART_INFO[k]['emoji'], value=part(d, k), low=PART_INFO[k]['low'],
                  effect=PART_INFO[k]['effect'], price=PART_INFO[k]['price'] + (RIM_COST if k == 'tyre' and rim else 0),
                  need=part(d, k) < 100 or (k == 'tyre' and rim)) for k in PARTS]
    worst = min(parts, key=lambda x: (x['value'] - x['low'], PARTS.index(x['id'])))
    d['bike'] = dict(tyre=d['tyre'], flat_at=TYRE_FLAT_AT, service=SERVICE_COST + (RIM_COST if rim else 0),
                     rim=rim, nogas=marks.get('nogas') == raw['day'] and d['clock'] < 60, parts=parts, worst=worst['id'],
                     alert=any(x['value'] < x['low'] for x in parts) or rim)
    d['book'] = _book(d)
    d.pop('regulars', None)
    d['forecast'] = _forecast(raw, d)
    d['desk'] = _desk_view(raw)
    d.pop('stars', None)
    return d


def _book(d: dict) -> list[dict]:
    """The regulars' notes card: only notes the courier has been told."""
    out = []
    for i, rows in REGULARS.items():
        npc = kit.npc_id(ID, i)
        reg = d['regulars'].get(npc) or dict(visits=0, bond=0, notes=[])
        level = next((label for at, _, label in BOND_TIP if reg['bond'] >= at), 'khách mới')
        tip = next((amount for at, amount, _ in BOND_TIP if reg['bond'] >= at), 0)
        nxt = next((at for k, at in enumerate(NOTE_AT) if k < len(rows) and rows[k]['id'] not in reg['notes']), None)
        out.append(dict(npc=npc, name=PEOPLE[i][0], role=PEOPLE[i][1], visits=reg['visits'], bond=reg['bond'], max=BOND_MAX,
                        level=level, tip=tip,
                        notes=[dict(id=x, kind=NOTE_INDEX[x]['kind'], text=NOTE_INDEX[x]['text']) for x in reg['notes']],
                        locked=len(rows) - len(reg['notes']), next_in=max(1, nxt - reg['visits']) if nxt else None))
    return out


def validate_task(t: dict, original: dict) -> None:
    r = t['run']
    kit.need(isinstance(r, dict) and set(_empty_run()) == set(r), 'Dữ liệu chuyến giao sai.')
    n = t['needs']
    for k in ('checked', 'loaded', 'reported', 'called', 'wet', 'burst', 'melted', '_broken', 'broken_seen', 'expired'):
        kit.need(type(r[k]) is bool, 'Trạng thái chuyến giao sai.')
    kit.integer(r['day'], 0, 10**6)
    kit.integer(r['t0'], 0, 2000)
    kit.integer(r['knocks'], 0, 50)
    kit.integer(r['late'], 0, 2000)
    for k in ('short', 'over', 'comp', 'tip'):
        kit.integer(r[k], 0, 1000)
    kit.integer(r['asked'], 0, 9)
    kit.need(type(r['returned']) is bool and (not r['returned'] or r['over']), 'Tiền thối dư sai.')
    kit.need(not r['tip'] or (n['cod'] and r['tip'] == n['cash'] - n['cod'] + r['discount'] and t.get('tip_given', 0) >= r['tip']), 'Tiền khách cho sai.')
    till.validate_tip(t)
    kit.need(r['w'] in (None, t['_w']) and (r['w'] is None or r['checked']), 'Số cân không khớp hàng.')
    kit.need(r['seam'] in (None, t['_seam']), 'Tình trạng thùng sai.')
    kit.need(r['missing'] in (None, '', t['_missing']) and (r['missing'] != '' or not t['_missing']), 'Phiếu kiểm món sai.')
    kit.need(r['unit'] in (None, t['_unit']) and (r['unit'] is None or r['called']), 'Số phòng sai.')
    kit.need(r['back'] is None or (t['_away'] and r['back'] == r['t0'] + t['_away']), 'Giờ hẹn sai.')
    kit.need(isinstance(r['packed'], list) and len(set(r['packed'])) == len(r['packed']) and all(x in ITEM_INDEX for x in r['packed']),
             'Vật tư đóng gói sai.')
    kit.need(n['kind'] == 'parcel' or not r['packed'], 'Vật tư đóng gói sai.')
    kit.need(r['outcome'] in (None, 'delivered', 'safedrop', 'failed', 'refused'), 'Kết quả giao sai.')
    kit.need((r['outcome'] is None) == (t['status'] not in DONE), 'Kết quả giao sai.')
    kit.need(r['change'] is None or (n['cod'] and kit.integer(r['change'], 0, 1000) + r['short'] + r['tip'] >= n['cash'] - n['cod']), 'Tiền thối sai.')
    kit.need(r['fee'] is None or 0 <= kit.integer(r['fee'], 0, 200), 'Phí ship sai.')
    kit.need(t.get('gen') == original.get('gen'), 'Phiên bản đơn giao sai.')
    kit.need(r['dog'] in (None, 'ok', 'bite') and (r['dog'] is None or t.get('_dog')), 'Chuyện chó ở cổng sai.')
    kit.need(r['bomb'] in (None, 'return', 'discount', 'accept', 'refuse') and (r['bomb'] is None or t.get('_bomb')), 'Chuyện bom hàng sai.')
    kit.need(r['moved'] in (None, 'accept', 'meet', 'nofee', 'refuse') and (r['moved'] is None or t.get('_moved')), 'Chuyện đổi địa chỉ sai.')
    kit.need(r['dest'] is None or (r['dest'] == t.get('_moved') and r['moved'] in ('accept', 'nofee')), 'Địa chỉ giao sai.')
    kit.need(type(r['spilled']) is bool and (not r['spilled'] or n['kind'] == 'food'), 'Tình trạng món sai.')
    kit.need(kit.integer(r['discount'], 0, DISCOUNT) in (0, DISCOUNT) and (not r['discount'] or r['bomb'] == 'discount'), 'Tiền bớt cho khách sai.')
    care = r['care']
    kit.need(isinstance(care, list) and len(set(care)) == len(care) and all(x in CARE_KINDS for x in care)
             and (not care or r['loaded']), 'Việc chăm khách sai.')
    who = _npc_index(t)
    for k in ('kept', 'missed'):
        v = r[k]
        kit.need(isinstance(v, list) and len(set(v)) == len(v) and all(isinstance(x, str) and x in NOTE_INDEX and NOTE_INDEX[x]['who'] == who for x in v)
                 and (not v or r['outcome'] in ('delivered', 'safedrop')), 'Lời dặn khách quen sai.')
    kit.need(not set(r['kept']) & set(r['missed']), 'Lời dặn khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.mark_legacy(c, ID, 'gen')
    for t in c.get('tasks', []):
        if isinstance(t, dict) and t.get('career') == ID and isinstance(t.get('run'), dict):
            for k, v in {**RUN_V2, **RUN_V3, **RUN_V4}.items():
                t['run'].setdefault(k, copy.deepcopy(v))
    kit.desk_validate(d['desk'], EVENTS)
    parts = d['parts']
    kit.need(isinstance(parts, dict) and set(parts) == set(PARTS[1:]), 'Tình trạng xe sai.')
    for k in PARTS[1:]:
        kit.integer(parts[k], 0, 100)
    regs = d['regulars']
    kit.need(isinstance(regs, dict) and set(regs) <= set(REGULAR_IDS), 'Sổ tay khách quen sai.')
    for npc, reg in regs.items():
        kit.need(isinstance(reg, dict) and set(reg) == {'visits', 'bond', 'notes'}, 'Sổ tay khách quen sai.')
        visits = kit.integer(reg['visits'], 0, 10**6)
        kit.need(kit.integer(reg['bond'], 0, BOND_MAX) <= visits, 'Độ thân thiết sai.')
        ids = [x['id'] for x in REGULARS[REGULAR_IDS.index(npc)]]
        notes = reg['notes']
        kit.need(isinstance(notes, list) and len(set(notes)) == len(notes) and all(isinstance(x, str) and x in ids for x in notes)
                 and len(notes) <= sum(visits >= at for at in NOTE_AT), 'Lời dặn trong sổ tay sai.')
    areas = d['areas']
    kit.need(isinstance(areas, dict) and set(areas) <= set(NODES), 'Khu phố quen sai.')
    for v in areas.values():
        kit.integer(v, 0, 10**6)
    ev = d['desk']['ev']
    if ev is not None and 'task' in ev:
        kit.need(any(t.get('id') == ev['task'] for t in c.get('tasks', [])), 'Chuyện dọc đường gắn với đơn không có.')
    kit.need(isinstance(d['today'], dict) and set(d['today']) == {'day', 'mod'} and d['today']['mod'] in MOD_INDEX, 'Điều kiện đường hôm nay sai.')
    kit.integer(d['today']['day'], 0, 10**6)
    kit.integer(d['tyre'], 0, 100)
    kit.integer(d['streak'], 0, 10**6)
    kit.integer(d['best'], 0, 10**6)
    kit.need(isinstance(d['stars'], list) and len(d['stars']) <= RATING_KEEP, 'Điểm đánh giá sai.')
    for x in d['stars']:
        kit.integer(x, 1, 5)
    q = d['quest']
    kit.need(isinstance(q, dict) and set(q) == {'day', 'goal', 'done', 'paid', 'bonus'} and type(q['paid']) is bool, 'Mốc thưởng ca sai.')
    for k in ('day', 'goal', 'done', 'bonus'):
        kit.integer(q[k], 0, 10**6)
    kit.need(isinstance(d['stats'], dict) and set(d['stats']) == set(STAT_KEYS), 'Thống kê giao hàng sai.')
    for k in STAT_KEYS:
        kit.integer(d['stats'][k], 0, 10**9)
    kit.need(d.get('at') in NODES, 'Vị trí shipper sai.')
    kit.integer(d.get('clock'), 0, 2000)
    kit.integer(d.get('fuel'), 0, 100)
    for k in ('bag', 'owed', 'km', 'delivered', 'failed', 'refused', 'settled', 'shortage',
              'day_delivered', 'day_failed', 'day_refused', 'day_km', 'day_fees'):
        kit.integer(d.get(k), 0, 10**9)
    kit.need(d['bag'] <= d['owed'], 'Túi COD sai.')
    kit.need(isinstance(d.get('route'), list) and len(d['route']) <= 10 and all(x in NODES for x in d['route']), 'Lộ trình sai.')
    rows = d.get('cod')
    kit.need(isinstance(rows, list) and len(rows) <= 40, 'Bảng kê COD sai.')
    for row in rows:
        kit.need(isinstance(row, dict) and isinstance(row.get('task'), str) and isinstance(row.get('item'), str), 'Bảng kê COD sai.')
        kit.integer(row.get('cod'), 1, 1000)
        kit.integer(row.get('day'), 1, 10**6)
    kit.need(sum(x['cod'] for x in rows) == d['owed'], 'Bảng kê COD không khớp.')


# --- shift hooks -------------------------------------------------------------------
def on_task(s: dict, c: dict, t: dict) -> None:
    t['run']['t0'] = kit.data(c)['clock']
    t['run']['day'] = c['day']


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    d['clock'] = 0
    d['at'] = 'hub'
    d['route'] = []
    for t in _open(c):
        r = t['run']
        if not r['expired']:
            r.update(t0=0, day=c['day'], called=False, unit=None, back=None, knocks=0, care=[])
    m = mod_of(c['day'])
    d['today'] = dict(day=c['day'], mod=m['id'])
    goal, bonus = _goal(c['day'])
    d['quest'] = dict(day=c['day'], goal=goal, done=0, paid=False, bonus=bonus)
    d['desk']['marks'].pop('nogas', None)
    kit.log(s, c, 'note', f'{m["emoji"]} Đường hôm nay: {m["name"]} — {_mod_text(c["day"])} Mốc thưởng ca: {goal} đơn (+{bonus} xu).')
    kit.desk_start(s, c, ID, d['desk'], EVENTS, m['id'], festival=c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    surprise = _close_desk(s, c, d)
    expired = 0
    for t in _open(c):
        if t['needs']['kind'] == 'food' and not t['run']['expired']:
            t['run']['expired'] = True
            expired += 1
            if t['run']['loaded']:
                kit.waste(c, 'food', 1, t['needs']['value'], 'Hết ca, đơn đồ ăn chưa giao bị hủy')
    auto = 0
    if d['owed']:
        short = max(0, d['owed'] - d['bag'])
        pay = min(short, c['money'])
        if pay:
            kit.money(s, c, -pay, 'Bù thiếu tiền COD khi nộp cuối ca')
            d['shortage'] += pay
        auto = d['owed']
        kit.log(s, c, 'note', f'Cuối ca: nộp {d["owed"]} xu COD còn giữ cho kế toán bưu cục.')
        d['bag'] = d['owed'] = 0
        d['cod'] = []
    q = d['quest']
    out = dict(delivered=d['day_delivered'], failed=d['day_failed'], refused=d['day_refused'], km=d['day_km'],
               fees=d['day_fees'], fuel=d['fuel'], settled_at_close=auto, food_cancelled=expired, tyre=d['tyre'],
               streak=d['streak'], rating=rating(d), quest=f'{q["done"]}/{q["goal"]}' if q['day'] == c['day'] else None,
               quest_paid=q['paid'] if q['day'] == c['day'] else None, surprise=surprise)
    lines = []
    if q['day'] == c['day']:
        lines.append(f'🎯 Mốc ca: {q["done"]}/{q["goal"]} đơn' + (f' — đã nhận thưởng {q["bonus"]} xu.' if q['paid'] else ' — chưa đạt.'))
    score = rating(d)
    lines.append(f'⭐ Điểm tài xế: {score / 10:.1f}'.replace('.', ',') + (' — được ưu tiên đơn (+2 xu/đơn).' if score >= TOP_RATING else '.')
                 if score is not None else '⭐ Điểm tài xế: cần thêm vài đơn để có điểm.')
    lines.append(f'🔥 Chuỗi đơn sạch hiện tại: {d["streak"]} (kỷ lục {d["best"]}).')
    worn = [k for k in PARTS if part(d, k) < PART_INFO[k]['low'] + 10]
    lines.append('🔧 Xe: ' + ', '.join(f'{PART_INFO[k]["name"].lower()} {part(d, k)}%' for k in PARTS) +
                 (' — nên ghé tiệm Chú Bảy: ' + ', '.join(PART_INFO[k]['name'].lower() for k in worn) + '.' if worn else '.'))
    friends = [(PEOPLE[REGULAR_IDS.index(npc)][0], reg['bond']) for npc, reg in d['regulars'].items() if reg['bond']]
    if friends:
        lines.append('💛 Khách quen: ' + ', '.join(f'{name} {bond}/{BOND_MAX}' for name, bond in sorted(friends, key=lambda x: -x[1])) + '.')
    fc = _forecast(c, d)
    lines.append(f'📡 Dự báo ngày mai: {fc["emoji"]} {fc["name"]}. ' + ' '.join(fc['advice'][:3]))
    if surprise:
        lines.append(surprise)
    out['lines'] = lines
    out['parts'] = {k: part(d, k) for k in PARTS}
    out['forecast'] = dict(day=fc['day'], id=fc['id'], weather=fc['weather'])
    d['day_delivered'] = d['day_failed'] = d['day_refused'] = d['day_km'] = d['day_fees'] = 0
    return out


def _nearest_route(c: dict) -> list[str]:
    d = kit.data(c)
    stops = []
    for t in _open(c):
        if not t['known'] or t['run']['outcome']:
            continue
        stops.append(_dest(t) if t['run']['loaded'] else t['needs']['pickup'])
    at, out = d['at'], []
    stops = [x for x in dict.fromkeys(stops) if x != d['at']]
    while stops:
        nxt = min(stops, key=lambda x: (dist(at, x), x))
        out.append(nxt)
        stops.remove(nxt)
        at = nxt
    return out


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e['role']
    if role == 'sorter':
        route = _nearest_route(c)
        return ('Xếp đơn theo tuyến gần nhất: ' + ' → '.join(NODES[x]['name'] for x in route) + '. (Chỉ gợi ý — nhớ ưu tiên đơn đồ ăn sắp trễ.)'
                if route else 'Đã phân loại hàng lên kệ theo khu phố.')
    if not t or t['career'] != ID or not t['known'] or t['status'] in DONE:
        return None
    n, r = t['needs'], t['run']
    if role == 'support' and not r['called'] and (t['_unit'] or t['_away']):
        r['called'] = True
        msg = 'Đã gọi khách giúp bạn: '
        if t['_unit']:
            r['unit'] = t['_unit']
            msg += f'số phòng {t["_unit"]}. '
        if t['_away'] and kit.data(c)['clock'] < r['t0'] + t['_away']:
            r['back'] = r['t0'] + t['_away']
            msg += f'Khách hẹn {hm(r["back"])} mới về.'
        return msg.strip()
    if role == 'packer' and n['kind'] == 'parcel' and n['pickup'] == 'hub' and not r['loaded']:
        done = []
        for item in _needs_pack(t, c['day']):
            if item in r['packed'] or ITEM_INDEX[item].get('unlock', 1) > kit.level(c) or kit.stock(c, item) == 0:
                continue
            kit.take(c, item, 1)
            r['packed'].append(item)
            done.append(ITEM_INDEX[item]['name'].lower())
        if done:
            return f'Đã gói {n["item"].lower()} ở bưu cục: ' + ', '.join(done) + '. Bạn vẫn tự cân và nhận hàng.'
    return None


def hint(c: dict, t: dict) -> str:
    return ('Nhận đơn → chọn điểm dừng, chốt lộ trình, chạy xe → ở điểm lấy: cân/kiểm hàng, đóng gói đúng loại, nhận lên xe '
            '(báo nếu lệch cân) → ở điểm giao: gọi khách nếu thiếu số phòng, làm theo lời dặn trong sổ tay khách quen, thối tiền COD '
            'cho đúng → cuối cùng về bưu cục nộp COD. Xem dự báo ngày mai và ghé tiệm Chú Bảy khi xe báo đỏ.')


def content() -> dict:
    return dict(nodes=NODES, mpu=MPU, fuel_rate=FUEL_RATE, fuel_step=FUEL_STEP, fuel_price=FUEL_PRICE, bottle_max=BOTTLE_MAX,
                load_limit=LOAD_LIMIT, cod_cap=COD_CAP, grace=GRACE, notes=list(NOTES), stairs=STAIRS, late_fee=LATE_FEE,
                mods=[dict(id=m['id'], emoji=m['emoji'], name=m['name']) for m in MODS + [RAINY, STORM]],
                service_cost=SERVICE_COST, flat_at=TYRE_FLAT_AT, streak_every=STREAK_EVERY, streak_bonus=STREAK_BONUS,
                top_rating=TOP_RATING, top_bonus=TOP_BONUS, redirect_fee=REDIRECT_FEE, discount=DISCOUNT,
                road_rules=['Đường chính: đúng số ô phố; kẹt xe giờ cao điểm thì chậm gấp đôi, công trình thì đi vòng.',
                            'Hẻm tắt: bớt 1 ô, né kẹt xe và công trình, nhưng xóc (đổ nước lèo), mòn lốp gấp đôi, hẻm ngập thì chết máy.',
                            f'Lốp dưới {TYRE_FLAT_AT}% dễ xẹp bánh — thay ruột ở cây xăng hoặc tiệm Chú Bảy.',
                            f'Thuộc hẻm: làm việc ở một điểm {AREA_SMOOTH} lần thì hẻm tắt vào đó chạy êm; {AREA_LOCAL} lần thì biết lối tắt bớt thêm 1 ô.'],
                parts=[dict(id=k, name=PART_INFO[k]['name'], emoji=PART_INFO[k]['emoji'], low=PART_INFO[k]['low'],
                            price=PART_INFO[k]['price'], effect=PART_INFO[k]['effect']) for k in PARTS],
                fix_minutes=FIX_MIN, rim_cost=RIM_COST, care_kinds=CARE_KINDS, note_at=list(NOTE_AT), bond_max=BOND_MAX,
                bond_tip=[dict(at=at, tip=tip, label=label) for at, tip, label in BOND_TIP],
                area_smooth=AREA_SMOOTH, area_local=AREA_LOCAL)


# --- situations --------------------------------------------------------------------
def _p(who, emoji, text):
    return dict(who=who, emoji=emoji, text=text)


SITUATIONS = [
    dict(id='DL-S01', title='Mở hàng ra rồi mới không nhận', npc=5, tone='tense', min_day=1,
         opening='Cô Lệ xé băng keo, mở hộp gương ra xem rồi đẩy lại: “Không giống hình. Tôi không nhận, cũng không trả phí ship.”',
         swap='Bạn là cô Lệ: tuần trước mua phải hàng lỗi, giờ nhìn đâu cũng thấy lừa.',
         facts=[dict(id='bill', title='Vận đơn', source='Tem dán trên hộp', text='Shop ghi: “Cho xem hàng, không cho thử”. Khách được quyền từ chối nhận.'),
                dict(id='seal', title='Tình trạng hộp', source='Bạn quan sát', text='Hàng còn nguyên, chỉ bị xé băng keo miệng hộp.'),
                dict(id='rule', title='Quy trình bưu cục', source='Chị Hạnh dặn', text='Khách từ chối: chụp ảnh, dán lại, ghi lý do lên app, hoàn về bưu cục. Không tranh cãi, không tự bù tiền.')],
         options=[dict(id='return', label='Chụp ảnh, dán lại hộp, ghi lý do từ chối lên app, chào khách lịch sự rồi hoàn hàng', requires=['bill', 'rule'], quality='good', stars=4,
                       review='Shipper không cãi, làm đúng thủ tục, còn chào tôi đàng hoàng.',
                       outcome='Shop nhận lại hàng nguyên vẹn, xin lỗi cô Lệ vì ảnh quảng cáo quá lung linh.',
                       perspectives=[_p('Cô Lệ', '😤', 'Tôi tưởng sẽ bị cãi, ai ngờ bạn shipper chỉ gật đầu làm biên bản.'),
                                     _p('Chị Hạnh', '📻', 'Hoàn hàng có ảnh là shop khỏi nghi mình tráo đồ.'),
                                     _p('Chủ shop gương', '🪞', 'Có ảnh đúng lúc khách mở, tôi biết lỗi ở ảnh quảng cáo của mình.')]),
                  dict(id='argue', label='Cãi tới cùng: “Mở rồi thì phải nhận!”', quality='bad', stars=1,
                       review='Shipper to tiếng ngay trước cửa phòng khám, mèo cũng giật mình.',
                       outcome='Hai bên to tiếng, khách gọi tổng đài khiếu nại. Hàng vẫn phải hoàn.',
                       perspectives=[_p('Cô Lệ', '😠', 'Luật ghi rõ được xem hàng, shipper định bắt tôi mua à?'),
                                     _p('Chị Hạnh', '😮‍💨', 'Mất thêm một cuộc gọi giải trình với tổng đài.')]),
                  dict(id='pay', label='Tự bỏ tiền túi trả phí ship cho êm chuyện', cost=10, quality='ok',
                       outcome='Êm được một lúc, nhưng sổ sách hoàn hàng thiếu ảnh và lý do.',
                       perspectives=[_p('Bạn', '💸', 'Mất 10 xu mà chẳng ai biết mình bị thiệt.'),
                                     _p('Chị Hạnh', '🤔', 'Không có ghi chú lý do thì shop tưởng mình làm mất khách.')])],
         lesson='Khách được quyền từ chối khi vận đơn cho xem hàng: làm đúng thủ tục hoàn, có ảnh, không cãi và không tự bù.'),
    dict(id='DL-S02', title='Quán ra món trễ, đồng hồ app cứ chạy', npc=1, tone='tense', min_day=1,
         opening='Dì Năm lau mồ hôi: “Nồi nước lèo mới sôi lại, chờ dì 20 phút nha con.” Điện thoại rung: Anh Tùng nhắn “Sao lâu vậy???”',
         facts=[dict(id='kitchen', title='Trong bếp', source='Bạn nhìn thấy', text='Ba đơn trước còn chưa xong, dì Năm làm một mình.'),
                dict(id='app', title='Nút báo quán trễ', source='App tài xế', text='App có nút “Quán chuẩn bị lâu” để thời gian chờ không bị tính cho tài xế.'),
                dict(id='customer', title='Tin nhắn khách', source='Anh Tùng', text='“Phòng họp đợi đồ ăn, trễ nữa là khỏi ăn.”')],
         options=[dict(id='honest', label='Bấm báo quán trễ, nhắn khách giờ dự kiến mới và xin lỗi thay quán', requires=['app', 'customer'], quality='good', stars=4,
                       review='Trễ thật nhưng được báo trước, biết giờ mà sắp xếp. Ok.',
                       outcome='Anh Tùng dời giờ ăn, không hủy đơn. App ghi nhận lỗi trễ thuộc về quán.',
                       perspectives=[_p('Anh Tùng', '⌚', 'Tôi ghét nhất là không biết gì. Có giờ cụ thể là được.'),
                                     _p('Dì Năm', '🙏', 'Con báo giùm dì, lần sau dì làm đơn online trước.')]),
                  dict(id='rush', label='Chờ xong rồi phóng thật nhanh để gỡ lại thời gian', quality='bad', stars=3,
                       review='Tới nhanh mà nước lèo đổ ra túi, tèm lem.',
                       outcome='Suýt va xe ở ngã tư, túi nước lèo xóc đổ một nửa.',
                       perspectives=[_p('Bạn', '😰', 'Tim đập thình thịch cả đoạn đường.'),
                                     _p('Anh Tùng', '😑', 'Nhanh mà đổ hết nước thì nhanh làm gì.')]),
                  dict(id='cancel', label='Hủy đơn, đi nhận đơn khác cho đỡ phí thời gian', quality='ok',
                       outcome='Đơn được gán cho tài xế khác, khách chờ thêm 15 phút.',
                       perspectives=[_p('Anh Tùng', '😡', 'Bị hủy ngang lúc sắp tới giờ, phải đặt lại từ đầu.'),
                                     _p('Chị Hạnh', '📉', 'Tỉ lệ hủy của em tăng, tuần sau ít được ưu tiên đơn.')])],
         lesson='Trễ vì quán thì báo đúng kênh và cho khách giờ mới — không đem an toàn ra đổi lấy vài phút.'),
    dict(id='DL-S03', title='“Không mang lên lầu 6 là 1 sao”', npc=5, tone='tense', min_day=2,
         opening='Thùng tủ vải 12 ký. Cô Lệ đứng trên ban công lầu 6 gọi vọng xuống: “Mang lên tận phòng, không thì 1 sao!”',
         facts=[dict(id='policy', title='Chính sách giao', source='App', text='Hàng cồng kềnh giao tầng trệt; lên lầu là dịch vụ thỏa thuận thêm.'),
                dict(id='stairs', title='Cầu thang', source='Bạn quan sát', text='Cầu thang hẹp, tối, không tay vịn ở hai tầng cuối.'),
                dict(id='time', title='Đơn đang chờ', source='App', text='Còn một đơn đồ ăn phải lấy trong 15 phút.')],
         options=[dict(id='deal', label='Giải thích chính sách, đề nghị hỗ trợ khiêng cùng tới lầu 2 hoặc phí lên lầu nhỏ; khách tự chọn', requires=['policy', 'stairs'], quality='good', stars=4,
                       review='Không lên tận nơi, nhưng nói năng đàng hoàng, còn phụ khiêng một đoạn.',
                       outcome='Cô Lệ gọi con trai xuống khiêng cùng từ lầu 2. Không ai trẹo lưng.',
                       perspectives=[_p('Cô Lệ', '😒', 'Tôi dọa vậy thôi, nghe giải thích cũng thấy có lý.'),
                                     _p('Bạn', '🙂', 'Giữ được lưng, giữ được đơn đồ ăn phía sau.')]),
                  dict(id='carry', label='Cắn răng vác một mình lên lầu 6 cho xong', quality='ok', stars=5,
                       review='Shipper vác tận phòng, 5 sao!',
                       outcome='Được 5 sao, nhưng đau lưng cả tối và trễ luôn đơn đồ ăn tiếp theo.',
                       perspectives=[_p('Bạn', '🥵', 'Lưng kêu răng rắc, đơn sau trễ 10 phút.'),
                                     _p('Khách đơn sau', '⌛', 'Cơm nguội rồi mới tới.')]),
                  dict(id='leave', label='Đặt thùng dưới đất, bỏ đi không nói gì', quality='bad', stars=1,
                       review='Vứt thùng dưới sân rồi đi mất. Tệ!',
                       outcome='Khách khiếu nại, bưu cục phải gọi xin lỗi.',
                       perspectives=[_p('Cô Lệ', '😡', 'Đúng chính sách hay không thì cũng phải nói một câu chứ.'),
                                     _p('Chị Hạnh', '📞', 'Chị lại phải đi xin lỗi thay em.')])],
         lesson='Biết chính sách và giới hạn sức mình; nói rõ và đưa lựa chọn thay vì im lặng hoặc cố quá sức.'),
    dict(id='DL-S04', title='Chiếc ví rơi giữa đường', npc=6, tone='gentle', min_day=1,
         opening='Dừng đèn đỏ gần Chợ Chiều, bạn thấy một chiếc ví nằm giữa làn xe: căn cước, thẻ xe buýt và khoảng 300 xu.',
         facts=[dict(id='id', title='Trong ví', source='Căn cước', text='Chủ ví là một bác lớn tuổi, địa chỉ ở phường bên.'),
                dict(id='hub', title='Quy định bưu cục', source='Chị Hạnh', text='Đồ nhặt được mang về quầy bưu cục, lập biên bản và báo công an phường.'),
                dict(id='rush', title='Đơn đang giao', source='App', text='Bạn còn hai đơn trong thùng, chưa đơn nào sắp trễ.')],
         options=[dict(id='report', label='Nhặt vào lề an toàn, mang về quầy bưu cục lập biên bản và báo công an phường', requires=['id', 'hub'], quality='good',
                       outcome='Ngay tối đó bác chủ ví được liên lạc, tới nhận lại đủ tiền, gửi lời cảm ơn tới bưu cục.',
                       perspectives=[_p('Chủ ví', '👴', 'Tiền thì ít, cái thẻ căn cước mà mất là tôi chạy giấy tờ cả tháng.'),
                                     _p('Chị Hạnh', '📝', 'Có biên bản rõ ràng thì ai cũng yên tâm.'),
                                     _p('Bạn', '😊', 'Chỉ mất 5 phút, mà nhẹ lòng cả ca.')]),
                  dict(id='post', label='Chụp ảnh căn cước đăng lên nhóm mạng xã hội để tìm chủ', requires=['id'], quality='ok',
                       outcome='Tìm được chủ, nhưng ảnh căn cước bị chia sẻ khắp nơi.',
                       perspectives=[_p('Chủ ví', '😟', 'Cảm ơn, nhưng số căn cước của tôi giờ ai cũng thấy.'),
                                     _p('Người trong nhóm', '📱', 'Lẽ ra nên che thông tin cá nhân trước khi đăng.')]),
                  dict(id='keep', label='Rút tiền, vứt ví lại chỗ cũ', quality='bad', reward=30,
                       outcome='Camera ở chợ ghi lại. Bưu cục bị hỏi thăm, bạn bị đình chỉ nhận đơn một tuần.',
                       perspectives=[_p('Chủ ví', '😢', 'Tiền thuốc của tôi cả tuần nằm trong đó.'),
                                     _p('Chị Hạnh', '😔', 'Uy tín cả bưu cục đi theo chiếc áo đồng phục của em.')])],
         lesson='Đồ nhặt được giao cho nơi có trách nhiệm và bảo vệ thông tin cá nhân của chủ đồ.'),
    dict(id='DL-S05', title='Thùng hàng móp vì xe đổ', npc=0, tone='gentle', min_day=2,
         opening='Mưa trơn, xe bạn nghiêng đổ ở đầu hẻm. Thùng hàng của chị Mận móp một góc, bên trong nghe “lạch cạch”.',
         facts=[dict(id='photo', title='Hiện trạng', source='Bạn kiểm tra', text='Góc thùng móp, băng keo còn nguyên, chưa biết hàng bên trong ra sao.'),
                dict(id='insurance', title='Bảo hiểm hàng', source='App', text='Hàng có khai giá; sự cố được báo kèm ảnh thì bảo hiểm hỗ trợ một nửa.'),
                dict(id='customer', title='Người nhận', source='Chị Mận', text='Chị Mận quý khách hàng này, muốn biết sự thật hơn là nghe hứa.')],
         options=[dict(id='report', label='Chụp ảnh ngay, báo sự cố lên app, giao kèm lời giải thích và mời khách đồng kiểm', requires=['photo', 'insurance'], quality='good', stars=4,
                       review='Hộp móp nhưng shipper nói thật, mở kiểm cùng, còn báo bảo hiểm. Quý!',
                       outcome='Chỉ một chiếc chén mẻ, bảo hiểm và shop đổi mới. Chị Mận vẫn giữ được khách.',
                       perspectives=[_p('Chị Mận', '🍵', 'Chị buồn chiếc chén nhưng quý sự thật thà.'),
                                     _p('Khách nhận', '🙂', 'Được mở kiểm cùng, không ai nghi ai.')]),
                  dict(id='hide', label='Dán thêm băng keo che góc móp rồi giao như chưa có gì', quality='bad', stars=1,
                       review='Nhận hộp dán chằng chịt, mở ra chén vỡ. Shipper chối bay!',
                       outcome='Khách phát hiện chén vỡ sau khi shipper đi, khiếu nại cả shop lẫn bưu cục.',
                       perspectives=[_p('Chị Mận', '😞', 'Mất khách quen chỉ vì một lớp băng keo.'),
                                     _p('Chị Hạnh', '📂', 'Không có ảnh sự cố thì bảo hiểm không hỗ trợ được.')]),
                  dict(id='lost', label='Báo “thất lạc hàng” cho gọn', quality='bad',
                       outcome='Kiểm tra định vị cho thấy hàng vẫn trong thùng xe. Bạn bị lập biên bản gian dối.',
                       perspectives=[_p('Chị Hạnh', '😠', 'Báo sai còn nặng hơn làm móp hàng.'),
                                     _p('Chị Mận', '❓', 'Hàng tôi rõ ràng đang ở đâu đó mà?')])],
         lesson='Sự cố thì báo ngay kèm ảnh và để khách đồng kiểm — che giấu làm chuyện nhỏ thành lớn.'),
    dict(id='DL-S06', title='Đường tắt ngược chiều', npc=1, tone='tense', min_day=1,
         opening='Còn 6 phút là trễ đơn của anh Tùng. Con đường ngược chiều trước Trường Bồ Câu sẽ cắt ngắn được hẳn một vòng.',
         facts=[dict(id='sign', title='Biển báo', source='Đầu đường', text='Đường một chiều, giờ tan trường đông học sinh.'),
                dict(id='late', title='Hậu quả trễ', source='App', text='Trễ vài phút chỉ bị trừ ít phí ship, không bị khóa tài khoản.'),
                dict(id='msg', title='Nhắn khách', source='App', text='Có thể nhắn khách “Em kẹt đường, trễ 5 phút”.')],
         options=[dict(id='around', label='Đi đúng đường vòng, nhắn khách xin trễ 5 phút', requires=['sign', 'msg'], quality='good', stars=4,
                       review='Trễ chút nhưng có báo trước, lịch sự.',
                       outcome='Tới trễ 5 phút, anh Tùng càu nhàu một câu rồi thôi.',
                       perspectives=[_p('Anh Tùng', '🙄', 'Trễ 5 phút thì cũng được, miễn là báo.'),
                                     _p('Phụ huynh trước trường', '👩‍👧', 'Giờ tan trường mà xe cứ đâm ngược chiều thì sợ lắm.')]),
                  dict(id='against', label='Chạy ngược chiều cho kịp', quality='bad', cost=15, stars=5,
                       review='Nhanh ghê, 5 sao.',
                       outcome='Suýt quẹt một em học sinh, bị cảnh sát giao thông lập biên bản phạt.',
                       perspectives=[_p('Em học sinh', '😨', 'Em giật mình làm rơi cả cặp.'),
                                     _p('Bạn', '😓', 'Được 5 sao mà mất tiền phạt, còn run cả tay.')]),
                  dict(id='sidewalk', label='Leo lề đi cho nhanh', quality='bad', cost=5,
                       outcome='Người đi bộ la ó, bảo vệ trường chụp ảnh gửi bưu cục.',
                       perspectives=[_p('Bảo vệ trường', '📸', 'Vỉa hè là của người đi bộ.'),
                                     _p('Chị Hạnh', '😮‍💨', 'Áo đồng phục in logo, ai cũng biết em là ai.')])],
         lesson='Vài phút trễ có thể xin lỗi; tai nạn thì không lấy lại được.'),
    dict(id='DL-S07', title='Ca mưa to, thưởng gấp đôi', npc=6, tone='gentle', min_day=3,
         opening='Mưa như trút, vài con hẻm ngập tới bánh xe. Chị Hạnh gọi: “Ca này thưởng gấp đôi, em chạy thêm được không?”',
         facts=[dict(id='flood', title='Đường ngập', source='Bản đồ', text='Hẻm Ốc Bươu ngập 30 cm, có sét xa.'),
                dict(id='gear', title='Đồ bảo hộ', source='Thùng xe', text='Áo mưa bộ còn tốt, đèn xe một bên mờ.'),
                dict(id='rule', title='Hướng dẫn an toàn', source='Bưu cục', text='Được từ chối đơn đi qua vùng ngập sâu; dừng trú khi có sét gần.')],
         options=[dict(id='safe', label='Nhận thêm ca nhưng chỉ tuyến không ngập, bật đèn, dừng trú khi có sét', requires=['flood', 'rule'], quality='good', reward=15,
                       outcome='Bạn chạy chậm mà chắc, giao được 3 đơn, về an toàn.',
                       perspectives=[_p('Chị Hạnh', '📻', 'Chị cần người chạy bền, không cần người liều.'),
                                     _p('Khách chờ đồ ăn', '☔', 'Trời mưa vậy mà vẫn có người mang tới, quý lắm.')]),
                  dict(id='all', label='Nhận hết mọi đơn kể cả hẻm ngập', quality='bad', reward=25, cost=20,
                       outcome='Xe chết máy giữa hẻm ngập, tốn tiền sửa bugi, hàng ướt.',
                       perspectives=[_p('Bạn', '🥶', 'Đẩy xe lội nước 20 phút.'),
                                     _p('Thợ sửa xe', '🔧', 'Nước vô bugi rồi, chạy không nổi đâu.')]),
                  dict(id='decline', label='Từ chối ca thêm vì đèn xe mờ', requires=['gear'], quality='ok',
                       outcome='Bạn về nghỉ an toàn, chị Hạnh tìm người khác.',
                       perspectives=[_p('Chị Hạnh', '🙂', 'Biết giới hạn là tốt, mai nhớ thay bóng đèn nhé.'),
                                     _p('Đồng nghiệp', '🛵', 'Ca mưa thiếu người, tụi mình chạy mệt hơn chút.')])],
         lesson='Tiền thưởng không đáng để đánh cược an toàn: nhận việc trong giới hạn an toàn của mình.'),
    dict(id='DL-S08', title='Cuộc gọi xin mã OTP', npc=6, tone='tense', min_day=2,
         opening='Số lạ gọi tới: “Anh là kỹ thuật app Giao Nhanh. Tài khoản em bị khóa ví, đọc mã OTP vừa gửi để anh mở giúp, kẻo mất tiền thưởng.”',
         facts=[dict(id='sms', title='Tin nhắn OTP', source='Điện thoại', text='“Mã OTP đăng nhập ví của bạn là …. KHÔNG chia sẻ mã cho bất kỳ ai.”'),
                dict(id='official', title='Kênh chính thức', source='Chị Hạnh dặn', text='Bưu cục không bao giờ xin OTP. Mọi hỗ trợ đều qua mục Trợ giúp trong app hoặc gặp trực tiếp.'),
                dict(id='pressure', title='Giọng người gọi', source='Cuộc gọi', text='Hối thúc liên tục: “Nhanh lên, 2 phút nữa là mất tiền!”')],
         options=[dict(id='hangup', label='Không đọc mã, cúp máy, báo chị Hạnh qua kênh chính thức', requires=['sms', 'official'], quality='good',
                       outcome='Chị Hạnh cảnh báo cả nhóm tài xế. Hai người khác cũng vừa nhận cuộc gọi y hệt.',
                       perspectives=[_p('Chị Hạnh', '🛡️', 'Em báo sớm nên cả nhóm tránh được.'),
                                     _p('Đồng nghiệp', '😮', 'Suýt nữa tôi cũng đọc mã rồi.')]),
                  dict(id='read', label='Đọc mã cho nhanh, sợ mất tiền thưởng', quality='bad', cost=40,
                       outcome='Ví tài xế bị rút sạch trong vài phút.',
                       perspectives=[_p('Bạn', '😱', 'Hai tuần chạy xe bay mất trong một cuộc gọi.'),
                                     _p('Chị Hạnh', '😔', 'Không ai từ bưu cục xin OTP cả, em nhớ nhé.')]),
                  dict(id='argue', label='Không đọc mã nhưng bấm vào đường link họ gửi để “kiểm tra”', requires=['pressure'], quality='bad', cost=10,
                       outcome='Đường link giả cài phần mềm lạ, bạn phải mang máy đi cài lại.',
                       perspectives=[_p('Thợ sửa điện thoại', '📱', 'Link lạ nguy hiểm không kém đọc OTP.'),
                                     _p('Bạn', '😩', 'Tưởng mình tỉnh táo rồi chứ.')])],
         lesson='Không đọc OTP, không bấm link lạ; xác minh qua kênh chính thức. Người thật sẽ không hối thúc bạn như vậy.'),
]

SPEC = dict(
    id=ID, prefix='dl_', category='outdoor',
    meta=dict(short='Giao hàng', place='Giao Nhanh Mây Chiều', tagline='Đúng người, đúng giờ, đúng tiền.', icon='bike',
              color='#e0823a', light='#fff1e2', weather='Chiều gió, trời hay đổi', work='Đơn đang chạy', station='Yên xe',
              greeting='Nhận đơn, chốt lộ trình, cân hàng, gói kỹ, gọi khách khi thiếu số phòng, thối tiền cho đúng và nộp COD về bưu cục nhé.',
              caption='Mỗi con hẻm là một câu chuyện đang chờ được gõ cửa', map_label='14 · GIAO NHANH MÂY CHIỀU'),
    people=PEOPLE,
    staff=[('Na', 'sorter', 'Phân loại hàng theo tuyến, nhớ đường như in.', 78, 84),
           ('Khôi', 'packer', 'Đóng gói chắc tay, tiết kiệm màng xốp.', 80, 88),
           ('Thảo', 'support', 'Gọi khách giọng ngọt, hỏi số phòng không sót.', 82, 90),
           ('Lợi', 'packer', 'Khỏe, chằng hàng cồng kềnh rất kỹ.', 74, 80)],
    roles={'sorter': 'Phân loại tuyến', 'packer': 'Đóng gói', 'support': 'CSKH gọi khách'},
    inventory=dict(items=ITEMS, capacity=40),
    prices={},
    tip=2,
    physical=('dl_ride', 'dl_deliver'),
    free_actions=(),
    no_tick=('dl_plan', 'dl_decide'),
    waste_items=('food',),
    activity=('🛵', 'Thùng xe gọn gàng', [('Bộ chén gốm', 'Bọc xốp hơi'), ('Thư bảo đảm', 'Túi chống nước'),
                                         ('Sữa chua', 'Túi giữ lạnh'), ('Tủ vải', 'Dây ràng')],
              ['Nhận đơn trên app', 'Chốt lộ trình', 'Cân, gói, nhận hàng', 'Gọi khách, giao, thu tiền', 'Về bưu cục nộp COD']),
    stories=[('Tô cháo cho ông Út', ('Bà Út đặt cháo cho ông nhà đang cảm, dặn đi dặn lại “ít hành”.',
                                     'Bạn đứng chờ quán nấu, so từng hộp với bill rồi mới đi.',
                                     'Hôm sau bà Út dúi cho bạn hai cái bánh ít: “Ông khỏe rồi, cảm ơn cháu.”')),
             ('Bản đồ trong đầu của Na', ('Na chỉ bạn cách xếp đơn theo cụm: lấy gần, giao xa, đồ ăn luôn đi trước.',
                                          'Bạn tập vẽ tuyến trên giấy trước mỗi ca, gạch dần từng điểm.',
                                          'Cuối tuần, số km của bạn giảm hẳn mà đơn giao lại nhiều hơn.')),
             ('Chiếc váy kịp giờ tiệc', ('Bé Vy đặt váy dự tiệc, nhưng cứ chạy ra tiệm làm tóc.',
                                         'Bạn gọi trước, giao đơn khác rồi quay lại đúng giờ hẹn.',
                                         'Vy gửi ảnh mặc váy dự tiệc: “Nhờ bạn shipper mà em kịp giờ!”'))],
    review_asides=['Shipper lễ phép, chào hỏi đàng hoàng 🛵', 'Hàng gói kỹ, sạch sẽ, cầm là thấy yên tâm.',
                   'Giao gọn gàng, không phải nhắc câu nào.', 'Tới đúng giờ như đồng hồ báo thức!'],
    situations=SITUATIONS,
    guide='Nhận đơn → chốt lộ trình → cân, kiểm, gói → nhận hàng → gọi khách → giao, thu tiền → nộp COD.',
)


# --- v0.5 surprises on the road ------------------------------------------------------------
# Generic ones come from the daily plan (kit.desk_*); order-bound ones (need_mark='ctx', a mark
# that is never set) are opened by the action that meets them, with the order id in the event.
SUNNY = ('normal', 'school', 'market', 'works', 'sale')
EVENTS = [
    dict(id='DE-POLICE', title='Chốt kiểm tra giấy tờ xe', emoji='👮', npc=6, min_day=2, tone='tense', weight=2,
         text='Tới ngã tư Chợ Chiều, cảnh sát giao thông ra hiệu tấp vào lề kiểm tra giấy tờ xe.',
         options=[dict(id='stop', label='Tấp vào lề, xuất trình bằng lái và giấy tờ xe', hint='+5 phút', effects=dict(clock=5), good=True,
                       outcome='Giấy tờ đủ, anh cảnh sát dặn cài quai mũ bảo hiểm rồi cho đi tiếp.'),
                  dict(id='dodge', label='Quay đầu né chốt, chạy đường khác', hint='Dễ bị chặn lại',
                       luck=dict(p=0.4, win=dict(effects=dict(clock=4), outcome='Né được, nhưng phải chạy vòng thêm một đoạn.', good=False),
                                 lose=dict(effects=dict(money=-20, clock=12), good=False,
                                           outcome='Bị chặn lại ở đầu hẻm, lập biên bản vì bỏ chạy: phạt 20 xu, mất 12 phút.')))],
         default='stop'),
    dict(id='DE-STORM', title='Mưa giông bất chợt', emoji='🌩️', npc=6, min_day=2, tone='tense', weight=2, mods=SUNNY,
         text='Trời đang nắng bỗng tối sầm, gió giật, mưa sắp đổ xuống. Hàng trên xe chưa có túi chống nước.',
         options=[dict(id='shelter', label='Tấp vào hiên trú 10 phút cho qua cơn', hint='+10 phút, hàng khô ráo', effects=dict(clock=10), good=True,
                       outcome='Cơn giông qua nhanh, hàng khô ráo, chỉ trễ chút.'),
                  dict(id='wrap', label='Trùm túi chống nước cho từng kiện rồi chạy', hint='Mỗi kiện một túi mưa', effects=dict(wrap=1, clock=3),
                       outcome='Trùm túi xong thì mưa cũng vừa tới.'),
                  dict(id='go', label='Chạy luôn cho kịp', hint='Kiện không có túi sẽ ướt', effects=dict(soak=1), good=False,
                       outcome='Mưa quất ướt cả người lẫn hàng.')],
         default='shelter'),
    dict(id='DE-SCAM', title='Shop lạ nhờ ứng tiền hàng', emoji='🎣', npc=6, min_day=3, tone='tense',
         text='Một shop lạ nhắn qua app: “Em ứng trước 80 xu tiền hàng giúp shop nha, lát khách trả COD 120 xu, em lời 40!”',
         options=[dict(id='call', label='Gọi thử số người nhận trước đã', hint='+3 phút', effects=dict(clock=3, xp=4), good=True,
                       outcome='Số người nhận không có thật — đơn ảo lừa ứng tiền. Bạn báo chị Hạnh chặn shop.'),
                  dict(id='report', label='Từ chối ứng tiền, báo bưu cục', effects=dict(xp=4), good=True,
                       outcome='Chị Hạnh: “Bưu cục không bao giờ bắt tài xế ứng tiền. Em làm đúng rồi.”'),
                  dict(id='pay', label='Ứng 80 xu cho nhanh, lời 40 xu mà', effects=dict(money=-80), good=False,
                       outcome='Shop chặn liên lạc, người nhận không có thật. Mất trắng 80 xu.')],
         default='report'),
    dict(id='DE-ERRAND', title='Bà Út nhờ mua giùm thuốc', emoji='👵', npc=3, min_day=2, tone='gentle',
         text='Bà Út đứng đầu hẻm vẫy: “Cháu tiện đường mua giùm bà vỉ thuốc ho cho ông nhà nghen, bà gửi tiền công.”',
         options=[dict(id='help', label='Ghé tiệm thuốc mua giùm bà', hint='+10 phút, +6 xu tiền công', effects=dict(clock=10, money=6), good=True,
                       review=[5, 'Cháu shipper tốt bụng, tiện đường mua thuốc giùm bà.'],
                       outcome='Bà Út dúi thêm cái bánh ít: “Có cháu đỡ quá.”'),
                  dict(id='later', label='Hẹn bà cuối ca ghé mua', outcome='Bà Út gật gù: “Ừ, không gấp đâu, cuối ca nhớ nghen.”'),
                  dict(id='no', label='Từ chối khéo vì đang chở đơn gấp', outcome='Bà Út cười xòa: “Thôi cháu đi đi, để bà nhờ đứa khác.”')],
         default='later'),
    dict(id='DE-BATTERY', title='Điện thoại còn 8% pin', emoji='🪫', npc=6, min_day=2, tone='gentle', no_mark='powerbank',
         text='App báo pin yếu: 8%. Hết pin là không gọi được khách, không xem được đơn.',
         options=[dict(id='charge', label='Ghé quán nước sạc nhờ 10 phút', hint='+10 phút, 2 xu ly trà đá', effects=dict(clock=10, money=-2), good=True,
                       outcome='Vừa sạc vừa nghỉ chân, pin lên 40%.'),
                  dict(id='buy', label='Mua sạc dự phòng ở tiệm điện thoại', hint='15 xu, không lo hết pin nữa', effects=dict(money=-15, mark='powerbank'), good=True,
                       outcome='Có cục sạc dự phòng, từ nay yên tâm chạy cả ca.'),
                  dict(id='risk', label='Tắt bớt ứng dụng, chạy tiếp', luck=dict(
                      p=0.5, win=dict(outcome='Về tới nơi máy còn đúng 1%, hú hồn.'),
                      lose=dict(effects=dict(clock=12), good=False, outcome='Máy sập nguồn giữa đường, phải mượn điện thoại gọi bưu cục, mất 12 phút.')))],
         default='charge'),
    dict(id='DE-URGENT', title='Chị Hạnh cần chạy gấp túi thuốc', emoji='💊', npc=6, min_day=3, tone='gentle',
         text='Bộ đàm rè rè: “Phòng khám cần gấp túi thuốc cho bé sốt ở chung cư, em chạy giúp chị được không? Thưởng 15 xu.”',
         options=[dict(id='take', label='Nhận chạy gấp', hint='+15 phút, +15 xu', effects=dict(clock=15, money=15, xp=6), good=True,
                       outcome='Túi thuốc tới tay mẹ bé kịp lúc. Chị Hạnh ghi tên bạn vào bảng khen.'),
                  dict(id='pass', label='Nhường đồng nghiệp vì đang có đơn sắp trễ',
                       outcome='Chị Hạnh: “Ok em, chị gọi Na.” Đơn của bạn vẫn kịp giờ.')],
         default='pass'),
    dict(id='DE-BUMP', title='Va quẹt nhẹ ở ngã tư', emoji='💥', npc=6, min_day=3, tone='tense',
         text='Một chiếc xe đạp điện lấn làn quẹt vào xe bạn: gương xe bạn gãy, đèn xe người kia bể.',
         options=[dict(id='talk', label='Dừng lại hỏi han, chụp ảnh, mỗi bên tự lo phần mình', hint='+6 phút', effects=dict(clock=6), good=True,
                       outcome='Hai bên bình tĩnh nói chuyện, ai sửa xe nấy, bắt tay ra về.'),
                  dict(id='pay', label=f'Đền luôn {cf.comp(12)} xu cho êm chuyện', effects=dict(money=-cf.comp(12), clock=3),
                       outcome='Người kia cầm tiền đi luôn, dù lỗi chưa chắc ở bạn.'),
                  dict(id='flee', label='Chạy luôn cho kịp đơn', luck=dict(
                      p=0.5, win=dict(good=False, outcome='Không ai đuổi theo, nhưng áo đồng phục in logo rõ to — lòng cứ thấp thỏm.'),
                      lose=dict(effects=dict(money=-25, review=[1, 'Shipper quẹt xe người ta rồi bỏ chạy!']), good=False,
                                outcome='Người ta chụp biển số gửi bưu cục. Bạn bị phạt 25 xu và một lời phàn nàn công khai.')))],
         default='talk'),
    dict(id='DE-THREAT', title='Khách dọa 1 sao đòi miễn phí ship', emoji='😤', npc=1, min_day=2, tone='tense',
         text='Anh Tùng nhắn: “Phí ship gì mà cao vậy? Không miễn phí thì anh đánh giá 1 sao cho biết.”',
         options=[dict(id='explain', label='Lễ phép giải thích phí do app tính, không tự ý bớt', effects=dict(review=[4, 'Shipper giải thích rõ ràng, lễ phép. Ok.']), good=True,
                       outcome='Anh Tùng đọc lại bảng phí, thôi không dọa nữa.'),
                  dict(id='pay', label='Tự bù 8 xu phí ship cho khách vui', effects=dict(money=-8, review=[5, 'Được freeship, 5 sao!']),
                       outcome='Được 5 sao, nhưng tiền túi mình bay 8 xu — và khách quen luôn kiểu dọa.'),
                  dict(id='argue', label='Cãi lại cho ra lẽ', effects=dict(review=[1, 'Shipper cãi tay đôi với khách.']), good=False,
                       outcome='Hai bên nhắn qua lại gay gắt, khách đánh 1 sao thật.')],
         default='explain'),
    dict(id='DE-NOGAS', title='Cây xăng mất điện', emoji='🔌', npc=6, min_day=2, tone='gentle', mods=SUNNY + ('rain', 'storm'),
         text='Tin nhắn nhóm tài xế: “Cây xăng Gió Lộng mất điện tới 18:00, bơm không chạy nha mọi người!”',
         options=[dict(id='bottle', label='Mua sẵn 20% xăng chai ven đường', hint='8 xu', effects=dict(money=-8, fuel=20, mark='nogas'), good=True,
                       outcome='Đổ sẵn 20% xăng chai, chạy yên tâm tới tối.'),
                  dict(id='wait', label='Bình còn đủ, chạy tiếp', effects=dict(mark='nogas'),
                       outcome='Nhớ canh xăng: cây xăng chỉ bơm lại sau 18:00.')],
         default='wait'),
    # --- order-bound ------------------------------------------------------------------
    dict(id='DE-DOG', title='Chó dữ trước cổng', emoji='🐕', npc=4, need_mark='ctx', tone='tense',
         text='Con chó vện to đùng đứng chắn cổng, nhe răng sủa ầm, không cho ai bước vào.',
         options=[dict(id='call', label='Đứng ngoài gọi khách ra giữ chó', hint='+4 phút', effects=dict(clock=4, dog='ok'), good=True,
                       outcome='Khách chạy ra xích chó lại: “Xin lỗi nha, nó dữ vậy chứ hiền.”'),
                  dict(id='treat', label='Mua cái bánh bao dỗ chó', hint='2 xu', effects=dict(money=-2, clock=2),
                       luck=dict(p=0.6, win=dict(effects=dict(dog='ok'), outcome='Chó ăn xong ngoắt đuôi tránh đường.'),
                                 lose=dict(effects=dict(dog='ok', clock=6), outcome='Chó ăn xong vẫn sủa, rốt cuộc vẫn phải gọi khách ra.'))),
                  dict(id='rush', label='Liều dắt xe đi thẳng vào', hint='Nhanh nhưng nguy hiểm',
                       luck=dict(p=0.5, win=dict(effects=dict(dog='ok'), good=False, outcome='Chó chỉ sủa theo, hú hồn.'),
                                 lose=dict(effects=dict(dog='bite', clock=10), good=False,
                                           outcome='Chó lao tới, bạn loạng choạng té xe, hàng văng xuống đất.')))],
         default='call'),
    dict(id='DE-BOMB', title='Khách “bom hàng”', emoji='📵', npc=2, need_mark='ctx', tone='tense',
         text='Đơn thu hộ tới nơi: khách không bắt máy, người nhà nói không ai đặt, không nhận.',
         options=[dict(id='return', label='Chụp ảnh, ghi lý do lên app, hoàn hàng về bưu cục', hint='Nhận phí giao lần đầu', effects=dict(bomb='return'), good=True,
                       outcome='Làm đúng thủ tục hoàn. Shop bị bom nhưng có ảnh, không ai trách bạn.'),
                  dict(id='discount', label=f'Nhắn được khách, tự bớt {DISCOUNT} xu để khách chịu nhận', hint=f'Túi COD hụt {DISCOUNT} xu, tự bù khi nộp',
                       effects=dict(bomb='discount'), outcome='Khách đồng ý nhận vì được bớt — tiền bớt là tiền túi của bạn.'),
                  dict(id='argue', label='Đứng lì ép khách phải nhận',
                       luck=dict(p=0.3, win=dict(effects=dict(bomb='accept'), outcome='Khách miễn cưỡng ra nhận, mặt nặng mày nhẹ.'),
                                 lose=dict(effects=dict(bomb='refuse', review=[1, 'Shipper đứng lì trước cửa ép nhận hàng.']), good=False,
                                           outcome='Khách gọi tổng đài phàn nàn. Hàng vẫn phải hoàn, còn mất luôn phí giao.')))],
         default='return'),
    dict(id='DE-MOVED', title='Khách đổi địa chỉ phút chót', emoji='📍', npc=2, need_mark='ctx', tone='gentle',
         text='Khách nhắn: “Mình mới chuyển chỗ, giao qua địa chỉ mới giúp nha!”',
         options=[dict(id='accept', label=f'Nhận đổi địa chỉ, app cộng phụ phí {REDIRECT_FEE} xu', effects=dict(moved='accept'), good=True,
                       outcome='Cập nhật địa chỉ mới trên app, khách cảm ơn rối rít.'),
                  dict(id='meet', label='Hẹn khách ra lại địa chỉ cũ nhận hàng',
                       luck=dict(p=0.5, win=dict(effects=dict(moved='meet', clock=10), outcome='Khách chạy xe ra lấy, mất 10 phút chờ.'),
                                 lose=dict(effects=dict(moved='nofee'), good=False,
                                           outcome='Khách không ra được, đành chạy qua địa chỉ mới mà không có phụ phí.'))),
                  dict(id='refuse', label='Từ chối, hoàn đơn về bưu cục', effects=dict(moved='refuse'),
                       outcome='Đơn hoàn về, khách phải đặt lại từ đầu.')],
         default='accept'),
    dict(id='DE-FLAT', title='Xẹp bánh giữa đường', emoji='💥', npc=6, need_mark='ctx', tone='tense',
         text='Bánh sau xẹp lép, xe lắc lư. Lốp mòn quá rồi.',
         options=[dict(id='patch', label='Dắt bộ tới tiệm vá gần nhất', hint='6 xu, +15 phút', effects=dict(money=-6, clock=15, tyre=60), good=True,
                       outcome='Chú thợ vá ruột, bơm căng. Lốp tạm ổn, nhớ bảo dưỡng sớm.'),
                  dict(id='mobile', label='Gọi thợ vá lưu động tới tận nơi', hint='14 xu, +6 phút', effects=dict(money=-14, clock=6, tyre=100),
                       outcome='Thợ tới nhanh, thay ruột mới. Tốn tiền nhưng giữ được giờ giao.'),
                  dict(id='ride', label='Chạy tiếp bánh xẹp cho kịp đơn', hint='Hư vành, hàng dễ vỡ bị xóc',
                       effects=dict(tyre=0, mark='rim', rimhit=1), good=False,
                       outcome='Xe cà giật suốt đoạn đường, vành móp — lần bảo dưỡng tới tốn thêm tiền.')],
         default='patch'),
    dict(id='DE-CHAIN', title='Tuột sên giữa đường', emoji='⛓️', npc=6, need_mark='ctx', tone='tense',
         text='Sên mòn chùng quá, tuột khỏi nhông. Xe đứng im, hàng vẫn còn trên xe.',
         options=[dict(id='refit', label='Tự lắp sên lại bên lề', hint='+8 phút, sên tạm 25%', effects=dict(clock=8, chain=25),
                       outcome='Tay lem nhớt nhưng sên vào lại được. Nhớ ghé tiệm Chú Bảy thay sên mới.'),
                  dict(id='push', label='Dắt xe vào tiệm sửa gần nhất thay sên mới', hint='8 xu, +15 phút, sên 100%',
                       effects=dict(money=-8, clock=15, chain=100), good=True,
                       outcome='Thợ thay sên mới, căng vừa tay. Xe chạy êm hẳn.'),
                  dict(id='mobile', label='Gọi thợ lưu động tới thay sên tại chỗ', hint='14 xu, +5 phút, sên 100%',
                       effects=dict(money=-14, clock=5, chain=100),
                       outcome='Thợ tới nhanh, thay sên tại chỗ. Tốn tiền nhưng giữ được giờ giao.')],
         default='refit'),
]


def _who(t: dict) -> str:
    return PEOPLE[int(t['npc'].rsplit('_', 1)[1]) - 1][0]


def _flat(c: dict, d: dict) -> bool:
    if d['tyre'] >= TYRE_FLAT_AT:
        return False
    if d['tyre'] <= 0:
        return True
    return kit.rng(ID, 'flat', c['day'], d['km'], d['tyre']).randrange(100) < (TYRE_FLAT_AT - d['tyre']) * 3


def _fire(s: dict, c: dict, sid: str, t: dict | None = None) -> None:
    """Open an order-bound surprise right now."""
    desk = _data(c)['desk']
    x = kit.desk_script(EVENTS, sid)
    desk['seq'] += 1
    desk['ev'] = dict(id=f'desk-{desk["seq"]}', script=sid, day=c['day'], at='between')
    if t is not None:
        desk['ev']['task'] = t['id']
    kit.log(s, c, 'surprise', f'{x["emoji"]} {x["title"]}', kit.npc_id(ID, x.get('npc', 0)), desk['ev']['id'])


def _ev_task(c: dict) -> dict | None:
    ev = _data(c)['desk']['ev']
    tid = ev.get('task') if ev else None
    return next((t for t in c['tasks'] if t['id'] == tid and t['status'] not in DONE), None) if tid else None


def _hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    t = _ev_task(c)
    if key == 'clock':
        _clock(d, int(v))
        return None
    if key == 'fuel':
        add = min(int(v), 100 - d['fuel'])
        d['fuel'] += add
        return f'Bình xăng lên {d["fuel"]}%.' if add else None
    if key in PARTS:
        _set_part(d, key, int(v))
        return None
    if key in ('wrap', 'soak'):
        wrapped, soaked = [], []
        for x in _open(c):
            r, n = x['run'], x['needs']
            if not r['loaded'] or n['kind'] != 'parcel' or 'rainbag' in r['packed'] or r['wet']:
                continue
            if key == 'wrap' and kit.stock(c, 'rainbag') > 0:
                kit.take(c, 'rainbag', 1)
                r['packed'].append('rainbag')
                wrapped.append(n['item'].lower())
            else:
                r['wet'] = True
                if n['paper']:
                    r['_broken'] = True
                soaked.append(n['item'].lower())
        out = []
        if wrapped:
            out.append('Đã trùm túi cho ' + ', '.join(wrapped) + '.')
        if soaked:
            out.append('Bị ướt: ' + ', '.join(soaked) + '.')
        return ' '.join(out) or None
    if key == 'rimhit':
        hurt = []
        for x in _open(c):
            r, n = x['run'], x['needs']
            if r['loaded'] and n['fragile'] and not r['_broken']:
                r['_broken'] = True
                hurt.append(n['item'].lower())
            elif r['loaded'] and n['kind'] == 'food' and n.get('soup') and not r['spilled']:
                r['spilled'] = True
                hurt.append(n['item'].lower())
        return ('Xóc quá: ' + ', '.join(hurt) + ' bị hư.') if hurt else None
    if t is None:
        return None
    r, n = t['run'], t['needs']
    if key == 'dog':
        r['dog'] = v
        if v == 'bite':
            if n['kind'] == 'food':
                r['spilled'] = True
                return 'Túi đồ ăn đổ tháo.'
            if n['fragile']:
                r['_broken'] = True
            return None
        return None
    if key == 'moved':
        r['moved'] = v
        d['stats']['moved'] += 1
        if v in ('accept', 'nofee'):
            r['dest'] = t['_moved']
            return f'Địa chỉ mới: {NODES[r["dest"]]["name"]} — thêm vào lộ trình nhé.'
        if v == 'refuse':
            r['outcome'] = 'failed'
            d['failed'] += 1
            d['day_failed'] += 1
            kit.metric(c, 'deliveries_failed')
            kit.complete(s, c, t, 0, f'Đơn {n["item"].lower()} bị hoàn vì không nhận giao tới địa chỉ mới.', status='cancelled')
            return _score(s, c, t, clean=None).strip() or None
        return None
    if key == 'bomb':
        r['bomb'] = v
        if v == 'discount':
            r['discount'] = DISCOUNT
            return f'Giao như bình thường, khách trả {n["cod"] - DISCOUNT} xu tiền hàng.'
        if v in ('return', 'refuse'):
            fee = 4 if v == 'return' else 0
            r['outcome'] = 'failed'
            d['failed'] += 1
            d['day_failed'] += 1
            kit.metric(c, 'deliveries_failed')
            kit.complete(s, c, t, fee, f'Khách không nhận {n["item"].lower()} (bom hàng), hoàn về bưu cục.', status='cancelled')
            return (f'Phí giao lần đầu +{fee} xu.' if fee else '') + _score(s, c, t, clean=None)
        return None
    return None


def _decide(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    kit.need(d['desk']['ev'] is not None, 'Không có chuyện nào đang chờ quyết.')
    return kit.desk_choose(s, c, ID, d['desk'], EVENTS, p.get('option'), hook=_hook)


def _close_desk(s: dict, c: dict, d: dict) -> str | None:
    return kit.desk_close(s, c, ID, d['desk'], EVENTS, _hook)


def _desk_view(c: dict) -> dict:
    d = _data(c)
    view = kit.desk_public(d['desk'], EVENTS, ID)
    ev = view['ev']
    t = _ev_task(c)
    if ev and t is not None:
        ev['task'] = t['id']
        ev['npc'] = t['npc']
        n = t['needs']
        if ev['script'] == 'DE-MOVED':
            ev['text'] = f'{_who(t)} nhắn: “Mình mới chuyển qua {NODES[t["_moved"]]["name"]}, giao {n["item"].lower()} qua đó giúp nha!”'
        elif ev['script'] == 'DE-BOMB':
            ev['text'] = f'Đơn thu hộ {n["cod"]} xu ({n["item"].lower()}): {_who(t)} không bắt máy, người nhà nói không ai đặt, không nhận.'
        elif ev['script'] == 'DE-DOG':
            ev['text'] = f'Cổng {NODES[_dest(t)]["name"]}: con chó vện to đùng nhe răng sủa ầm, không cho ai bước vào giao {n["item"].lower()}.'
    return view
