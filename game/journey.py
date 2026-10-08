"""Hành trình: one young person, one small neighbourhood, many workplaces.

A root `s['journey']` turns the collection of careers into one life story:

* chapters with short story beats; each chapter's goals are read from the real
  save (tasks done, levels, places worked, office contract…) and completing a
  chapter unlocks the next workplaces;
* a personal wallet ("Ví của bạn") that pays daily living costs, separate from
  each workplace's own fund (the career `money`, which keeps its ledger);
* withdrawals to the wallet and investments back into a fund. A workplace you
  are not working at costs nothing (#oldcost, 04/10/2026: the old "duy trì khi
  vắng chủ" kept charging places players had moved on from, shown in the wallet
  as "Nơi làm khác −X"); pausing stays for old saves and reopening is free;
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
from . import price_index as pi   # 💹 07/10: LIVING
from . import wardrobe as wd   # 👗 Tủ đồ (game/wardrobe.py)
from . import avatar as avt    # 🙂 Ảnh đại diện khi chat (game/avatar.py)
from . import housing as hs   # 🏠 Nhà của bạn (game/housing.py)
from . import household as hh
from . import outings as outings_
from . import courier as ship
from . import reno as rn   # 🛠️ Sửa và trang trí nhà (game/reno.py)
from . import deco as dc   # 🪴 Bày trí phòng (game/deco.py)
from . import garage as gr   # 🚗 Xe & phương tiện (game/garage.py)
from . import gadgets as gd   # 📱 Cửa hàng điện thoại (game/gadgets.py)
from . import pets as pt   # 🐾 Nuôi thú cưng (game/pets.py)
from . import spend as sp   # ☕ Đi quán, spa, rạp, 🙏 công đức, 🎨 phong cách tuần (game/spend.py)
from . import auction as auc   # 🔨 Nhà đấu giá đồ độc bản (game/auction.py)
from . import lux as lx   # 🛍️ Mua sắm: du lịch, sưu tập, dinh thự, tiệc, khóa học, 🎆 Mạnh Thường Quân (game/lux.py)
from . import estates as es   # 🏰 Dinh thự: living in a villa (game/estates.py)
from . import upkeep as up   # 🧾 Hóa đơn tháng: phí giữ xe, bảo trì nhà (game/upkeep.py)
from . import rui   # 🛡️ Rủi ro & bảo hiểm (game/rui.py)
from . import vang   # 💰 Tiệm vàng Kim Phát (game/vang.py)
from . import system_gift as sg   # 🎁 Quà từ Phố Có Chuyện (game/system_gift.py)
from . import live_effects as lfx   # 🧧 rewards from the live service (game/live_effects.py)
from . import fair as fh   # 🏮 Hội chợ dân gian (game/fair.py)
from . import wedding_live as wl   # 🎁 the admin's gift for the weddings (journey['wed_gift'])
from . import needs as nd   # 🍚 No bụng, 😴 Tỉnh táo (game/needs.py)
from . import chua as cg    # 🛕 Đi chùa (game/chua.py)
from . import relax as rx   # 🏊 Thư giãn ở nhà: hồ bơi, bồn tắm (game/relax.py)
from . import leisure as ls   # 🏝️ 2.5D town: private, free pixel fishing/boat/community-pool rounds (game/leisure.py)
from . import fridge as fr   # 🧊 Tủ lạnh ở nhà: cất đồ ăn, đói thì ăn (game/fridge.py)
from . import x3_week as x3   # 🔥 Nghề x3 trong tuần (game/x3_week.py)
from . import accounting_jobs as aj   # 💼 Việc làm kế toán: exam gate, entry check, ×3/×5 (game/accounting_jobs.py)
from . import whats_new as wn   # "Có gì mới": read already for a brand-new save (_welcome_settings)
from . import quay as qy   # 🏪 Quầy của bạn: your own counter, staff, the till (game/quay.py)
from . import abroad as ab   # ✈️ Du học, 🌏 Làm việc ở nước ngoài (game/abroad.py)

VERSION = 1
START_WALLET = 60
RESERVE = 80          # a fund keeps this much after a withdrawal
REOPEN_FEE = 0         # reopening a paused place is free: a place you are away from costs nothing (was 15)
ONBOARD_MARK = 'onb1'   # settings.notesSeen: named with the new-player onboarding (its contextual hints, v4/onboard.js)
WELCOME_GIFT = 20     # a brand-new neighbour's gift, into the wallet when the first life day ends
WELCOME_LABEL = 'Quà chào hàng xóm mới 🎁'
BREADTH_XP = 80       # maturity bonus for every workplace you really worked at
# 💹 07/10 (game/price_index.py): written as the base, indexed -> 11 13 15 18 20 22 22 xu a life day
LIVING = {ch: pi.price(xu, luxury=False) for ch, xu in {1: 10, 2: 12, 3: 14, 4: 16, 5: 18, 6: 20, 7: 20}.items()}
UPKEEP = {'cozy': 4, 'sunny': 7, 'garden': 11}   # the old idle fee per tier: no longer charged (upkeep() is 0)
MODES = (('calm', .25), ('normal', .55), ('festival', .20))
HISTORY_KINDS = ('living', 'upkeep', 'draw', 'invest', 'salary', 'reopen', 'incident', 'life', 'study', 'backdoor', 'bank', 'home', 'fair', 'karaoke')   # 'karaoke': accepted from 1.9.5 (step 1); game/karaoke.py WRITE_KIND says when it is written
NEWS_KINDS = ('chapter', 'titles')
# 🏷️ Đang đeo: game titles and certificates worn at once (owner, 01/10: "danh hiệu trò chơi và chứng chỉ được chọn
# nhiều 1 lúc"). Three fit one line of chips on a 390 px phone and keep a name tag short (the first one by name, the
# others by their emoji). The first title worn stays in `equipped` for older clients and the live service.
WEAR_MAX = 3
CERT_WEAR = 'cert:'   # a worn certificate: 'cert:<group id>' (game/certificates.py GROUPS)

CH_UNLOCKS = {
    # New players get every storefront at once; the service places follow after the first day.
    1: ('milk_tea', 'grocery', 'delivery', 'cafe_bakery', 'florist', 'mother_baby', 'restaurant'),
    2: ('pet_care', 'salon', 'repair', 'farm', 'homestay', 'homemaker', 'nail', 'pagoda', 'photobooth', 'giupviec', 'naucom', 'babysitter'),
    3: ('clothing', 'pet_shop', 'tra_da', 'fruit', 'garbage', 'drain', 'ice_cream', 'pho', 'com', 'zpop'),
    4: ('customer_care', 'pharmacy', 'tour_guide', 'teacher', 'accounting', 'pilot', 'flight_attendant', 'library', 'oil', 'railway', 'nurse', 'lighthouse', 'rescue', 'lifeguard', 'police'),
    5: ('corp_accounting', 'tax_payroll', 'hr_admin', 'secretary', 'it_helpdesk'),
    6: ('group_accounting',),
}
OFFICE = ('corp_accounting', 'tax_payroll', 'group_accounting', 'hr_admin', 'secretary', 'it_helpdesk')

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
                _line('ba_tam', 'Chợ dạo này lên giá, tiền cơm bà nhích thêm chút. Nhớ giữ ví cho đều nghe cháu.'),
                _line('ba_tam', 'Đứa cháu bà mê nhóm nhạc BLANKPINK gì đó, ngày nào cũng đòi ra tiệm album Mây Pop. Chị Thơ ở đó đang cần người đứng quầy.')],
         outro=[_line('chu_tu', 'Giờ thì có nghề trong tay thật rồi đó.'),
                _line('co_lua', 'Phường đang cần người cẩn thận ở mấy chỗ: nhà thuốc, trạm chăm sóc khách hàng, lớp học… Cô giới thiệu cháu nha.')],
         goals=[dict(id='level', goal=3, text='Đạt cấp 3 ở một nơi làm việc'),
                dict(id='clean', goal=3, text='Giữ ví không nợ 3 ngày sống liền'),
                dict(id='places', goal=3, text='Làm việc ở 3 nơi khác nhau')]),
    dict(n=4, title='Được tin cậy', art='🤝',
         tagline='Có những việc người ta chỉ giao cho người mình tin.',
         intro=[_line('co_lua', 'Mấy chỗ này cần người cẩn thận, nói năng rõ ràng. Cô tin cháu làm được.'),
                _line('anh_khoa', 'Lớp học Mầm Nắng đang tuyển người. Phải nộp hồ sơ, phỏng vấn đàng hoàng đó.'),
                _line('anh_khoa', 'Mà hồ sơ giờ ghi được một dòng rất thật: có kinh nghiệm ở một nghề khác trong phố.'),
                _line('chu_tu', 'Thằng Mẫn nhà bên làm thợ máy ở sân bay. Nó bảo Hãng bay Cánh Cò đang tuyển cơ phó với tiếp viên đó.'),
                _line('ba_sau', 'Đường ngang Bến Mây đầu phố Ray đang thiếu người gác chắn. Chú Sáu Cờ gác ở đó gần ba chục năm, đang tìm người cẩn thận để kèm.'),
                _line('ba_sau', 'Tuần trước bà nằm viện Lá Sen, mấy đứa điều dưỡng chăm bà khéo lắm. Khoa Nội đang tuyển người đó con.'),
                _line('chu_tu', 'Ông Bảy giữ đèn biển Hòn Gió ngoài đảo kia đang tìm người kèm. Ở đảo buồn lắm, mà đêm nào cũng có tàu nhờ cái đèn đó mà về.'),
                _line('chu_tu', 'Tổng đài cứu hộ phường Mây đang tìm người trực máy. Giọng bình tĩnh, hỏi địa chỉ trước tiên là được việc.'),
                _line('be_ti', dict(male='Hè này em học bơi ở Hồ bơi Sóng Xanh. Anh Hải cứu hộ bảo đang tìm thêm người cẩn thận, anh thử không?',
                                    female='Hè này em học bơi ở Hồ bơi Sóng Xanh. Anh Hải cứu hộ bảo đang tìm thêm người cẩn thận, chị thử không?',
                                    none='Hè này em học bơi ở Hồ bơi Sóng Xanh. Anh Hải cứu hộ bảo đang tìm thêm người cẩn thận, thử không?')),
                _line('co_lua', 'Công an phường Mây đang tuyển cán bộ khu vực. Cô thấy cháu nói nhẹ mà dứt khoát, không nhận của ai cái gì. Hợp lắm.')],
         outro=[_line('co_lua', 'Giờ đi đâu trong phố cũng có người gửi lời chào cháu.'),
                _line('anh_khoa', 'Công ty mình với bên dịch vụ thuế đang tuyển. Kinh nghiệm ở phố ghi vào CV được hết, thử không?')],
         goals=[dict(id='places', goal=5, text='Làm việc ở 5 nơi khác nhau'),
                dict(id='titles', goal=6, text='Có 6 danh hiệu'),
                dict(id='mature', goal=5, text='Đạt trưởng thành cấp 5')]),
    dict(n=5, title='Bước vào văn phòng', art='💼',
         tagline='Một chiếc bàn làm việc, một tấm thẻ nhân viên và đồng lương đầu tiên.',
         intro=[_line('anh_khoa', 'Văn phòng khác tiệm nhiều lắm: tin tuyển dụng, CV, thư ứng tuyển rồi phỏng vấn.'),
                _line('anh_khoa', 'Nhớ chọn dòng “Có kinh nghiệm ở một nghề khác trong phố” nha. Người ta kiểm tra đó, nhưng mình làm thật mà.'),
                _line('ba_tam', 'Đi làm văn phòng thì lương về ví. Nhận lương rồi nhớ để dành tiền phòng nghe cháu.'),
                _line('co_lua', 'Công ty balo Cánh Diều cuối phố cũng đang tuyển người làm nhân sự, thư ký giám đốc với bạn trực máy tính. Không giỏi số vẫn làm được, miễn cẩn thận.')],
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
    'hr_admin': dict(communication=2, careful=1, teamwork=1),
    'secretary': dict(communication=2, careful=1, calm=1),
    'it_helpdesk': dict(tech=2, calm=1, careful=1),
    'oil': dict(careful=2, calm=1, teamwork=1),
    'lighthouse': dict(careful=2, calm=1, patience=1),
    'rescue': dict(calm=2, communication=1, careful=1),
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
    _t('c_hr_admin', 'career', '🗂️', 'Người giữ hồ sơ nhân sự', 'Đạt cấp 3 ở phòng nhân sự Cánh Diều.', lambda x: x['lv'].get('hr_admin', 1) >= 3),
    _t('c_secretary', 'career', '📅', 'Thư ký chu đáo', 'Đạt cấp 3 ở bàn thư ký giám đốc Cánh Diều.', lambda x: x['lv'].get('secretary', 1) >= 3),
    _t('c_it_helpdesk', 'career', '🖥️', 'Cứu tinh máy tính', 'Đạt cấp 3 ở bàn IT Cánh Diều.', lambda x: x['lv'].get('it_helpdesk', 1) >= 3),
    _t('c_oil', 'career', '🛢️', 'Người giữ ổ khóa đỏ', 'Đạt cấp 3 trên giàn Hải Âu.', lambda x: x['lv'].get('oil', 1) >= 3),
    _t('c_lighthouse', 'career', '🗼', 'Người giữ lửa Hòn Gió', 'Đạt cấp 3 ở đèn biển Hòn Gió.', lambda x: x['lv'].get('lighthouse', 1) >= 3),
    _t('c_rescue', 'career', '📞', 'Giọng nói giữ bình tĩnh', 'Đạt cấp 3 ở tổng đài cứu hộ phường Mây.', lambda x: x['lv'].get('rescue', 1) >= 3),
    _t('c_police', 'career', '👮', 'Người giữ bình yên hẻm', 'Đạt cấp 3 ở Công an phường Mây.', lambda x: x['lv'].get('police', 1) >= 3),
    _t('c_zpop', 'career', '💿', 'Người giữ seal nguyên vẹn', 'Đạt cấp 3 ở tiệm album Mây Pop.', lambda x: x['lv'].get('zpop', 1) >= 3),
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
    _t('m_home', 'money', '🏠', 'An cư', 'Có căn nhà đứng tên mình.', lambda x: x['stats'].get('homes_bought', 0) > 0),
    _t('m_home_free', 'money', '🔑', 'Nhà hết nợ', 'Trả xong khoản vay mua nhà.', lambda x: x['stats'].get('home_paid', 0) > 0),
    # Fun, hidden until earned.
    _t('x_streak10', 'secret', '✨', 'Mười việc liền mạch', 'Làm 10 việc liền không sai sót ở một nơi.', lambda x: x['best_streak'] >= 10, True),
    _t('x_festival3', 'secret', '🎏', 'Mê ngày hội', 'Làm việc trọn 3 ngày hội khu phố.', lambda x: x['stats'].get('festival_days', 0) >= 3, True),
    _t('x_calm5', 'secret', '🍵', 'Người của ngày thư thả', 'Làm việc trọn 5 ngày thư thả.', lambda x: x['stats'].get('calm_days', 0) >= 5, True),
    _t('x_reopen', 'secret', '🔑', 'Nghỉ để đi xa hơn', 'Tạm đóng rồi mở lại một nơi làm việc.', lambda x: x['stats'].get('reopened', 0) > 0, True),
    _t('x_boss', 'secret', '🍀', 'Người gặp may', 'Được sếp mời thẳng vào làm.', lambda x: x['direct_offer'], True),
    _t('x_loyal', 'secret', '🏡', 'Chung thủy một quán', 'Làm 7 ngày sống liền ở cùng một nơi.', lambda x: x['loyal'] >= 7, True),
    _t('x_hopper', 'secret', '🦘', 'Chân sáo', 'Làm ở 3 nơi khác nhau trong 3 ngày sống liền.', lambda x: x['hopper'], True),
    _t('x_comeback', 'secret', '🌅', 'Từ tay trắng', 'Từng nợ tiền nhà, rồi để dành được 300 xu.', lambda x: x['stats'].get('debt_repaid', 0) > 0 and x['wallet'] >= 300, True),
    # 💍 Live weddings (game/wedding_live.py): granted only through game/live_effects.py, never by _award.
    _t('w_crowd', 'secret', '🎉', 'Đám cưới đông vui', 'Đám cưới có từ 20 khách ở lại dự.', lambda x: False, True),
    _t('w_100', 'secret', '💞', 'Trăm ngày bên nhau', 'Tròn 100 ngày cưới.', lambda x: False, True),
    _t('w_1y', 'secret', '🎂', 'Tròn một năm', 'Tròn một năm ngày cưới.', lambda x: False, True),
    _t('w_500', 'secret', '💍', 'Năm trăm ngày thương', 'Tròn 500 ngày cưới.', lambda x: False, True),
    _t('w_1000', 'secret', '👑', 'Nghìn ngày son sắt', 'Tròn 1000 ngày cưới.', lambda x: False, True),
    _t('w_vip', 'secret', '🥇', 'Khách quý của phố', 'Đứng đầu bảng Khách mời của tuần.', lambda x: False, True),
    _t('w_pro', 'secret', '🎊', 'Ăn cưới chuyên nghiệp', 'Lọt top 3 Khách mời của tuần.', lambda x: False, True),
]
TITLES += fh.titles(_t)   # 🏮 Hội chợ dân gian: secret, granted by a round or after the fair (game/fair.py)
TITLE_INDEX = {t['id']: t for t in TITLES}
STATS = ('withdrawn', 'invested', 'living_paid', 'upkeep_paid', 'salary', 'reopened', 'paused', 'max_wallet',
         'debt_repaid', 'calm_days', 'normal_days', 'festival_days', 'homes_bought', 'home_paid')

LOCKED = 'Nơi này chưa mở với bạn. Cứ làm quen khu phố thêm, hàng xóm sẽ giới thiệu sau nhé.'


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


_EMPLOYMENT = None  # game.employment, imported once (import cycle)


def _emp():
    global _EMPLOYMENT
    if _EMPLOYMENT is None:
        from . import employment
        _EMPLOYMENT = employment
    return _EMPLOYMENT


def _place(cid: str) -> str:
    return CAREER_META.get(cid, {}).get('place', cid)


def _employed(cid: str) -> bool:
    return _emp().required(cid)


def _unpaid(c: dict) -> int:
    return sum(b['amount'] for b in c['ops']['finance']['bills'] if b['status'] == 'unpaid')


def upkeep(s: dict, cid: str) -> int:
    """Daily cost of keeping a started workplace while you work elsewhere: nothing.
    Leaving a place (switching career, the town map, Hành trình) stops every charge of it;
    its fund, stock and staff simply wait for you (a shift still open is closed when you come back)."""
    return 0


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
                paused={}, titles={}, equipped=None, worn=[], history=[], news=[], news_seq=0, clean_days=0, in_debt=False,
                days=[], stats={k: 0 for k in STATS} | dict(max_wallet=START_WALLET),
                certificates={}, study=None, cert_paper=None)   # 🎓 thi chứng chỉ (game/certificates.py)


def _context(s: dict) -> dict:
    """Everything the goals and titles read, derived from the real save."""
    cs, j = s['careers'], s['journey']
    served, lv, xp = {}, {}, 0
    for cid, c in cs.items():  # one pass (this runs on every command's view)
        served[cid] = int(c.get('metrics', {}).get('served', 0))
        x = int(c.get('xp', 0))
        lv[cid] = 1 + x // 90
        xp += x
    places = sum(1 for n in served.values() if n > 0)
    xp += BREADTH_XP * places
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
    if 'worn' not in j:   # 1.2: several worn at once; the one title worn before comes first
        eq = j.get('equipped')
        j['worn'] = [eq] if isinstance(eq, str) and eq in TITLE_INDEX and eq in (j.get('titles') or {}) else []
    for k, v in initial().items():
        j.setdefault(k, copy.deepcopy(v))
    for k in STATS:
        j['stats'].setdefault(k, 0)
    _refund_upkeep(j)
    bk.upgrade(j)   # 🏦 term deposits quoted per year (0.9.5)
    hs.upgrade(j)   # 🏠
    rn.upgrade(j)   # 🛠️
    dc.upgrade(j)   # 🪴
    gr.upgrade(j)   # 🚗
    gd.upgrade(j)   # 📱
    sp.upgrade(j)   # ☕
    pt.upgrade(j)   # 🐾
    lx.upgrade(j)   # 🛍️
    auc.upgrade(j)   # 🔨
    if j.get('story'):
        for n in range(1, min(int(j.get('chapter', 1)), LAST) + 1):
            _unlock_chapter(j, n)


REFUND_LABEL = 'Hoàn phí duy trì nơi vắng chủ 💰'


def _refund_upkeep(j: dict) -> None:
    """Owner 04/10/2026: give back every "duy trì khi vắng chủ" fee ever paid (1.6.5 stopped charging it).
    stats.upkeep_paid is that total (fund and wallet parts); it goes to the wallet once and the stat drops to 0,
    so no new save field is needed and a second load refunds nothing."""
    paid = int(j['stats'].get('upkeep_paid') or 0)
    if paid > 0:
        _wallet(j, paid, 'upkeep', REFUND_LABEL)
        j['stats']['upkeep_paid'] = 0


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
    if not j or not j.get('story'):
        return True
    # 💼 an accounting place: its certificate opens it early, and without it (nor past work there) it stays shut
    return (career in j.get('unlocked', ()) or aj.opens(s, career)) and aj.can_work(s, career)[0]


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
    """{total, rent, meals, label, where}: Bà Tám's rent, or a rented room's, or điện nước at home (game/housing.py)."""
    return es.living(j, hs.living(j, LIVING.get(j['chapter'], LIVING[LAST])))   # 🏰 a villa you live in: its điện nước


# ---------------------------------------------------------------- engine hooks
def gate(s: dict, career: str, action: str, internal: bool = False, p: dict | None = None) -> None:
    """Called for every career action before anything changes (p: its payload)."""
    e = _core()
    if action == 'life_mode':
        raise e.GameError('Nhịp mỗi ngày do khu phố quyết định. Cứ mở cửa, hôm nay ra sao sẽ biết ngay!')
    j = s['journey']
    if internal or not j['story']:
        return
    e.need(career in j['unlocked'] or aj.opens(s, career), LOCKED, 'locked')
    ok, why = aj.can_work(s, career)   # 💼 an accounting place takes you once you pass its exam
    e.need(ok, why, 'need_cert')
    if action == 'start_day' and not s['careers'][career]['open']:
        aj.gate_start(s, career, p if isinstance(p, dict) else {})   # kiểm tra kiến thức đầu ca
    if action == 'select_career':
        e.need(j['intro'] or j['gender'], 'Chọn nhân vật của bạn trước nhé.', 'no_profile')
    if action == 'start_day':
        e.need(career not in j['paused'], 'Nơi này đang tạm đóng. Mở lại ở trang Hành trình rồi làm tiếp nhé.', 'paused')
        ab.gate_start(s, career)   # 🌏 away on a contract abroad: only that job's branch opens


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
    job_note = ((result.get('summary') or {}).get('job') or {})
    pay = int(job_note.get('salary') or 0)
    if pay > 0 and c['money'] >= pay:
        times = job_note.get('multiplier') if isinstance(job_note.get('multiplier'), int) else 1   # 💼 ×3 / ×5 kế toán
        _transfer(s, c, -pay, 'Lương chuyển về ví', 'salary_to_wallet')
        _wallet(j, pay, 'salary', f'Lương ngày {c["day"] - 1} · {_place(career)}' + (f' · x{times}' if times > 1 else ''), career)
        j['stats']['salary'] += pay
        notes.append(f'Lương {pay} xu đã về ví của bạn.' if times <= 1 else
                     f'Lương kế toán x{times}{" ngày lễ" if times == aj.X5 else ""}: {pay} xu đã về ví của bạn.')
    notes.extend(ab.day_lines(job_note))   # 🌏 a day at the branch abroad: the city, a letter from home, coming home
    # 🔥 This career's x3 day (game/x3_week.py): the day's net once more, twice, into the wallet.
    extra = 0
    if x3.on(career):
        # ⏱️ Tăng ca ×2 and ⚡ năng suất (game/overtime.py) stay out of the boosted net: they never stack with x3.
        ot = ((result.get('summary') or {}).get('ot') or {}).get('total') or 0
        extra = x3.bonus(int((result.get('summary') or {}).get('net') or 0) - int(ot))
        if extra > 0:
            _wallet(j, extra, 'salary', f'🔥 Thưởng ngày x{x3.X} · {_place(career)}', career)
            notes.append(f'🔥 Hôm nay {_place(career)} lời x{x3.X}: thưởng thêm {extra} xu vào ví.')
    # Rent and meals for the day that just ended.
    cost = living_cost(j)
    _wallet(j, -cost['total'], 'living', cost['label'])
    j['stats']['living_paid'] += cost['total']
    # A workplace you are not working at today costs nothing: no fund or wallet line for it
    # (it used to pay 4-11 xu "duy trì khi vắng chủ" every day, the "Nơi làm khác" chip).
    idle_total = 0
    if day == 1:   # the end of a new player's first day: Bà Tám's welcome, through the wallet like any income
        _wallet(j, WELCOME_GIFT, 'life', WELCOME_LABEL)
        notes.append(f'🎁 Bà Tám gửi quà chào hàng xóm mới: +{WELCOME_GIFT} xu vào ví.')
    j['clean_days'] = j['clean_days'] + 1 if j['wallet'] >= 0 else 0
    j['life_day'] += 1
    line = f'Ngày sống {day}: {cost["label"].lower()} {cost["total"]} xu'
    notes.insert(0, line + '.')
    if j['wallet'] < 0:
        notes.append(f'Ví đang nợ {-j["wallet"]} xu. Rút tiền lời từ một nơi làm việc để trả nhé.')
    summary = result.get('summary')
    if isinstance(summary, dict):
        summary['journey'] = dict(life_day=day, living=cost['total'], upkeep=idle_total, salary=pay, wallet=j['wallet'],
                                  **({'gift': WELCOME_GIFT} if day == 1 else {}), **({'x3': extra} if extra > 0 else {}))
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
    hs.on_life_day(s, result)   # 🏠 home installments and comfort (after the bank's morning)
    rn.on_life_day(s, result)   # 🛠️ wear and the Ấm cúng morning (after the home's)
    dc.on_life_day(s, result)   # 🪴 follow the player home, a rented room's Ấm cúng morning, a neighbour drops by
    up.on_life_day(s, result)   # 🧾 the monthly bills of the vehicles and homes owned (after the home's morning)
    lx.on_life_day(s, result)   # 🛍️ phí hạng sang: villas, crewed vehicles, insured collection pieces
    rui.on_life_day(s, result)   # 🛡️ warnings, cards and premiums (after the bills: a waived bill raises the odds)
    qy.on_life_day(s, result)   # 🏪 each counter runs the day that just ended (after the month's bills)
    qy.on_shift(s, career, action, result)   # 💼 a hired shift at another player's counter ends with its day (game/quay_hire.py)
    ship.on_action(s, career, action, p, result)
    ab.sync(s)   # 🌏 a contract abroad whose job was quit or changed ends
    if action == 'start_day' and career in s['careers']:
        line = _emp().backdoor_remark(s, s['careers'][career], career)   # vào bằng cửa sau: one remark, day one
        if line:
            result.setdefault('effects', []).append(line)
    if not j['story']:
        return
    if action == 'start_day' and career in s['careers'] and career not in j['unlocked'] and s['careers'][career].get('started'):
        j['unlocked'].append(career)   # 💼 opened early by a certificate: kept once worked (an older build accepts it)
    for cid in list(j['paused']):
        if not s['careers'].get(cid, {}).get('started'):
            j['paused'].pop(cid)
    if j['equipped'] and j['equipped'] not in j['titles']:
        j['equipped'] = None
    if any(not _owns(j, x) for x in j['worn']):
        _wear(j, [x for x in j['worn'] if _owns(j, x)])
    _evaluate(s, result)


def _owns(j: dict, item) -> bool:
    """A worn item the save really has: a title it earned, or a certificate it passed."""
    if not isinstance(item, str):
        return False
    if item.startswith(CERT_WEAR):
        return ct.earned(j, item[len(CERT_WEAR):])
    return item in TITLE_INDEX and item in j['titles']


def _wear(j: dict, items: list) -> None:
    """Set what is worn; `equipped` mirrors the first title among them (older clients, the live service)."""
    j['worn'] = list(items)
    j['equipped'] = next((x for x in items if not x.startswith(CERT_WEAR)), None)


def worn_view(j: dict) -> list:
    """[{id, kind, emoji, name}] of what is worn, in order (profile, Phố nghề, name tags)."""
    out = []
    for x in j.get('worn') or ():
        if not isinstance(x, str):
            continue
        if x.startswith(CERT_WEAR):
            g = ct.INDEX.get(x[len(CERT_WEAR):])
            if g:
                out.append(dict(id=x, kind='cert', emoji=g['emoji'], name=g['name']))
        elif x in TITLE_INDEX:
            t = TITLE_INDEX[x]
            out.append(dict(id=x, kind='title', emoji=t['emoji'], name=t['name']))
    return out


def _welcome_settings(s: dict) -> None:
    """A brand-new save has just been named (still in the intro): the "Có gì mới" release notes are for
    returning players, so the current ones count as read, silently; and the save is marked for the
    contextual first-time hints (the marker rides with the other seen-flags in settings.notesSeen)."""
    st = s['settings']
    st['whatsNewSeen'] = wn.newer(st.get('whatsNewSeen', ''), wn.LATEST)
    seen = [x for x in str(st.get('notesSeen', '')).split(',') if x]
    if ONBOARD_MARK not in seen and len(seen) < 12:
        st['notesSeen'] = ','.join(seen + [ONBOARD_MARK])


def action(s: dict, career: str | None, name: str, p: dict) -> tuple[dict, dict]:
    """`jr_*` commands. `career` is ignored, like `settings`."""
    e = _core()
    need = e.need
    j = s['journey']
    result = dict(message='Đã cập nhật hành trình.', effects=[])
    if name == 'jr_profile':
        need(set(p) <= {'name', 'gender'} and p, 'Thông tin nhân vật không hợp lệ.')
        if 'name' in p:
            from .accounts import character_name   # moderation #13: the display-name rules (profanity too)
            s['name'] = character_name(p['name'], s.get('name'))
        if 'gender' in p:
            need(p['gender'] in ('male', 'female'), 'Chọn Nam hoặc Nữ nhé.')
            old, j['gender'] = j['gender'], p['gender']
            wd.on_gender(s, old)
        if j['story'] and not j['intro'] and j['gender']:
            _welcome_settings(s)
        result['message'] = f'Chào {s["name"]}! Khu phố đã nhớ tên bạn.'
    elif name == 'jr_equip':
        if 'worn' in p:   # several at once: the whole list, in the order shown
            items = p.get('worn')
            need(isinstance(items, list) and all(isinstance(x, str) for x in items), 'Danh sách đang đeo không hợp lệ.')
            need(len(items) == len(set(items)), 'Mỗi danh hiệu chỉ đeo một lần thôi.')
            need(len(items) <= WEAR_MAX, f'Đeo tối đa {WEAR_MAX} danh hiệu và chứng chỉ cùng lúc. Bỏ bớt một cái trước nhé.')
            for x in items:
                need(_owns(j, x), 'Bạn chưa có chứng chỉ này.' if x.startswith(CERT_WEAR) else 'Bạn chưa có danh hiệu này.')
            _wear(j, items)
            result['message'] = f'Đang đeo {len(items)}/{WEAR_MAX}.' if items else 'Đã cất hết danh hiệu.'
        else:             # one title (clients from before 1.2): it replaces what is worn
            tid = p.get('title')
            need(tid is None or tid in j['titles'], 'Bạn chưa có danh hiệu này.')
            _wear(j, [tid] if tid else [])
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
            result['message'] = f'{place} tạm đóng. Mở lại lúc nào cũng được, không tốn phí.'
        else:
            need(cid in j['paused'], 'Nơi này đang mở rồi.')
            need(p.get('confirm') is True, 'Xác nhận mở lại nơi này.')
            j['paused'].pop(cid)   # free: a place you were away from never owed anything
            j['stats']['reopened'] += 1
            result['message'] = f'{place} mở cửa lại (không tốn phí).'
    elif name.startswith('jr_cert_'):
        result.update(ct.action(s, name, p))
    elif name.startswith('jr_bk_'):
        result.update(bk.action(s, name, p))
    elif name.startswith('jr_wd_'):
        result.update(wd.action(s, name, p))
    elif name == 'jr_avatar':
        result.update(avt.action(s, name, p))
    elif name.startswith('jr_home_'):
        result.update(hs.action(s, name, p))
    elif name.startswith('jr_hh_'):
        result.update(hh.action(s, name, p))
    elif name.startswith('jr_out_'):
        result.update(outings_.action(s, name, p))
    elif name.startswith('jr_leisure_'):
        result.update(ls.action(s, name, p))
    elif name.startswith('jr_ship_'):
        result.update(ship.action(s, name, p))
    elif name.startswith('jr_reno_'):
        result.update(rn.action(s, name, p))
    elif name.startswith('jr_deco_'):
        result.update(dc.action(s, name, p))
    elif name.startswith('jr_garage_'):
        result.update(gr.action(s, name, p))
    elif name.startswith('jr_gadget_'):
        result.update(gd.action(s, name, p))
    elif name.startswith('jr_lux_'):
        result.update(lx.action(s, name, p))
    elif name.startswith('jr_auc_'):
        result.update(auc.action(s, name, p))
    elif name.startswith('jr_spend_'):
        result.update(sp.action(s, name, p))
    elif name.startswith('jr_pet_'):
        result.update(pt.action(s, name, p))
    elif name.startswith('jr_needs_'):
        result.update(nd.action(s, name, p))
    elif name.startswith('jr_chua_'):
        result.update(cg.action(s, name, p))
    elif name.startswith('jr_relax_'):
        result.update(rx.action(s, name, p))
    elif name.startswith('jr_fridge_'):
        result.update(fr.action(s, name, p))
    elif name.startswith('jr_rui_'):
        result.update(rui.action(s, name, p))
    elif name.startswith('jr_vang_'):
        result.update(vang.action(s, name, p))
    elif name.startswith('jr_quay_'):
        result.update(qy.action(s, name, p))
    elif name.startswith('jr_abroad_'):
        result.update(ab.action(s, name, p))   # ✈️🌏
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
        # upkeep(), withdraw_max() without asking twice
        employed, unpaid = _employed(cid), _unpaid(c)
        places[cid] = dict(fund=c['money'], upkeep=0,   # a place you are away from costs nothing (upkeep())
                           paused=cid in j['paused'], employed=employed, unpaid=unpaid, withdraw_max=max(0, c['money'] - unpaid - RESERVE))
    secret = {tid: dict(name=TITLE_INDEX[tid]['name'], emoji=TITLE_INDEX[tid]['emoji'], desc=TITLE_INDEX[tid]['desc'])
              for tid in j['titles'] if TITLE_INDEX[tid]['secret']}
    eq = TITLE_INDEX.get(j['equipped'])
    return dict(
        story=j['story'], gender=j['gender'], intro=j['intro'], chapter=j['chapter'], done=list(j['done']),
        finale=j['chapter'] > LAST,
        unlocked=list(j['unlocked']) + [cid for cid in aj.opened(s) if cid not in j['unlocked']] if j['story'] else list(s['careers']),
        wallet=j['wallet'], debt=max(0, -j['wallet']), life_day=j['life_day'], living=living_cost(j),
        places=places, titles=sorted(([tid, day] for tid, day in j['titles'].items()), key=lambda x: (-x[1], x[0])),
        equipped=j['equipped'], equipped_title=dict(id=eq['id'], name=eq['name'], emoji=eq['emoji']) if eq else None,
        worn=worn_view(j), wear_max=WEAR_MAX,
        secret=secret, maturity=maturity(ctx['xp']),
        skills=[dict(id=sid, points=ctx['points'].get(sid, 0), level=ctx['sk'].get(sid, 0)) for sid in _skill_ids()],
        goals=_goals_view(ctx, j['chapter']), progress_paused=j['story'] and j['wallet'] < 0 and j['chapter'] <= LAST,
        clean_days=j['clean_days'], history=list(reversed(j['history'][-30:])), news=tree_copy(j['news']),
        suggested=suggested(s, ctx), tasks=ctx['tasks'], worked=ctx['places'],
        stats={k: j['stats'].get(k, 0) for k in ('withdrawn', 'invested', 'living_paid', 'upkeep_paid', 'salary')},
        bank=bk.public(s), home=hs.public(s), household=hh.public(s), outings=outings_.public(s), leisure=ls.public(s), courier=ship.public(s), reno=rn.public(s), deco=dc.public(s),
        garage=gr.public(s), gadgets=gd.public(s), spend=sp.public(s), pets=pt.public(s), lux=lx.public(s), **({'uniq': u} if (u := auc.public(s)) else {}), wed_gift=wl.gift_public(j), **ct.public(s),   # wed_gift False: the client may claim it at a party
        **({'quay': qy.public(s)} if qy.visible(s) else {}),   # 🏪 only once a save reaches it (state size)
        **({'abroad': a} if (a := ab.public(s)) else {}))   # ✈️🌏 story mode


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
        unlock_chapter={cid: n for n, ids in CH_UNLOCKS.items() for cid in ids if cid in CAREERS}, certs=ct.content(),
        wardrobe=wd.content(), homes=hs.catalogue(), reno=rn.catalogue(), deco=dc.catalogue(),
        garage=gr.catalogue(), gadgets=gd.catalogue(), spend=sp.catalogue(), pets=pt.catalogue(), lux=lx.catalogue(), auction=auc.catalogue(), rui=rui.catalogue(), quay=qy.catalogue(), outings=outings_.content(), leisure=ls.content(),
        abroad=ab.catalogue())


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
    need(isinstance(j['worn'], list) and len(j['worn']) <= WEAR_MAX and len(set(map(str, j['worn']))) == len(j['worn'])
         and all(_owns(j, x) for x in j['worn']), 'Danh hiệu đang đeo không hợp lệ.')
    need(isinstance(j['history'], list) and len(j['history']) <= 120, 'Sổ ví không hợp lệ.')
    for row in j['history']:
        need(isinstance(row, dict) and row.get('kind') in HISTORY_KINDS, 'Dòng sổ ví không hợp lệ.')
        integer(row.get('day'), 1, 10**6)
        limit = 10**9 if row.get('kind') == 'bank' else 10**7
        integer(row.get('amount'), -limit, limit)
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
    sg.validate(j)
    lfx.validate(j)
    fh.validate(j)   # 🏮 journey['fair'] (optional)
    wl.gift_validate(j)   # 🎁 journey['wed_gift'] (optional)
    nd.validate(s)   # 🍚😴 journey['needs'] (optional)
    cg.validate(s)   # 🛕 journey['chua'] (optional)
    from . import promotion
    promotion.validate(s)   # 🎖️ journey['promo'] (optional)

    rx.validate(s)   # 🏊 journey['relax'] (optional)
    ls.validate(s)   # 🏝️ journey['leisure'] (optional: only once a leisure round was played)
    fr.validate(s)   # 🧊 journey['fridge'] (optional)
    ct.validate(s)
    bk.validate(s)
    wd.validate(s)
    avt.validate(s)   # 🙂 s['avatar'] (optional)
    hs.validate(s)
    from . import rentals
    rentals.validate(s)
    hh.validate(s)
    outings_.validate(s)
    ship.validate(s)
    rn.validate(s)
    dc.validate(s)
    gr.validate(s)   # 🚗 journey['garage'] (optional)
    gd.validate(s)   # 📱 journey['gadgets'] (optional)
    sp.validate(s)   # ☕ journey['spend'] (optional)
    pt.validate(s)   # 🐾 journey['pets'] (optional)
    lx.validate(s)   # 🛍️ journey['lux'] (optional)
    auc.validate(s)   # 🔨 journey['uniq'] (optional)
    up.validate(s)   # 🧾 journey['upk'] (optional)
    rui.validate(s)   # 🛡️ journey['rui'] (optional)
    vang.validate(s)   # 💰 journey['vang'] (optional)
    qy.validate(s)   # 🏪 journey['quay'] (optional)
    ab.validate(s)   # ✈️🌏 journey['abroad'] (optional)
