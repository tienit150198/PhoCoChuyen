"""Hành trình: one young person, one small neighbourhood, many workplaces.

A root `s['journey']` turns the collection of careers into one life story:

* chapters with short story beats; each chapter's goals are read from the real
  save (tasks done, levels, places worked, office contract…) and completing a
  chapter unlocks the next workplaces;
* a personal wallet ("Ví của bạn") that pays daily living costs, separate from
  each workplace's own fund (the career `money`, which keeps its ledger);
* upkeep for every started workplace that sits idle on a day, pausing and
  reopening, withdrawals to the wallet and investments back into a fund;
* a maturity level and skills derived from the careers, and titles.

Server authoritative: the client only renders `public()` and sends `jr_*`
commands. Rules only bite when `story` is on: new sessions on a real server
and imported saves. States from `engine.new_state()` (tests, tools) keep every
workplace open and no living costs, so plugin tests can play any career.
"""
from __future__ import annotations

import copy
from .jsoncopy import tree_copy
import hashlib
import random

from .content import CAREERS, CAREER_META
from . import archive as ar
from . import certificates as ct
from . import bank as bk   # 🏦 Ngân hàng Phố (game/bank.py)

VERSION = 1
START_WALLET = 60
RESERVE = 80          # a fund keeps this much after a withdrawal
REOPEN_FEE = 15
BREADTH_XP = 80       # maturity bonus for every workplace you really worked at
LIVING = {1: 10, 2: 12, 3: 14, 4: 16, 5: 18, 6: 20, 7: 20}
UPKEEP = {'cozy': 4, 'sunny': 7, 'garden': 11}
MODES = (('calm', .25), ('normal', .55), ('festival', .20))
HISTORY_KINDS = ('living', 'upkeep', 'draw', 'invest', 'salary', 'reopen', 'incident', 'life', 'study', 'backdoor', 'bank')
NEWS_KINDS = ('chapter', 'titles')

CH_UNLOCKS = {
    # New players get every storefront at once; the service places follow after the first day.
    1: ('milk_tea', 'grocery', 'delivery', 'cafe_bakery', 'florist', 'mother_baby', 'restaurant'),
    2: ('pet_care', 'salon', 'repair', 'farm', 'homestay'),
    3: ('clothing', 'pet_shop', 'tra_da'),
    4: ('customer_care', 'pharmacy', 'tour_guide', 'teacher', 'accounting'),
    5: ('corp_accounting', 'tax_payroll'),
    6: ('group_accounting',),
}
OFFICE = ('corp_accounting', 'tax_payroll', 'group_accounting')

CAST = {
    'ba_tam': dict(name='Bà Tám', emoji='👵', role='Chủ nhà trọ'),
    'co_ba': dict(name='Cô Ba', emoji='👩‍🦳', role='Tạp hóa đầu hẻm'),
    'co_lua': dict(name='Cô Lụa', emoji='👩‍💼', role='Tổ trưởng tổ dân phố'),
    'anh_khoa': dict(name='Anh Khoa', emoji='🧑‍💻', role='Hàng xóm làm văn phòng'),
    'chu_tu': dict(name='Chú Tư', emoji='👨‍🔧', role='Tiệm sửa đồ'),
    'be_ti': dict(name='Bé Tí', emoji='👦', role='Học sinh lớp 9'),
    'ba_sau': dict(name='Bà Sáu', emoji='🧓', role='Hàng xóm lâu năm'),
}


def _line(who, text):
    return dict(who=who, text=text)


CHAPTERS = [
    dict(n=1, title='Chuyển tới khu phố', art='🏘️',
         tagline='Một căn gác nhỏ, một con hẻm lạ và những người hàng xóm đầu tiên.',
         intro=[_line('ba_tam', 'Phòng trên gác đây cháu. Cửa sổ nhìn ra hẻm, sáng nào cũng nghe tiếng rao bánh mì.'),
                _line('ba_tam', 'Tiền phòng với cơm nước bà tính theo ngày, cháu đi làm rồi trả dần, đừng lo.'),
                _line('co_ba', 'Mới tới hả? Đầu hẻm đang thiếu người: tiệm trà sữa, tạp hóa của cô, rồi bên giao hàng. Thử một chỗ đi con.')],
         outro=[_line('co_ba', 'Ngày đầu mà làm tới nơi tới chốn vậy là cô yên tâm rồi.'),
                _line('ba_tam', 'Tối nay bà nấu canh chua, xuống ăn chung cho vui nghe.'),
                _line('anh_khoa', 'Nghe nói có người mới về hẻm? Tiệm bánh, tiệm hoa, quán mì đầu phố đều đang cần người phụ đó.'),
                _line('chu_tu', 'Tiệm chú đang cần người phụ. Tay chân nhanh nhẹn vậy, ghé đây chú chỉ nghề cho.'),
                _line('ba_sau', 'Mèo nhà bà cũng cần người tắm, salon đầu dốc thì thiếu thợ. Con ghé thử nghe.')],
         goals=[dict(id='days', goal=1, text='Khép lại ngày làm việc đầu tiên'),
                dict(id='tasks', goal=3, text='Hoàn thành 3 việc cho hàng xóm')]),
    dict(n=2, title='Hàng xóm quen mặt', art='🥐',
         tagline='Mỗi nơi làm việc là thêm vài gương mặt nhớ tên bạn.',
         intro=[_line('anh_khoa', 'Tiệm bánh, tiệm hoa, tiệm mẹ và bé, quán mì cay… chỗ nào cũng mừng khi có thêm một đôi tay.'),
                _line('co_lua', 'Cô là tổ trưởng tổ dân phố. Làm ở vài chỗ khác nhau là mau quen người lắm.'),
                _line('ba_tam', 'Tiền lời ở tiệm thì nhớ rút về ví mà lo cơm nước. Đừng để sổ tiền phòng đỏ chữ nghe.'),
                _line('be_ti', dict(male='Anh ơi, mai anh ghé tiệm bánh không? Em mê bánh su kem ở đó lắm!',
                                    female='Chị ơi, mai chị ghé tiệm bánh không? Em mê bánh su kem ở đó lắm!',
                                    none='Mai ghé tiệm bánh không? Em mê bánh su kem ở đó lắm!'))],
         outro=[_line('co_lua', 'Mới mấy hôm mà đi đâu trong hẻm cũng có người nhắc tên cháu rồi.')],
         goals=[dict(id='places', goal=2, text='Làm việc ở 2 nơi khác nhau'),
                dict(id='tasks', goal=10, text='Hoàn thành 10 việc'),
                dict(id='draw', goal=1, text='Rút tiền lời về ví một lần')]),
    dict(n=3, title='Có nghề trong tay', art='🛠️',
         tagline='Làm nhiều thì tay quen, mắt tinh, lòng cũng vững.',
         intro=[_line('chu_tu', 'Nghề nào cũng vậy, làm đi làm lại thì tay quen, mắt tinh.'),
                _line('ba_sau', 'Tiệm thú cưng, salon, nông trại trên đồi, homestay trên dốc… giờ ai cũng biết mặt con rồi.'),
                _line('ba_tam', 'Chợ dạo này lên giá, tiền cơm bà nhích thêm chút. Nhớ giữ ví cho đều nghe cháu.')],
         outro=[_line('chu_tu', 'Giờ thì có nghề trong tay thật rồi đó.'),
                _line('co_lua', 'Phường đang cần người cẩn thận ở mấy chỗ: nhà thuốc, trạm chăm sóc khách hàng, lớp học… Cô giới thiệu cháu nha.')],
         goals=[dict(id='level', goal=3, text='Đạt cấp 3 ở một nơi làm việc'),
                dict(id='clean', goal=3, text='Giữ ví không nợ 3 ngày sống liền'),
                dict(id='places', goal=3, text='Làm việc ở 3 nơi khác nhau')]),
    dict(n=4, title='Được tin cậy', art='🤝',
         tagline='Có những việc người ta chỉ giao cho người mình tin.',
         intro=[_line('co_lua', 'Mấy chỗ này cần người cẩn thận, nói năng rõ ràng. Cô tin cháu làm được.'),
                _line('anh_khoa', 'Lớp học Mầm Nắng đang tuyển người. Phải nộp hồ sơ, phỏng vấn đàng hoàng đó.'),
                _line('anh_khoa', 'Mà hồ sơ giờ ghi được một dòng rất thật: có kinh nghiệm ở một nghề khác trong phố.')],
         outro=[_line('co_lua', 'Giờ đi đâu trong phố cũng có người gửi lời chào cháu.'),
                _line('anh_khoa', 'Công ty mình với bên dịch vụ thuế đang tuyển. Kinh nghiệm ở phố ghi vào CV được hết, thử không?')],
         goals=[dict(id='places', goal=5, text='Làm việc ở 5 nơi khác nhau'),
                dict(id='titles', goal=6, text='Có 6 danh hiệu'),
                dict(id='mature', goal=5, text='Đạt trưởng thành cấp 5')]),
    dict(n=5, title='Bước vào văn phòng', art='💼',
         tagline='Một chiếc bàn làm việc, một tấm thẻ nhân viên và đồng lương đầu tiên.',
         intro=[_line('anh_khoa', 'Văn phòng khác tiệm nhiều lắm: tin tuyển dụng, CV, thư ứng tuyển rồi phỏng vấn.'),
                _line('anh_khoa', 'Nhớ chọn dòng “Có kinh nghiệm ở một nghề khác trong phố” nha. Người ta kiểm tra đó, nhưng mình làm thật mà.'),
                _line('ba_tam', 'Đi làm văn phòng thì lương về ví. Nhận lương rồi nhớ để dành tiền phòng nghe cháu.')],
         outro=[_line('anh_khoa', 'Chào đồng nghiệp mới! Lương về rồi, tối nay đi ăn chè không?'),
                _line('co_lua', 'Bên Sông Hồng Group kia cầu đang tìm người giỏi sổ sách. Cô nghe người ta nhắc tên cháu đó.')],
         goals=[dict(id='office_hired', goal=1, text='Được nhận vào làm ở một văn phòng'),
                dict(id='office_days', goal=3, text='Đi làm đủ 3 ngày ở văn phòng'),
                dict(id='clean', goal=5, text='Giữ ví không nợ 5 ngày sống liền')]),
    dict(n=6, title='Người của khu phố', art='🏮',
         tagline='Từ một căn gác lạ tới một nơi để gọi là nhà.',
         intro=[_line('ba_sau', 'Hồi con mới tới, con chỉ xách có cái ba lô. Giờ cả hẻm này ai cũng quen con.'),
                _line('co_lua', 'Cuối năm phố làm tiệc. Cô muốn mời cháu lên nói vài câu, vì cháu đã giúp nhiều nơi lắm.'),
                _line('co_ba', 'Cứ làm theo nhịp của mình thôi con. Người ta nhớ mình vì mình tử tế, đâu phải vì mình vội.')],
         outro=[_line('co_lua', 'Từ hôm nay, cháu là người của khu phố này.'),
                _line('ba_tam', 'Phòng trên gác bà vẫn để đèn. Đi đâu thì đi, nhớ đường về nghe cháu.'),
                _line('co_ba', 'Ly trà đầu tiên cháu pha ở phố, cô vẫn còn nhớ đó.')],
         goals=[dict(id='places', goal=8, text='Làm việc ở 8 nơi khác nhau'),
                dict(id='mature', goal=8, text='Đạt trưởng thành cấp 8'),
                dict(id='titles', goal=15, text='Có 15 danh hiệu')]),
]
CHAPTER_INDEX = {ch['n']: ch for ch in CHAPTERS}
TRACKED_GOALS = ('clean', 'draw')   # need play after the journey starts; fast-forward skips them
LAST = len(CHAPTERS)

LEVEL_NAMES = ['Người mới tới', 'Làm quen', 'Tập việc', 'Quen tay', 'Vững vàng', 'Đáng tin cậy',
               'Được nhờ cậy', 'Chỗ dựa của phố', 'Người dẫn đường', 'Trưởng thành']
MAX_LEVEL = 30

# Per-workplace skill weights (ids from employment.STRENGTHS).
SKILL_WEIGHTS = {
    'milk_tea': dict(careful=1, creative=1, calm=1),
    'grocery': dict(numbers=2, communication=1, careful=1),
    'delivery': dict(calm=2, careful=1, communication=1),
    'cafe_bakery': dict(creative=2, careful=1, patience=1),
    'florist': dict(creative=2, communication=1, patience=1),
    'mother_baby': dict(communication=2, careful=1, creative=1),
    'restaurant': dict(calm=2, teamwork=1, careful=1),
    'pet_care': dict(patience=2, calm=1, careful=1),
    'salon': dict(creative=2, communication=1, patience=1),
    'repair': dict(careful=2, tech=1, learning=1),
    'farm': dict(patience=2, learning=1, careful=1),
    'homestay': dict(communication=2, teamwork=1, numbers=1),
    'customer_care': dict(communication=2, calm=2, patience=1),
    'pharmacy': dict(careful=3, calm=1),
    'tour_guide': dict(communication=2, teamwork=1, learning=1),
    'teacher': dict(patience=2, communication=2, creative=1),
    'accounting': dict(numbers=2, careful=2),
    'corp_accounting': dict(numbers=2, careful=1, tech=1),
    'tax_payroll': dict(numbers=2, tech=1, careful=1),
    'group_accounting': dict(numbers=2, teamwork=1, tech=1, learning=1),
}
SKILL_STEPS = (0, 6, 18, 40, 75, 120, 180)

TITLE_CATS = [('story', 'Câu chuyện'), ('general', 'Hành trình'), ('career', 'Nghề'), ('skill', 'Kỹ năng'),
              ('money', 'Tiền bạc'), ('secret', 'Bí mật')]


def _t(tid, cat, emoji, name, desc, check, secret=False):
    return dict(id=tid, cat=cat, emoji=emoji, name=name, desc=desc, check=check, secret=secret)


TITLES = [
    _t('st_newcomer', 'story', '🏠', 'Hàng xóm mới', 'Xong chương 1: những ngày đầu ở khu phố.', lambda x: x['done'] >= 1),
    _t('st_familiar', 'story', '👋', 'Người quen mặt', 'Xong chương 2: hàng xóm đã nhớ tên bạn.', lambda x: x['done'] >= 2),
    _t('st_skilled', 'story', '🛠️', 'Có nghề trong tay', 'Xong chương 3: tay đã quen việc.', lambda x: x['done'] >= 3),
    _t('st_trusted', 'story', '🤝', 'Người được tin cậy', 'Xong chương 4: được giao những việc cần sự cẩn thận.', lambda x: x['done'] >= 4),
    _t('st_office', 'story', '💼', 'Dân văn phòng', 'Xong chương 5: có tấm thẻ nhân viên đầu tiên.', lambda x: x['done'] >= 5),
    _t('st_local', 'story', '🏮', 'Người của khu phố', 'Xong chương 6: khu phố đã là nhà.', lambda x: x['done'] >= 6),
    _t('g_first', 'general', '🌱', 'Việc đầu tiên', 'Hoàn thành việc đầu tiên ở khu phố.', lambda x: x['tasks'] >= 1),
    _t('g_tasks50', 'general', '💪', 'Chăm chỉ', 'Hoàn thành 50 việc.', lambda x: x['tasks'] >= 50),
    _t('g_tasks200', 'general', '🙌', 'Đôi tay không nghỉ', 'Hoàn thành 200 việc.', lambda x: x['tasks'] >= 200),
    _t('g_places3', 'general', '🧭', 'Thử nhiều nghề', 'Làm việc ở 3 nơi khác nhau.', lambda x: x['places'] >= 3),
    _t('g_places8', 'general', '🌈', 'Đa năng', 'Làm việc ở 8 nơi khác nhau.', lambda x: x['places'] >= 8),
    _t('g_places_all', 'general', '🗺️', 'Thuộc từng ngõ nghề', 'Làm việc ở mọi nơi trong phố.', lambda x: x['places'] >= x['all_places']),
    _t('g_mature5', 'general', '🌿', 'Vững vàng', 'Đạt trưởng thành cấp 5.', lambda x: x['mature'] >= 5),
    _t('g_mature10', 'general', '🌳', 'Trưởng thành', 'Đạt trưởng thành cấp 10.', lambda x: x['mature'] >= 10),
    _t('g_days30', 'general', '📅', 'Một tháng ở phố', 'Sống ở khu phố 30 ngày.', lambda x: x['life_days'] >= 30),
    _t('g_days100', 'general', '🗓️', 'Trăm ngày thương', 'Sống ở khu phố 100 ngày.', lambda x: x['life_days'] >= 100),
    # One per workplace, at level 3 there.
    _t('c_milk_tea', 'career', '🧋', 'Thợ pha trà sữa', 'Đạt cấp 3 ở tiệm trà sữa.', lambda x: x['lv'].get('milk_tea', 1) >= 3),
    _t('c_grocery', 'career', '🛒', 'Chủ quầy tạp hóa', 'Đạt cấp 3 ở tiệm tạp hóa.', lambda x: x['lv'].get('grocery', 1) >= 3),
    _t('c_delivery', 'career', '🛵', 'Shipper thuộc đường', 'Đạt cấp 3 ở chỗ giao hàng.', lambda x: x['lv'].get('delivery', 1) >= 3),
    _t('c_cafe_bakery', 'career', '☕', 'Barista buổi sớm', 'Đạt cấp 3 ở tiệm bánh và cà phê.', lambda x: x['lv'].get('cafe_bakery', 1) >= 3),
    _t('c_florist', 'career', '💐', 'Người cắm hoa', 'Đạt cấp 3 ở tiệm hoa.', lambda x: x['lv'].get('florist', 1) >= 3),
    _t('c_mother_baby', 'career', '🎁', 'Người gói quà khéo', 'Đạt cấp 3 ở tiệm mẹ và bé.', lambda x: x['lv'].get('mother_baby', 1) >= 3),
    _t('c_restaurant', 'career', '🍜', 'Đầu bếp mì cay', 'Đạt cấp 3 ở quán mì cay.', lambda x: x['lv'].get('restaurant', 1) >= 3),
    _t('c_pet_care', 'career', '🐾', 'Bạn của chó mèo', 'Đạt cấp 3 ở tiệm chăm sóc thú cưng.', lambda x: x['lv'].get('pet_care', 1) >= 3),
    _t('c_salon', 'career', '💇', 'Thợ tóc có nghề', 'Đạt cấp 3 ở salon tóc.', lambda x: x['lv'].get('salon', 1) >= 3),
    _t('c_repair', 'career', '🔧', 'Thợ sửa đồ tin cậy', 'Đạt cấp 3 ở tiệm sửa đồ.', lambda x: x['lv'].get('repair', 1) >= 3),
    _t('c_farm', 'career', '🌾', 'Nông dân đồi gió', 'Đạt cấp 3 ở nông trại.', lambda x: x['lv'].get('farm', 1) >= 3),
    _t('c_homestay', 'career', '🏡', 'Chủ nhà hiếu khách', 'Đạt cấp 3 ở homestay.', lambda x: x['lv'].get('homestay', 1) >= 3),
    _t('c_customer_care', 'career', '🎧', 'Người lắng nghe', 'Đạt cấp 3 ở trạm chăm sóc khách hàng.', lambda x: x['lv'].get('customer_care', 1) >= 3),
    _t('c_pharmacy', 'career', '💊', 'Người đọc nhãn kỹ', 'Đạt cấp 3 ở nhà thuốc.', lambda x: x['lv'].get('pharmacy', 1) >= 3),
    _t('c_tour_guide', 'career', '🧭', 'Người kể chuyện đường xa', 'Đạt cấp 3 khi dẫn đoàn du lịch.', lambda x: x['lv'].get('tour_guide', 1) >= 3),
    _t('c_teacher', 'career', '🍎', 'Người dạy tận tâm', 'Đạt cấp 3 ở lớp học.', lambda x: x['lv'].get('teacher', 1) >= 3),
    _t('c_accounting', 'career', '📒', 'Người giữ sổ gọn', 'Đạt cấp 3 ở góc sổ kế toán.', lambda x: x['lv'].get('accounting', 1) >= 3),
    _t('c_corp_accounting', 'career', '🧮', 'Kế toán vững tay', 'Đạt cấp 3 ở công ty Mây Tre Xanh.', lambda x: x['lv'].get('corp_accounting', 1) >= 3),
    _t('c_tax_payroll', 'career', '🧾', 'Người tính lương chuẩn', 'Đạt cấp 3 ở dịch vụ thuế và tiền lương.', lambda x: x['lv'].get('tax_payroll', 1) >= 3),
    _t('c_group_accounting', 'career', '🏢', 'Kế toán hợp nhất', 'Đạt cấp 3 ở Sông Hồng Group.', lambda x: x['lv'].get('group_accounting', 1) >= 3),
    # Skills at level 3.
    _t('k_careful', 'skill', '🔍', 'Mắt tinh', 'Kỹ năng cẩn thận, tỉ mỉ đạt mức 3.', lambda x: x['sk'].get('careful', 0) >= 3),
    _t('k_communication', 'skill', '💬', 'Nói dễ hiểu', 'Kỹ năng giao tiếp đạt mức 3.', lambda x: x['sk'].get('communication', 0) >= 3),
    _t('k_patience', 'skill', '🌱', 'Kiên nhẫn như đất', 'Kỹ năng kiên nhẫn đạt mức 3.', lambda x: x['sk'].get('patience', 0) >= 3),
    _t('k_numbers', 'skill', '🔢', 'Đầu óc con số', 'Kỹ năng số liệu đạt mức 3.', lambda x: x['sk'].get('numbers', 0) >= 3),
    _t('k_teamwork', 'skill', '🫶', 'Đồng đội tốt', 'Kỹ năng làm việc nhóm đạt mức 3.', lambda x: x['sk'].get('teamwork', 0) >= 3),
    _t('k_creative', 'skill', '🎨', 'Bàn tay khéo', 'Kỹ năng sáng tạo đạt mức 3.', lambda x: x['sk'].get('creative', 0) >= 3),
    _t('k_tech', 'skill', '💻', 'Rành máy móc', 'Kỹ năng dùng phần mềm đạt mức 3.', lambda x: x['sk'].get('tech', 0) >= 3),
    _t('k_calm', 'skill', '🧘', 'Bình tĩnh giờ cao điểm', 'Kỹ năng bình tĩnh khi áp lực đạt mức 3.', lambda x: x['sk'].get('calm', 0) >= 3),
    _t('k_learning', 'skill', '📚', 'Ham học hỏi', 'Kỹ năng ham học đạt mức 3.', lambda x: x['sk'].get('learning', 0) >= 3),
    # Money.
    _t('m_first_draw', 'money', '👛', 'Tự lo cơm áo', 'Lần đầu rút tiền lời về ví.', lambda x: x['stats'].get('withdrawn', 0) > 0),
    _t('m_save200', 'money', '🐷', 'Có của để dành', 'Ví có từ 200 xu.', lambda x: x['stats'].get('max_wallet', 0) >= 200),
    _t('m_save1000', 'money', '💰', 'Ví dày', 'Ví có từ 1.000 xu.', lambda x: x['stats'].get('max_wallet', 0) >= 1000),
    _t('m_investor', 'money', '📈', 'Nhà đầu tư nhỏ', 'Góp vốn tổng cộng 100 xu cho các nơi làm việc.', lambda x: x['stats'].get('invested', 0) >= 100),
    _t('m_salary', 'money', '💵', 'Đồng lương đầu tiên', 'Nhận lương về ví lần đầu.', lambda x: x['stats'].get('salary', 0) > 0),
    _t('m_debt_free', 'money', '🕊️', 'Trả hết nợ', 'Từng nợ tiền nhà và đã trả xong.', lambda x: x['stats'].get('debt_repaid', 0) > 0),
    # Fun, hidden until earned.
    _t('x_streak10', 'secret', '✨', 'Mười việc liền mạch', 'Làm 10 việc liền không sai sót ở một nơi.', lambda x: x['best_streak'] >= 10, True),
    _t('x_festival3', 'secret', '🎏', 'Mê ngày hội', 'Làm việc trọn 3 ngày hội khu phố.', lambda x: x['stats'].get('festival_days', 0) >= 3, True),
    _t('x_calm5', 'secret', '🍵', 'Người của ngày thư thả', 'Làm việc trọn 5 ngày thư thả.', lambda x: x['stats'].get('calm_days', 0) >= 5, True),
    _t('x_reopen', 'secret', '🔑', 'Nghỉ để đi xa hơn', 'Tạm đóng rồi mở lại một nơi làm việc.', lambda x: x['stats'].get('reopened', 0) > 0, True),
    _t('x_boss', 'secret', '🍀', 'Người gặp may', 'Được sếp mời thẳng vào làm.', lambda x: x['direct_offer'], True),
    _t('x_loyal', 'secret', '🏡', 'Chung thủy một quán', 'Làm 7 ngày sống liền ở cùng một nơi.', lambda x: x['loyal'] >= 7, True),
    _t('x_hopper', 'secret', '🦘', 'Chân sáo', 'Làm ở 3 nơi khác nhau trong 3 ngày sống liền.', lambda x: x['hopper'], True),
    _t('x_comeback', 'secret', '🌅', 'Từ tay trắng', 'Từng nợ tiền nhà, rồi để dành được 300 xu.', lambda x: x['stats'].get('debt_repaid', 0) > 0 and x['wallet'] >= 300, True),
]
TITLE_INDEX = {t['id']: t for t in TITLES}
STATS = ('withdrawn', 'invested', 'living_paid', 'upkeep_paid', 'salary', 'reopened', 'paused', 'max_wallet',
         'debt_repaid', 'calm_days', 'normal_days', 'festival_days')

LOCKED = 'Nơi này chưa mở với bạn. Cứ làm quen khu phố thêm, hàng xóm sẽ giới thiệu sau nhé.'


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _emp():
    from . import employment
    return employment


def _place(cid: str) -> str:
    return CAREER_META.get(cid, {}).get('place', cid)


def _employed(cid: str) -> bool:
    return _emp().required(cid)


def _unpaid(c: dict) -> int:
    return sum(b['amount'] for b in c['ops']['finance']['bills'] if b['status'] == 'unpaid')


def upkeep(s: dict, cid: str) -> int:
    """Daily cost of keeping a started workplace while you work elsewhere."""
    if _employed(cid):
        return 0
    return UPKEEP.get(s['careers'][cid]['ops']['property']['tier'], UPKEEP['cozy'])


def withdraw_max(c: dict) -> int:
    return max(0, c['money'] - _unpaid(c) - RESERVE)


def _need_xp(level: int) -> int:
    return 60 * level * (level - 1)


def maturity(xp: int) -> dict:
    level = 1
    while level < MAX_LEVEL and xp >= _need_xp(level + 1):
        level += 1
    return dict(level=level, xp=xp, floor=_need_xp(level), next=_need_xp(level + 1) if level < MAX_LEVEL else None,
                name=LEVEL_NAMES[min(level, len(LEVEL_NAMES)) - 1])


def _skill_level(points: int) -> int:
    return sum(points >= step for step in SKILL_STEPS[1:])


def initial(story: bool = False, seed: int = 0) -> dict:
    return dict(version=VERSION, story=bool(story), seed=int(seed), gender=None, intro=False, chapter=1, done=[],
                unlocked=[cid for cid in CH_UNLOCKS[1] if cid in CAREERS], wallet=START_WALLET, life_day=1,
                paused={}, titles={}, equipped=None, history=[], news=[], news_seq=0, clean_days=0, in_debt=False,
                days=[], stats={k: 0 for k in STATS} | dict(max_wallet=START_WALLET),
                certificates={}, study=None, cert_paper=None)   # 🎓 thi chứng chỉ (game/certificates.py)


def _context(s: dict) -> dict:
    """Everything the goals and titles read, derived from the real save."""
    cs, j = s['careers'], s['journey']
    served = {cid: int(c.get('metrics', {}).get('served', 0)) for cid, c in cs.items()}
    places = sum(1 for n in served.values() if n > 0)
    lv = {cid: 1 + int(c.get('xp', 0)) // 90 for cid, c in cs.items()}
    xp = sum(int(c.get('xp', 0)) for c in cs.values()) + BREADTH_XP * places
    points = {}
    for cid, n in served.items():
        for sid, w in SKILL_WEIGHTS.get(cid, {}).items():
            points[sid] = points.get(sid, 0) + n * w
    office = [cid for cid in OFFICE if cid in cs] or [cid for cid in cs if _employed(cid)]
    days = j.get('days', [])
    loyal = run = 0
    for i, row in enumerate(days):
        run = run + 1 if i and row['c'] == days[i - 1]['c'] and row['d'] == days[i - 1]['d'] + 1 else 1
        loyal = max(loyal, run)
    hopper = any(days[i]['d'] == days[i - 2]['d'] + 2 and len({days[i]['c'], days[i - 1]['c'], days[i - 2]['c']}) == 3
                 for i in range(2, len(days)))
    return dict(
        tasks=sum(served.values()), places=places, all_places=len(cs), lv=lv, level=max(lv.values(), default=1),
        days=sum(max(0, int(c.get('day', 1)) - 1) for c in cs.values()),
        mature=maturity(xp)['level'], xp=xp, points=points, sk={k: _skill_level(v) for k, v in points.items()},
        clean=j['clean_days'], draw=int(j['stats'].get('withdrawn', 0) > 0), titles=len(j['titles']),
        office_hired=sum(1 for cid in office if cs[cid].get('job', {}).get('status') == 'hired'),
        office_days=sum(int(cs[cid].get('job', {}).get('days_worked', 0)) for cid in office),
        done=len(j['done']), stats=j['stats'], wallet=j['wallet'], life_days=j['life_day'] - 1,
        best_streak=max((int(c.get('life', {}).get('best_streak', 0)) for c in cs.values()), default=0),
        direct_offer=any(h.get('event') == 'direct_offer' for c in cs.values() for h in c.get('job', {}).get('history', [])),
        loyal=loyal, hopper=hopper)


def _goal_done(ctx: dict, goal: dict, fast: bool = False) -> bool:
    if fast and goal['id'] in TRACKED_GOALS:
        return True
    return ctx[goal['id']] >= goal['goal']


def _chapter_done(ctx: dict, n: int, fast: bool = False) -> bool:
    ch = CHAPTER_INDEX.get(n)
    return bool(ch) and all(_goal_done(ctx, g, fast) for g in ch['goals'])


def _unlock_chapter(j: dict, n: int) -> list[str]:
    added = [cid for cid in CH_UNLOCKS.get(n, ()) if cid in CAREERS and cid not in j['unlocked']]
    j['unlocked'].extend(added)
    return added


def _fast_forward(s: dict) -> None:
    """An older save joins the story where its progress already is."""
    j = s['journey']
    for cid, c in s['careers'].items():
        if c.get('started') and cid not in j['unlocked']:
            j['unlocked'].append(cid)
    while j['chapter'] <= LAST and _chapter_done(_context(s), j['chapter'], fast=True):
        j['done'].append(j['chapter'])
        j['chapter'] += 1
        _unlock_chapter(j, j['chapter'])
    j['intro'] = j['intro'] or any(c.get('started') for c in s['careers'].values())
    j['life_day'] = max(j['life_day'], 1 + sum(max(0, int(c.get('day', 1)) - 1) for c in s['careers'].values()))


def enable_story(s: dict, seed: int | None = None) -> dict:
    """Turn the story on (new sessions and imports on a real server)."""
    j = s.setdefault('journey', initial())
    if seed is not None and not j['story']:
        j['seed'] = int(seed) % 2**31
    if not j['story']:
        j['story'] = True
        _fast_forward(s)
    return s


def migrate(s: dict) -> dict:
    """Saves from before the journey: story on, fast-forwarded, no retro costs."""
    seed = int(hashlib.sha256(f"{s.get('name')}|{s.get('seq')}".encode()).hexdigest()[:7], 16)
    s['journey'] = initial(True, seed)
    _fast_forward(s)
    return s['journey']


def upgrade(j: dict) -> None:
    """Future fields join existing journeys here (setdefault only)."""
    for k, v in initial().items():
        j.setdefault(k, copy.deepcopy(v))
    for k in STATS:
        j['stats'].setdefault(k, 0)
    if j.get('story'):
        for n in range(1, min(int(j.get('chapter', 1)), LAST) + 1):
            _unlock_chapter(j, n)


def roll_mode(s: dict, career: str, day: int) -> str:
    """Luck of the day, fixed by (seed, workplace, day): reloads never reroll."""
    if day <= 1:
        return 'normal'
    r = random.Random(f"mode|{s['journey'].get('seed', 0)}|{career}|{day}").random()
    edge = 0.0
    for mode, weight in MODES:
        edge += weight
        if r < edge:
            return mode
    return 'normal'


def is_unlocked(s: dict, career: str) -> bool:
    j = s.get('journey')
    return not j or not j.get('story') or career in j.get('unlocked', ())


def _playable(s: dict, cid: str) -> bool:
    j = s['journey']
    return cid in s['careers'] and is_unlocked(s, cid) and cid not in j['paused']


# ---------------------------------------------------------------- wallet
def _history(j: dict, amount: int, kind: str, label: str, career: str | None = None) -> None:
    j['history'].append(dict(day=j['life_day'], amount=int(amount), kind=kind, label=label[:120], career=career))
    j['history'] = ar.last(j['history'], 120, 'wallet', ar.JOURNEY)


def _wallet(j: dict, amount: int, kind: str, label: str, career: str | None = None) -> None:
    j['wallet'] += amount
    _history(j, amount, kind, label, career)
    if j['wallet'] < 0:
        j['in_debt'] = True
    elif j['in_debt']:
        j['in_debt'] = False
        j['stats']['debt_repaid'] += 1
    j['stats']['max_wallet'] = max(j['stats']['max_wallet'], j['wallet'])


def _transfer(s: dict, c: dict, amount: int, reason: str, category: str) -> None:
    """Owner transfers move cash but are not the workplace's income or cost:
    the ledger records them, the day's income/cost/net stay as they were."""
    e = _core()
    e.money(s, c, amount, reason, category=category)
    c['earnings'] -= max(amount, 0)
    c['costs'] -= max(-amount, 0)
    c['day_start_money'] = max(0, c['day_start_money'] + amount)


def living_cost(j: dict) -> dict:
    total = LIVING.get(j['chapter'], LIVING[LAST])
    rent = total * 6 // 10
    return dict(total=total, rent=rent, meals=total - rent)


# ---------------------------------------------------------------- engine hooks
def gate(s: dict, career: str, action: str, internal: bool = False) -> None:
    """Called for every career action before anything changes."""
    e = _core()
    if action == 'life_mode':
        raise e.GameError('Nhịp mỗi ngày do khu phố quyết định. Cứ mở cửa, hôm nay ra sao sẽ biết ngay!')
    j = s['journey']
    if internal or not j['story']:
        return
    e.need(career in j['unlocked'], LOCKED, 'locked')
    if action == 'select_career':
        e.need(j['intro'] or j['gender'], 'Chọn nhân vật của bạn trước nhé.', 'no_profile')
    if action == 'start_day':
        e.need(career not in j['paused'], 'Nơi này đang tạm đóng. Mở lại ở trang Hành trình rồi làm tiếp nhé.', 'paused')


def on_select(s: dict, career: str) -> None:
    j = s['journey']
    if j['story'] and not j['intro']:
        j['intro'] = True


def _end_of_day(s: dict, career: str, result: dict) -> None:
    e = _core()
    j = s['journey']
    c = s['careers'][career]
    ended_mode = c['life'].get('mode', 'normal')
    c['life']['mode'] = roll_mode(s, career, c['day'])
    if not j['story']:
        return
    day = j['life_day']
    j['stats'][f'{ended_mode}_days'] = j['stats'].get(f'{ended_mode}_days', 0) + 1
    j['days'] = ar.last(j['days'] + [dict(d=day, c=career, m=ended_mode)], 60, 'journey.days', ar.JOURNEY)
    notes = []
    # Salary is personal money: it lands in the wallet on payday.
    pay = int(((result.get('summary') or {}).get('job') or {}).get('salary') or 0)
    if pay > 0 and c['money'] >= pay:
        _transfer(s, c, -pay, 'Lương chuyển về ví', 'salary_to_wallet')
        _wallet(j, pay, 'salary', f'Lương ngày {c["day"] - 1} · {_place(career)}', career)
        j['stats']['salary'] += pay
        notes.append(f'Lương {pay} xu đã về ví của bạn.')
    # Rent and meals for the day that just ended.
    cost = living_cost(j)
    _wallet(j, -cost['total'], 'living', 'Tiền phòng và cơm nước')
    j['stats']['living_paid'] += cost['total']
    # Every other started workplace keeps its lights on while you are away.
    idle_total = 0
    for cid, other in s['careers'].items():
        if cid == career or not other.get('started') or cid in j['paused'] or cid not in j['unlocked']:
            continue
        fee = upkeep(s, cid)
        if not fee:
            continue
        from_fund = min(fee, other['money'])
        if from_fund:
            e.money(s, other, -from_fund, f'Chi phí duy trì khi vắng chủ · ngày sống {day}', category='upkeep')
        if fee > from_fund:
            _wallet(j, -(fee - from_fund), 'upkeep', f'Bù chi phí duy trì · {_place(cid)}', cid)
        idle_total += fee
    j['stats']['upkeep_paid'] += idle_total
    j['clean_days'] = j['clean_days'] + 1 if j['wallet'] >= 0 else 0
    j['life_day'] += 1
    line = f'Ngày sống {day}: tiền phòng và cơm nước {cost["total"]} xu'
    if idle_total:
        line += f', duy trì nơi vắng chủ {idle_total} xu'
    notes.insert(0, line + '.')
    if j['wallet'] < 0:
        notes.append(f'Ví đang nợ {-j["wallet"]} xu. Rút tiền lời từ một nơi làm việc để trả nhé.')
    summary = result.get('summary')
    if isinstance(summary, dict):
        summary['journey'] = dict(life_day=day, living=cost['total'], upkeep=idle_total, salary=pay, wallet=j['wallet'])
    result.setdefault('effects', []).extend(notes)


def _news(j: dict, kind: str, ref: str, items: list | None = None) -> None:
    j['news_seq'] += 1
    j['news'].append(dict(id=f'n{j["news_seq"]}', kind=kind, ref=ref, day=j['life_day'], items=list(items or [])))
    j['news'] = ar.last(j['news'], 12, 'journey.news', ar.JOURNEY)


def _award(s: dict) -> list[str]:
    j = s['journey']
    ctx = _context(s)
    earned = [t['id'] for t in TITLES if t['id'] not in j['titles'] and t['check'](ctx)]
    for tid in earned:
        j['titles'][tid] = j['life_day']
    return earned


def _evaluate(s: dict, result: dict) -> None:
    j = s['journey']
    earned = _award(s)
    finished = []
    # Debt pauses the story (never a game over): repay, then it moves on.
    while j['chapter'] <= LAST and j['wallet'] >= 0 and _chapter_done(_context(s), j['chapter']):
        n = j['chapter']
        j['done'].append(n)
        j['chapter'] += 1
        _unlock_chapter(j, j['chapter'])
        finished.append(n)
    if finished:
        earned += _award(s)
    for n in finished:
        _news(j, 'chapter', str(n))
    story = [t for t in earned if t.startswith('st_')]
    others = [t for t in earned if not t.startswith('st_')]
    if others:
        _news(j, 'titles', 'titles', others[:60])
    if finished:
        result['celebrate'] = True
        result['journey'] = dict(chapters=finished, titles=story + others)
    elif others:
        result['journey'] = dict(chapters=[], titles=others)


def after(s: dict, career: str | None, action: str, p: dict, result: dict) -> None:
    """Runs after every successful action, before validation."""
    j = s['journey']
    if action == 'end_day' and career in s['careers']:
        _end_of_day(s, career, result)
    bk.on_life_day(s, result)   # 🏦 interest, statements, installments: once per life day (idempotent)
    if action == 'start_day' and career in s['careers']:
        line = _emp().backdoor_remark(s, s['careers'][career], career)   # vào bằng cửa sau: one remark, day one
        if line:
            result.setdefault('effects', []).append(line)
    if not j['story']:
        return
    for cid in list(j['paused']):
        if not s['careers'].get(cid, {}).get('started'):
            j['paused'].pop(cid)
    if j['equipped'] and j['equipped'] not in j['titles']:
        j['equipped'] = None
    _evaluate(s, result)


def action(s: dict, career: str | None, name: str, p: dict) -> tuple[dict, dict]:
    """`jr_*` commands. `career` is ignored, like `settings`."""
    e = _core()
    need = e.need
    j = s['journey']
    result = dict(message='Đã cập nhật hành trình.', effects=[])
    if name == 'jr_profile':
        need(set(p) <= {'name', 'gender'} and p, 'Thông tin nhân vật không hợp lệ.')
        if 'name' in p:
            s['name'] = e.clean_text(p['name'], 24)
        if 'gender' in p:
            need(p['gender'] in ('male', 'female'), 'Chọn Nam hoặc Nữ nhé.')
            j['gender'] = p['gender']
        result['message'] = f'Chào {s["name"]}! Khu phố đã nhớ tên bạn.'
    elif name == 'jr_equip':
        tid = p.get('title')
        need(tid is None or tid in j['titles'], 'Bạn chưa có danh hiệu này.')
        j['equipped'] = tid
        result['message'] = f'Đã đeo danh hiệu “{TITLE_INDEX[tid]["name"]}”.' if tid else 'Đã cất danh hiệu.'
    elif name == 'jr_seen':
        ids = p.get('ids')
        need(isinstance(ids, list) and 1 <= len(ids) <= 20 and all(isinstance(x, str) for x in ids), 'Danh sách tin không hợp lệ.')
        j['news'] = [n for n in j['news'] if n['id'] not in ids]
        result['message'] = ''
    elif name in ('jr_withdraw', 'jr_invest', 'jr_pause', 'jr_reopen'):
        need(j['story'], 'Ví và quỹ nơi làm việc chỉ có trong hành trình.')
        cid = p.get('career')
        need(cid in CAREERS, 'Nơi làm việc không hợp lệ.')
        c = s['careers'][cid]
        need(cid in j['unlocked'] and c['started'], 'Bạn chưa làm việc ở nơi này.')
        place = _place(cid)
        if name == 'jr_withdraw':
            amount = e.integer(p.get('amount'), 1, 10**6)
            most = withdraw_max(c)
            need(most > 0, f'Quỹ cần giữ lại {RESERVE} xu và đủ tiền các hóa đơn chưa trả, nên chưa rút được.')
            need(amount <= most, f'Chỉ rút được tối đa {most} xu: quỹ cần giữ {RESERVE} xu và tiền các hóa đơn chưa trả.')
            _transfer(s, c, -amount, 'Rút tiền lời về ví', 'owner_draw')
            _wallet(j, amount, 'draw', f'Rút từ {place}', cid)
            j['stats']['withdrawn'] += amount
            result['message'] = f'Đã rút {amount} xu từ {place} về ví.'
        elif name == 'jr_invest':
            amount = e.integer(p.get('amount'), 1, 10**6)
            need(j['wallet'] >= amount, 'Ví không đủ để góp vốn số này.')
            _transfer(s, c, amount, 'Góp vốn từ ví của bạn', 'owner_capital')
            _wallet(j, -amount, 'invest', f'Góp vốn cho {place}', cid)
            j['stats']['invested'] += amount
            result['message'] = f'Đã góp {amount} xu vào quỹ {place}.'
        elif name == 'jr_pause':
            need(cid not in j['paused'], 'Nơi này đang tạm đóng rồi.')
            need(not _employed(cid), 'Nơi làm thuê không cần tạm đóng: không làm thì không tốn phí duy trì.')
            need(not c['open'], 'Khép ca ở nơi này trước rồi hãy tạm đóng nhé.')
            need(p.get('confirm') is True, 'Xác nhận tạm đóng nơi này.')
            j['paused'][cid] = j['life_day']
            j['stats']['paused'] += 1
            result['message'] = f'{place} tạm đóng: không tốn phí duy trì. Mở lại tốn {REOPEN_FEE} xu.'
        else:
            need(cid in j['paused'], 'Nơi này đang mở rồi.')
            need(p.get('confirm') is True, 'Xác nhận mở lại nơi này.')
            elsewhere = any(_playable(s, k) and k != cid and (not _employed(k) or s['careers'][k]['job']['status'] == 'hired')
                            for k in j['unlocked'])
            if c['money'] >= REOPEN_FEE:
                e.money(s, c, -REOPEN_FEE, 'Phí mở lại sau khi tạm đóng', category='reopen_fee')
                paid = f'quỹ trả {REOPEN_FEE} xu'
            elif j['wallet'] >= REOPEN_FEE:
                _wallet(j, -REOPEN_FEE, 'reopen', f'Phí mở lại {place}', cid)
                paid = f'ví trả {REOPEN_FEE} xu'
            else:
                need(not elsewhere, f'Cần {REOPEN_FEE} xu để mở lại. Làm thêm ở nơi khác rồi quay lại nhé.')
                paid = 'hàng xóm giúp, không tốn phí'
            j['paused'].pop(cid)
            j['stats']['reopened'] += 1
            result['message'] = f'{place} mở cửa lại ({paid}).'
    elif name.startswith('jr_cert_'):
        result.update(ct.action(s, name, p))
    elif name.startswith('jr_bk_'):
        result.update(bk.action(s, name, p))
    else:
        raise e.GameError('Thao tác hành trình không hợp lệ.', 'unknown_action')
    after(s, None, name, p, result)
    e.validate_state(s)
    return s, result


# ---------------------------------------------------------------- views
def _goals_view(ctx: dict, n: int) -> list[dict]:
    ch = CHAPTER_INDEX.get(n)
    if not ch:
        return []
    return [dict(id=g['id'], text=g['text'], goal=g['goal'], cur=min(int(ctx[g['id']]), 10**6), done=_goal_done(ctx, g))
            for g in ch['goals']]


def default_career(s: dict) -> str:
    """The workplace shown before the player picks one: open in the story, the suggested one first."""
    j = s.get('journey') or {}
    if not j.get('story'):
        return 'mother_baby'
    open_ids = [cid for cid in j.get('unlocked', ()) if cid in s['careers']]
    pick = suggested(s)
    return pick if pick in open_ids else (open_ids or ['mother_baby'])[0]


def suggested(s: dict, ctx: dict | None = None) -> str | None:
    """The workplace the primary button sends you to."""
    j = s['journey']
    cs = s['careers']
    ctx = ctx or _context(s)
    open_ids = [cid for cid in (j['unlocked'] if j['story'] else cs) if _playable(s, cid)]
    goals = {g['id']: g for g in _goals_view(ctx, j['chapter']) if not g['done']}
    fresh = [cid for cid in open_ids if not cs[cid]['metrics'].get('served')]
    if 'office_hired' in goals or 'office_days' in goals:
        office = [cid for cid in OFFICE if cid in open_ids]
        if office:
            hired = [cid for cid in office if cs[cid]['job']['status'] == 'hired']
            return (hired or office)[0]
    if 'places' in goals and fresh:
        current = [cid for cid in CH_UNLOCKS.get(j['chapter'], ()) if cid in fresh]
        return (current or fresh)[0]
    cur = s.get('current')
    if cur in open_ids and cs[cur]['started']:
        return cur
    for row in reversed(j['days']):
        if row['c'] in open_ids:
            return row['c']
    started = [cid for cid in open_ids if cs[cid]['started']]
    return (started or open_ids or [None])[0]


def public(s: dict) -> dict:
    j = s['journey']
    ctx = _context(s)
    places = {}
    for cid, c in s['careers'].items():
        if not c.get('started'):
            continue
        places[cid] = dict(fund=c['money'], upkeep=upkeep(s, cid), paused=cid in j['paused'], employed=_employed(cid),
                           unpaid=_unpaid(c), withdraw_max=withdraw_max(c))
    secret = {tid: dict(name=TITLE_INDEX[tid]['name'], emoji=TITLE_INDEX[tid]['emoji'], desc=TITLE_INDEX[tid]['desc'])
              for tid in j['titles'] if TITLE_INDEX[tid]['secret']}
    eq = TITLE_INDEX.get(j['equipped'])
    return dict(
        story=j['story'], gender=j['gender'], intro=j['intro'], chapter=j['chapter'], done=list(j['done']),
        finale=j['chapter'] > LAST, unlocked=list(j['unlocked']) if j['story'] else list(s['careers']),
        wallet=j['wallet'], debt=max(0, -j['wallet']), life_day=j['life_day'], living=living_cost(j),
        places=places, titles=sorted(([tid, day] for tid, day in j['titles'].items()), key=lambda x: (-x[1], x[0])),
        equipped=j['equipped'], equipped_title=dict(id=eq['id'], name=eq['name'], emoji=eq['emoji']) if eq else None,
        secret=secret, maturity=maturity(ctx['xp']),
        skills=[dict(id=sid, points=ctx['points'].get(sid, 0), level=ctx['sk'].get(sid, 0)) for sid in _skill_ids()],
        goals=_goals_view(ctx, j['chapter']), progress_paused=j['story'] and j['wallet'] < 0 and j['chapter'] <= LAST,
        clean_days=j['clean_days'], history=list(reversed(j['history'][-30:])), news=tree_copy(j['news']),
        suggested=suggested(s, ctx), tasks=ctx['tasks'], worked=ctx['places'],
        stats={k: j['stats'].get(k, 0) for k in ('withdrawn', 'invested', 'living_paid', 'upkeep_paid', 'salary')},
        bank=bk.public(s), **ct.public(s))


def _skill_ids() -> list[str]:
    return [x['id'] for x in _emp().STRENGTHS]


def _content_line(line: dict) -> dict:
    who = CAST[line['who']]
    return dict(who=line['who'], name=who['name'], emoji=who['emoji'], text=line['text'])


def content() -> dict:
    """Static story data for the client (bootstrap only). Secret titles stay hidden."""
    return dict(
        chapters=[dict(n=ch['n'], title=ch['title'], art=ch['art'], tagline=ch['tagline'],
                       unlocks=[cid for cid in CH_UNLOCKS[ch['n']] if cid in CAREERS],
                       intro=[_content_line(x) for x in ch['intro']], outro=[_content_line(x) for x in ch['outro']],
                       goals=[dict(id=g['id'], text=g['text'], goal=g['goal']) for g in ch['goals']]) for ch in CHAPTERS],
        cast=CAST, cats=[dict(id=k, name=v) for k, v in TITLE_CATS],
        titles=[dict(id=t['id'], cat=t['cat'], secret=True) if t['secret'] else
                {k: t[k] for k in ('id', 'cat', 'emoji', 'name', 'desc')} for t in TITLES],
        skills=_emp().STRENGTHS, levels=LEVEL_NAMES, reserve=RESERVE, reopen_fee=REOPEN_FEE, start_wallet=START_WALLET,
        unlock_chapter={cid: n for n, ids in CH_UNLOCKS.items() for cid in ids if cid in CAREERS}, certs=ct.content())


def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s.get('journey')
    need(isinstance(j, dict) and set(initial()) <= set(j), 'Bản lưu thiếu dữ liệu hành trình.', 'invalid_save')
    need(j['version'] == VERSION, 'Phiên bản hành trình không hợp lệ.', 'invalid_save')
    for k in ('story', 'intro', 'in_debt'):
        need(type(j[k]) is bool, 'Cờ hành trình không hợp lệ.')
    integer(j['seed'], 0, 2**31)
    need(j['gender'] in (None, 'male', 'female'), 'Giới tính nhân vật không hợp lệ.')
    integer(j['chapter'], 1, LAST + 1)
    need(j['done'] == list(range(1, j['chapter'])), 'Tiến trình chương không hợp lệ.')
    need(isinstance(j['unlocked'], list) and len(j['unlocked']) == len(set(j['unlocked'])) and set(j['unlocked']) <= set(CAREERS),
         'Danh sách nơi làm việc đã mở không hợp lệ.')
    allowed = {cid for n in range(1, min(j['chapter'], LAST) + 1) for cid in CH_UNLOCKS[n]}
    allowed |= {cid for cid, c in s['careers'].items() if c.get('started')}
    need(set(j['unlocked']) <= allowed, 'Nơi làm việc mở sớm hơn chương hiện tại.')
    need({cid for cid in CH_UNLOCKS[1] if cid in CAREERS} <= set(j['unlocked']), 'Thiếu nơi làm việc của chương đầu.')
    integer(j['wallet'], -10**7, 10**9)
    integer(j['life_day'], 1, 10**6)
    integer(j['clean_days'], 0, 10**6)
    integer(j['news_seq'], 0, 10**9)
    need(isinstance(j['paused'], dict) and len(j['paused']) <= len(CAREERS), 'Danh sách tạm đóng không hợp lệ.')
    for cid, day in j['paused'].items():
        need(cid in j['unlocked'], 'Nơi tạm đóng không hợp lệ.')
        integer(day, 1, 10**6)
    need(isinstance(j['titles'], dict) and set(j['titles']) <= set(TITLE_INDEX), 'Danh hiệu không hợp lệ.')
    for day in j['titles'].values():
        integer(day, 1, 10**6)
    need(j['equipped'] is None or j['equipped'] in j['titles'], 'Danh hiệu đang đeo không hợp lệ.')
    need(isinstance(j['history'], list) and len(j['history']) <= 120, 'Sổ ví không hợp lệ.')
    for row in j['history']:
        need(isinstance(row, dict) and row.get('kind') in HISTORY_KINDS, 'Dòng sổ ví không hợp lệ.')
        integer(row.get('day'), 1, 10**6)
        integer(row.get('amount'), -10**7, 10**7)
        txt(row.get('label'), 120)
        need(row.get('career') is None or row['career'] in CAREERS, 'Dòng sổ ví sai nơi làm việc.')
    need(isinstance(j['news'], list) and len(j['news']) <= 12, 'Tin hành trình không hợp lệ.')
    for n in j['news']:
        need(isinstance(n, dict) and n.get('kind') in NEWS_KINDS, 'Tin hành trình không hợp lệ.')
        txt(n.get('id'), 20)
        txt(n.get('ref'), 20)
        integer(n.get('day'), 1, 10**6)
        need(isinstance(n.get('items'), list) and len(n['items']) <= 60 and all(x in TITLE_INDEX for x in n['items']),
             'Tin danh hiệu không hợp lệ.')
    need(isinstance(j['days'], list) and len(j['days']) <= 60, 'Nhật ký ngày sống không hợp lệ.')
    for row in j['days']:
        need(isinstance(row, dict) and row.get('c') in CAREERS and row.get('m') in [m for m, _ in MODES], 'Nhật ký ngày sống không hợp lệ.')
        integer(row.get('d'), 1, 10**6)
    need(isinstance(j['stats'], dict) and set(j['stats']) <= set(STATS), 'Thống kê hành trình không hợp lệ.')
    for v in j['stats'].values():
        integer(v, 0, 10**9)
    ct.validate(s)
    bk.validate(s)
