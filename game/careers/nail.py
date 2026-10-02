"""Tiệm nail của chị Diệp: a small nail shop on the street (plugin career).

Chị Diệp (the street's talkative neighbour, game/board_content.py) left the spa and opened her own
little shop; the player works the table beside her. What the job is:

* the morning (``setup`` task): test the LED lamp with a drop of gel (some mornings a bulb is weak:
  swap it from the spare, or work with the old UV lamp), put the metal nippers and pushers into the
  sterilizer, look over the stock shelf, then open;
* every client: listen (service, colour, shape, length, the reference photo), look at the nails
  yourself (a nail with fungus or an infected cuticle is not worked on: decline politely and send
  them to a doctor; a broken nail is fixed first), open a fresh file and buffer for this client
  (they are single-use) and work with tools that came out of the sterilizer;
* take the old polish off: regular polish wipes off with acetone; gel is filed on top, then soaked
  in acetone wraps for ten minutes (a real-time wait). Prying it off thins the nail;
* shape (square, oval, almond, round) to the length asked (cut shorter only: longer needs tips),
  push back the cuticles (cut too deep and it bleeds: stop the bleeding, and say so honestly);
* gel: base, two thin colour coats, top, each cured under the lamp for its own time (LED, UV or the
  battery lamp; a lookup card is on the table), gel on the skin is wiped off before curing, then the
  sticky layer is wiped off; art (French tips, flowers, stones) goes on before the top; regular
  polish dries under the fan instead. A thick coat wrinkles; a coat cured far too short stays wet;
  a coat cured a little too short looks fine today and peels in two days (the client comes back
  the next morning: a review and the redo money);
* cash with the shared till (game/careers/till.py), tips from happy regulars.

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

ID = 'nail'
GEN = 1

SOAK_S = 20               # real seconds of the acetone wrap (shown as "10 phút")
RUSH_S = 150              # real seconds a hurried client gives you from your first move on her nails
CURE_SECS = (30, 60, 90, 120)
CURE = {
    'led': dict(base=30, color=60, top=60, art=60, da=30),
    'uv': dict(base=120, color=120, top=120, art=120, da=120),
    'pin': dict(base=60, color=90, top=90, art=90, da=60),
}
LAMPS = {'led': 'Đèn LED', 'uv': 'Đèn UV cũ', 'pin': 'Đèn LED sạc pin'}
WEAK_X = 2                # a weak LED bulb needs twice the time
HEAT_AT = 120             # a strong LED for this long: a heat spike
SKIN_P = {'mong': 18, 'day': 45}   # % a coat touches the skin, by how thick it is laid
COAT_MAX = 12
LEN = ('ngan', 'vua', 'dai')
LEN_NAME = {'ngan': 'ngắn', 'vua': 'vừa', 'dai': 'dài'}
SHAPES = {'vuong': 'Vuông', 'oval': 'Oval', 'hanh_nhan': 'Hạnh nhân', 'tron': 'Tròn'}
ART = {'french': 'Vẽ French đầu móng', 'hoa': 'Vẽ hoa nhí', 'da': 'Đính đá'}
CUTS = {'day': 'Đẩy da nhẹ', 'nhat': 'Nhặt da thừa', 'sau': 'Cắt sâu cho sạch'}
CONDS = ('ok', 'broken', 'fungus', 'infected')
OLDS = ('none', 'thuong', 'gel')
FLAGS = ('dirty_tools', 'reuse_file', 'over_file', 'pry', 'heat', 'over_old', 'smear')

COLOURS = [
    dict(id='do', name='Đỏ cherry', emoji='🍒', hex='#b5122e'),
    dict(id='nude', name='Hồng nude', emoji='🌸', hex='#e6b3a6'),
    dict(id='sua', name='Trắng sữa', emoji='🥛', hex='#f3ede2'),
    dict(id='den', name='Đen bóng', emoji='🖤', hex='#1d1d1f'),
    dict(id='mint', name='Xanh mint', emoji='🌿', hex='#9cd9c0'),
    dict(id='nhu', name='Nhũ vàng', emoji='✨', hex='#cfa83a'),
]
COLOUR = {x['id']: x for x in COLOURS}
REGULAR = ('do', 'nude', 'den')         # regular polish comes in these colours

# Multi-use bottles: uses per bottle (an open bottle lives in the shop data).
USES = {'base': 15, 'top': 15, 'son_bong': 15, 'acetone': 8, 'con': 20, 'dau': 20, 'kem': 10,
        **{f'gel_{x["id"]}': 10 for x in COLOURS}, **{f'son_{x}': 8 for x in REGULAR}}
ITEMS = ([dict(id=f'gel_{x["id"]}', name=f'Gel {x["name"].lower()}', emoji=x['emoji'], group='gel', unit='lọ', cost=8, life=90, start=1)
          for x in COLOURS]
         + [dict(id=f'son_{x}', name=f'Sơn thường {COLOUR[x]["name"].lower()}', emoji=COLOUR[x]['emoji'], group='son', unit='lọ', cost=3,
                 life=90, start=1) for x in REGULAR]
         + [dict(id='base', name='Gel base (lớp lót)', emoji='🧴', group='gel', unit='lọ', cost=8, life=90, start=1),
            dict(id='top', name='Gel top (lớp bóng)', emoji='💎', group='gel', unit='lọ', cost=8, life=90, start=1),
            dict(id='son_bong', name='Sơn lót & bóng thường', emoji='🫙', group='son', unit='lọ', cost=3, life=90, start=1),
            dict(id='acetone', name='Nước tẩy acetone', emoji='🧪', group='vt', unit='chai', cost=4, life=120, start=2),
            dict(id='con', name='Cồn lau lớp dính', emoji='🧴', group='vt', unit='chai', cost=2, life=120, start=1),
            dict(id='foil', name='Bông + giấy bạc ủ gel', emoji='🥡', group='vt', unit='bộ', cost=1, life=200, start=8),
            dict(id='dua', name='Dũa + phao (dùng một lần)', emoji='🪵', group='vt', unit='bộ', cost=1, life=200, start=10),
            dict(id='tips', name='Móng úp (tips)', emoji='💅', group='vt', unit='bộ', cost=3, life=200, start=3),
            dict(id='da', name='Đá đính móng', emoji='💠', group='vt', unit='vỉ', cost=2, life=200, start=3),
            dict(id='dau', name='Dầu dưỡng viền móng', emoji='💧', group='vt', unit='lọ', cost=5, life=120, start=1),
            dict(id='kem', name='Kem dưỡng da tay', emoji='🧴', group='vt', unit='hũ', cost=5, life=60, start=1),
            dict(id='cam_mau', name='Bông cầm máu', emoji='🩹', group='vt', unit='gói', cost=1, life=200, start=3),
            dict(id='bong_led', name='Bóng đèn LED dự phòng', emoji='💡', group='vt', unit='bóng', cost=6, life=999, start=1)])
ITEM = {x['id']: x for x in ITEMS}
PRICES = dict(cat_dua=4, son_thuong=8, son_gel=15, thao_gel=5, noi=20, french=4, hoa=5, da=4, cham_da=6)
SVC = {'cat_dua': 'Cắt dũa', 'son_thuong': 'Sơn thường', 'son_gel': 'Sơn gel', 'thao_gel': 'Tháo gel cũ', 'noi': 'Nối móng (úp tips)',
       'french': 'Vẽ French', 'hoa': 'Vẽ hoa', 'da': 'Đính đá', 'cham_da': 'Chăm sóc da tay'}

PEOPLE = [
    ('Chị Diệp', 'Chủ tiệm nail', 'Bỏ spa ra mở tiệm nhỏ trên phố. Nói nhiều, hay than, mà tay nghề khéo.', 'warm'),
    ('Chị Thảo Vy', 'Cô dâu tháng này', 'Sắp cưới, muốn bộ móng giống y ảnh mẫu.', 'bossy'),
    ('Chị Ngân', 'Nhân viên văn phòng', 'Lúc nào cũng vội, tranh thủ giờ nghỉ trưa.', 'sour'),
    ('Bé My', 'Sinh viên năm nhất', 'Ít tiền, mê màu pastel, làm xong là chụp ảnh liền.', 'genz'),
    ('Bà Năm', 'Hưu trí', 'Chỉ muốn móng ngắn, sạch. Đang uống thuốc loãng máu.', 'warm'),
    ('Chị Kiều', 'Khách ruột, bán mỹ phẩm', 'Khó tính, soi từng móng, mà quý tiệm.', 'picky'),
    ('Cô Lan', 'Bán vải ngoài chợ', 'Ngại đi khám, muốn sơn che cái móng xấu.', 'quiet'),
]

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Khách ghé đều tay, có người hẹn trước, có người ghé ngang.', weight=3),
    dict(id='wedding', emoji='💍', label='Mùa cưới', hint='Cô dâu, phù dâu đặt lịch: nối móng, đính đá, làm y ảnh mẫu.', min_day=2, weight=2),
    dict(id='rain', emoji='🌧️', label='Mưa dầm', hint='Ít khách hơn; tay khách lạnh, khô: nhiều người muốn chăm da tay.', min_day=2, weight=2),
    dict(id='weekend', emoji='🛍️', label='Cuối tuần', hint='Sinh viên rủ nhau đi làm móng, vẽ, đính đá chụp ảnh.', min_day=2, weight=2),
    dict(id='outage', emoji='🔌', label='Lịch cúp điện', hint='Phường báo cúp điện trong ngày: đèn hơ gel sẽ tắt.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}


def _o(npc, title, opening, svc, polish=None, colour=None, shape='tron', length='vua', art=None, extend=False, care=False,
       cond=('ok', 'none', 'vua'), note='', min_day=1, mod=None, photo=None, **flags):
    return dict(npc=npc, title=title, opening=opening, svc=list(svc), polish=polish, colour=colour, shape=shape, length=length, art=art,
                extend=extend, care=care, cond=cond, note=note, min_day=min_day, mod=mod, photo=photo, flags=flags)


ORDERS = [
    _o(3, 'Bé My sơn thường', 'Chị ơi em sơn thường màu hồng nude, dũa tròn thôi, em còn ít tiền à.', ['son_thuong'], 'thuong', 'nude',
       'tron', 'vua', note='Bé My đếm tiền lẻ trong ví.'),
    _o(4, 'Bà Năm cắt móng', 'Con cắt ngắn, dũa tròn cho bà, sạch sẽ là được. Bà không sơn đâu.', ['cat_dua'], None, None, 'tron', 'ngan',
       note='Bà Năm dặn: “Bà đang uống thuốc loãng máu, đừng cắt da sâu nghe con.”', blood=True),
    _o(2, 'Chị Ngân tháo gel làm mới', 'Tháo bộ gel cũ, sơn gel đỏ, móng vuông ngắn giùm chị. Hai giờ chị họp rồi.', ['thao_gel', 'son_gel'],
       'gel', 'do', 'vuong', 'ngan', cond=('ok', 'gel', 'vua'), note='Chị Ngân vừa ngồi xuống đã nhìn đồng hồ.', rush=True),
    _o(5, 'Chị Kiều làm French', 'Gel trắng sữa, dáng hạnh nhân, vẽ French đầu móng. Dũa đều mười móng nghe, lần trước lệch.',
       ['son_gel', 'french'], 'gel', 'sua', 'hanh_nhan', 'vua', art='french', cond=('ok', 'thuong', 'dai'), min_day=2,
       note='Chị Kiều còn sơn thường cũ, tróc mép.', photo='Ảnh mẫu: móng hạnh nhân, nền trắng sữa, viền French trắng mảnh.', check=True),
    _o(6, 'Cô Lan sơn che móng', 'Sơn gel đen che giùm cô cái móng xấu. Cô ngại đi bác sĩ lắm.', ['son_gel'], 'gel', 'den', 'tron', 'ngan',
       cond=('fungus', 'none', 'vua'), min_day=2, note='Cô Lan giấu bàn tay phải dưới vạt áo.'),
    _o(3, 'Bé My vẽ hoa', 'Gel xanh mint, móng tròn, vẽ hoa nhí nha chị. Em đi chụp kỷ yếu.', ['son_gel', 'hoa'], 'gel', 'mint', 'tron',
       'vua', art='hoa', cond=('ok', 'thuong', 'vua'), min_day=2, mod='weekend', photo='Ảnh mẫu: nền xanh mint, mấy bông hoa trắng li ti.',
       note='Bé My dẫn theo hai đứa bạn cùng lớp.'),
    _o(4, 'Bà Năm chăm da tay', 'Mưa lạnh tay bà khô nứt. Con chăm da tay, sơn thường đỏ cho bà vui.', ['cham_da', 'son_thuong'],
       'thuong', 'do', 'tron', 'ngan', care=True, cond=('ok', 'thuong', 'ngan'), min_day=2, mod='rain',
       note='Bà Năm xoa hai bàn tay lạnh ngắt.', blood=True),
    _o(2, 'Chị Ngân đi tiệc', 'Tối nay tiệc công ty: gel nhũ vàng, móng vuông. Lẹ giùm chị nha.', ['son_gel'], 'gel', 'nhu', 'vuong', 'vua',
       cond=('ok', 'thuong', 'vua'), min_day=3, note='Chị Ngân gọi điện dặn chỗ đặt bàn.', rush=True),
    _o(5, 'Chị Kiều làm lại gel', 'Tháo gel, làm gel hồng nude dáng oval. Chị soi kỹ lắm đó.', ['thao_gel', 'son_gel'], 'gel', 'nude',
       'oval', 'vua', cond=('ok', 'gel', 'vua'), min_day=3, note='Chị Kiều đặt túi xách lên ghế bên cạnh.', check=True),
    _o(6, 'Cô Lan đau khóe móng', 'Khóe móng cô sưng mấy bữa nay. Con cắt da, sơn thường đỏ cho cô.', ['son_thuong'], 'thuong', 'do', 'tron',
       'ngan', cond=('infected', 'none', 'ngan'), min_day=4, note='Cô Lan nhăn mặt khi chạm vào ngón cái.'),
    _o(1, 'Chị Thảo Vy sơn thử', 'Chị sơn thử màu hồng nude coi lên tay sao, cuối tháng chị cưới.', ['son_gel'], 'gel', 'nude', 'oval', 'vua',
       min_day=2, mod='wedding', note='Chị Thảo Vy chìa điện thoại có ảnh váy cưới.'),
    _o(3, 'Bé My ngày cúp điện', 'Cúp điện hả chị? Vậy sơn thường đỏ cũng được, dũa tròn.', ['son_thuong'], 'thuong', 'do', 'tron', 'vua',
       min_day=3, mod='outage', note='Bé My bật đèn pin điện thoại soi giùm.'),
    _o(5, 'Chị Kiều đính đá', 'Gel đen dáng hạnh nhân, đính đá hai ngón áp út. Cuối tuần chị đi đám cưới.', ['son_gel', 'da'], 'gel', 'den',
       'hanh_nhan', 'vua', art='da', min_day=3, mod='weekend', photo='Ảnh mẫu: nền đen bóng, một hàng đá nhỏ ở ngón áp út.',
       note='Chị Kiều lấy kính lúp soi từng viên đá.', check=True),
    _o(2, 'Chị Ngân giờ nghỉ trưa', 'Sơn thường đen, móng vuông ngắn. Nửa tiếng là chị phải về.', ['son_thuong'], 'thuong', 'den', 'vuong',
       'ngan', cond=('ok', 'thuong', 'vua'), min_day=2, note='Chị Ngân vừa ăn bánh mì vừa chìa tay.', rush=True),
]
BRIDE = _o(1, 'Bộ móng cô dâu Thảo Vy', 'Thứ bảy chị cưới! Nối móng dài, gel hồng nude, đính đá như ảnh nha em.', ['noi', 'son_gel', 'da'],
           'gel', 'nude', 'hanh_nhan', 'dai', art='da', extend=True, cond=('ok', 'none', 'ngan'), min_day=3,
           photo='Ảnh mẫu: móng hạnh nhân dài, hồng nude, đá nhỏ ở ngón áp út.', note='Mẹ chị Thảo Vy ngồi chờ, tay ôm giỏ trầu cau.',
           check=True)
KINDS = ('setup', 'serve', 'bride')
STAGES = ('prep', 'pay', 'done')

REG_STORY = {
    1: ('Chị Thảo Vy: “Chụp hình cưới mà tay xinh vầy là chị vui cả tuần.”', 'Chị Thảo Vy gửi ảnh cưới, bàn tay cầm hoa rõ từng viên đá.',
        'Chị Thảo Vy giới thiệu cả nhóm phù dâu tới tiệm.'),
    2: ('Chị Ngân: “Họp xong sếp khen móng đẹp, chị quê muốn xỉu.”', 'Chị Ngân đặt lịch cố định trưa thứ sáu.',
        'Chị Ngân rủ cả phòng kế toán qua làm móng.'),
    3: ('Bé My: “Em đăng ảnh móng được hai trăm tim luôn chị!”', 'Bé My để dành tiền làm thêm cả tuần để đi làm móng.',
        'Bé My vẽ tặng tiệm cái logo bàn tay nhỏ xinh.'),
    4: ('Bà Năm: “Móng sạch, tay mềm, bà đi chùa cũng thấy vui.”', 'Bà Năm mang cho tiệm hũ mứt gừng bà tự làm.',
        'Bà Năm dặn con cháu: làm móng thì qua tiệm cô Diệp.'),
    5: ('Chị Kiều: “Mười móng đều nhau, được.”', 'Chị Kiều giới thiệu khách mua mỹ phẩm của chị qua tiệm.',
        'Chị Kiều khen trên nhóm khu phố: tiệm nhỏ mà làm kỹ.'),
    6: ('Cô Lan: “Cô đi khám rồi, bác sĩ cho thuốc bôi.”', 'Cô Lan khoe móng đã đỡ vàng, hẹn khỏi hẳn sẽ quay lại sơn.',
        'Cô Lan cảm ơn vì hôm đó tiệm nói thật.'),
}

INTRO = dict(
    title='Giới thiệu nghề: làm móng',
    lead='Một bàn làm móng nhỏ, cái đèn hơ gel, tủ hấp dụng cụ và kệ sơn đủ màu. Chị Diệp bỏ spa ra mở tiệm trên phố, '
         'bạn ngồi bàn bên cạnh chị.',
    work=[('💡', 'Thử đèn hơ gel mỗi sáng, bóng yếu thì thay'), ('♨️', 'Hấp dụng cụ kim loại, dũa và phao dùng một lần'),
          ('🔍', 'Xem móng khách trước khi làm: móng nấm, khóe viêm thì không làm'), ('🧪', 'Tháo sơn cũ: sơn thường lau, gel dũa rồi ủ'),
          ('💅', 'Dũa đúng dáng, đúng độ dài, đẩy da nhẹ tay'), ('🪔', 'Gel: base, hai lớp màu mỏng, top, lớp nào hơ đủ giờ lớp nấy'),
          ('🌸', 'Vẽ, đính đá trước lớp top'), ('💵', 'Thu tiền, thối đúng')],
    meet=[('👰', 'Chị Thảo Vy: cô dâu, làm y ảnh mẫu'), ('⏰', 'Chị Ngân: lúc nào cũng vội'), ('🎒', 'Bé My: ít tiền, mê vẽ hoa'),
          ('👵', 'Bà Năm: móng ngắn sạch, đang uống thuốc loãng máu'), ('🧐', 'Chị Kiều: soi từng móng'),
          ('🤫', 'Cô Lan: muốn sơn che móng xấu')],
    stars=[('💅', 'Đúng dáng, đúng màu, đúng ảnh mẫu'), ('🪔', 'Gel bền, không nhăn, không bong'), ('♨️', 'Dụng cụ sạch, dũa mới'),
           ('🩹', 'Nhẹ tay, không chảy máu'), ('⏱️', 'Gọn, nhanh'), ('💵', 'Thối đúng tiền')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='power_cut', title='Cúp điện giữa buổi', emoji='🔌', npc=0, min_day=3, tone='tense', at='between', weight=5, mods=('outage',),
         text='Phụt một cái, quạt tắt, đèn hơ gel tắt ngấm. Chị Diệp than: “Trời ơi lần thứ ba trong tháng rồi đó!”',
         options=[dict(id='pin', label='Lấy đèn LED sạc pin của chị Diệp, hơ lâu hơn chút', hint='Đèn yếu hơn: base 60 giây, màu và top 90',
                       effects=dict(power='off', patience=-3, xp=3), good=True,
                       outcome='Đèn sạc pin sáng xanh. Chị Diệp nói: “May có cái đèn này, mua từ hồi làm móng tại nhà đó.”'),
                  dict(id='wait', label='Mời khách ngồi chờ có điện lại', hint='Khách chờ lâu', effects=dict(patience=-9), good=None,
                       outcome='Bốn mươi phút sau có điện. Khách ngồi quạt tay, mặt hơi nhăn.'),
                  dict(id='sun', label='Cho khách hơ móng ngoài nắng cho nhanh', hint='',
                       effects=dict(review=[2, 'Cúp điện mà tiệm bảo ra nắng hơ móng, về hai bữa gel bong hết.']), good=False,
                       outcome='Nắng gắt mà gel vẫn mềm. Có điện lại phải hơ lại từ đầu.')],
         default='wait'),
    dict(id='cheap_gel', title='Người chào gel không nhãn', emoji='📦', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một người chở thùng gel tới: “Gel xách tay, giá rẻ một nửa, không cần nhãn mác đâu em, ai cũng xài.”',
         options=[dict(id='no', label='Không lấy: gel không nhãn, không rõ thành phần, dễ làm khách dị ứng', hint='', effects=dict(xp=4), good=True,
                       outcome='Chị Diệp gật gù: “Hồi ở spa có khách bị dị ứng gel dỏm, đỏ cả mười đầu ngón. Sợ lắm.”'),
                  dict(id='test', label='Mua một lọ về thử trên tay mình trước', hint='6 xu', effects=dict(money=-6), good=None,
                       outcome='Bạn sơn thử một ngón, hôm sau ngứa râm ran. Lọ gel nằm luôn trong thùng rác.'),
                  dict(id='buy', label='Mua cả thùng cho rẻ, dùng cho khách', hint='Rẻ…', effects=dict(money=-10,
                       review=[1, 'Làm móng xong đầu ngón tay đỏ ngứa cả tuần. Hỏi gel gì tiệm không trả lời được.']), good=False,
                       outcome='Tuần đó có khách quay lại, mười đầu ngón đỏ lên.')],
         default='no'),
    dict(id='kid_acetone', title='Bé nghịch chai acetone', emoji='🧒', npc=3, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Đứa nhỏ đi theo mẹ làm móng cầm chai acetone lắc lắc, mở nắp ngửi, ngay cạnh cái đèn hơ đang nóng.',
         options=[dict(id='away', label='Cầm lại chai, đóng nắp, cất lên kệ cao; đưa bé cây bút màu', hint='', effects=dict(xp=4), good=True,
                       outcome='Bé ngồi vẽ ngoan. Mẹ bé cảm ơn: “Chị lo làm móng không để ý con.”'),
                  dict(id='scold', label='Nạt bé bỏ xuống', hint='', effects=dict(patience=-4), good=None,
                       outcome='Bé khóc, mẹ bé dỗ mãi, khách khác chờ thêm.'),
                  dict(id='ignore', label='Kệ, chắc bé không sao đâu', hint='',
                       effects=dict(review=[2, 'Tiệm để chai acetone lung tung, con tôi cầm lên ngửi mà không ai nhắc.']), good=False,
                       outcome='Bé làm đổ acetone ra sàn, cả tiệm nồng nặc mùi.')],
         default='scold'),
    dict(id='fumes', title='Mùi hóa chất nồng nặc', emoji='😷', npc=5, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Ba bàn cùng tháo gel, mùi acetone với mùi keo nồng cả tiệm. Chị Kiều nhăn mũi: “Nhức đầu quá em ơi.”',
         options=[dict(id='air', label='Mở cửa, bật quạt hút, đậy nắp mọi chai, đeo khẩu trang', hint='', effects=dict(xp=3), good=True,
                       outcome='Mùi bay bớt. Chị Kiều gật đầu: “Vậy mới làm lâu dài được.”'),
                  dict(id='spray', label='Xịt nước hoa phòng cho át mùi', hint='', effects=dict(patience=-3), good=None,
                       outcome='Mùi nước hoa trộn mùi acetone, càng khó chịu hơn.'),
                  dict(id='nothing', label='Kệ, tiệm nail nào chẳng có mùi', hint='',
                       effects=dict(review=[2, 'Tiệm bí, mùi hóa chất nồng, ngồi một tiếng về nhức đầu.']), good=False,
                       outcome='Chị Kiều xin ra ngoài đứng hít thở.')],
         default='spray'),
    dict(id='own_polish', title='Khách mang sơn tự mua', emoji='🛍️', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một bạn sinh viên mang lọ sơn mua trên mạng: “Chị sơn giùm em lọ này nha, em trả tiền công thôi.”',
         options=[dict(id='check', label='Xem nhãn, nói rõ tiệm chỉ bảo hành sơn của tiệm, vẫn lót base, phủ top cho bền', hint='',
                       effects=dict(money=4, xp=3), good=True, outcome='Bạn ấy hiểu, sơn xong còn hỏi mua thêm lọ top của tiệm.'),
                  dict(id='plain', label='Sơn thẳng lọ đó, không lót gì', hint='', effects=dict(money=4), good=None,
                       outcome='Hai ngày sau sơn tróc, bạn ấy nhắn hỏi sao nhanh tróc vậy.'),
                  dict(id='refuse', label='“Sơn ngoài là tiệm không làm”', hint='',
                       effects=dict(review=[2, 'Mang sơn tới nhờ sơn giùm mà bị từ chối thẳng thừng.']), good=False,
                       outcome='Bạn ấy đi qua tiệm khác.')],
         default='plain'),
    dict(id='walkin_group', title='Nhóm sinh viên ghé không hẹn', emoji='👯', npc=3, min_day=2, tone='gentle', at='open', weight=3,
         mods=('weekend',), text='Mới mở cửa đã có bốn bạn sinh viên ùa vào: “Tụi em làm cả bốn đứa được không chị?”',
         options=[dict(id='book', label='Ghi tên, hẹn giờ từng bạn, mời ngồi chờ uống nước', hint='', effects=dict(xp=3), good=True,
                       outcome='Bốn bạn chia nhau đi ăn sáng rồi quay lại đúng giờ hẹn.'),
                  dict(id='all', label='Nhận hết, làm cùng lúc cho nhanh', hint='Khách chờ lâu', effects=dict(patience=-8), good=None,
                       outcome='Bàn nào cũng dở dang, khách nào cũng chờ.'),
                  dict(id='shoo', label='“Không hẹn thì về đi”', hint='', effects=dict(review=[2, 'Tới tận nơi mà bị đuổi về, không ghé nữa.']),
                       good=False, outcome='Nhóm bạn kéo nhau sang tiệm cuối phố.')],
         default='all'),
    dict(id='influencer', title='Người quay clip xin làm miễn phí', emoji='📱', npc=3, min_day=3, tone='tense', at='between', weight=2,
         mods=None, text='Một chị cầm điện thoại: “Chị review tiệm nail, mấy chục nghìn người xem. Em làm free bộ đính đá, chị lên clip.”',
         options=[dict(id='price', label='Mời làm đúng giá, tặng thêm lọ dầu dưỡng nhỏ', hint='', effects=dict(money=8, xp=3), good=True,
                       outcome='Chị ấy trả tiền, clip quay kỹ từng bước hấp dụng cụ, khen tiệm sạch.'),
                  dict(id='free', label='Làm free cho được việc', hint='Mất công, mất đá', effects=dict(money=-4), good=None,
                       outcome='Clip lên ba giây, rồi chuyển qua quán khác.'),
                  dict(id='shoo', label='“Muốn free thì đi chỗ khác”', hint='',
                       effects=dict(review=[2, 'Hỏi có một câu mà tiệm nail nói chuyện cộc lốc.']), good=False,
                       outcome='Chị ấy quay luôn cảnh bị từ chối.')],
         default='price'),
    dict(id='wet_floor', title='Mưa hắt ướt sàn', emoji='🌧️', npc=4, min_day=2, tone='gentle', at='between', weight=3, mods=('rain',),
         text='Mưa tạt qua cửa, sàn gạch trơn ướt. Bà Năm chống gậy đang bước vào.',
         options=[dict(id='mop', label='Đỡ bà vào, lau sàn, đặt biển “sàn ướt”, trải thảm', hint='', effects=dict(xp=3, patience=-2), good=True,
                       outcome='Bà Năm ngồi xuống an toàn, còn khen tiệm chu đáo.'),
                  dict(id='later', label='Lát tạnh mưa rồi lau', hint='', effects=dict(review=[3, 'Sàn tiệm trơn ướt, suýt trượt chân.']),
                       good=False, outcome='Một chị khách trượt chân, may chống tay kịp.')],
         default='later'),
    dict(id='bridal_call', title='Đặt lịch cho cả nhóm phù dâu', emoji='💍', npc=1, min_day=2, tone='gentle', at='between', weight=3,
         mods=('wedding',), text='Chị Thảo Vy gọi: “Sáng thứ bảy em làm giùm chị năm đứa phù dâu nha, bảy giờ là phải xong!”',
         options=[dict(id='plan', label='Ghi sổ từng người, hẹn từ sáu giờ, báo trước giá', hint='', effects=dict(xp=4, money=6), good=True,
                       outcome='Chị Diệp mừng: “Mở tiệm mới mà có đám cưới đặt rồi!”'),
                  dict(id='yes', label='Hứa đại bảy giờ xong hết', hint='', effects=dict(patience=-5), good=None,
                       outcome='Sáng thứ bảy làm chạy muốn đứt hơi, trễ gần nửa tiếng.'),
                  dict(id='no', label='“Ai rảnh đâu mà làm sớm vậy”', hint='',
                       effects=dict(review=[2, 'Đặt lịch cưới mà tiệm trả lời trống không.']), good=False,
                       outcome='Nhóm phù dâu đặt tiệm khác.')],
         default='yes'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='NL-S01', title='Bộ gel bong sau ba ngày', npc=5, tone='tense', min_day=2,
         opening='Chị Kiều chìa tay: “Mới ba ngày mà bong hai móng rồi nè. Làm ăn kiểu gì vậy em?”',
         swap='Bạn là chị Kiều: làm móng ba trăm ngàn ngoài đời, ba ngày đã bong, mai lại đi gặp khách.',
         facts=[dict(id='edge', title='Mép móng', source='Soi kỹ', text='Gel bong cả mảng từ mép, mặt dưới còn mềm: lớp màu chưa khô hẳn.'),
                dict(id='lamp', title='Sổ đèn', source='Chị Diệp', text='Hôm đó bóng LED yếu mà chưa thay, mỗi lớp vẫn hơ sáu mươi giây.'),
                dict(id='home', title='Lời khách', source='Chị Kiều', text='Chị có rửa chén, nhưng lần nào cũng đeo găng.')],
         options=[dict(id='redo', label='Xin lỗi, làm lại miễn phí, thay bóng đèn mới', requires=['edge', 'lamp'], quality='good', stars=5,
                       review='Bong thật nhưng tiệm nhận lỗi ngay, làm lại miễn phí còn thay đèn mới. Quay lại tiếp.',
                       outcome='Chị Kiều ngồi xuống, lần này hai tuần chưa bong móng nào.',
                       perspectives=[dict(who='Chị Kiều', emoji='🧐', text='Nhận lỗi đàng hoàng thì chị còn ghé.'),
                                     dict(who='Chị Diệp', emoji='💅', text='Bóng đèn yếu là gel không khô. Sáng nào cũng thử đèn.')]),
                  dict(id='half', label='Làm lại, tính nửa tiền công', requires=['edge'], quality='ok', stars=3,
                       review='Làm lại có tính tiền, mà lỗi tại đèn tiệm.',
                       outcome='Chị Kiều trả tiền, mặt không vui.',
                       perspectives=[dict(who='Chị Kiều', emoji='😒', text='Lỗi tiệm mà khách trả tiền.'),
                                     dict(who='Bé My', emoji='🎒', text='Em cũng sợ bong nên chưa dám làm gel.')]),
                  dict(id='blame', label='“Chắc tại chị làm việc nhà nhiều”', quality='bad', stars=1,
                       review='Gel bong mà đổ tại khách. Không quay lại.',
                       outcome='Chị Kiều đứng dậy đi thẳng, tối đó lên nhóm khu phố kể.',
                       perspectives=[dict(who='Chị Kiều', emoji='😠', text='Đeo găng rồi mà còn đổ cho tôi.'),
                                     dict(who='Chị Diệp', emoji='😭', text='Mất một khách ruột vì cái bóng đèn.')])],
         lesson='Gel bong sớm thường do hơ thiếu giờ hoặc bóng đèn yếu. Sáng nào cũng thử đèn; lỗi tiệm thì nhận và làm lại.'),
    dict(id='NL-S02', title='Khách xin sơn đè lên móng nấm', npc=6, tone='tense', min_day=2,
         opening='Cô Lan năn nỉ: “Con sơn gel đen phủ kín giùm cô, không ai thấy là được. Cô ngại đi bác sĩ lắm.”',
         facts=[dict(id='look', title='Cái móng', source='Xem móng', text='Móng trỏ vàng đục, dày, sần, tách khỏi nền móng.'),
                dict(id='spread', title='Vì sao không làm', source='Chị Diệp', text='Dũa, kềm chạm vào móng nấm là mang nấm sang khách sau; gel phủ kín làm nấm nặng thêm.'),
                dict(id='doctor', title='Đi đâu', source='Bảng ở quầy', text='Phòng khám da liễu phường mở tới năm giờ chiều, khám nhanh.')],
         options=[dict(id='doctor', label='Nói nhẹ nhàng, không làm móng đó, chỉ chỗ khám da liễu', requires=['look', 'spread'], quality='good',
                       stars=5, review='Tiệm nói thật, chỉ chỗ khám. Đi khám mới biết bị nấm, giờ đỡ nhiều rồi.',
                       outcome='Cô Lan đi khám, hai tuần sau ghé khoe móng đã đỡ.',
                       perspectives=[dict(who='Cô Lan', emoji='🤫', text='Ngại thì ngại, mà người ta nói đúng.'),
                                     dict(who='Bà Năm', emoji='👵', text='Tiệm vậy bà mới yên tâm ngồi sau.')]),
                  dict(id='other', label='Chỉ làm các ngón lành bằng bộ dụng cụ riêng, khuyên đi khám', requires=['look'], quality='ok',
                       stars=4, review='Không làm móng bệnh, làm mấy móng còn lại, dặn đi khám.',
                       outcome='Cô Lan hơi buồn mà cũng gật đầu.',
                       perspectives=[dict(who='Cô Lan', emoji='🙂', text='Được mấy móng cũng vui.'),
                                     dict(who='Chị Diệp', emoji='💅', text='Bộ dụng cụ đó phải hấp riêng.')]),
                  dict(id='cover', label='Sơn phủ cho cô vui', quality='bad', stars=1,
                       review='Tiệm sơn đè lên móng nấm, mấy hôm sau khách sau tôi cũng bị.',
                       outcome='Tuần sau có khách quay lại kể móng bị vàng.',
                       perspectives=[dict(who='Khách sau', emoji='😟', text='Sao móng tôi tự nhiên vàng vậy?'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Nấm móng lây qua dụng cụ dùng chung.')])],
         lesson='Móng nấm, khóe viêm thì không làm: nói nhẹ nhàng, khuyên đi khám. Dụng cụ chạm vào thì hấp lại.'),
    dict(id='NL-S03', title='Khóe móng chảy máu', npc=4, tone='tense', min_day=3,
         opening='Lỡ tay cắt hơi sâu, khóe móng bà Năm rớm máu mãi không ngừng. Bà Năm nhìn xuống: “Gì vậy con?”',
         facts=[dict(id='pill', title='Thuốc của bà', source='Lời dặn', text='Bà Năm uống thuốc loãng máu, máu lâu cầm.'),
                dict(id='kit', title='Hộp sơ cứu', source='Ngăn kéo', text='Có bông cầm máu, băng cá nhân, cồn sát trùng.'),
                dict(id='call', title='Khi nào đi khám', source='Chị Diệp', text='Ép mười phút không cầm thì đưa đi trạm y tế.')],
         options=[dict(id='tell', label='Nói thật với bà, ép bông cầm máu, sát trùng, không tính tiền hôm nay', requires=['pill', 'kit'],
                       quality='good', stars=4, review='Con bé lỡ tay nhưng nói thật, lo cho bà chu đáo. Bà vẫn quý.',
                       outcome='Mười phút sau máu cầm. Bà Năm dặn: “Lần sau đẩy da thôi nghe con.”',
                       perspectives=[dict(who='Bà Năm', emoji='👵', text='Lỡ tay ai cũng có, nói thật là được.'),
                                     dict(who='Chị Diệp', emoji='💅', text='Khách uống thuốc loãng máu thì chỉ đẩy da.')]),
                  dict(id='hide', label='Dán băng cá nhân, nói “trầy chút xíu thôi bà”', requires=['kit'], quality='bad', stars=2,
                       review='Về nhà mới thấy máu thấm đỏ băng, hỏi thì tiệm bảo trầy xíu.',
                       outcome='Tối đó con gái bà Năm gọi điện hỏi chuyện.',
                       perspectives=[dict(who='Con gái bà Năm', emoji='📞', text='Mẹ tôi uống thuốc loãng máu đó!'),
                                     dict(who='Bà Năm', emoji='😞', text='Bà buồn vì không ai nói thật.')]),
                  dict(id='go', label='Ép cầm máu rồi đưa bà ra trạm y tế cho chắc', requires=['call'], quality='good', stars=5,
                       review='Tiệm đưa tôi ra tận trạm y tế, chờ khám xong mới về.',
                       outcome='Y tá sát trùng, băng lại. Bà Năm cảm ơn mãi.',
                       perspectives=[dict(who='Bà Năm', emoji='👵', text='Được đưa đi tận nơi, bà yên tâm.'),
                                     dict(who='Y tá', emoji='🩺', text='Người uống thuốc loãng máu thì cẩn thận vậy là đúng.')])],
         lesson='Khách uống thuốc loãng máu thì chỉ đẩy da. Lỡ chảy máu: cầm máu, sát trùng, nói thật.'),
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


def _p(c: dict, key: str) -> int:
    return max(1, int(kit.price(c, key, PRICES[key])))


def rank(length: str) -> int:
    return LEN.index(length)


def svc_text(n: dict) -> str:
    out = []
    for s in n['svc']:
        if s in ('son_gel', 'son_thuong') and n.get('colour'):
            out.append(f'{_lower(SVC[s])} {_lower(COLOUR[n["colour"]]["name"])}')
        else:
            out.append(_lower(SVC[s]))
    return ', '.join(out)


def weak_of(day: int) -> bool:
    """A weak LED bulb this morning (the second morning teaches the lamp test)."""
    if day <= 1:
        return False
    if day == 2:
        return True
    return kit.rng(ID, 'bulb', day).randrange(100) < 25


# ================================================================ tasks
def _kind(day: int, slot: int, mod: str) -> str:
    if slot == 0:
        return 'setup'
    if day >= 3 and slot == 2 and (day % 4 == 0 or mod == 'wedding'):
        return 'bride'
    return 'serve'


def _pick(day: int, slot: int, mod: str) -> dict:
    if day == 1:
        return ORDERS[(slot - 1) % 3]
    pool = [o for o in ORDERS if o['min_day'] <= day and o['mod'] in (None, mod)]
    weighted = [o for o in pool for _ in range(3 if o['mod'] else 1)]
    return weighted[kit.rng(ID, day, slot).randrange(len(weighted))]


def _common() -> dict:
    return dict(gen=GEN, stage='prep', seen=False, file=False, rm=dict(wiped=False, filed=False, wrap=None, off=False),
                fixed=False, tip=False, shape=None, len=None, cut=None, bleed=False, staunch=False, told=None, coats=[],
                wiped=False, dried=False, oil=False, care=False, flags=[], seq=0, clock=None, price=None, cash=None, cost=0,
                choice=None, story=None)


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    if kind == 'setup':
        needs = dict(setup=True, note={'outage': 'Phường báo cúp điện trong ngày: sạc sẵn đèn pin.',
                                       'wedding': 'Mùa cưới: coi lại đá đính, móng úp còn đủ không.',
                                       'rain': 'Mưa dầm: trải thảm chùi chân trước cửa.'}.get(mod, 'Thử đèn, hấp dụng cụ, coi kệ hàng rồi mở tiệm.'))
        return kit.base_task(ID, day, slot, serial, 0, 'Mở tiệm nail đầu ngày',
                             'Chị Diệp nhắn: “Em thử đèn hơ gel, hấp dụng cụ, coi kệ hàng rồi mở tiệm nghe. Hôm qua đèn chị chập chờn đó!”',
                             kind='setup', needs=needs, _cond=None, **_common())
    o = BRIDE if kind == 'bride' else _pick(day, slot, mod)
    nail, old, nat = o['cond']
    if nail == 'ok' and day >= 2 and kind == 'serve' and kit.rng(ID, 'broken', day, slot).randrange(100) < 15:
        nail = 'broken'
    f = o['flags']
    needs = dict(svc=list(o['svc']), polish=o['polish'], colour=o['colour'], shape=o['shape'], length=o['length'], art=o['art'],
                 extend=o['extend'], care=o['care'], photo=o['photo'], note=o['note'], check=bool(f.get('check')),
                 rush=bool(f.get('rush')), blood=bool(f.get('blood')))
    return kit.base_task(ID, day, slot, serial, o['npc'], o['title'], o['opening'], kind=kind, needs=needs,
                         _cond=dict(nail=nail, old=old, nat=nat), **_common())


FIXED = ('needs', '_cond')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the shop's data
def _fresh_shop(day: int) -> dict:
    return dict(day=day, open=False, stocked=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, clients=0, gel=0, declined=0, bled=0, peeled=0)


def initial() -> dict:
    return dict(v=1, intro=False, shop=_fresh_shop(0), lamp=dict(kind='led', weak=False, tested=False), power='on',
                tools=dict(clean=False, by=None), open={}, peel=[], regulars={}, today=_fresh_today(0),
                stats=dict(clients=0, gel=0, declined=0, bled=0, peeled=0, fair=0), desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'shop', 'lamp', 'tools'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


def need_of(d: dict, layer: str) -> int:
    """Seconds this layer needs under the lamp in use (a weak LED bulb doubles it)."""
    lamp = d['lamp']
    n = CURE[lamp['kind']][layer]
    if lamp['kind'] == 'led' and lamp['weak']:
        n *= WEAK_X
    return n


# ================================================================ the actions
FREE = ('nl_intro',)
NO_TICK = ('nl_intro', 'nl_desk', 'nl_short', 'nl_pay', 'nl_inspect', 'nl_tell', 'nl_lamp')
PHYSICAL = ('nl_remove', 'nl_shape', 'nl_cuticle', 'nl_coat', 'nl_cure', 'nl_art', 'nl_tip', 'nl_care', 'nl_fix')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'nl_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Chị Diệp đang lau bàn chờ bạn.')
    desk = d['desk']
    if name == 'nl_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'), hook=_desk_hook)
    kit.desk_block(desk, 'Có chuyện ở tiệm, quyết xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tiệm nail.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=('serve', 'bride')) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm nail.')
    kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_open(d: dict) -> None:
    kit.need(d['shop']['open'], 'Chưa mở tiệm: thử đèn, hấp dụng cụ, coi kệ hàng rồi bấm “Mở tiệm” nhé.')


def _client(c: dict, d: dict, p: dict) -> dict:
    """The client whose hands are on the table, ready to be worked on."""
    t = _task(c, p)
    _need_open(d)
    kit.need(t['known'], 'Hỏi khách muốn làm gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Bộ móng này đã xong, đang tính tiền.')
    return t


def _work(t: dict) -> None:
    kit.start_work(t)
    t['seq'] = min(999, t['seq'] + 1)
    if t['clock'] is None:
        t['clock'] = round(kit.now(), 3)


def _flag(t: dict, f: str) -> None:
    if f not in t['flags']:
        t['flags'].append(f)


def _tools(d: dict, t: dict) -> None:
    """Metal tools on this client's hands: clean from the sterilizer, or already this client's."""
    tl = d['tools']
    if not tl['clean'] and tl['by'] != t['id']:
        _flag(t, 'dirty_tools')
    d['tools'] = dict(clean=False, by=t['id'])


def _filing(t: dict) -> None:
    if not t['file']:
        _flag(t, 'reuse_file')


def _take(c: dict, t: dict | None, item: str) -> None:
    kit.need(kit.stock(c, item) > 0, f'Hết {_lower(ITEM[item]["name"])} rồi. Nhập thêm ở kho nhé.')
    cost = kit.take(c, item, 1)
    if t is not None:
        t['cost'] += cost


def _use(c: dict, d: dict, t: dict | None, item: str) -> None:
    """One use from an open bottle; opens a new bottle from stock when the last one is empty."""
    b = d['open'].get(item)
    if not b or b['n'] <= 0:
        kit.need(kit.stock(c, item) > 0, f'Hết {_lower(ITEM[item]["name"])} rồi. Nhập thêm ở kho nhé.')
        b = d['open'][item] = dict(n=USES[item], c=kit.take(c, item, 1))
    b['n'] -= 1
    if t is not None:
        t['cost'] += b['c'] // USES[item]
    if b['n'] <= 0:
        d['open'].pop(item, None)


def has(c: dict, d: dict, item: str) -> bool:
    b = d['open'].get(item)
    return bool(b and b['n'] > 0) or kit.stock(c, item) > 0


def removed(t: dict) -> bool:
    old = t['_cond']['old']
    rm = t['rm']
    return old == 'none' or (old == 'thuong' and (rm['wiped'] or rm['off'])) or (old == 'gel' and rm['off'])


# ---------------------------------------------------------------- the morning
def _lamp_test(s, c, d, p):
    lamp = d['lamp']
    lamp['tested'] = True
    if lamp['kind'] == 'led' and lamp['weak']:
        return dict(message='💡 Nhỏ một giọt gel lên giấy bạc, hơ đèn LED 60 giây: giọt gel vẫn ướt, nhão. Bóng LED yếu rồi.')
    sec = CURE[lamp['kind']]['color']
    return dict(message=f'💡 Nhỏ một giọt gel lên giấy bạc, hơ {_lower(LAMPS[lamp["kind"]])} {sec} giây: giọt gel cứng bóng. Đèn tốt.')


def _bulb(s, c, d, p):
    lamp = d['lamp']
    kit.need(lamp['kind'] == 'led', 'Đang dùng đèn khác, không phải đèn LED.')
    kit.need(kit.stock(c, 'bong_led') > 0, 'Hết bóng LED dự phòng. Dùng tạm đèn UV cũ, hoặc nhập bóng ở kho.')
    kit.take(c, 'bong_led', 1)
    was = lamp['weak']
    lamp['weak'] = False
    return dict(message='🔧 Rút điện, thay bóng LED mới.' + (' Đèn sáng xanh đều.' if was else ' Bóng cũ vẫn còn tốt, hơi phí.'))


def _lamp(s, c, d, p):
    kind = kit.one_of(p.get('kind'), ('led', 'uv'), 'Dùng đèn nào?')
    kit.need(d['power'] == 'on', 'Cúp điện: chỉ còn đèn sạc pin dùng được.')
    d['lamp']['kind'] = kind
    return dict(message=f'🪔 Đổi sang {_lower(LAMPS[kind])}. Coi lại bảng giờ hơ trên bàn nhé.')


def _sterilize(s, c, d, p):
    d['tools'] = dict(clean=True, by=None)
    return dict(message='♨️ Rửa kềm, sủi da, cây đẩy da bằng xà phòng, lau khô rồi cho vào tủ hấp. Lấy ra bộ sạch, để trong khay đậy nắp.')


def _stock(s, c, d, p):
    d['shop']['stocked'] = True
    low = [ITEM[k]['name'] for k in ITEM if k != 'bong_led' and not has(c, d, k)]
    few = [ITEM[k]['name'] for k in ITEM if k in ('dua', 'foil', 'cam_mau', 'tips', 'da') and 0 < kit.stock(c, k) <= 2]
    if not low and not few:
        return dict(message='📋 Coi kệ hàng: lọ nào cũng còn, dũa, giấy bạc đủ dùng.')
    parts = []
    if low:
        parts.append('Hết: ' + ', '.join(_lower(x) for x in low[:6]) + '.')
    if few:
        parts.append('Sắp hết: ' + ', '.join(_lower(x) for x in few) + '.')
    return dict(message='📋 Coi kệ hàng. ' + ' '.join(parts) + ' Nhập ở kho nhé.')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    sh = d['shop']
    kit.need(not sh['open'], 'Tiệm mở rồi.')
    if not d['lamp']['tested']:
        t['mistakes'] += 1
        cq.slip(t, 'no_lamp_test', 1, 'Chưa thử đèn đã mở tiệm, đèn yếu hay mạnh cũng không biết.', 'chưa thử đèn')
    if not d['tools']['clean']:
        t['mistakes'] += 1
        cq.slip(t, 'tools_dirty', 1, 'Kềm, cây đẩy da từ hôm qua chưa hấp.', 'chưa hấp dụng cụ')
    if not sh['stocked']:
        t['mistakes'] += 1
        cq.slip(t, 'no_stock', 1, 'Chưa coi kệ hàng, lỡ giữa chừng hết lọ màu khách chọn.', 'chưa coi kệ hàng')
    sh['open'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Thử đèn, hấp dụng cụ, coi kệ hàng.')
    return dict(message='💅 Mở tiệm! ' + ('Chị Diệp: “Giỏi quá em, hôm nay chắc đông!”' if ok else 'Chị Diệp: “Mở đi em, mai nhớ kỹ hơn nghe.”'),
                celebrate=ok)


# ---------------------------------------------------------------- looking at the nails, preparing them
def _inspect(s, c, d, p):
    t = _client(c, d, p)
    t['seen'] = True
    kit.start_work(t)
    cd = t['_cond']
    look = {'ok': 'Móng chắc, hồng hào, da viền móng lành.',
            'broken': 'Móng ngón giữa nứt ngang tới gần nền móng.',
            'fungus': 'Móng ngón trỏ vàng đục, dày, sần sùi, tách khỏi nền móng.',
            'infected': 'Khóe móng ngón cái sưng đỏ, có mủ, khách chạm vào là đau.'}[cd['nail']]
    old = {'none': 'Không có sơn cũ.', 'thuong': 'Còn sơn thường cũ, tróc mép.', 'gel': 'Đang có lớp gel cũ, bóng cứng.'}[cd['old']]
    return dict(message=f'🔍 {look} {old} Móng thật dài {LEN_NAME[cd["nat"]]}.')


def _kit(s, c, d, p):
    t = _client(c, d, p)
    kit.need(not t['file'], 'Đã mở bộ dũa mới cho khách này rồi.')
    _take(c, t, 'dua')
    t['file'] = True
    _work(t)
    return dict(message='🪵 Bóc bộ dũa và phao mới, dùng riêng cho khách này.')


def _remove(s, c, d, p):
    t = _client(c, d, p)
    how = kit.one_of(p.get('how'), ('wipe', 'file', 'wrap', 'unwrap', 'pry'), 'Tháo sơn cách nào?')
    old = t['_cond']['old']
    rm = t['rm']
    kit.need(old != 'none', 'Móng khách không có sơn cũ.')
    _work(t)
    if how == 'wipe':
        _use(c, d, t, 'acetone')
        if old == 'gel':
            return dict(message='🧪 Lau acetone mãi mà lớp gel vẫn bóng cứng: gel phải dũa mặt rồi ủ.')
        rm['wiped'] = True
        return dict(message='🧪 Thấm acetone vào bông, ép nhẹ rồi vuốt một đường: sơn thường cũ sạch trơn.')
    if how == 'file':
        _filing(t)
        if old == 'gel':
            rm['filed'] = True
            return dict(message='🪵 Dũa phá lớp bóng trên mặt gel cho acetone thấm vào.')
        _flag(t, 'over_file')
        return dict(message='🪵 Dũa mặt móng… sơn thường mỏng, đường dũa ăn luôn vào móng thật.')
    if how == 'wrap':
        kit.need(not rm['off'], 'Gel cũ đã tháo xong rồi.')
        _use(c, d, t, 'acetone')
        _take(c, t, 'foil')
        rm['wrap'] = round(kit.now(), 3)
        return dict(message='🥡 Đắp bông thấm acetone lên từng móng, quấn giấy bạc. Ủ chừng mười phút.')
    if how == 'unwrap':
        kit.need(rm['wrap'] is not None, 'Chưa quấn giấy bạc ủ móng nào.')
        if old == 'thuong':
            rm['wrap'], rm['off'] = None, True
            return dict(message='🥡 Gỡ giấy bạc: sơn thường tan sạch. (Sơn thường lau acetone là đủ, ủ chi cho tốn giấy.)')
        if not rm['filed']:
            rm['wrap'] = None
            return dict(message='🥡 Gỡ giấy bạc: mặt gel còn nguyên lớp bóng, acetone không thấm. Gel vẫn bám chặt.')
        left = SOAK_S - (kit.now() - rm['wrap'])
        if left > 0:
            mins = max(1, round(left * 10 / SOAK_S))
            return dict(message=f'🥡 Gỡ thử một ngón: gel còn bám. Ủ thêm chừng {mins} phút nữa.', correct=False)
        rm['wrap'], rm['off'] = None, True
        return dict(message='🥡 Gỡ giấy bạc: gel cũ phồng lên, lấy cây gỗ đẩy nhẹ là bong ra. Móng thật còn nguyên.')
    kit.need(old == 'gel' and not rm['off'], 'Không có lớp gel nào để cạy.')
    rm['wrap'], rm['off'] = None, True
    _flag(t, 'pry')
    return dict(message='🔪 Lấy sủi cạy mạnh: gel bật lên từng mảng, kéo theo cả lớp móng thật mỏng dính.')


def _fix(s, c, d, p):
    t = _client(c, d, p)
    kit.need(t['seen'], 'Xem móng khách trước đã.')
    kit.need(t['_cond']['nail'] == 'broken', 'Móng khách không có chỗ gãy.')
    kit.need(not t['fixed'], 'Móng gãy đã sửa rồi.')
    _filing(t)
    _use(c, d, t, 'base')
    t['fixed'] = True
    _work(t)
    return dict(message='🩹 Dũa bằng chỗ nứt, đắp một lớp gel gia cố mỏng cho móng chắc lại.')


def _tip(s, c, d, p):
    t = _client(c, d, p)
    kit.need(not t['tip'], 'Đã nối móng rồi.')
    kit.need(not t['coats'], 'Nối móng phải làm trước khi sơn.')
    _take(c, t, 'tips')
    _filing(t)
    t['tip'] = True
    _work(t)
    return dict(message='💅 Chọn tips vừa từng móng, gắn keo, ép chặt mười giây, dũa mối nối cho phẳng. Móng giờ dài.')


def _shape(s, c, d, p):
    t = _client(c, d, p)
    shape = kit.one_of(p.get('shape'), SHAPES, 'Dáng móng nào?')
    length = kit.one_of(p.get('length'), LEN, 'Dài, vừa hay ngắn?')
    now = 'dai' if t['tip'] else t['len'] or t['_cond']['nat']
    kit.need(rank(length) <= rank(now), f'Móng đang dài {LEN_NAME[now]}, chỉ cắt ngắn bớt được. Muốn dài hơn phải nối móng.')
    if rank(length) < rank(now):
        _tools(d, t)          # the clipper
    _filing(t)
    t['shape'], t['len'] = shape, length
    _work(t)
    return dict(message=f'🪵 {"Bấm ngắn bớt, d" if rank(length) < rank(now) else "D"}ũa dáng {_lower(SHAPES[shape])}, độ dài {LEN_NAME[length]}.')


def _cuticle(s, c, d, p):
    t = _client(c, d, p)
    how = kit.one_of(p.get('how'), CUTS, 'Làm da thế nào?')
    _tools(d, t)
    t['cut'] = how
    _work(t)
    if how == 'sau':
        t['bleed'] = True
        d['today']['bled'] += 1
        d['stats']['bled'] += 1
        return dict(message='✂️ Kềm cắt sâu vào khóe… tách! Khóe móng rớm máu.')
    if how == 'nhat':
        return dict(message='✂️ Đẩy da lên rồi nhặt sạch phần da chết, không chạm da sống.')
    return dict(message='🪵 Thoa chút nước mềm da, đẩy nhẹ viền da về sau. Viền móng gọn gàng.')


def _staunch(s, c, d, p):
    t = _client(c, d, p)
    kit.need(t['bleed'], 'Không có chỗ nào chảy máu.')
    kit.need(not t['staunch'], 'Đã cầm máu rồi.')
    _take(c, t, 'cam_mau')
    t['staunch'] = True
    _work(t)
    slow = ' Khách uống thuốc loãng máu nên ép lâu mới cầm.' if t['needs'].get('blood') else ''
    return dict(message=f'🩹 Ép bông cầm máu, sát trùng, dán băng nhỏ.{slow}')


def _tell(s, c, d, p):
    t = _client(c, d, p)
    kit.need(t['bleed'], 'Không có chuyện gì phải nói.')
    kit.need(t['told'] is None, 'Đã nói rồi.')
    honest = p.get('honest')
    kit.need(type(honest) is bool, 'Nói thật hay không?')
    t['told'] = honest
    if honest:
        return dict(message=f'🙏 “Em xin lỗi {_lower(_who(t))}, em lỡ tay cắt sâu. Em cầm máu, sát trùng rồi, mai còn đau thì báo em.”')
    return dict(message='🤐 “Không có gì đâu, trầy chút xíu thôi.”')


# ---------------------------------------------------------------- polish, the lamp, art
def _pending(t: dict) -> list:
    """Gel layers still soft: never cured, or cured so short they are wet on top."""
    return [x for x in t['coats'] if x['p'] == 'gel' and (x['cure'] is None or x['cure'] * 2 < x['need'])]


def _coat(s, c, d, p):
    t = _client(c, d, p)
    layer = kit.one_of(p.get('layer'), ('base', 'color', 'top'), 'Lớp nào?')
    kind = kit.one_of(p.get('p'), ('gel', 'thuong'), 'Gel hay sơn thường?')
    thick = kit.one_of(p.get('thick', 'mong'), ('mong', 'day'), 'Quét mỏng hay dày?')
    kit.need(len(t['coats']) < COAT_MAX, 'Móng dày cộm rồi, không quét thêm được.')
    colour = None
    if layer == 'color':
        colour = kit.one_of(p.get('colour'), COLOUR, 'Màu nào?')
        kit.need(kind == 'gel' or colour in REGULAR, 'Sơn thường ở tiệm chỉ có đỏ, hồng nude và đen.')
        item = f'gel_{colour}' if kind == 'gel' else f'son_{colour}'
    else:
        item = layer if kind == 'gel' else 'son_bong'
    _use(c, d, t, item)
    if not removed(t):
        _flag(t, 'over_old')
    if kind == 'gel' and _pending(t):
        _flag(t, 'smear')
    skin = _hash('nl-skin', t['id'], t['seq'], layer) % 100 < SKIN_P[thick]
    t['coats'].append(dict(l=layer, k=colour, p=kind, th=thick, cure=None, need=need_of(d, layer) if kind == 'gel' else 0, skin=skin))
    _work(t)
    what = {'base': 'lớp base' if kind == 'gel' else 'lớp sơn lót', 'top': 'lớp top' if kind == 'gel' else 'lớp sơn bóng',
            'color': f'lớp {_lower(COLOUR[colour]["name"]) if colour else ""}'}[layer]
    warn = ' ⚠️ Sơn lem ra da ở khóe ngón áp út.' if skin else ''
    return dict(message=f'🖌️ Quét {"dày" if thick == "day" else "mỏng"} {what}' + (' (gel).' if kind == 'gel' else ' (sơn thường).') + warn)


def _clean(s, c, d, p):
    t = _client(c, d, p)
    wet = [x for x in t['coats'] if x['skin'] and (x['p'] == 'thuong' or x['cure'] is None)]
    kit.need(wet, 'Không có chỗ sơn lem nào còn ướt để lau.')
    for x in wet:
        x['skin'] = False
    _work(t)
    return dict(message='🧹 Lấy que gỗ quấn bông lau sạch chỗ sơn lem ra da.')


def _cure(s, c, d, p):
    t = _client(c, d, p)
    sec = kit.one_of(kit.integer(p.get('sec'), 1, 600), CURE_SECS, 'Hẹn giờ đèn không có mức đó.')
    todo = _pending(t)
    kit.need(todo, 'Không có lớp gel nào cần hơ. Sơn thường thì để khô, không hơ đèn.')
    for x in todo:
        x['cure'] = min(1000, (x['cure'] or 0) + sec)
    lamp = d['lamp']
    _work(t)
    msg = f'🪔 Đặt tay khách vào {_lower(LAMPS[lamp["kind"]])}, hẹn {sec} giây.'
    if lamp['kind'] == 'led' and not lamp['weak'] and sec >= HEAT_AT:
        _flag(t, 'heat')
        msg += ' Khách rụt tay lại: “Nóng rát quá!”'
    if any(x['cure'] * 2 < x['need'] for x in todo):
        msg += ' ⚠️ Mặt gel còn ướt, chạm vào là lem.'
    if any(x['th'] == 'day' and x['l'] == 'color' for x in todo):
        msg += ' Lớp màu dày, mặt gel hơi nhăn.'
    return dict(message=msg)


def _art(s, c, d, p):
    t = _client(c, d, p)
    kind = kit.one_of(p.get('art'), ART, 'Vẽ hay đính gì?')
    kit.need(any(x['l'] == 'color' and x['p'] == 'gel' for x in t['coats']), 'Vẽ, đính đá làm trên nền gel màu đã hơ.')
    kit.need(not any(x['l'] == 'art' for x in t['coats']), 'Bộ này đã có trang trí rồi.')
    if kind == 'da':
        _take(c, t, 'da')
        _use(c, d, t, 'base')
    else:
        _use(c, d, t, 'gel_sua')
    layer = 'da' if kind == 'da' else 'art'
    t['coats'].append(dict(l='art', k=kind, p='gel', th='mong', cure=None, need=need_of(d, layer), skin=False))
    _work(t)
    return dict(message={'french': '🖌️ Cọ mảnh kéo một đường cong trắng ở đầu từng móng.',
                         'hoa': '🌼 Chấm năm cánh hoa trắng li ti, chấm nhụy vàng.',
                         'da': '💠 Chấm keo gel, gắp từng viên đá đặt lên ngón áp út.'}[kind] + ' Nhớ hơ đèn.')


def _wipe(s, c, d, p):
    t = _client(c, d, p)
    tops = [x for x in t['coats'] if x['l'] == 'top' and x['p'] == 'gel']
    kit.need(tops and tops[-1]['cure'] is not None, 'Chưa có lớp top gel nào đã hơ. Sơn thường không có lớp dính.')
    kit.need(not t['wiped'], 'Đã lau lớp dính rồi.')
    _use(c, d, t, 'con')
    t['wiped'] = True
    _work(t)
    return dict(message='🧴 Thấm cồn vào bông, lau lớp dính trên mặt top: móng bóng lên.')


def _dry(s, c, d, p):
    t = _client(c, d, p)
    kit.need(any(x['p'] == 'thuong' for x in t['coats']), 'Không có lớp sơn thường nào để hong khô.')
    kit.need(not t['dried'], 'Đã hong khô rồi.')
    t['dried'] = True
    _work(t)
    return dict(message='🌬️ Mời khách đặt tay trước quạt hong năm phút, sơn khô mặt.')


def _oil(s, c, d, p):
    t = _client(c, d, p)
    kit.need(not t['oil'], 'Đã thoa dầu rồi.')
    _use(c, d, t, 'dau')
    t['oil'] = True
    _work(t)
    return dict(message='💧 Nhỏ dầu dưỡng lên viền móng, xoa tròn cho thấm.')


def _care(s, c, d, p):
    t = _client(c, d, p)
    kit.need(not t['care'], 'Đã chăm da tay rồi.')
    _use(c, d, t, 'kem')
    t['care'] = True
    _work(t)
    return dict(message='🫧 Ngâm tay nước ấm, tẩy da chết nhẹ, thoa kem, xoa bóp từng ngón.')


# ---------------------------------------------------------------- handing it over
def _did(t: dict, svc: str) -> bool:
    coats = t['coats']
    if svc == 'cat_dua':
        return t['shape'] is not None
    if svc == 'son_gel':
        return any(x['l'] == 'color' and x['p'] == 'gel' for x in coats)
    if svc == 'son_thuong':
        return any(x['l'] == 'color' and x['p'] == 'thuong' for x in coats)
    if svc == 'thao_gel':
        return t['rm']['off']
    if svc == 'noi':
        return t['tip']
    if svc in ART:
        return any(x['l'] == 'art' and x['k'] == svc for x in coats)
    if svc == 'cham_da':
        return t['care']
    return False


def price_of(c: dict, t: dict) -> int:
    return max(1, sum(_p(c, s) for s in t['needs']['svc'] if _did(t, s)))


def _under(t: dict) -> list:
    """Cured a little short: looks fine at the table, peels in a couple of days."""
    return [x for x in t['coats'] if x['p'] == 'gel' and x['cure'] is not None and x['need'] <= x['cure'] * 2 and x['cure'] < x['need']]


def _checks(c: dict, d: dict, t: dict) -> None:
    """Record what the client notices at the hand-over (the most serious first: eight at most)."""
    n, cd, fl = t['needs'], t['_cond'], set(t['flags'])
    who = _who(t)
    coats = t['coats']
    worked = bool(coats or t['shape'] or t['cut'] or t['tip'] or t['rm']['off'] or t['rm']['wiped'])

    def bad(code, sev, text, note, safety=False):
        t['mistakes'] += 1
        cq.slip(t, code, sev, text, note, safety)

    if cd['nail'] in ('fungus', 'infected') and worked:
        bad('health', 3, 'Móng đang bị nấm mà tiệm vẫn làm, dũa kềm dùng chung lây cho người khác.' if cd['nail'] == 'fungus'
            else 'Khóe móng đang sưng mủ mà tiệm vẫn cắt, vẫn sơn, đau nhức cả đêm.', 'làm móng đang bệnh', True)
    if 'dirty_tools' in fl:
        bad('dirty_tools', 2, 'Kềm lấy ra từ khay dùng rồi, không thấy hấp gì cả.', 'dụng cụ chưa hấp', True)
    if 'reuse_file' in fl:
        bad('reuse_file', 2, 'Cây dũa đã mòn, dùng cho khách trước rồi còn dũa cho tôi.', 'dùng lại dũa của khách trước', True)
    if t['bleed']:
        blood = n.get('blood')
        bad('bleed', 3 if blood else 2, 'Đã dặn uống thuốc loãng máu mà còn cắt sâu, máu chảy mãi.' if blood else 'Cắt da sâu chảy máu, rát lắm.',
            'cắt da quá sâu', bool(blood))
        if not t['told']:
            bad('hid', 2, 'Chảy máu mà còn bảo trầy xíu, về nhà mới thấy băng đỏ.', 'giấu chuyện chảy máu')
    if not t['seen']:
        bad('no_inspect', 1, 'Không thèm nhìn móng tôi đã cầm dũa làm luôn.', 'chưa xem móng')
    want = n.get('polish')
    colour_coats = [x for x in coats if x['l'] == 'color']
    if want and colour_coats and any(x['p'] != want for x in colour_coats):
        bad('wrong_polish', 2, 'Tôi gọi sơn thường mà làm gel, tính tiền sao đây?' if want == 'thuong' else 'Tôi gọi sơn gel mà quét sơn thường.',
            'sai loại sơn')
    if want and not colour_coats:
        bad('no_colour', 2, 'Tôi tới sơn màu mà về móng trơn.', 'chưa sơn màu')
    elif want and any(x['k'] != n['colour'] for x in colour_coats):
        bad('colour', 2, f'Tôi chọn {_lower(COLOUR[n["colour"]]["name"])} mà sơn màu khác.', 'sai màu')
    if not want and coats:
        bad('extra_svc', 1, 'Tôi đâu có kêu sơn.', 'làm thêm thứ khách không gọi')
    if not removed(t) or 'over_old' in fl:
        bad('old_left', 2, 'Sơn mới quét đè lên lớp cũ, mặt móng lồi lõm.', 'chưa tháo sơn cũ')
    if 'pry' in fl:
        bad('pry', 2, 'Cạy gel mạnh tay, móng tôi mỏng dính, đau buốt.', 'cạy gel không ủ')
    gel = [x for x in coats if x['p'] == 'gel']
    if any(x['cure'] is None or x['cure'] * 2 < x['need'] for x in gel):
        bad('wet', 2, 'Gel còn ướt, chạm vào là lem cả móng.', 'hơ đèn thiếu giờ')
    if n.get('extend') and not t['tip']:
        bad('no_tip', 2, 'Tôi muốn móng dài như ảnh mà không nối.', 'chưa nối móng')
    if cd['nail'] == 'broken' and not t['fixed'] and worked:
        bad('broken', 1, 'Móng gãy chưa sửa mà sơn đè lên, đụng nhẹ là nứt tiếp.', 'chưa sửa móng gãy')
    if t['shape'] is None or t['shape'] != n['shape']:
        bad('shape', 2 if n.get('check') else 1, f'Tôi muốn dáng {_lower(SHAPES[n["shape"]])} mà.', 'sai dáng móng')
    if t['len'] is not None and rank(t['len']) < rank(n['length']):
        bad('too_short', 2, 'Cắt ngắn cũn cỡn, mấy tháng mới dài lại.', 'cắt móng quá ngắn')
    elif t['len'] is not None and rank(t['len']) > rank(n['length']) or t['len'] is None and not n.get('extend') \
            and rank(t['_cond']['nat']) > rank(n['length']):
        bad('too_long', 1, 'Tôi dặn ngắn mà để dài nguyên.', 'chưa cắt đúng độ dài')
    if n.get('art'):
        art = next((x for x in coats if x['l'] == 'art'), None)
        if not art:
            bad('no_art', 1, f'Còn {_lower(ART[n["art"]])} như ảnh đâu rồi?', 'thiếu phần trang trí')
        elif art['k'] != n['art']:
            bad('art', 1, 'Trang trí không giống ảnh mẫu.', 'sai kiểu trang trí')
        else:
            top = max((i for i, x in enumerate(coats) if x['l'] == 'top'), default=-1)
            if coats.index(art) > top >= 0:
                bad('art_loose', 1, 'Đá đính lên trên lớp bóng, sờ là lung lay.' if art['k'] == 'da' else 'Hình vẽ nằm ngoài lớp bóng, rửa tay là trôi.',
                    'trang trí sau lớp top')
    elif any(x['l'] == 'art' for x in coats):
        bad('extra_svc', 1, 'Tôi đâu có kêu vẽ.', 'làm thêm thứ khách không gọi')
    if want == 'gel' and colour_coats:
        base = [x for x in coats if x['l'] == 'base']
        if not base:
            bad('no_base', 1, 'Không lót base, gel bám không chắc.', 'thiếu lớp base')
        if len(colour_coats) == 1:
            bad('patchy', 1, 'Màu loang, nhìn thấy cả móng bên dưới.', 'màu chỉ một lớp')
        elif len(colour_coats) >= 3 or any(x['th'] == 'day' for x in colour_coats):
            bad('thick', 1, 'Lớp màu dày cộm, mặt nhăn nheo.', 'quét màu dày quá')
        if not any(x['l'] == 'top' for x in coats):
            bad('no_top', 1, 'Móng không bóng, mau trầy.', 'thiếu lớp top')
        elif not t['wiped']:
            bad('sticky', 1, 'Mặt móng còn dính tay, bám đầy bụi.', 'chưa lau lớp dính')
    if any(x['skin'] for x in gel):
        bad('lift', 1, 'Gel dính ra da, mép móng hở lên.', 'gel lem ra da')
    if 'smear' in fl:
        bad('smear', 1, 'Quét lớp sau khi lớp trước chưa hơ, màu lem loang lổ.', 'quét lớp mới lên lớp chưa hơ')
    if want == 'thuong' and colour_coats and not t['dried']:
        bad('smudge', 1, 'Sơn chưa khô đã cho về, cầm túi là lem.', 'chưa hong khô')
    if any(x['skin'] for x in coats if x['p'] == 'thuong'):
        bad('messy', 1, 'Sơn lem ra da, nhìn lem nhem.', 'sơn lem ra da')
    if 'heat' in fl:
        bad('heat', 1, 'Hơ đèn lâu nóng rát cả đầu ngón.', 'hơ đèn quá lâu')
    if 'over_file' in fl:
        bad('over_file', 1, 'Dũa vào tận mặt móng thật, móng mỏng đi.', 'dũa vào móng thật')
    if n.get('care') and not t['care']:
        bad('no_care', 1, 'Tôi nhờ chăm da tay mà quên mất.', 'quên chăm da tay')
    if n.get('rush') and t['clock'] is not None and kit.now() - t['clock'] > RUSH_S:
        bad('late', 1, f'{who} nhìn đồng hồ: “Trễ giờ họp của chị rồi!”', 'làm quá lâu')


def _done(s, c, d, p):
    t = _client(c, d, p)
    kit.need(t['coats'] or t['shape'] or t['care'], 'Chưa làm gì cho khách.')
    kit.need(not t['bleed'] or t['staunch'], 'Khóe móng còn rớm máu: cầm máu cho khách đã.')
    kit.need(not any(x['p'] == 'gel' and x['cure'] is None for x in t['coats']) or p.get('confirm') is True,
             'Còn lớp gel chưa hơ đèn. Vẫn giao cho khách?')
    _checks(c, d, t)
    t['price'] = price_of(c, t)
    peel = _under(t)
    if peel and not any(x['code'] == 'wet' for x in cq.slips(t)):
        d['peel'] = (d['peel'] + [dict(id=t['id'], day=c['day'], npc=t['npc'], title=t['title'][:80], price=t['price'])])[-12:]
    if any(x['l'] == 'color' and x['p'] == 'gel' for x in t['coats']):
        d['today']['gel'] += 1
        d['stats']['gel'] += 1
    t['stage'] = 'pay'
    t['cash'] = till.new(t['price'], t['id'], c=c, t=t)
    look = ' Khách xòe tay ngắm: “Xinh quá!”' if not cq.slips(t) else ''
    return dict(message=f'💅 Giao móng cho {_who(t)} · {t["price"]} xu.{look} Khách đưa {sum(t["cash"]["tender"])} xu: thối lại cho đúng.')


def _decline(s, c, d, p):
    """Not today: a nail that must not be worked on (send them to a doctor), or what they want is out of stock."""
    t = _client(c, d, p)
    why = kit.one_of(p.get('why'), ('health', 'stock'), 'Vì sao không làm?')
    cd, n = t['_cond'], t['needs']
    worked = bool(t['coats'] or t['shape'] or t['cut'] or t['tip'])
    if why == 'health':
        if cd['nail'] in ('fungus', 'infected'):
            if worked:
                t['mistakes'] += 1
                cq.slip(t, 'health', 3, 'Làm dở rồi mới bảo móng bệnh, dụng cụ chạm cả vào.', 'làm móng đang bệnh', True)
            words = ('móng có dấu hiệu nấm' if cd['nail'] == 'fungus' else 'khóe móng đang viêm')
            msg = (f'Nói nhẹ nhàng với {_who(t)}: {words}, tiệm không làm để khỏi nặng thêm và khỏi lây; '
                   'chỉ chỗ khám da liễu, khỏi rồi quay lại tiệm làm đẹp.')
        else:
            t['mistakes'] += 1
            cq.slip(t, 'wrong_refuse', 2, 'Móng tôi có sao đâu mà không làm?', 'từ chối khách móng lành')
            msg = f'Từ chối {_who(t)}: móng có sao đâu, khách bực bỏ về.'
    else:
        items = []
        if n.get('polish') and n.get('colour'):
            items.append(f'gel_{n["colour"]}' if n['polish'] == 'gel' else f'son_{n["colour"]}')
        if n.get('extend'):
            items.append('tips')
        if n.get('art') == 'da':
            items.append('da')
        if items and all(has(c, d, x) for x in items):
            t['mistakes'] += 1
            cq.slip(t, 'wrong_refuse', 1, 'Lọ màu đó trên kệ kia mà bảo hết.', 'từ chối khi còn hàng')
        msg = f'Nói thật với {_who(t)}: tiệm hết đồ cho bộ này, hẹn hôm sau.'
    t['choice'] = why
    d['today']['declined'] += 1
    d['stats']['declined'] += 1
    kit.start_work(t)
    return dict(message='🙏 ' + _finish(s, c, d, t, 0, msg))


def _pay(s, c, d, p):
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    react = cq.react(s, c, t, t['price'], who=who)
    st = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - st['loss']
    d['today']['clients'] += 1
    d['stats']['clients'] += 1
    if not cq.slips(t):
        d['stats']['fair'] += 1
    parts = [x for x in (react['message'], st['message']) if x]
    msg = _finish(s, c, d, t, max(0, net), ' '.join(parts))
    if net < 0:
        lost = min(-net, c['money'])
        if lost:
            kit.money(s, c, -lost, f'Thối dư cho khách: {t["title"]}'[:120], t['id'], 'change_loss')
    given = sum(rec['change'])
    head = f'💵 Thu {t["price"]} xu' + (f', thối {given} xu.' if given else '.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t))


def _short(s, c, p):
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    return till.short_action(s, c, t, t['cash'], p, _who(t))


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
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    if key == 'power' and v == 'off':
        d['power'] = 'off'
        d['lamp']['kind'] = 'pin'
        return 'Đèn sạc pin đã sẵn trên bàn.'
    return None


ACTIONS = {
    'nl_lamp_test': _lamp_test, 'nl_bulb': _bulb, 'nl_lamp': _lamp, 'nl_sterilize': _sterilize, 'nl_stock': _stock, 'nl_open': _open,
    'nl_inspect': _inspect, 'nl_kit': _kit, 'nl_remove': _remove, 'nl_fix': _fix, 'nl_tip': _tip, 'nl_shape': _shape,
    'nl_cuticle': _cuticle, 'nl_staunch': _staunch, 'nl_tell': _tell, 'nl_coat': _coat, 'nl_clean': _clean, 'nl_cure': _cure,
    'nl_art': _art, 'nl_wipe': _wipe, 'nl_dry': _dry, 'nl_oil': _oil, 'nl_care': _care, 'nl_done': _done, 'nl_decline': _decline,
    'nl_pay': _pay, 'nl_short': lambda s, c, d, p: _short(s, c, p),
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['shop'] = _fresh_shop(day)
    d['today'] = _fresh_today(day)
    d['lamp'] = dict(kind='led', weak=weak_of(day), tested=False)
    d['power'] = 'on'
    d['tools'] = dict(clean=False, by=None)          # last night's tools wait for the sterilizer
    # Gel cured a little short yesterday has peeled by now: the client comes back.
    keep = []
    for x in d['peel']:
        if x['day'] >= day:
            keep.append(x)
            continue
        kit.review(s, c, x['npc'], 2, f'Làm {_lower(x["title"])} hôm trước, mới hai ngày gel đã bong mép mấy móng. Hơ đèn chưa đủ hay sao?', x['id'])
        lost = min(max(1, x['price'] // 2), c['money'])
        if lost:
            kit.money(s, c, -lost, f'Làm lại bộ gel bong: {x["title"]}'[:120], x['id'], 'refund')
        kit.log(s, c, 'promise', f'💅 Khách quay lại vì gel bong sớm ({x["title"]}). Chị Diệp: “Lớp nào cũng hơ đủ giờ, sáng nào cũng thử đèn nghe em.”',
                x['npc'], x['id'])
        d['today']['peeled'] += 1
        d['stats']['peeled'] += 1
    d['peel'] = keep
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


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK, hook=_desk_hook)
    today = d['today']
    lines = [f'💅 Làm móng cho {today["clients"]} khách, {today["gel"]} bộ gel.']
    if today['declined']:
        lines.append(f'🙏 Có {today["declined"]} khách hẹn hôm khác.')
    if today['bled']:
        lines.append(f'🩹 Chị Diệp dặn: hôm nay có {today["bled"]} lần cắt da chảy máu. Đẩy da là đủ, nhặt da chết thôi nghe em.')
    if today['peeled']:
        lines.append(f'😭 {today["peeled"]} khách quay lại vì gel bong sớm.')
    if not d['tools']['clean']:
        lines.append('♨️ Dụng cụ còn nằm ngoài khay. Mai nhớ hấp trước khi làm.')
    if desk_note:
        lines.append(desk_note)
    d['shop'].update(open=False, stocked=False)
    d['power'] = 'on'
    gels = sum(kit.stock(c, f'gel_{x["id"]}') for x in COLOURS)
    return dict(lines=lines, note=f'Kệ còn {gels} lọ gel màu chưa mở, {len(d["open"])} lọ đang dùng dở trên bàn.',
                clients=today['clients'], gel=today['gel'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        lamp = 5 - len(codes & {'no_lamp_test', 'no_stock'})
        clean = 5 - 2 * len(codes & {'tools_dirty'})
        return dict(criteria=[dict(key='lamp', label='Đèn, kệ hàng sẵn sàng', score=max(2, lamp), note='thử đèn, coi kệ' if lamp == 5 else 'còn sót khâu chuẩn bị'),
                              dict(key='clean', label='Dụng cụ sạch', score=max(1, clean), note='hấp dụng cụ' if clean == 5 else 'chưa hấp dụng cụ')])
    if t.get('choice') in ('health', 'stock'):
        ok = 'wrong_refuse' not in codes and 'health' not in codes
        return dict(criteria=[dict(key='honest', label='Nói thật', score=5 if ok else 2, note='nói thật, khuyên đúng' if ok else 'từ chối chưa đúng'),
                              dict(key='service', label='Có làm móng', score=3, note='lần này chưa làm')])
    service = 2 if codes & {'colour', 'no_colour', 'wrong_polish', 'no_tip'} else 3 if codes & {'shape', 'too_short', 'no_art', 'art'} \
        else 4 if codes & {'too_long', 'extra_svc', 'no_care'} else 5
    finish = 2 if codes & {'wet', 'old_left'} else 3 if codes & {'thick', 'patchy', 'lift', 'smear', 'smudge', 'no_base', 'broken'} \
        else 4 if codes & {'sticky', 'no_top', 'art_loose', 'messy'} else 5
    clean = 1 if codes & {'health', 'dirty_tools', 'reuse_file'} else 3 if codes & {'bleed', 'hid'} else 5
    gentle = 2 if codes & {'pry', 'bleed'} else 3 if codes & {'heat', 'over_file', 'too_short'} else 5
    return dict(criteria=[dict(key='service', label='Đúng ý, đúng ảnh mẫu', score=service, note='đúng dáng, đúng màu' if service == 5 else 'chưa đúng ý khách'),
                          dict(key='finish', label='Móng bền đẹp', score=finish, note='bóng, đều, khô cứng' if finish == 5 else 'gel chưa đẹp'),
                          dict(key='clean', label='Sạch sẽ, an toàn', score=clean, note='dụng cụ hấp, dũa mới' if clean == 5 else 'chưa sạch, chưa an toàn'),
                          dict(key='gentle', label='Nhẹ tay', score=gentle, note='không đau, không rát' if gentle == 5 else 'làm khách đau'),
                          dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return 'Chị Diệp dặn: thử đèn hơ gel (bóng yếu thì thay), hấp dụng cụ, coi kệ hàng rồi mở tiệm. ' + n['note']
    tail = ''
    if n.get('photo'):
        tail += f' {n["photo"]}'
    if n.get('rush'):
        tail += ' ⏰ Khách đang vội.'
    if n.get('check'):
        tail += ' Khách soi từng móng.'
    return f'{_who(t)} muốn: {svc_text(n)}; dáng {_lower(SHAPES[n["shape"]])}, móng {LEN_NAME[n["length"]]}.{tail} {n["note"]}'.strip()


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    v['cond'] = tree_copy(t['_cond']) if t.get('seen') and t.get('_cond') else None
    for x in v.get('coats') or []:
        x.pop('need', None)
    v['cash'] = till.public(t.get('cash'))
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    lamp = d['lamp']
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS} if c['ext'].get('inv') else {}
    return dict(intro=d['intro'], shop=d['shop'], power=d['power'],
                lamp=dict(kind=lamp['kind'], tested=lamp['tested'], weak=lamp['weak'] if lamp['tested'] else None),
                tools=dict(clean=d['tools']['clean'], by=d['tools']['by']), open={k: v['n'] for k, v in d['open'].items()},
                stock=stock, mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID))


def content() -> dict:
    return dict(colours=COLOURS, regular=list(REGULAR), shapes=SHAPES, lengths={k: LEN_NAME[k] for k in LEN}, art=ART, cuts=CUTS,
                services=SVC, prices=PRICES, cure=CURE, lamps=LAMPS, cure_secs=list(CURE_SECS), soak_s=SOAK_S, rush_s=RUSH_S,
                uses=USES, denoms=list(till.DENOMS), intro=INTRO, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'setup':
        return 'Thử đèn → hấp dụng cụ → coi kệ hàng → Mở tiệm.'
    return ('Hỏi khách → xem móng → bóc dũa mới → tháo sơn cũ → dũa dáng → đẩy da → base, màu hai lớp, top (lớp nào hơ đủ giờ lớp nấy) '
            '→ lau lớp dính → dầu dưỡng → giao móng → thu tiền.')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'clean':
        d['tools'] = dict(clean=True, by=None)
        return 'Đã rửa, hấp lại kềm và cây đẩy da, lau bàn sạch.'
    if e.get('role') == 'greet':
        return 'Đã mời khách ngồi, rót ly trà đá.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tiệm nail sai.')


def _vnum(x, lo, hi) -> None:
    kit.need(type(x) in (int, float) and lo <= x <= hi, 'Dữ liệu tiệm nail sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc tiệm nail không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc tiệm nail sai.')
    for k in ('seen', 'file', 'fixed', 'tip', 'bleed', 'staunch', 'wiped', 'dried', 'oil', 'care'):
        _vbool(t.get(k))
    kit.need(t.get('told') in (None, True, False), 'Dữ liệu tiệm nail sai.')
    rm = t.get('rm')
    kit.need(isinstance(rm, dict) and set(rm) == {'wiped', 'filed', 'wrap', 'off'}, 'Tháo sơn cũ sai.')
    for k in ('wiped', 'filed', 'off'):
        _vbool(rm[k])
    if rm['wrap'] is not None:
        _vnum(rm['wrap'], 0, 10 ** 11)
    kit.need(t.get('shape') is None or t['shape'] in SHAPES, 'Dáng móng sai.')
    kit.need(t.get('len') is None or t['len'] in LEN, 'Độ dài móng sai.')
    kit.need(t.get('cut') is None or t['cut'] in CUTS, 'Làm da sai.')
    coats = t.get('coats')
    kit.need(isinstance(coats, list) and len(coats) <= COAT_MAX + 1, 'Các lớp sơn sai.')
    for x in coats:
        kit.need(isinstance(x, dict) and set(x) == {'l', 'k', 'p', 'th', 'cure', 'need', 'skin'}
                 and x['l'] in ('base', 'color', 'top', 'art') and x['p'] in ('gel', 'thuong') and x['th'] in ('mong', 'day'), 'Lớp sơn sai.')
        if x['l'] == 'color':
            kit.need(x['k'] in COLOUR, 'Lớp sơn sai.')
        elif x['l'] == 'art':
            kit.need(x['k'] in ART and x['p'] == 'gel', 'Lớp sơn sai.')
        else:
            kit.need(x['k'] is None, 'Lớp sơn sai.')
        if x['cure'] is not None:
            kit.integer(x['cure'], 0, 1000)
        kit.integer(x['need'], 0, 1000)
        _vbool(x['skin'])
    fl = t.get('flags')
    kit.need(isinstance(fl, list) and len(fl) <= len(FLAGS) and set(fl) <= set(FLAGS) and len(set(fl)) == len(fl), 'Ghi chú việc sai.')
    kit.integer(t.get('seq'), 0, 1000)
    if t.get('clock') is not None:
        _vnum(t['clock'], 0, 10 ** 11)
    if t.get('price') is not None:
        kit.integer(t['price'], 0, 10 ** 6)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    kit.need(t.get('choice') in (None, 'health', 'stock'), 'Cách giải quyết sai.')
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    till.validate_book(c)
    sh = d['shop']
    kit.need(isinstance(sh, dict) and set(sh) == {'day', 'open', 'stocked'}, 'Tiệm nail sai.')
    kit.integer(sh['day'], 0, 10 ** 7)
    _vbool(sh['open'])
    _vbool(sh['stocked'])
    lamp = d['lamp']
    kit.need(isinstance(lamp, dict) and set(lamp) == {'kind', 'weak', 'tested'} and lamp['kind'] in LAMPS, 'Đèn hơ gel sai.')
    _vbool(lamp['weak'])
    _vbool(lamp['tested'])
    kit.need(d['power'] in ('on', 'off'), 'Điện của tiệm sai.')
    tl = d['tools']
    kit.need(isinstance(tl, dict) and set(tl) == {'clean', 'by'}, 'Dụng cụ sai.')
    _vbool(tl['clean'])
    kit.need(tl['by'] is None or (isinstance(tl['by'], str) and len(tl['by']) <= 80), 'Dụng cụ sai.')
    kit.need(isinstance(d['open'], dict) and set(d['open']) <= set(USES), 'Lọ đang dùng sai.')
    for k, v in d['open'].items():
        kit.need(isinstance(v, dict) and set(v) == {'n', 'c'}, 'Lọ đang dùng sai.')
        kit.integer(v['n'], 1, USES[k])
        kit.integer(v['c'], 0, 10000)
    kit.need(isinstance(d['peel'], list) and len(d['peel']) <= 12, 'Sổ gel bong sai.')
    for x in d['peel']:
        kit.need(isinstance(x, dict) and set(x) == {'id', 'day', 'npc', 'title', 'price'}, 'Sổ gel bong sai.')
        kit.need(isinstance(x['id'], str) and len(x['id']) <= 80 and isinstance(x['title'], str) and len(x['title']) <= 80, 'Sổ gel bong sai.')
        kit.need(isinstance(x['npc'], str) and x['npc'].startswith(f'{ID}_npc_'), 'Sổ gel bong sai.')
        kit.integer(x['day'], 0, 10 ** 7)
        kit.integer(x['price'], 0, 10 ** 6)
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu tiệm nail sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='nl_', category='service',
    meta=dict(short='Làm móng', place='Tiệm nail của chị Diệp', tagline='Móng xinh, dụng cụ sạch, gel bền.', icon='sparkles',
              color='#c2477f', light='#fde8f1', weather='Chiều mát trên phố', work='Khách làm móng', station='Bàn làm móng & đèn',
              greeting='Thử đèn hơ gel, hấp dụng cụ, coi kệ hàng rồi mở tiệm. Xem móng khách trước khi làm, lớp gel nào cũng hơ đủ giờ nhé.',
              caption='Dụng cụ hấp sạch, dũa mới từng khách', map_label='24 · TIỆM NAIL CHỊ DIỆP'),
    people=PEOPLE,
    staff=[('Thắm', 'clean', 'Em họ chị Diệp, hấp dụng cụ, lau bàn kỹ từng góc.', 76, 92),
           ('Na', 'greet', 'Sinh viên làm thêm, mời nước, ghi lịch hẹn.', 84, 74),
           ('Huyền', 'clean', 'Từng làm spa với chị Diệp, quen tay khử trùng.', 72, 94),
           ('Vũ', 'greet', 'Giọng nhẹ nhàng, khách nào cũng nhớ tên.', 80, 80)],
    roles={'clean': 'Hấp dụng cụ, lau bàn', 'greet': 'Đón khách, ghi lịch hẹn'},
    inventory=dict(items=ITEMS, capacity=80),
    prices=PRICES,
    tip=2,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('💅', 'Bàn làm móng gọn gàng', [('Gel màu', 'Kệ sơn'), ('Kềm, cây đẩy da', 'Tủ hấp'), ('Dũa đã dùng', 'Thùng rác'),
                                             ('Bông, giấy bạc', 'Khay ủ gel')],
              ['Thử đèn, hấp dụng cụ', 'Xem móng khách', 'Base, màu, top, hơ đèn', 'Lau lớp dính, giao móng, thu tiền']),
    stories=[('Cái đèn của chị Diệp', ('Hồi còn làm móng tại nhà, chị Diệp mua cái đèn LED sạc pin vì khu chị hay cúp điện.',
                                       'Một tối cúp điện, chị ngồi hơ móng cho khách dưới ánh đèn pin điện thoại.',
                                       'Giờ cái đèn đó nằm trong ngăn kéo tiệm, sạc đầy mỗi sáng.')),
             ('Mười móng đều nhau', ('Chị Kiều đặt bàn tay lên khăn, soi từng móng như soi hàng mỹ phẩm.',
                                     'Bạn dũa chậm từng móng, so hai bàn tay với nhau.',
                                     'Chị Kiều gật đầu: “Được.” Một chữ thôi mà bạn vui cả buổi.')),
             ('Lời nói thật', ('Cô Lan muốn sơn gel che cái móng vàng đục.',
                               'Bạn nói nhẹ nhàng: móng này phải đi khám trước.',
                               'Hai tuần sau cô Lan quay lại, khoe móng đã đỡ, cảm ơn vì hôm đó tiệm nói thật.'))],
    review_asides=['Dụng cụ hấp sạch, dũa mới bóc trước mặt.', 'Gel bóng, hai tuần chưa bong móng nào.', 'Làm nhẹ tay, không đau chút nào.',
                   'Dáng móng y ảnh mẫu luôn.'],
    situations=SITUATIONS,
    guide='Thử đèn → hấp dụng cụ → coi kệ → mở tiệm. Mỗi khách: hỏi → xem móng → dũa mới → tháo sơn cũ → dũa dáng → đẩy da → '
          'base, màu hai lớp, top, lớp nào hơ đủ giờ lớp nấy → lau lớp dính → giao móng → thu tiền.',
)
