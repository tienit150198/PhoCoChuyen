"""Salon Tóc Gió — a neighbourhood hair salon (plugin career).

Real work of the job: seat the client and listen; consult (chemical history,
patch-test record, lifestyle, length, budget) and look at the hair yourself
(roots, lengths, ends, scalp); agree an honest plan — the reference photo may
need several sessions; patch test before any dye when there is no record
(game rule: colour on another game day); strand test before bleaching box-dyed
hair; mix a formula (tube level/tone, developer volume, ratio) and rinse inside
a real-time processing window (narrower on previously dyed hair); wash; cut in
a guided sequence (sections → guide length → layers → symmetry check — too
short cannot be undone); treat and style; check out with product advice that
fits both the hair and the budget.

Every number here is a simplified GAME rule, not an instruction for real
chemicals. Imperfect work can still be paid (the review tells the truth);
unsafe work is stopped (no patch record, scratched scalp, 40 vol on the scalp,
bleach on box dye without a strand test).

v0.5 (tasks with gen=2; saves from before keep their clients through the legacy
serial band): a luck-of-the-day modifier, a two-tube mixing bowl (parts of two
tubes → level and tone, grey coverage needs a natural base, brassy hair warms
the mix), special clients (filtered reference photo, patch-test reaction with a
salon allergy book, a wriggly kid with a calm meter, a bride on a deadline with
an updo, an express walk-in, grey coverage, colour correction) and surprise
events at the counter (kit desk engine) that block work until decided — except
rinsing, because a processing timer never waits.
"""
from __future__ import annotations
import copy
from ..jsoncopy import tree_copy
from . import kit
from .. import consequences as cq
from .. import archive as ar

ID = 'salon'

SERVICES = [
    dict(id='color', name='Nhuộm màu', emoji='🎨', chem=True),
    dict(id='bleach', name='Tẩy sáng', emoji='⚗️', chem=True),
    dict(id='toner', name='Phủ toner', emoji='💜', chem=True),
    dict(id='cut', name='Cắt', emoji='✂️', chem=False),
    dict(id='treatment', name='Phục hồi keratin', emoji='💧', chem=False),
    dict(id='style', name='Sấy tạo kiểu', emoji='💨', chem=False),
]
SERVICE_IDS = [x['id'] for x in SERVICES]
SERVICE_INDEX = {x['id']: x for x in SERVICES}
CHEM = ('color', 'bleach', 'toner')
DYE_SERVICES = ('color', 'toner')          # need a patch-test record (game rule)
PRICES = {'cut': 30, 'color': 60, 'bleach': 70, 'toner': 25, 'treatment': 35, 'style': 15, 'patch': 8}

LEVELS = [
    dict(level=1, name='Đen', color='#17110e'), dict(level=2, name='Nâu đen', color='#2a1b14'),
    dict(level=3, name='Nâu tối', color='#3d2719'), dict(level=4, name='Nâu', color='#553724'),
    dict(level=5, name='Nâu sáng', color='#6f4b31'), dict(level=6, name='Vàng tối', color='#8c6440'),
    dict(level=7, name='Vàng', color='#ad8452'), dict(level=8, name='Vàng sáng', color='#caa56c'),
    dict(level=9, name='Vàng rất sáng', color='#e0c58e'), dict(level=10, name='Bạch kim', color='#efe4c6'),
]
LEVEL_COLOR = {x['level']: x['color'] for x in LEVELS}
DYES = [
    dict(id='dye_3_0', code='3.0', level=3, tone='Nâu tối tự nhiên', color='#3d2719', fam='N'),
    dict(id='dye_4_6', code='4.6', level=4, tone='Đỏ rượu vang', color='#6d2433', fam='R'),
    dict(id='dye_5_0', code='5.0', level=5, tone='Nâu sáng tự nhiên', color='#6f4b31', fam='N'),
    dict(id='dye_6_1', code='6.1', level=6, tone='Nâu lạnh ánh tro', color='#7d6a5a', fam='A'),
    dict(id='dye_7_3', code='7.3', level=7, tone='Vàng mật ong', color='#b98a45', fam='G'),
    dict(id='dye_8_1', code='8.1', level=8, tone='Vàng tro', color='#bfae90', fam='A'),
]
# Tone of a tube family (×20 in the maths): ash −1, natural 0, gold +1, red +2.
TONE = {'N': 0, 'A': -1, 'G': 1, 'R': 2}
BANDS = [dict(id='ash', name='Lạnh ánh tro'), dict(id='cool', name='Hơi lạnh'), dict(id='natural', name='Tự nhiên'),
         dict(id='warm', name='Ấm'), dict(id='deep', name='Ấm đậm (mật ong, đỏ)')]
BAND_IDS = [x['id'] for x in BANDS]
BAND_NAME = {x['id']: x['name'] for x in BANDS}
MIX_PARTS = (1, 2, 3)
DYE_INDEX = {x['id']: x for x in DYES}
TONERS = [
    dict(id='toner_silver', code='T-bạc', tone='Khói bạc (khử cam vàng)', color='#b9b7c9'),
    dict(id='toner_beige', code='T-be', tone='Be sữa ấm', color='#d9c7a8'),
]
TONER_INDEX = {x['id']: x for x in TONERS}
DEVS = [10, 20, 30, 40]
DEV_ITEM = {10: 'dev_10', 20: 'dev_20', 30: 'dev_30', 40: 'dev_40'}
RATIOS = ['1:1', '1:1.5', '1:2']
# Processing windows in real seconds: <under under-processed, ≤ideal ideal, ≤over over-processed, beyond → damage.
WINDOWS = {
    'color': dict(under=10, ideal=18, over=26),
    'bleach': dict(under=8, ideal=15, over=20),
    'bleach_fragile': dict(under=8, ideal=11, over=14),
    'toner': dict(under=4, ideal=8, over=12),
}
ZONES_T = ('under', 'ideal', 'over', 'damage')
CUT_STEPS = ['section', 'guide', 'layers', 'check']
FINISHES = [
    dict(id='natural', name='Sấy tự nhiên', emoji='🍃', note='Tự làm lại trong 2–5 phút'),
    dict(id='sleek', name='Sấy thẳng suôn', emoji='🪮', note='Gọn, lịch sự · khoảng 10 phút'),
    dict(id='volume', name='Sấy phồng, lọn sóng', emoji='🌊', note='Dự tiệc · 20 phút nếu tự làm'),
    dict(id='updo', name='Búi cô dâu', emoji='👰', note='Ngày cưới · kẹp ghim, giữ nếp cả buổi'),
]
FINISH_IDS = [x['id'] for x in FINISHES]
TOPICS = [
    dict(id='history', label='Lịch sử hóa chất', emoji='🧪', ask='Tóc mình từng nhuộm, tẩy, uốn hay duỗi chưa?'),
    dict(id='patch', label='Thử dị ứng', emoji='🩹', ask='Mình đã có kết quả thử dị ứng thuốc nhuộm chưa?'),
    dict(id='lifestyle', label='Thói quen tạo kiểu', emoji='⏰', ask='Mỗi sáng mình dành bao nhiêu phút cho tóc?'),
    dict(id='length', label='Độ dài mong muốn', emoji='📏', ask='Mình muốn giữ lại dài tới đâu?'),
    dict(id='budget', label='Ngân sách', emoji='💰', ask='Hôm nay mình dự tính khoảng bao nhiêu?'),
]
TOPIC_IDS = [x['id'] for x in TOPICS]
ZONES = [
    dict(id='roots', label='Chân tóc', emoji='🌱'),
    dict(id='lengths', label='Thân tóc', emoji='〰️'),
    dict(id='ends', label='Ngọn tóc', emoji='🪶'),
    dict(id='scalp', label='Da đầu', emoji='🔎'),
]
ZONE_IDS = [x['id'] for x in ZONES]
FLAGS = ('overpromise', 'pushy', 'breakage', 'no_patch', 'skip_patch', 'scalp_stop', 'wet_color', 'cut_short', 'no_strand', 'layers_wrong', 'finish_wrong',
         'slip', 'grey_show', 'photo_blind', 'dye_no_patch', 'allergy_hit', 'weak_stop')
RULES = [
    'Nhuộm cùng tông hoặc tối hơn: oxy 10 vol (3%).',
    'Nâng 1–2 tông trên tóc tự nhiên, phủ bạc: oxy 20 vol (6%).',
    'Nâng 3 tông: oxy 30 vol (9%). Oxy 40 vol (12%) không bao giờ thoa sát da đầu.',
    'Thuốc nhuộm không nâng được màu nhuộm cũ; muốn sáng hơn phải tẩy.',
    'Tỷ lệ trộn: thuốc nhuộm 1:1 · bột tẩy 1:2 với 20 vol · toner 1:2 với 10 vol.',
    'Chưa có kết quả thử dị ứng → thử trước, hẹn nhuộm từ ngày sau.',
    'Tóc nhuộm hộp: thử lọn trước khi tẩy. Tóc đã qua hóa chất: cửa sổ ủ tẩy ngắn hơn.',
    'Da đầu trầy, viêm: hôm đó không thoa hóa chất.',
    'Nhuộm, tẩy trên tóc khô chưa gội; xả thuốc xong mới gội.',
    'Tóc yếu sau hóa chất nên phục hồi; chỉ mời sản phẩm hợp tóc và vừa ngân sách.',
    'Bát hai tuýp: level = trung bình theo phần; ánh tro kéo lạnh, ánh vàng/đỏ kéo ấm. Lệch tối đa ¼ tông.',
    'Tóc bạc từ một nửa trở lên: ít nhất một nửa bát là tuýp nền tự nhiên (x.0).',
    'Nền tóc ánh cam đồng làm màu mới ấm thêm một bậc — pha lạnh hơn để bù.',
]
DISCLAIMER = ''

ITEMS = [
    *[dict(id=x['id'], name=f'Tuýp {x["code"]} · {x["tone"]}', emoji='🎨', group='ingredient', unit='tuýp', cost=6, life=60, start=4) for x in DYES],
    dict(id='dev_10', name='Oxy 10 vol (3%)', emoji='🧴', group='ingredient', unit='lượt', cost=2, life=60, start=6),
    dict(id='dev_20', name='Oxy 20 vol (6%)', emoji='🧴', group='ingredient', unit='lượt', cost=2, life=60, start=8),
    dict(id='dev_30', name='Oxy 30 vol (9%)', emoji='🧴', group='ingredient', unit='lượt', cost=2, life=60, start=4),
    dict(id='dev_40', name='Oxy 40 vol (12%)', emoji='🧴', group='ingredient', unit='lượt', cost=3, life=60, start=2),
    dict(id='bleach', name='Bột tẩy', emoji='⚗️', group='ingredient', unit='gói', cost=5, start=4),
    dict(id='toner_silver', name='Toner khói bạc', emoji='💜', group='ingredient', unit='tuýp', cost=5, life=60, start=3),
    dict(id='toner_beige', name='Toner be sữa', emoji='🤎', group='ingredient', unit='tuýp', cost=5, life=60, start=3),
    dict(id='shampoo', name='Dầu gội salon', emoji='🫧', group='supply', unit='lượt', cost=1, start=20),
    dict(id='conditioner', name='Dầu xả', emoji='🧴', group='supply', unit='lượt', cost=1, start=20),
    dict(id='towel', name='Khăn sạch', emoji='🧺', group='supply', unit='chiếc', cost=1, start=20),
    dict(id='keratin', name='Keratin phục hồi', emoji='💧', group='care', unit='lượt', cost=8, life=30, start=4),
    dict(id='foil', name='Giấy bạc', emoji='🪙', group='tool', unit='xấp', cost=1, start=6),
    dict(id='gloves', name='Găng tay', emoji='🧤', group='tool', unit='đôi', cost=1, start=16),
    dict(id='rt_colorsafe', name='Dầu gội giữ màu', emoji='🌸', group='goods', unit='chai', cost=12, price=25, start=3),
    dict(id='rt_mask', name='Kem ủ phục hồi', emoji='🫙', group='goods', unit='hũ', cost=14, price=30, start=3),
    dict(id='rt_heat', name='Xịt chống nhiệt', emoji='🔥', group='goods', unit='chai', cost=10, price=22, start=3),
    dict(id='rt_purple', name='Dầu gội tím khử vàng', emoji='💜', group='goods', unit='chai', cost=12, price=26, start=3),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}
RETAIL_IDS = [x['id'] for x in ITEMS if x['group'] == 'goods']

PEOPLE = [
    ('Chị Thảo', 'Nhân viên văn phòng', 'Chỉn chu, sợ màu lố khi lên hình hội nghị.', 'picky'),
    ('Hà Mi', 'Sinh viên mê idol', 'Hay mang ảnh idol tới, muốn đổi màu liền tay.', 'genz'),
    ('Cô Ngọc', 'Giáo viên về hưu', 'Hiền, hơi lo khi lần đầu nhuộm phủ bạc.', 'warm'),
    ('Anh Tùng', 'Thợ cơ khí', 'Ít nói, cần cắt nhanh gọn trước giờ vào xưởng.', 'quiet'),
    ('Bà Lựu', 'Khách quen lắm chuyện', 'Thích đổi gió, thích hỏi chuyện thiên hạ.', 'bossy'),
    ('Chị Vy', 'MC tiệc cưới', 'Thẳng tính, lúc nào cũng vội.', 'sour'),
    ('Mẹ bé Su', 'Phụ huynh', 'Đưa bé Su 4 tuổi đi cắt tóc lần đầu.', 'warm'),
    ('Chị Hồng', 'Kế toán', 'Da nhạy cảm nhưng hay ngại nói, tin là “thử năm ngoái rồi”.', 'warm'),
    ('Bố bé Bin', 'Phụ huynh', 'Dắt bé Bin 5 tuổi hiếu động, ngồi đâu được đó hai phút.', 'warm'),
    ('Cô dâu Trâm', 'Cô dâu', 'Chiều nay rước dâu, hồi hộp từng phút.', 'picky'),
    ('Chú Hải', 'Tài xế xe ôm', 'Tóc bạc nhiều, muốn trẻ ra mà vẫn tự nhiên.', 'quiet'),
    ('Bảo Ngân', 'Người làm video ngắn', 'Ảnh nào cũng qua filter, mê tóc khói.', 'genz'),
    ('Chị Diệu', 'Chủ tiệm tạp hóa', 'Tự nhuộm ở nhà, lên màu cam đồng, ngại ra đường.', 'sour'),
    ('Chị Mai', 'Nhân viên ngân hàng', 'Muốn màu ấm áp mà vẫn nghiêm túc khi đi làm.', 'picky'),
    ('Anh Phát', 'Tài xế giao hàng', 'Tạt vào giữa hai cuốc, lúc nào cũng nhìn đồng hồ.', 'quiet'),
    ('Chị Bích', 'Đại lý mỹ phẩm', 'Mối hàng quen, hay chào lô giá mềm.', 'warm'),
    ('Cô Tám', 'Cán bộ y tế phường', 'Kỹ tính, lật sổ vệ sinh từng dòng.', 'picky'),
]

# Client templates. `hair` and `key` are private (the stylist discovers them).
CLIENTS = [
    dict(npc=0, min_day=1, title='Nâu lạnh đi làm, tỉa ngọn',
         opening='Chào em, chị muốn đổi màu tóc cho tươi hơn mà vẫn đi làm được.',
         want='Nhuộm nâu lạnh sáng hơn chút, tỉa phần ngọn xơ, sấy suôn.', services=['color', 'cut', 'style'],
         photo=dict(level=6, tone='Nâu lạnh ánh tro', style='Ngang vai, suôn thẳng'),
         note='Chị hay lên hình hội nghị, đừng để ra ánh đỏ nha.',
         hair=dict(level=4, shown=4, length=40, history='virgin', patch=True, damage=1, scalp='ok'),
         say=dict(history='Chưa nhuộm bao giờ em, tóc zin.', lifestyle='Sáng chị có 10 phút, chải thẳng rồi đi làm.',
                  length='Giữ ngang vai nha, cắt bỏ phần xơ thôi.', budget='Tầm 140 xu đổ lại em nhé.',
                  patch='Tháng trước chị thử dị ứng ở đây rồi, không bị gì.'),
         find=dict(roots='Chân tóc tự nhiên level 4 (nâu), không có tóc bạc.', lengths='Thân tóc zin, đều màu level 4; sợi trung bình, dày vừa.',
                   ends='Ngọn khô, chẻ khoảng 2–3 cm.', scalp='Da đầu khỏe, không trầy xước.'),
         key=dict(color=dict(shade='dye_6_1', dev=20, ratio='1:1'), cut=dict(min=2, max=4, layers=False), finish='sleek',
                  fit=['rt_colorsafe'], sessions=1, must_ask=['history', 'patch', 'length'], must_inspect=['ends'], budget=140)),
    dict(npc=1, min_day=2, title='Bạch kim như ảnh idol',
         opening='Chị ơi em muốn tóc y chang ảnh này nè, tối nay em đi concert!',
         want='Tẩy lên bạch kim khói như ảnh idol, phủ toner, hấp phục hồi.', services=['bleach', 'toner', 'treatment'],
         photo=dict(level=10, tone='Bạch kim khói bạc', style='Bob ngang cằm (đã có sẵn)'),
         note='Em nhuộm đen ở nhà có một lần thôi à, lâu rồi.',
         hair=dict(level=4, shown=3, length=22, history='box_dye', patch=True, damage=2, scalp='ok'),
         say=dict(history='Dạ em tự nhuộm đen bằng thuốc hộp mua trên mạng, chắc nửa năm rồi.', lifestyle='Em sấy 15 phút mỗi sáng, thích thử kiểu mới.',
                  length='Không cắt đâu ạ, em mới cắt bob.', budget='Em để dành được 170 xu.', patch='Em thử dị ứng ở tiệm hồi tháng trước rồi ạ.'),
         find=dict(roots='Chân tóc mọc mới 2 cm, tự nhiên level 4.',
                   lengths='Thân tóc nhuộm hộp màu đen level 3, bám dày, ánh xanh đen — màu nhân tạo, tẩy lên sẽ loang cam.',
                   ends='Ngọn hơi giòn, dễ gãy nếu tẩy mạnh.', scalp='Da đầu khỏe.'),
         strand='Lọn thử sau một lần tẩy lên level 7 ánh cam vàng; sợi hơi giãn nhưng không đứt. Muốn tới bạch kim cần khoảng 3 buổi, mỗi buổi cách 2 tuần.',
         key=dict(bleach=dict(dev=20, ratio='1:2'), toner=dict(shade='toner_silver', dev=10, ratio='1:2'), strand=True,
                  fit=['rt_purple', 'rt_mask'], sessions=3, must_ask=['history'], must_inspect=['lengths'], budget=170)),
    dict(npc=2, min_day=1, title='Nhuộm phủ bạc lần đầu',
         opening='Cô muốn nhuộm phủ tóc bạc, lần đầu cô ghé tiệm mình.',
         want='Nhuộm phủ bạc màu nâu tự nhiên, tỉa gọn đuôi và tỉa tầng nhẹ cho bồng.', services=['color', 'cut'],
         photo=dict(level=5, tone='Nâu tự nhiên', style='Ngắn ngang gáy, tỉa tầng nhẹ'),
         note='Con gái cô bảo nhuộm ở đâu cũng được, cô thì hơi lo.',
         hair=dict(level=5, shown=5, length=18, history='virgin', patch=False, damage=0, scalp='ok'),
         say=dict(history='Cô chưa nhuộm bao giờ, tóc bạc cứ để vậy.', lifestyle='Cô gội xong để khô tự nhiên thôi con.',
                  length='Tỉa gọn đuôi, tỉa tầng nhẹ cho bồng, đừng ngắn quá gáy.', budget='Cô mang theo 120 xu.',
                  patch='Thử dị ứng hả con? Cô chưa thử bao giờ.'),
         find=dict(roots='Chân tóc level 5, khoảng 40% tóc bạc.', lengths='Tóc zin, sợi to, dày.',
                   ends='Ngọn khỏe, chỉ cần tỉa 1–2 cm cho gọn.', scalp='Da đầu khỏe.'),
         key=dict(color=dict(shade='dye_5_0', dev=20, ratio='1:1'), cut=dict(min=1, max=2, layers=True), finish=None,
                  fit=[], sessions=1, must_ask=['patch', 'length'], must_inspect=['roots'], budget=120)),
    dict(npc=3, min_day=1, title='Undercut gọn cho mùa nóng',
         opening='Cắt giùm anh cho mát, chiều anh còn vào xưởng.',
         want='Cắt ngắn gọn kiểu undercut, sấy nhanh.', services=['cut', 'style'],
         photo=dict(level=None, tone='', style='Undercut, phần đỉnh để lại khoảng 5 cm'),
         note='Đừng vuốt keo nhiều, anh không quen.',
         hair=dict(level=2, shown=2, length=11, history='virgin', patch=True, damage=0, scalp='ok'),
         say=dict(history='Chưa làm gì hết.', lifestyle='Sáng anh vuốt nước là đi, 2 phút.',
                  length='Phần đỉnh hiện dài 11 phân, để lại chừng 4–6 phân.', budget='Năm chục xu.', patch='Anh đâu có nhuộm.'),
         find=dict(roots='Tóc đen level 2, mọc dày.', lengths='Sợi to, cứng; hai bên đã dài chạm tai.', ends='Ngọn khỏe.',
                   scalp='Da đầu hơi nhiều dầu, không trầy.'),
         key=dict(cut=dict(min=5, max=7, layers=False), finish='natural', fit=[], sessions=1, must_ask=['length', 'lifestyle'],
                  must_inspect=[], budget=60)),
    dict(npc=5, min_day=1, title='Tóc bóng mượt để làm MC',
         opening='Tối nay chị dẫn tiệc cưới, tóc khô như rơm, cứu chị với.',
         want='Hấp phục hồi cho bóng, sấy phồng lọn sóng nhẹ dự tiệc. Không cắt.', services=['treatment', 'style'],
         photo=dict(level=8, tone='Giữ màu hiện tại', style='Sóng nhẹ buông vai'),
         note='Chị không muốn cắt ngắn đâu nha, nói trước.',
         hair=dict(level=5, shown=8, length=35, history='bleached', patch=True, damage=3, scalp='ok'),
         say=dict(history='Chị highlight tẩy từ Tết, sau đó còn duỗi một lần.', lifestyle='Bình thường chị buộc tóc, nay đi tiệc nên cần đẹp.',
                  length='Không cắt! Giữ nguyên.', budget='Chị trả 75 xu, miễn đẹp.', patch='Có thử rồi.'),
         find=dict(roots='Chân tóc tự nhiên level 5 mọc 4 cm.', lengths='Thân tóc đã tẩy level 8, rỗng, hút nước rất nhanh.',
                   ends='Ngọn rất xơ, dễ gãy khi kéo nhiệt cao.', scalp='Da đầu bình thường.'),
         key=dict(finish='volume', fit=['rt_heat', 'rt_mask'], sessions=1, must_ask=['history'], must_inspect=['ends'], budget=75)),
    dict(npc=6, min_day=1, title='Mái bằng đầu đời của bé Su',
         opening='Bé Su 4 tuổi, lần đầu cắt ở tiệm, hơi sợ kéo đó em.',
         want='Cắt mái bằng qua lông mày, tỉa đuôi gọn cho bé đi học.', services=['cut'],
         photo=dict(level=None, tone='', style='Mái bằng, tóc ngang vai'),
         note='Bé mà khóc thì cho mẹ bế nha.',
         hair=dict(level=2, shown=2, length=26, history='virgin', patch=True, damage=0, scalp='ok'),
         say=dict(history='Tóc bé chưa làm gì hết.', lifestyle='Sáng mẹ chỉ kịp chải rồi kẹp.',
                  length='Mái chạm lông mày, đuôi cắt đúng 2 phân thôi nha.', budget='50 xu nha em.', patch='Bé không nhuộm đâu.'),
         find=dict(roots='Tóc bé mềm, đen tự nhiên.', lengths='Sợi mảnh, hơi rối ở gáy.', ends='Ngọn khỏe, tỉa 2 cm là gọn.',
                   scalp='Da đầu bé nhạy, dùng dầu gội dịu nhẹ.'),
         key=dict(cut=dict(min=2, max=2, layers=False), finish=None, fit=[], sessions=1, must_ask=['length'], must_inspect=[], budget=50)),
    dict(npc=4, min_day=2, title='Đỏ rượu vang cho sang',
         opening='Bà muốn đổi gió, nhuộm đỏ rượu vang như bà bạn cùng hội dưỡng sinh!',
         want='Nhuộm đỏ rượu vang, gội sấy phồng.', services=['color', 'style'],
         photo=dict(level=4, tone='Đỏ tím rượu vang', style='Ngắn, sấy phồng'),
         note='Hôm qua bà gãi đầu hơi mạnh vì ngứa, chắc không sao đâu.',
         hair=dict(level=4, shown=4, length=16, history='virgin', patch=True, damage=1, scalp='scratch'),
         say=dict(history='Bà chưa nhuộm, chỉ uốn phồng từ năm ngoái.', lifestyle='Sáng bà chải phồng 10 phút.',
                  length='Không cắt.', budget='Bà có 110 xu.', patch='Có, tiệm thử cho bà tuần trước.'),
         find=dict(roots='Chân tóc level 4, lác đác vài sợi bạc.', lengths='Thân tóc uốn cũ, hơi khô.', ends='Ngọn hơi xơ nhẹ.',
                   scalp='Da đầu có vài vết trầy đỏ mới do gãi — không thoa hóa chất lên da đầu tổn thương (luật an toàn của salon).'),
         key=dict(color=dict(shade='dye_4_6', dev=10, ratio='1:1'), postpone=['color'], finish='volume', fit=[], sessions=1,
                  must_ask=['patch'], must_inspect=['scalp'], budget=110)),
    dict(npc=1, min_day=4, title='Buổi 2: vàng tro hết cam',
         opening='Em quay lại nè chị! Tóc hết đen rồi mà hơi cam, buổi này mình làm gì ạ?',
         want='Nhuộm vàng tro khử cam, hấp phục hồi, sấy suôn.', services=['color', 'treatment', 'style'],
         photo=dict(level=8, tone='Vàng tro lạnh', style='Bob ngang cằm'),
         note='Lần trước chị dặn đúng 2 tuần mới quay lại, em nhớ nè.',
         hair=dict(level=7, shown=7, length=23, history='bleached', patch=True, damage=2, scalp='ok'),
         say=dict(history='Buổi trước tiệm tẩy cho em một lần, về em dùng dầu gội tím đều.', lifestyle='Em sấy 15 phút.',
                  length='Không cắt ạ.', budget='Em có 150 xu.', patch='Có rồi ạ.'),
         find=dict(roots='Chân tóc mọc 1 cm, level 4.', lengths='Thân tóc đã tẩy level 7, ánh cam nhẹ, hơi rỗng.',
                   ends='Ngọn khô nhưng không gãy.', scalp='Da đầu khỏe.'),
         key=dict(color=dict(shade='dye_8_1', dev=20, ratio='1:1'), finish='sleek', fit=['rt_purple'], sessions=1,
                  must_ask=['history'], must_inspect=['lengths'], budget=150)),
]
KEY_DEFAULTS = dict(color=None, bleach=None, toner=None, strand=False, cut=None, finish=None, fit=[], sessions=1,
                    must_ask=[], must_inspect=[], postpone=[], budget=100)

FIXED = ('needs', '_hair', '_key', '_x', 'gen')


# ------------------------------------------------------------------ tasks
def _make_v1(day: int, slot: int, serial: int) -> dict:
    """The generator saves from before v0.5 were made with (kept unchanged for them)."""
    pool = [x for x in CLIENTS if x['min_day'] <= day]
    x = pool[(kit.rng(ID, day).randrange(len(pool)) + slot) % len(pool)]   # distinct clients within a day
    hair = dict(copy.deepcopy(x['hair']), say=dict(x['say']), find=dict(x['find']),
                strand=x.get('strand', 'Lọn thử lên đều, sợi khỏe — tóc chịu được tẩy nhẹ.'))
    key = dict(copy.deepcopy(KEY_DEFAULTS), **copy.deepcopy(x['key']))
    needs = dict(want=x['want'], services=list(x['services']), photo=dict(x['photo']), note=x['note'])
    return kit.base_task(ID, day, slot, serial, x['npc'], x['title'], x['opening'], needs=needs, _hair=hair, _key=key,
                         asked=[], patch_record=None, plan=None, quote=None, patch_fee=0, bowl=None, timer=None, results={},
                         cut=_empty_cut(), washed=False, patch_done=False, strand=False, treated=False, styled=None,
                         done=[], flags=[], sold=[], declined=[], cost=0)


# ------------------------------------------------------------------ v0.5: luck of the day, mixing bowl, special clients
GEN = 2
TODAY = [
    dict(id='steady', title='Ngày thường', emoji='☀️', weight=3, text='Khách đều đều, làm kỹ từng người.'),
    dict(id='wedding', title='Mùa cưới', emoji='💍', min_day=2, weight=2, text='Cô dâu và khách dự tiệc ghé nhiều, ai cũng cần kịp giờ.'),
    dict(id='heat', title='Nắng nóng 38°C', emoji='🥵', min_day=2, weight=2, text='Thuốc lên nhanh hơn: vùng xanh khi ủ tới sớm hơn thường lệ.'),
    dict(id='walkin', title='Thứ bảy đông khách vãng lai', emoji='🚶', min_day=2, weight=2, text='Khách tạt vào liên tục, ai cũng sốt ruột hơn một chút.'),
    dict(id='school', title='Tuần tựu trường', emoji='🎒', min_day=2, weight=2, text='Phụ huynh dắt con đi cắt tóc; các bé khó ngồi yên.'),
    dict(id='rain', title='Mưa dầm', emoji='🌧️', min_day=2, weight=2, text='Khách thưa, tóc ẩm dễ xù; mái hiên có chỗ dột.'),
]
TODAY_INDEX = {x['id']: x for x in TODAY}
SPECIAL_P = (0.3, 0.4, 0.5, 0.6)           # chance a slot (after the first) is a special client, by tier
CASES = {
    'photo': dict(emoji='📸', label='Ảnh mẫu qua filter'),
    'react': dict(emoji='🩹', label='Thử dị ứng lại'),
    'kid': dict(emoji='🧒', label='Bé khó ngồi yên'),
    'bride': dict(emoji='👰', label='Cô dâu kịp giờ'),
    'walkin': dict(emoji='⏱️', label='Khách vãng lai gấp'),
    'grey': dict(emoji='🤍', label='Tóc bạc nhiều'),
    'fix': dict(emoji='🧯', label='Cứu màu tự nhuộm'),
}
CALM_TOOLS = [
    dict(id='cartoon', emoji='📱', label='Mở phim hoạt hình'),
    dict(id='toy', emoji='🦖', label='Đưa đồ chơi khủng long'),
    dict(id='lap', emoji='🤗', label='Cho ngồi trong lòng bố'),
    dict(id='game', emoji='🗿', label='Chơi trò “tượng đá”'),
]
CALM_IDS = [x['id'] for x in CALM_TOOLS]
CALM_HINT = {
    'cartoon': 'Ở nhà mở phim hoạt hình là bé ngồi im như tượng, không thì leo trèo cả buổi.',
    'toy': 'Bé đi đâu cũng ôm con khủng long nhựa, ai lấy là khóc.',
    'lap': 'Bé bám bố lắm, rời tay bố ra là giãy.',
    'game': 'Cô giáo mẫu giáo hay cho chơi trò “tượng đá”, về nhà bé đòi chơi hoài.',
}
CALM_BEST, CALM_OTHER = 35, 10
PHOTO_REAL = [
    dict(level=7, tone='ash', text='Lật ảnh gốc chưa filter: dưới đèn thường tóc chỉ là vàng tro khói level 7 — filter kéo sáng thêm hai tông và phủ ánh bạc.'),
    dict(level=6, tone='cool', text='Lật ảnh gốc chưa filter: màu thật là nâu khói hơi lạnh level 6 — filter kéo sáng ba tông và làm trắng ánh.'),
]


def _col(level: int, tone: str, dev: int, grey: bool = False) -> dict:
    return dict(level=level, tone=tone, dev=dev, ratio='1:1', grey=grey)


def _c(key, npc, title, opening, want, services, photo, note, hair, say, find, k, case=None, min_day=1, weight=2,
       mods=(), strand=None, more=None) -> dict:
    return dict(key=key, npc=npc, title=title, opening=opening, want=want, services=list(services), photo=photo, note=note,
                hair=hair, say=say, find=find, k=k, case=case, min_day=min_day, weight=weight, mods=tuple(mods),
                strand=strand, more=more or {})


def _v1(title: str, key: str, opening: str | None = None, colour: dict | None = None, **over) -> dict:
    """An everyday client of the first generator, with a neutral greeting and a level/tone colour target."""
    x = next(v for v in CLIENTS if v['title'] == title)
    k = copy.deepcopy(x['key'])
    photo = dict(x['photo'])
    if colour:
        k['color'] = colour
        photo['band'] = colour['tone']
    row = _c(key, x['npc'], x['title'], opening or x['opening'], x['want'], x['services'], photo, x['note'],
             copy.deepcopy(x['hair']), dict(x['say']), dict(x['find']), k, min_day=x['min_day'], strand=x.get('strand'))
    row.update(over)
    return row


JOBS2 = [
    # ---- everyday clients (the first client of a day is always one of these)
    _v1('Nâu lạnh đi làm, tỉa ngọn', 'c_office', colour=_col(6, 'ash', 20)),
    _v1('Bạch kim như ảnh idol', 'c_idol', opening='Tiệm ơi, em muốn tóc y chang ảnh này nè, tối nay em đi concert!'),
    _v1('Nhuộm phủ bạc lần đầu', 'c_grey', colour=_col(5, 'natural', 20)),
    _v1('Undercut gọn cho mùa nóng', 'c_undercut', mods=('walkin',)),
    _v1('Tóc bóng mượt để làm MC', 'c_mc', mods=('wedding', 'rain')),
    _v1('Mái bằng đầu đời của bé Su', 'c_su', mods=('school',)),
    _v1('Đỏ rượu vang cho sang', 'c_red', colour=_col(4, 'deep', 10)),
    _v1('Buổi 2: vàng tro hết cam', 'c_idol2', opening='Em quay lại rồi nè! Tóc hết đen rồi mà hơi cam, buổi này mình làm gì ạ?',
        colour=_col(8, 'ash', 20)),
    _c('c_choco', 5, 'Nâu socola ấm cho mùa tiệc', 'Cuối năm chị chạy show liên tục, muốn tóc nâu socola ấm cho lên đèn đẹp.',
       'Nhuộm nâu socola ấm level 5, sấy phồng dự tiệc.', ['color', 'style'],
       dict(level=5, tone='Nâu socola ấm', style='Dài ngang vai, sấy phồng', band='warm'), 'Đừng ra đỏ quá nha, chị dẫn tiệc cưới.',
       dict(level=4, shown=4, length=34, history='virgin', patch=True, damage=1, scalp='ok'),
       dict(history='Tóc chị chưa nhuộm bao giờ, chỉ hay sấy nóng.', lifestyle='Đi show là chị sấy phồng, mười lăm phút.',
            length='Không cắt nha.', budget='Tầm 110 xu.', patch='Tháng rồi thử dị ứng ở đây, ổn.'),
       dict(roots='Chân tóc tự nhiên level 4, không có tóc bạc.', lengths='Thân tóc zin level 4, sợi khỏe.',
            ends='Ngọn hơi khô vì nhiệt.', scalp='Da đầu khỏe.'),
       dict(color=_col(5, 'warm', 20), finish='volume', fit=['rt_heat'], sessions=1, must_ask=['history', 'patch'],
            must_inspect=['roots'], budget=110), min_day=2, mods=('wedding',)),
    _c('c_honey', 13, 'Vàng mật ong dịu đi làm', 'Chào em, chị muốn tóc sáng ấm như mật ong mà vẫn đi làm ngân hàng được.',
       'Nhuộm vàng mật ong dịu level 7 (ấm vừa, không đỏ), sấy suôn.', ['color', 'style'],
       dict(level=7, tone='Mật ong dịu', style='Ngang vai, suôn', band='warm'), 'Ngân hàng không cho màu chói, dịu thôi nha.',
       dict(level=6, shown=6, length=30, history='virgin', patch=True, damage=0, scalp='ok'),
       dict(history='Chị chưa nhuộm lần nào.', lifestyle='Sáng chị chải thẳng là đi, năm phút.', length='Giữ nguyên độ dài.',
            budget='Chị để 110 xu.', patch='Có thử dị ứng rồi, sổ tiệm có ghi.'),
       dict(roots='Chân tóc tự nhiên level 6, sáng sẵn.', lengths='Thân tóc zin, sợi mảnh.', ends='Ngọn khỏe.', scalp='Da đầu khỏe.'),
       dict(color=_col(7, 'warm', 20), finish='sleek', fit=['rt_colorsafe'], sessions=1, must_ask=['history'],
            must_inspect=['roots'], budget=110), min_day=3),
    # ---- special clients
    _c('s_photo', 11, 'Ảnh filter “tóc khói”', 'Tiệm ơi, làm em y chang ảnh này nha, em quay video giới thiệu tóc mới luôn!',
       'Nhuộm tóc khói như ảnh, sấy phồng lọn sóng.', ['color', 'style'],
       dict(level=9, tone='Khói bạc lạnh', style='Dài ngang lưng, sóng nhẹ', band='ash', filtered=True), 'Ảnh em tự chụp đó, đẹp hông?',
       dict(level=5, shown=5, length=48, history='virgin', patch=True, damage=0, scalp='ok'),
       dict(history='Tóc em zin, chưa làm gì.', lifestyle='Em sấy mười phút rồi quay video.', length='Không cắt nha.',
            budget='Em có 120 xu.', patch='Em thử dị ứng ở đây rồi.'),
       dict(roots='Chân tóc tự nhiên level 5.', lengths='Thân tóc zin level 5, đều màu.', ends='Ngọn khỏe.', scalp='Da đầu khỏe.'),
       dict(finish='volume', fit=['rt_colorsafe'], sessions=1, must_ask=['history'], must_inspect=['roots'], budget=120),
       case='photo', min_day=2),
    _c('s_react', 7, 'Thử dị ứng từ năm ngoái', 'Chị nhuộm nâu cho sáng mặt, năm ngoái thử dị ứng rồi nên làm luôn nha em.',
       'Nhuộm nâu tự nhiên level 5, sấy suôn.', ['color', 'style'],
       dict(level=5, tone='Nâu tự nhiên', style='Ngang vai, suôn', band='natural'), 'Da chị hơi nhạy, xài mỹ phẩm lạ hay ngứa.',
       dict(level=4, shown=4, length=32, history='virgin', patch=False, damage=0, scalp='ok'),
       dict(history='Chị chưa nhuộm lần nào.', lifestyle='Sáng chị chải thẳng là đi làm.', length='Không cắt.',
            budget='Chị có 100 xu.', patch='Năm ngoái chị chấm thử ở tiệm khác, giấy tờ đâu mất rồi, chắc vẫn còn tính ha?'),
       dict(roots='Chân tóc level 4, không bạc.', lengths='Thân tóc zin, sợi mảnh.', ends='Ngọn khỏe.',
            scalp='Da đầu hơi hồng, dễ đỏ khi gãi — da nhạy cảm.'),
       dict(color=_col(5, 'natural', 20), finish='sleek', fit=[], sessions=1, must_ask=['patch'], must_inspect=['scalp'], budget=100),
       case='react', min_day=2),
    _c('s_kid', 8, 'Bé Bin ngồi không yên', 'Bé Bin 5 tuổi, ngồi đâu được đó hai phút là tuột xuống. Tiệm cắt gọn giùm, mái chừa qua lông mày nha.',
       'Cắt ngắn gọn 2–3 cm, mái ngang lông mày.', ['cut'], dict(level=None, tone='', style='Tóc ngắn gọn, mái ngang mày'),
       'Bé mà giãy là lẹm liền đó, cẩn thận giùm nha.',
       dict(level=2, shown=2, length=14, history='virgin', patch=True, damage=0, scalp='ok'),
       dict(history='Tóc bé chưa làm gì, ở nhà bố tự cắt bằng tông đơ.', lifestyle='(bố kể thói quen của bé)',
            length='Bớt chừng 2–3 phân thôi, ngắn quá bé bị bạn trêu.', budget='Năm chục xu nha.', patch='Bé không nhuộm đâu.'),
       dict(roots='Tóc bé mềm, đen tự nhiên.', lengths='Sợi mảnh, xoáy ở đỉnh.', ends='Ngọn khỏe.', scalp='Da đầu bé nhạy, dùng dầu gội dịu nhẹ.'),
       dict(cut=dict(min=2, max=3, layers=False), finish=None, fit=[], sessions=1, must_ask=['length', 'lifestyle'], must_inspect=[],
            budget=50), case='kid', min_day=2, mods=('school',)),
    _c('s_bride', 9, 'Tóc cô dâu trước giờ rước', 'Ba giờ chiều nhà trai tới rước, em cần búi tóc cô dâu thật chắc, kịp giờ nha!',
       'Hấp phục hồi cho tóc bóng, búi cô dâu gọn chắc.', ['treatment', 'style'],
       dict(level=None, tone='', style='Búi thấp, cài hoa baby'), 'Tuần trước em lỡ duỗi tóc, sợ tóc yếu không giữ nếp.',
       dict(level=3, shown=3, length=45, history='relaxed', patch=True, damage=2, scalp='ok'),
       dict(history='Tuần trước em duỗi thẳng ở tiệm gần nhà.', lifestyle='Ngày thường em buộc gọn, hôm nay phải thật lung linh.',
            length='Không cắt ạ, em nuôi dài để búi.', budget='Nhà em gửi 90 xu.', patch='Em không nhuộm đâu ạ.'),
       dict(roots='Chân tóc đen khỏe.', lengths='Thân tóc vừa duỗi, khô và trơn — khó giữ nếp nếu không phục hồi trước.',
            ends='Ngọn khô.', scalp='Da đầu khỏe.'),
       dict(finish='updo', fit=['rt_heat'], sessions=1, must_ask=['history'], must_inspect=['lengths'], budget=90),
       case='bride', min_day=2, mods=('wedding',), more=dict(rush=(16, 20))),
    _c('s_walkin', 14, 'Cắt nhanh giữa hai cuốc xe', 'Cắt nhanh giùm anh, mười một giờ còn đơn phải giao!',
       'Cắt ngắn gọn hai bên, sấy tự nhiên.', ['cut', 'style'], dict(level=None, tone='', style='Ngắn gọn, hai bên cao'),
       'Anh đội mũ bảo hiểm cả ngày, đừng vuốt keo.',
       dict(level=2, shown=2, length=9, history='virgin', patch=True, damage=0, scalp='ok'),
       dict(history='Chưa làm gì hết.', lifestyle='Anh đội mũ bảo hiểm cả ngày, tóc để tự nhiên.', length='Bớt ba bốn phân cho mát.',
            budget='Sáu chục xu.', patch='Anh đâu có nhuộm.'),
       dict(roots='Tóc đen dày.', lengths='Sợi cứng, bết mồ hôi vì đội mũ.', ends='Ngọn khỏe.', scalp='Da đầu hơi dầu, không trầy.'),
       dict(cut=dict(min=3, max=4, layers=False), finish='natural', fit=[], sessions=1, must_ask=['length'], must_inspect=[], budget=60),
       case='walkin', min_day=2, mods=('walkin',), more=dict(rush=(11, 8))),
    _c('s_grey', 10, 'Phủ bạc nhiều cho trẻ ra', 'Tóc chú bạc hơn nửa đầu rồi, nhuộm cho trẻ ra mà đừng đen kịt như đội mũ nha.',
       'Nhuộm phủ bạc nâu ấm level 5, tỉa gọn.', ['color', 'cut'], dict(level=5, tone='Nâu ấm tự nhiên', style='Ngắn gọn', band='warm'),
       'Lần trước nhuộm chỗ khác, ba tuần là lộ bạc lại.',
       dict(level=5, shown=5, length=9, history='virgin', patch=True, damage=0, scalp='ok', grey=60),
       dict(history='Nhuộm một lần hồi Tết ở tiệm khác, giờ phai hết rồi.', lifestyle='Chú gội xong để khô.',
            length='Tỉa gọn một hai phân thôi.', budget='Chú có 120 xu.', patch='Tháng trước tiệm thử cho chú rồi, không sao.'),
       dict(roots='Chân tóc level 5, bạc khoảng 60% — sợi bạc cứng, khó ăn màu.', lengths='Thân tóc phai, còn ánh nâu cũ nhạt.',
            ends='Ngọn khỏe.', scalp='Da đầu khỏe.'),
       dict(color=_col(5, 'warm', 20, grey=True), cut=dict(min=1, max=2, layers=False), finish=None, fit=['rt_colorsafe'],
            sessions=1, must_ask=['history'], must_inspect=['roots'], budget=120), case='grey', min_day=3),
    _c('s_fix', 12, 'Cứu tóc tự nhuộm bị cam', 'Chị tự nhuộm ở nhà, ra cái màu cam đồng như cái nồi. Cứu chị với, về nâu tự nhiên thôi!',
       'Nhuộm về nâu tự nhiên level 6 (hết cam), hấp phục hồi.', ['color', 'treatment'],
       dict(level=6, tone='Nâu tự nhiên, hết ánh cam', style='Giữ nguyên độ dài', band='natural'), 'Đừng ra đen quá, chị sợ già.',
       dict(level=6, shown=7, length=30, history='box_dye', patch=True, damage=2, scalp='ok', warm=1),
       dict(history='Chị mua thuốc nhuộm hộp “nâu hạt dẻ” tự nhuộm tuần trước, lên cam rực.', lifestyle='Chị buộc tóc đứng bán hàng cả ngày.',
            length='Không cắt.', budget='Chị có 130 xu.', patch='Có, tiệm thử cho chị hồi đầu tháng.'),
       dict(roots='Chân tóc tự nhiên level 6.',
            lengths='Thân tóc tự nhuộm lên level 7 ánh cam đồng rực — nền này làm mọi màu mới ấm thêm một bậc.',
            ends='Ngọn khô, hơi xơ vì thuốc hộp.', scalp='Da đầu khỏe.'),
       dict(color=_col(6, 'natural', 10), finish=None, fit=['rt_mask'], sessions=1, must_ask=['history'], must_inspect=['lengths'],
            budget=130), case='fix', min_day=3),
]
JOB2_INDEX = {j['key']: j for j in JOBS2}
_t2 = [(j['npc'], j['title']) for j in JOBS2]
assert len(set(j['key'] for j in JOBS2)) == len(JOBS2) and len(set(_t2)) == len(_t2), 'salon jobs must be unique'


def today(day: int) -> dict:
    return kit.daily(ID, day, TODAY)


def _today(c: dict) -> dict:
    t = kit.data(c).get('today')
    if isinstance(t, dict) and t.get('day') == c['day'] and t.get('id') in TODAY_INDEX:
        return TODAY_INDEX[t['id']]
    return today(c['day'])


def _order(pool: list, day: int, tag: str, mod: str) -> list:
    r = kit.rng(ID, 'order', tag, day)
    keyed = []
    for j in pool:
        w = j['weight'] * (3 if mod in j['mods'] else 1)
        keyed.append((r.random() ** (1.0 / w), j['key']))
    keyed.sort(reverse=True)
    return [JOB2_INDEX[k] for _, k in keyed]


PLAN_SLOTS = 12   # a day's first slots are planned together (later extra slots fall back to the plain walk)
SEEN_SLOTS = 4    # the first slots of the last two days count as "recently seen"
_PLAN: dict = {}


def _pools(day: int):
    mod = today(day)['id']
    classic = _order([j for j in JOBS2 if not j['case'] and j['min_day'] <= day], day, 'c', mod)
    special = _order([j for j in JOBS2 if j['case'] and j['min_day'] <= day], day, 's', mod)
    return classic, special, SPECIAL_P[kit.tier(day)] + (0.1 if mod in ('wedding', 'walkin', 'school') else 0)


def _is_special(day: int, k: int, special: list, p: float) -> bool:
    # The first client of the day is always an everyday one.
    return bool(special) and k > 0 and kit.rng(ID, 'kind', day, k).random() < p


def _plan_build(day: int, recent: set) -> list:
    """The day's clients in slot order: no template or client twice in a day, nobody from the last two mornings when avoidable."""
    classic, special, p = _pools(day)
    out, keys, npcs, kinds = [], set(), set(), set()
    rules = (
        lambda j: j['key'] not in keys and j['npc'] not in npcs and j['key'] not in recent,
        lambda j: j['key'] not in keys and j['npc'] not in npcs,
        lambda j: j['key'] not in keys,
        lambda j: True)
    for k in range(PLAN_SLOTS):
        pool = special if _is_special(day, k, special, p) else classic
        pick = next(j for ok in rules for j in pool if ok(j))
        out.append(pick)
        keys.add(pick['key']); npcs.add(pick['npc'])
    return out


def _plan(day: int) -> list:
    if day not in _PLAN:
        # Days are planned in order (each one looks back two days); the cache always holds days 1..N.
        start = max((d for d in _PLAN if d < day), default=0)
        for d in range(max(1, start + 1), day + 1):
            recent = {j['key'] for back in (1, 2) for j in _PLAN.get(d - back, [])[:SEEN_SLOTS]}
            _PLAN[d] = _plan_build(d, recent)
    return _PLAN[day]


def _walk_v2(day: int, slot: int) -> dict:
    classic, special, p = _pools(day)
    ci = si = 0
    for k in range(slot + 1):
        is_special = _is_special(day, k, special, p)
        if k == slot:
            return special[si % len(special)] if is_special else classic[ci % len(classic)]
        if is_special:
            si += 1
        else:
            ci += 1
    raise AssertionError


def _pick_v2(day: int, slot: int) -> dict:
    return _plan(day)[slot] if 1 <= day and slot < PLAN_SLOTS else _walk_v2(day, slot)


def _make_v2(day: int, slot: int, serial: int) -> dict:
    j = _pick_v2(day, slot)
    r = kit.rng(ID, 'facts', day, slot)
    tier = kit.tier(day)
    hair = dict(copy.deepcopy(j['hair']), say=dict(j['say']), find=dict(j['find']),
                strand=j['strand'] or 'Lọn thử lên đều, sợi khỏe — tóc chịu được tẩy nhẹ.')
    hair.setdefault('grey', 0)
    hair.setdefault('warm', 0)
    key = dict(copy.deepcopy(KEY_DEFAULTS), **copy.deepcopy(j['k']))
    needs = dict(want=j['want'], services=list(j['services']), photo=dict(j['photo']), note=j['note'], case=j['case'])
    case, x, calm = j['case'], {}, None
    if case == 'photo':
        real = PHOTO_REAL[r.randrange(len(PHOTO_REAL))]
        key['color'] = _col(real['level'], real['tone'], 20)
        x = dict(real=dict(real))
    elif case == 'react':
        x = dict(react=r.random() < (0.6, 0.65, 0.7, 0.75)[tier])
    elif case == 'kid':
        best = CALM_IDS[r.randrange(len(CALM_IDS))]
        hair['say']['lifestyle'] = CALM_HINT[best]
        x = dict(soothe=best)
        calm = 55 - 5 * tier
    if 'rush' in j['more']:
        steps, bonus = j['more']['rush']
        needs['rush'] = dict(steps=max(8, steps - 2 * max(0, tier - 1)), bonus=bonus)
    return kit.base_task(ID, day, slot, serial, j['npc'], j['title'], j['opening'], needs=needs, _hair=hair, _key=key, _x=x, gen=GEN,
                         asked=[], patch_record=None, plan=None, quote=None, patch_fee=0, bowl=None, timer=None, results={},
                         cut=_empty_cut(), washed=False, patch_done=False, strand=False, treated=False, styled=None,
                         done=[], flags=[], sold=[], declined=[], cost=0, photo_seen=False, calm=calm, soothed=[], reacted=False)


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        return _make_v1(day, slot, serial)
    return _make_v2(day, slot, serial)


# ------------------------------------------------------------------ mixing maths (the client mirrors it for the preview)
def _band(tn: int, den: int) -> str:
    """Tone band of a mix whose tone total is tn (tone×20 per part) over den parts."""
    if tn <= -12 * den:
        return 'ash'
    if tn <= -3 * den:
        return 'cool'
    if tn < 3 * den:
        return 'natural'
    if tn < 18 * den:
        return 'warm'
    return 'deep'


def _blend(rows) -> str:
    tot = sum(p for _, p in rows)
    rgb = [sum(int(col[1 + 2 * i:3 + 2 * i], 16) * p for col, p in rows) / tot for i in range(3)]
    return '#' + ''.join(f'{int(v + 0.5):02x}' for v in rgb)


def _mix(shade: str, shade2: str | None = None, pa: int = 1, pb: int = 0, warm: int = 0) -> dict:
    rows = [(DYE_INDEX[shade], pa)] + ([(DYE_INDEX[shade2], pb)] if shade2 and pb else [])
    den = sum(p for _, p in rows)
    lv = sum(d['level'] * p for d, p in rows)
    tn = sum(TONE[d['fam']] * 20 * p for d, p in rows) + warm * 20 * den
    nat = sum(p for d, p in rows if d['fam'] == 'N')
    return dict(den=den, lv=lv, tn=tn, nat=nat, band=_band(tn, den), color=_blend([(d['color'], p) for d, p in rows]))


def _level_ok(m: dict, level: int) -> bool:
    return abs(m['lv'] - level * m['den']) * 4 <= m['den']


def _level_text(m: dict) -> str:
    return f'{m["lv"] / m["den"]:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


def _bowl_mix(t: dict, b: dict) -> dict | None:
    mx = b.get('mix')
    if not mx:
        return None
    return _mix(b['shade'], mx['b'], mx['pa'], mx['pb'], t['_hair'].get('warm', 0))


# Tones a developer lifts natural hair by (RULES 1–3; 40 vol is never used on the scalp).
LIFT = {10: 0, 20: 2, 30: 3, 40: 4}
# What each bowl kind is mixed with, by the rule table (every recipe in the game follows it).
KIND_RATIO = {'color': '1:1', 'bleach': '1:2', 'toner': '1:2'}


def _dev_note(dev, need, tones) -> str | None:
    """Why the developer is right or wrong for this target: ok, dev40, weak (lifts too few tones), cover (grey needs it),
    low (too weak, reason unknown), strong — or None while the developer or the one needed is not known."""
    if need is None or dev is None:
        return None
    if dev == need:
        return 'ok'
    if dev == 40:
        return 'dev40'
    if dev < need:
        if tones is None:
            return 'low'
        return 'weak' if tones > LIFT[dev] else 'cover'
    return 'strong'


def bowl_check(kind: str, shade, mix: dict | None, dev, ratio, want: dict | None, warm: int = 0,
               photo_blind: bool = False, lift: dict | None = None) -> dict:
    """The verdict on a bowl, before anything is mixed. Pure (no task, no randomness), so the client runs the very
    same rules for its preview: public/js/careers/salon_mix.js bowlCheck() is a line-for-line port and
    tests/test_salon_mix_parity.py runs every combination through both.

    mix: {b, pa, pb} for a v0.5 two-tube colour bowl (shade is tube A), None for a single tube, bleach or toner.
    want: what the client needs — {level, tone, dev, ratio, grey} for a two-tube bowl, {shade, dev, ratio} otherwise
    (the server passes the task key; the preview passes what the stylist has found out, dev/shade None if unknown).
    warm: the brassy base (+1 band); photo_blind: a filtered photo not yet checked; lift: {base, dyed} for the notes.
    issue is the first thing Linh says, in her order (None: the bowl is right)."""
    out = dict(issue=None, hit=None, mix=None, text=None, level_ok=None, band_ok=None, nat_ok=None, dlv=None, dband=None,
               dev_note=None, need=None, cap=LIFT.get(dev), tones=None, block=False)
    if mix is not None:
        m = _mix(shade, mix['b'], mix['pa'], mix['pb'], warm)
        out.update(mix=m, text=_level_text(m))
        if lift and lift.get('dyed') is not None:
            # Dye never lifts old dye: anything lighter than the dyed lengths needs bleach.
            out['block'] = (m['lv'] - lift['dyed'] * m['den']) * 4 > m['den']
        if not want:
            out.update(issue='nowant', hit=False)
            return out
        lv_ok, bd_ok = _level_ok(m, want['level']), m['band'] == want['tone']
        nat_ok = not want.get('grey') or 2 * m['nat'] >= m['den']
        hit = lv_ok and bd_ok
        need = want.get('dev')
        tones = want['level'] - lift['base'] if lift and lift.get('base') is not None else None
        out.update(hit=hit, level_ok=lv_ok, band_ok=bd_ok, nat_ok=nat_ok, dlv=m['lv'] - want['level'] * m['den'],
                   dband=BAND_IDS.index(m['band']) - BAND_IDS.index(want['tone']), need=need, tones=tones,
                   dev_note=None if photo_blind else _dev_note(dev, need, tones))
        if dev == 40:
            out['issue'] = 'dev40'
        elif not hit:
            out['issue'] = 'photo' if photo_blind else 'level' if not lv_ok else 'tone'
        elif not nat_ok:
            out['issue'] = 'grey'
        elif need is not None and dev != need:
            out['issue'] = 'dev'
        elif ratio != want['ratio']:
            out['issue'] = 'ratio'
        return out
    if not want:
        out['issue'] = 'nowant'
        return out
    need = want.get('dev')
    out.update(need=need, dev_note=_dev_note(dev, need, None))
    if dev == 40:
        out['issue'] = 'dev40'
    elif kind != 'bleach' and want.get('shade') is not None and shade != want['shade']:
        out['issue'] = 'shade'
    elif need is not None and dev != need:
        out['issue'] = 'dev'
    elif ratio != want['ratio']:
        out['issue'] = 'ratio'
    return out


def _mix_issue(t: dict, shade: str, mx: dict, dev: int, ratio: str) -> tuple:
    want = t['_key'].get('color')
    v = bowl_check('color', shade, mx, dev, ratio, want, t['_hair'].get('warm', 0),
                   t['needs'].get('case') == 'photo' and not t.get('photo_seen'))
    issue, hit, m = v['issue'], v['hit'], v['mix']
    if issue == 'nowant':
        return 'Linh (thợ màu) lắc đầu: phiếu của khách không cần bát này.', False
    if issue == 'dev40':
        return 'Linh giật mình: oxy 40 vol không bao giờ được thoa sát da đầu!', hit
    if issue == 'photo':
        return 'Linh nhìn ảnh rồi nhìn tóc khách: “Ảnh này qua filter đó, soi ảnh gốc rồi hãy pha.”', hit
    if issue == 'level':
        return f'Linh ước độ sáng bát: khoảng level {_level_text(m)} — khách cần level {want["level"]}.', hit
    if issue == 'tone':
        msg = f'Linh soi ánh: trên tóc này bát ra “{BAND_NAME[m["band"]]}”, khách cần “{BAND_NAME[want["tone"]]}”.'
        if t['_hair'].get('warm') and 'lengths' not in t['inspected']:
            msg += ' Nền tóc đang ánh cam cũng đẩy màu ấm lên — xem kỹ thân tóc.'
        return msg, hit
    if issue == 'grey':
        return 'Linh nhắc: tóc bạc nhiều, ít nhất một nửa bát phải là tuýp nền tự nhiên (x.0) — không thì bạc vẫn lộ.', hit
    if issue == 'dev':
        return 'Linh nhắc: đếm số tông cần nâng từ chân tóc thật rồi tra bảng oxy.', hit
    if issue == 'ratio':
        return 'Linh nhắc: tỷ lệ trộn của loại thuốc này chưa đúng bảng pha.', hit
    return None, hit


def _recipe_view(t: dict) -> dict:
    """The half of bowl_check's `want` the stylist has found out (public view, v0.5 tasks): ratios and the bleach and
    toner developers come from the rule table; the colour's developer once the roots are seen (count the lift from
    the real roots); the dyed lengths once seen; the toner once the bleach is rinsed (the base shows its tint)."""
    k, h, seen, out = t['_key'], t['_hair'], t['inspected'], {}
    if k.get('color'):
        w, roots = k['color'], 'roots' in seen
        out['color'] = dict(dev=w['dev'] if roots else None, ratio=w['ratio'], base=h['level'] if roots else None,
                            dyed=h['shown'] if h['history'] == 'box_dye' and 'lengths' in seen else None)
    if k.get('bleach'):
        out['bleach'] = dict(dev=k['bleach']['dev'], ratio=k['bleach']['ratio'])
    if k.get('toner'):
        w = k['toner']
        out['toner'] = dict(dev=w['dev'], ratio=w['ratio'],
                            shade=w['shade'] if 'bleach' in t['results'] or not k.get('bleach') else None)
    return out


def _empty_cut() -> dict:
    return dict(steps=[], removed=0, short=False, done=False)


DATA_V2 = dict(today=None, allergy={}, mixes=0, rush_on_time=0, kids_calm=0, day_served=0)

# ------------------------------------------------------------------ care loop: client cards, hair health, bookings, clean tool sets
# (docs/superpowers/specs/2026-09-29-salon-care-design.md) — all game rules, nothing random.
TRUST_MAX = 5
TRUST_NAMES = ('Khách mới', 'Quen mặt', 'Khách quen', 'Thân thiết', 'Khách ruột', 'Như người nhà')
TRUST_PATIENCE = 3                      # a regular arrives this much more patient per trust level
HEALTH_RECOVER, HEALTH_NATURAL_CAP = 3, 85
WEAK, BLEACH_STOP, CARE_BELOW = 50, 30, 60
HEALTH_HIT = {'bleach': dict(under=-12, ideal=-20, over=-28, damage=-40),
              'color': dict(under=-4, ideal=-6, over=-10, damage=-25),
              'toner': dict(under=-2, ideal=-2, over=-2, damage=-8)}
HEALTH_TREAT = 25
HEALTH_RETAIL = {'rt_mask': 5, 'rt_heat': 3}
HEALTH_WORDS = ((85, 'Khỏe'), (70, 'Khá'), (50, 'Hơi yếu'), (30, 'Yếu'), (0, 'Rất yếu'))
HIST = {'virgin': 'Tóc zin · độ xốp thấp, ăn màu chậm mà đều',
        'box_dye': 'Từng nhuộm hộp · độ xốp không đều, dễ loang',
        'bleached': 'Đã tẩy · độ xốp cao, hút thuốc rất nhanh',
        'relaxed': 'Đã duỗi · xốp vừa, dễ khô'}
APPTS = {
    'roots': dict(days=4, label='Dặm chân tóc', emoji='🎨', price=35, why='Chân tóc mọc khoảng 4 tuần (4 ngày trong game)'),
    'trim': dict(days=5, label='Tỉa giữ dáng', emoji='✂️', price=20, why='Giữ dáng tóc vừa cắt'),
    'care': dict(days=2, label='Hấp phục hồi', emoji='💧', price=None, why='Tóc còn yếu sau lần làm này'),
}
APPT_KINDS = tuple(APPTS)
APPT_KEEP, APPT_MAX = 2, 40
APPT_STATES = ('open', 'done', 'merged', 'lapsed', 'void')
ROOT_HIT = -3                           # a root touch-up only touches the regrowth
TRIM_CAP = (2, 1)                       # cm a keep-the-shape trim may take (after a too-short cut: 1)
CLEAN_SETS = 4
CARD_KEYS = ('visits', 'first', 'last', 'trust', 'health', 'hist', 'formula', 'cut', 'services', 'stars', 'patch_file')
FORMULA_KEYS = ('shade', 'b', 'pa', 'pb', 'dev', 'ratio', 'level', 'band', 'hit', 'zone', 'day')
DATA_CARE = dict(cards={}, appts=[], appt_seq=0, appts_done=0)


def initial() -> dict:
    d = dict(served=0, dumped=0, sanitize_day=0, patch_log={})
    d.update(copy.deepcopy(DATA_V2))
    d.update(copy.deepcopy(DATA_CARE))
    d['clean'] = 0
    d['desk'] = kit.desk_initial()
    return d


def _data(c: dict) -> dict:
    """Plugin data with the v0.5 fields and the care loop (old saves get them here)."""
    d = kit.data(c)
    for k, v in DATA_V2.items():
        d.setdefault(k, copy.deepcopy(v))
    for k, v in DATA_CARE.items():
        d.setdefault(k, copy.deepcopy(v))
    if 'clean' not in d:
        # A save from before the tool sets: tools sterilised today count as a full jar.
        d['clean'] = CLEAN_SETS if d.get('sanitize_day') == c.get('day') else 0
    d.setdefault('desk', kit.desk_initial())
    return d


# ---- hair health
def _health_word(h: int) -> str:
    return next(w for lim, w in HEALTH_WORDS if h >= lim)


def _hp(t: dict) -> int:
    """Hair health of this visit: set on arrival (v0.5 tasks), else from the template damage."""
    h = t.get('health')
    return h if type(h) is int else max(10, 100 - 20 * t['_hair'].get('damage', 0))


def _arrival_health(c: dict, t: dict) -> int:
    card = _data(c)['cards'].get(t['npc'])
    if not card:
        return max(10, 100 - 20 * t['_hair'].get('damage', 0))
    h = card['health']
    if h < HEALTH_NATURAL_CAP:     # new growth and home care; only a treatment lifts hair above the cap
        h = min(HEALTH_NATURAL_CAP, h + HEALTH_RECOVER * max(0, c['day'] - card['last']))
    return h


def _health_after(t: dict, sold=()) -> int:
    h = _hp(t)
    for kind, r in t['results'].items():
        h += HEALTH_HIT[kind][r['zone']]
    if 'treatment' in t['done']:
        h += HEALTH_TREAT
    h += sum(HEALTH_RETAIL.get(x, 0) for x in sold)
    return max(10, min(100, h))


def _weak(t: dict) -> bool:
    return bool(t.get('gen')) and _hp(t) < WEAK


def _health_known(t: dict) -> bool:
    return t.get('regular') is not None or bool({'lengths', 'ends'} & set(t['inspected']))


# ---- clean tool sets
def _take_set(c: dict) -> bool:
    d = _data(c)
    if d['clean'] > 0:
        d['clean'] -= 1
        return True
    return False


def _use_tools(c: dict, t: dict) -> str:
    """The client's first hands-on step takes a sterilised set from the jar (or a used one when the jar is empty)."""
    if not t.get('gen') or t.get('tools'):
        return ''
    if _take_set(c):
        t['tools'] = 'clean'
        return f' 🧼 Lấy bộ lược kéo đã khử khuẩn (còn {_data(c)["clean"]}/{CLEAN_SETS}).'
    t['tools'] = 'dirty'
    return ' ⚠️ Hết bộ lược kéo đã khử khuẩn — đành dùng bộ vừa dùng. Khử khuẩn trước khách sau nhé.'


# ---- formulas on the card
def _parts(shade: str, b, pa: int, pb: int) -> dict:
    rows = {shade: pa}
    if b and pb:
        rows[b] = rows.get(b, 0) + pb
    g = 0
    for v in rows.values():
        a, g2 = v, g
        while g2:
            a, g2 = g2, a % g2
        g = a
    return {k: v // g for k, v in rows.items()}


def _same_formula(f: dict, shade: str, b, pa: int, pb: int, dev: int, ratio: str) -> bool:
    return _parts(f['shade'], f['b'], f['pa'], f['pb']) == _parts(shade, b, pa, pb) and f['dev'] == dev and f['ratio'] == ratio


def _formula_text(f: dict) -> str:
    a = DYE_INDEX[f['shade']]['code']
    tubes = f'{f["pa"]} phần {a} + {f["pb"]} phần {DYE_INDEX[f["b"]]["code"]}' if f['b'] else f'{a}'
    return f'{tubes} · oxy {f["dev"]} vol · {f["ratio"]}'


def _card_formula(c: dict, t: dict):
    """The formula on this regular's card when it worked and today's colour target is the same one."""
    card = kit.data(c).get('cards', {}).get(t['npc'])
    f = card and card.get('formula')
    want = t['_key'].get('color') if t.get('gen') else None
    if not (f and f['hit'] and want and 'level' in want):
        return None
    return f if (f['level'], f['band']) == (want['level'], want['tone']) else None


def _case(t: dict) -> str | None:
    return (t.get('needs') or {}).get('case') if t.get('gen') else None


def _allergic(c: dict, t: dict) -> bool:
    return t['npc'] in kit.data(c).get('allergy', {})


def _rush_left(c: dict, t: dict) -> int | None:
    rush = t['needs'].get('rush') if t.get('gen') else None
    if not rush:
        return None
    return t['created_turn'] + rush['steps'] - c['turn']


def _who(t: dict) -> str:
    return PEOPLE[int(t['npc'].rsplit('_', 1)[1]) - 1][0]


def _names(ids) -> str:
    return ', '.join(SERVICE_INDEX[x]['name'].lower() for x in ids)


def _has_record(c: dict, t: dict) -> bool:
    """A patch-test result on file: the client's card, or a salon test from an earlier day.
    A reaction written in the salon's allergy book overrides both."""
    if _allergic(c, t):
        return False
    day = kit.data(c)['patch_log'].get(t['npc'])
    return bool(t['_hair']['patch']) or (day is not None and day < c['day'])


def _dye_requested(t: dict) -> bool:
    return any(x in DYE_SERVICES for x in t['needs']['services'])


def _too_weak_to_bleach(t: dict) -> bool:
    return bool(t.get('gen')) and 'bleach' in t['needs']['services'] and _hp(t) < BLEACH_STOP


def _may_postpone(c: dict, t: dict, service: str) -> bool:
    return (service in t['_key']['postpone'] or (service in DYE_SERVICES and not _has_record(c, t))
            or (service in ('bleach', 'toner') and _too_weak_to_bleach(t)))


def _quote(c: dict, services) -> int:
    return sum(kit.price(c, x, PRICES[x]) for x in services)


def _window(kind: str, fragile: bool, fast: bool = False) -> dict:
    w = WINDOWS['bleach_fragile' if kind == 'bleach' and fragile else kind]
    if fast:   # a hot day: the chemistry runs about a fifth faster
        w = {k: max(2, int(v * 0.8 + 0.5)) for k, v in w.items()}
    return w


def _zone(seconds: float, w: dict) -> str:
    if seconds < w['under']:
        return 'under'
    if seconds <= w['ideal']:
        return 'ideal'
    if seconds <= w['over']:
        return 'over'
    return 'damage'


def _flag(t: dict, name: str) -> None:
    if name not in t['flags']:
        t['flags'].append(name)


def _work_started(t: dict) -> bool:
    """Re-planning stays possible until a planned service has actually begun."""
    return bool(t['done'] or t['bowl'] or t['timer'] or t['cut']['steps'])


def _drop(c: dict, t: dict, services) -> None:
    """Take services out of the agreed plan (safety stop) and re-quote the rest."""
    plan = t['plan']
    if not plan:
        return
    keep = [x for x in plan['services'] if x not in services]
    if keep:
        plan['services'] = keep
        t['quote'] = _quote(c, keep)
    else:
        t['plan'], t['quote'] = None, None


def _answer(t: dict, topic: str) -> str:
    h = t['_hair']
    if topic == 'patch' and t['patch_record'] == 'log':
        return 'Sổ thử dị ứng của tiệm ghi: đã chấm thử ở một ngày trước, không phản ứng.'
    if topic == 'patch' and t['patch_record'] == 'allergy':
        return 'Sổ dị ứng của tiệm ghi rõ: khách từng phản ứng với thuốc nhuộm — không nhuộm hóa chất cho khách này.'
    return h['say'][topic]


def _formula_issue(t: dict, kind: str, shade, dev: int, ratio: str) -> str | None:
    issue = bowl_check(kind, shade, None, dev, ratio, t['_key'].get(kind))['issue']
    if issue == 'nowant':
        return 'Linh (thợ màu) lắc đầu: phiếu của khách không cần bát này.'
    if issue == 'dev40':
        return 'Linh giật mình: oxy 40 vol không bao giờ được thoa sát da đầu!'
    if issue == 'shade':
        if kind == 'color':
            return 'Linh so tuýp với ảnh mẫu và chân tóc: tông, số tuýp này chưa đúng màu khách muốn.'
        return 'Linh soi màu nền sau tẩy: toner này không khử đúng ánh đang có.'
    if issue == 'dev':
        return 'Linh nhắc: đếm số tông cần nâng rồi tra bảng oxy.'
    if issue == 'ratio':
        return 'Linh nhắc: tỷ lệ trộn của loại thuốc này chưa đúng bảng pha.'
    return None


def _look(t: dict) -> dict:
    """What the mirror shows: visible colour level and current length."""
    h = t['_hair']
    color = LEVEL_COLOR[h['shown']]
    level = h['shown']
    col = t['results'].get('color')
    if col and col['zone'] != 'under':
        d = DYE_INDEX.get(col['shade'])
        if col.get('mix'):
            m = _bowl_mix(t, col)
            color, level = m['color'], max(1, min(10, int(m['lv'] / m['den'] + 0.5)))
        elif d:
            color, level = d['color'], d['level']
    if 'bleach' in t['results']:
        z = t['results']['bleach']['zone']
        level = {'under': 5, 'ideal': 7, 'over': 8, 'damage': 8}[z]
        color = LEVEL_COLOR[level]
        tn = t['results'].get('toner')
        if tn and tn['zone'] in ('ideal', 'over') and tn['shade'] in TONER_INDEX:
            color = TONER_INDEX[tn['shade']]['color']
    return dict(color=color, level=level, length=max(1, h['length'] - t['cut']['removed']))


# ------------------------------------------------------------------ what the client sees in the mirror (recorded at checkout)
BAND_POS = {b: i for i, b in enumerate(BAND_IDS)}
SHIFT = {
    ('warm', 'light'): 'ấm và sáng hơn', ('warm', 'dark'): 'ấm và tối hơn', ('warm', ''): 'ấm hơn',
    ('cool', 'light'): 'lạnh và sáng hơn', ('cool', 'dark'): 'lạnh và tối hơn', ('cool', ''): 'lạnh hơn',
    ('', 'light'): 'sáng hơn', ('', 'dark'): 'tối hơn', ('', ''): 'lệch tông',
}
ZONE_SLIP = {
    ('color', 'under'): (2, 'Màu lên nhạt, chân tóc loang lổ vì ủ chưa đủ giờ.', 'màu loang vì ủ thiếu giờ'),
    ('color', 'over'): (1, 'Màu ra tối và đục hơn mong muốn một chút.', 'màu hơi tối, đục'),
    ('color', 'damage'): (3, 'Ủ thuốc quá lâu, tóc nóng rát, chải tới đâu gãy tới đó.', 'ủ quá lâu, tóc gãy'),
    ('bleach', 'under'): (2, 'Tẩy chưa tới, tóc lên cam đậm chứ không sáng như đã hẹn.', 'tẩy chưa tới, tóc cam đậm'),
    ('bleach', 'over'): (1, 'Tóc sáng rồi mà sờ vào thấy xơ hơn hẳn.', 'tẩy hơi quá, tóc xơ'),
    ('bleach', 'damage'): (3, 'Tẩy quá giờ, tóc cháy xém, gãy từng mảng.', 'tẩy quá giờ, tóc cháy gãy'),
    ('toner', 'under'): (1, 'Toner chưa ăn, tóc vẫn còn ánh cam.', 'toner chưa đủ, còn ánh cam'),
    ('toner', 'over'): (1, 'Toner để hơi lâu, tóc ngả xám tím.', 'toner hơi quá, ngả xám tím'),
    ('toner', 'damage'): (2, 'Toner để quá lâu, tóc tím xỉn hẳn.', 'toner quá lâu, tóc tím xỉn'),
}


def _shade(t: dict, r: dict) -> tuple:
    """(level, tone band) a colour result or recipe gives on this client's hair."""
    if r.get('mix'):
        m = _bowl_mix(t, r)
        return m['lv'] / m['den'], m['band']
    d = DYE_INDEX[r['shade']]
    return d['level'], _band((TONE[d['fam']] + t['_hair'].get('warm', 0)) * 20, 1)


def _colour_slip(t: dict) -> None:
    col, want = t['results'].get('color'), t['_key'].get('color')
    if not col or not want:
        return
    wrong = (not col['hit']) if 'hit' in col else ('shade' in want and col['shade'] != want['shade'])
    if not wrong:
        return
    got_lv, got_band = _shade(t, col)
    want_lv, want_band = _shade(t, dict(shade=want['shade'])) if 'shade' in want else (want['level'], want['tone'])
    dl, db = abs(got_lv - want_lv), BAND_POS[got_band] - BAND_POS[want_band]
    tone = 'warm' if db > 0 else 'cool' if db < 0 else ''
    light = 'light' if got_lv - want_lv > 0.25 else 'dark' if want_lv - got_lv > 0.25 else ''
    shift = SHIFT[(tone, light)]
    name = (t['needs']['photo'].get('tone') or BAND_NAME[want_band]).lower()
    if dl >= 2 or abs(db) >= 3 or (dl >= 1 and abs(db) >= 2):
        cq.slip(t, 'colour', 3, f'Dặn màu {name} mà nhuộm ra màu khác hẳn, {shift} quá nhiều.', 'nhuộm ra màu khác hẳn ảnh mẫu')
    elif dl >= 1 or abs(db) >= 2:
        cq.slip(t, 'colour', 2, f'Dặn màu {name} mà màu ra {shift} hẳn, không giống ảnh mẫu.', 'màu khác ảnh mẫu')
    else:
        cq.slip(t, 'colour', 1, f'Màu ra {shift} một chút so với màu {name} đã dặn.', 'màu lệch ảnh mẫu một chút')


def _record_slips(c: dict, t: dict, products: list) -> None:
    """Checkout is the hand-off: compare what the mirror shows with what was agreed."""
    k, flags, plan = t['_key'], set(t['flags']), t['plan']
    if 'dye_no_patch' in flags:
        if 'allergy_hit' in flags:
            cq.slip(t, 'no_patch', 3, 'Chưa thử dị ứng mà nhuộm luôn, da đầu nổi mẩn đỏ rát cả đêm.', 'nhuộm khi chưa thử dị ứng, bị dị ứng', safety=True)
        else:
            cq.slip(t, 'no_patch', 3, 'Chưa thử dị ứng mà tiệm cứ nhuộm luôn, lỡ dị ứng thì ai chịu?', 'nhuộm khi chưa thử dị ứng', safety=True)
    _colour_slip(t)
    tn, want_tn = t['results'].get('toner'), k.get('toner')
    if tn and want_tn and tn['shade'] != want_tn['shade'] and tn['zone'] != 'under':
        cq.slip(t, 'toner', 2, f'Dặn ánh {TONER_INDEX[want_tn["shade"]]["tone"].lower()} mà toner ra ánh {TONER_INDEX[tn["shade"]]["tone"].lower()}, không giống ảnh.',
                'ánh toner khác mẫu')
    for kind in CHEM:
        r = t['results'].get(kind)
        if r and r['zone'] != 'ideal':
            sev, text, note = ZONE_SLIP[(kind, r['zone'])]
            cq.slip(t, f'{kind}_{r["zone"]}', sev, text, note)
    if 'grey_show' in flags:
        cq.slip(t, 'grey_show', 2, 'Nhuộm xong soi gương vẫn thấy tóc bạc lộ lấm tấm.', 'tóc bạc còn lộ')
    if t['cut']['short'] and k.get('cut'):
        mx, rm = k['cut']['max'], t['cut']['removed']
        over = rm - mx
        if over >= 4:
            cq.slip(t, 'cut_short', 3, f'Dặn bớt {mx} phân mà cắt mất tận {rm} phân, giờ nuôi lại mất cả năm.', 'cắt ngắn hơn thỏa thuận quá nhiều')
        elif over >= 2:
            cq.slip(t, 'cut_short', 2, f'Dặn bớt {mx} phân mà cắt mất {rm} phân, ngắn hẳn so với đã hẹn.', 'cắt ngắn hơn thỏa thuận')
        else:
            cq.slip(t, 'cut_short', 1, f'Dặn bớt {mx} phân mà cắt mất {rm} phân, hơi ngắn hơn ý.', 'cắt hơi ngắn hơn thỏa thuận')
    elif 'slip' in flags:
        cq.slip(t, 'kid_slip', 1, 'Bé giãy một cái là bị lẹm một mảng tóc.', 'bé bị lẹm tóc')
    if 'layers_wrong' in flags:
        cq.slip(t, 'layers', 2, 'Mẫu tóc bằng mà bị tỉa tầng lởm chởm, không giống ảnh.', 'tỉa tầng không đúng mẫu')
    if 'finish_wrong' in flags and t['styled'] and k.get('finish'):
        want, got = (FINISHES[FINISH_IDS.index(x)]['name'].lower() for x in (k['finish'], t['styled']))
        sev = 2 if k['finish'] in ('updo', 'volume') else 1
        cq.slip(t, 'finish', sev, f'Cần {want} mà lại làm kiểu {got}, không hợp dịp của mình.', 'kiểu sấy không đúng dịp')
    if plan and plan['overpromise']:
        cq.slip(t, 'overpromise', 2, 'Hứa làm giống ảnh ngay trong một buổi, về soi gương chẳng giống chút nào.', 'hứa giống ảnh mà không làm được')
    if 'pushy' in flags or any(pid not in k['fit'] for pid in products):
        cq.slip(t, 'pushy', 1, 'Cứ mời làm thêm, mua thêm những thứ tóc mình đâu cần.', 'mời thứ không cần')
    if _dye_requested(t) and not _has_record(c, t) and not t['patch_done'] and not _allergic(c, t) and 'dye_no_patch' not in flags:
        cq.slip(t, 'skip_patch', 1, 'Tới để nhuộm mà không được thử dị ứng, lần sau tới lại vẫn phải chờ.', 'không thử dị ứng để hẹn màu lần sau')


# ------------------------------------------------------------------ actions
CUT_LOG = 16          # validate_task's bound on cut['steps']


def _cut_log(cut: dict, step: str) -> None:
    """Write a step into the chair's log. A long log (many small "cắt thêm" rounds) folds its repeats first, so it
    stays within CUT_LOG and no step is ever refused for the log's length (feedback #67)."""
    steps = cut['steps']
    if len(steps) >= CUT_LOG - 1:
        seen = []
        for x in steps:
            if x != 'check' and x not in seen:
                seen.append(x)
        if steps[-1] == 'check':          # a standing request from the client stays the last word
            seen.append('check')
        steps[:] = seen
    steps.append(step)


def cut_ask(t: dict) -> str | None:
    """What the client asked for at the last mirror check, while it still stands: 'long' (cut a bit more) or
    'layers'. A turned-down check is logged as a 'check' step on a cut that is not done; any later step answers it."""
    cut = t['cut']
    if cut['done'] or not cut['steps'] or cut['steps'][-1] != 'check' or not t['_key'].get('cut'):
        return None
    k = t['_key']['cut']
    if cut['removed'] < k['min']:
        return 'long'
    return 'layers' if k['layers'] and 'layers' not in cut['steps'] else None


def _cut_step(t: dict, key: dict, who: str, step: str, p: dict) -> dict:
    """One step at the cutting chair (section → guide → layers → check). When the client looks in the mirror and
    says it is still too long, the guide line is cut again (also after layering: feedback #67) and checked again."""
    cut, k = t['cut'], key['cut']
    if step == 'section':
        kit.need(not cut['steps'], 'Đã chia vùng tóc rồi.')
        _cut_log(cut, 'section')
        return dict(message='Chia 4 vùng: đỉnh, hai bên, gáy; kẹp gọn từng vùng.')
    kit.need('section' in cut['steps'], 'Chia vùng tóc trước đã.')
    if step == 'guide':
        length = kit.integer(p.get('length'), 1, 10)
        again = 'guide' in cut['steps']
        slip = 0
        if _case(t) == 'kid':
            slip = 2 if t['calm'] < 20 else 1 if t['calm'] < 40 else 0
        cut['removed'] += length + slip
        _cut_log(cut, 'guide')
        lead = ''
        if slip:
            t['mistakes'] += 1
            _flag(t, 'slip')
            lead = f'Bé Bin quay phắt sang nhìn cửa — kéo trượt, lẹm thêm {slip} cm! '
        if cut['removed'] > k['max'] and not cut['short']:
            cut['short'] = True
            t['mistakes'] += 1
            _flag(t, 'cut_short')
            return dict(message=f'{lead}Xoẹt! Tổng đã bớt {cut["removed"]} cm — ngắn hơn thỏa thuận. Tóc cắt rồi không nối lại được…')
        if again:
            return dict(message=f'{lead}Dóng lại đường chuẩn, cắt thêm {length + slip} cm (tổng đã bớt {cut["removed"]} cm).')
        return dict(message=f'{lead}Cắt đường chuẩn ở gáy rồi dóng theo: bớt {length + slip} cm (tổng {cut["removed"]} cm).')
    kit.need('guide' in cut['steps'], 'Cắt đường chuẩn trước đã.')
    if step == 'layers':
        kit.need('layers' not in cut['steps'], 'Đã tỉa tầng rồi.')
        _cut_log(cut, 'layers')
        if not k['layers']:
            t['mistakes'] += 1
            _flag(t, 'layers_wrong')
            return dict(message=f'{who} nhíu mày nhìn gương: mẫu của mình là tóc bằng, đâu có tỉa tầng…')
        return dict(message='Nâng từng lớp 90°, tỉa tầng nhẹ — tóc bồng lên thấy rõ.')
    # A turned-down check is logged once, so the client's request survives a reload (cut_ask); the next step answers it.
    if cut['removed'] < k['min'] or (k['layers'] and 'layers' not in cut['steps']):
        if cut['steps'][-1] != 'check':
            _cut_log(cut, 'check')
        if cut['removed'] < k['min']:
            return dict(message=f'{who} soi gương: “Còn hơi dài so với mình dặn.” Cắt thêm chút rồi kiểm lại.')
        return dict(message=f'{who}: “Mẫu có tầng mà em?” Tỉa tầng rồi kiểm lại.')
    if cut['steps'][-1] != 'check':
        _cut_log(cut, 'check')
    cut['done'] = True
    t['done'].append('cut')
    return dict(message='Kiểm đối xứng bằng gương cầm tay: hai bên đều. ' + (f'{who} tiếc vì ngắn hơn dự định.' if cut['short'] else f'{who} gật gù hài lòng.'))


DESK_FREE = ('sl_rinse',)      # a processing timer never waits for the counter


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    desk = d['desk']
    if name == 'sl_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'), _desk_hook)
    if name not in DESK_FREE:
        kit.desk_block(desk, 'Có chuyện ở quầy lễ tân — quyết xong rồi làm tiếp nhé (thuốc đang ủ vẫn xả được).')
    result = _handle(s, c, name, p)
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, _today(c)['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]} — ra quầy quyết giúp nhé.'.strip()
        result['surprise'] = True
    return result


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = kit.data(c)
    if key == 'sanitize':
        if d['sanitize_day'] != c['day']:
            d['sanitize_day'] = c['day']
            kit.metric(c, 'salon_sanitized')
        d['clean'] = CLEAN_SETS
        return None
    if key == 'inspect':
        if d['sanitize_day'] == c['day']:
            c['xp'] += 10
            return 'Sổ đã ký khử khuẩn hôm nay — đoàn ký “đạt”, còn khen khăn thơm.'
        fine = min(15, c['money'])
        if fine:
            kit.money(s, c, -fine, 'Phạt vệ sinh: chưa khử khuẩn dụng cụ', None, 'event_cost')
        return f'Sổ vệ sinh hôm nay còn trống: phạt {fine} xu, dặn khử khuẩn trước khi nhận khách.'
    return None


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = kit.data(c)
    if name == 'sl_sanitize':
        kit.need(d['clean'] < CLEAN_SETS, f'Cả {CLEAN_SETS} bộ lược kéo trong hũ đều đã khử khuẩn — dùng hết rồi ngâm lại.')
        d['clean'] = CLEAN_SETS
        if d['sanitize_day'] != c['day']:
            d['sanitize_day'] = c['day']
            kit.metric(c, 'salon_sanitized')
            return dict(message=f'Thay dung dịch khử khuẩn đầu ngày, ngâm kéo, lược, tông đơ; giặt khăn, lau ghế gội. '
                                f'Sổ vệ sinh ký ngày {c["day"]} · {CLEAN_SETS}/{CLEAN_SETS} bộ sạch.')
        return dict(message=f'Ngâm lại các bộ vừa dùng: {CLEAN_SETS}/{CLEAN_SETS} bộ lược kéo sạch.')
    if name == 'sl_appt':
        return _appt(s, c, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Công việc không thuộc salon.')
    kit.need(t['known'], 'Mời khách ngồi ghế tư vấn và nghe mong muốn trước (bấm “Mời ngồi & nghe mong muốn”).')
    key, hair, n, who = t['_key'], t['_hair'], t['needs'], _who(t)
    plan = t['plan']

    if name == 'sl_consult':
        topic = kit.one_of(p.get('topic'), TOPIC_IDS, 'Câu hỏi tư vấn không có trong phiếu.')
        kit.need(topic not in t['asked'], 'Đã hỏi câu này rồi.')
        t['asked'].append(topic)
        if topic == 'patch':
            t['patch_record'] = ('allergy' if _allergic(c, t) else 'file' if hair['patch'] else 'log' if _has_record(c, t)
                                 else 'none')
        kit.metric(c, 'salon_questions')
        return dict(message=f'{who}: “{_answer(t, topic)}”')

    if name == 'sl_inspect':
        zone = kit.one_of(p.get('zone'), ZONE_IDS, 'Vùng tóc không hợp lệ.')
        kit.need(zone not in t['inspected'], 'Đã xem kỹ vùng này rồi.')
        t['inspected'].append(zone)
        msg = '🔎 ' + hair['find'][zone]
        if zone == 'roots' and hair.get('grey', 0) >= 50:
            msg += ' Luật phủ bạc: một nửa bát trở lên là tuýp nền tự nhiên.'
        return dict(message=msg)

    if name == 'sl_photo':
        kit.need(_case(t) == 'photo', 'Ảnh mẫu của khách này là ảnh thường, không cần soi ảnh gốc.')
        kit.need(not t['photo_seen'], 'Đã soi ảnh gốc rồi.')
        t['photo_seen'] = True
        return dict(message=f'📸 {t["_x"]["real"]["text"]} {who} ngẩn ra: “Ủa… vậy màu thật là vầy hả? Vậy làm màu thật đó đi!”')

    if name == 'sl_calm':
        kit.need(_case(t) == 'kid', 'Chỉ cần dỗ khi có bé khó ngồi yên trên ghế.')
        tool = kit.one_of(p.get('tool'), CALM_IDS, 'Cách dỗ bé không hợp lệ.')
        kit.need(tool not in t['soothed'], 'Cách này dùng rồi, bé hết hứng.')
        kit.need('cut' not in t['done'], 'Đã cắt xong rồi.')
        t['soothed'].append(tool)
        best = tool == t['_x']['soothe']
        gain = CALM_BEST if best else CALM_OTHER
        t['calm'] = min(100, t['calm'] + gain)
        label = next(x['label'] for x in CALM_TOOLS if x['id'] == tool)
        if best:
            return dict(message=f'{label}: bé Bin sáng mắt, ngồi yên hẳn (+{gain} bình tĩnh). Bố bé thở phào.', celebrate=True)
        return dict(message=f'{label}: bé chỉ chịu yên được một chút (+{gain}). Nghe lại bố kể thói quen của bé xem.')

    if name == 'sl_plan':
        kit.need(not _work_started(t), 'Đã bắt đầu làm rồi, không đổi phương án giữa chừng.')
        services = kit.id_list(p.get('services'), SERVICE_IDS, 6, 'Chọn dịch vụ trong danh sách.')
        kit.need(services, 'Chọn ít nhất một dịch vụ.')
        sessions = kit.integer(p.get('sessions'), 1, 3)
        services = [x for x in SERVICE_IDS if x in services]
        # Weak hair: recommending a treatment the client did not ask for is care, not an upsell.
        advised = _weak(t) and 'treatment' in services and 'treatment' not in n['services']
        extra = [x for x in services if x not in n['services'] and not (x == 'treatment' and advised)]
        if extra:
            t['mistakes'] += 1
            _flag(t, 'pushy')
            return dict(message=f'{who}: “Mình đâu có nhờ {_names(extra)}. Làm đúng phần mình cần thôi nha.”', refused=True)
        if t['patch_done'] and any(x in DYE_SERVICES for x in services):
            t['mistakes'] += 1
            return dict(message='Vừa thử dị ứng xong: phải chờ tới ngày sau mới nhuộm. Bỏ phần màu khỏi phương án hôm nay.', refused=True)
        unjust = [x for x in n['services'] if x not in services and not _may_postpone(c, t, x)]
        if unjust:
            t['mistakes'] += 1
            return dict(message=f'{who}: “Sao lại bỏ {_names(unjust)}? Mình vẫn muốn làm mà.”', refused=True)
        if sessions > key['sessions']:
            t['mistakes'] += 1
            return dict(message=f'{who}: “Tới {sessions} buổi lận hả? Tóc mình đâu cần lâu vậy?”', refused=True)
        quote = _quote(c, services)
        # The client agrees to pay for a treatment her hair really needs, beyond what she planned to spend.
        if quote - (_quote(c, ['treatment']) if advised else 0) > key['budget']:
            return dict(message=f'{who}: “{quote} xu hả… vượt ngân sách mất rồi.” Xem lại giá dịch vụ nhé.', refused=True)
        informed = set(key['must_ask']) <= set(t['asked']) and set(key['must_inspect']) <= set(t['inspected'])
        if _case(t) == 'photo' and not t['photo_seen']:
            informed = False
            _flag(t, 'photo_blind')
        elif 'photo_blind' in t['flags']:
            t['flags'].remove('photo_blind')    # re-planned after looking at the original photo
        overpromise = sessions < key['sessions']
        t['plan'] = dict(services=services, sessions=sessions, informed=informed, overpromise=overpromise)
        t['quote'] = quote
        if t.get('gen'):
            t['advised'] = advised
        kit.start_work(t)
        msg = f'Đã chốt: {_names(services)} · {quote} xu.'
        if advised:
            msg += f' {who} sờ ngọn tóc, gật đầu: “Tóc yếu thật, làm thêm phục hồi cho chắc.”'
        if overpromise:
            msg += f' {who} reo lên: “Hôm nay là giống ảnh luôn hả!”'
        elif sessions > 1:
            msg += f' {who} hơi tiếc nhưng hiểu: chia {sessions} buổi để tóc còn khỏe.'
        else:
            msg += f' {who} gật đầu đồng ý.'
        return dict(message=msg)

    if name == 'sl_patch':
        kit.need(_dye_requested(t), 'Khách không làm màu, không cần thử dị ứng.')
        kit.need(not _allergic(c, t), 'Sổ dị ứng của tiệm đã ghi khách phản ứng với thuốc nhuộm — không thử lại, không nhuộm.')
        kit.need(not _has_record(c, t), 'Khách đã có kết quả thử dị ứng trong hồ sơ, không cần thử lại.')
        kit.need(not t['patch_done'], 'Đã thử dị ứng cho khách hôm nay rồi.')
        kit.need(not t['bowl'] and not t['timer'], 'Đang có bát màu dở. Xử lý xong rồi thử dị ứng.')
        t['cost'] += kit.take(c, 'gloves', 1)
        t['patch_done'] = True
        t['patch_fee'] = kit.price(c, 'patch', PRICES['patch'])
        kit.metric(c, 'salon_patch_tests')
        kit.start_work(t)
        _drop(c, t, DYE_SERVICES)
        rest = [x for x in n['services'] if x not in DYE_SERVICES and x not in key['postpone']]
        if t.get('gen') and t['_x'].get('react'):
            # The stale record was worth nothing: the test itself reacts. Written in the allergy book for good.
            t['reacted'] = True
            d['allergy'][t['npc']] = c['day']
            kit.metric(c, 'salon_allergy_caught')
            head = ('🩹 Chấm thử sau tai: chưa tới hai mươi phút, vùng da đã đỏ, ngứa rát — phản ứng dị ứng. '
                    'Lau sạch, chườm mát, ghi sổ dị ứng: không nhuộm hóa chất cho khách này.')
            if not rest:
                kit.complete(s, c, t, t['patch_fee'], f'Bạn thử dị ứng lại cho {who}, phát hiện phản ứng và không nhuộm.', status='referred')
                return dict(message=f'{head} {who} run run: “May mà chưa nhuộm cả đầu…”' + _visit(c, t), celebrate=True)
            return dict(message=f'{head} Hôm nay vẫn làm được: {_names(rest)}. Chốt lại phương án nhé.', celebrate=True)
        d['patch_log'][t['npc']] = c['day']
        if not rest:
            kit.complete(s, c, t, t['patch_fee'], f'Bạn đã thử dị ứng cho {who} và hẹn nhuộm vào ngày sau thay vì liều nhuộm ngay.', status='referred')
            return dict(message=f'Đã chấm thử thuốc sau tai và ghi sổ. Hẹn {who} nhuộm từ ngày sau · +{t["patch_fee"]} xu phí thử.' + _visit(c, t), celebrate=True)
        return dict(message=f'Đã chấm thử thuốc sau tai, ghi sổ. Màu hẹn ngày sau; hôm nay vẫn làm được: {_names(rest)}. Chốt lại phương án nhé.')

    if name == 'sl_strand':
        kit.need('bleach' in n['services'], 'Chỉ thử lọn khi khách cần tẩy.')
        kit.need(not t['strand'], 'Đã thử lọn rồi.')
        t['cost'] += kit.take(c, 'foil', 1)
        t['strand'] = True
        kit.start_work(t)
        return dict(message='🧵 ' + hair['strand'])

    if name == 'sl_mix':
        kit.need(plan, 'Chốt phương án với khách trước khi pha màu.')
        kind = kit.one_of(p.get('kind'), CHEM, 'Chọn loại bát: nhuộm, tẩy hoặc toner.')
        kit.need(kind in plan['services'], 'Phần này không có trong phương án khách đã đồng ý.')
        kit.need(kind not in t['done'], 'Phần này đã làm xong.')
        kit.need(t['bowl'] is None, 'Bát đang có thuốc. Thoa hoặc đổ bát trước khi pha bát mới.')
        kit.need(t['timer'] is None, 'Đang ủ thuốc. Xả xong rồi pha bát tiếp.')
        if kind == 'toner' and 'bleach' in plan['services']:
            kit.need('bleach' in t['done'], 'Tẩy và xả xong rồi mới phủ toner.')
        dev = kit.integer(p.get('dev'), 10, 40)
        kit.need(dev in DEVS, 'Chọn oxy 10, 20, 30 hoặc 40 vol.')
        ratio = kit.one_of(p.get('ratio'), RATIOS, 'Tỷ lệ trộn không hợp lệ.')
        mx = None
        if kind == 'color':
            shade = kit.one_of(p.get('shade'), DYE_INDEX, 'Chọn một tuýp thuốc nhuộm.')
            if t.get('gen'):
                # v0.5 bowl: up to two tubes, 1–3 parts each.
                shade2 = p.get('shade2')
                if shade2 is not None:
                    kit.one_of(shade2, DYE_INDEX, 'Tuýp thứ hai không hợp lệ.')
                    kit.need(shade2 != shade, 'Tuýp thứ hai phải khác tuýp thứ nhất.')
                parts = p.get('parts', [1, 0] if shade2 is None else None)
                kit.need(isinstance(parts, list) and len(parts) == 2 and all(type(v) is int for v in parts), 'Số phần pha không hợp lệ.')
                kit.need(parts[0] in MIX_PARTS and (parts[1] == 0 if shade2 is None else parts[1] in MIX_PARTS), 'Mỗi tuýp pha 1–3 phần.')
                mx = dict(b=shade2, pa=parts[0], pb=parts[1])
        elif kind == 'toner':
            shade = kit.one_of(p.get('shade'), TONER_INDEX, 'Chọn một tuýp toner.')
        else:
            shade = 'bleach'
        # Safety stops happen before any tube is opened.
        if kind in DYE_SERVICES and _allergic(c, t):
            t['mistakes'] += 1
            _flag(t, 'no_patch')
            _drop(c, t, DYE_SERVICES)
            return dict(message=f'Linh (thợ màu) giữ tay bạn lại: sổ dị ứng ghi {who} từng phản ứng với thuốc nhuộm. Không nhuộm — phần màu đã được gạch khỏi phương án.', refused=True)
        insist = ''
        if kind in DYE_SERVICES and not _has_record(c, t):
            if 'no_patch' not in t['flags']:
                t['mistakes'] += 1
                _flag(t, 'no_patch')
                _drop(c, t, DYE_SERVICES)
                return dict(message=f'Linh (thợ màu) giữ tay bạn lại: {who} chưa có kết quả thử dị ứng. Phải thử dị ứng trước, hẹn nhuộm hôm khác. Phần màu đã được gạch khỏi phương án hôm nay.', refused=True)
            # Warned once and the colour put back in the plan anyway: it goes ahead, and the client will know.
            if 'dye_no_patch' not in t['flags']:
                t['mistakes'] += 1
            _flag(t, 'dye_no_patch')
            insist = 'Linh lắc đầu bỏ đi: bạn vẫn pha thuốc khi khách chưa thử dị ứng. '
        if kind in key['postpone']:
            t['mistakes'] += 1
            _flag(t, 'scalp_stop')
            _drop(c, t, key['postpone'])
            msg = 'Rẽ ngôi thì thấy da đầu có vết trầy đỏ. Luật an toàn của salon: không thoa hóa chất lên da đầu tổn thương. Phần này đã được gạch khỏi phương án, hẹn khi da lành.'
            if not t['plan'] and not [x for x in n['services'] if x not in key['postpone'] and x not in DYE_SERVICES]:
                kit.complete(s, c, t, 0, f'Bạn phát hiện da đầu {who} bị trầy và hẹn làm màu khi da lành.', status='referred')
                msg += _visit(c, t)
            return dict(message=msg, refused=True)
        if kind == 'bleach' and _too_weak_to_bleach(t):
            t['mistakes'] += 1
            _flag(t, 'weak_stop')
            _drop(c, t, ('bleach', 'toner'))
            return dict(message=f'Linh vuốt thử ngọn tóc rồi lắc đầu: tóc {who} chỉ còn sức khỏe {_hp(t)}/100 — tẩy lúc này là gãy. '
                                'Hôm nay phục hồi trước, hẹn tẩy khi tóc khỏe lại. Phần tẩy đã được gạch khỏi phương án.', refused=True)
        cost = kit.take(c, shade, 1) + kit.take(c, DEV_ITEM[dev], 1) + kit.take(c, 'gloves', 1)
        if mx and mx['b']:
            cost += kit.take(c, mx['b'], 1)
        if kind == 'bleach':
            cost += kit.take(c, 'foil', 1)
        if mx is not None:
            issue, hit = _mix_issue(t, shade, mx, dev, ratio)
        else:
            issue, hit = _formula_issue(t, kind, shade if kind != 'bleach' else None, dev, ratio), None
        t['bowl'] = dict(kind=kind, shade=shade, dev=dev, ratio=ratio, cost=cost, ok=issue is None)
        if mx is not None:
            t['bowl'].update(mix=mx, hit=hit)
        t['cost'] += cost
        label = DYE_INDEX[shade]['code'] if kind == 'color' else TONER_INDEX[shade]['tone'] if kind == 'toner' else 'bột tẩy'
        if mx and mx['b']:
            label = f'{mx["pa"]} phần {label} + {mx["pb"]} phần {DYE_INDEX[mx["b"]]["code"]}'
        msg = f'{insist}Đã trộn bát {SERVICE_INDEX[kind]["name"].lower()}: {label} + oxy {dev} vol, tỷ lệ {ratio}.'
        if mx is not None:
            m = _bowl_mix(t, t['bowl'])
            msg += f' Hỗn hợp: level {_level_text(m)} · {BAND_NAME[m["band"]].lower()}.'
        if issue:
            t['mistakes'] += 1
            return dict(message=msg + ' ' + issue + ' Có thể đổ bát và pha lại.')
        return dict(message=msg + ' Kem mịn, đúng màu khách cần — sẵn sàng thoa.' if mx is not None else msg + ' Kem mịn, sẵn sàng thoa.')

    if name == 'sl_dump':
        kit.confirm(p, 'Xác nhận đổ bát; thuốc đã pha được ghi hao hụt.')
        kit.need(t['bowl'], 'Bát màu đang trống.')
        kit.waste(c, 'bowl', 1, t['bowl']['cost'], 'Đổ bát thuốc pha sai hoặc không dùng')
        t['bowl'] = None
        d['dumped'] += 1
        kit.metric(c, 'salon_bowls_dumped')
        return dict(message='Đã đổ bát, rửa sạch. Pha lại theo bảng luật nhé.')

    if name == 'sl_apply':
        b = t['bowl']
        kit.need(b, 'Chưa có bát thuốc để thoa.')
        kit.need(t['timer'] is None, 'Đang ủ một lượt thuốc rồi.')
        kit.need(b['dev'] != 40, 'Không thoa oxy 40 vol sát da đầu — quy định an toàn của salon. Đổ bát và pha lại.')
        if b['kind'] == 'bleach' and hair['history'] == 'box_dye' and not t['strand']:
            t['mistakes'] += 1
            _flag(t, 'no_strand')
            return dict(message='Linh (thợ màu) cản lại: tóc nhuộm hộp phải thử lọn trước khi tẩy cả đầu — thuốc hộp có thể phản ứng nóng và làm gãy tóc. Thử lọn trước nhé.', refused=True)
        fragile = b['kind'] == 'bleach' and (hair['history'] in ('box_dye', 'bleached') or _weak(t))
        tools = _use_tools(c, t)
        t['timer'] = dict(kind=b['kind'], start=round(kit.now(), 3), fragile=fragile, bowl=b)
        fast = False
        if t.get('gen'):
            fast = _today(c)['id'] == 'heat'
            t['timer']['fast'] = fast
        t['bowl'] = None
        w = _window(b['kind'], fragile, fast)
        return dict(message=f'Đã thoa đều từ chân tới ngọn. Xả khi thanh ủ vào vùng xanh ({w["under"]}–{w["ideal"]} giây).'
                    + (' Tóc đã qua hóa chất: cửa sổ ngắn hơn, canh kỹ!' if fragile else '')
                    + (' Trời nóng: thuốc lên nhanh hơn thường lệ!' if fast else '') + tools)

    if name == 'sl_rinse':
        tm = t['timer']
        kit.need(tm, 'Chưa có thuốc nào đang ủ.')
        secs = max(0.0, kit.now() - tm['start'])
        zone = _zone(secs, _window(tm['kind'], tm['fragile'], tm.get('fast', False)))
        res = dict(zone=zone, secs=round(min(secs, 10**6), 1), ok=tm['bowl']['ok'], shade=tm['bowl']['shade'], dev=tm['bowl']['dev'],
                   ratio=tm['bowl']['ratio'])
        mix_note = ''
        if tm['bowl'].get('mix'):
            res.update(mix=dict(tm['bowl']['mix']), hit=tm['bowl']['hit'])
            m = _bowl_mix(t, tm['bowl'])
            want = key.get('color') or {}
            if want.get('grey') and 2 * m['nat'] < m['den'] and zone != 'under':
                _flag(t, 'grey_show')
                mix_note = ' Soi gương: tóc bạc vẫn lộ lấm tấm vì bát thiếu nền tự nhiên.'
            if zone == 'ideal' and tm['bowl']['ok']:
                d['mixes'] += 1
        t['results'][tm['kind']] = res
        t['timer'] = None
        t['done'].append(tm['kind'])
        if zone in ('under', 'damage'):
            t['mistakes'] += 1
        if zone == 'damage':
            _flag(t, 'breakage')
        for item in ('shampoo', 'towel'):
            if kit.stock(c, item):
                t['cost'] += kit.take(c, item, 1)
        t['washed'] = True
        text = {
            'color': dict(under='Chưa đủ giờ: màu lên nhạt, chân tóc loang.', ideal='Màu lên đều, đúng độ bóng.',
                          over='Hơi quá giờ: màu tối và đục hơn một chút.', damage='Ủ quá lâu: tóc nóng, giòn, vài sợi gãy khi chải!'),
            'bleach': dict(under='Tẩy chưa đủ: tóc mới lên cam đậm.', ideal='Tóc lên đều level 7 ánh vàng — đúng mức an toàn hôm nay.',
                           over='Tóc sáng nhưng hơi xơ.', damage='Quá giờ: tóc bị “cháy”, gãy từng mảng!'),
            'toner': dict(under='Toner chưa đủ, vẫn còn ánh cam.', ideal='Ánh cam vàng đã được khử, ra màu khói lạnh.',
                          over='Hơi quá: tóc ngả xám tím.', damage='Quá lâu: tóc tím xỉn.'),
        }[tm['kind']][zone]
        if tm['kind'] in DYE_SERVICES and 'dye_no_patch' in t['flags'] and (t.get('_x') or {}).get('react') and 'allergy_hit' not in t['flags']:
            # The stale record was worth nothing: the whole head reacts. Written in the allergy book for good.
            _flag(t, 'allergy_hit')
            d['allergy'][t['npc']] = c['day']
            mix_note += f' {who} kêu rát: da đầu và vành tai nổi mẩn đỏ, ngứa — phản ứng dị ứng thuốc nhuộm! Chườm mát, ghi sổ dị ứng.'
        return dict(message=f'Xả thuốc sau {secs:.1f} giây, gội sạch. {text}{mix_note}',
                    celebrate=zone == 'ideal' and tm['bowl']['ok'] and 'dye_no_patch' not in t['flags'])

    if name == 'sl_wash':
        kit.need(plan, 'Chốt phương án trước khi gội.')
        kit.need(not t['washed'], 'Tóc khách đã được gội, xả rồi.')
        kit.need(t['timer'] is None, 'Đang ủ thuốc, dùng nút “Xả” để xả thuốc.')
        t['cost'] += kit.take(c, 'shampoo', 1) + kit.take(c, 'conditioner', 1) + kit.take(c, 'towel', 1)
        t['washed'] = True
        tools = _use_tools(c, t)
        pending = [x for x in plan['services'] if x in ('color', 'bleach') and x not in t['done']]
        if pending:
            t['mistakes'] += 1
            _flag(t, 'wet_color')
            return dict(message='Đã gội, massage da đầu. Linh nhắc: nhuộm, tẩy nên làm trên tóc khô chưa gội để dầu tự nhiên bảo vệ da đầu.' + tools)
        if _case(t) == 'kid':
            t['calm'] = max(0, t['calm'] - 8)
            return dict(message=f'Gội xong, bé Bin lắc đầu vẩy nước tung tóe (bình tĩnh còn {t["calm"]}).' + tools)
        return dict(message=f'Đã gội, massage da đầu, lau khô bằng khăn sạch. {who} thư giãn thấy rõ.' + tools)

    if name == 'sl_cut':
        kit.need(plan and 'cut' in plan['services'], 'Phương án đã chốt không có cắt.')
        kit.need('cut' not in t['done'], 'Đã cắt xong và kiểm đối xứng rồi.')
        kit.need(t['timer'] is None, 'Đang ủ thuốc, xả xong rồi mới cắt.')
        kit.need(t['washed'], 'Gội ẩm tóc trước khi cắt để đường cắt chính xác.')
        step = kit.one_of(p.get('step'), CUT_STEPS, 'Bước cắt không hợp lệ.')
        out = _cut_step(t, key, who, step, p)
        snip = step != 'check' or t['cut']['done']     # a mirror check the client turns down is not a snip
        if _case(t) == 'kid' and snip:
            # Every snip on the chair wears a wriggly child down a little more.
            t['calm'] = max(0, t['calm'] - (12 + 3 * kit.tier(t['day'])))
        if snip:
            out['message'] += _use_tools(c, t)
        return out

    if name == 'sl_treat':
        kit.need(plan and 'treatment' in plan['services'], 'Phương án đã chốt không có phục hồi.')
        kit.need('treatment' not in t['done'], 'Đã phục hồi rồi.')
        kit.need(t['timer'] is None and t['bowl'] is None, 'Xử lý xong bát thuốc đang dở trước.')
        kit.need(not [x for x in plan['services'] if x in CHEM and x not in t['done']], 'Làm xong phần hóa chất rồi mới phục hồi.')
        kit.need(t['washed'], 'Gội sạch trước khi thoa keratin.')
        t['cost'] += kit.take(c, 'keratin', 1)
        t['treated'] = True
        t['done'].append('treatment')
        return dict(message='Thoa keratin từng lớp, hấp ấm 10 phút, xả mát. Sợi tóc mềm và bóng hơn hẳn.' + _use_tools(c, t))

    if name == 'sl_style':
        kit.need(plan and 'style' in plan['services'], 'Phương án đã chốt không có sấy tạo kiểu.')
        kit.need('style' not in t['done'], 'Đã tạo kiểu rồi.')
        kit.need(t['timer'] is None and t['bowl'] is None, 'Xử lý xong bát thuốc đang dở trước.')
        kit.need(t['washed'], 'Gội, xả trước khi sấy.')
        pending = [x for x in plan['services'] if x != 'style' and x not in t['done']]
        kit.need(not pending, 'Làm xong ' + _names(pending) + ' rồi mới sấy tạo kiểu.')
        finish = kit.one_of(p.get('finish'), FINISH_IDS, 'Kiểu sấy không hợp lệ.')
        t['styled'] = finish
        t['done'].append('style')
        tools = _use_tools(c, t)
        if key['finish'] and finish != key['finish']:
            t['mistakes'] += 1
            _flag(t, 'finish_wrong')
            return dict(message=f'{who}: “Đẹp thì đẹp… nhưng không hợp thói quen và dịp của mình.”' + tools)
        return dict(message=f'Sấy xong: {FINISHES[FINISH_IDS.index(finish)]["name"].lower()}. {who} xoay trái xoay phải trước gương.' + tools)

    if name == 'sl_checkout':
        kit.confirm(p, 'Xác nhận thanh toán với khách.')
        kit.need(plan, 'Chưa chốt phương án nào để thanh toán.')
        pending = [x for x in plan['services'] if x not in t['done']]
        kit.need(not pending, 'Còn dịch vụ chưa làm: ' + _names(pending) + '.')
        kit.need(t['timer'] is None and t['bowl'] is None, 'Còn bát thuốc hoặc lượt ủ chưa xử lý.')
        products = kit.id_list(p.get('products', []), RETAIL_IDS, 3, 'Sản phẩm tư vấn không hợp lệ.')
        book = kit.id_list(p.get('book', []), APPT_KINDS, len(APPT_KINDS), 'Lịch hẹn lần tới không hợp lệ.')
        kit.need(all(k in _bookable(t) for k in book), 'Lần làm hôm nay không cần hẹn này.')
        # The hand-off: the client looks in the mirror and holds us to what was agreed.
        _record_slips(c, t, products)
        redo = bool(cq.slips(t)) and all(x['code'] == 'finish' for x in cq.slips(t))
        mood = cq.decide(c, t, remake=redo)
        if mood == 'remake':
            first = cq.slips(t)[0]['text']
            r = cq.react(s, c, t, 0, remake=True, who=who)
            t['done'].remove('style')
            t['styled'] = None
            t['flags'].remove('finish_wrong')
            t['patience'] = max(25, t.get('patience', 100) - 15)
            cq.downgrade(t, 'returned', f'{first} Phải sấy lại.', 'phải sấy lại')
            return dict(message=f'{r["message"]} Khách ngồi lại ghế — sấy lại theo đúng dịp của khách nhé.', correct=False)
        if mood in ('walkout', 'refuse'):
            products = []                  # nobody buys shampoo on the way out of a bad visit
            book = []                      # …nor books the next visit
        left = key['budget'] - t['quote'] - t['patch_fee']
        sold, declined, retail, notes = [], [], 0, []
        for pid in products:
            it = ITEM_INDEX[pid]
            kit.need(it.get('unlock', 1) <= kit.level(c), f'{it["name"]} mở ở cấp {it.get("unlock", 1)}.')
            kit.need(kit.stock(c, pid) > 0, f'Hết {it["name"]} trên kệ. Mở Kho để nhập thêm nhé.')
            if pid not in key['fit']:
                t['mistakes'] += 1
                _flag(t, 'pushy')
                declined.append(pid)
                notes.append(f'“{it["name"]} hả? Tóc mình đâu cần.”')
            elif it['price'] > left:
                declined.append(pid)
                notes.append(f'“{it["name"]} để lần sau nha, hết ngân sách rồi.”')
            else:
                t['cost'] += kit.take(c, pid, 1)
                sold.append(pid)
                retail += it['price']
                left -= it['price']
        if _dye_requested(t) and not _has_record(c, t) and not t['patch_done'] and not _allergic(c, t):
            _flag(t, 'skip_patch')
        t['sold'], t['declined'] = sold, declined
        bonus, rush_note = 0, ''
        left_turns = _rush_left(c, t)
        if left_turns is not None:
            if left_turns >= 0:
                d['rush_on_time'] += 1
                if mood in ('accept', 'grumble'):      # an unhappy client keeps the “thank you” money
                    bonus = n['rush']['bonus']
                    rush_note = f' Kịp giờ! {who} gửi thêm {bonus} xu cảm ơn.'
            else:
                rush_note = f' Trễ hẹn {-left_turns} nhịp — {who} vội chạy đi, không còn tiền gấp.'
        if _case(t) == 'kid' and 'slip' not in t['flags']:
            d['kids_calm'] += 1
        if t.get('gen'):
            t['memo'] = _memo(c, t)
        # Money for a job done wrong is settled once, by the client's reaction (services only; products are their own sale).
        r = cq.react(s, c, t, t['quote'] + t['patch_fee'], who=who)
        reward = r['pay'] + retail + bonus
        d['served'] += 1
        d['day_served'] += 1
        kit.metric(c, 'salon_clients')
        if sold:
            kit.metric(c, 'salon_retail', len(sold))
        kit.complete(s, c, t, reward, f'Bạn đã làm tóc cho {who}: {_names(plan["services"])}.')
        tail = (' ' + ' '.join(notes)) if notes else ''
        tail += _visit(c, t, sold, book)
        if reward:
            parts = [f'dịch vụ {r["pay"]}'] + ([f'sản phẩm {retail}'] if retail else []) + ([f'tiền gấp {bonus}'] if bonus else [])
            head = f'Thanh toán {reward} xu' + (f' ({" + ".join(parts)})' if len(parts) > 1 else '') + f'. {who} sẽ để lại đánh giá.'
        else:
            head = f'{who} không thanh toán đồng nào và sẽ để lại đánh giá.'
        msg = head + rush_note + tail + (' ' + r['message'] if r['message'] else '')
        return dict(message=msg, celebrate=not cq.slips(t), correct=not cq.slips(t))

    raise kit.eng().GameError('Thao tác salon không hợp lệ.')


# ------------------------------------------------------------------ care loop: the client card, bookings, appointments
def _npc_name(npc: str) -> str:
    return PEOPLE[int(npc.rsplit('_', 1)[1]) - 1][0]


def _bookable(t: dict) -> list:
    """What this visit calls for next time (computed from the finished work only)."""
    if not t.get('gen') or not t.get('plan'):
        return []
    out = []
    col = t['results'].get('color')
    if (col and col.get('mix') and col['zone'] in ('ideal', 'over') and col['ok'] and col.get('hit')
            and not {'dye_no_patch', 'allergy_hit'} & set(t['flags'])):
        out.append('roots')
    if 'cut' in t['done'] and not t['cut']['short']:
        out.append('trim')
    if _health_after(t) < CARE_BELOW:
        out.append('care')
    return out


def _memo(c: dict, t: dict):
    """Did a regular get the colour on her card again? ('same' formula, a different bowl that still hit, or not relevant)."""
    f, col = _card_formula(c, t), t['results'].get('color')
    if not f or not col or not col.get('mix') or col['zone'] == 'under':
        return None
    mx = col['mix']
    if _same_formula(f, col['shade'], mx['b'], mx['pa'], mx['pb'], col['dev'], col.get('ratio', '1:1')):
        return 'same'
    return 'drift' if col.get('hit') else None


def _stars(c: dict, t: dict) -> int:
    post = next((p for p in reversed(c['feed']) if p.get('source') == t['id'] and p.get('kind') == 'review'), None)
    if not post:
        return 0
    fb = post.get('feedback') or {}
    return int(fb.get('fair') or post.get('stars') or 0)


def _trim_appts(d: dict) -> None:
    rows = d['appts']
    while len(rows) > APPT_MAX:
        old = next((a for a in rows if a['state'] != 'open'), rows[0])
        ar.record([old], 'salon.appts')
        rows.remove(old)


def _visit(c: dict, t: dict, sold=(), book=()) -> str:
    """After a finished v0.5 visit: write the client card (health, formula, cut, trust), close bookings the visit
    already covered and book the next ones. Returns a short line for the checkout message."""
    if not t.get('gen'):
        return ''
    d = _data(c)
    npc, cards = t['npc'], d['cards']
    card = cards.get(npc)
    new = card is None
    if new:
        card = cards[npc] = dict(visits=0, first=c['day'], last=c['day'], trust=0, health=_hp(t), hist=None, formula=None,
                                 cut=None, services=[], stars=0, patch_file=False)
    stars = _stars(c, t)
    before = card['health']
    card.update(visits=min(10 ** 6, card['visits'] + 1), last=c['day'], stars=max(0, min(5, stars)),
                services=list((t['plan'] or {}).get('services', [])), health=_health_after(t, sold))
    if 'history' in t['asked'] and t['_hair'].get('history') in HIST:
        card['hist'] = t['_hair']['history']
    if t['patch_record'] == 'file':
        card['patch_file'] = True
    col, want = t['results'].get('color'), t['_key'].get('color')
    if col and col.get('mix') and want and 'level' in want:
        mx = col['mix']
        card['formula'] = dict(shade=col['shade'], b=mx['b'], pa=mx['pa'], pb=mx['pb'], dev=col['dev'], ratio=col.get('ratio', '1:1'),
                               level=want['level'], band=want['tone'], hit=bool(col.get('hit')) and col['ok'], zone=col['zone'], day=c['day'])
    if 'cut' in t['done']:
        card['cut'] = dict(removed=t['cut']['removed'], short=t['cut']['short'], day=c['day'])
    parts = []
    if cq.safety(t):
        if card['trust']:
            card['trust'] -= 1
            parts.append('khách bớt tin tiệm một chút')
    elif t['status'] in ('completed', 'referred') and stars >= 4 and not cq.slips(t) and card['trust'] < TRUST_MAX:
        card['trust'] += 1
        parts.append(TRUST_NAMES[card['trust']].lower())
    covered = {'roots': 'color', 'trim': 'cut', 'care': 'treatment'}
    for a in d['appts']:
        if a['state'] == 'open' and a['npc'] == npc and covered[a['kind']] in t['done']:
            a['state'] = 'merged'
    if t['status'] == 'completed' and ('treatment' in t['done'] or 'bleach' in t['done'] or before != card['health']):
        parts.append(f'sức khỏe tóc {card["health"]}/100 ({_health_word(card["health"]).lower()})')
    msg = f' 📇 Thẻ khách {"mới" if new else "cập nhật"}: ' + (', '.join(parts) if parts else f'{card["visits"]} lần ghé') + '.'
    if book:
        booked = []
        for k in book:
            due = c['day'] + APPTS[k]['days']
            a = next((a for a in d['appts'] if a['state'] == 'open' and a['npc'] == npc and a['kind'] == k), None)
            if a:
                a.update(due=due, booked=c['day'])
            else:
                d['appt_seq'] += 1
                d['appts'].append(dict(id=f'H{d["appt_seq"]}', npc=npc, kind=k, due=due, booked=c['day'], state='open', stars=0))
            booked.append(f'{APPTS[k]["label"].lower()} ngày {due}')
        _trim_appts(d)
        t['booked'] = list(book)
        kit.metric(c, 'salon_booked', len(book))
        msg += f' 📅 Đã hẹn: {", ".join(booked)}.'
    return msg


def _appt(s: dict, c: dict, p: dict) -> dict:
    """A booked client is back: serve the appointment in one sitting (roots, trim or care)."""
    d = _data(c)
    aid = p.get('id')
    a = next((a for a in d['appts'] if a['id'] == aid), None) if isinstance(aid, str) else None
    kit.need(a is not None and a['state'] == 'open', 'Lịch hẹn này không còn.')
    kit.need(a['due'] <= c['day'], f'Khách hẹn ngày {a["due"]} mới tới.')
    kit.need(c['day'] <= a['due'] + APPT_KEEP, 'Lịch hẹn này đã quá hạn.')
    card = d['cards'].get(a['npc'])
    kit.need(card is not None, 'Chưa có thẻ khách này.')
    who, kind, info = _npc_name(a['npc']), a['kind'], APPTS[a['kind']]
    notes, stars = [], 5
    if kind == 'roots':
        f = card['formula']
        kit.need(f is not None, 'Thẻ khách chưa có công thức màu.')
        if a['npc'] in d['allergy']:
            a['state'] = 'void'
            return dict(message=f'Sổ dị ứng ghi {who} từng phản ứng với thuốc nhuộm — không dặm màu. Đã gọi báo hủy hẹn, khách cảm ơn vì tiệm cẩn thận.',
                        refused=True)
        shade = kit.one_of(p.get('shade'), DYE_INDEX, 'Chọn tuýp thuốc nhuộm.')
        shade2 = p.get('shade2')
        if shade2 is not None:
            kit.one_of(shade2, DYE_INDEX, 'Tuýp thứ hai không hợp lệ.')
            kit.need(shade2 != shade, 'Tuýp thứ hai phải khác tuýp thứ nhất.')
        parts = p.get('parts', [1, 0] if shade2 is None else None)
        kit.need(isinstance(parts, list) and len(parts) == 2 and all(type(v) is int for v in parts), 'Số phần pha không hợp lệ.')
        kit.need(parts[0] in MIX_PARTS and (parts[1] == 0 if shade2 is None else parts[1] in MIX_PARTS), 'Mỗi tuýp pha 1–3 phần.')
        dev = kit.integer(p.get('dev'), 10, 40)
        kit.need(dev in DEVS, 'Chọn oxy 10, 20, 30 hoặc 40 vol.')
        kit.need(dev != 40, 'Chân tóc sát da đầu: không bao giờ dùng oxy 40 vol.')
        kit.take(c, shade, 1)
        if shade2:
            kit.take(c, shade2, 1)
        kit.take(c, DEV_ITEM[dev], 1)
        kit.take(c, 'gloves', 1)
        m = _mix(shade, shade2, parts[0], parts[1])
        if _same_formula(f, shade, shade2, parts[0], parts[1], dev, f['ratio']):
            text, done = f'Dặm chân tóc đúng công thức cũ, chân và thân liền một màu như chưa từng mọc.', 'chân tóc liền màu thân tóc'
        elif _level_ok(m, f['level']) and m['band'] == f['band'] and dev == f['dev']:
            stars = 4
            text, done = 'Chân tóc đã phủ, nhìn kỹ dưới nắng thấy ánh hơi khác phần thân.', 'chân tóc hơi khác ánh thân tóc'
        else:
            stars = 2
            text, done = 'Chân tóc ra một màu, thân tóc một màu, lộ vệt ngang như đội mũ.', 'chân tóc lệch màu, lộ vệt'
        card['health'] = max(10, card['health'] + ROOT_HIT)
    elif kind == 'trim':
        length = kit.integer(p.get('length'), 1, 6)
        cap = TRIM_CAP[1] if card['cut'] and card['cut']['short'] else TRIM_CAP[0]
        if length <= cap:
            text, done = f'Tỉa đúng {length} cm, giữ nguyên dáng tóc lần trước.', f'tỉa {length} cm giữ dáng'
        else:
            stars = 3
            text, done = f'Dặn chỉ tỉa giữ dáng mà cắt mất {length} cm.', f'tỉa {length} cm, quá mức giữ dáng {cap} cm'
        card['cut'] = dict(removed=length, short=length > cap, day=c['day'])
    else:
        kit.take(c, 'keratin', 1)
        card['health'] = min(100, card['health'] + HEALTH_TREAT)
        text, done = 'Hấp phục hồi đúng hẹn, tóc mềm và bóng lại hẳn.', f'sức khỏe tóc lên {card["health"]}/100'
    if kind in ('roots', 'trim'):
        if _take_set(c):
            notes.append(f'🧼 bộ sạch, còn {d["clean"]}/{CLEAN_SETS}')
        else:
            stars = max(1, stars - 1)
            text += ' Lược kéo dùng lại chưa khử khuẩn, thấy ngại.'
            notes.append('⚠️ dùng bộ lược kéo chưa khử khuẩn')
    price = _appt_price(c, a['kind'])
    pay = price if stars >= 3 else price // 2
    kit.money(s, c, pay, f'Lịch hẹn: {info["label"].lower()} — {who}', a['id'], 'revenue')
    kit.review(s, c, a['npc'], stars, text, f'appt-{a["id"]}')
    a.update(state='done', stars=stars)
    card.update(visits=min(10 ** 6, card['visits'] + 1), last=c['day'], stars=stars)
    if stars == 5 and card['trust'] < TRUST_MAX:
        card['trust'] += 1
    d['appts_done'] += 1
    kit.metric(c, 'salon_appts')
    tail = f' ({"; ".join(notes)})' if notes else ''
    half = f' (chưa vừa ý, chỉ trả nửa giá {price} xu)' if pay < price else ''
    return dict(message=f'{info["emoji"]} {who} tới đúng hẹn — {done}. +{pay} xu{half} · {stars}★.{tail}', celebrate=stars == 5)


def _appt_price(c: dict, kind: str) -> int:
    info = APPTS[kind]
    return info['price'] if info['price'] is not None else kit.price(c, 'treatment', PRICES['treatment'])


def _appt_view(c: dict, a: dict) -> dict:
    info = APPTS[a['kind']]
    return dict(a, who=_npc_name(a['npc']), label=info['label'], emoji=info['emoji'], until=a['due'] + APPT_KEEP, price=_appt_price(c, a['kind']),
                ready=a['state'] == 'open' and a['due'] <= c['day'] <= a['due'] + APPT_KEEP)


def _card_view(c: dict, npc: str, card: dict) -> dict:
    d = kit.data(c)
    v = dict(card, npc=npc, name=_npc_name(npc), trust_name=TRUST_NAMES[card['trust']], health_word=_health_word(card['health']),
             hair=HIST.get(card['hist']) if card['hist'] else None, patch_day=d.get('patch_log', {}).get(npc),
             allergy=npc in d.get('allergy', {}), trim_cap=TRIM_CAP[1] if card['cut'] and card['cut']['short'] else TRIM_CAP[0])
    f = card['formula']
    if f:
        m = _mix(f['shade'], f['b'], f['pa'], f['pb'])
        v['formula'] = dict(f, text=_formula_text(f), mix_level=_level_text(m), mix_band=m['band'], color=m['color'],
                            target=f'level {f["level"]} · {BAND_NAME[f["band"]].lower()}')
    v['next'] = next((dict(kind=a['kind'], due=a['due'], label=APPTS[a['kind']]['label'])
                      for a in sorted(d.get('appts', []), key=lambda a: a['due']) if a['state'] == 'open' and a['npc'] == npc), None)
    return v


# ------------------------------------------------------------------ review
def feedback(c: dict, t: dict) -> dict:
    k, h, flags = t['_key'], t['_hair'], set(t['flags'])
    patience = t.get('patience', 100)
    speed = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    speed_note = f'kiên nhẫn còn {patience}%'
    rush = t['needs'].get('rush') if t.get('gen') else None
    if rush and t['status'] == 'completed':
        on_time = (_rush_left(c, t) or 0) >= 0
        speed, speed_note = (5, 'kịp giờ hẹn gấp') if on_time else (2, 'trễ giờ hẹn gấp')
    if t['status'] == 'referred':
        reacted = t.get('reacted')
        return dict(criteria=[
            dict(key='care', label='An toàn khi làm màu', score=5 if 'scalp_stop' not in flags else 4,
                 note='dừng khi thấy da đầu trầy' if 'scalp_stop' in flags else
                 'thử dị ứng lại, phát hiện phản ứng, không nhuộm' if reacted else 'thử dị ứng trước, hẹn nhuộm sau'),
            dict(key='attitude', label='Tư vấn thật lòng', score=5 if not t['mistakes'] else 3,
                 note='nói rõ vì sao không nhuộm được' if reacted else 'giải thích rõ vì sao phải chờ'),
            dict(key='speed', label='Thời gian chờ', score=speed, note=speed_note)])
    plan = t['plan'] or dict(services=[], informed=False, overpromise=False)
    acc, an = 5, []
    col, tn = t['results'].get('color'), t['results'].get('toner')
    if col and k['color'] and 'shade' in k['color'] and col['shade'] != k['color']['shade']:
        acc -= 2
        an.append('màu khác ảnh mẫu')
    if col and 'hit' in col and not col['hit']:
        acc -= 2
        an.append('màu khác ảnh mẫu')
    if 'grey_show' in flags:
        acc -= 1
        an.append('tóc bạc còn lộ')
    if tn and k['toner'] and tn['shade'] != k['toner']['shade']:
        acc -= 1
        an.append('ánh toner khác mẫu')
    if t['cut']['short']:
        acc -= 2
        an.append('cắt ngắn hơn thỏa thuận')
    if 'layers_wrong' in flags:
        acc -= 1
        an.append('tỉa tầng không đúng mẫu')
    if 'finish_wrong' in flags:
        acc -= 1
        an.append('kiểu sấy không hợp thói quen')
    if plan['overpromise']:
        acc -= 2
        an.append('không giống ảnh mẫu như đã hứa')
    score_of = {'ideal': 5, 'over': 3, 'under': 2, 'damage': 1}
    qual, qn = 5, []
    for kind, r in t['results'].items():
        v = score_of[r['zone']] - (0 if r['ok'] else 1)
        if v < qual:
            qual = v
            qn = [{'ideal': 'công thức pha chưa chuẩn', 'over': 'ủ hơi quá giờ', 'under': 'ủ chưa đủ giờ, màu loang', 'damage': 'ủ quá lâu, tóc gãy'}[r['zone']]
                  + f' ({SERVICE_INDEX[kind]["name"].lower()})']
    if t['cut']['short'] and qual > 3:
        qual, qn = 3, ['đường cắt bị lẹm']
    care, cn = 5, []
    for f, pen, note in (('breakage', 2, 'tóc gãy vì ủ quá lâu'), ('no_strand', 1, 'suýt tẩy khi chưa thử lọn'),
                         ('no_patch', 1, 'suýt nhuộm khi chưa thử dị ứng'), ('scalp_stop', 1, 'suýt thoa thuốc lên da đầu trầy'),
                         ('wet_color', 1, 'gội trước khi nhuộm'), ('skip_patch', 1, 'không thử dị ứng để hẹn màu lần sau'),
                         ('slip', 1, 'bé giãy, kéo trượt vì chưa dỗ được bé'), ('weak_stop', 1, 'suýt tẩy trên tóc quá yếu')):
        if f in flags:
            care -= pen
            cn.append(note)
    if (h['damage'] >= 2 or _weak(t)) and any(x in t['done'] for x in ('bleach', 'color')) and not t['treated']:
        care -= 1
        cn.append('tóc yếu mà không được phục hồi')
    if t.get('tools') == 'dirty':
        care -= 1
        cn.append('dùng lược kéo chưa khử khuẩn')
    if t.get('reacted'):
        cn.append('thử dị ứng lại, phát hiện phản ứng kịp thời')
    att, tnotes = 5, []
    if not plan['informed']:
        att -= 2
        tnotes.append('chốt theo ảnh filter, chưa soi ảnh gốc' if 'photo_blind' in flags else 'chốt phương án khi chưa hỏi, xem kỹ')
    if t.get('gen') and _case(t) == 'kid' and t['_x']['soothe'] in t.get('soothed', []):
        tnotes.append('dỗ bé đúng cách bố kể')
    if 'pushy' in flags:
        att -= 1
        tnotes.append('mời thứ không cần')
    if t.get('advised'):
        tnotes.append('khuyên phục hồi vì tóc yếu thật')
    if plan['overpromise']:
        att = 1
        tnotes.append('hứa giống ảnh mẫu trong một buổi')
    return dict(criteria=[
        dict(key='accuracy', label='Đúng mong muốn', score=max(1, acc), note=', '.join(an) or 'đúng như đã thống nhất'),
        dict(key='quality', label='Tay nghề màu & cắt', score=max(1, qual), note=', '.join(qn) or 'màu và đường cắt chuẩn'),
        dict(key='care', label='An toàn & sức khỏe tóc', score=max(1, care), note=', '.join(cn) or 'an toàn từng bước'),
        dict(key='attitude', label='Tư vấn thật lòng', score=max(1, att), note=', '.join(tnotes) or 'hỏi kỹ, nói thật, không ép mua'),
        dict(key='speed', label='Thời gian chờ', score=speed, note=speed_note)] + _memory_row(t))


def _memory_row(t: dict) -> list:
    memo = t.get('memo') if t.get('gen') else None
    if memo == 'same':
        return [dict(key='memory', label='Nhớ khách', score=5, note='pha đúng công thức trong thẻ, màu y lần trước')]
    if memo == 'drift':
        return [dict(key='memory', label='Nhớ khách', score=4, note='màu đúng nhưng khác công thức lần trước, ánh hơi khác')]
    return []


# ------------------------------------------------------------------ projection & validation
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    ph = n['photo']
    photo = ph['style'] + (f', màu {ph["tone"].lower()} (level {ph["level"]})' if ph.get('level') else '')
    text = f'{n["want"]} Ảnh mẫu: {photo}. {n["note"]}'
    case = _case(t)
    if case == 'photo':
        text += ' (Ảnh khách tự chụp, có dùng filter.)'
    if case == 'kid':
        text += ' Bé khó ngồi yên — dỗ bé đúng cách trước khi cầm kéo.'
    rush = n.get('rush') if t.get('gen') else None
    if rush:
        text += f' Cần xong trong {rush["steps"]} nhịp; kịp giờ khách gửi thêm {rush["bonus"]} xu.'
    return text


def public_task(t: dict) -> dict:
    v = {k: tree_copy(val) for k, val in t.items() if not k.startswith('_')}
    # Hair health is felt with the hands (lengths, ends) or read on a regular's card.
    v['health'] = _hp(t) if t['known'] and t.get('gen') and _health_known(t) else None
    v['health_word'] = _health_word(v['health']) if v['health'] is not None else None
    if not t['known']:
        v['needs'] = None
        return v
    h, k = t['_hair'], t['_key']
    v['answers'] = {x: _answer(t, x) for x in t['asked']}
    v['findings'] = {z: h['find'][z] for z in t['inspected']}
    v['budget'] = k['budget'] if 'budget' in t['asked'] else None
    v['strand_text'] = h['strand'] if t['strand'] else None
    v['look'] = _look(t)
    v['cut_ask'] = cut_ask(t)
    if t['timer']:
        v['timer']['window'] = _window(t['timer']['kind'], t['timer']['fragile'], t['timer'].get('fast', False))
    if t.get('gen'):
        rush = t['needs'].get('rush')
        v['due_turn'] = t['created_turn'] + rush['steps'] if rush else None
        # What the stylist has actually found out, nothing more.
        v['base_warm'] = h.get('warm', 0) if 'lengths' in t['inspected'] else None
        v['grey'] = h.get('grey', 0) if 'roots' in t['inspected'] else None
        v['recipe'] = _recipe_view(t)
        v['real'] = ({k2: t['_x']['real'][k2] for k2 in ('level', 'tone', 'text')}
                     if _case(t) == 'photo' and t['photo_seen'] else None)
        col = t['results'].get('color')
        if col and col.get('mix'):
            m = _bowl_mix(t, col)
            v['mix_result'] = dict(level=_level_text(m), band=m['band'], color=m['color'])
        if t['status'] in ('completed', 'referred', 'cancelled') and _case(t) == 'kid':
            v['truth'] = dict(soothe=t['_x']['soothe'])
        pending = [x for x in (t['plan'] or {}).get('services', []) if x not in t['done']]
        v['bookable'] = _bookable(t) if t['plan'] and not pending else []
        v['weak'] = _weak(t) if v['health'] is not None else None
    return v


def public_data(c: dict) -> dict:
    d = tree_copy(kit.data(c))
    desk = d.pop('desk', None) or kit.desk_initial()
    for k, v in DATA_V2.items():
        d.setdefault(k, tree_copy(v))
    d['sanitized_today'] = d['sanitize_day'] == c['day']
    mod = _today(c)
    d['today'] = dict(id=mod['id'], title=mod['title'], emoji=mod['emoji'], text=mod['text'])
    d['desk'] = kit.desk_public(desk, DESK, ID)
    if d['desk']['ev']:
        # Options come in a shuffled order so the careful answer is not always the first button.
        kit.rng(ID, 'desk-order', d['desk']['ev']['id'], c['day']).shuffle(d['desk']['ev']['options'])
    d['tier'] = kit.tier(c['day'])
    d['allergy'] = len(d['allergy'])
    # Care loop: cards, the appointment book, the tool jar.
    real = kit.data(c)
    d['cards'] = {npc: _card_view(c, npc, card) for npc, card in real.get('cards', {}).items()}
    d['appts'] = [_appt_view(c, a) for a in sorted(real.get('appts', []), key=lambda a: (a['due'], a['id']))
                  if a['state'] == 'open' or (a['state'] == 'done' and a['due'] >= c['day'] - APPT_KEEP)]
    d.setdefault('clean', CLEAN_SETS if d['sanitized_today'] else 0)
    d['clean_max'] = CLEAN_SETS
    d['card_for'] = [t['id'] for t in c['tasks'] if t.get('career') == ID and t.get('gen') and t['status'] not in ('completed', 'referred', 'cancelled')
                     and _card_formula(c, t)]
    return d


def _check_bowl(b) -> None:
    kit.need(isinstance(b, dict) and b.get('kind') in CHEM and b.get('dev') in DEVS and type(b.get('dev')) is int
             and b.get('ratio') in RATIOS and type(b.get('ok')) is bool, 'Bát thuốc sai.')
    allowed = DYE_INDEX if b['kind'] == 'color' else TONER_INDEX if b['kind'] == 'toner' else ('bleach',)
    kit.need(b.get('shade') in allowed, 'Tuýp thuốc sai.')
    kit.integer(b.get('cost'), 0, 1000)
    _check_mix(b)


def _check_mix(b: dict) -> None:
    """v0.5 two-tube bowls carry the second tube and the parts (colour only)."""
    if 'mix' not in b and 'hit' not in b:
        return
    mx = b.get('mix')
    kit.need(b['kind'] == 'color' and isinstance(mx, dict) and set(mx) == {'b', 'pa', 'pb'} and type(b.get('hit')) is bool, 'Bát pha hai tuýp sai.')
    kit.need(type(mx['pa']) is int and mx['pa'] in MIX_PARTS, 'Số phần pha sai.')
    if mx['b'] is None:
        kit.need(type(mx['pb']) is int and mx['pb'] == 0, 'Số phần pha sai.')
    else:
        kit.need(mx['b'] in DYE_INDEX and mx['b'] != b['shade'] and type(mx['pb']) is int and mx['pb'] in MIX_PARTS, 'Tuýp thứ hai sai.')


def validate_task(t: dict, original: dict) -> None:
    def ids(v, allowed, msg):
        kit.need(isinstance(v, list) and len(v) <= len(allowed) and len(set(v)) == len(v) and all(x in allowed for x in v), msg)
    ids(t['asked'], TOPIC_IDS, 'Câu hỏi tư vấn sai.')
    ids(t['inspected'], ZONE_IDS, 'Vùng tóc đã xem sai.')
    ids(t['done'], SERVICE_IDS, 'Dịch vụ đã làm sai.')
    ids(t['flags'], FLAGS, 'Ghi chú công việc sai.')
    ids(t['sold'], RETAIL_IDS, 'Sản phẩm đã bán sai.')
    ids(t['declined'], RETAIL_IDS, 'Sản phẩm từ chối sai.')
    kit.need(t['patch_record'] in (None, 'file', 'log', 'none', 'allergy'), 'Hồ sơ thử dị ứng sai.')
    for k in ('washed', 'patch_done', 'strand', 'treated'):
        kit.need(type(t[k]) is bool, 'Trạng thái salon sai.')
    kit.need(t['styled'] is None or t['styled'] in FINISH_IDS, 'Kiểu sấy sai.')
    kit.integer(t['patch_fee'], 0, 200)
    kit.integer(t['cost'], 0, 100000)
    kit.need(t['quote'] is None or kit.integer(t['quote'], 0, 5000) >= 0, 'Báo giá sai.')
    pl = t['plan']
    if pl is not None:
        kit.need(isinstance(pl, dict) and set(pl) == {'services', 'sessions', 'informed', 'overpromise'}, 'Phương án sai.')
        ids(pl['services'], SERVICE_IDS, 'Dịch vụ trong phương án sai.')
        kit.need(pl['services'] and all(x in t['needs']['services'] or (x == 'treatment' and t.get('advised')) for x in pl['services']),
                 'Phương án có dịch vụ khách không yêu cầu.')
        kit.integer(pl['sessions'], 1, 3)
        kit.need(type(pl['informed']) is bool and type(pl['overpromise']) is bool, 'Phương án sai.')
        kit.need(t['quote'] is not None, 'Thiếu báo giá.')
        kit.need(all(x in pl['services'] for x in t['done']), 'Dịch vụ đã làm ngoài phương án.')
    else:
        kit.need(not [x for x in t['done'] if x != 'patch'], 'Dịch vụ đã làm khi chưa có phương án.')
    if t['bowl'] is not None:
        _check_bowl(t['bowl'])
    tm = t['timer']
    if tm is not None:
        kit.need(isinstance(tm, dict) and tm.get('kind') in CHEM and type(tm.get('fragile')) is bool, 'Lượt ủ sai.')
        kit.need(isinstance(tm.get('start'), (int, float)) and type(tm['start']) is not bool and 0 <= tm['start'] < 10**11, 'Giờ ủ sai.')
        _check_bowl(tm.get('bowl'))
        kit.need(tm['bowl']['kind'] == tm['kind'], 'Lượt ủ sai.')
        kit.need(type(tm.get('fast', False)) is bool and ('fast' not in tm or t.get('gen')), 'Lượt ủ sai.')
    if t.get('gen'):
        kit.need(type(t.get('photo_seen')) is bool and type(t.get('reacted')) is bool, 'Trạng thái salon sai.')
        kit.need(not t['photo_seen'] or _case(t) == 'photo', 'Ảnh gốc sai.')
        kit.need(not t['reacted'] or (_case(t) == 'react' and t['patch_done']), 'Kết quả thử dị ứng sai.')
        soothed = t.get('soothed')
        kit.need(isinstance(soothed, list) and len(set(soothed)) == len(soothed) and all(x in CALM_IDS for x in soothed), 'Cách dỗ bé sai.')
        if _case(t) == 'kid':
            kit.integer(t.get('calm'), 0, 100)
        else:
            kit.need(t.get('calm') is None and not soothed, 'Cách dỗ bé sai.')
        # Care loop fields (tasks saved before it have none of them).
        h, reg = t.get('health'), t.get('regular')
        kit.need(h is None or (type(h) is int and 0 <= h <= 100), 'Sức khỏe tóc sai.')
        kit.need(reg is None or (type(reg) is int and 0 <= reg <= TRUST_MAX), 'Thẻ khách quen sai.')
        kit.need(t.get('tools') in (None, 'clean', 'dirty') and t.get('memo') in (None, 'same', 'drift'), 'Trạng thái salon sai.')
        kit.need(type(t.get('advised', False)) is bool, 'Trạng thái salon sai.')
        kit.need(not t.get('advised') or (h is not None and h < WEAK and 'treatment' not in t['needs']['services']),
                 'Phục hồi khuyên thêm chỉ dành cho tóc yếu.')
        ids(t.get('booked', []), APPT_KINDS, 'Lịch hẹn sai.')
    else:
        kit.need(not t.get('advised') and not t.get('booked') and t.get('tools') is None, 'Trạng thái salon sai.')
    kit.need(isinstance(t['results'], dict) and all(k in CHEM for k in t['results']), 'Kết quả màu sai.')
    for kind, r in t['results'].items():
        kit.need(isinstance(r, dict) and r.get('zone') in ZONES_T and type(r.get('ok')) is bool and kind in t['done'], 'Kết quả màu sai.')
        kit.need(isinstance(r.get('secs'), (int, float)) and type(r['secs']) is not bool and 0 <= r['secs'] <= 10**6, 'Thời gian ủ sai.')
        kit.need(r.get('dev') in DEVS and (r.get('shade') in DYE_INDEX or r.get('shade') in TONER_INDEX or r.get('shade') == 'bleach'), 'Kết quả màu sai.')
        _check_mix(dict(r, kind=kind))
    cut = t['cut']
    kit.need(isinstance(cut, dict) and set(cut) == set(_empty_cut()), 'Dữ liệu cắt sai.')
    kit.need(isinstance(cut['steps'], list) and len(cut['steps']) <= CUT_LOG and all(x in CUT_STEPS for x in cut['steps']), 'Các bước cắt sai.')
    kit.integer(cut['removed'], 0, 160)
    kit.need(type(cut['short']) is bool and type(cut['done']) is bool and cut['done'] == ('cut' in t['done']), 'Trạng thái cắt sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.mark_legacy(c, ID)
    for k in ('served', 'dumped', 'sanitize_day', 'mixes', 'rush_on_time', 'kids_calm', 'day_served'):
        kit.integer(d.get(k), 0, 10**9)
    people = [kit.npc_id(ID, i) for i in range(len(PEOPLE))]
    for book, msg in (('patch_log', 'Sổ thử dị ứng'), ('allergy', 'Sổ dị ứng')):
        log = d.get(book)
        kit.need(isinstance(log, dict) and len(log) <= len(PEOPLE), msg + ' sai.')
        for npc, day in log.items():
            kit.need(npc in people, msg + ' có khách lạ.')
            kit.integer(day, 1, 10**7)
    kit.need(d['today'] is None or (isinstance(d['today'], dict) and d['today'].get('id') in TODAY_INDEX), 'Chuyện hôm nay sai.')
    kit.desk_validate(d['desk'], DESK)
    _validate_care(d, people)


def _day(v, msg: str) -> int:
    kit.need(type(v) is int, msg)
    return kit.integer(v, 0, 10 ** 7)


def _validate_care(d: dict, people: list) -> None:
    kit.integer(d['clean'], 0, CLEAN_SETS)
    kit.integer(d['appt_seq'], 0, 10 ** 9)
    kit.integer(d['appts_done'], 0, 10 ** 9)
    cards = d['cards']
    kit.need(isinstance(cards, dict) and len(cards) <= len(PEOPLE), 'Thẻ khách sai.')
    for npc, x in cards.items():
        kit.need(npc in people and isinstance(x, dict) and set(x) == set(CARD_KEYS), 'Thẻ khách sai.')
        kit.need(type(x['visits']) is int and 1 <= x['visits'] <= 10 ** 6, 'Số lần ghé sai.')
        kit.need(_day(x['first'], 'Ngày ghé sai.') <= _day(x['last'], 'Ngày ghé sai.'), 'Ngày ghé sai.')
        kit.need(type(x['trust']) is int and 0 <= x['trust'] <= TRUST_MAX, 'Độ thân thiết sai.')
        kit.need(type(x['health']) is int and 0 <= x['health'] <= 100, 'Sức khỏe tóc sai.')
        kit.need(x['hist'] is None or x['hist'] in HIST, 'Lịch sử tóc sai.')
        kit.need(isinstance(x['services'], list) and len(set(x['services'])) == len(x['services']) and all(v in SERVICE_IDS for v in x['services']),
                 'Dịch vụ lần trước sai.')
        kit.need(type(x['stars']) is int and 0 <= x['stars'] <= 5 and type(x['patch_file']) is bool, 'Thẻ khách sai.')
        f = x['formula']
        if f is not None:
            kit.need(isinstance(f, dict) and set(f) == set(FORMULA_KEYS), 'Công thức màu sai.')
            kit.need(f['shade'] in DYE_INDEX and f['dev'] in DEVS and type(f['dev']) is int and f['ratio'] in RATIOS, 'Công thức màu sai.')
            kit.need(type(f['pa']) is int and f['pa'] in MIX_PARTS and type(f['pb']) is int, 'Công thức màu sai.')
            kit.need(f['pb'] == 0 if f['b'] is None else (f['b'] in DYE_INDEX and f['b'] != f['shade'] and f['pb'] in MIX_PARTS), 'Công thức màu sai.')
            kit.need(type(f['level']) is int and 1 <= f['level'] <= 10 and f['band'] in BAND_IDS, 'Công thức màu sai.')
            kit.need(type(f['hit']) is bool and f['zone'] in ZONES_T, 'Công thức màu sai.')
            _day(f['day'], 'Công thức màu sai.')
        cut = x['cut']
        if cut is not None:
            kit.need(isinstance(cut, dict) and set(cut) == {'removed', 'short', 'day'} and type(cut['short']) is bool, 'Lần cắt trước sai.')
            kit.need(type(cut['removed']) is int and 0 <= cut['removed'] <= 160, 'Lần cắt trước sai.')
            _day(cut['day'], 'Lần cắt trước sai.')
    appts = d['appts']
    kit.need(isinstance(appts, list) and len(appts) <= APPT_MAX, 'Sổ hẹn sai.')
    seen = set()
    for a in appts:
        kit.need(isinstance(a, dict) and set(a) == {'id', 'npc', 'kind', 'due', 'booked', 'state', 'stars'}, 'Lịch hẹn sai.')
        kit.need(isinstance(a['id'], str) and a['id'][:1] == 'H' and a['id'][1:].isdigit() and len(a['id']) <= 12 and a['id'] not in seen, 'Lịch hẹn sai.')
        seen.add(a['id'])
        kit.need(a['npc'] in people and a['kind'] in APPT_KINDS and a['state'] in APPT_STATES, 'Lịch hẹn sai.')
        kit.need(_day(a['booked'], 'Lịch hẹn sai.') <= _day(a['due'], 'Lịch hẹn sai.'), 'Lịch hẹn sai.')
        kit.need(type(a['stars']) is int and 0 <= a['stars'] <= 5, 'Lịch hẹn sai.')
        kit.need(a['npc'] in cards, 'Lịch hẹn của khách chưa có thẻ.')


def on_task(s: dict, c: dict, t: dict) -> None:
    _data(c)
    if t.get('career') != ID or not t.get('gen'):
        return
    tier = kit.tier(t['day'])
    start = 100 - 4 * tier - (8 if _today(c)['id'] == 'walkin' else 0) - (6 if _case(t) in ('bride', 'walkin') else 0)
    t['patience'] = max(60, min(t.get('patience', 100), start))
    if t['status'] == 'new' and 'health' not in t:
        # The client card: a regular is recognised, arrives more patient, with the hair health the card remembers.
        card = _data(c)['cards'].get(t['npc'])
        t.update(regular=card['trust'] if card else None, health=_arrival_health(c, t), tools=None, memo=None, advised=False, booked=[])
        if card:
            t['patience'] = min(100, t['patience'] + TRUST_PATIENCE * card['trust'])


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    mod = today(c['day'])
    d['today'] = dict(id=mod['id'], day=c['day'])
    kit.log(s, c, 'today', f'{mod["emoji"]} Hôm nay: {mod["title"]} — {mod["text"]}')
    # A new morning: fresh disinfectant, so every tool set needs soaking again.
    d['clean'] = 0
    kit.log(s, c, 'salon', f'🧴 Đầu ngày thay dung dịch khử khuẩn: 0/{CLEAN_SETS} bộ lược kéo sạch — ngâm dụng cụ trước khi nhận khách.')
    due, lapsed = [], []
    for a in d['appts']:
        if a['state'] != 'open':
            continue
        if c['day'] > a['due'] + APPT_KEEP:
            a['state'] = 'lapsed'
            card = d['cards'].get(a['npc'])
            if card and card['trust']:
                card['trust'] -= 1
            lapsed.append(f'{_npc_name(a["npc"])} ({APPTS[a["kind"]]["label"].lower()})')
        elif a['due'] <= c['day']:
            due.append(f'{_npc_name(a["npc"])} — {APPTS[a["kind"]]["label"].lower()}')
    if due:
        kit.log(s, c, 'salon', '📅 Hôm nay có hẹn: ' + '; '.join(due) + '. Xem Sổ hẹn ở bàn làm việc.')
    if lapsed:
        kit.log(s, c, 'salon', '📅 Lỡ hẹn quá 2 ngày, khách đã đi tiệm khác: ' + ', '.join(lapsed) + '. Thẻ khách bớt thân một bậc.')
    kit.desk_start(s, c, ID, d['desk'], DESK, mod['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    note = kit.desk_close(s, c, ID, d['desk'], DESK, _desk_hook)
    lines = [f'Khách đã làm tóc hôm nay: {d["day_served"]}.']
    if d['mixes']:
        lines.append(f'Bát pha hai tuýp trúng màu (tính từ đầu): {d["mixes"]}.')
    if d['allergy']:
        lines.append(f'Sổ dị ứng đang ghi {len(d["allergy"])} khách không được nhuộm.')
    if note:
        lines.append(note)
    waiting = [a for a in d['appts'] if a['state'] == 'open' and a['due'] <= c['day']]
    tomorrow = [a for a in d['appts'] if a['state'] == 'open' and a['due'] == c['day'] + 1]
    if d['appts_done']:
        lines.append(f'Lịch hẹn đã phục vụ (tính từ đầu): {d["appts_done"]}.')
    if waiting:
        last = [a for a in waiting if c['day'] >= a['due'] + APPT_KEEP]
        lines.append(f'Còn {len(waiting)} khách hẹn chưa làm' + (f' — {len(last)} khách hết hạn chờ hôm nay.' if last else ' (vẫn chờ được thêm ít hôm).'))
    if tomorrow:
        lines.append('Ngày mai có hẹn: ' + ', '.join(f'{_npc_name(a["npc"])} ({APPTS[a["kind"]]["label"].lower()})' for a in tomorrow) + '.')
    if d['cards']:
        lines.append(f'Sổ khách quen: {len(d["cards"])} thẻ.')
    nxt = today(c['day'] + 1)
    lines.append(f'Dự báo ngày mai: {nxt["emoji"]} {nxt["title"]} — {nxt["text"]}')
    d['day_served'] = 0
    return dict(lines=lines)


# ------------------------------------------------------------------ staff & hints
def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e.get('role')
    if role == 'cut':
        d = _data(c)
        if d['sanitize_day'] == c['day'] and d['clean'] < CLEAN_SETS:
            # Tops up the jar you prepared this morning; the morning change of disinfectant is still yours.
            d['clean'] += 1
            return f'Đã quét tóc, ngâm khử khuẩn thêm một bộ lược kéo ({d["clean"]}/{CLEAN_SETS} bộ sạch).'
        return 'Đã quét tóc, sát khuẩn kéo, lược và tông đơ giữa hai lượt khách.'
    if not t or t['career'] != ID or not t['known']:
        return 'Đã gấp khăn, lau gương và châm nước ấm cho bồn gội.' if role == 'assist' else None
    plan = t['plan']
    if role == 'assist' and plan and not t['washed'] and t['timer'] is None:
        if [x for x in plan['services'] if x in ('color', 'bleach') and x not in t['done']]:
            return 'Đã chuẩn bị khăn choàng, kem bảo vệ viền tóc; chờ bạn thoa thuốc trên tóc khô.'
        if all(kit.stock(c, x) for x in ('shampoo', 'conditioner', 'towel')):
            t['cost'] += kit.take(c, 'shampoo', 1) + kit.take(c, 'conditioner', 1) + kit.take(c, 'towel', 1)
            t['washed'] = True
            return 'Đã gội đầu, massage nhẹ cho khách đúng phương án đã chốt.'
    if role == 'color':
        if t['bowl'] and not t['bowl']['ok']:
            return 'Linh xem bát: công thức chưa khớp bảng pha, nên đổ bát và pha lại.'
        low = next((x['name'] for x in ITEMS if x['group'] == 'ingredient' and kit.stock(c, x['id']) <= 1), None)
        if low:
            return f'Linh kiểm tủ màu: {low} sắp hết, nhớ nhập thêm.'
        return 'Linh xếp tuýp theo số tông và kiểm hạn dùng oxy.'
    return None


def hint(c: dict, t: dict) -> str:
    if not t['known']:
        return 'Mời khách ngồi, nghe mong muốn và xem ảnh mẫu trước.'
    tip = {'photo': ' Ảnh có filter: soi ảnh gốc trước khi hứa màu.',
           'react': ' Kết quả thử dị ứng từ năm ngoái ở tiệm khác không còn giá trị — thử lại.',
           'kid': ' Bé khó ngồi yên: nghe bố kể thói quen của bé rồi dỗ đúng cách trước khi cầm kéo.',
           'bride': ' Cô dâu cần kịp giờ: phục hồi trước, búi chắc, đừng thao tác thừa.',
           'walkin': ' Khách vội: hỏi độ dài rồi cắt gọn, ít thao tác mà trúng.',
           'grey': ' Tóc bạc nhiều: một nửa bát là tuýp nền tự nhiên, oxy 20 vol.',
           'fix': ' Nền tóc ánh cam: xem thân tóc, pha lạnh hơn để bù phần ấm.'}.get(_case(t) or '', '')
    if t.get('regular') is not None:
        tip += ' Khách quen: lật thẻ khách xem công thức màu, sức khỏe tóc và lần cắt trước.'
    if t.get('gen') and _weak(t):
        tip += ' Tóc yếu: khuyên phục hồi là thật lòng, không phải ép mua.'
    if not t['plan']:
        return 'Hỏi lịch sử hóa chất, hồ sơ thử dị ứng, độ dài; xem chân – thân – ngọn – da đầu rồi mới chốt. Ảnh mẫu có thể cần nhiều buổi.' + tip
    return 'Pha đúng bảng luật → thoa → xả trong vùng xanh → gội → cắt theo trình tự → phục hồi, sấy → tư vấn sản phẩm vừa túi tiền.' + tip


def content() -> dict:
    return dict(services=SERVICES, prices=PRICES, levels=LEVELS, dyes=DYES, toners=TONERS, devs=DEVS, ratios=RATIOS,
                windows=WINDOWS, cut_steps=CUT_STEPS, finishes=FINISHES, topics=TOPICS, zones=ZONES,
                retail=[dict(id=x['id'], name=x['name'], emoji=x['emoji'], price=x['price'], unlock=x.get('unlock', 1)) for x in ITEMS if x['group'] == 'goods'],
                rules=RULES, disclaimer=DISCLAIMER,
                bands=BANDS, tone=TONE, mix_parts=list(MIX_PARTS), lift={str(k): v for k, v in LIFT.items()}, kind_ratio=KIND_RATIO,
                cases=CASES, calm_tools=CALM_TOOLS,
                care=dict(appts={k: dict(v, id=k) for k, v in APPTS.items()}, keep=APPT_KEEP, clean_sets=CLEAN_SETS, weak=WEAK,
                          bleach_stop=BLEACH_STOP, trust_names=list(TRUST_NAMES), trim_cap=list(TRIM_CAP),
                          health_words=[list(x) for x in HEALTH_WORDS]),
                today=[dict(id=x['id'], title=x['title'], emoji=x['emoji'], text=x['text']) for x in TODAY])


# ------------------------------------------------------------------ surprises at the reception desk
DESK = [
    dict(id='trio', title='Ba bạn học sinh xin tết tóc chụp kỷ yếu', emoji='🎓', npc=1, min_day=2, tone='gentle', weight=2,
         text='Ba bạn học sinh ùa vào: “Tiệm tết tóc giùm tụi em được không? Nửa tiếng nữa lớp chụp kỷ yếu rồi!” Ghế nào cũng đang có khách.',
         options=[dict(id='squeeze', label='Nhận luôn, giao Tí tết nhanh ngay bây giờ', hint='+18 xu · khách đang ngồi phải chờ',
                       luck=dict(p=0.6, win=dict(effects=dict(money=18, review=[5, 'Tiệm tết tóc siêu nhanh, ảnh kỷ yếu xinh xỉu 📸']), good=True,
                                                 outcome='Tí tết ba kiểu gọn gàng kịp giờ chụp. Ba bạn chụp ảnh check-in ngay cửa tiệm.'),
                                 lose=dict(effects=dict(money=18, patience=-15), good=None,
                                           outcome='Tết kịp, nhưng khách trên ghế phải chờ thêm một lúc, mặt ai cũng nặng.'))),
                  dict(id='slot', label='Hẹn 15 phút nữa, tết kiểu đơn giản', hint='+10 xu · ít ảnh hưởng', good=True,
                       effects=dict(money=10, patience=-5),
                       outcome='Ba bạn chờ chút rồi được tết hai bím gọn. Khách trong tiệm gần như không phải chờ.'),
                  dict(id='refuse', label='Xin lỗi, hôm nay kín ghế', hint='Không tốn gì', good=None,
                       outcome='Ba bạn chạy sang tiệm khác. Khách trong tiệm vẫn được làm đúng giờ.')],
         default='refuse'),
    dict(id='price_review', title='Đánh giá 2★: “Báo 60 mà tính 95”', emoji='⭐', npc=0, min_day=2, tone='tense', weight=2, no_mark='price_board',
         text='Trang của tiệm hiện đánh giá 2★: “Hỏi nhuộm bao nhiêu thì bảo 60, lúc tính tiền thành 95 vì tóc dài với phục hồi. Không ai nói trước!”',
         options=[dict(id='reply', label='Trả lời công khai, xin lỗi, dán bảng giá theo độ dài tóc', hint='−5 xu in bảng', good=True,
                       effects=dict(money=-5, mark='price_board',
                                    review=[4, 'Tiệm trả lời đàng hoàng, giờ có bảng giá theo độ dài tóc rõ ràng. Sửa 2★ thành 4★.']),
                       outcome='Bảng giá mới dán ngay quầy: giá theo độ dài tóc, phụ phí ghi rõ. Từ nay báo giá là trọn gói.'),
                  dict(id='refund', label='Nhắn riêng, hoàn 15 xu phần chênh', hint='−15 xu', good=None,
                       effects=dict(money=-15, review=[4, 'Tiệm nhắn xin lỗi và hoàn phần chênh. Cũng được.']),
                       outcome='Khách nhận tiền và sửa đánh giá, nhưng quầy vẫn chưa có bảng giá rõ ràng.'),
                  dict(id='argue', label='Đáp trả: “Giá ghi trên menu rồi mà”', hint='Hên xui', good=False,
                       luck=dict(p=0.3, win=dict(outcome='Vài khách quen vào bênh tiệm, chuyện lắng xuống.', good=None),
                                 lose=dict(effects=dict(review=[1, 'Hỏi giá mập mờ, bị đánh giá còn lên mạng cãi khách. Né!']), good=False,
                                           outcome='Cuộc cãi nhau bị chụp màn hình chia sẻ khắp nhóm khu phố.'))),
                  dict(id='ignore', label='Kệ, lát tính', hint='Không tốn gì', good=None,
                       outcome='Đánh giá 2★ nằm đó, ai mở trang tiệm cũng thấy.')],
         default='ignore'),
    dict(id='price_again', title='Khách cãi giá ở quầy', emoji='🧾', npc=4, min_day=4, tone='tense', no_mark='price_board',
         text='Bà Lựu đứng ở quầy: “Sao gội sấy tính thêm 15 xu? Lần trước đâu có tính!” Khách ngồi chờ nhìn sang.',
         options=[dict(id='board', label='Xin lỗi, bỏ phụ phí lần này, in bảng giá dán quầy', hint='−20 xu', good=True,
                       effects=dict(money=-20, mark='price_board'), outcome='Bà Lựu gật gù. Bảng giá mới dán quầy, từ nay ai cũng thấy trước.'),
                  dict(id='explain', label='Giải thích miệng, vẫn tính đủ', hint='Hên xui', good=None,
                       luck=dict(p=0.5, win=dict(outcome='Bà Lựu nghe ra, trả đủ.', good=None),
                                 lose=dict(effects=dict(patience=-10, review=[2, 'Tiệm tính thêm tiền mà không nói trước.']), good=False,
                                           outcome='Bà Lựu trả tiền mà càu nhàu cả buổi; khách chờ cũng ngại.'))),
                  dict(id='insist', label='“Giá vậy rồi, bà trả đi”', hint='Nhanh gọn', good=False,
                       effects=dict(patience=-15, review=[1, 'Thái độ tính tiền khó chịu. Không quay lại.']),
                       outcome='Bà Lựu đập tiền xuống quầy rồi về. Khách chờ im phăng phắc.')],
         default='explain'),
    dict(id='staff_fight', title='Linh và Khoa cãi nhau giữa ca', emoji='💢', npc=0, min_day=3, tone='tense', weight=2, no_mark='grudge',
         text='Linh (thợ màu) và Khoa (thợ cắt) to tiếng ở góc tiệm: ai được dùng ghế cạnh cửa sổ, tiền tip hôm qua chia sao. Khách đang nghe.',
         options=[dict(id='mediate', label='Mời hai người ra sau: chia lịch ghế theo giờ, tip bỏ hộp chung', hint='Khách chờ thêm chút', good=True,
                       effects=dict(patience=-6, xp=6),
                       outcome='Năm phút sau hai người quay lại, mỗi người một khung giờ ghế cửa sổ. Không khí dịu hẳn.'),
                  dict(id='side', label='Bênh Linh vì làm lâu năm hơn', hint='Nhanh', good=False, effects=dict(mark='grudge'),
                       outcome='Khoa im lặng làm tiếp, nhưng mặt lạnh tanh cả buổi.'),
                  dict(id='ignore', label='Kệ, để hai người tự giải quyết', hint='Không tốn gì', good=False,
                       effects=dict(patience=-10, mark='grudge'), outcome='Tiếng cãi nhau kéo dài, khách trên ghế nhìn nhau ngại ngùng.')],
         default='ignore'),
    dict(id='quit', title='Khoa đòi nghỉ ngang', emoji='🚪', npc=0, min_day=3, tone='tense', need_mark='grudge', weight=3,
         text='Khoa tháo tạp dề: “Làm ở đây không ai công bằng với em. Em nghỉ!” Còn hai khách hẹn cắt chiều nay.',
         options=[dict(id='talk', label='Ngồi nói chuyện thẳng, xin lỗi, chia lại lịch ghế và tip', hint='−5 xu', good=True,
                       effects=dict(money=-5, unmark='grudge'),
                       outcome='Khoa nguôi, buộc lại tạp dề. Lịch ghế và hộp tip chung được dán lên tường.'),
                  dict(id='raise', label='Tăng tiền ca giữ người, không nhắc chuyện ghế', hint='−15 xu', good=None,
                       effects=dict(money=-15, unmark='grudge'), outcome='Khoa ở lại vì tiền, nhưng chuyện ghế vẫn chưa ai giải quyết.'),
                  dict(id='let_go', label='Để Khoa về', hint='Khách hẹn cắt phải chờ', good=False,
                       effects=dict(patience=-20, unmark='grudge', review=[2, 'Tới giờ hẹn cắt thì thợ nghỉ ngang, chờ mãi.']),
                       outcome='Khoa về. Khách hẹn cắt phải chờ tiệm xoay xở.')],
         default='let_go'),
    dict(id='rep_deal', title='Đại lý chào lô thuốc nhuộm giá mềm', emoji='📦', npc=15, min_day=2, tone='gentle', weight=2,
         text='Chị Bích (đại lý) mở thùng: “Tuýp 6.1 với 7.3 hàng chính hãng, có hóa đơn, còn hai tháng hạn. Sáu tuýp chị tính 18 xu.”',
         options=[dict(id='buy', label='Lấy 6 tuýp (3 tuýp 6.1, 3 tuýp 7.3)', hint='−18 xu', good=True,
                       effects=dict(money=-18, stock=dict(dye_6_1=3, dye_7_3=3)),
                       outcome='Tủ màu đầy thêm hai ngăn hay dùng nhất — pha bát ấm, bát lạnh đều dư dả.'),
                  dict(id='haggle', label='Trả 12 xu', hint='Hên xui',
                       luck=dict(p=0.5, win=dict(effects=dict(money=-12, stock=dict(dye_6_1=3, dye_7_3=3)), good=True,
                                                 outcome='Chị Bích cười: “Thôi lấy đi, mối quen mà.”'),
                                 lose=dict(outcome='Chị Bích lắc đầu, chở thùng hàng sang tiệm bên.', good=None))),
                  dict(id='skip', label='Thôi, tủ còn đủ', hint='Không tốn gì', good=None, outcome='Chị Bích hẹn tuần sau ghé.')],
         default='skip'),
    dict(id='no_label', title='Dầu gội xách tay không nhãn phụ', emoji='🕶️', npc=15, min_day=3, tone='tense', no_mark='no_label',
         text='Một người lạ chào hàng: “Dầu gội giữ màu xách tay, không nhãn tiếng Việt, không hóa đơn, giá một nửa. Bán lại lời gấp đôi.”',
         options=[dict(id='take', label='Lấy 3 chai bán lại', hint='−10 xu · không giấy tờ', good=False,
                       effects=dict(money=-10, stock=dict(rt_colorsafe=3), mark='no_label'),
                       outcome='Ba chai dầu gội lên kệ. Trong sổ nhập hàng có một dòng không hóa đơn…'),
                  dict(id='refuse', label='Chỉ bán hàng có nhãn, có hóa đơn', hint='An toàn', good=True, effects=dict(xp=4),
                       outcome='Người lạ bỏ đi. Kệ hàng của tiệm vẫn rõ nguồn gốc.')],
         default='refuse'),
    dict(id='label_check', title='Đoàn kiểm tra hàng mỹ phẩm', emoji='🚨', npc=16, min_day=3, tone='tense', need_mark='no_label', weight=3,
         text='Đoàn kiểm tra lật chai dầu gội trên kệ: “Hàng này nhãn phụ đâu? Hóa đơn nhập đâu?”',
         options=[dict(id='surrender', label='Nhận lỗi, giao nộp hàng, nộp phạt nhẹ', hint='−15 xu · mất 3 chai', good=True,
                       effects=dict(money=-15, stock=dict(rt_colorsafe=-3), unmark='no_label'),
                       outcome='Đoàn ghi nhận thành khẩn, phạt nhẹ. Kệ hàng sạch trở lại.'),
                  dict(id='argue', label='Nói là hàng khách gửi bán', hint='Hên xui', good=False,
                       luck=dict(p=0.25, win=dict(effects=dict(unmark='no_label'), outcome='Đoàn tạm tin, dặn bổ sung giấy tờ trong tuần.', good=None),
                                 lose=dict(effects=dict(money=-40, unmark='no_label',
                                                        review=[1, 'Salon bị phạt vì bán mỹ phẩm không rõ nguồn gốc.']),
                                           outcome='Nói dối bị phát hiện: phạt 40 xu, chuyện lan khắp phố.', good=False)))],
         default='surrender'),
    dict(id='outage', title='Cúp điện: máy sấy tắt ngấm', emoji='🔌', npc=4, min_day=2, tone='tense', at='any',
         text='Phụt một cái, cả dãy phố mất điện. Máy sấy, máy hấp tắt ngấm; khách tóc còn ướt nhìn ra cửa.',
         options=[dict(id='generator', label='Thuê máy phát nhà bên', hint='−8 xu', good=True, effects=dict(money=-8),
                       outcome='Máy phát nổ giòn, máy sấy chạy lại. Khách không phải chờ lâu.'),
                  dict(id='towel', label='Lau khăn, quạt tay, xin lỗi khách', hint='Khách sốt ruột', good=None, effects=dict(patience=-15),
                       outcome='Nửa tiếng sau mới có điện. Khách ngồi quạt tay, ai cũng sốt ruột.')],
         default='towel'),
    dict(id='health', title='Đoàn y tế phường kiểm tra vệ sinh', emoji='🧴', npc=16, min_day=2, tone='tense', weight=2,
         text='Cô Tám (y tế phường) chìa thẻ: “Cho cô xem sổ khử khuẩn dụng cụ hôm nay và khăn đang dùng.”',
         options=[dict(id='show', label='Mở sổ vệ sinh hôm nay ra', hint='Đạt nếu hôm nay đã khử khuẩn', effects=dict(inspect=1), good=None,
                       outcome='Cô Tám lật sổ vệ sinh.'),
                  dict(id='clean', label='Xin 10 phút khử khuẩn ngay trước mặt đoàn', hint='Khách chờ thêm', good=True,
                       effects=dict(sanitize=1, patience=-10),
                       outcome='Kéo, lược, tông đơ ngâm khử khuẩn ngay tại chỗ; khăn bẩn đem giặt. Cô Tám ký “đạt”.'),
                  dict(id='coffee', label='Mời đoàn “ly cà phê” cho qua', hint='Hên xui', good=False,
                       luck=dict(p=0.2, win=dict(outcome='Đoàn cười trừ, dặn lần sau làm đúng sổ.', good=None),
                                 lose=dict(effects=dict(money=-30, review=[1, 'Salon định “bồi dưỡng” đoàn kiểm tra thay vì khử khuẩn dụng cụ. Ghê!']),
                                           outcome='Đoàn lập biên bản: phạt 30 xu vì không hợp tác.', good=False)))],
         default='show'),
    dict(id='kol', title='Người nổi tiếng xin làm tóc miễn phí', emoji='🤳', npc=11, min_day=3, tone='gentle',
         text='Một bạn có trăm nghìn người theo dõi nhắn: “Tiệm làm tóc miễn phí cho mình, mình quay clip giới thiệu nha. Ok là mình qua liền.”',
         options=[dict(id='deal', label='Giảm 30%, clip ghi rõ “hợp tác có trả phí”', hint='+10 xu · minh bạch', good=True,
                       effects=dict(money=10, xp=4), outcome='Bạn ấy đồng ý, clip ghi rõ hợp tác. Người xem tin tưởng hơn.'),
                  dict(id='free', label='Nhận làm miễn phí', hint='Tốn 1 keratin · hên xui', good=None, effects=dict(stock=dict(keratin=-1)),
                       luck=dict(p=0.5, win=dict(effects=dict(xp=10, review=[5, 'Clip giới thiệu salon được chia sẻ nghìn lượt: “tóc mềm, thợ tư vấn có tâm”.']),
                                                 good=True, outcome='Clip lên xu hướng, cả tuần có khách nhắc tên tiệm.'),
                                 lose=dict(effects=dict(review=[3, 'Clip về salon: “cũng được, không có gì đặc biệt”.']), good=None,
                                           outcome='Clip ít lượt xem, còn tiệm mất một buổi hấp.'))),
                  dict(id='refuse', label='Cảm ơn, tiệm không đổi dịch vụ lấy lời khen', hint='Không tốn gì', good=None,
                       outcome='Bạn ấy thả tim rồi đi tìm tiệm khác.')],
         default='refuse'),
    dict(id='recall', title='Hãng báo thu hồi lô oxy 20 vol', emoji='📣', npc=15, min_day=3, tone='tense', no_mark='recall',
         text='Chị Bích gọi gấp: “Lô oxy 20 vol giao tuần trước lỗi nồng độ, hãng thu hồi. Gửi trả thì hãng hoàn tiền.”',
         options=[dict(id='pull', label='Rút 3 chai khỏi kệ, gửi trả hãng', hint='+6 xu hoàn · bớt oxy 20', good=True,
                       effects=dict(stock=dict(dev_20=-3), money=6),
                       outcome='Ba chai oxy lỗi được gửi trả, hãng hoàn tiền. Kệ oxy chỉ còn hàng an toàn.'),
                  dict(id='keep', label='Dùng nốt, chắc không sao', hint='Tiết kiệm', good=False, effects=dict(mark='recall'),
                       outcome='Ba chai oxy lỗi vẫn nằm trên kệ…')],
         default='keep'),
    dict(id='itch', title='Khách quay lại: da đầu rát đỏ', emoji='😣', npc=2, min_day=3, tone='tense', need_mark='recall', weight=3,
         text='Cô Ngọc quay lại, vạch tóc: “Hôm qua nhuộm xong về da đầu rát đỏ luôn con ơi.” Mấy chai oxy bị thu hồi vẫn nằm trên kệ.',
         options=[dict(id='care', label='Xin lỗi, xả dịu, trả tiền khám, bỏ lô oxy lỗi', hint='−20 xu', good=True,
                       effects=dict(money=-20, stock=dict(dev_20=-3), unmark='recall',
                                    review=[4, 'Có sự cố nhưng tiệm nhận lỗi, lo cho cô tới nơi tới chốn.']),
                       outcome='Cô Ngọc dịu lại, còn khen tiệm thật thà. Lô oxy lỗi bị bỏ đi.'),
                  dict(id='deny', label='“Chắc tại cô dị ứng thôi”', hint='Không tốn gì', good=False,
                       effects=dict(unmark='recall', review=[1, 'Nhuộm xong rát da đầu, tiệm còn đổ tại mình. Cẩn thận!']),
                       outcome='Cô Ngọc bỏ về, kể với cả hội dưỡng sinh.')],
         default='deny'),
    dict(id='leak', title='Mái dột ngay trên bồn gội', emoji='💧', npc=4, min_day=2, tone='tense', mods=('rain',), at='any',
         text='Mưa lớn, nước nhỏ tong tong xuống bồn gội; chồng khăn sạch ướt một góc.',
         options=[dict(id='fix', label='Gọi thợ dán mái ngay', hint='−10 xu', good=True, effects=dict(money=-10),
                       outcome='Thợ trèo lên dán mái trong mười lăm phút. Bồn gội khô ráo trở lại.'),
                  dict(id='bucket', label='Đặt xô hứng, làm tiếp', hint='Mất 3 khăn · khách chờ', good=None,
                       effects=dict(stock=dict(towel=-3), patience=-8),
                       outcome='Xô hứng nước kêu tong tong suốt buổi, ba chiếc khăn phải đem giặt.')],
         default='bucket'),
    dict(id='ring', title='Nhẫn bỏ quên ở bồn gội', emoji='💍', npc=9, min_day=2, tone='gentle',
         text='Nhung (phụ gội) cầm chiếc nhẫn vàng tìm thấy cạnh bồn gội: “Của khách hồi sáng thì phải.”',
         options=[dict(id='call', label='Tra sổ lịch hẹn, gọi báo khách tới lấy', hint='Nhanh, rõ ràng', good=True,
                       effects=dict(xp=6, review=[5, 'Bỏ quên nhẫn ở tiệm, tiệm gọi báo liền, giữ kỹ giùm. Cảm ơn nhiều!']),
                       outcome='Khách chạy tới, rưng rưng: nhẫn đính hôn đó. Cả tiệm vui lây.'),
                  dict(id='box', label='Cất hộp đồ thất lạc, chờ ai hỏi', hint='Không tốn gì', good=None,
                       outcome='Chiếc nhẫn nằm trong hộp đồ thất lạc, dán nhãn ngày giờ.')],
         default='box'),
    dict(id='ti_try', title='Tí xin cắt thử cho khách quen', emoji='✂️', npc=6, min_day=3, tone='gentle',
         text='Tí học việc năn nỉ: “Cho em tỉa mái cho bé Su nha, em tập trên đầu mẫu cả tuần rồi!” Mẹ bé Su nhìn sang.',
         options=[dict(id='guide', label='Cho Tí làm, mình đứng kèm từng đường kéo', hint='Khách chờ thêm chút', good=True,
                       effects=dict(patience=-6, xp=8), outcome='Tí tỉa run run nhưng đều. Mẹ bé Su khen, Tí cười tít mắt.'),
                  dict(id='alone', label='Để Tí tự làm cho quen tay', hint='Hên xui', good=None,
                       luck=dict(p=0.5, win=dict(effects=dict(review=[5, 'Bạn học việc tỉa mái cho bé khéo ghê!']), good=True,
                                                 outcome='Tí tỉa gọn gàng, tự tin hẳn.'),
                                 lose=dict(effects=dict(money=-10, review=[2, 'Mái bé bị lệch, tiệm phải sửa lại và giảm tiền.']), good=False,
                                           outcome='Mái lệch một bên, phải sửa lại và giảm 10 xu.'))),
                  dict(id='later', label='Hẹn Tí tập trên đầu mẫu sau giờ', hint='An toàn', good=None,
                       outcome='Tí hơi xịu nhưng gật đầu, tối ở lại tập thêm.')],
         default='later'),
]
DESK_INDEX = {x['id']: x for x in DESK}


# ------------------------------------------------------------------ situations
SITUATIONS = [
    dict(id='SL-S01', title='Ảnh idol cần ba buổi', npc=1, tone='gentle', min_day=1,
         opening='Hà Mi chìa điện thoại: “Tiệm làm em y chang ảnh này nha, tối nay em đi fan meeting!” Ảnh là tóc bạch kim khói, còn tóc em đen nhánh vì thuốc hộp.',
         swap='Bạn là Hà Mi, sinh viên mê idol, đã để dành tiền cả tháng cho mái tóc trong ảnh.',
         facts=[dict(id='photo', title='Soi ảnh mẫu', source='Điện thoại của Mi', text='Ảnh đã qua bộ lọc và đèn sân khấu; tóc idol level 10 — đẹp nhưng không phải màu thật 100%.'),
                dict(id='hair', title='Xem thân tóc', source='Tay thợ', text='Thuốc nhuộm hộp màu đen phủ dày từ chân tới ngọn; tẩy một lần chỉ lên được khoảng level 6–7 ánh cam.'),
                dict(id='budget', title='Hỏi ngân sách & lịch', source='Hà Mi', text='Mi có 170 xu, cuối tháng mới có tiền tiêu vặt tiếp.')],
         options=[dict(id='plan3', label='Nói thật: cần 3 buổi cách nhau 2 tuần; hôm nay tẩy nhẹ + toner khói, tặng lịch chăm tóc giữa các buổi',
                       requires=['photo', 'hair'], quality='good', stars=5,
                       review='Thợ ở tiệm nói thật là phải 3 buổi, hơi tiếc nhưng tóc em vẫn mềm, màu khói hôm nay cũng xinh ✨',
                       outcome='Mi hơi xịu, nhưng tối đó màu khói nâu sáng vẫn lên hình đẹp. Mi đặt lịch buổi 2 ngay tại quầy.',
                       perspectives=[dict(who='Hà Mi', emoji='🎤', text='Tưởng bị từ chối, hóa ra có lộ trình rõ, em yên tâm hơn.'),
                                     dict(who='Linh (thợ màu)', emoji='🎨', text='Tẩy một lần vừa đủ, tóc còn sức cho buổi sau.'),
                                     dict(who='Chủ salon', emoji='💼', text='Mất khoản “làm liền” hôm nay, được một khách quay lại ba lần.')]),
                  dict(id='oneday', label='Chiều khách: tẩy hai lần liền trong hôm nay cho giống ảnh', quality='bad', stars=1,
                       review='Tóc em giờ như mì tôm nhúng nước, chải là gãy 😭 Red flag!',
                       outcome='Tóc lên vàng loang, ngọn gãy lả tả. Mi khóc ở ghế gội, tối không dám đi fan meeting.',
                       perspectives=[dict(who='Hà Mi', emoji='😭', text='Em muốn giống ảnh, chứ đâu muốn mất tóc.'),
                                     dict(who='Tí (học việc)', emoji='😰', text='Em nghe tóc kêu lạo xạo khi chải, sợ lắm.'),
                                     dict(who='Khách ghế bên', emoji='👀', text='Nhìn cảnh đó ai cũng ngại đặt lịch tẩy ở đây.')]),
                  dict(id='refuse', label='Từ chối luôn vì tóc nhuộm hộp khó làm', quality='ok',
                       outcome='Mi sang tiệm khác. Salon an toàn nhưng mất một cơ hội tư vấn đúng cách.',
                       perspectives=[dict(who='Hà Mi', emoji='😕', text='Tiệm không giải thích gì, em thấy bị đuổi khéo.'),
                                     dict(who='Chủ salon', emoji='🤔', text='Đúng là rủi ro, nhưng mình có thể đưa ra lộ trình mà.')])],
         lesson='Ảnh mẫu là đích đến, không phải lời hứa trong một buổi: nói thật số buổi và giữ tóc khỏe.'),
    dict(id='SL-S02', title='Khách không ưng kiểu cắt, đòi hoàn tiền', npc=0, tone='tense', min_day=2,
         opening='Chị Thảo quay lại quầy: “Em cắt ngắn quá, chị đi họp ai cũng hỏi. Hoàn tiền cho chị!”',
         swap='Bạn là khách vừa cắt tóc hôm qua, sáng nay soi gương thấy không giống mình mong.',
         facts=[dict(id='card', title='Phiếu tư vấn', source='Sổ salon', text='Phiếu ghi chị chọn “bớt 3 cm, ngang vai”, có chữ ký xác nhận trước khi cắt.'),
                dict(id='photo', title='Ảnh trước/sau', source='Máy tính bảng', text='Tóc chạm vai khi để thẳng, nhưng sấy phồng thì trông ngắn hơn khoảng 2 cm.'),
                dict(id='feel', title='Nghe chị kể', source='Chị Thảo', text='Đồng nghiệp trêu “tóc học sinh”, chị ngượng cả buổi họp.')],
         options=[dict(id='fix', label='Mời chị ngồi, lắng nghe; chỉnh miễn phí (tỉa mềm đuôi, chỉ cách sấy suôn) và tặng một buổi hấp dưỡng',
                       requires=['card', 'photo'], cost=10, quality='good', stars=5,
                       review='Salon nghe mình nói hết, chỉnh lại miễn phí và chỉ cách sấy. Giờ tóc vào nếp, đi họp tự tin rồi.',
                       outcome='Tỉa mềm đuôi và đổi cách sấy, tóc trông dài hơn. Chị Thảo về còn nhắn cảm ơn.',
                       perspectives=[dict(who='Chị Thảo', emoji='😌', text='Mình cần được nghe trước, chuyện tiền tính sau.'),
                                     dict(who='Khoa (thợ cắt)', emoji='✂️', text='Phiếu tư vấn giúp mình bình tĩnh: không cãi, chỉ sửa phần làm được.'),
                                     dict(who='Chủ salon', emoji='💼', text='Mất một buổi hấp, giữ một khách quen và một đánh giá tốt.')]),
                  dict(id='refund', label='Hoàn toàn bộ tiền cho nhanh, không hỏi thêm', cost=30, quality='ok', stars=3,
                       review='Được hoàn tiền nhưng tóc vẫn vậy. Thôi, coi như xong.',
                       outcome='Chị Thảo nhận tiền rồi về; chuyện mái tóc vẫn chưa được giải quyết.',
                       perspectives=[dict(who='Chị Thảo', emoji='😐', text='Tiền về rồi, nhưng tóc thì không dài lại.'),
                                     dict(who='Khoa (thợ cắt)', emoji='😔', text='Không ai hỏi em đã cắt theo phiếu thế nào.')]),
                  dict(id='argue', label='“Chị ký phiếu rồi mà, lỗi đâu phải tại tiệm”', requires=['card'], quality='bad', stars=1,
                       review='Đúng là chị ký, nhưng thái độ vậy thì chị không quay lại.',
                       outcome='Chị Thảo bỏ về, tối đăng bài nhắc tên salon.',
                       perspectives=[dict(who='Chị Thảo', emoji='😤', text='Chị không cãi chữ ký, chị cần được giúp.'),
                                     dict(who='Khách đang chờ', emoji='👀', text='Nghe cãi nhau ở quầy, mình cũng ngại.')])],
         lesson='Phiếu tư vấn để hiểu nhau, không phải để thắng cãi; sửa những gì còn sửa được.'),
    dict(id='SL-S03', title='Đòi tẩy ngay trên tóc nhuộm hộp', npc=5, tone='tense', min_day=3,
         opening='Chị Vy ngồi phịch xuống ghế: “Tẩy highlight luôn cho chị, chiều chị có hẹn!” Tóc chị đen bóng đều từ chân tới ngọn — kiểu thuốc hộp.',
         swap='Bạn là MC đang chạy show, chỉ có đúng một buổi chiều trống để làm tóc.',
         facts=[dict(id='ask', title='Hỏi lịch sử tóc', source='Chị Vy', text='Chị tự nhuộm đen bằng thuốc hộp 2 lần, lần gần nhất 3 tuần trước; không nhớ hộp ghi thành phần gì.'),
                dict(id='strand', title='Thử một lọn sau gáy', source='Bàn màu', text='Lọn thử nóng lên và bốc hơi nhẹ sau 3 phút — dấu hiệu thuốc hộp phản ứng với chất tẩy.'),
                dict(id='rule', title='Quy định salon', source='Sổ quy trình', text='Tóc nhuộm hộp: bắt buộc thử lọn; lọn phản ứng thì không tẩy trong ngày, hẹn phục hồi và tẩy màu chuyên dụng.')],
         options=[dict(id='stop', label='Dừng, cho chị xem lọn thử, giải thích và đề xuất lộ trình phục hồi rồi hẹn lại',
                       requires=['strand', 'rule'], quality='good', stars=4,
                       review='Tiệm không làm liền như chị muốn, nhưng cho xem tận mắt lọn tóc bốc hơi. Cảm ơn đã không liều.',
                       outcome='Chị Vy cằn nhằn nhưng đặt lịch phục hồi. Tóc an toàn.',
                       perspectives=[dict(who='Chị Vy', emoji='😒', text='Chị ghét chờ, nhưng thấy lọn tóc bốc hơi thì hết cãi.'),
                                     dict(who='Linh (thợ màu)', emoji='🧪', text='Thử lọn mất 10 phút, cứu được cả mái tóc.'),
                                     dict(who='Chủ salon', emoji='🛡️', text='Không có doanh thu hôm nay, nhưng không có sự cố.')]),
                  dict(id='rush', label='Chiều khách, tẩy luôn cả đầu cho kịp hẹn', cost=40, quality='bad', stars=1,
                       review='Tóc nóng ran, gãy ngang. Salon gì mà liều vậy!',
                       outcome='Thuốc phản ứng nóng, tóc gãy từng mảng. Salon phải hoàn tiền và trả phí phục hồi.',
                       perspectives=[dict(who='Chị Vy', emoji='😡', text='Chị vội, nhưng tiệm mới là người biết nghề.'),
                                     dict(who='Tí (học việc)', emoji='😱', text='Em thấy hơi bốc lên mà không dám nói.')]),
                  dict(id='refuse', label='Từ chối, bảo chị đi tiệm khác', quality='ok',
                       outcome='Chị Vy bực bội đi mất, có thể gặp một tiệm dám liều hơn.',
                       perspectives=[dict(who='Chị Vy', emoji='🙄', text='Không nói lý do, ai mà chịu.'),
                                     dict(who='Linh (thợ màu)', emoji='🤷', text='An toàn cho mình, nhưng khách vẫn gặp rủi ro ở chỗ khác.')])],
         lesson='Tóc nhuộm hộp: thử lọn trước, cho khách thấy bằng chứng, và dám nói “hôm nay chưa được”.'),
    dict(id='SL-S04', title='Khách hỏi chuyện của khách khác', npc=4, tone='gentle', min_day=1,
         opening='Bà Lựu hạ giọng: “Con bé cô dâu hôm qua nhuộm màu gì? Nghe nói nó còn nợ tiền tiệm hả? Kể bà nghe coi.”',
         swap='Bạn là bà Lựu, ngồi chờ ủ tóc một mình, buồn buồn muốn có người nói chuyện.',
         facts=[dict(id='book', title='Sổ lịch hẹn', source='Quầy lễ tân', text='Sổ có tên, số điện thoại, dịch vụ và công nợ của mọi khách — thông tin riêng tư.'),
                dict(id='rule', title='Nội quy salon', source='Bảng nội quy', text='Không chia sẻ thông tin khách với người khác, kể cả chuyện “vui vui”.'),
                dict(id='mood', title='Để ý Bà Lựu', source='Quan sát', text='Bà ngồi một mình khá lâu, có vẻ buồn chán và muốn có người trò chuyện.')],
         options=[dict(id='redirect', label='Cười nhẹ: “Chuyện của khách con giữ kín, như chuyện của bà vậy đó”, rồi hỏi han chuyện của bà',
                       requires=['rule', 'mood'], quality='good', stars=5,
                       review='Đứa nhỏ ở tiệm này kín miệng mà dễ thương, bà yên tâm kể chuyện nhà bà.',
                       outcome='Bà Lựu bật cười, kể chuyện hội dưỡng sinh suốt buổi, không còn hỏi chuyện người khác.',
                       perspectives=[dict(who='Bà Lựu', emoji='😄', text='Nó không kể chuyện người ta, chắc cũng không kể chuyện mình.'),
                                     dict(who='Cô dâu hôm qua', emoji='👰', text='May mà tiệm giữ kín, chuyện tiền nong là việc riêng của mình.'),
                                     dict(who='Lễ tân', emoji='📒', text='Sổ khách không phải chuyện để tám.')]),
                  dict(id='gossip', label='Kể vài chuyện cho bà vui', quality='bad', stars=2,
                       review='Tiệm kể chuyện người khác vanh vách, chắc cũng kể chuyện bà.',
                       outcome='Chuyện lan ra hội dưỡng sinh; cô dâu biết được và hủy lịch làm tóc cưới.',
                       perspectives=[dict(who='Cô dâu', emoji='😠', text='Mình trả tiền để làm tóc, không phải để thành chuyện đầu hẻm.'),
                                     dict(who='Bà Lựu', emoji='🤭', text='Vui thì vui, mà giờ bà cũng ngại.')]),
                  dict(id='cold', label='Nói cứng: “Không được hỏi chuyện người khác”', quality='ok', stars=3,
                       review='Nói đúng mà sao nghe như bị la.',
                       outcome='Bà Lựu im lặng, buổi làm tóc hơi ngượng.',
                       perspectives=[dict(who='Bà Lựu', emoji='😶', text='Bà hỏi chơi thôi mà.'),
                                     dict(who='Khoa (thợ cắt)', emoji='🤐', text='Đúng quy định, nhưng không khí hơi lạnh.')])],
         lesson='Giữ bí mật của khách một cách ấm áp: từ chối chuyện người khác, quan tâm tới người trước mặt.'),
    dict(id='SL-S05', title='Khách vãng lai và khách đã đặt lịch', npc=3, tone='tense', min_day=2,
         opening='Anh Tùng đẩy cửa: “Cắt nhanh giùm anh, 15 phút thôi!” Nhưng 10 phút nữa chị Thảo đã đặt lịch ở chiếc ghế duy nhất còn trống.',
         swap='Bạn là thợ cơ khí, chỉ có đúng giờ nghỉ trưa để đi cắt tóc.',
         facts=[dict(id='book', title='Lịch hẹn', source='Sổ lịch', text='Chị Thảo đặt lịch từ tuần trước, dịch vụ nhuộm mất khoảng 90 phút.'),
                dict(id='staff', title='Nhân sự', source='Bảng ca', text='Khoa rảnh sau 20 phút nữa; Tí học việc có thể gội đầu trước.'),
                dict(id='walkin', title='Hỏi anh Tùng', source='Anh Tùng', text='Anh có thể quay lại lúc 3 giờ, chỉ cần biết chắc có chỗ.')],
         options=[dict(id='slot', label='Giữ ghế cho khách đã hẹn; mời anh Tùng chờ 20 phút với Khoa (có trà đá) hoặc giữ giờ 3 giờ chiều',
                       requires=['book', 'staff'], quality='good', stars=5,
                       review='Không được cắt liền nhưng tiệm hẹn giờ rõ ràng, tới là có ghế. Được.',
                       outcome='Chị Thảo vào đúng giờ; anh Tùng uống trà đá 20 phút rồi được Khoa cắt gọn.',
                       perspectives=[dict(who='Anh Tùng', emoji='🙂', text='Biết chắc giờ nào thì anh chờ được.'),
                                     dict(who='Chị Thảo', emoji='😊', text='Đặt lịch mà được giữ chỗ, đúng là tiệm có tâm.'),
                                     dict(who='Khoa (thợ cắt)', emoji='✂️', text='Ca làm vẫn trong tầm tay.')]),
                  dict(id='swap', label='Nhận anh Tùng ngay, để chị Thảo chờ “chút xíu”', quality='bad', stars=2,
                       review='Đặt lịch trước một tuần mà phải ngồi chờ khách vãng lai. Lần sau khỏi đặt.',
                       outcome='Cắt quá giờ, chị Thảo chờ 35 phút rồi bỏ về.',
                       perspectives=[dict(who='Chị Thảo', emoji='😤', text='Đặt lịch để làm gì nếu ai tới trước người đó làm?'),
                                     dict(who='Anh Tùng', emoji='😅', text='Anh được cắt liền mà thấy áy náy.')]),
                  dict(id='refuse', label='Từ chối anh Tùng vì hết chỗ', quality='ok',
                       outcome='Anh Tùng đi tiệm khác. Lịch đúng nhưng mất một khách.',
                       perspectives=[dict(who='Anh Tùng', emoji='😕', text='Chỉ cần hẹn giờ khác là được mà.'),
                                     dict(who='Lễ tân', emoji='📒', text='Giá như mình có sẵn khung giờ trống để mời.')])],
         lesson='Tôn trọng lịch hẹn, và luôn có một khung giờ cụ thể để mời khách vãng lai.'),
    dict(id='SL-S06', title='Học việc làm rát da đầu khách', npc=2, tone='tense', min_day=3,
         opening='Cô Ngọc nhăn mặt: “Sao da đầu cô rát quá con?” Tí học việc vừa thoa thuốc và bật máy hấp cho “nhanh lên màu”.',
         swap='Bạn là cô Ngọc, giáo viên về hưu, lần đầu nhuộm tóc và đang thấy da đầu nóng rát.',
         facts=[dict(id='bowl', title='Kiểm bát thuốc', source='Bàn màu', text='Tí pha oxy 30 vol thay vì 20 vol, lại bật hấp nóng — sai quy trình của salon.'),
                dict(id='scalp', title='Xem da đầu', source='Tay thợ', text='Da đầu đỏ nhẹ vùng đỉnh, chưa phồng rộp.'),
                dict(id='ti', title='Hỏi Tí', source='Tí (học việc)', text='Tí run run: “Em thấy khách chờ lâu, em muốn nhanh…”')],
         options=[dict(id='care', label='Dừng ngay, xả nước mát, xin lỗi cô, ghi sổ sự cố, miễn phí và gọi hỏi thăm hôm sau; kèm Tí học lại quy trình',
                       requires=['bowl', 'scalp'], cost=40, quality='good', stars=4,
                       review='Có sự cố nhưng tiệm xử lý ngay, xin lỗi đàng hoàng, hôm sau còn gọi hỏi thăm. Cô tin tiệm.',
                       outcome='Da đầu cô Ngọc dịu lại sau vài giờ. Tí được kèm lại quy trình và ghi nhớ bài học.',
                       perspectives=[dict(who='Cô Ngọc', emoji='🙏', text='Sự cố thì ai cũng có thể gặp, quan trọng là cách người ta lo cho mình.'),
                                     dict(who='Tí (học việc)', emoji='😢', text='Em sợ bị đuổi, nhưng được dạy lại tới nơi tới chốn.'),
                                     dict(who='Chủ salon', emoji='📋', text='Sổ sự cố giúp cả tiệm không lặp lại lỗi này.')]),
                  dict(id='blame', label='Mắng Tí trước mặt khách cho khách hả giận', quality='bad', stars=2,
                       review='Da đầu cô rát, còn phải nghe tiệm la nhân viên. Mệt.',
                       outcome='Cô Ngọc khó chịu hơn, Tí khóc trong phòng gội; sự cố không được ghi sổ.',
                       perspectives=[dict(who='Cô Ngọc', emoji='😣', text='Cô cần được lo cho da đầu, không cần xem mắng người.'),
                                     dict(who='Tí (học việc)', emoji='😭', text='Em biết em sai, nhưng giờ em sợ không dám hỏi ai nữa.')]),
                  dict(id='downplay', label='“Nhuộm hơi rát là bình thường cô ơi”, làm tiếp', cost=30, quality='bad', stars=1,
                       review='Rát vậy mà bảo bình thường. Về nhà da đầu đỏ ửng!',
                       outcome='Da đầu cô Ngọc kích ứng nặng hơn, tiệm phải trả tiền khám và mất khách.',
                       perspectives=[dict(who='Cô Ngọc', emoji='😠', text='Cô tin tiệm nên mới ngồi chịu.'),
                                     dict(who='Linh (thợ màu)', emoji='😟', text='Rát không bao giờ là bình thường.')])],
         lesson='Khi khách đau: dừng ngay, lo cho khách trước, ghi sổ sự cố và dạy lại — không đổ lỗi trước mặt khách.'),
    dict(id='SL-S07', title='Bé Su khóc trong lần cắt tóc đầu tiên', npc=6, tone='gentle', min_day=1,
         opening='Vừa thấy cây kéo, bé Su òa khóc, ôm chặt cổ mẹ: “Không cắt! Không cắt đâu!”',
         swap='Bạn là bé Su 4 tuổi, lần đầu ngồi ghế cao, nghe tiếng tông đơ rè rè.',
         facts=[dict(id='fear', title='Hỏi mẹ bé', source='Mẹ bé Su', text='Bé sợ tiếng tông đơ vì lần trước bị giật tóc khi cắt ở nhà.'),
                dict(id='tools', title='Nhìn bàn dụng cụ', source='Bàn cắt', text='Có kéo tỉa êm, gương cầm tay, lược nhỏ màu hồng và bình xịt nước hình con cá.'),
                dict(id='time', title='Lịch hẹn', source='Sổ lịch', text='Khách kế tiếp 30 phút nữa mới tới, còn đủ thời gian.')],
         options=[dict(id='gentle', label='Cho bé cầm lược và bình xịt “con cá”, ngồi trong lòng mẹ, cắt từng chút bằng kéo, không dùng tông đơ',
                       requires=['fear', 'tools'], quality='good', stars=5,
                       review='Bé Su về khoe “con cá xịt nước”, mái bằng xinh xỉu. Cảm ơn tiệm kiên nhẫn với bé!',
                       outcome='Bé nín dần, còn xịt nước lên tay thợ. Mái bằng hơi chậm nhưng đều.',
                       perspectives=[dict(who='Mẹ bé Su', emoji='🥰', text='Tiệm không vội, con được là trẻ con.'),
                                     dict(who='Bé Su', emoji='🐟', text='Xịt nước con cá vui ghê, con không sợ nữa!'),
                                     dict(who='Khoa (thợ cắt)', emoji='✂️', text='Cắt cho trẻ con: chậm mới là nhanh.')]),
                  dict(id='hold', label='Nhờ mẹ giữ chặt đầu bé, cắt thật nhanh cho xong', quality='bad', stars=2,
                       review='Cắt xong mà bé khóc cả buổi, giờ thấy tiệm tóc là né.',
                       outcome='Mái lệch vì bé giãy; bé sợ tiệm tóc từ đó.',
                       perspectives=[dict(who='Bé Su', emoji='😭', text='Con sợ!'),
                                     dict(who='Mẹ bé Su', emoji='😔', text='Giá mà mình chờ con bình tĩnh.')]),
                  dict(id='later', label='Dừng lại, hẹn bé hôm khác khi bé sẵn sàng', quality='ok', stars=4,
                       review='Không cắt được nhưng tiệm không ép bé. Hẹn lần sau.',
                       outcome='Bé Su nín, lần sau quay lại cùng… con gấu bông.',
                       perspectives=[dict(who='Mẹ bé Su', emoji='🙂', text='Hơi mất công nhưng bé không bị sợ.'),
                                     dict(who='Chủ salon', emoji='🤔', text='Mất một lượt, được một khách nhỏ tương lai.')])],
         lesson='Với trẻ nhỏ, cảm giác an toàn quan trọng hơn tốc độ.'),
]

SPEC = dict(
    id=ID, prefix='sl_', category='service',
    meta=dict(short='Salon tóc', place='Salon Tóc Gió', tagline='Hỏi kỹ trước khi cắt. Canh từng giây màu.', icon='scissors',
              color='#b25f86', light='#fbe9f1', weather='Nắng hanh, gió nhẹ', work='Khách hẹn', station='Ghế làm tóc',
              greeting='Mời khách ngồi ghế tư vấn: hỏi lịch sử tóc, xem tận mắt rồi mới chốt phương án nhé.',
              caption='Một mái tóc, một câu chuyện được lắng nghe', map_label='17 · SALON TÓC GIÓ'),
    people=PEOPLE,
    staff=[('Linh', 'color', 'Thợ màu, thuộc bảng tuýp và oxy như cháo chảy.', 72, 93),
           ('Khoa', 'cut', 'Cắt nam gọn, chia line đều tăm tắp.', 84, 82),
           ('Nhung', 'assist', 'Gội đầu êm tay, khăn lúc nào cũng thơm.', 80, 85),
           ('Tí', 'assist', 'Học việc chăm chỉ, đang tập sấy phồng.', 74, 76)],
    roles={'color': 'Thợ màu', 'cut': 'Thợ cắt', 'assist': 'Phụ gội'},
    inventory=dict(items=ITEMS, capacity=40),
    prices=dict(PRICES),
    tip=3,
    physical=('sl_wash', 'sl_mix', 'sl_cut', 'sl_treat', 'sl_style', 'sl_checkout', 'sl_appt'),
    free_actions=(),
    no_tick=('sl_rinse', 'sl_desk'),
    waste_items=('bowl',),
    activity=('💇', 'Salon Gió gọn gàng', [('Tuýp 6.1', 'Tủ thuốc nhuộm'), ('Oxy 20 vol', 'Kệ oxy'), ('Tuýp 8.1', 'Tủ thuốc nhuộm'), ('Oxy 10 vol', 'Kệ oxy')],
              ['Tư vấn & xem tóc', 'Thử dị ứng, thử lọn', 'Pha màu, canh giờ xả', 'Cắt, sấy, dặn chăm sóc']),
    stories=[('Lộ trình bạch kim của Hà Mi', ('Hà Mi quay lại với một cuốn sổ nhỏ: “Tiệm ghi giúp em lộ trình 3 buổi được không?”',
                                              'Bạn ghi mốc từng buổi, dầu gội tím và những ngày không nên dùng nhiệt.',
                                              'Buổi cuối, Mi gửi ảnh bạch kim tự chụp dưới nắng: “Không cần filter luôn!”')),
             ('Cô Ngọc và tấm thẻ thử dị ứng', ('Cô Ngọc hỏi: “Sao lần đầu nhuộm lại phải thử trước vậy con?”',
                                                'Bạn kể về vết chấm thử sau tai, lý do phải chờ và cách tiệm ghi sổ.',
                                                'Cô Ngọc làm tấm thẻ ghi ngày thử dị ứng kẹp vào ví, còn nhắc cả hội dưỡng sinh.')),
             ('Tí học việc cầm kéo', ('Tí xin tập cắt trên đầu mẫu sau giờ đóng cửa.',
                                      'Bạn chỉ Tí chia vùng, cắt đường chuẩn rồi kiểm đối xứng — chậm mà chắc.',
                                      'Tí cắt cho vị khách đầu tiên dưới sự kèm cặp: bé Su, mái bằng thẳng tắp.'))],
    review_asides=['Tóc mềm mượt, soi gương mãi không chán 💇', 'Được tư vấn kỹ, không bị ép mua gì.',
                   'Màu lên đúng như đã thống nhất.', 'Thợ canh giờ chuẩn từng giây!'],
    situations=SITUATIONS,
    guide='Tư vấn → xem tóc → chốt phương án thật lòng → pha màu, canh giờ → gội → cắt theo trình tự → sấy → thanh toán.',
)
