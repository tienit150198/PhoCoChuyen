"""Tiệm chụp ảnh Tách Tách: chị Lam's photobooth shop on the street (plugin career).

Chị Lam shot weddings for fifteen years before she opened a little photobooth shop by the night market:
a booth with a curtain, a ring light, a basket of silly props, a dye-sub printer and a wall of sample
strips. The player works the counter and the booth. What the job is:

* the morning (``setup`` task): wipe the lens (dust settles overnight; a dirty lens fogs every photo),
  look at the ink ribbon in the printer (24 prints a roll; change it before it runs out mid-print),
  take a test shot, then open;
* the order, said once at the counter: the package (one 4-cut strip, two strips on one sheet that
  are cut apart, or one big photo in a wooden frame), the frame design (14, drawn by the client's
  photo-frames.js: Tết, Trung thu, hoa sen, phố cổ, phim cũ, dễ thương, cưới, tốt nghiệp, biển,
  mưa Sài Gòn, sinh nhật, đêm hội, mùa phượng, Giáng sinh), the backdrop, the props (hats,
  glasses, a sign, flowers, a balloon, a star lantern), the light, the stickers, the date stamp
  and the colour filter;
* the shutter (a stop tap, kit.tap_now): every shot is a countdown 3-2-1, then the group holds the
  pose with their eyes open for a moment. Shoot in that moment: too early and they are still moving
  (blurry), a little late and someone blinks, later and the pose is gone. Toddlers hold it for a
  shorter moment, grandparents smile a little later and hold it longer. Eight shots a round;
* the choice: show the shots on the screen and the customers say which ones they want; the player
  selects exactly those (a closed-eye or blurry shot in the print is the first thing they see);
* decorating and printing what was asked; a wrong print can be printed again before it is trimmed
  (the sheet is the shop's loss); trimming (cut a double sheet down the middle, a sleeve for every
  strip, the big photo into its frame); handing over; cash through the shared till;
* the apprenticeship: for the first three customers chị Lam looks at the print settings before the
  printer runs and stops each kind of mistake once (nothing recorded, no surprises).

Mistakes go through consequences (cq.slip / cq.react); money only through the engine's money().
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from . import till
from .. import consequences as cq

ID = 'photobooth'
GEN = 1

# ---------------------------------------------------------------- what the shop sells and uses
# Ids match public/js/v4/photo-frames.js (LAYOUTS, FRAMES, BACKDROPS, PROPS, STICKERS, FILTERS).
PKGS = {
    'strip': dict(name='Dải 4 ô', emoji='🎞️', shots=4, paper='giay_dai', sleeves=1, frame=None, cut=False),
    'double': dict(name='2 dải 4 ô', emoji='🎞️', shots=4, paper='giay_doi', sleeves=2, frame=None, cut=True),
    'big': dict(name='Khung lớn', emoji='🖼️', shots=1, paper='giay_lon', sleeves=0, frame='khung', cut=False),
}
FRAMES = {
    'tet': 'Tết sum vầy', 'trung_thu': 'Trung thu', 'hoa_sen': 'Hoa sen', 'pho_co': 'Phố cổ', 'retro': 'Phim cũ',
    'kawaii': 'Dễ thương', 'cuoi': 'Ngày cưới', 'tot_nghiep': 'Tốt nghiệp', 'bien': 'Biển gọi', 'mua_sg': 'Mưa Sài Gòn',
    'sinh_nhat': 'Sinh nhật', 'dem_hoi': 'Đêm hội', 'phuong': 'Mùa phượng', 'giang_sinh': 'Giáng sinh',
}
BACKDROPS = {'kem': 'Phông kem trơn', 'hong': 'Phông hồng phấn', 'mint': 'Phông xanh bạc hà', 'den': 'Phông đen sang',
             'hoa': 'Tường hoa giấy', 'kim_tuyen': 'Rèm kim tuyến'}
PROPS = {'mu_tiec': 'Mũ sinh nhật', 'non_la': 'Nón lá', 'mu_tn': 'Mũ tốt nghiệp', 'tai_tho': 'Bờm tai thỏ', 'vuong_mien': 'Vương miện',
         'kinh_tim': 'Kính trái tim', 'kinh_ram': 'Kính râm', 'bang_chu': 'Bảng chữ', 'hoa': 'Bó hoa', 'bong_bay': 'Bong bóng',
         'long_den': 'Lồng đèn ông sao'}
STICKERS = {'tim': 'Trái tim', 'sao': 'Ngôi sao', 'meo': 'Mặt mèo', 'tho': 'Thỏ con', 'hoa': 'Bông hoa', 'may': 'Đám mây',
            'lap_lanh': 'Lấp lánh', 'vuong_mien': 'Vương miện', 'not_nhac': 'Nốt nhạc', 'cau_vong': 'Cầu vồng'}
FILTERS = {'none': 'Màu gốc', 'den_trang': 'Đen trắng', 'co_dien': 'Cổ điển (nâu)', 'am': 'Nắng ấm', 'lanh': 'Xanh mát',
           'phim': 'Phim cũ', 'hong': 'Hồng mộng mơ'}
LIGHTS = {'diu': 'Đèn dịu', 'sang': 'Đèn sáng', 'am': 'Đèn vàng ấm'}
QUALITY = ('good', 'early', 'blink', 'late')
Q_WORD = {'good': 'đẹp, ai cũng mở mắt', 'early': 'nhòe, cả nhóm còn đang nhúc nhích', 'blink': 'có người nhắm mắt',
          'late': 'hết dáng, có người quay đi'}

ITEMS = [
    dict(id='giay_dai', name='Giấy in dải 5×15', emoji='🎞️', group='giay', unit='tờ', cost=1, start=24),
    dict(id='giay_doi', name='Giấy in tờ đôi 10×15', emoji='📄', group='giay', unit='tờ', cost=2, start=16),
    dict(id='giay_lon', name='Giấy in ảnh lớn 15×20', emoji='🖼️', group='giay', unit='tờ', cost=3, start=8),
    dict(id='khung', name='Khung gỗ 15×20', emoji='🪵', group='khung', unit='cái', cost=5, start=4),
    dict(id='bao', name='Bao kiếng đựng ảnh', emoji='🛍️', group='bao', unit='cái', cost=1, start=30),
    dict(id='muc', name='Cuộn mực in (24 tấm)', emoji='🖨️', group='muc', unit='cuộn', cost=8, start=2),
]
PRICES = dict(strip=14, double=20, big=30)
RIBBON = 24               # prints in one ink roll
RIBBON_LOW = 4            # opening with fewer than this left is a slip
MAX_SHOTS = 8             # shots in one round at the booth
MAX_PROPS = 6
MAX_STICKERS = 8

# The shutter: a countdown, then the moment everyone holds the pose with their eyes open.
COUNT = 3.0               # 3-2-1
HOLD = 1.3                # how long the pose holds (seconds), by group below
BLINK_AFTER = 1.2         # after the moment: someone blinks; later still the pose is gone
RECHARGE = 1.0            # the flash recharges and the group poses again
FIRST_DAYS_WIDE = 1.3     # the first days hold the pose longer


# ---------------------------------------------------------------- the people
PEOPLE = [
    ('Chị Lam', 'Chủ tiệm Tách Tách', 'Chụp ảnh cưới mười lăm năm rồi mới mở tiệm photobooth, nhìn ảnh là biết ai nhắm mắt.', 'warm'),
    ('Bé Nhi', 'Học sinh lớp 11A1', 'Tan học là kéo cả hội bạn mặc nguyên đồng phục vào chụp, mỗi tuần một kiểu.', 'genz'),
    ('Chị Vy', 'Bạn gái anh Khôi', 'Soi từng ô ảnh, ô nào có người nhắm mắt là chị biết liền.', 'picky'),
    ('Ông Chín', 'Hưu trí, đi cùng bà Chín', 'Năm mươi năm cưới nhau, năm nào cũng chụp một tấm treo phòng khách.', 'quiet'),
    ('Chị Trâm', 'Mẹ của bé Gạo ba tuổi', 'Dặn dò kỹ từng thứ; bé Gạo thì không ngồi yên được ba giây.', 'bossy'),
    ('Mẫn', 'Làm clip trên mạng', 'Chê nhanh khen chậm, chụp xong là đăng liền.', 'sour'),
    ('Thầy Phong', 'Giáo viên chủ nhiệm 12A3', 'Dẫn học trò đi chụp kỷ niệm cuối cấp, nói nhỏ nhẹ mà ai cũng nghe.', 'warm'),
]

# How each group looks in the photos (public/js/v4/photo-frames.js paintShot people), by look id.
def _p(age, style, top, skin=0, hair=None, wear='tee', **kw):
    d = dict(age=age, style=style, top=top, skin=skin, wear=wear, **kw)
    if hair:
        d['hair'] = hair
    return d


LOOKS = {
    'na': [_p('teen', 'long', '#ffffff', 0, '#2b1d17', 'uniform'), _p('teen', 'bob', '#ffffff', 1, None, 'uniform'),
           _p('teen', 'spiky', '#ffffff', 2, '#1d1410', 'uniform'), _p('teen', 'pony', '#ffffff', 0, None, 'uniform')],
    'na_aodai': [_p('teen', 'long', '#ffffff', 0, '#2b1d17', 'aodai'), _p('teen', 'bob', '#fdfbf5', 1, None, 'aodai'),
                 _p('teen', 'pony', '#ffffff', 0, None, 'aodai')],
    'khoi': [_p('adult', 'short', '#4a6fa5', 1), _p('adult', 'long', '#e98aa0', 0)],
    'khoi_cuoi': [_p('adult', 'short', '#2d3340', 1, None, 'suit'), _p('adult', 'bun', '#fffdf8', 0, None, 'bride')],
    'bay': [_p('old', 'bald', '#8a6f5a', 1), _p('old', 'bun', '#b24a5a', 0, '#cfc8bd')],
    'bay_tet': [_p('old', 'bald', '#2f5fa8', 1, None, 'aodai'), _p('old', 'bun', '#c0392b', 0, '#cfc8bd', 'aodai')],
    'hanh': [_p('adult', 'bob', '#e2574c', 0), _p('kid', 'pigtails', '#f2c84b', 0, None, 'tee', mouth='grin'), _p('adult', 'short', '#5b8fd1', 2)],
    'man': [_p('adult', 'pony', '#9b6bd1', 0, '#4a2f2a'), _p('adult', 'long', '#3a3a3a', 1, '#6b3f2a')],
    'phong_tn': [_p('adult', 'short', '#ffffff', 1, None, 'suit'), _p('teen', 'long', '#c0392b', 0, None, 'gown'),
                 _p('teen', 'short', '#c0392b', 2, None, 'gown'), _p('teen', 'bob', '#c0392b', 1, None, 'gown')],
    'phong_gv': [_p('adult', 'short', '#6f8f6a', 1), _p('adult', 'bun', '#b3746b', 0), _p('adult', 'bob', '#7a8db3', 2)],
}

# (npc, title, opening, needs, note, min_day, mod) — needs: pkg, frames (any of), bd (any of), props (exactly),
# light, st (stickers asked for), free (other stickers welcome), date, flt, look, sign, check / kid / old.
def _o(pkg, frames, bd, props, light, st=(), free=False, date=True, flt='none', look='na', sign='', **flags):
    return dict(pkg=pkg, frames=list(frames), bd=list(bd), props=sorted(props), light=light, st=list(st), free=free, date=date,
                flt=flt, look=look, sign=sign, check=bool(flags.get('check')), kid=bool(flags.get('kid')), old=bool(flags.get('old')))


ORDERS = [
    (1, 'Hội bạn 11A1 tan học', 'Chị ơi tụi em chụp một dải bốn ô, khung dễ thương, phông hồng nha! Cho tụi em mượn bờm tai thỏ, kính tim với cái bảng chữ!',
     _o('strip', ['kawaii'], ['hong'], ['tai_tho', 'kinh_tim', 'bang_chu'], 'sang', ['tim', 'sao'], True, True, 'none', 'na', 'BFF 11A1'),
     'Bé Nhi dặn: “Dán tim với sao nha chị, thêm gì dễ thương cũng được. Có ngày tháng luôn!”', 1, None),
    (3, 'Ông bà Chín kỷ niệm 50 năm', 'Hai ông bà chụp một tấm khung lớn treo phòng khách. Nền trơn thôi, đèn dịu dịu cho bà khỏi chói mắt.',
     _o('big', ['cuoi', 'hoa_sen'], ['kem'], ['hoa'], 'diu', (), False, True, 'co_dien', 'bay', old=True),
     'Bà Chín cầm bó hoa: “Màu nâu nâu như ảnh cưới hồi xưa nghe con. Đừng dán hình gì hết, ghi ngày là được.”', 1, None),
    (2, 'Anh Khôi chị Vy hẹn hò', 'Hai dải giống nhau nha em, khung phim cũ, phông đen, đèn vàng ấm. Anh đeo kính râm cho ngầu.',
     _o('double', ['retro'], ['den'], ['kinh_ram'], 'am', ['tim'], False, True, 'phim', 'khoi', check=True),
     'Chị Vy nói nhỏ: “Màu phim cũ, một cái tim thôi, có ngày tháng. Ô nào ảnh nhắm mắt là chị không lấy đâu nha.”', 1, None),
    (4, 'Bé Gạo tròn ba tuổi', 'Một dải bốn ô khung sinh nhật, phông xanh bạc hà. Cho bé đội mũ sinh nhật, cầm bong bóng nhé.',
     _o('strip', ['sinh_nhat'], ['mint'], ['mu_tiec', 'bong_bay'], 'sang', ['sao', 'tho'], True, True, 'none', 'hanh', kid=True),
     'Chị Trâm dặn: “Dán sao với thỏ, có ngày tháng. Bé Gạo không ngồi yên đâu, canh nhanh tay giùm chị.”', 2, None),
    (5, 'Mẫn quay clip đi chơi', 'Một dải, khung đêm hội, rèm kim tuyến, đèn sáng. Cho tôi cái vương miện.',
     _o('strip', ['dem_hoi'], ['kim_tuyen'], ['vuong_mien'], 'sang', ['lap_lanh'], True, False, 'hong', 'man', check=True),
     'Mẫn bấm điện thoại: “Màu hồng mộng mơ, dán lấp lánh. Khỏi ghi ngày, đăng lên nhìn quê lắm.”', 2, None),
    (1, 'Hội bạn chụp mùa phượng', 'Tụi em mặc áo dài trắng chụp kỷ niệm, khung mùa phượng, tường hoa giấy nha chị! Mỗi đứa cầm một bó hoa.',
     _o('strip', ['phuong'], ['hoa'], ['hoa'], 'am', ['hoa', 'may'], True, True, 'am', 'na_aodai'),
     'Bé Nhi: “Màu nắng ấm, dán hoa với mây, có ngày tháng để mai mốt nhớ!”', 2, None),
    (6, 'Lớp 12A3 chụp kỷ yếu', 'Thầy với mấy em chụp hai dải, khung tốt nghiệp. Phông kem, đèn sáng, đội mũ tốt nghiệp, cầm bảng tên lớp.',
     _o('double', ['tot_nghiep', 'phuong'], ['kem'], ['mu_tn', 'bang_chu'], 'sang', ['sao'], False, True, 'none', 'phong_tn', '12A3 ♥'),
     'Thầy Phong: “Dán một ngôi sao, ghi ngày cho các em nhớ. Màu để nguyên nhé.”', 3, None),
    (2, 'Anh Khôi trú mưa', 'Mưa quá, hai đứa vô chụp một dải cho vui. Khung mưa Sài Gòn, phông xanh bạc hà.',
     _o('strip', ['mua_sg'], ['mint'], [], 'diu', ['may'], True, True, 'lanh', 'khoi', check=True),
     'Chị Vy: “Đèn dịu thôi, màu xanh mát, dán đám mây. Khỏi đạo cụ, tóc ướt rồi.”', 2, 'rain'),
    (3, 'Ông bà Chín chụp ảnh Tết', 'Tết này ông bà mặc áo dài chụp một tấm khung lớn khung Tết. Tường hoa, đèn vàng cho ấm.',
     _o('big', ['tet'], ['hoa'], ['non_la'], 'am', (), False, False, 'none', 'bay_tet', old=True),
     'Ông Chín: “Bà đội nón lá cho có Tết. Đừng dán gì, đừng ghi ngày, màu để y vậy.”', 2, 'le_hoi'),
    (4, 'Bé Gạo rước đèn Trung thu', 'Một dải khung Trung thu, phông đen cho lồng đèn nổi. Bé cầm lồng đèn ông sao.',
     _o('strip', ['trung_thu'], ['den'], ['long_den'], 'am', ['sao'], True, True, 'none', 'hanh', kid=True),
     'Chị Trâm: “Đèn vàng ấm, dán sao, có ngày tháng. Canh lúc bé nhìn máy nha!”', 3, 'le_hoi'),
    (2, 'Anh Khôi cầu hôn', 'Em ơi, một tấm khung lớn, khung cưới, rèm kim tuyến. Anh cầm bó hoa, cô ấy đội vương miện. Đèn dịu thôi.',
     _o('big', ['cuoi'], ['kim_tuyen'], ['hoa', 'vuong_mien'], 'diu', ['tim'], False, True, 'none', 'khoi', check=True),
     'Anh Khôi nháy mắt: “Một trái tim thôi, có ngày hôm nay. Nhắm mắt là hỏng cả đời đó em.”', 4, None),
    (5, 'Mẫn đi biển về', 'Hai dải khung biển, phông xanh bạc hà, đeo kính râm. Đèn sáng.',
     _o('double', ['bien'], ['mint'], ['kinh_ram'], 'sang', ['may', 'lap_lanh'], True, False, 'lanh', 'man', check=True),
     'Mẫn: “Màu xanh mát, dán mây với lấp lánh, khỏi ngày tháng.”', 3, 'weekend'),
    (6, 'Thầy cô đi phố cổ về', 'Mấy thầy cô chụp một dải khung phố cổ cho vui. Phông kem, đèn dịu, khỏi đạo cụ.',
     _o('strip', ['pho_co'], ['kem'], [], 'diu', (), False, True, 'den_trang', 'phong_gv'),
     'Thầy Phong: “Đen trắng cho có nét xưa, đừng dán gì, ghi ngày là được.”', 3, None),
    (1, 'Hội bạn đi hội đêm', 'Chị ơi một dải khung đêm hội, phông đen, đèn sáng! Kính tim với mũ sinh nhật cho vui!',
     _o('strip', ['dem_hoi'], ['den'], ['kinh_tim', 'mu_tiec'], 'sang', ['not_nhac', 'lap_lanh'], True, True, 'none', 'na'),
     'Bé Nhi: “Dán nốt nhạc với lấp lánh, có ngày tháng nha!”', 2, 'weekend'),
    (4, 'Cả nhà chụp Giáng sinh', 'Hai dải khung Giáng sinh, phông kem, bé đội vương miện. Đèn vàng ấm.',
     _o('double', ['giang_sinh'], ['kem'], ['vuong_mien'], 'am', ['sao'], True, True, 'none', 'hanh', kid=True),
     'Chị Trâm: “Dán sao, có ngày tháng, gửi ông bà một dải.”', 3, 'le_hoi'),
    (1, 'Tan trường chụp vội', 'Chị ơi một dải bốn ô, khung gì dễ thương cũng được, phông hồng hay bạc hà đều được! Bờm tai thỏ nha!',
     _o('strip', ['kawaii', 'phuong', 'sinh_nhat'], ['hong', 'mint'], ['tai_tho'], 'sang', (), True, True, 'none', 'na'),
     'Bé Nhi: “Dán gì cũng được, có ngày tháng là được, nhanh nhanh tụi em còn học thêm!”', 2, 'tan_truong'),
]
KINDS = ('setup', 'serve')
STAGES = ('prep', 'pay', 'done')

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Khách lai rai: học sinh tan học, cặp đôi buổi tối.', weight=3),
    dict(id='weekend', emoji='🛍️', label='Cuối tuần', hint='Hội bạn rủ nhau đi chơi, hay lấy hai dải.', min_day=2, weight=2),
    dict(id='rain', emoji='🌧️', label='Mưa chiều', hint='Hơi nước bám ống kính: lau lại giữa buổi. Khách trú mưa ghé chụp.', min_day=2, weight=2),
    dict(id='le_hoi', emoji='🏮', label='Mùa lễ hội', hint='Khung Tết, Trung thu, Giáng sinh được hỏi nhiều.', min_day=2, weight=2),
    dict(id='tan_truong', emoji='🎒', label='Tan trường', hint='Học sinh ùa vào lúc năm giờ, chụp vội rồi đi học thêm.', min_day=2, weight=2),
]
MOD = {m['id']: m for m in MODS}

# Regulars' small stories: one line per finished visit.
REG_STORY = {
    1: ('Bé Nhi dán dải ảnh lên bìa vở: “Cả lớp hỏi chụp ở đâu đó chị!”', 'Bé Nhi kể hội bạn đặt tên nhóm là “Tách Tách 11A1”.',
        'Bé Nhi mang tặng tiệm một bức vẽ cả hội đội tai thỏ.', 'Bé Nhi thi học kỳ xong, dẫn thêm hai bạn lớp bên qua chụp.'),
    2: ('Chị Vy kẹp dải ảnh vào ốp điện thoại.', 'Anh Khôi hỏi nhỏ giá khung lớn, mắt nhìn chị Vy.',
        'Chị Vy khen: “Ô nào cũng mở mắt, đỉnh!”', 'Anh Khôi chị Vy gửi thiệp cưới, mời cả tiệm.'),
    3: ('Bà Chín kể tấm ảnh năm ngoái treo ngay cạnh bàn thờ ông bà.', 'Ông Chín mang biếu tiệm một bịch mứt gừng bà làm.',
        'Ông Chín: “Năm mươi năm rồi mà bà vẫn cười như hồi con gái.”'),
    4: ('Bé Gạo đòi lấy cái bờm tai thỏ về, chị Trâm phải dỗ mãi.', 'Chị Trâm khoe dải ảnh dán trên tủ lạnh, ông bà ngoại thích lắm.',
        'Bé Gạo lần này ngồi yên được tới số một rồi mới cười.'),
    5: ('Mẫn đăng clip, ghim tên tiệm: “Ok, cũng được.”', 'Mẫn rủ thêm hai bạn làm clip tới chụp.',
        'Mẫn khen thật: “Chỗ này chụp không ai nhắm mắt, hiếm à nha.”'),
    6: ('Thầy Phong treo dải ảnh lớp lên bảng tin.', 'Thầy Phong kể có em xin thêm một dải gửi bố mẹ đang làm xa.',
        'Thầy Phong: “Mấy đứa nói tấm này là kỷ yếu đẹp nhất.”'),
}

INTRO = dict(
    title='Giới thiệu nghề: nhân viên photobooth',
    lead='Một buồng chụp có rèm, cây đèn vòng, rổ đạo cụ và cái máy in ảnh nhỏ ở góc phố chợ đêm. '
         'Chị Lam chụp ảnh cưới mười lăm năm mới mở tiệm, giờ bạn đứng quầy với chị.',
    work=[('🧽', 'Sáng: lau ống kính, xem cuộn mực in, chụp thử'), ('📋', 'Nghe khách: gói ảnh, khung, phông, đạo cụ, đèn'),
          ('⏱️', 'Đếm 3-2-1 rồi bấm chụp đúng lúc cả nhóm mở mắt, giữ dáng'), ('🖼️', 'Cho khách xem, chọn đúng những tấm khách chọn'),
          ('✨', 'Dán sticker, đóng ngày, chọn màu theo lời dặn'), ('🖨️', 'In, cắt, bỏ bao kiếng hoặc lồng khung'),
          ('💵', 'Thu tiền, thối đúng')],
    meet=[('🎒', 'Bé Nhi và hội bạn 11A1 mặc đồng phục'), ('💑', 'Anh Khôi và chị Vy: soi từng con mắt'),
          ('👴', 'Ông bà Chín: mỗi năm một tấm khung lớn'), ('🎈', 'Chị Trâm với bé Gạo ba tuổi không ngồi yên'),
          ('📱', 'Mẫn làm clip, chê nhanh khen chậm'), ('🎓', 'Thầy Phong dẫn lớp 12A3 chụp kỷ yếu')],
    stars=[('😊', 'Ô nào cũng mở mắt, nét'), ('🖼️', 'Đúng gói, đúng khung, đúng phông'), ('🎩', 'Đủ đạo cụ, đúng đèn'),
           ('✨', 'Sticker, ngày tháng, màu đúng ý'), ('✂️', 'Cắt gọn, bỏ bao kiếng'), ('⏱️', 'Nhanh gọn'), ('💵', 'Thối đúng tiền')],
)

# ---------------------------------------------------------------- học nghề: the first customers with chị Lam
APPRENTICE = 3
LESSONS = [
    ('Bài 1 · Bấm đúng lúc', 'Chị Lam đứng sau máy: “Đếm 3-2-1 xong cả nhóm mới đứng yên. Vạch xanh là lúc ai cũng mở mắt, bấm ngay lúc đó.”'),
    ('Bài 2 · Khách chọn ảnh', 'Chị Lam dặn: “Chụp xong mời khách xem, khách chọn tấm nào thì in tấm đó. Tấm nhắm mắt đừng bao giờ in.”'),
    ('Bài 3 · Đúng lời dặn', 'Chị Lam nhắc: “Gói nào, khung nào, sticker gì, có ngày không, màu gì: nghe một lần là nhớ. In rồi mà sai là mất giấy.”'),
]
CATCH = {
    'pkg': 'Khoan, khách mua gói khác mà con. Coi lại phiếu rồi chọn đúng gói hẵng in.',
    'frame': 'Khung này khách đâu có chọn. Đổi khung đi con.',
    'bad_shot': 'Dừng! Có tấm nhắm mắt hay nhòe trong bản in kìa. Bỏ tấm đó ra, chọn tấm đẹp.',
    'choice': 'Khách chọn mấy tấm khác mà con. Chọn lại đúng tấm khách chọn.',
    'no_choice': 'Chưa mời khách xem ảnh mà in rồi sao. Bấm “Cho khách xem” đã con.',
    'backdrop': 'Mấy tấm này chụp nhầm phông rồi. Đổi phông, chụp lại vài kiểu.',
    'props': 'Đạo cụ chưa đúng lời khách dặn. Sửa lại rồi chụp thêm.',
    'light': 'Đèn chưa đúng ý khách. Chỉnh đèn rồi chụp lại.',
    'sticker': 'Sticker chưa đúng lời dặn kìa con. Coi lại phiếu.',
    'date': 'Khách dặn ngày tháng mà con làm ngược rồi.',
    'filter': 'Màu chưa đúng khách dặn. Chọn lại màu.',
    'haze': 'Ảnh mờ quá, ống kính bẩn rồi. Lau ống kính rồi chụp lại.',
}

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='lost_phone', title='Điện thoại bỏ quên trong buồng', emoji='📱', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Dọn buồng chụp thì thấy một cái điện thoại hồng kẹt dưới ghế. Màn hình sáng lên: “Mẹ gọi”.',
         options=[dict(id='keep', label='Cất ở quầy, nghe máy báo người nhà tới lấy', hint='', effects=dict(xp=4), good=True,
                       outcome='Mười phút sau cô bé chạy lại, mếu máo cảm ơn. Mẹ cô bé còn gửi lời cảm ơn tiệm.'),
                  dict(id='post', label='Chụp hình đăng nhóm khu phố tìm chủ', hint='', effects=dict(xp=1), good=None,
                       outcome='Bài đăng có người chia sẻ, tối đó chủ máy tới lấy.'),
                  dict(id='drawer', label='Bỏ vô ngăn kéo, ai hỏi thì đưa', hint='', effects=dict(review=[2, 'Bỏ quên điện thoại ở tiệm, gọi mãi không ai nghe máy, hú hồn.']),
                       good=False, outcome='Điện thoại reo cả buổi trong ngăn kéo. Hôm sau chủ máy mới dò tới.')],
         default='drawer'),
    dict(id='stranger_copy', title='Người lạ xin ảnh của khách', emoji='🙅', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Một anh đứng chờ nãy giờ hỏi nhỏ: “Gửi anh file mấy em vừa chụp được không? Anh trả thêm.”',
         options=[dict(id='no', label='Từ chối: ảnh của ai người đó giữ, tiệm không đưa cho ai', hint='', effects=dict(xp=5), good=True,
                       outcome='Anh ta lầm bầm bỏ đi. Chị Lam gật đầu: “Đúng rồi, ảnh khách là của khách.”'),
                  dict(id='ask', label='Bảo anh tự đi hỏi mấy em đó', hint='', effects=dict(patience=-2), good=None,
                       outcome='Mấy em nghe xong sợ, đi về vội.'),
                  dict(id='give', label='Gửi file cho anh, thêm tiền thì thêm', hint='+10 xu',
                       effects=dict(money=10, review=[1, 'Tiệm đưa ảnh của con tôi cho người lạ. Không thể chấp nhận được!']), good=False,
                       outcome='Tối đó phụ huynh của mấy em gọi điện tới tiệm, giọng run run.')],
         default='ask'),
    dict(id='paper_jam', title='Kẹt giấy trong máy in', emoji='🖨️', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Máy in kêu “rẹt” một tiếng rồi đứng hình. Đèn đỏ nháy: kẹt giấy.',
         options=[dict(id='gentle', label='Tắt máy, mở khay, rút giấy thẳng tay theo chiều in', hint='Mất một tờ giấy',
                       effects=dict(stock={'giay_dai': -1}, xp=3), good=True, outcome='Tờ giấy ra nguyên vẹn mép, máy in chạy lại êm ru.'),
                  dict(id='yank', label='Giật mạnh tờ giấy ra cho nhanh', hint='',
                       effects=dict(stock={'giay_dai': -2}, patience=-3), good=False, outcome='Giấy rách kẹt lại một mẩu, phải tháo nửa cái máy.'),
                  dict(id='call', label='Gọi chị Lam ra coi giùm', hint='Khách chờ lâu', effects=dict(patience=-4, xp=1), good=None,
                       outcome='Chị Lam gỡ trong năm phút, chỉ cho bạn cách mở khay.')],
         default='call'),
    dict(id='kid_light', title='Bé con nghịch đèn vòng', emoji='💡', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một bé chạy vào buồng chụp, níu cái chân đèn vòng lắc qua lắc lại. Cây đèn chao đảo.',
         options=[dict(id='hold', label='Giữ chân đèn, dắt bé ra chỗ mẹ, khóa chân đèn lại', hint='', effects=dict(xp=4), good=True,
                       outcome='Đèn đứng vững. Mẹ bé xin lỗi rối rít, bé được cho cầm thử cái bờm tai thỏ.'),
                  dict(id='shout', label='La lớn cho bé sợ mà buông', hint='', effects=dict(review=[3, 'Nhân viên la con nít to quá, bé khóc cả đường về.']),
                       good=False, outcome='Bé buông tay, khóc òa. Cả tiệm quay lại nhìn.'),
                  dict(id='ignore', label='Kệ, đèn chắc mà', hint='', luck=dict(p=0.5,
                       win=dict(effects={}, good=None, outcome='Bé chán rồi tự chạy đi.'),
                       lose=dict(effects=dict(money=-6), good=False, outcome='Đèn ngã, vỡ một bóng. Thay bóng mới hết sáu xu.')), effects={})],
         default='ignore'),
    dict(id='free_post', title='Đòi chụp miễn phí để đăng bài', emoji='🎥', npc=5, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một nhóm cầm gậy quay: “Tụi mình có trang mấy chục nghìn người theo dõi. Cho chụp free một lượt, tụi mình đăng khen tiệm.”',
         options=[dict(id='price', label='Mời chụp đúng giá, tặng thêm một sticker đặc biệt', hint='', effects=dict(xp=3, money=6), good=True,
                       outcome='Nhóm đó trả tiền, chụp vui, đăng clip khen khung đêm hội.'),
                  dict(id='free', label='Cho chụp free cho được việc', hint='Mất giấy', effects=dict(stock={'giay_dai': -1}), good=None,
                       outcome='Clip lên, nói vài câu rồi lướt qua tiệm khác.'),
                  dict(id='shoo', label='“Muốn free thì qua tiệm khác”', hint='', effects=dict(review=[2, 'Hỏi có một câu mà bị đuổi, né tiệm này nha.']),
                       good=False, outcome='Họ quay luôn cảnh bị đuổi, đăng lên mạng.')],
         default='price'),
    dict(id='leak', title='Mưa dột trên buồng chụp', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=('rain',),
         text='Mưa lớn, mái tôn nhỏ giọt ngay trên mép phông. Một vệt nước loang dần xuống tấm phông kem.',
         options=[dict(id='bucket', label='Kê xô hứng, kéo phông lùi vào, lau khô đèn', hint='Khách chờ một chút', effects=dict(patience=-3, xp=3), good=True,
                       outcome='Phông khô ráo, đèn không dính nước. Chị Lam gọi thợ sửa mái ngày mai.'),
                  dict(id='later', label='Chụp tiếp, lát mưa tạnh rồi lau', hint='', effects=dict(money=-4), good=None,
                       outcome='Tấm phông ố một vệt, phải đem đi giặt.')],
         default='later'),
    dict(id='delete', title='Xin xóa ảnh trong máy', emoji='🗑️', npc=2, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Một cô gái quay lại quầy: “Hôm trước em với bạn trai chụp ở đây… giờ chia tay rồi. Tiệm còn giữ ảnh không, xóa giùm em.”',
         options=[dict(id='delete', label='Mở máy, xóa trước mặt cô ấy, cho coi thư mục trống', hint='', effects=dict(xp=4), good=True,
                       outcome='Cô gái thở phào: “Cảm ơn tiệm.” Chị Lam dặn: máy chỉ giữ ảnh tới cuối ngày rồi xóa hết.'),
                  dict(id='later', label='Hẹn khi rảnh sẽ xóa', hint='', effects=dict(review=[3, 'Nhờ xóa ảnh mà hẹn lần hẹn lữa.']), good=None,
                       outcome='Cô gái đi về, vẫn chưa yên tâm.'),
                  dict(id='keep', label='“Ảnh đẹp mà, giữ làm mẫu treo tường”', hint='',
                       effects=dict(review=[1, 'Xin xóa ảnh riêng mà tiệm còn đòi treo lên tường làm mẫu.']), good=False,
                       outcome='Cô gái giận đỏ mặt bỏ đi.')],
         default='later'),
    dict(id='prop_broken', title='Gãy càng kính trái tim', emoji='😍', npc=1, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Hội bạn trả đạo cụ, cái kính trái tim gãy một bên càng. Mấy em nhìn nhau lo lắng.',
         options=[dict(id='glue', label='Cười trấn an, dán lại bằng keo, nhắc lần sau nhẹ tay', hint='', effects=dict(xp=3), good=True,
                       outcome='Kính dán lại vẫn đeo được. Mấy em xin lỗi rối rít.'),
                  dict(id='charge', label='Bắt đền cái kính', hint='+3 xu', effects=dict(money=3, review=[3, 'Kính nhựa gãy càng cũng bắt đền, hơi căng.']), good=None,
                       outcome='Mấy em gom tiền lẻ đền, mặt buồn hiu.')],
         default='glue'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='PB-S01', title='Xin ảnh của người yêu cũ', npc=2, tone='tense', min_day=1,
         opening='Một anh tới quầy: “Tuần trước bạn gái cũ của anh chụp ở đây với bạn. Em gửi anh mấy tấm đó, anh chỉ muốn giữ làm kỷ niệm.”',
         swap='Bạn là cô gái trong ảnh: chụp với bạn thân cho vui, không hề muốn người cũ có ảnh của mình.',
         facts=[dict(id='owner', title='Ảnh của ai', source='Sổ tiệm', text='Ảnh do cô gái và bạn chụp, trả tiền; anh này không có trong ảnh.'),
                dict(id='rule', title='Lời chị Lam', source='Chị Lam', text='Máy chỉ giữ ảnh tới cuối ngày rồi xóa; không đưa ảnh của khách cho người khác.'),
                dict(id='mood', title='Anh ấy', source='Quầy', text='Anh ta nói nhỏ nhẹ, nhưng hỏi đi hỏi lại giờ cô gái hay ghé.')],
         options=[dict(id='refuse', label='Từ chối nhẹ nhàng, không nói gì về cô gái, báo chị Lam', requires=['owner', 'rule'], quality='good', stars=5,
                       review='Tiệm giữ ảnh khách kỹ, ai hỏi cũng không đưa. Yên tâm chụp ở đây.',
                       outcome='Anh ta đi về. Chị Lam dặn cả tiệm: ai hỏi lịch khách cũng không nói.',
                       perspectives=[dict(who='Cô gái', emoji='🙂', text='Biết vậy càng yên tâm rủ bạn tới chụp.'),
                                     dict(who='Chị Lam', emoji='📷', text='Ảnh của khách là chuyện riêng của khách.')]),
                  dict(id='ask_her', label='Hứa sẽ hỏi cô gái giùm anh', requires=['owner'], quality='ok', stars=3,
                       review='Tiệm không đưa ảnh, nhưng lại đi hỏi chuyện riêng của khách giùm người khác.',
                       outcome='Cô gái nghe xong thấy ngại, ít ghé hơn.',
                       perspectives=[dict(who='Cô gái', emoji='😟', text='Sao tiệm lại nhắn chuyện này cho mình…'),
                                     dict(who='Anh ấy', emoji='😐', text='Ít ra tiệm cũng hỏi giùm.')]),
                  dict(id='give', label='Còn ảnh trong máy thì gửi một tấm, chắc không sao', quality='bad', stars=1,
                       review='Tiệm gửi ảnh của tôi cho người tôi không muốn gặp. Thật đáng sợ.',
                       outcome='Cô gái biết chuyện, làm đơn phản ánh lên phường.',
                       perspectives=[dict(who='Cô gái', emoji='😨', text='Mình không còn dám đi chụp ở đâu nữa.'),
                                     dict(who='Chị Lam', emoji='📷', text='Một tấm ảnh đưa sai người là mất cả tiệm.')])],
         lesson='Ảnh của khách là của khách: không đưa cho ai, không kể lịch khách ghé. Máy xóa ảnh cuối ngày.'),
    dict(id='PB-S02', title='Ô ảnh nhắm mắt', npc=5, tone='tense', min_day=2,
         opening='Mẫn quay lại quầy, chìa dải ảnh: “Ô thứ ba bạn tôi nhắm mắt. Tiệm in vậy mà cũng đưa? Trả tiền lại đi.”',
         facts=[dict(id='strip', title='Dải ảnh', source='Soi kỹ', text='Ô thứ ba đúng là có một người nhắm mắt; ba ô kia đẹp.'),
                dict(id='screen', title='Máy chụp', source='Máy tính', text='Trong máy còn ba tấm đẹp khác của lượt đó, chưa xóa.'),
                dict(id='rule', title='Lời chị Lam', source='Chị Lam', text='Ảnh lỗi do tiệm thì in lại miễn phí; tiền thì không nhất thiết hoàn.')],
         options=[dict(id='reprint', label='Xin lỗi, in lại dải mới với tấm đẹp thay ô nhắm mắt', requires=['strip', 'screen'], quality='good', stars=4,
                       review='Ô ảnh lỗi thật, nhưng tiệm in lại liền, không cãi một câu.',
                       outcome='Mẫn nhận dải mới, gật gù: “Vậy còn được.”',
                       perspectives=[dict(who='Mẫn', emoji='📱', text='Sai mà sửa liền thì tôi vẫn quay lại.'),
                                     dict(who='Chị Lam', emoji='📷', text='Một tờ giấy rẻ hơn một khách quen.')]),
                  dict(id='refund', label='Trả lại hết tiền cho nhanh', requires=['strip'], quality='ok', stars=3,
                       review='Trả tiền thì trả, nhưng tôi muốn có ảnh đẹp cơ.',
                       outcome='Mẫn cầm tiền đi về, không có ảnh đẹp nào.',
                       perspectives=[dict(who='Mẫn', emoji='😑', text='Tiền thì có, ảnh thì không.'),
                                     dict(who='Chị Lam', emoji='📷', text='Trong máy còn tấm đẹp mà con.')]),
                  dict(id='deny', label='“Lúc chụp bạn chị nhắm mắt chứ đâu phải tại tiệm”', quality='bad', stars=1,
                       review='In tấm nhắm mắt rồi còn đổ cho khách. Né.',
                       outcome='Mẫn quay luôn cảnh cãi nhau, đăng lên mạng.',
                       perspectives=[dict(who='Mẫn', emoji='😠', text='Đã sai còn cãi.'),
                                     dict(who='Bé Nhi', emoji='🎒', text='Tụi em coi clip rồi… hơi ngại.')])],
         lesson='Chọn ảnh là cho khách chọn và soi từng con mắt trước khi in. Lỗi của tiệm thì in lại liền.'),
    dict(id='PB-S03', title='Đăng ảnh học trò lên trang tiệm', npc=0, tone='gentle', min_day=3,
         opening='Chị Lam ngắm dải ảnh hội 11A1: “Dễ thương quá, đăng lên trang tiệm làm mẫu ha?”',
         facts=[dict(id='minor', title='Ai trong ảnh', source='Phiếu', text='Cả bốn em đều mười sáu tuổi, mặc đồng phục có tên trường.'),
                dict(id='consent', title='Đã hỏi chưa', source='Quầy', text='Chưa ai hỏi các em hay bố mẹ các em có đồng ý không.'),
                dict(id='other', title='Ảnh mẫu khác', source='Máy tính', text='Tiệm có ảnh mẫu của chính chị Lam và nhân viên.')],
         options=[dict(id='ask', label='Không đăng; dùng ảnh mẫu của tiệm, lần sau hỏi các em và phụ huynh trước', requires=['minor', 'consent'],
                       quality='good', stars=5, review='Tiệm không tự ý đăng ảnh học sinh, phụ huynh rất yên tâm.',
                       outcome='Chị Lam gật đầu, treo ảnh mẫu của cả tiệm đội tai thỏ.',
                       perspectives=[dict(who='Bé Nhi', emoji='🎒', text='May quá, ảnh đó tụi em làm mặt xấu mà.'),
                                     dict(who='Chị Trâm', emoji='👩', text='Có con nhỏ mới thấy chuyện này quan trọng.')]),
                  dict(id='blur', label='Đăng nhưng che mặt, che tên trường', requires=['minor'], quality='ok', stars=3,
                       review='Che mặt rồi nhưng vẫn là ảnh của tụi nhỏ, chưa ai hỏi.',
                       outcome='Bài đăng ít người xem. Một phụ huynh nhắn hỏi đó có phải con mình không.',
                       perspectives=[dict(who='Bé Nhi', emoji='😕', text='Nhìn cái bờm là biết tụi em rồi.'),
                                     dict(who='Chị Lam', emoji='📷', text='Che mặt chưa phải là đã xin phép.')]),
                  dict(id='post', label='Đăng luôn, ảnh đẹp mà', quality='bad', stars=1,
                       review='Ảnh con tôi mặc đồng phục bị đăng công khai mà không ai hỏi một câu.',
                       outcome='Phụ huynh gọi điện, chị Lam phải gỡ bài và xin lỗi.',
                       perspectives=[dict(who='Phụ huynh', emoji='😠', text='Ảnh trẻ con có tên trường, ai cũng tìm ra được.'),
                                     dict(who='Bé Nhi', emoji='😳', text='Cả trường thấy hết rồi…')])],
         lesson='Ảnh của khách, nhất là trẻ vị thành niên, chỉ đăng khi đã hỏi và được đồng ý.'),
]


# ================================================================ small helpers
def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Khách'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _p_(c: dict, key: str) -> int:
    return max(1, int(kit.price(c, key, PRICES[key])))


def _names(ids, table) -> str:
    return ', '.join(_lower(table[x]) for x in ids) if ids else 'không'


def order_text(n: dict) -> str:
    """The order in one line (the ticket, the hint, reviews)."""
    pk = PKGS[n['pkg']]['name']
    fr = ' hoặc '.join(FRAMES[x] for x in n['frames'])
    bd = ' hoặc '.join(_lower(BACKDROPS[x]) for x in n['bd'])
    props = _names(n['props'], PROPS)
    st = ('dán ' + _names(n['st'], STICKERS) + (' (thêm gì cũng được)' if n['free'] else '')) if n['st'] else (
        'dán gì cũng được' if n['free'] else 'không dán sticker')
    return (f'{pk}, khung {fr}, {bd}, đạo cụ: {props}, {_lower(LIGHTS[n["light"]])}, {st}, '
            f'{"có" if n["date"] else "không"} ngày tháng, {flt_text(n["flt"])}')


def flt_text(f: str) -> str:
    return 'giữ màu gốc' if f == 'none' else f'màu {_lower(FILTERS[f])}'


# ================================================================ tasks
def _order_for(day: int, slot: int, mod: str) -> tuple:
    if day == 1:
        return ORDERS[(slot - 1) % 3]
    pool = [o for o in ORDERS if o[5] <= day and o[6] in (None, mod)]
    weighted = [o for o in pool for _ in range(3 if o[6] else 1)]
    return weighted[kit.rng(ID, day, slot).randrange(len(weighted))]


def _fresh_fields() -> dict:
    return dict(gen=GEN, stage='prep', set=dict(pkg=None, frame=None, bd=None, light=None, props=[]), cam=None, shots=[], want=None,
                pick=[], deco=dict(st=[], date=False, flt='none'), printed=None, prints=0, trim=False, redo=0,
                price=None, cash=None, cost=0, choice=None, story=None)


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    if slot == 0:
        note = {'rain': 'Mưa chiều: hơi nước dễ bám ống kính.', 'le_hoi': 'Mùa lễ hội: khách hỏi khung Tết, Trung thu, Giáng sinh.',
                'weekend': 'Cuối tuần: hội bạn kéo nhau tới, chuẩn bị giấy tờ đôi.'}.get(mod, 'Lau ống kính, xem cuộn mực, chụp thử rồi mở tiệm.')
        return kit.base_task(ID, day, slot, serial, 0, 'Mở tiệm photobooth đầu ngày',
                             'Chị Lam nhắn: “Chị đi lấy khung gỗ. Em lau ống kính, xem cuộn mực in, chụp thử một tấm rồi hẵng mở tiệm nghe.”',
                             kind='setup', needs=dict(setup=True, note=note), **_fresh_fields())
    npc, title, opening, needs, note, _, _ = _order_for(day, slot, mod)
    n = copy.deepcopy(needs)
    n['note'] = note
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='serve', needs=n, **_fresh_fields())


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the shop's data
def _fresh_booth(day: int) -> dict:
    return dict(day=day, open=False, lens=False, tested=False, fog=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, shots=0, good=0, customers=0, prints=0, reprints=0, wasted=0)


def initial() -> dict:
    return dict(v=1, intro=False, booth=_fresh_booth(0), ribbon=3, regulars={}, today=_fresh_today(0),
                stats=dict(shots=0, good=0, customers=0, prints=0, reprints=0, fair=0), desk=kit.desk_initial(),
                learn=dict(task=None, codes=[], done=False))


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'booth', 'learn'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


# ================================================================ the shutter
def hold_of(t: dict, day: int) -> tuple[float, float]:
    """(when the pose starts after the countdown, how long it holds), for this customer's group."""
    n = t['needs']
    lead = 0.2 + (_hash('pb-lead', t['id']) % 5) / 10           # 0.2–0.6 s
    hold = HOLD
    if n.get('kid'):
        hold = 0.85
    if n.get('old'):
        lead += 0.6
        hold = 1.7
    if kit.tier(day) == 0:
        hold *= FIRST_DAYS_WIDE
    return round(lead, 2), round(hold, 2)


def judge(t: dict, day: int, elapsed: float) -> str:
    lead, hold = hold_of(t, day)
    a = COUNT + lead
    if elapsed < a:
        return 'early'
    if elapsed <= a + hold:
        return 'good'
    if elapsed <= a + hold + BLINK_AFTER:
        return 'blink'
    return 'late'


# ================================================================ the actions
FREE = ('pb_intro',)
NO_TICK = ('pb_intro', 'pb_desk', 'pb_lens', 'pb_test', 'pb_pkg', 'pb_frame', 'pb_bd', 'pb_prop', 'pb_light', 'pb_snap', 'pb_stop',
           'pb_pick', 'pb_sticker', 'pb_date', 'pb_filter', 'pb_short', 'pb_pay')
PHYSICAL = ('pb_shoot', 'pb_redo', 'pb_print', 'pb_trim', 'pb_ribbon')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'pb_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Buồng chụp đang chờ, đèn vòng đã cắm điện.')
    desk = d['desk']
    if name == 'pb_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở tiệm, quyết xong rồi chụp tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tiệm chụp ảnh.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    if learning(d):
        return             # no surprises while chị Lam is still teaching
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm chụp ảnh.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_open(d: dict) -> None:
    _open_rules(d)


def _open_rules(d: dict, setup=None, need=kit.need) -> None:
    """The shop must be open before any customer's work (live 04-06/10: refusals on the first tap of a customer
    picked before “Mở tiệm”). public_data sends it as can.open, with a fix that brings up the morning set-up."""
    need(d['booth']['open'], 'Chưa mở tiệm: lau ống kính, xem cuộn mực, chụp thử rồi bấm “Mở tiệm” nhé.',
         fix=dict(cmd='task_select', payload=dict(task=setup), label='🏪 Mở tiệm') if setup else None)


def _setup_id(c: dict):
    """Today's open set-up task (the morning chores), if any."""
    return next((t['id'] for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup'
                 and t.get('status') not in ('completed', 'referred', 'cancelled')), None)


def _need_prep(t: dict) -> None:
    kit.need(t['known'], 'Hỏi khách muốn chụp gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Khách này đã nhận ảnh rồi.')


def _need_unprinted(t: dict, what: str) -> None:
    kit.need(not t['trim'], f'Ảnh đã cắt rồi, không đổi {what} được nữa.')


# ---------------------------------------------------------------- the morning and the printer
def _lens(s, c, d, p):
    b = d['booth']
    was = b['lens'] and not b['fog']
    b['lens'], b['fog'] = True, False
    return dict(message='🧽 Lau ống kính bằng khăn mềm theo vòng tròn.' + (' Ống kính vốn đã sạch.' if was else ' Sạch bóng, không còn vệt mờ.'))


def _ribbon(s, c, d, p):
    kit.need(kit.stock(c, 'muc') > 0, 'Hết cuộn mực trong kho rồi. Nhập thêm ở Kho nhé.')
    left = d['ribbon']
    cost = kit.take(c, 'muc', 1)
    if left > 0:
        kit.waste(c, 'muc', 1, cost * left // RIBBON if cost else 0, 'Cuộn mực thay khi còn dư')
    d['ribbon'] = RIBBON
    return dict(message=f'🖨️ Thay cuộn mực mới: in được {RIBBON} tấm.' + (f' Cuộn cũ còn {left} tấm thì bỏ.' if left else ''))


def _test(s, c, d, p):
    b = d['booth']
    b['tested'] = True
    lens = 'ảnh thử nét căng, màu trong.' if b['lens'] and not b['fog'] else 'ảnh thử mờ một mảng như có sương: ống kính bám bụi.'
    rib = d['ribbon']
    ink = f' Máy in báo cuộn mực còn {rib} tấm.' + (' Sắp hết rồi, thay cuộn mới đi.' if rib < RIBBON_LOW + 4 else '')
    return dict(message=f'📸 Chụp thử phông trống: {lens}{ink}')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    b = d['booth']
    kit.need(not b['open'], 'Tiệm mở rồi.')
    if not b['lens']:
        t['mistakes'] += 1
        cq.slip(t, 'lens', 1, 'Ống kính chưa lau, ảnh nào cũng mờ mờ như có sương.', 'chưa lau ống kính')
    if not b['tested']:
        t['mistakes'] += 1
        cq.slip(t, 'no_test', 1, 'Chưa chụp thử đã mở tiệm, máy có vấn đề gì cũng không biết.', 'chưa chụp thử')
    if d['ribbon'] < RIBBON_LOW:
        t['mistakes'] += 1
        cq.slip(t, 'ribbon', 1, 'Cuộn mực sắp hết mà không thay, in tới khách thứ hai là hết.', 'cuộn mực sắp hết')
    b['open'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Lau ống kính, xem cuộn mực, chụp thử.')
    return dict(message='📸 Mở tiệm! ' + ('Chị Lam nhắn: “Giỏi lắm, hôm nay chụp đẹp nha!”' if ok else 'Chị Lam nhắn: “Mở đi em, mai nhớ kỹ hơn nghe.”'),
                celebrate=ok)


# ---------------------------------------------------------------- setting up the booth for an order
def _set_one(s, c, d, p, key, table, word):
    t = _task(c, p, ('serve',))
    _need_open(d)
    _need_prep(t)
    v = kit.one_of(p.get(key), table, f'{word} không có ở tiệm.')
    st = t['set']
    field = {'pkg': 'pkg', 'frame': 'frame', 'bd': 'bd', 'light': 'light'}[key]
    if field in ('pkg', 'frame'):
        _need_unprinted(t, word.lower())
    st[field] = v
    kit.start_work(t)
    if field == 'pkg':
        x = PKGS[v]
        return dict(message=f'{x["emoji"]} Gói {_lower(x["name"])}: chụp {x["shots"]} tấm đẹp để in.')
    if field == 'frame':
        return dict(message=f'🖼️ Chọn khung {FRAMES[v]}.')
    if field == 'bd':
        return dict(message=f'🎨 Kéo {_lower(BACKDROPS[v])} xuống sau ghế chụp.')
    return dict(message=f'💡 Chỉnh {_lower(LIGHTS[v])}.')


def _prop(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_open(d)
    _need_prep(t)
    v = kit.one_of(p.get('prop'), PROPS, 'Rổ đạo cụ không có món này.')
    props = t['set']['props']
    kit.start_work(t)
    if v in props:
        props.remove(v)
        return dict(message=f'↩️ Cất {_lower(PROPS[v])} lại vào rổ.')
    kit.need(len(props) < MAX_PROPS, 'Cầm nhiều quá rồi, cất bớt đạo cụ đi.')
    props.append(v)
    props.sort()
    return dict(message=f'🎩 Đưa khách {_lower(PROPS[v])}.')


# ---------------------------------------------------------------- the shutter
def _shoot(s, c, d, p):
    """Start the countdown (or start it again after a stop)."""
    t = _task(c, p, ('serve',))
    _need_open(d)
    _need_prep(t)
    st = t['set']
    kit.need(st['bd'] and st['light'], 'Chọn phông và đèn trước khi chụp nhé.')
    kit.need(len(t['shots']) < MAX_SHOTS, f'Lượt này đã đủ {MAX_SHOTS} tấm. Cho khách xem, hoặc xóa để chụp lượt mới.')
    kit.need(t['cam'] is None, 'Máy đang đếm rồi, canh lúc bấm chụp.')
    kit.need(not t['printed'], 'Ảnh đã in rồi.')
    t['cam'] = dict(start=round(kit.now(), 3))
    kit.start_work(t)
    return dict(message='⏱️ 3… 2… 1… Cả nhóm vào dáng! Bấm chụp lúc ai cũng đứng yên, mở mắt.')


def _snap(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_prep(t)
    cam = t['cam']
    kit.need(isinstance(cam, dict), 'Máy chưa đếm. Bấm “Bắt đầu chụp” trước đã.')
    at = kit.tap_now(p)
    el = max(0.0, at - cam['start'])
    q = judge(t, c['day'], el)
    st = t['set']
    n = len(t['shots'])
    who = _hash('pb-who', t['id'], n) % max(1, len(LOOKS.get(t['needs'].get('look'), [1])))
    t['shots'].append(dict(q=q, bd=st['bd'], light=st['light'], props=list(st['props']), haze=not d['booth']['lens'] or d['booth']['fog'], who=who))
    d['today']['shots'] += 1
    d['stats']['shots'] += 1
    if q == 'good':
        d['today']['good'] += 1
        d['stats']['good'] += 1
    left = MAX_SHOTS - len(t['shots'])
    t['cam'] = dict(start=round(at + RECHARGE, 3)) if left > 0 else None
    word = {'good': '📸 Tách! Đẹp: ai cũng mở mắt, dáng chuẩn.', 'early': '📸 Tách… sớm quá, cả nhóm còn đang nhúc nhích: ảnh nhòe.',
            'blink': '📸 Tách… trễ một nhịp, có người chớp mắt.', 'late': '📸 Tách… trễ quá, hết dáng rồi, có người quay đi.'}[q]
    tail = f' Còn {left} kiểu, máy đếm lại.' if left > 0 else ' Hết lượt tám kiểu: mời khách xem ảnh.'
    if d['booth']['fog'] or not d['booth']['lens']:
        tail += ' ⚠️ Ảnh hơi mờ: ống kính cần lau.'
    return dict(message=word + tail, correct=q == 'good' or None)


def _stop(s, c, d, p):
    t = _task(c, p, ('serve',))
    kit.need(t['cam'] is not None, 'Máy đâu có đang đếm.')
    t['cam'] = None
    return dict(message='⏸️ Tạm dừng máy, cả nhóm thả lỏng.')


def _redo(s, c, d, p):
    """Clear the round and shoot again (the group is getting tired of smiling)."""
    t = _task(c, p, ('serve',))
    _need_prep(t)
    kit.need(t['shots'], 'Chưa có tấm nào để xóa.')
    kit.need(not t['printed'], 'Ảnh đã in rồi.')
    t['shots'], t['want'], t['pick'], t['cam'] = [], None, [], None
    t['redo'] = min(9, t['redo'] + 1)
    return dict(message='🔄 Xóa lượt cũ, mời khách vào chụp lượt mới. Cả nhóm xoa xoa má cho đỡ mỏi miệng cười.')


def _need_k(t: dict) -> int:
    return PKGS[t['needs']['pkg']]['shots']


def _show(s, c, d, p):
    """The customers look at the shots on the screen and say which ones they want."""
    t = _task(c, p, ('serve',))
    _need_prep(t)
    kit.need(t['shots'], 'Chưa chụp tấm nào.')
    t['cam'] = None
    k = _need_k(t)
    if t['want'] is not None:
        return dict(message=f'🖥️ {_who(t)} chọn rồi: tấm {", ".join(str(i + 1) for i in t["want"])}.')
    good = [i for i, x in enumerate(t['shots']) if x['q'] == 'good']
    if len(good) < k:
        need = k - len(good)
        left = MAX_SHOTS - len(t['shots'])
        more = (f'chụp thêm giùm {need} tấm nha' if left >= need else 'lượt này hết chỗ rồi, xóa chụp lại giùm')
        return dict(message=f'🖥️ {_who(t)} xem xong: “Mới có {len(good)} tấm đẹp, {more}.”', correct=False)
    ranked = sorted(good, key=lambda i: _hash('pb-like', t['id'], i))
    t['want'] = sorted(ranked[:k])
    kit.start_work(t)
    return dict(message=f'🖥️ {_who(t)} chụm đầu xem màn hình: “Lấy tấm {", ".join(str(i + 1) for i in t["want"])} nha!”')


def _pick(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_prep(t)
    _need_unprinted(t, 'ảnh')
    i = kit.integer(p.get('i'), 0, max(0, len(t['shots']) - 1))
    kit.need(i < len(t['shots']), 'Không có tấm này.')
    if i in t['pick']:
        t['pick'].remove(i)
        return dict(message=f'↩️ Bỏ chọn tấm {i + 1}.')
    k = _need_k(t)
    _pick_rules(t)
    t['pick'].append(i)
    t['pick'].sort()
    return dict(message=f'☑️ Chọn tấm {i + 1} ({len(t["pick"])}/{k}).')


# ---------------------------------------------------------------- decorating
def _sticker(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_prep(t)
    _need_unprinted(t, 'sticker')
    v = kit.one_of(p.get('st'), STICKERS, 'Không có sticker này.')
    sts = t['deco']['st']
    if v in sts:
        sts.remove(v)
        return dict(message=f'↩️ Gỡ sticker {_lower(STICKERS[v])}.')
    kit.need(len(sts) < MAX_STICKERS, 'Dán nhiều quá rồi, che mất mặt khách.')
    sts.append(v)
    return dict(message=f'✨ Dán sticker {_lower(STICKERS[v])}.')


def _date(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_prep(t)
    _need_unprinted(t, 'ngày tháng')
    on = p.get('on')
    kit.need(type(on) is bool, 'Có đóng ngày hay không?')
    t['deco']['date'] = on
    return dict(message='📅 Đóng ngày tháng góc ảnh.' if on else '📅 Bỏ ngày tháng.')


def _filter(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_prep(t)
    _need_unprinted(t, 'màu')
    v = kit.one_of(p.get('flt'), FILTERS, 'Không có màu này.')
    t['deco']['flt'] = v
    return dict(message=f'🎨 Chọn màu {_lower(FILTERS[v])}.')


# ---------------------------------------------------------------- what the customer will notice
def print_slips(t: dict, picked: list | None = None) -> list[tuple]:
    """(code, weight, the customer's words, short note, safety) for what is wrong with the print as set now."""
    n, st, de = t['needs'], t['set'], t['deco']
    picked = t['pick'] if picked is None else picked
    shots = [t['shots'][i] for i in picked if i < len(t['shots'])]
    out = []
    if st['pkg'] != n['pkg']:
        out.append(('pkg', 2, f'Tôi lấy {_lower(PKGS[n["pkg"]]["name"])} mà in ra {_lower(PKGS[st["pkg"]]["name"])}.', 'sai gói ảnh'))
    if st['frame'] not in n['frames']:
        out.append(('frame', 1, f'Tôi chọn khung {FRAMES[n["frames"][0]]} mà.', 'sai khung'))
    bad = [x for x in shots if x['q'] != 'good']
    if bad:
        q = bad[0]['q']
        out.append(('bad_shot', 3 if n.get('check') else 2,
                    {'blink': 'Ô ảnh có người nhắm mắt mà cũng in!', 'early': 'Ô ảnh nhòe nhoẹt, cả nhóm như bóng ma.',
                     'late': 'Ô ảnh có đứa quay đi chỗ khác, mất dáng rồi.'}[q], 'in ảnh hỏng'))
    if t['want'] is None:
        out.append(('no_choice', 1, 'Không cho tụi tôi xem chọn ảnh gì hết.', 'không cho khách chọn ảnh'))
    elif sorted(picked) != sorted(t['want']) and not bad:
        out.append(('choice', 1, 'Tụi tôi chọn mấy tấm khác mà.', 'in không đúng tấm khách chọn'))
    if any(x['bd'] not in n['bd'] for x in shots):
        out.append(('backdrop', 1, f'Tôi muốn {_lower(BACKDROPS[n["bd"][0]])} cơ.', 'sai phông'))
    if any(sorted(x['props']) != sorted(n['props']) for x in shots):
        out.append(('props', 1, 'Đạo cụ không đúng như tôi dặn.' if n['props'] else 'Tôi đâu có cầm đạo cụ gì.', 'sai đạo cụ'))
    if any(x['light'] != n['light'] for x in shots):
        out.append(('light', 1, {'diu': 'Đèn chói quá, chụp ai cũng nheo mắt.', 'sang': 'Ảnh tối thui.', 'am': 'Màu da xanh xao, không ấm như tôi muốn.'}[n['light']],
                    'sai đèn'))
    if any(x['haze'] for x in shots):
        out.append(('haze', 1, 'Ảnh mờ mờ như chụp qua cửa kính đọng hơi nước.', 'ống kính bẩn, ảnh mờ'))
    sts = set(de['st'])
    if not set(n['st']) <= sts:
        out.append(('sticker', 1, f'Tôi dặn dán {_names(n["st"], STICKERS)} mà.', 'thiếu sticker khách dặn'))
    elif sts - set(n['st']) and not n['free']:
        out.append(('sticker', 1, 'Tôi đâu có kêu dán thêm mấy cái này.' if n['st'] else 'Tôi dặn đừng dán gì mà.', 'dán sticker khách không muốn'))
    if de['date'] != n['date']:
        out.append(('date', 1, 'Tôi dặn ghi ngày tháng mà.' if n['date'] else 'Ghi ngày chi vậy, tôi dặn đừng ghi.', 'ngày tháng sai lời dặn'))
    if de['flt'] != n['flt']:
        out.append(('filter', 1, f'Tôi muốn {flt_text(n["flt"])} mà.', 'sai màu'))
    return out


def learning(d: dict) -> bool:
    """Học nghề: the first APPRENTICE customers, chị Lam at your side."""
    return not d['learn']['done'] and d['stats']['customers'] < APPRENTICE


def _catch(d: dict, t: dict) -> dict | None:
    """While learning, chị Lam looks at the print settings before the printer runs: the first time a kind of
    mistake shows she stops you and says how to fix it (nothing recorded). The same mistake again goes through."""
    if not learning(d):
        return None
    lr = d['learn']
    if lr['task'] != t['id']:
        lr['task'], lr['codes'] = t['id'], []
    for code, *_ in print_slips(t):
        if code in CATCH and code not in lr['codes']:
            lr['codes'].append(code)
            return dict(message=f'📷 Chị Lam: “{CATCH[code]}”', correct=False, lesson=code)
    return None


# ---------------------------------------------------------------- printing, trimming, handing over
def _print(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_open(d)
    _need_prep(t)
    st = t['set']
    kit.need(st['pkg'], 'Chọn gói ảnh trước đã.')
    kit.need(st['frame'], 'Chọn khung ảnh trước đã.')
    k = PKGS[st['pkg']]['shots']
    kit.need(len(t['pick']) == k, f'Gói {_lower(PKGS[st["pkg"]]["name"])} in {k} tấm: chọn đủ {k} tấm trước.')
    kit.need(not t['trim'], 'Ảnh đã cắt xong rồi.')
    paper = PKGS[st['pkg']]['paper']
    kit.need(kit.stock(c, paper) > 0, f'Hết {_lower(kit.item(ID, paper)["name"])} rồi. Nhập thêm ở Kho, hoặc nói thật với khách.')
    kit.need(d['ribbon'] > 0, 'Máy in báo hết mực: thay cuộn mực mới đã.')
    caught = _catch(d, t)
    if caught:
        return caught
    t['cam'] = None
    old = t['printed']
    if old:   # the earlier sheet goes in the bin
        lost = old.get('cost', 0)
        if lost:
            kit.waste(c, old['paper'], 1, lost, 'Ảnh in lại')
        t['cost'] = max(0, t['cost'] - lost)
        d['today']['reprints'] += 1
        d['stats']['reprints'] += 1
    cost = kit.take(c, paper, 1)
    d['ribbon'] -= 1
    t['cost'] += cost
    t['printed'] = dict(pkg=st['pkg'], frame=st['frame'], pick=list(t['pick']), st=list(t['deco']['st']), date=t['deco']['date'],
                        flt=t['deco']['flt'], paper=paper, cost=cost)
    t['prints'] = min(20, t['prints'] + 1)
    d['today']['prints'] += 1
    d['stats']['prints'] += 1
    kit.start_work(t)
    how = 'cắt đôi theo vạch, mỗi dải một bao kiếng' if PKGS[st['pkg']]['cut'] else 'lồng vào khung gỗ' if st['pkg'] == 'big' else 'cắt rìa, bỏ bao kiếng'
    low = f' ⚠️ Cuộn mực còn {d["ribbon"]} tấm.' if d['ribbon'] < RIBBON_LOW else ''
    return dict(message=f'🖨️ Máy in rè rè… tấm ảnh {"in lại " if old else ""}trồi ra, màu lên dần. Giờ {how}.{low}')


def _trim_rules(c: dict, pkg: str, need=kit.need) -> None:
    """The frame and the sleeves a package takes. pb_trim refuses with these; public_data sends them per package
    as can.pb_trim (live 06/10: 669 refusals “Hết khung gỗ rồi”)."""
    x = PKGS[pkg]
    shop = dict(act='inventory', label='📦 Kho')
    if x['frame']:
        need(kit.stock(c, x['frame']) > 0, 'Hết khung gỗ rồi. Nhập thêm ở Kho nhé.', fix=shop)
    need(kit.stock(c, 'bao') >= x['sleeves'], 'Hết bao kiếng rồi. Nhập thêm ở Kho nhé.', fix=shop)


def _pick_rules(t: dict, need=kit.need) -> None:
    """One more shot for the package (a picked one can always be unpicked). pb_pick refuses with it; public_task
    sends it as can.pb_pick (live 06/10: 445 refusals “Gói này in # tấm thôi”)."""
    k = _need_k(t)
    need(len(t['pick']) < k, f'Gói này in {k} tấm thôi. Bỏ chọn bớt rồi chọn tấm khác.')


def _trim(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_prep(t)
    pr = t['printed']
    kit.need(pr, 'Chưa in ảnh.')
    kit.need(not t['trim'], 'Cắt xong rồi.')
    x = PKGS[pr['pkg']]
    _trim_rules(c, pr['pkg'])
    cost = 0
    if x['frame']:
        cost += kit.take(c, x['frame'], 1)
    if x['sleeves']:
        cost += kit.take(c, 'bao', x['sleeves'])
    t['cost'] += cost
    t['trim'] = True
    msg = {'strip': '✂️ Cắt rìa dải ảnh thẳng tắp, bỏ vào bao kiếng.', 'double': '✂️ Cắt đôi tờ ảnh đúng vạch giữa, hai dải hai bao kiếng.',
           'big': '🪵 Lau kính, lồng tấm ảnh vào khung gỗ, đóng nẹp sau lưng.'}[pr['pkg']]
    return dict(message=msg)


def _serve(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_open(d)
    _need_prep(t)
    kit.need(t['printed'], 'Chưa in ảnh.')
    kit.need(t['trim'], 'Cắt ảnh, bỏ bao (hoặc lồng khung) trước khi đưa khách.')
    pr = t['printed']
    for code, weight, words, note in print_slips(t, pr['pick']):
        t['mistakes'] += 1
        cq.slip(t, code, weight, words, note)
    # what was printed decides the price: a wrong package is charged at the cheaper of the two
    price = min(_p_(c, pr['pkg']), _p_(c, t['needs']['pkg']))
    t['price'] = price
    t['stage'] = 'pay'
    t['cash'] = till.new(price, t['id'], c=c, t=t)
    rec = t['cash']
    head = f'🖼️ Đưa ảnh cho {_who(t)} · {price} xu.'
    if not cq.slips(t):
        head += f' {_who(t)} xem ảnh, cười tít: “Đẹp quá trời!”'
    return dict(message=f'{head} Khách đưa {sum(rec["tender"])} xu: thối lại cho đúng.')


def _decline(s, c, d, p):
    """Out of paper or frames: say so honestly."""
    t = _task(c, p, ('serve',))
    kit.need(t['known'] and t['stage'] == 'prep', 'Không phải lúc này.')
    if t['printed'] and t['printed'].get('cost'):
        kit.waste(c, t['printed']['paper'], 1, t['printed']['cost'], 'Ảnh không giao được')
    t['cost'], t['choice'], t['cam'] = 0, 'decline', None
    kit.start_work(t)
    msg = _finish(s, c, d, t, 0, f'Nói thật với {_who(t)}: tiệm hết vật tư cho gói này, hẹn hôm sau.')
    return dict(message='🙏 ' + msg)


def _pay(s, c, d, p):
    t = _task(c, p, ('serve',))
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    react = cq.react(s, c, t, t['price'], who=who)
    stl = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - stl['loss']
    d['today']['customers'] += 1
    d['stats']['customers'] += 1
    if not cq.slips(t):
        d['stats']['fair'] += 1
    fog_tick(c, d)
    parts = [x for x in (react['message'], stl['message']) if x]
    msg = _finish(s, c, d, t, max(0, net), ' '.join(parts))
    if net < 0:
        lost = min(-net, c['money'])
        if lost:
            kit.money(s, c, -lost, f'Thối dư cho khách: {t["title"]}'[:120], t['id'], 'change_loss')
    given = sum(rec['change'])
    head = f'💵 Thu {t["price"]} xu' + (f', thối {given} xu.' if given else '.')
    grad = _graduate(s, d)
    return dict(message=f'{head} {msg}{grad}'.strip(), celebrate=not cq.slips(t) or bool(grad))


def _short(s, c, d, p):
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    return till.short_action(s, c, t, t['cash'], p, _who(t))


def _graduate(s: dict, d: dict) -> str:
    if d['learn']['done'] or d['stats']['customers'] < APPRENTICE:
        return ''
    d['learn'].update(done=True, task=None, codes=[])
    return ' 🎓 Học nghề xong! Chị Lam: “Giờ em tự đứng máy được rồi. Chị ra sau dán khung mẫu đây.”'


def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str) -> str:
    i = _npc_index(t)
    story = ''
    if i in REG_STORY and t['kind'] != 'setup':
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        lines = REG_STORY[i]
        story = lines[min(r['visits'], len(lines)) - 1]
        t['story'] = story
    t['stage'] = 'done'
    t['cam'] = None
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


ACTIONS = {
    'pb_lens': _lens, 'pb_ribbon': _ribbon, 'pb_test': _test, 'pb_open': _open,
    'pb_pkg': lambda s, c, d, p: _set_one(s, c, d, p, 'pkg', PKGS, 'Gói ảnh'),
    'pb_frame': lambda s, c, d, p: _set_one(s, c, d, p, 'frame', FRAMES, 'Khung'),
    'pb_bd': lambda s, c, d, p: _set_one(s, c, d, p, 'bd', BACKDROPS, 'Phông'),
    'pb_light': lambda s, c, d, p: _set_one(s, c, d, p, 'light', LIGHTS, 'Đèn'),
    'pb_prop': _prop, 'pb_shoot': _shoot, 'pb_snap': _snap, 'pb_stop': _stop, 'pb_redo': _redo, 'pb_show': _show, 'pb_pick': _pick,
    'pb_sticker': _sticker, 'pb_date': _date, 'pb_filter': _filter, 'pb_print': _print, 'pb_trim': _trim, 'pb_serve': _serve,
    'pb_decline': _decline, 'pb_pay': _pay, 'pb_short': _short,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['booth'] = _fresh_booth(day)
    d['today'] = _fresh_today(day)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    setup = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if setup is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        setup = make_task(day, 0, c['turn'])
        c['tasks'].append(setup)
        on_task(s, c, setup)
    if setup:
        c['active_task'] = setup['id']
        setup['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def fog_tick(c: dict, d: dict) -> None:
    """A rainy afternoon: steam settles on the lens once, after the second customer."""
    if mod_of(c['day'])['id'] == 'rain' and d['today']['customers'] == 2 and d['booth']['lens'] and not d['booth']['fog'] \
            and not d['today'].get('fogged'):
        d['booth']['fog'] = True
        d['today']['fogged'] = 1


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    lines = [f'📸 Chụp {today["shots"]} kiểu cho {today["customers"]} lượt khách, in {today["prints"]} tấm.']
    if today['shots']:
        rate = today['good'] * 100 // max(1, today['shots'])
        lines.append(f'⏱️ {today["good"]}/{today["shots"]} kiểu bấm đúng lúc ({rate}%).' +
                     (' Chị Lam: “Tay bấm chắc rồi đó!”' if rate >= 70 else ' Chị Lam: “Canh vạch xanh, đừng vội.”'))
    if today['reprints']:
        lines.append(f'🗑️ In lại {today["reprints"]} lần: giấy đó tiệm chịu.')
    if desk_note:
        lines.append(desk_note)
    d['booth'].update(open=False)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('cam'):
            t['cam'] = None
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS}
    tm = mod_of(c['day'] + 1)
    return dict(tomorrow=dict(emoji=tm['emoji'], label=tm['label'], hint=tm['hint']), lines=lines, note=f'Cuộn mực còn {d["ribbon"]} tấm · giấy dải {stock["giay_dai"]}, tờ đôi {stock["giay_doi"]}, '
                                  f'ảnh lớn {stock["giay_lon"]}, khung {stock["khung"]}, bao {stock["bao"]}.',
                shots=today['shots'], good=today['good'], customers=today['customers'], prints=today['prints'], ribbon=d['ribbon'],
                low=[x['id'] for x in ITEMS if stock[x['id']] <= (1 if x['id'] in ('muc', 'khung') else 4)])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        cam = 5 - len(codes & {'lens', 'no_test'})
        ink = 3 if 'ribbon' in codes else 5
        return dict(criteria=[dict(key='camera', label='Máy ảnh sẵn sàng', score=max(2, cam), note='lau kính, chụp thử' if cam == 5 else 'còn sót khâu chuẩn bị'),
                              dict(key='printer', label='Máy in đủ mực', score=ink, note='cuộn mực đủ dùng' if ink == 5 else 'mực sắp hết')])
    if t.get('choice') == 'decline':
        return dict(criteria=[dict(key='honest', label='Nói thật', score=5, note='hết vật tư thì nói thật'),
                              dict(key='order', label='Có ảnh đúng ý', score=3, note='lần này chưa có')])
    order = 2 if 'pkg' in codes else 3 if 'frame' in codes else 4 if codes & {'backdrop', 'choice', 'no_choice'} else 5
    shot = 1 if 'bad_shot' in codes and t['needs'].get('check') else 2 if 'bad_shot' in codes else 3 if codes & {'haze', 'light'} else 5
    deco = 5 - min(3, len(codes & {'sticker', 'date', 'filter', 'props'}))
    return dict(criteria=[dict(key='order', label='Đúng gói, đúng khung', score=order, note='đúng như đã chọn' if order == 5 else 'chưa đúng gói, khung'),
                          dict(key='shot', label='Ảnh đẹp, ai cũng mở mắt', score=shot, note='ô nào cũng đẹp' if shot == 5 else
                               'có ô nhắm mắt, nhòe' if 'bad_shot' in codes else 'ảnh mờ, sai đèn'),
                          dict(key='deco', label='Trang trí đúng ý', score=deco, note='sticker, ngày, màu đúng lời dặn' if deco == 5 else 'trang trí chưa đúng ý'),
                          dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return 'Chị Lam dặn: lau ống kính, xem cuộn mực in (sắp hết thì thay), chụp thử một tấm rồi mở tiệm. ' + n['note']
    tail = ' Khách soi ảnh rất kỹ.' if n.get('check') else ''
    tail += ' Có bé nhỏ, khó ngồi yên.' if n.get('kid') else ''
    tail += ' Ông bà cười chậm, giữ dáng lâu.' if n.get('old') else ''
    return f'{_who(t)} muốn: {order_text(n)}.{tail} {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    elif v['kind'] == 'serve':
        lead, hold = hold_of(t, t['day'])
        v['beat'] = dict(count=COUNT, lead=lead, hold=hold, blink=BLINK_AFTER, recharge=RECHARGE)
        v['can'] = dict(pb_pick=kit.check(_pick_rules, t))
    v['cash'] = till.public(t.get('cash'))
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS} if c['ext'].get('inv') else {}
    on = not d['learn']['done'] and d['stats']['customers'] < APPRENTICE
    n = min(d['stats']['customers'], APPRENTICE - 1)
    return dict(intro=d['intro'], booth=d['booth'], ribbon=d['ribbon'], stock=stock,
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID),
                can=dict(pb_trim={k: kit.check(_trim_rules, c, k) for k in PKGS}, open=kit.check(_open_rules, d, _setup_id(c))),
                learn=dict(on=on, n=d['stats']['customers'], of=APPRENTICE, title=LESSONS[n][0] if on else None, text=LESSONS[n][1] if on else None))


def content() -> dict:
    return dict(pkgs=PKGS, frames=FRAMES, backdrops=BACKDROPS, props=PROPS, stickers=STICKERS, filters=FILTERS, lights=LIGHTS,
                looks=LOOKS, q_word=Q_WORD, prices=PRICES, ribbon=RIBBON, ribbon_low=RIBBON_LOW, max_shots=MAX_SHOTS,
                max_props=MAX_PROPS, max_stickers=MAX_STICKERS, intro=INTRO, apprentice=APPRENTICE,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE], denoms=list(till.DENOMS))


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'setup':
        return 'Lau ống kính → xem cuộn mực (sắp hết thì thay) → chụp thử → Mở tiệm.'
    return ('Hỏi khách → gói, khung, phông, đạo cụ, đèn → bấm chụp lúc vạch xanh → cho khách xem, chọn đúng tấm → '
            'sticker, ngày, màu → in → cắt, bỏ bao → đưa ảnh → thu tiền.')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'lens':
        d['booth']['lens'], d['booth']['fog'] = True, False
        return 'Đã lau ống kính, xếp lại rổ đạo cụ.'
    if e.get('role') == 'call':
        return 'Đã mời khách xếp hàng, phát phiếu chọn khung.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tiệm chụp ảnh sai.')


def _vnum(x, lo, hi) -> None:
    kit.need(type(x) in (int, float) and lo <= x <= hi, 'Dữ liệu tiệm chụp ảnh sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc tiệm chụp ảnh không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc tiệm chụp ảnh sai.')
    st = t.get('set')
    kit.need(isinstance(st, dict) and set(st) == {'pkg', 'frame', 'bd', 'light', 'props'}, 'Cài đặt buồng chụp sai.')
    for k, table in (('pkg', PKGS), ('frame', FRAMES), ('bd', BACKDROPS), ('light', LIGHTS)):
        kit.need(st[k] is None or st[k] in table, 'Cài đặt buồng chụp sai.')
    kit.need(isinstance(st['props'], list) and len(st['props']) <= MAX_PROPS and len(set(st['props'])) == len(st['props'])
             and set(st['props']) <= set(PROPS), 'Đạo cụ sai.')
    cam = t.get('cam')
    if cam is not None:
        kit.need(isinstance(cam, dict) and set(cam) == {'start'}, 'Máy chụp sai.')
        _vnum(cam['start'], 0, 10 ** 11)
    shots = t.get('shots')
    kit.need(isinstance(shots, list) and len(shots) <= MAX_SHOTS, 'Ảnh đã chụp sai.')
    for x in shots:
        kit.need(isinstance(x, dict) and set(x) == {'q', 'bd', 'light', 'props', 'haze', 'who'} and x['q'] in QUALITY and x['bd'] in BACKDROPS
                 and x['light'] in LIGHTS and isinstance(x['props'], list) and len(x['props']) <= MAX_PROPS and set(x['props']) <= set(PROPS),
                 'Ảnh đã chụp sai.')
        _vbool(x['haze'])
        kit.integer(x['who'], 0, 10)
    n = len(shots)
    want = t.get('want')
    kit.need(want is None or (isinstance(want, list) and len(want) <= 4 and all(type(i) is int and 0 <= i < n for i in want)), 'Ảnh khách chọn sai.')
    pick = t.get('pick')
    kit.need(isinstance(pick, list) and len(pick) <= 4 and len(set(pick)) == len(pick) and all(type(i) is int and 0 <= i < max(n, 1) for i in pick),
             'Ảnh đã chọn sai.')
    de = t.get('deco')
    kit.need(isinstance(de, dict) and set(de) == {'st', 'date', 'flt'} and isinstance(de['st'], list) and len(de['st']) <= MAX_STICKERS
             and len(set(de['st'])) == len(de['st']) and set(de['st']) <= set(STICKERS) and de['flt'] in FILTERS, 'Trang trí ảnh sai.')
    _vbool(de['date'])
    pr = t.get('printed')
    if pr is not None:
        kit.need(isinstance(pr, dict) and set(pr) == {'pkg', 'frame', 'pick', 'st', 'date', 'flt', 'paper', 'cost'} and pr['pkg'] in PKGS
                 and pr['frame'] in FRAMES and pr['flt'] in FILTERS and pr['paper'] in {x['paper'] for x in PKGS.values()}
                 and isinstance(pr['pick'], list) and len(pr['pick']) <= 4 and all(type(i) is int and 0 <= i < max(n, 1) for i in pr['pick'])
                 and isinstance(pr['st'], list) and len(pr['st']) <= MAX_STICKERS and set(pr['st']) <= set(STICKERS), 'Ảnh đã in sai.')
        _vbool(pr['date'])
        kit.integer(pr['cost'], 0, 10000)
    kit.integer(t.get('prints'), 0, 20)
    _vbool(t.get('trim'))
    kit.integer(t.get('redo'), 0, 9)
    if t.get('price') is not None:
        kit.integer(t['price'], 0, 10 ** 6)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    kit.need(t.get('choice') in (None, 'decline'), 'Cách giải quyết sai.')
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    till.validate_book(c)
    b = d['booth']
    kit.need(isinstance(b, dict) and set(b) == {'day', 'open', 'lens', 'tested', 'fog'}, 'Buồng chụp sai.')
    kit.integer(b['day'], 0, 10 ** 7)
    for k in ('open', 'lens', 'tested', 'fog'):
        _vbool(b[k])
    kit.integer(d['ribbon'], 0, RIBBON)
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'task', 'codes', 'done'}, 'Học nghề sai.')
    kit.need(lr['task'] is None or (isinstance(lr['task'], str) and len(lr['task']) <= 80), 'Học nghề sai.')
    kit.need(isinstance(lr['codes'], list) and len(lr['codes']) <= len(CATCH) and set(lr['codes']) <= set(CATCH), 'Học nghề sai.')
    _vbool(lr['done'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu tiệm chụp ảnh sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='pb_', category='service',
    meta=dict(short='Photobooth', place='Tiệm chụp ảnh Tách Tách', tagline='Ba, hai, một… ai cũng mở mắt!', icon='camera',
              color='#d0567f', light='#ffe6ef', weather='Chiều tối phố chợ đêm', work='Khách vào chụp', station='Buồng chụp & máy in',
              greeting='Lau ống kính, xem cuộn mực, chụp thử rồi mở tiệm. Bấm chụp lúc cả nhóm mở mắt, cho khách chọn ảnh rồi mới in nhé.',
              caption='Ô ảnh nào cũng mở mắt', map_label='24 · TIỆM ẢNH TÁCH TÁCH'),
    people=PEOPLE,
    staff=[('Tí', 'lens', 'Em họ chị Lam, lau kính, xếp đạo cụ nhanh tay.', 80, 88),
           ('Ngọc', 'call', 'Sinh viên làm thêm buổi tối, nói chuyện duyên.', 82, 78),
           ('Khang', 'lens', 'Mê máy ảnh, lau ống kính như lau báu vật.', 70, 94),
           ('My', 'call', 'Nhớ tên khách quen, ai vào cũng chào.', 78, 82)],
    roles={'lens': 'Lau kính, xếp đạo cụ', 'call': 'Đón khách, phát phiếu chọn khung'},
    inventory=dict(items=ITEMS, capacity=80),
    prices=PRICES,
    tip=2,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('📸', 'Buồng chụp gọn gàng', [('Bờm tai thỏ', 'Rổ đạo cụ'), ('Giấy in dải', 'Ngăn máy in'), ('Khung gỗ', 'Kệ khung'), ('Khăn lau kính', 'Hộp máy ảnh')],
              ['Lau ống kính, chụp thử', 'Xem cuộn mực in', 'Bấm chụp lúc cả nhóm mở mắt', 'In, cắt, bỏ bao, thu tiền']),
    stories=[('Tấm ảnh đầu tiên', ('Hồi mở tiệm, chị Lam chụp thử chính mình đội bờm tai thỏ.',
                                   'Dải ảnh đó vẫn dán ở góc tường, hơi phai màu.',
                                   'Chị bảo: “Ảnh đẹp nhất là ảnh ai cũng cười thật.”')),
             ('Ba giây', ('Chị Lam dạy bạn đếm theo nhịp thở của khách.',
                          'Đếm tới một, đợi thêm nửa nhịp, ai cũng đứng yên.',
                          'Từ đó bạn bấm chụp như bắt nhịp một bài hát.')),
             ('Năm mươi năm', ('Ông bà Chín chụp tấm đầu ở tiệm ảnh cũ trên phố từ năm nào không nhớ.',
                               'Năm nào hai ông bà cũng chụp một tấm, treo thành một hàng dài.',
                               'Năm nay bạn là người bấm máy cho tấm thứ năm mươi.'))],
    review_asides=['Ô nào cũng mở mắt, cười tươi.', 'Khung đẹp, cắt thẳng tắp, có bao kiếng đàng hoàng.',
                   'Nhớ đúng từng cái sticker tôi dặn.', 'Bấm máy đúng lúc, không phải chụp lại.'],
    situations=SITUATIONS,
    guide='Lau ống kính → xem cuộn mực → chụp thử → mở tiệm. Mỗi khách: hỏi → gói, khung, phông, đạo cụ, đèn → bấm chụp lúc vạch xanh → '
          'cho khách xem, chọn đúng tấm → sticker, ngày, màu → in → cắt, bỏ bao → đưa ảnh → thu tiền.',
)
