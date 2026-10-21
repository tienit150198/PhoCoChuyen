"""Plugin careers (v0.4).

Each module in this package describes one playable job: its content, task
factory, rules and public projection. The engine owns money, reviews, turns and
validation; a plugin can only change its own task/ext data through `kit`.
Modules listed in ORDER but not present on disk are skipped, so careers can be
added one at a time without touching the engine.
"""
from __future__ import annotations
import os
from importlib import import_module

ORDER = (
    'restaurant', 'cafe_bakery', 'florist', 'grocery', 'repair', 'farm', 'delivery',
    'homestay', 'pet_care', 'salon', 'corp_accounting', 'tax_payroll', 'group_accounting',
    'clothing', 'pet_shop', 'tra_da',
    'fruit', 'garbage', 'drain',   # street trades: fruit stall, rubbish round, drain cleaning
    'homemaker',                   # nội trợ: a home helper in a three-generation family
    'ice_cream',                   # bán kem: cô Hiền's ice-cream corner by the school gate
    'nail',                        # tiệm nail: chị Diệp's little nail shop on the street
    'pagoda',                      # thầy chùa: a young monk at chùa Gió Lành by the river landing
    'pho',                         # bán phở: bác Lâm's phở shop under the old banyan, the broth pot on all day
    'com',                         # bán cơm: dì Bảy's broken-rice stall at the mouth of the market
    'photobooth',                  # photobooth: chị Lam's Tiệm ảnh Tách Tách by the night market
    'giupviec',                    # giúp việc theo giờ: cô Mai's Nhà Thơm team, cleaning clients' flats by the hour
    'naucom',                      # nấu cơm gia đình: a hired home cook, one family's meal a day
    'babysitter',                  # bảo mẫu: a day minding one family's child for cô Tâm's sitting service
    'library',                     # thư viện – lưu trữ: cô Nguyệt's ward library and the ward's records store
    'pilot', 'flight_attendant',
    'oil',                         # thợ dầu khí: an offshore technician on giàn Hải Âu, 14-day hitches by helicopter
    'hr_admin', 'secretary', 'it_helpdesk',   # Công ty CP Cánh Diều: HR, the director's secretary, IT helpdesk
    'railway',                     # gác chắn đường sắt: the level crossing at Bến Mây and the track patrol (Xí nghiệp Đường sắt Sông Mây)
    'nurse',                       # điều dưỡng: a day shift on the medical ward of Bệnh viện phường Lá Sen
    'lighthouse',                  # gác hải đăng: keeper of đèn biển Hòn Gió, an island light off bến cá Cửa Lở
    'rescue',                      # trực tổng đài cứu hộ: the hotline of Tổng đài Cứu hộ phường Mây (fire, flood, accidents, lifts, pets, medical)
    'lifeguard',                   # cứu hộ hồ bơi: the high chair at Hồ bơi Sóng Xanh, the ward's public pool
    'police',                      # công an phường: community police at Công an phường Mây (papers, lost and found, mediation, patrols)
    'zpop',                        # bán album ZPOP: chị Thơ's Tiệm album Mây Pop on Phố chợ (BLANKPINK, 7GIÓ, KIWIZ; all fictional)
    'art_studio', 'lawyer', 'laundry', 'post_office',
    'customs',                     # hải quan: Chi cục Hải quan cửa khẩu Bến Mây (lanes, smuggling, duties, controls; org ladder 'hq')
    'hotel',                       # khách sạn: Khách sạn Sông Mây, salaried shift staff rotating desk, rooms, laundry, breakfast, repairs, decor
    'banquet',                     # nhà hàng tiệc: Nhà hàng tiệc Hồng Mây, salaried kitchen (phụ bếp → đầu bếp) or event-hall shifts
    'reception',                   # lễ tân: the front desk of Khách sạn Hoa Sứ (six rooms), its own ca thử việc, desk oddities with lasting consequences
    'teller',                      # ngân hàng: Quầy số 3 at the Bến Chợ office of Ngân hàng Phố (NPC customers; never the player's own bank)
    'restore',                     # thợ phục chế: Xưởng phục chế Hồn Xưa, old and broken pieces with awkward customer demands; players' things via Phố dịch vụ
    'research',                    # viện nghiên cứu: Viện nghiên cứu Sông Mây, salaried shifts on seeds, recipes or inventions; player research orders (game/research_lab.py)
    'radio',                       # đài phát thanh: Đài phát thanh Sóng Mây, salaried phát thanh viên (DJ after probation); players' ads and songs on the town ticker
    'moto',                        # sửa xe máy: Tiệm sửa xe Út Lanh, step-graded tickets (lốp, nhớt, bugi, sên, phanh, đèn, ắc quy, xe ngập); players' bikes serviced via Phố dịch vụ
    'vet',                         # bác sĩ thú y: Phòng khám Thú y Cỏ May, salaried, step-graded cases (tiêm, ve, ngộ độc, tắc tiểu, mổ); players' pets examined via Phố dịch vụ
    'kol',                         # nhà sáng tạo nội dung: Studio Hẻm Xanh, step-graded brand deals (brief, quay, nhạc miễn phí bản quyền, bình luận, báo cáo số thật)
    'singer',                      # ca sĩ phòng trà: Phòng trà Mây Chiều, salaried, step-graded sets (chọn bài, khởi động, thử âm, sự cố, lời chúc)
    'actor',                       # diễn viên: Hãng phim Bến Mây, salaried, step-graded scenes (thoại, vị trí, nối cảnh, đạo diễn, hành động an toàn, họp báo)
    'tuning',                      # độ xe: Xưởng độ xe Tư Pít-tông, step-graded build tickets (bảng độ trong ngân sách, đồ đúng luật, dyno, đo tiếng ồn, thẻ thông số); players' vehicles tuned via Phố dịch vụ
)
# Development filter: MNL_CAREERS=restaurant,florist loads only those plugins.
_ONLY = {x.strip() for x in os.environ.get('MNL_CAREERS', '').split(',') if x.strip()}
PLUGINS = {}
for _name in ORDER:
    if _ONLY and _name not in _ONLY:
        continue
    try:
        _module = import_module(f'.{_name}', __name__)
    except ModuleNotFoundError as error:
        if error.name == f'{__name__}.{_name}':
            continue
        raise
    PLUGINS[_module.SPEC['id']] = _module
IDS = tuple(PLUGINS)


def spec(career: str) -> dict:
    return PLUGINS[career].SPEC


def get(career: str):
    return PLUGINS.get(career)
