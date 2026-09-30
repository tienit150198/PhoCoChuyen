"""Tiệm Hoa Nắng — a neighbourhood florist (plugin career).

Real work of the job: read the brief (dịp tặng, kiểu bó, ngân sách, tông màu,
người nhận), pick stems from the cooler (oldest lot first, so check how many
days each stem has left and cull wilting lots), condition them (cắt xéo gốc,
tuốt lá dưới mực nước, ngâm nước — real seconds), choose the base (bó cầm tay,
bình, giỏ mút xốp, kệ viếng) and let floral foam sink by itself (pushing it
under leaves a dry core), arrange / tie the spiral, wrap, ribbon, print the
funeral banner, hand-write the card and deliver in the booked time slot.

Flower meaning matters: white chrysanthemum is for funerals, bright red or
yellow blooms never go to a condolence. Those are refused by the recipient and
must be redone. Lilies in a home with cats are a safety mistake (1 star, no
pay, a complaint, an inspection). Other mistakes (off-palette colours, the
wrong number of focal stems, a flower that sends a mixed message, a plain card,
stems about to wilt, a bouquet far below its budget, a late delivery) reach the
customer, who reacts in proportion (grumble, money back, a re-wrap, or refusing
to pay) and names the mistake in the review.

Every day is a little different (see food_service): the luck of the day (rain
— cover deliveries; heat — longer soak; a flower-market gift; holiday rush;
wedding season), one or two surprises that need a decision, customers with
personalities, walk-ins, a streak bonus and an end-of-day grade. From day 2 a
customer does not say everything up front: ask about colours, the recipient
(a cat at home?) or the delivery time — each question costs a little patience.
From day 3 some orders are sets (two pieces for one customer), finished one by
one and delivered together.
"""
from __future__ import annotations
import copy
import re
import unicodedata
from . import kit
from . import food_service as FS
from .. import consequences as cq
from .. import archive as ar
ID = 'florist'

def _one_of(value, options, message: str):
    """kit.one_of, but a list/dict payload is a clean GameError instead of a TypeError."""
    kit.need(isinstance(value, str) and value in options, message)
    return value

SOAK_MIN = 8        # seconds in the bucket before stems count as hydrated
FOAM_MIN = 10       # seconds for floral foam to sink by itself
MAX_BUCKETS = 2
MAX_STEMS = 30
DELIVERY_FEE = 15

OCCASIONS = {
    'birthday': dict(id='birthday', name='Sinh nhật', emoji='🎂', celebrate=True),
    'condolence': dict(id='condolence', name='Chia buồn / viếng', emoji='🕊️', celebrate=False),
    'opening': dict(id='opening', name='Khai trương', emoji='🎉', celebrate=True),
    'apology': dict(id='apology', name='Xin lỗi', emoji='🙏', celebrate=True),
    'oct20': dict(id='oct20', name='20/10', emoji='👩‍🏫', celebrate=True),
    'mar8': dict(id='mar8', name='8/3', emoji='💐', celebrate=True),
    'graduation': dict(id='graduation', name='Tốt nghiệp', emoji='🎓', celebrate=True),
    'proposal': dict(id='proposal', name='Cầu hôn', emoji='💍', celebrate=True),
}
COLORS = {
    'red': dict(id='red', name='đỏ', hex='#d8344a'), 'pink': dict(id='pink', name='hồng', hex='#f29ab6'),
    'white': dict(id='white', name='trắng', hex='#f7f4ee'), 'yellow': dict(id='yellow', name='vàng', hex='#f5c83a'),
    'purple': dict(id='purple', name='tím', hex='#a878c8'), 'green': dict(id='green', name='xanh lá', hex='#6f9a6a'),
}
ALL = tuple(OCCASIONS)
# taboo → the recipient refuses; bad → accepted with a complaint.
FLOWERS = {
    'rose_red': dict(id='rose_red', name='Hồng đỏ', emoji='🌹', color='red', role='focal', meaning='Tình yêu nồng nhiệt',
                     good=('proposal', 'mar8', 'oct20', 'birthday'), bad=(), taboo=('condolence',), unlock=1),
    'rose_pink': dict(id='rose_pink', name='Hồng phấn', emoji='🌸', color='pink', role='focal', meaning='Dịu dàng, biết ơn',
                      good=('birthday', 'oct20', 'mar8', 'apology', 'graduation', 'proposal'), bad=(), taboo=('condolence',), unlock=1),
    'rose_white': dict(id='rose_white', name='Hồng trắng', emoji='🤍', color='white', role='focal', meaning='Chân thành, tưởng nhớ',
                       good=('apology', 'condolence', 'proposal', 'birthday', 'oct20', 'mar8'), bad=(), taboo=(), unlock=1),
    'rose_yellow': dict(id='rose_yellow', name='Hồng vàng', emoji='💛', color='yellow', role='focal', meaning='Tình bạn, niềm vui',
                        good=('graduation', 'opening', 'birthday'), bad=('proposal', 'apology'), taboo=('condolence',), unlock=1),
    'lily': dict(id='lily', name='Ly trắng', emoji='🌷', color='white', role='focal', meaning='Trang trọng, thanh khiết',
                 good=('condolence', 'opening', 'mar8', 'oct20'), bad=(), taboo=(), unlock=1, cats='toxic'),
    'mum_white': dict(id='mum_white', name='Cúc trắng', emoji='💮', color='white', role='focal', meaning='Tiếc thương, tiễn biệt',
                      good=('condolence',), bad=(), taboo=tuple(o for o in ALL if o != 'condolence'), unlock=1),
    'sunflower': dict(id='sunflower', name='Hướng dương', emoji='🌻', color='yellow', role='focal', meaning='Năng lượng, hướng về phía trước',
                      good=('graduation', 'opening', 'birthday'), bad=('proposal',), taboo=('condolence',), unlock=1),
    'carnation': dict(id='carnation', name='Cẩm chướng hồng', emoji='🌺', color='pink', role='focal', meaning='Lòng biết ơn, tình mẹ',
                      good=('oct20', 'mar8', 'birthday', 'apology'), bad=(), taboo=('condolence',), unlock=2),
    'orchid': dict(id='orchid', name='Lan hồ điệp', emoji='💜', color='purple', role='focal', meaning='Sang trọng, thịnh vượng',
                   good=('opening', 'mar8', 'oct20', 'graduation'), bad=(), taboo=(), unlock=1),
    'babys_breath': dict(id='babys_breath', name='Baby trắng', emoji='☁️', color='white', role='filler', meaning='Tinh khôi, điểm xuyết',
                         good=ALL, bad=(), taboo=(), unlock=1, cats='caution'),
    'eucalyptus': dict(id='eucalyptus', name='Bạch đàn', emoji='🌿', color='green', role='green', meaning='Lá phụ, giữ dáng bó',
                       good=ALL, bad=(), taboo=(), unlock=1, cats='caution'),
}
BAD_NOTE = dict(proposal='hồng vàng/hướng dương dễ bị hiểu là “chỉ là bạn”', apology='hồng vàng dễ bị hiểu là hờ hững')
FORMATS = {
    'bouquet': dict(id='bouquet', name='Bó hoa cầm tay', emoji='💐', uses={}, foam=False, soak=True, wrap=True, unlock=1),
    'vase': dict(id='vase', name='Bình hoa để bàn', emoji='🏺', uses={'vase': 1}, foam=False, soak=True, wrap=False, unlock=2),
    'basket': dict(id='basket', name='Giỏ hoa mút xốp', emoji='🧺', uses={'basket': 1, 'foam': 1}, foam=True, soak=False, wrap=False, unlock=1),
    'wreath': dict(id='wreath', name='Kệ hoa viếng', emoji='🕊️', uses={'stand': 1, 'foam': 2}, foam=True, soak=False, wrap=False, unlock=1),
}
PAPERS = {
    'kraft': dict(id='kraft', item='paper_kraft', name='Giấy kraft nâu', hex='#c89f73', color=None),
    'white': dict(id='white', item='paper_white', name='Giấy lụa trắng', hex='#f6f3ec', color=None),
    'pink': dict(id='pink', item='paper_pink', name='Giấy hồng pastel', hex='#f5c6d4', color='pink'),
    'black': dict(id='black', item='paper_black', name='Giấy đen nhám', hex='#3a3538', color=None),
}
RIBBONS = {
    'white': dict(id='white', name='Trắng', hex='#faf8f3'), 'red': dict(id='red', name='Đỏ', hex='#c8283c'),
    'pink': dict(id='pink', name='Hồng', hex='#f08fb0'), 'gold': dict(id='gold', name='Vàng kim', hex='#d4a94a'),
    'black': dict(id='black', name='Đen', hex='#2d2a2c'), 'purple': dict(id='purple', name='Tím', hex='#8e62b8'),
}
SLOTS = {'08-10': '8–10 giờ', '10-12': '10–12 giờ', '14-16': '14–16 giờ', '16-18': '16–18 giờ'}
# Card tone: (words that fit the occasion, words that must never appear), compared without accents.
TONE = {
    'birthday': (('sinh nhat', 'tuoi moi', 'happy birthday', 'hpbd', 'chuc mung', 'mung tuoi'), ('chia buon', 'phan uu', 'vinh biet', 'thuong tiec', 'kinh vieng')),
    'condolence': (('chia buon', 'phan uu', 'thuong tiec', 'tuong nho', 'vinh biet', 'kinh vieng', 'an nghi', 'nguoi da khuat', 'yen nghi'),
                   ('chuc mung', 'happy', 'sinh nhat', 'hanh phuc', 'khai truong', 'hong phat', 'vui ve')),
    'opening': (('khai truong', 'hong phat', 'thinh vuong', 'phat dat', 'van su', 'may man', 'dat khach', 'chuc mung', 'thanh cong'), ('chia buon', 'phan uu', 'vinh biet', 'thuong tiec')),
    'apology': (('xin loi', 'tha thu', 'loi cua', 'sorry', 'lam lanh', 'hoi han'), ('chia buon', 'phan uu', 'vinh biet')),
    'oct20': (('20/10', 'phu nu', 'ngay cua', 'cam on', 'tri an', 'yeu thuong', 'co giao', 'kinh chuc'), ('chia buon', 'phan uu', 'vinh biet')),
    'mar8': (('8/3', 'phu nu', 'ngay cua', 'cam on', 'yeu thuong', 'xinh dep', 'hanh phuc'), ('chia buon', 'phan uu', 'vinh biet')),
    'graduation': (('tot nghiep', 'chuc mung', 'tuong lai', 'thanh cong', 'tu hao', 'ra truong', 'chang duong'), ('chia buon', 'phan uu', 'vinh biet')),
    'proposal': (('lay', 'cuoi', 'ben nhau', 'mai mai', 'yeu', 'marry', 'tron doi', 'ca doi'), ('chia buon', 'phan uu', 'vinh biet', 'chia tay')),
}

ITEMS = [
    dict(id='rose_red', name='Hồng đỏ', emoji='🌹', group='flower', unit='cành', cost=5, price=14, life=4, start=20),
    dict(id='rose_pink', name='Hồng phấn', emoji='🌸', group='flower', unit='cành', cost=4, price=12, life=4, start=16),
    dict(id='rose_white', name='Hồng trắng', emoji='🤍', group='flower', unit='cành', cost=4, price=12, life=3, start=12),
    dict(id='rose_yellow', name='Hồng vàng', emoji='💛', group='flower', unit='cành', cost=4, price=12, life=4, start=10),
    dict(id='lily', name='Ly trắng', emoji='🌷', group='flower', unit='cành', cost=6, price=18, life=4, start=8),
    dict(id='mum_white', name='Cúc trắng', emoji='💮', group='flower', unit='cành', cost=2, price=6, life=4, start=20),
    dict(id='sunflower', name='Hướng dương', emoji='🌻', group='flower', unit='cành', cost=4, price=14, life=3, start=10),
    dict(id='carnation', name='Cẩm chướng hồng', emoji='🌺', group='flower', unit='cành', cost=2, price=8, life=4, start=12, unlock=2),
    dict(id='orchid', name='Lan hồ điệp (cành)', emoji='💜', group='flower', unit='cành', cost=10, price=30, life=6, start=6),
    dict(id='babys_breath', name='Baby trắng', emoji='☁️', group='filler', unit='nhánh', cost=1, price=4, life=3, start=16),
    dict(id='eucalyptus', name='Bạch đàn', emoji='🌿', group='filler', unit='nhánh', cost=1, price=3, life=5, start=20),
    dict(id='paper_kraft', name='Giấy kraft nâu', emoji='🟫', group='wrap', unit='tờ', cost=1, start=12),
    dict(id='paper_white', name='Giấy lụa trắng', emoji='⬜', group='wrap', unit='tờ', cost=1, start=12),
    dict(id='paper_pink', name='Giấy hồng pastel', emoji='🟪', group='wrap', unit='tờ', cost=1, start=10),
    dict(id='paper_black', name='Giấy đen nhám', emoji='⬛', group='wrap', unit='tờ', cost=2, start=8),
    dict(id='ribbon', name='Ruy băng lụa', emoji='🎀', group='wrap', unit='đoạn', cost=1, start=24),
    dict(id='card', name='Thiệp viết tay', emoji='💌', group='wrap', unit='tấm', cost=1, start=24),
    dict(id='foam', name='Mút cắm hoa', emoji='🧽', group='base', unit='bánh', cost=2, start=8),
    dict(id='vase', name='Bình thủy tinh', emoji='🏺', group='base', unit='cái', cost=6, start=3, unlock=2),
    dict(id='basket', name='Giỏ mây', emoji='🧺', group='base', unit='cái', cost=5, start=4),
    dict(id='stand', name='Chân kệ hoa viếng', emoji='🪜', group='base', unit='bộ', cost=6, start=2),
    dict(id='banner', name='Băng rôn in chữ', emoji='🎗️', group='wrap', unit='dải', cost=3, start=4),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}

PEOPLE = [
    ('Anh Minh', 'Nhân viên ngân hàng', 'Lãng mạn, lo xa, sắp cầu hôn bạn gái.', 'warm'),
    ('Chị Hạnh', 'Giáo viên', 'Kỹ tính, mẹ chị nuôi ba bé mèo.', 'picky'),
    ('Cô Lụa', 'Tổ trưởng tổ dân phố', 'Lo việc hiếu hỉ cho cả hẻm, nói là làm.', 'bossy'),
    ('Anh Đạt', 'Chủ tiệm sửa xe', 'Ít nói, chỉ cần đúng giờ, đúng việc.', 'quiet'),
    ('Linh', 'Sinh viên', 'Ngân sách mỏng, gu thẩm mỹ dày.', 'genz'),
    ('Chú Phúc', 'Tài xế về hưu', 'Hay quên ngày kỷ niệm, rất thương vợ.', 'warm'),
    ('Bà Tám', 'Hàng xóm lâu năm', 'Tinh mắt, nhìn cánh hoa là biết hoa mấy ngày.', 'sour'),
]


# Personalities of the regulars (food_service.PERSONAS).
NPC_GUEST = {0: 'chatty', 1: 'picky', 2: 'rush', 3: 'plain', 4: 'plain', 5: 'regular', 6: 'elder'}
GEN = 2            # order generator version (older saves are upgraded once)

# Consultation: from day 2 some parts of the brief stay unknown until asked.
TOPICS = {
    'palette': dict(id='palette', emoji='🎨', label='Người nhận thích màu gì?'),
    'recipient': dict(id='recipient', emoji='🏠', label='Người nhận là ai, nhà có gì cần tránh?'),
    'slot': dict(id='slot', emoji='🕒', label='Giao lúc mấy giờ thì kịp?'),
}
ASK_COST = 5       # patience per question (a guest in a hurry loses more)
ASK_COST_RUSH = 7


def _o(**k):
    return k


# Each order: the brief, what the customer says up front (note), and what they
# answer when asked (clues). A note never gives away a clue.
ORDERS = [
    _o(npc=0, title='Bó 9 hồng đỏ cầu hôn', occasion='proposal', format='bouquet', budget=220, palette=['red', 'white'], focal=('rose_red', 9),
       stems=(11, 21), card=True, note='Tối nay anh cầu hôn. Đúng 9 bông nha em, “mãi mãi bên nhau”.', day=1,
       clues=dict(palette='Cô ấy mê hồng đỏ, điểm thêm chút trắng cho tinh khôi.', recipient='Bạn gái anh ở chung cư, không nuôi thú cưng.')),
    _o(npc=1, title='Hoa sinh nhật cho mẹ chị Hạnh', occasion='birthday', format='bouquet', budget=180, palette=['pink', 'white'], focal=None,
       stems=(9, 19), cats=True, card=True, delivery='16-18', note='Sinh nhật mẹ chị, bó nào nhẹ nhàng, xinh xắn nha em.', day=1,
       clues=dict(palette='Mẹ chị thích hồng phấn với trắng, nhìn dịu mắt.', recipient='Mẹ chị nuôi ba bé mèo hay nhảy lên bàn, đừng cho hoa ly nha em.',
                  slot='Giao giùm chị 16 tới 18 giờ, lúc mẹ đi chợ về.')),
    _o(npc=3, title='Giỏ hoa khai trương tiệm sửa xe', occasion='opening', format='basket', budget=260, palette=['yellow', 'red'], focal=None,
       stems=(11, 25), card=True, delivery='08-10', note='Tiệm sửa xe của anh khai trương, làm giỏ hoa cho ra dáng nha.', day=1,
       clues=dict(palette='Cho rực rỡ lên, vàng với đỏ, hướng dương càng tốt.', recipient='Giỏ đặt ngay cửa tiệm ngoài đường, không có chó mèo gì đâu.',
                  slot='Khai trương 8 giờ sáng, giao khung 8 tới 10 giờ giùm anh.')),
    _o(npc=4, title='Bó hoa tốt nghiệp cho bạn thân', occasion='graduation', format='bouquet', budget=120, palette=['yellow', 'white'], focal=('sunflower', 3),
       stems=(7, 15), card=True, note='Em có 120 xu thôi, 3 bông hướng dương nha chị.', day=1,
       clues=dict(palette='Bạn em mê màu vàng, thêm chút trắng cho sáng.', recipient='Bạn em ở ký túc xá, không nuôi gì hết.')),
    _o(npc=5, title='Hoa xin lỗi vợ', occasion='apology', format='bouquet', budget=160, palette=['pink', 'white'], focal=None,
       stems=(7, 17), card=True, note='Chú lỡ quên kỷ niệm ngày cưới… bó nào nói được chữ “xin lỗi” giùm chú.', day=1,
       clues=dict(palette='Vợ chú thích hồng nhạt với trắng, nhẹ nhàng thôi.', recipient='Nhà chú không nuôi mèo, chỉ có hồ cá vàng.')),
    _o(npc=6, title='Bó cúc trắng đi viếng bạn già', occasion='condolence', format='bouquet', budget=90, palette=['white', 'green'], focal=('mum_white', 10),
       stems=(10, 20), card=True, note='Bà đi viếng bạn già, bó cúc trắng giản dị thôi con. Thiệp ghi giùm bà vài chữ.', day=1,
       clues=dict(palette='Trắng với xanh lá thôi con, cho trang nghiêm.', recipient='Nhà bạn bà đang có tang, con cháu đông đủ, không nuôi con gì.')),
    _o(npc=2, title='Kệ hoa viếng cụ Tư đầu hẻm', occasion='condolence', format='wreath', budget=300, palette=['white', 'green'], focal=None,
       stems=(15, 30), banner='Thành kính phân ưu · Tổ dân phố 5', delivery='08-10',
       note='Kệ hoa của tổ dân phố viếng cụ Tư, băng rôn ghi đúng giùm cô: “Thành kính phân ưu · Tổ dân phố 5”.', day=2,
       clues=dict(palette='Trắng và xanh lá cho trang nghiêm con nhé.', recipient='Kệ đặt ở nhà tang lễ đầu hẻm, ngay lối vào.',
                  slot='Lễ viếng 9 giờ sáng, con giao khung 8 tới 10 giờ giùm cô.')),
    _o(npc=1, title='Hoa 20/10 cho cô chủ nhiệm', occasion='oct20', format='bouquet', budget=150, palette=['pink', 'white'], focal=None,
       stems=(9, 17), card=True, note='Hoa cho cô chủ nhiệm của con, thanh lịch thôi em.', day=2,
       clues=dict(palette='Cô thích hồng phấn với trắng.', recipient='Cô ở khu tập thể giáo viên, không nuôi thú cưng.')),
    _o(npc=4, title='Hoa sinh nhật bạn trai (ngân sách sinh viên)', occasion='birthday', format='bouquet', budget=100, palette=['red', 'pink', 'white'], focal=None,
       stems=(5, 13), card=True, note='Rẻ mà xinh nha chị. Thiệp em đọc chị viết giùm.', day=2,
       clues=dict(palette='Bạn em thích màu đỏ, pha hồng với trắng cũng được.', recipient='Bạn trai em ở trọ một mình, không nuôi gì.')),
    _o(npc=6, title='Hoa 8/3 bất ngờ cho con dâu', occasion='mar8', format='bouquet', budget=140, palette=['pink', 'red'], focal=None,
       stems=(7, 15), card=True, delivery='10-12', note='Hoa 8/3 bất ngờ cho con dâu bà, giao tới chỗ làm của nó.', day=2,
       clues=dict(palette='Con dâu bà thích hồng với đỏ, tươi tắn.', recipient='Nó làm ở ngân hàng, hoa để trên bàn làm việc.',
                  slot='Giao 10 tới 12 giờ, trước giờ nghỉ trưa cho nó bất ngờ.')),
    _o(npc=0, title='Bình hoa 8/3 cho quầy lễ tân', occasion='mar8', format='vase', budget=200, palette=['pink', 'red', 'white'], focal=None,
       stems=(9, 19), card=True, delivery='08-10', note='Bình hoa để bàn lễ tân cho chị em văn phòng.', day=3,
       clues=dict(palette='Hồng, đỏ, trắng cho vui mắt.', recipient='Quầy lễ tân tòa nhà, không có thú nuôi.', slot='Giao trước giờ làm, 8 tới 10 giờ nha.')),
    _o(npc=5, title='Bình hoa ly thơm cho phòng khách', occasion='opening', format='vase', budget=180, palette=['white', 'green'], focal=('lily', 5),
       stems=(7, 15), card=False, note='Nhà chú mới sửa xong, cắm bình ly trắng cho thơm.', day=3,
       clues=dict(palette='Trắng với xanh lá cho sang.', recipient='Nhà chú không nuôi mèo đâu, cứ ly trắng cho thơm.')),
    _o(npc=2, title='Giỏ hoa chia buồn gửi đồng nghiệp', occasion='condolence', format='basket', budget=220, palette=['white', 'green'], focal=None,
       stems=(11, 21), card=True, delivery='14-16', note='Giỏ hoa chia buồn gửi đồng nghiệp của cô, trang nghiêm giùm cô.', day=4,
       clues=dict(palette='Trắng với xanh lá thôi con.', recipient='Gửi tới nhà tang lễ, không có thú nuôi.', slot='Chiều nay, 14 tới 16 giờ con nhé.')),
    _o(npc=3, title='Giỏ lan hồ điệp mừng khai trương', occasion='opening', format='basket', budget=400, palette=['purple', 'white', 'yellow'], focal=('orchid', 3),
       stems=(9, 21), cats=True, card=True, delivery='08-10', note='Tiệm quần áo của bạn anh khai trương, cho sang một chút, 3 cành lan.', day=5,
       clues=dict(palette='Tím lan làm chủ, điểm trắng với vàng.', recipient='Trong tiệm bạn anh có nuôi một bé mèo lông trắng đó em.',
                  slot='Khai trương 8 giờ, giao 8 tới 10 giờ nha em.')),
]
# Sets: several pieces for one customer, finished one by one, delivered together.
SETS = [
    _o(npc=1, title='Hai bó 20/10 cho hai cô giáo', occasion='oct20', note='Con có hai cô, mỗi cô một bó nhỏ kèm thiệp riêng nha em.', day=3,
       clues=dict(palette='Cô chủ nhiệm thích hồng phấn với trắng; cô dạy toán thích đỏ với trắng.', recipient='Hai cô ở khu tập thể giáo viên, không ai nuôi mèo.'),
       parts=[dict(label='Bó cho cô chủ nhiệm', format='bouquet', budget=110, palette=['pink', 'white'], focal=None, stems=(7, 13), card=True),
              dict(label='Bó cho cô dạy toán', format='bouquet', budget=110, palette=['red', 'white'], focal=None, stems=(7, 13), card=True)]),
    _o(npc=3, title='Khai trương: giỏ hoa cửa tiệm & bó tặng chủ', occasion='opening', delivery='08-10',
       note='Một giỏ hoa đặt cửa, một bó nhỏ tặng chủ tiệm. Giao một lượt nha em.', day=4,
       clues=dict(palette='Giỏ thì vàng với đỏ cho rực rỡ; bó tặng chủ thì vàng với trắng.', recipient='Tiệm điện thoại đầu chợ, không có thú nuôi.',
                  slot='Cắt băng khai trương 9 giờ, giao 8 tới 10 giờ.'),
       parts=[dict(label='Giỏ hoa đặt cửa', format='basket', budget=220, palette=['yellow', 'red'], focal=None, stems=(11, 21), card=True),
              dict(label='Bó tặng chủ tiệm', format='bouquet', budget=100, palette=['yellow', 'white'], focal=('sunflower', 3), stems=(7, 13), card=False)]),
    _o(npc=0, title='Cầu hôn: bó hoa & bình hoa bàn tiệc', occasion='proposal', delivery='16-18',
       note='Bó 9 hồng đỏ để anh quỳ xuống, thêm một bình hoa cho bàn tiệc tối nay.', day=5,
       clues=dict(palette='Đỏ với trắng hết nha em.', recipient='Nhà hàng sân thượng, không có thú nuôi.', slot='Tiệc lúc 19 giờ, giao 16 tới 18 giờ để kịp bày bàn.'),
       parts=[dict(label='Bó hoa cầu hôn', format='bouquet', budget=220, palette=['red', 'white'], focal=('rose_red', 9), stems=(11, 21), card=True),
              dict(label='Bình hoa bàn tiệc', format='vase', budget=150, palette=['red', 'white'], focal=None, stems=(7, 15), card=False)]),
]
OPENING = 'Chào tiệm, mình muốn đặt hoa. Tư vấn giúp mình với!'
PIECE_KEYS = ('format', 'budget', 'palette', 'focal', 'stems', 'card', 'banner')
CORE_KEYS = ('occasion', *PIECE_KEYS, 'cats', 'delivery')

# --- luck of the day -----------------------------------------------------------
MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Nhịp tiệm vừa phải, hợp để làm quen tay.', weight=3),
    dict(id='rain', emoji='🌧️', label='Trời mưa', hint='Đơn giao tận nơi phải bọc nylon chống mưa trước khi đi. Ít khách ghé tiệm.', min_day=2, weight=2, walkin=0.1),
    dict(id='heat', emoji='☀️', label='Nắng gắt', hint='Hoa mất nước nhanh: ngâm xô ít nhất 12 giây mới đủ nước.', min_day=2, weight=2, soak=4),
    dict(id='quiet', emoji='🍃', label='Phố vắng', hint='Ít khách, ai cũng thong thả. Tranh thủ sơ chế, dọn tủ mát.', min_day=2, weight=1, patience=-1),
    dict(id='market', emoji='🚚', label='Chợ sỉ về hoa đẹp', hint='Nhà vườn tặng 6 cành hồng phấn tươi. Khách ghé tiệm nhiều hơn.', min_day=3, weight=2, walkin=0.25),
    dict(id='holiday', emoji='🎊', label='Mùa lễ tặng hoa', hint='Khách vào liên tục, nhiều người đang vội. Đơn 20/10, 8/3, sinh nhật dồn dập.', min_day=3, weight=2, walkin=0.4, patience=1),
    dict(id='wedding', emoji='💒', label='Mùa cưới', hint='Nhiều đơn cầu hôn, khai trương; khách hay đặt theo bộ nhiều món.', min_day=4, weight=1, walkin=0.2),
]
MOD_INDEX = {m['id']: m for m in MODS}


def _style(day: int, slot: int, mod: str) -> str:
    """Single orders; from day 3 some are sets (more of them in the wedding season)."""
    if day < 3 or slot == 0:
        return 'single'
    deck = ['single', 'single', 'single', 'set'] + (['set'] if mod == 'wedding' else []) + (['set'] if day >= 6 else [])
    kit.rng(ID, 'styles', day).shuffle(deck)
    return deck[(slot - 1) % len(deck)]


def _hidden(day: int, slot: int, o: dict) -> list:
    """What the customer does not say until asked: nothing on day 1, one topic, then two."""
    if day < 2:
        return []
    topics = [k for k in TOPICS if k in o['clues']]
    k = 1 if day < 4 else 2
    return sorted(kit.rng(ID, 'hide', day, slot).sample(topics, min(k, len(topics))))


def _piece(p: dict) -> dict:
    return dict(format=p['format'], budget=p['budget'], palette=list(p['palette']),
                focal=dict(item=p['focal'][0], count=p['focal'][1]) if p['focal'] else None,
                stems=list(p['stems']), card=bool(p.get('card')), banner=p.get('banner'))


DAY1 = (3, 1, 4, 0, 5, 2)   # first day: a simple bouquet first, then one of each kind
FAVOURED = dict(holiday=('oct20', 'mar8', 'birthday'), wedding=('proposal', 'opening'))


def _deck(day: int, mod: str) -> list:
    """Today's single orders in serving order: no repeats until the list runs out,
    orders new today come first, busy seasons favour their occasions."""
    if day <= 1:
        return [ORDERS[i] for i in DAY1]
    pool = [x for x in ORDERS if x['day'] <= day]
    kit.rng(ID, 'deck', day).shuffle(pool)
    fav = FAVOURED.get(mod, ())
    pool.sort(key=lambda x: (x['day'] != day, x['occasion'] not in fav))
    for i in range(1, len(pool)):
        # Two orders for the same occasion back to back feel repetitive.
        if pool[i]['occasion'] == pool[i - 1]['occasion']:
            j = next((j for j in range(i + 1, len(pool)) if pool[j]['occasion'] != pool[i - 1]['occasion']), None)
            if j is not None:
                pool[i], pool[j] = pool[j], pool[i]
    return pool


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = FS.pick_mod(ID, day, MODS)['id']
    styles = [_style(day, j, mod) for j in range(slot + 1)]
    style = styles[slot]
    k = styles[:slot].count(style)
    if style == 'set':
        sets = [x for x in SETS if x['day'] <= day]
        kit.rng(ID, 'sets', day).shuffle(sets)
        o = sets[k % len(sets)]
    else:
        deck = _deck(day, mod)
        o = deck[k % len(deck)]
    common = dict(style=style, occasion=o['occasion'], cats=bool(o.get('cats')), delivery=o.get('delivery'), note=o['note'],
                  clues={k: v for k, v in o['clues'].items() if k in TOPICS}, hidden=_hidden(day, slot, o))
    if style == 'set':
        parts = [dict(_piece(p), label=p['label']) for p in o['parts']]
        head = {k: copy.deepcopy(parts[0][k]) for k in PIECE_KEYS}
        needs = dict(head, **common, party=parts)
        needs['budget'] = sum(p['budget'] for p in parts)
    else:
        needs = dict(_piece(o), **common)
    total = len(needs.get('party') or [needs])
    return kit.base_task(ID, day, slot, serial, o['npc'], o['title'], OPENING, needs=needs, work=_empty_work(),
                         quoted_price=None, served=None, refused=0, guest=FS.guest(NPC_GUEST[o['npc']]), gen=GEN,
                         asked=[], cur=0, pieces=[None] * total)


FIXED = ('needs', 'guest')


def _empty_work() -> dict:
    return dict(stems=[], soak=None, soaked=0.0, base=None, foam=None, arranged=False, foam_ok=None,
                paper=None, ribbon=None, banner=None, card=None, slot=None, value=0, cost=0, cover=False)


def initial() -> dict:
    return dict(spare=[], delivered=0, dumped=0, wreaths=0, pins=0, regulars={}, grades=[], ev_hist=[], **_care_defaults(1))


# --- order shape ---------------------------------------------------------------
def _specs(n: dict) -> list:
    return n.get('party') or [n]


def _spec(t: dict, i: int | None = None) -> dict:
    """The brief as seen from one piece (the one on the bench by default)."""
    n = t['needs']
    party = n.get('party')
    if not party:
        return n
    return {**n, **party[t.get('cur', 0) if i is None else i]}


def _is_set(t: dict) -> bool:
    return bool(t['needs'].get('party'))


def _total(t: dict) -> int:
    return len(_specs(t['needs']))


def _core(n: dict | None) -> tuple:
    return tuple(repr((n or {}).get(k)) for k in CORE_KEYS)


def _started(w: dict) -> bool:
    return bool(w['stems'] or w['base'])


def _upgrade_task(t: dict, c: dict | None) -> None:
    """A task saved by an older order generator: regenerate its fixed facts once.
    What the florist already heard stays heard; work is kept when the brief did not change."""
    slot = int(t['id'].rsplit('-', 1)[1])
    fresh = make_task(t['day'], slot, t['created_turn'])
    same = _core(t.get('needs')) == _core(fresh['needs']) and not fresh['needs'].get('party')
    for k in ('npc', 'title', 'opening', 'needs', 'guest', 'gen'):
        t[k] = copy.deepcopy(fresh[k])
    for k, v in fresh.items():
        t.setdefault(k, copy.deepcopy(v))
    t['asked'] = list(t['needs']['hidden']) if t.get('known') else []
    t['cur'] = 0
    t['pieces'] = [None] * _total(t)
    for k, v in _empty_work().items():
        t['work'].setdefault(k, v)
    if t['served'] and isinstance(t['served'].get('work'), dict):
        for k, v in _empty_work().items():
            t['served']['work'].setdefault(k, v)
    if t['status'] not in FS.DONE and not same:
        t['work'] = _empty_work()
        t['refused'] = 0
        t['quoted_price'] = None
        if c is not None:
            on_task(None, c, t)


def _migrate(c: dict) -> dict:
    d = FS.migrate(c)
    d.setdefault('pins', 0)
    for k, v in _care_defaults(c['day']).items():
        d.setdefault(k, v)
    for t in c['tasks']:
        if t['career'] == ID and t.get('gen') != GEN:
            _upgrade_task(t, c)
    return d


def _plan(c: dict) -> dict:
    return FS.plan(c, ID, MODS, EVENTS)


def _peek_plan(c: dict) -> dict:
    """Read-only view of today's plan (the public projection must not write)."""
    p = kit.data(c).get('plan')
    if isinstance(p, dict) and p.get('day') == c['day']:
        return p
    return FS.new_plan(ID, c['day'], MODS, EVENTS)


def _soak_min(c: dict) -> int:
    return SOAK_MIN + MOD_INDEX[_peek_plan(c)['mod']].get('soak', 0)


def _walkin_chance(c: dict, pl: dict) -> float:
    return MOD_INDEX[pl['mod']].get('walkin', 0.0)


def _patience_extra(c: dict, pl: dict) -> int:
    return MOD_INDEX[pl['mod']].get('patience', 0) + (1 if c['day'] >= 6 else 0)


def _drain_patience(c: dict, n: int) -> None:
    for t in FS.open_tasks(c, ID):
        t['patience'] = max(25, t.get('patience', 100) - n)


def on_task(s: dict | None, c: dict, t: dict) -> None:
    if t.get('gen') != GEN:
        _upgrade_task(t, c)
    if t.get('quoted_price') is None:
        t['quoted_price'] = t['needs']['budget'] + (DELIVERY_FEE if t['needs']['delivery'] else 0)
    if (t.get('guest') or {}).get('kind') == 'regular' and 'recipient' in t['needs']['hidden'] and 'recipient' not in t['asked']:
        # A regular: the shop already knows who lives there.
        t['asked'].append('recipient')


def on_start(s: dict, c: dict) -> None:
    d = _migrate(c)
    pl = _plan(c)
    for t in c['tasks']:
        if _open(t):
            on_task(s, c, t)
    _care_start(s, c, d, pl)
    if pl['mod'] == 'market' and not pl['rules'].get('market_gift'):
        pl['rules']['market_gift'] = True
        if kit.stock(c, 'rose_pink') + 6 <= SPEC['inventory']['capacity']:
            kit.add_lot(c, 'rose_pink', 6, 0, 4, 'gift')
            kit.log(s, c, 'stock', 'Nhà vườn tặng 6 cành hồng phấn mới cắt.')
            FS.flash(pl, 'good', '🚚 Nhà vườn tặng 6 cành hồng phấn mới cắt.')


def _palette_text(p: list) -> str:
    return ' – '.join(COLORS[x]['name'] for x in p)


def _known(t: dict, topic: str) -> bool:
    return topic not in t['needs']['hidden'] or topic in t.get('asked', [])


def _piece_text(n: dict, palette: bool, name: bool = True) -> str:
    parts = ([FORMATS[n['format']]['name']] if name else []) + [f'ngân sách {n["budget"]} xu']
    if palette:
        parts.append(f'tông {_palette_text(n["palette"])}')
    parts.append(f'{n["stems"][0]}–{n["stems"][1]} cành')
    if n['focal']:
        parts.append(f'đúng {n["focal"]["count"]} cành {FLOWERS[n["focal"]["item"]]["name"].lower()}')
    if n['card']:
        parts.append('kèm thiệp viết tay')
    if n['banner']:
        parts.append(f'băng rôn: “{n["banner"]}”')
    return ', '.join(parts)


def known_request(c: dict, t: dict) -> str:
    """The brief as far as the florist has heard it (hidden topics stay out)."""
    n = t['needs']
    occ = OCCASIONS[n['occasion']]['name'].lower()
    pal = _known(t, 'palette')
    if n.get('party'):
        text = f'{len(n["party"])} món dịp {occ}: ' + '; '.join(f'{p["label"].lower()} là {_piece_text(p, pal).lower()}' for p in n['party'])
    else:
        text = f'{FORMATS[n["format"]]["name"]} dịp {occ}, ' + _piece_text(n, pal, name=False)
    if n['delivery']:
        text += f', giao {SLOTS[n["delivery"]]}' if _known(t, 'slot') else ', giao tận nơi (chưa hỏi giờ)'
        text += f' (+{DELIVERY_FEE} xu phí giao)'
    text += '.'
    if n['cats'] and _known(t, 'recipient'):
        text += ' ⚠️ Nhà người nhận có mèo.'
    heard = [n['clues'][k] for k in TOPICS if k in n['clues'] and _known(t, k)]
    return ' '.join([text, n['note'], *heard])



# --- helpers ------------------------------------------------------------------

def _open(t: dict) -> bool:
    return t['career'] == ID and t['status'] not in ('completed', 'cancelled', 'referred')


def _norm(text: str) -> str:
    t = unicodedata.normalize('NFD', (text or '').lower()).replace('đ', 'd')
    return ' '.join(''.join(ch for ch in t if unicodedata.category(ch) != 'Mn').split())


def _letters(text: str) -> str:
    """Banner comparison: accents and letters matter, punctuation/case/spacing do not."""
    t = unicodedata.normalize('NFC', text or '').casefold()
    t = ''.join(ch if (ch.isalnum() or ch.isspace()) else ' ' for ch in t)
    return ' '.join(t.split())


def _has(text: str, words) -> bool:
    return any(re.search(r'(?<![a-z0-9])' + re.escape(w) + r'(?![a-z0-9])', text) for w in words)


def card_tone(occasion: str, card: str | None) -> str | None:
    if not card:
        return None
    fit, wrong = TONE[occasion]
    text = _norm(card)
    if _has(text, wrong):
        return 'wrong'
    return 'fit' if _has(text, fit) else 'plain'


def _next_expiry(c: dict, item: str) -> int | None:
    """Expiry day of the stem kit.take would hand out next (oldest lot first)."""
    lots = [l for l in c['ext']['inv']['lots'] if l['item'] == item and l['expires'] >= c['day'] and l['qty'] > 0]
    lots.sort(key=lambda l: (l['expires'], l['received']))
    return lots[0]['expires'] if lots else None


def _spare(d: dict, item: str) -> list:
    return sorted((x for x in d['spare'] if x['item'] == item), key=lambda x: x['e'])


def _soaking(c: dict) -> list:
    return [t for t in c['tasks'] if _open(t) and t['work']['soak']]


def _wanted(t: dict, item: str) -> bool:
    f = _spec(t)['focal'] if t.get('known') else None
    return bool(f and f['item'] == item)


def _value(c: dict, w: dict) -> int:
    v = sum(kit.price(c, s['i'], ITEM_INDEX[s['i']]['price']) for s in w['stems'])
    if w['base']:
        v += kit.price(c, w['base'], SPEC['prices'][w['base']])
    return min(100000, v)


def _revalue(c: dict, t: dict) -> None:
    t['work']['value'] = _value(c, t['work'])


def _take_many(c: dict, uses: dict) -> int:
    for k, q in uses.items():
        kit.need(kit.stock(c, k) >= q, f'Hết {ITEM_INDEX[k]["name"]} (cần {q} {ITEM_INDEX[k]["unit"]}). Mở Kho để nhập thêm.')
    return sum(kit.take(c, k, q) for k, q in uses.items())


def _unfinished(sp: dict, w: dict) -> str | None:
    """Why this piece cannot leave the bench yet (None = it can)."""
    if not (w['base'] and w['arranged']):
        return 'Hoa chưa cắm/bó xong: vào “Cắm & gói”, chọn kiểu cắm rồi bấm cắm/bó.'
    if w['soak']:
        return 'Nhấc hoa khỏi xô trước.'
    if w['base'] == 'bouquet' and not (w['paper'] and w['ribbon']):
        return 'Bó hoa cần gói giấy và thắt ruy băng trước khi giao.'
    if w['base'] == 'wreath' and not w['banner']:
        return 'Kệ viếng cần băng rôn chữ.'
    if sp['card'] and not w['card']:
        return 'Khách dặn kèm thiệp — viết thiệp trước khi giao.'
    return None


# --- actions ------------------------------------------------------------------
BENCH = ('fl_pick', 'fl_remove', 'fl_cut', 'fl_strip', 'fl_soak', 'fl_lift', 'fl_base', 'fl_push', 'fl_arrange', 'fl_untie',
         'fl_wrap', 'fl_ribbon', 'fl_banner', 'fl_unwrap', 'fl_card', 'fl_dump', 'fl_cover')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _migrate(c)
    pl = _plan(c)
    out = _handle(s, c, d, pl, name, p)
    if name in SPEC['physical']:
        FS.patience_tick(c, ID, p.get('task') or c.get('active_task'), _patience_extra(c, pl))
    return out


def _handle(s: dict, c: dict, d: dict, pl: dict, name: str, p: dict) -> dict:
    if name == 'fl_event':
        return FS.resolve(s, c, pl, EVENT_INDEX, p)
    if name == 'fl_pin':
        return _pin(s, c, d, pl)
    if name == 'fl_water':
        return _water(s, c, d)
    if name == 'fl_pre':
        return _pre(s, c, d, p)
    if name == 'fl_sub':
        return _sub(s, c, d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Công việc không thuộc tiệm hoa.')
    kit.need(t['known'], 'Hỏi khách về dịp tặng và ngân sách trước nhé (bấm “Nghe yêu cầu”).')
    if t.get('quoted_price') is None:
        on_task(s, c, t)
    if name == 'fl_ask':
        return _ask(s, c, t, p)
    if name in ('fl_done', 'fl_tab'):
        kit.need(_is_set(t), 'Đơn này chỉ có một món.')
        result = _set_action(s, c, t, name, p)
    elif name == 'fl_deliver':
        return _deliver(s, c, d, pl, t, p)
    else:
        kit.need(name in BENCH, 'Thao tác tiệm hoa không hợp lệ.')
        if _is_set(t) and t['pieces'][t['cur']] is not None:
            raise kit.eng().GameError(f'Món {t["cur"] + 1} đã xong. Chọn món khác ở phiếu đơn, hoặc giao cả bộ.')
        result = _act(s, c, d, pl, t, name, p)
    if _open(t):
        _revalue(c, t)
    return result


def _ask(s: dict, c: dict, t: dict, p: dict) -> dict:
    """Consultation: one question, one answer (a chatty guest adds one more)."""
    n = t['needs']
    topic = _one_of(p.get('topic'), TOPICS, 'Chọn điều muốn hỏi khách.')
    kit.need(topic in n['hidden'], 'Khách đã nói rõ điều này rồi.')
    kit.need(topic not in t['asked'], 'Bạn đã hỏi điều này rồi.')
    kind = (t.get('guest') or {}).get('kind')
    told = [topic]
    t['asked'].append(topic)
    if kind == 'chatty':
        more = [k for k in n['hidden'] if k not in t['asked']]
        if more:
            t['asked'].append(more[0])
            told.append(more[0])
    t['patience'] = max(25, t.get('patience', 100) - (ASK_COST_RUSH if kind == 'rush' else ASK_COST))
    lines = [n['clues'][k] for k in told]
    for line in lines:
        kit.log(s, c, 'fact', line, t['npc'], t['id'])
    msg = f'“{lines[0]}”'
    if len(lines) > 1:
        msg += f' Khách vui chuyện kể luôn: “{lines[1]}”'
    return dict(message=msg, topics=told)


def _set_action(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    """Sets: finish pieces one by one; switch between pieces that are not started."""
    pieces, cur, w = t['pieces'], t['cur'], t['work']
    labels = [x['label'] for x in t['needs']['party']]
    if name == 'fl_tab':
        i = kit.integer(p.get('index'), 0, len(pieces) - 1)
        kit.need(i != cur, 'Đang làm món này rồi.')
        kit.need(not w['soak'], 'Nhấc hoa khỏi xô trước.')
        busy = pieces[cur] is None and _started(w)
        kit.need(not busy, f'Món {cur + 1} đang làm dở. Làm xong (hoặc bỏ bó làm lại) rồi mới đổi món.')
        if pieces[i] is not None:
            # Reopen a finished piece: take it back to the bench.
            t['work'], pieces[i] = pieces[i], None
        t['cur'] = i
        return dict(message=f'Đang làm món {i + 1}: {labels[i].lower()}.')
    kit.need(pieces[cur] is None, f'Món {cur + 1} đã xong rồi.')
    why = _unfinished(_spec(t), w)
    kit.need(not why, why or '')
    w['value'] = _value(c, w)
    pieces[cur] = w
    t['work'] = _empty_work()
    pending = [i for i, x in enumerate(pieces) if x is None]
    if pending:
        t['cur'] = pending[0]
        return dict(message=f'Xong món {cur + 1}, đặt sang bàn chờ. Tiếp theo: {labels[pending[0]].lower()}.')
    return dict(message='Đủ món rồi, giao cả bộ thôi!')


def _act(s: dict, c: dict, d: dict, pl: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    sp = _spec(t)
    w = t['work']
    occ = n['occasion']
    if name == 'fl_pick':
        item = _one_of(p.get('item'), FLOWERS, 'Loại hoa này tiệm không có.')
        f = FLOWERS[item]
        kit.need(f['unlock'] <= kit.level(c) or _wanted(t, item), f'{f["name"]} mở ở cấp {f["unlock"]}.')
        kit.need(not w['arranged'], 'Bó đã hoàn thành dáng. Bấm “Tháo ra” ở “Cắm & gói” nếu muốn thêm cành.')
        kit.need(not w['soak'], 'Hoa đang ngâm trong xô: vào “Sơ chế”, bấm “Nhấc ra” trước đã.')
        kit.need(len(w['stems']) < MAX_STEMS, f'Tối đa {MAX_STEMS} cành một đơn.')
        spare = _spare(d, item)
        if spare:
            x = spare[0]
            d['spare'].remove(x)
            exp, cost = x['e'], x['k']
        else:
            exp = _next_expiry(c, item)
            kit.need(exp is not None, f'Hết {f["name"]}. Mở Kho để nhập thêm nhé.')
            cost = kit.take(c, item, 1)
        w['stems'].append(dict(i=item, e=exp, k=cost, c=0, s=False, h=False))
        w['cost'] += cost
        kit.start_work(t)
        left = exp - c['day']
        tag = ' · ⚠️ sắp héo' if left <= 0 else ' · còn 1 ngày' if left == 1 else ''
        return dict(message=f'Lấy 1 cành {f["name"].lower()}{tag}.')
    if name == 'fl_remove':
        item = _one_of(p.get('item'), FLOWERS, 'Loại hoa này không có trên bàn.')
        kit.need(not w['arranged'] and not w['soak'], 'Nhấc hoa khỏi xô (Sơ chế) hoặc tháo bó (Cắm & gói) trước.')
        idx = max((i for i, st in enumerate(w['stems']) if st['i'] == item), default=None)
        kit.need(idx is not None, 'Không có cành này trên bàn.')
        st = w['stems'].pop(idx)
        w['cost'] = max(0, w['cost'] - st['k'])
        if st['c'] == 0 and len(d['spare']) < 60:
            d['spare'].append(dict(item=item, e=st['e'], k=st['k']))
            return dict(message=f'Đã cắm lại cành {FLOWERS[item]["name"].lower()} vào xô chờ.')
        kit.waste(c, item, 1, st['k'], 'Cành đã cắt bị loại khỏi bó')
        return dict(message=f'Cành {FLOWERS[item]["name"].lower()} đã cắt gốc nên không dùng lại được, ghi hao hụt.')
    if name == 'fl_cut':
        angle = _one_of(p.get('angle'), ('angled', 'straight'), 'Chọn cắt xéo hoặc cắt thẳng.')
        kit.need(not w['arranged'] and not w['soak'], 'Không cắt gốc lúc này được.')
        fresh = [st for st in w['stems'] if st['c'] == 0]
        kit.need(fresh, 'Không còn cành nào chưa cắt gốc.')
        for st in fresh:
            st['c'] = 1 if angle == 'angled' else 2
        if angle == 'straight':
            t['mistakes'] += 1
            return dict(message=f'Đã cắt thẳng {len(fresh)} gốc. Gốc thẳng dễ bị bịt đáy xô, hoa hút nước kém hơn cắt xéo 45°.')
        return dict(message=f'Đã cắt xéo 45° {len(fresh)} gốc dưới vòi nước, bỏ đoạn gốc thâm.')
    if name == 'fl_strip':
        kit.need(not w['arranged'] and not w['soak'], 'Không tuốt lá lúc này được.')
        todo = [st for st in w['stems'] if not st['s']]
        kit.need(todo, 'Các cành đều đã tuốt lá.')
        for st in todo:
            st['s'] = True
        return dict(message=f'Đã tuốt lá và gai phần gốc của {len(todo)} cành — không để lá nào ngập dưới mực nước.')
    if name == 'fl_soak':
        kit.need(w['stems'], 'Chưa có cành nào để ngâm.')
        kit.need(not w['arranged'], 'Bó đã hoàn thành dáng.')
        kit.need(not w['soak'], 'Hoa đang ngâm rồi.')
        kit.need(all(st['c'] for st in w['stems']), 'Cắt gốc trước khi ngâm (bấm “Cắt xéo 45°”) — gốc cũ đã khô, hút nước kém.')
        kit.need(len(_soaking(c)) < MAX_BUCKETS, 'Cả hai xô ngâm đang có hoa của đơn khác. Mở đơn đó, bấm “Nhấc ra” để trống một xô.')
        w['soak'] = round(kit.now(), 3)
        return dict(message=f'Đã thả hoa vào xô nước mát. Ngâm ít nhất {_soak_min(c)} giây cho cành hút no nước.')
    if name == 'fl_lift':
        kit.need(w['soak'], 'Hoa không ở trong xô.')
        sec = max(0.0, kit.now() - w['soak'])
        w['soak'] = None
        w['soaked'] = round(min(sec, 9999.0), 1)
        need_sec = _soak_min(c)
        if sec >= need_sec:
            for st in w['stems']:
                st['h'] = True
            return dict(message=f'Hoa đã hút no nước ({sec:.1f} giây), cánh căng lại.')
        return dict(message=f'Mới ngâm {sec:.1f} giây — cành chưa kịp hút nước (cần {need_sec} giây). Có thể ngâm lại.')
    if name == 'fl_base':
        kind = _one_of(p.get('kind'), FORMATS, 'Kiểu cắm không có trong tiệm.')
        fm = FORMATS[kind]
        kit.need(w['base'] is None, 'Đã chọn đế/kiểu cắm cho đơn này.')
        kit.need(fm['unlock'] <= kit.level(c) or sp['format'] == kind, f'{fm["name"]} mở ở cấp {fm["unlock"]}.')
        w['cost'] += _take_many(c, fm['uses'])
        w['base'] = kind
        if fm['foam']:
            w['foam'] = dict(start=round(kit.now(), 3), pushed=False)
        kit.start_work(t)
        extra = f' Thả mút nổi trên mặt nước, để nó tự chìm (~{FOAM_MIN} giây).' if fm['foam'] else ''
        return dict(message=f'Đã chuẩn bị {fm["name"].lower()}.{extra}')
    if name == 'fl_push':
        kit.need(w['foam'] and not w['arranged'], 'Không có mút đang ngâm.')
        kit.need(not w['foam']['pushed'], 'Mút đã bị ấn chìm rồi.')
        w['foam']['pushed'] = True
        t['mistakes'] += 1
        return dict(message='Mút chìm ngay… nhưng lõi bên trong còn khô, cành cắm vào chỗ đó sẽ thiếu nước.')
    if name == 'fl_arrange':
        kit.need(w['base'], 'Chọn kiểu cắm trước: “Cắm & gói”, mục 1 · Kiểu cắm.')
        kit.need(not w['arranged'], 'Đã hoàn thành dáng.')
        kit.need(len(w['stems']) >= 3, 'Cần ít nhất 3 cành: lấy thêm hoa ở “Tủ hoa”.')
        kit.need(not w['soak'], 'Hoa còn trong xô: vào “Sơ chế”, bấm “Nhấc ra” trước.')
        kit.need(all(st['c'] for st in w['stems']), 'Còn cành chưa cắt gốc: vào “Sơ chế”, bấm “Cắt xéo 45°”.')
        if w['foam']:
            sec = kit.now() - w['foam']['start']
            kit.need(w['foam']['pushed'] or sec >= FOAM_MIN, f'Mút đang tự ngấm nước (còn {max(0.0, FOAM_MIN - sec):.0f} giây). Đừng ấn xuống — chờ nó tự chìm.')
            w['foam_ok'] = not w['foam']['pushed']
        w['arranged'] = True
        how = {'bouquet': 'Đã bó xoắn ốc, buộc dây ở điểm chụm.', 'vase': 'Đã đổ nước sạch và gói dưỡng hoa vào bình, cắm dáng tròn.',
               'basket': 'Đã cắm dáng tỏa tròn vào mút, che mút bằng lá.', 'wreath': 'Đã cắm kín mặt kệ viếng theo dáng tròn trang nghiêm.'}[w['base']]
        return dict(message=how)
    if name == 'fl_untie':
        kit.need(w['arranged'], 'Bó chưa hoàn thành dáng.')
        kit.need(not w['paper'] and not w['ribbon'] and not w['banner'], 'Đã gói/buộc ruy băng, không tháo được nữa. Đổ bó để làm lại.')
        w['arranged'] = False
        w['cover'] = False
        if FORMATS[w['base']]['foam']:
            t['mistakes'] += 1
            return dict(message='Đã rút hoa ra, mút bị thủng lỗ nên giữ nước kém hơn.')
        return dict(message='Đã tháo dây, có thể thêm hoặc bớt cành.')
    if name == 'fl_wrap':
        kit.need(w['base'] == 'bouquet', 'Chỉ bó hoa cầm tay mới gói giấy.')
        kit.need(w['arranged'], 'Bó hoa xong trước (bấm “Bó xoắn ốc & buộc dây”), rồi mới gói giấy.')
        kit.need(w['paper'] is None, 'Bó đã gói giấy.')
        paper = _one_of(p.get('paper'), PAPERS, 'Loại giấy này tiệm không có.')
        w['cost'] += kit.take(c, PAPERS[paper]['item'], 1)
        w['paper'] = paper
        return dict(message=f'Đã gói {PAPERS[paper]["name"].lower()} hai lớp, gấp nếp gọn.')
    if name == 'fl_ribbon':
        kit.need(w['arranged'], 'Cắm/bó hoa xong trước (ở “Cắm & gói”), rồi mới thắt ruy băng.')
        kit.need(w['base'] != 'bouquet' or w['paper'], 'Gói giấy trước (chọn một màu giấy ở “Cắm & gói”), rồi mới thắt ruy băng.')
        kit.need(w['ribbon'] is None, 'Đã thắt ruy băng.')
        color = _one_of(p.get('color'), RIBBONS, 'Màu ruy băng không có.')
        w['cost'] += kit.take(c, 'ribbon', 1)
        w['ribbon'] = color
        return dict(message=f'Đã thắt nơ ruy băng màu {RIBBONS[color]["name"].lower()}.')
    if name == 'fl_banner':
        kit.need(w['base'] == 'wreath', 'Băng rôn chữ chỉ dùng cho kệ hoa viếng.')
        kit.need(w['arranged'], 'Cắm xong kệ rồi mới treo băng rôn.')
        text = kit.text(p.get('text'), 60, 2)
        w['cost'] += kit.take(c, 'banner', 1)
        w['banner'] = text
        return dict(message=f'Đã in và treo băng rôn: “{text}”. Đọc lại từng chữ trước khi giao nhé.')
    if name == 'fl_unwrap':
        kit.need(w['paper'] or w['ribbon'], 'Chưa gói giấy hay thắt ruy băng.')
        kit.need(not w['soak'], 'Nhấc hoa khỏi xô trước.')
        w['paper'] = None
        w['ribbon'] = None
        w['cover'] = False
        return dict(message='Đã gỡ giấy gói và ruy băng (vật liệu cũ bỏ đi). Có thể tháo bó hoặc gói lại.')
    if name == 'fl_card':
        text = kit.text(p.get('text'), 160, 3)
        w['cost'] += kit.take(c, 'card', 1)
        w['card'] = text
        tone = card_tone(occ, text)
        return dict(message='Đã viết thiệp tay' + {'fit': ', lời chúc hợp dịp.', 'plain': '. Lời hơi chung chung — thêm một câu đúng dịp sẽ ấm hơn.',
                                                    'wrong': ' — ⚠️ lời thiệp có vẻ không hợp dịp này!'}[tone])
    if name == 'fl_cover':
        kit.need(pl['mod'] == 'rain', 'Hôm nay trời không mưa, không cần bọc nylon.')
        kit.need(n['delivery'], 'Khách nhận hoa tại tiệm, không cần bọc chống mưa.')
        kit.need(w['arranged'] and (w['base'] != 'bouquet' or w['paper']), 'Cắm/gói xong rồi mới bọc nylon.')
        kit.need(not w['cover'], 'Đã bọc nylon rồi.')
        w['cover'] = True
        return dict(message='Đã bọc nylon trong suốt chống mưa, chừa lỗ thoáng cho hoa thở.')
    if name == 'fl_dump':
        kit.confirm(p, 'Xác nhận bỏ bó hoa đang làm; hoa và vật liệu đã dùng ghi hao hụt.')
        kit.need(w['stems'] or w['base'], 'Bàn đang trống.')
        kit.need(not w['soak'], 'Nhấc hoa khỏi xô trước.')
        kit.waste(c, 'bouquet', 1, w['cost'], 'Bỏ bó hoa làm lại')
        t['work'] = _empty_work()
        t['mistakes'] += 1
        d['dumped'] += 1
        return dict(message='Đã bỏ bó hoa. Làm lại từ đầu nhé.')
    raise kit.eng().GameError('Thao tác tiệm hoa không hợp lệ.')


def _refusal(sp: dict, w: dict, day: int) -> str | None:
    """Mistakes the recipient will not accept (one piece; sp = its brief)."""
    occ = sp['occasion']
    items = {st['i'] for st in w['stems']}
    if w['base'] != sp['format']:
        return f'khách đặt {FORMATS[sp["format"]]["name"].lower()}, không phải {FORMATS[w["base"]]["name"].lower()}.'
    taboo = [FLOWERS[i]['name'].lower() for i in items if occ in FLOWERS[i]['taboo']]
    if taboo:
        return f'{", ".join(taboo)} không hợp dịp {OCCASIONS[occ]["name"].lower()}.'
    if occ == 'condolence' and ((w['paper'] and PAPERS[w['paper']]['color'] == 'pink') or w['ribbon'] in ('red', 'pink', 'gold')):
        return 'giấy gói hoặc ruy băng màu rực không dùng để đi viếng.'
    if any(st['e'] < day for st in w['stems']):
        return 'có cành hoa đã héo rũ. Bỏ cành đó ra và thay cành tươi.'
    if sp['banner'] and _letters(w['banner']) != _letters(sp['banner']):
        return f'băng rôn ghi “{w["banner"]}” nhưng gia đình cần “{sp["banner"]}”. In lại băng rôn.'
    if card_tone(occ, w['card']) == 'wrong':
        return 'lời thiệp không hợp dịp này. Viết lại thiệp.'
    return None


def _who(t: dict) -> str:
    people = kit.eng().NPC_INDEX
    return people[t['npc']].get('display_name') or 'Khách' if t['npc'] in people else 'Khách'


def _refusal_line(sp: dict, w: dict, day: int) -> str:
    """What the customer says about flowers the recipient handed back (same order as _refusal)."""
    occ = sp['occasion']
    items = {st['i'] for st in w['stems']}
    if w['base'] != sp['format']:
        return f'Đặt {FORMATS[sp["format"]]["name"].lower()} mà giao {FORMATS[w["base"]]["name"].lower()}, phải chờ làm lại.'
    taboo = [FLOWERS[i]['name'].lower() for i in items if occ in FLOWERS[i]['taboo']]
    if taboo:
        return f'Hoa dịp {OCCASIONS[occ]["name"].lower()} mà có {", ".join(taboo)}, nhìn ngại quá, phải chờ làm lại.'
    if any(st['e'] < day for st in w['stems']):
        return 'Có cành hoa héo rũ, phải chờ thay cành tươi.'
    if sp['banner'] and _letters(w['banner'] or '') != _letters(sp['banner']):
        return 'Băng rôn in sai chữ, phải chờ in lại.'
    if card_tone(occ, w['card']) == 'wrong':
        return 'Lời thiệp không hợp dịp, phải chờ viết lại.'
    return 'Đi viếng mà giấy gói, ruy băng màu rực, phải chờ gói lại.'


def _piece_slip(t: dict, code: str, i: int | None, sev: int, text: str, note: str) -> None:
    if i is None:
        cq.slip(t, code, sev, text, note)
    else:
        cq.slip(t, f'{code}{i}', sev, f'Món {i + 1}: {text}', f'món {i + 1}: {note}')


MIXED = dict(proposal='Cầu hôn mà bó có hoa vàng, người ta tưởng mình chỉ là bạn.',
             apology='Xin lỗi mà tặng hoa vàng, nhìn như hờ hững.')


def _record_slips(c: dict, t: dict, made: list, slot: str | None, pl: dict) -> list[int]:
    """At the hand-off: what the customer finds against the brief. Returns pieces to re-wrap."""
    many = len(made) > 1
    faulty = []
    for i, w in enumerate(made):
        at = i if many else None
        sp = _spec(t, i) if many else t['needs']
        before = len(cq.slips(t))
        occ = sp['occasion']
        counts = {}
        for st in w['stems']:
            counts[st['i']] = counts.get(st['i'], 0) + 1
        if sp['cats'] and any(FLOWERS[k].get('cats') == 'toxic' for k in counts):
            cq.slip(t, 'cats', 3, 'Nhà có mèo mà tiệm vẫn cắm hoa ly. Con mèo gặm lá, phải chạy đi thú y cả đêm.',
                    'cắm hoa ly cho nhà có mèo', safety=True)
        if any(occ in FLOWERS[k]['bad'] for k in counts):
            _piece_slip(t, 'mixed', at, 2, MIXED.get(occ, 'Có hoa dễ bị hiểu sai ý, người nhận hơi chạnh lòng.'), 'có hoa dễ hiểu sai ý')
        allowed = set(sp['palette']) | {'green'}
        # A flower already counted as a mixed message is not blamed twice for its colour.
        off = sorted({FLOWERS[k]['color'] for k in counts if FLOWERS[k]['color'] not in allowed and FLOWERS[k]['role'] != 'filler'
                      and occ not in FLOWERS[k]['bad']})
        if off:
            got = ', '.join(COLORS[x]['name'] for x in off)
            _piece_slip(t, 'palette', at, 2, f'Dặn tông {_palette_text(sp["palette"])} mà bó lại có màu {got}.', f'lệch tông: {got}')
        f = sp['focal']
        if f and counts.get(f['item'], 0) != f['count']:
            have = counts.get(f['item'], 0)
            name = FLOWERS[f['item']]['name'].lower()
            sev = 1 if abs(have - f['count']) <= 2 else 2
            _piece_slip(t, 'count', at, sev, f'Đặt {f["count"]} cành {name} mà bó có {have}.', f'{have} cành {name} thay vì {f["count"]}')
        if sp['card'] and card_tone(occ, w['card']) == 'plain':
            _piece_slip(t, 'card', at, 1, 'Lời thiệp chung chung, chẳng nhắc gì tới dịp này.', 'lời thiệp chung chung')
        if w['stems'] and min(st['e'] for st in w['stems']) <= c['day']:
            _piece_slip(t, 'wilting', at, 1, 'Hoa về tới nơi đã rũ cánh, chắc mai là héo.', 'có cành sắp héo')
        ratio = w['value'] / max(1, sp['budget'])
        if ratio < 0.7:
            _piece_slip(t, 'value', at, 2 if ratio < 0.5 else 1, f'Trả {sp["budget"]} xu mà bó hoa lèo tèo.', f'giá trị hoa ~{w["value"]}/{sp["budget"]} xu')
        if pl['mod'] == 'rain' and sp['delivery'] and not w.get('cover'):
            _piece_slip(t, 'rain', at, 1, 'Hoa ướt mưa, giấy gói nhũn cả.', 'không bọc nylon khi mưa')
        if pl['rules'].get('bruised') and counts.get('rose_red'):
            _piece_slip(t, 'bruised', at, 1, 'Hồng đỏ dập mép cánh, nhìn không tươi.', 'hồng đỏ dập cánh')
        if len(cq.slips(t)) > before and not cq.safety(t):
            faulty.append(i)
    n = t['needs']
    if slot and n['delivery'] and slot != n['delivery']:
        order = list(SLOTS)
        if order.index(slot) > order.index(n['delivery']):
            cq.slip(t, 'late', 1, f'Hẹn giao {SLOTS[n["delivery"]]} mà tới {SLOTS[slot]} hoa mới tới.', 'giao trễ hẹn')
        else:
            cq.slip(t, 'late', 1, f'Hẹn giao {SLOTS[n["delivery"]]} mà giao sớm lúc {SLOTS[slot]}, nhà không ai nhận.', 'giao lệch giờ hẹn')
    return faulty


def _deliver(s: dict, c: dict, d: dict, pl: dict, t: dict, p: dict) -> dict:
    kit.confirm(p, 'Xác nhận giao hoa.')
    n = t['needs']
    many = _is_set(t)
    pieces, cur, w = t['pieces'], t['cur'], t['work']
    if not many or pieces[cur] is None:
        why = _unfinished(_spec(t), w)
        kit.need(not why, (f'Món {cur + 1}: ' if many else '') + (why or ''))
    if many:
        missing = [str(i + 1) for i, x in enumerate(pieces) if x is None and i != cur]
        kit.need(not missing, 'Còn món ' + ', '.join(missing) + ' chưa xong. Làm xong từng món rồi giao cả bộ nhé.')
    ev = FS.open_event(pl)
    kit.need(not ev, 'Có chuyện cần bạn quyết trước: ' + (EVENT_INDEX[ev['id']]['title'] if ev else '') + '.')
    slot = None
    if n['delivery']:
        slot = _one_of(p.get('slot'), SLOTS, 'Chọn khung giờ giao ở “Thiệp & giao” trước nhé.')
    made = [x if x is not None else w for x in pieces] if many else [w]
    for i, work in enumerate(made):
        why = _refusal(_spec(t, i), work, c['day'])
        if not why:
            continue
        if many:
            why = f'món {i + 1}: {why}'
            # The accepted pieces wait on the side; the returned one comes back to the bench.
            if pieces[cur] is None:
                pieces[cur] = w
            t['cur'] = i
            t['work'] = pieces[i]
            pieces[i] = None
        t['refused'] += 1
        t['mistakes'] += 1
        pl['refused'] += 1
        # The customer remembers the flowers coming back (one small slip after the redo). The piece is
        # remade like a sent-back order: once fixed, the wait is only a grumble, never money off too.
        line = _refusal_line(_spec(t, i), work, c['day'])
        cq.downgrade(t, 'returned', f'Món {i + 1}: {line}' if many else line, 'người nhận trả hoa một lần')
        t['remade'] = True
        kit.log(s, c, 'refused', 'Người nhận không nhận hoa: ' + why, t['npc'], t['id'])
        FS.flash(pl, 'bad', '↩️ Không nhận: ' + why)
        return dict(message='Không nhận: ' + why, refused=True)
    for work in made:
        work['slot'] = slot
        work['value'] = _value(c, work)
    if slot and slot != n['delivery']:
        t['mistakes'] += 1
    faulty = _record_slips(c, t, made, slot, pl)
    if cq.slips(t) and not t['mistakes']:
        t['mistakes'] = 1
    if faulty and cq.decide(c, t, remake=True) == 'remake':
        cq.react(s, c, t, t['quoted_price'], remake=True, who=_who(t))
        first = cq.slips(t)[0]['text']
        if many and faulty:
            if pieces[cur] is None:
                pieces[cur] = w
            i = faulty[0]
            t['cur'] = i
            t['work'] = pieces[i]
            pieces[i] = None
        if c['life'].get('mode') != 'calm':
            t['patience'] = max(25, t.get('patience', 100) - 10)
        cq.downgrade(t, 'returned', f'{first} Phải làm lại.', 'phải làm lại')
        kit.log(s, c, 'refused', 'Khách trả hoa: ' + first, t['npc'], t['id'])
        FS.flash(pl, 'bad', '↩️ Khách trả hoa: ' + first)
        return dict(message=f'{_who(t)}: “{first}” Khách đưa hoa lại, sửa giúp khách nhé.', refused=True, correct=False)
    rules = {k: pl['rules'][k] for k in ('bruised', 'warm') if pl['rules'].get(k)}
    t['served'] = dict(work=copy.deepcopy(made[0]), pieces=copy.deepcopy(made), day=c['day'], mod=pl['mod'], rules=rules)
    if many:
        t['pieces'] = made
        t['work'] = _empty_work()
    d['delivered'] += len(made)
    d['wreaths'] += sum(1 for x in made if x['base'] == 'wreath')
    kit.metric(c, 'bouquets_delivered', len(made))
    r = cq.react(s, c, t, t['quoted_price'], who=_who(t))
    price = r['pay']
    how = f'giao lúc {SLOTS[slot]}' if slot else 'trao tận tay tại tiệm'
    kit.complete(s, c, t, price, f'Bạn đã làm “{t["title"]}” và {how}.')
    told = _visit(d, int(t['npc'].rsplit('_', 1)[1]) - 1)
    lines = FS.after_serve(s, c, ID, pl, t, _walkin_chance(c, pl))
    lines += ['📒 Ghi vào sổ khách quen: ' + x for x in told]
    lines += _after_rules(s, c, pl, t)
    opened = FS.trigger(s, c, pl, EVENT_INDEX)
    if opened:
        lines.append('⚡ ' + EVENT_INDEX[opened['id']]['title'])
    else:
        perfect = t['mistakes'] == 0 and not t['refused']
        FS.flash(pl, 'good' if perfect else 'info', ('⭐ Hoàn hảo! ' if perfect else '💐 Đã giao. ') + ' '.join(lines[:2]))
    head = f'Đã {how} · +{price} xu.' + (' ' + r['message'] if r['message'] else '')
    return dict(message=head + (' ' + ' '.join(lines) if lines else ' Người nhận sẽ để lại lời nhắn.'), celebrate=True)


# --- review -------------------------------------------------------------------

def _piece_rows(sp: dict, w: dict, day: int, ctx: dict) -> list[dict]:
    """Meaning, look, freshness, card/banner and value of one piece."""
    occ = sp['occasion']
    stems = w['stems']
    rules = ctx.get('rules') or {}
    counts = {}
    for st in stems:
        counts[st['i']] = counts.get(st['i'], 0) + 1
    rows = []
    # Meaning of the flowers for the occasion.
    score, notes = 5, []
    bad = [i for i in counts if occ in FLOWERS[i]['bad']]
    if bad:
        score -= 2
        notes.append(BAD_NOTE.get(occ, 'có hoa dễ hiểu sai ý'))
    if sp['focal']:
        have = counts.get(sp['focal']['item'], 0)
        if have != sp['focal']['count']:
            score -= 1 if abs(have - sp['focal']['count']) <= 2 else 2
            notes.append(f'{have} cành {FLOWERS[sp["focal"]["item"]]["name"].lower()} thay vì {sp["focal"]["count"]}')
    focal_total = sum(q for i, q in counts.items() if FLOWERS[i]['role'] == 'focal')
    if OCCASIONS[occ]['celebrate'] and focal_total % 2 == 0 and not (sp['focal'] and counts.get(sp['focal']['item'], 0) == sp['focal']['count']):
        score -= 1
        notes.append(f'{focal_total} hoa chính — số chẵn (tiệm quy ước hoa mừng dùng số lẻ)')
    if not notes:
        good = [FLOWERS[i]['name'].lower() for i in counts if occ in FLOWERS[i]['good'] and FLOWERS[i]['role'] == 'focal']
        notes.append(('đúng ý nghĩa: ' + ', '.join(good[:2])) if good else 'hoa hợp dịp')
    rows.append(dict(key='meaning', label='Ý nghĩa hoa', score=max(1, score), note='; '.join(notes)))
    # Colour palette, materials and composition.
    score, notes = 5, []
    allowed = set(sp['palette']) | {'green'}
    off = sorted({FLOWERS[i]['color'] for i in counts if FLOWERS[i]['color'] not in allowed and FLOWERS[i]['role'] != 'filler'})
    if off:
        score -= min(2, len(off))
        notes.append('lệch tông: ' + ', '.join(COLORS[x]['name'] for x in off))
    neutral_ribbons = {'white', 'black'} if occ == 'condolence' else {'white', 'gold'}
    if w['paper'] and PAPERS[w['paper']]['color'] and PAPERS[w['paper']]['color'] not in allowed:
        score -= 1
        notes.append('giấy gói lệch tông')
    if w['ribbon'] and w['ribbon'] not in allowed and w['ribbon'] not in neutral_ribbons:
        score -= 1
        notes.append('ruy băng lệch tông')
    total = len(stems)
    if total < sp['stems'][0]:
        score -= 1
        notes.append(f'bó hơi thưa ({total} cành)')
    elif total > sp['stems'][1]:
        score -= 1
        notes.append(f'quá dày ({total} cành)')
    if sp['cats']:
        risky = [FLOWERS[i]['name'].lower() for i in counts if FLOWERS[i].get('cats') == 'caution']
        if risky:
            score -= 1
            notes.append(', '.join(risky) + ' không tốt nếu mèo gặm')
    elif sp['format'] != 'wreath' and not any(FLOWERS[i]['role'] in ('filler', 'green') for i in counts):
        score -= 1
        notes.append('thiếu lá/hoa phụ nên bó bị cứng')
    if rules.get('bruised') and 'rose_red' in counts:
        score -= 1
        notes.append('hồng đỏ dập mép cánh')
    rows.append(dict(key='look', label='Màu sắc & bố cục', score=max(1, score), note=', '.join(notes) or 'hài hòa, đúng tông'))
    # Freshness and conditioning.
    lefts = [st['e'] - day for st in stems] or [3]
    worst = min(lefts)
    score = 5 if worst >= 2 else 4 if worst == 1 else 2
    notes = ['có cành sắp héo'] if worst <= 0 else ['có cành chỉ còn 1 ngày'] if worst == 1 else []
    if any(not st['s'] for st in stems):
        score -= 1
        notes.append('lá dưới mực nước chưa tuốt, nước nhanh đục')
    if any(st['c'] == 2 for st in stems):
        score -= 1
        notes.append('gốc cắt thẳng, hút nước kém')
    if FORMATS[sp['format']]['soak'] and any(not st['h'] for st in stems):
        score -= 1
        notes.append('chưa ngâm nước đủ')
    if w['foam_ok'] is False:
        score -= 1
        notes.append('mút bị ấn chìm, lõi khô')
    if ctx.get('mod') == 'rain' and sp['delivery'] and not w.get('cover'):
        score -= 1
        notes.append('hoa ướt mưa, giấy gói nhũn vì không bọc nylon')
    warm = rules.get('warm') or 0
    if warm and score > 5 - warm:
        score = 5 - warm
        notes.append('hoa mềm cánh vì tủ mát mất điện')
    rows.append(dict(key='fresh', label='Độ tươi & sơ chế', score=max(1, score), note=', '.join(notes) or 'cành cắt xéo, tuốt lá, hút no nước'))
    # Card / banner.
    if sp['card']:
        tone = card_tone(occ, w['card'])
        rows.append(dict(key='card', label='Thiệp', score={'fit': 5, 'plain': 3}.get(tone, 2), note={'fit': 'lời thiệp đúng dịp', 'plain': 'lời chúc hơi chung chung'}.get(tone, 'thiếu thiệp')))
    elif sp['banner']:
        rows.append(dict(key='card', label='Băng rôn', score=5, note='chữ in đúng, trang nghiêm'))
    # Value for the agreed budget.
    ratio = w['value'] / max(1, sp['budget'])
    score = 2 if ratio < 0.5 else 3 if ratio < 0.7 else 4 if ratio < 0.85 else 5
    rows.append(dict(key='value', label='Xứng ngân sách', score=score, note=f'giá trị hoa ~{w["value"]}/{sp["budget"]} xu'))
    return rows


def judge(t: dict, work: dict, day: int, ctx: dict | None = None) -> list[dict]:
    """Review rows for a single-piece order (kept for tools and tests)."""
    return _piece_rows(t['needs'], work, day, ctx or {}) + [_time_row(t, work)]


def _time_row(t: dict, w: dict) -> dict:
    n = t['needs']
    if n['delivery']:
        ok = w['slot'] == n['delivery']
        return dict(key='delivery', label='Giao đúng hẹn', score=5 if ok else 2, note=f'giao {SLOTS.get(w["slot"], "?")}' + ('' if ok else f', hẹn {SLOTS[n["delivery"]]}'))
    patience = t.get('patience', 100)
    return dict(key='speed', label='Thời gian chờ', score=5 if patience >= 85 else 4 if patience >= 65 else 3 if patience >= 45 else 2, note=f'kiên nhẫn còn {patience}%')


def feedback(c: dict, t: dict) -> dict:
    sv = t['served']
    day = sv.get('day', c['day'])
    ctx = dict(mod=sv.get('mod', 'normal'), rules=sv.get('rules') or {})
    works = sv.get('pieces') or [sv['work']]
    many = len(works) > 1
    per = [_piece_rows(_spec(t, i) if many else t['needs'], w, day, ctx) for i, w in enumerate(works)]
    rows, order = [], []
    for rs in per:
        for r in rs:
            if r['key'] not in order:
                order.append(r['key'])
    for key in order:
        cand = [(i, r) for i, rs in enumerate(per) for r in rs if r['key'] == key]
        i, worst = min(cand, key=lambda x: x[1]['score'])
        row = dict(worst)
        if many:
            row['note'] = (f'món {i + 1}: ' + row['note']) if row['score'] < 5 else 'cả bộ: ' + row['note']
        rows.append(row)
    rows.append(_time_row(t, works[0]))
    if t['refused']:
        rows.append(dict(key='care', label='Cẩn thận', score=2, note='người nhận phải trả hoa một lần'))
    cap = 3 if (t.get('guest') or {}).get('kind') == 'picky' and t['mistakes'] else 5
    return dict(criteria=rows, cap=cap)


# --- projections & validation ----------------------------------------------------

def public_task(t: dict) -> dict:
    v = copy.deepcopy(t)
    if v.get('gen') != GEN:
        _upgrade_task(v, None)
    v['soak_min'] = SOAK_MIN
    v['foam_min'] = FOAM_MIN
    v['pieces_total'] = _total(v)
    if not v['known']:
        v['needs'] = None
        v['card_tone'] = None
        v['quoted_price'] = None
        return v
    n = v['needs']
    v['card_tone'] = card_tone(n['occasion'], v['work']['card'])
    n['deliver'] = bool(n['delivery'])
    asked = set(v.get('asked') or [])
    for topic in n['hidden']:
        if topic in asked:
            continue
        # Not asked yet: the answer stays with the customer.
        if topic == 'palette':
            n['palette'] = None
            for part in n.get('party') or []:
                part['palette'] = None
        elif topic == 'recipient':
            n['cats'] = None
        elif topic == 'slot':
            n['delivery'] = None
        n['clues'].pop(topic, None)
    return v


def public_data(c: dict) -> dict:
    d = copy.deepcopy(kit.data(c))
    cooler = {}
    for item in FLOWERS:
        spare = _spare(kit.data(c), item)
        nxt = spare[0]['e'] if spare else _next_expiry(c, item)
        by_left = {}
        for l in c['ext']['inv']['lots']:
            if l['item'] == item and l['expires'] >= c['day'] and l['qty'] > 0:
                k = min(3, l['expires'] - c['day'])
                by_left[k] = by_left.get(k, 0) + l['qty']
        stages = dict(bud=0, bloom=0, wilt=0)
        for l in _flower_lots(c, item):
            stages[_stage(c['day'], l)] += l['qty']
        cooler[item] = dict(next=None if nxt is None else nxt - c['day'], spare=len(spare), fresh=by_left, stages=stages)
    d['cooler'] = cooler
    d['buckets'] = [dict(task=t['id'], start=t['work']['soak']) for t in _soaking(c)]
    pl = _peek_plan(c)
    d.pop('plan', None)
    d.pop('ev_hist', None)
    for k, v in (('regulars', {}), ('grades', []), ('pins', 0)):
        d.setdefault(k, v)
    d['day'] = FS.public_plan(c, pl, MODS, EVENT_INDEX)
    for k in ('water', 'kept', 'book', 'pre', 'sub'):
        d.pop(k, None)
    d['care'] = _public_care(c, kit.data(c))
    d['rules'] = {k: copy.deepcopy(v) for k, v in pl['rules'].items() if not k.startswith('_')}
    d['soak_min'] = _soak_min(c)
    d['rain'] = pl['mod'] == 'rain'
    return d


def _ts(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 10**11


def _valid_work(w) -> None:
    need = kit.need
    need(isinstance(w, dict) and set(_empty_work()) <= set(w), 'Bàn cắm hoa thiếu dữ liệu.')
    need(isinstance(w['stems'], list) and len(w['stems']) <= MAX_STEMS, 'Số cành sai.')
    for st in w['stems']:
        need(isinstance(st, dict) and st.get('i') in FLOWERS and st.get('c') in (0, 1, 2) and type(st.get('s')) is bool and type(st.get('h')) is bool, 'Cành hoa sai.')
        kit.integer(st.get('e'), 0, 10**7)
        kit.integer(st.get('k'), 0, 10000)
    need(w['soak'] is None or _ts(w['soak']), 'Xô ngâm sai.')
    need(isinstance(w['soaked'], (int, float)) and 0 <= w['soaked'] <= 9999, 'Thời gian ngâm sai.')
    need(w['base'] in (None, *FORMATS), 'Kiểu cắm sai.')
    need(w['foam'] is None or (isinstance(w['foam'], dict) and _ts(w['foam'].get('start')) and type(w['foam'].get('pushed')) is bool), 'Mút cắm sai.')
    need(w['foam'] is None or (w['base'] in FORMATS and FORMATS[w['base']]['foam']), 'Mút cắm sai.')
    need(type(w['arranged']) is bool and w['foam_ok'] in (None, True, False), 'Trạng thái cắm sai.')
    need(not w['arranged'] or w['base'] is not None, 'Trạng thái cắm sai.')
    need(w['paper'] in (None, *PAPERS) and w['ribbon'] in (None, *RIBBONS) and w['slot'] in (None, *SLOTS), 'Vật liệu gói sai.')
    need(w['paper'] is None or w['base'] == 'bouquet', 'Chỉ bó cầm tay mới gói giấy.')
    need(type(w['cover']) is bool, 'Lớp bọc chống mưa sai.')
    if w['banner'] is not None:
        kit.text(w['banner'], 60, 2)
    if w['card'] is not None:
        kit.text(w['card'], 160, 3)
    kit.integer(w['value'], 0, 100000)
    kit.integer(w['cost'], 0, 100000)


def validate_task(t: dict, original: dict) -> None:
    need = kit.need
    need(t.get('gen') == GEN, 'Đơn cũ chưa được cập nhật.')
    _valid_work(t['work'])
    total = _total(t)
    pieces = t.get('pieces')
    need(isinstance(pieces, list) and len(pieces) == total, 'Bàn chờ các món sai.')
    kit.integer(t.get('cur'), 0, total - 1)
    for x in pieces:
        if x is not None:
            _valid_work(x)
            need(x['arranged'] and not x['soak'], 'Món chờ giao sai.')
    asked = t.get('asked')
    need(isinstance(asked, list) and len(set(asked)) == len(asked) and set(asked) <= set(t['needs']['hidden']), 'Câu hỏi tư vấn sai.')
    kit.integer(t['refused'], 0, 1000)
    need(t['quoted_price'] is None or t['quoted_price'] == t['needs']['budget'] + (DELIVERY_FEE if t['needs']['delivery'] else 0), 'Giá đơn hoa sai.')
    need(t['served'] is None or (isinstance(t['served'], dict) and isinstance(t['served'].get('work'), dict)), 'Đơn đã giao sai.')


def validate_data(c: dict) -> None:
    need = kit.need
    d = _migrate(c)
    need(isinstance(d.get('spare'), list) and len(d['spare']) <= 60, 'Xô hoa chờ sai.')
    for x in d['spare']:
        need(isinstance(x, dict) and x.get('item') in FLOWERS, 'Cành hoa chờ sai.')
        kit.integer(x.get('e'), 0, 10**7)
        kit.integer(x.get('k'), 0, 10000)
    for k in ('delivered', 'dumped', 'wreaths', 'pins'):
        kit.integer(d.get(k), 0, 10**9)
    _valid_care(d)
    FS.validate(c, MODS, EVENT_INDEX)
    p = d.get('plan')
    if p is not None:
        need(set(p['rules']) <= RULE_KEYS, 'Luật trong ngày không hợp lệ.')
        pins = p['rules'].get('pins')
        if pins is not None:
            need(isinstance(pins, dict) and pins.get('status') in ('open', 'sent', 'failed'), 'Đơn hoa cài áo không hợp lệ.')
            kit.integer(pins.get('goal'), 1, 8)
            kit.integer(pins.get('done'), 0, pins['goal'])
            for k in ('pay', 'due'):
                kit.integer(pins.get(k), 0, 1000)
        need(p['rules'].get('warm') in (None, 1, 2), 'Luật trong ngày không hợp lệ.')


def on_close(s: dict, c: dict) -> dict:
    """Loose stems in the waiting bucket wilt like the lots they came from; then
    the day is graded (food_service)."""
    _migrate(c)
    pl = _plan(c)
    pins = pl['rules'].get('pins')
    if isinstance(pins, dict) and pins['status'] == 'open':
        pins['status'] = 'failed'
        _event_outcome(pl, 'pins', False, 'Hết ca mà chưa đủ hoa cài áo cho tiệc cưới.')
    d = kit.data(c)
    keep, lost, value = [], 0, 0
    for x in d['spare']:
        if x['e'] <= c['day']:
            lost += 1
            value += x['k']
            kit.waste(c, x['item'], 1, x['k'], 'Cành chờ trong xô đã héo')
        else:
            keep.append(x)
    d['spare'] = keep
    for t in c['tasks']:
        if _open(t) and t['work']['soak']:
            t['work']['soak'] = None
    lines = [f'{lost} cành chờ trong xô đã héo, ghi hao hụt.'] if lost else []
    if lines:
        kit.log(s, c, 'florist', lines[0])
    care = _care_close(s, c, d)
    out = FS.close(s, c, ID, pl, MODS)
    out['lines'] = lines + out['lines']
    out['care'] = care
    out.update(wilted=lost, wilted_value=value)
    return out


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    try:
        return _assist(s, c, e, t)
    except kit.eng().GameError:
        return None


def _assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e['role']
    if role == 'prep':
        if t and _open(t) and t['known'] and not t['work']['arranged'] and not t['work']['soak'] and t['work']['stems']:
            w = t['work']
            todo = [st for st in w['stems'] if st['c'] == 0 or not st['s']]
            if todo:
                for st in todo:
                    st['c'] = st['c'] or 1
                    st['s'] = True
                return f'Đã cắt xéo và tuốt lá {len(todo)} cành trên bàn. Bạn vẫn là người ngâm nước và bó.'
        d = _migrate(c)
        if c['open'] and d['water'] != c['day']:
            d['water'] = c['day']
            return 'Đã thay nước tủ mát, cắt lại gốc hoa trong tủ: đêm nay hoa không già thêm.'
        return 'Đã lau tủ mát, loại cánh dập, xếp lô cũ ra phía trước.'
    if role == 'courier':
        if t and _open(t) and t['known'] and t['needs']['delivery'] and _known(t, 'slot'):
            return f'Đã gọi xác nhận địa chỉ và khung giờ {SLOTS[t["needs"]["delivery"]]} với người nhận.'
        return 'Đã kiểm xe, thùng giữ hoa và bình nước dự phòng cho chuyến giao.'
    if role == 'designer':
        return 'Đã chuẩn bị giấy gói, ruy băng và thiệp trắng theo tông màu các đơn đang chờ.'
    return None


def hint(c: dict, t: dict) -> str:
    if t.get('known') and any(k not in t.get('asked', []) for k in t['needs']['hidden']):
        return 'Khách chưa nói hết: hỏi thêm màu yêu thích, người nhận (nhà có mèo không?) hoặc giờ giao trước khi chọn hoa.'
    if t.get('known') and _is_set(t):
        return 'Đơn nhiều món: làm xong từng món rồi bấm “Xong món”, đủ món thì giao cả bộ một lượt.'
    return ('Đọc dịp tặng → chọn hoa đúng ý nghĩa, đúng tông, số lẻ cho dịp vui → cắt xéo, tuốt lá, ngâm nước ≥ 8 giây '
            '→ chọn đế (mút phải tự chìm) → bó/cắm → gói, ruy băng, thiệp/băng rôn → giao đúng giờ.')


def content() -> dict:
    return dict(occasions=list(OCCASIONS.values()), colors=list(COLORS.values()), flowers=list(FLOWERS.values()),
                formats=list(FORMATS.values()), papers=list(PAPERS.values()), ribbons=list(RIBBONS.values()),
                slots=[dict(id=k, name=v) for k, v in SLOTS.items()], soak_min=SOAK_MIN, foam_min=FOAM_MIN,
                delivery_fee=DELIVERY_FEE, max_stems=MAX_STEMS, buckets=MAX_BUCKETS, topics=list(TOPICS.values()),
                ask_cost=ASK_COST, ask_cost_rush=ASK_COST_RUSH, pin_recipe=PIN_RECIPE, buds=list(BUDS))


# --- surprises of the day --------------------------------------------------------
PIN_RECIPE = {'rose_white': 1, 'babys_breath': 1, 'ribbon': 1}


def _event_outcome(pl: dict, eid: str, good: bool | None, note: str) -> None:
    for e in pl['events']:
        if e['id'] == eid and e['status'] == 'done':
            e['good'] = good
            e['note'] = note[:300]


def _post(s: dict, c: dict, npc: int, text: str) -> None:
    kit.eng().add_feed(s, c, kit.npc_id(ID, npc), text, 'event', None, 'post')


def _regular_visit(c: dict, npc: int) -> None:
    regs = kit.data(c).setdefault('regulars', {})
    key = kit.npc_id(ID, npc)
    regs[key] = min(99, regs.get(key, 0) + 1)


def _take_waste(c: dict, item: str, qty: int, reason: str) -> int:
    q = min(qty, kit.stock(c, item))
    if q:
        cost = kit.take(c, item, q)
        kit.waste(c, item, q, cost, reason)
    return q


def _after_rules(s: dict, c: dict, pl: dict, t: dict) -> list[str]:
    """Follow-ups of today's surprises that wait for a delivered order."""
    rules, lines = pl['rules'], []
    if rules.get('influencer') == 'next':
        rules['influencer'] = 'done'
        if t['mistakes'] == 0 and not t['refused']:
            w = FS.spawn_walkin(s, c, ID, 1.0, 'influencer')
            if w:
                pl['walkins'] += 1
            _post(s, c, 4, '📱 Clip cắm hoa ở Tiệm Hoa Nắng: cắt gốc, ngâm nước, bó xoắn ốc gọn gàng. Xem mà muốn đặt một bó!')
            _event_outcome(pl, 'influencer', True, 'Clip bó hoa vừa làm lên xu hướng, khách mới tìm tới tiệm.')
            lines.append('📱 Clip bó hoa vừa làm lên xu hướng!')
        else:
            _event_outcome(pl, 'influencer', False, 'Clip quay đúng lúc bó hoa bị sửa, bình luận chê tiệm lóng ngóng.')
            lines.append('📱 Clip quay đúng lúc bó hoa có lỗi…')
    pins = rules.get('pins')
    if isinstance(pins, dict) and pins['status'] == 'open' and pl['served'] > pins['due']:
        pins['status'] = 'failed'
        _event_outcome(pl, 'pins', False, 'Tiệc cưới chờ lâu quá nên tự mua hoa cài áo chỗ khác.')
        lines.append('📌 Tiệc cưới chờ lâu quá nên hủy đơn hoa cài áo.')
    return lines


def _pin(s: dict, c: dict, d: dict, pl: dict) -> dict:
    """One boutonniere for the wedding order (no customer at the counter needed)."""
    pins = pl['rules'].get('pins')
    kit.need(isinstance(pins, dict) and pins['status'] == 'open', 'Không có đơn hoa cài áo nào đang chờ.')
    for item, q in PIN_RECIPE.items():
        kit.need(kit.stock(c, item) >= q, f'Hết {ITEM_INDEX[item]["name"].lower()} để làm hoa cài áo. Mở Kho để nhập thêm.')
    for item, q in PIN_RECIPE.items():
        kit.take(c, item, q)
    pins['done'] += 1
    d['pins'] = d.get('pins', 0) + 1
    kit.metric(c, 'pins_made')
    if pins['done'] < pins['goal']:
        return dict(message=f'Xong hoa cài áo {pins["done"]}/{pins["goal"]}: một hồng trắng, một nhánh baby, quấn ruy băng, cài kim.')
    pay = pins['goal'] * pins['pay']
    kit.money(s, c, pay, f'{pins["goal"]} hoa cài áo cho tiệc cưới', f'pins-{c["day"]}', category='revenue')
    pins['status'] = 'sent'
    _event_outcome(pl, 'pins', True, f'Đã gửi {pins["goal"]} hoa cài áo cho tiệc cưới, nhận {pay} xu.')
    FS.flash(pl, 'good', f'📌 Đã gửi {pins["goal"]} hoa cài áo cho tiệc cưới · +{pay} xu.')
    return dict(message=f'Đủ {pins["goal"]} hoa cài áo, xếp vào hộp giữ ẩm, gửi tiệc cưới · +{pay} xu.')


def _ev_kid(s, c, pl, choice):
    if choice == 'refuse':
        return 'Bé cúi đầu đi ra. Bà Tám bán xôi đầu hẻm thấy hết, lắc đầu.', False
    cost = kit.take(c, 'rose_pink', 1)
    if choice == 'sell':
        kit.money(s, c, 8, 'Bé học sinh mua một cành hồng tặng mẹ', None, 'revenue')
        return 'Bạn gói một cành hồng phấn trong giấy kraft, thắt nơ nhỏ. Bé đưa đủ 8 xu, cười tít mắt chạy về.', True
    kit.waste(c, 'rose_pink', 1, cost, 'Tặng bé học sinh một cành hồng')
    w = FS.spawn_walkin(s, c, ID, 1.0, 'kid')
    if w:
        pl['walkins'] += 1
    return 'Bạn tặng bé cành hồng và dặn cất tiền mua bánh cho mẹ. Chiều đó mẹ bé ghé tiệm cảm ơn và đặt hoa luôn.', True


def _ev_overpay(s, c, pl, choice):
    if choice == 'return':
        _regular_visit(c, 3)
        return 'Bạn gọi báo anh Đạt và chuyển trả ngay 50 xu. Anh cười: “Tiệm này làm ăn được!”', True
    if choice == 'wait':
        return 'Bạn ghi sổ khoản dư, chờ anh hỏi. Tối anh gọi, tiệm trả lại ngay, nhưng anh hơi ngạc nhiên sao không ai báo.', None
    return 'Tối anh Đạt kiểm sao kê, gọi hỏi. Tiệm phải trả lại, còn mất lòng một khách quen.', False


def _ev_bruised(s, c, pl, choice):
    if choice == 'return':
        _drain_patience(c, 8)
        return 'Chợ sỉ nhận lại lô dập, chở lô mới tới sau nửa tiếng. Khách trong tiệm chờ thêm chút.', True
    if choice == 'cull':
        q = _take_waste(c, 'rose_red', 3, 'Hồng đỏ dập cánh bị lọc bỏ')
        return f'Bạn lọc bỏ {q} bông dập, ghi hao hụt. Bông nào ra khỏi tiệm cũng căng đẹp.', True
    pl['rules']['bruised'] = True
    return 'Bạn tỉa cánh ngoài rồi dùng hết. Nhìn gần vẫn thấy mép cánh thâm, khách tinh mắt sẽ chê.', False


def _ev_power(s, c, pl, choice):
    if choice == 'ice':
        kit.money(s, c, -12, 'Mua đá cây giữ lạnh hoa lúc mất điện', None, 'utilities')
        return 'Bạn mua hai cây đá, chuyển hoa sang xô đá, che bạt. Hoa vẫn căng đến khi có điện lại.', True
    pl['rules']['warm'] = 1 if choice == 'close' else 2
    if choice == 'close':
        return 'Bạn đóng kín tủ, hạn chế mở. Hoa hơi mềm cánh một chút, không tốn đồng nào.', None
    return 'Tủ mở ra đóng vào liên tục, trong tủ ấm dần. Cuối buổi hoa nào cũng mềm cánh.', False


def _ev_photo(s, c, pl, choice):
    if choice == 'fee':
        kit.money(s, c, 20, 'Phí dọn dẹp góc chụp ảnh cưới', None, 'revenue')
        _drain_patience(c, 4)
        return 'Cặp đôi trả 20 xu phí dọn dẹp, chụp 15 phút. Khách trong tiệm chờ lâu hơn một chút.', None
    if choice == 'free':
        _drain_patience(c, 4)
        _take_waste(c, 'babys_breath', 1, 'Tặng cặp đôi nhánh baby làm đạo cụ')
        w = FS.spawn_walkin(s, c, ID, 1.0, 'photo')
        if w:
            pl['walkins'] += 1
        _post(s, c, 0, '📸 Ảnh cưới chụp ở góc Tiệm Hoa Nắng đẹp như phim. Tiệm còn tặng một nhánh baby làm đạo cụ!')
        return 'Bạn mời cặp đôi chụp thoải mái, tặng một nhánh baby làm đạo cụ. Ảnh đăng lên, bạn bè họ hỏi địa chỉ tiệm.', True
    return 'Bạn từ chối khéo vì tiệm đang đông. Cặp đôi hơi tiếc nhưng hiểu.', None


def _ev_pins(s, c, pl, choice):
    if choice == 'decline':
        return 'Bạn từ chối khéo vì tiệm đang kín đơn. Chị tổ chức tiệc cảm ơn và gọi tiệm khác.', None
    goal = 4 if choice == 'all' else 2
    pl['rules']['pins'] = dict(goal=goal, done=0, pay=14, due=pl['served'] + 3, status='open')
    return f'Bạn nhận làm {goal} hoa cài áo. Mỗi cái cần 1 hồng trắng, 1 nhánh baby, 1 đoạn ruy băng — làm xong trước khi giao thêm 3 đơn.', None


def _ev_funeral(s, c, pl, choice):
    if choice == 'quiet':
        _regular_visit(c, 6)
        return 'Bạn tắt nhạc, dời kệ hoa đỏ vào trong, sang chia buồn với gia đình bác Sáu. Cả xóm thấy ấm lòng.', True
    if choice == 'gift':
        kit.money(s, c, -20, 'Giỏ hoa trắng chia buồn tặng nhà bác Sáu', None, 'other_cost')
        _regular_visit(c, 6)
        return 'Bạn tự tay cắm một giỏ hoa trắng mang sang chia buồn. Con cháu bác Sáu cảm ơn mãi.', True
    return 'Nhạc vui vẫn mở, kệ hoa đỏ vẫn bày cạnh rạp tang. Vài người trong xóm nhìn sang, lắc đầu.', False


def _ev_sneeze(s, c, pl, choice):
    if choice == 'rose':
        kit.take(c, 'rose_pink', 3)
        kit.money(s, c, 30, 'Bó 3 hồng phấn ít phấn cho bàn làm việc', None, 'revenue')
        return 'Bạn gợi ý 3 cành hồng phấn ít phấn hoa, gói gọn. Chị đặt lên bàn cả tuần không hắt hơi lần nào.', True
    if choice == 'lily':
        kit.take(c, 'lily', 2)
        kit.money(s, c, 30, 'Bó ly trắng cho bàn làm việc', None, 'revenue')
        return 'Bó ly thơm nức nhưng nhiều phấn. Hôm sau chị nhắn: cả phòng hắt hơi, phải mang hoa về.', False
    return 'Bạn khuyên chị chọn một chậu cây xanh nhỏ ở tiệm cây bên cạnh. Chị cảm ơn vì được tư vấn thật lòng.', None


def _ev_leak(s, c, pl, choice):
    if choice == 'move':
        _drain_patience(c, 4)
        return 'Bạn dời giấy gói và thiệp vào kệ trong, đặt xô hứng nước dột. Không mất tờ giấy nào.', True
    if choice == 'cover':
        return 'Bạn phủ tạm tấm nylon lên kệ. Vài tờ ngoài cùng hơi ẩm nhưng vẫn dùng được.', None
    q = _take_waste(c, 'paper_kraft', 2, 'Giấy kraft ướt mưa') + _take_waste(c, 'card', 2, 'Thiệp ướt mưa')
    return f'Lát sau quay lại thì {q} tờ giấy và thiệp đã ướt nhũn, phải bỏ.', False


def _ev_influencer(s, c, pl, choice):
    if choice == 'welcome':
        pl['rules']['influencer'] = 'next'
        return 'Bạn nhận lời. Đơn tiếp theo sẽ được quay từ lúc chọn hoa tới lúc gói — làm thật chuẩn nhé.', None
    if choice == 'later':
        return 'Bạn hẹn bạn ấy hôm khác, lúc tiệm vắng hơn.', None
    kit.money(s, c, -30, 'Trả tiền đăng clip quảng cáo', None, 'marketing')
    return 'Bạn trả 30 xu để clip đăng ngay, không ghi là quảng cáo. Người xem phát hiện, bình luận chê “quảng cáo trá hình”.', False


def _has_rose_pink(n):
    return lambda s, c, p: None if kit.stock(c, 'rose_pink') >= n else f'Tủ mát cần {n} cành hồng phấn.'


EVENTS = [
    dict(id='kid', emoji='🧒', title='Bé học sinh cầm 8 xu muốn mua hoa tặng mẹ', gentle=True, min_day=1,
         text='Một bé tiểu học đứng nép ở cửa, xòe tay đếm 8 xu: “Con muốn mua một bông hoa tặng mẹ, hôm nay sinh nhật mẹ con.”',
         choices=[dict(id='sell', label='Bán một cành hồng phấn đúng 8 xu, gói giấy kraft xinh xắn', hint='Giá thường 12 xu một cành.', check=_has_rose_pink(1)),
                  dict(id='gift', label='Tặng bé cành hoa, dặn bé cất tiền mua bánh cho mẹ', hint='Mất một cành, được một nụ cười.', check=_has_rose_pink(1)),
                  dict(id='refuse', label='Bảo bé tiệm không bán lẻ từng cành', hint='')],
         apply=_ev_kid),
    dict(id='overpay', emoji='💸', title='Khách chuyển khoản dư 50 xu', gentle=True, min_day=1,
         text='Anh Đạt chuyển khoản tiền giỏ hoa nhưng bấm dư một số 0: tài khoản tiệm nhận thừa 50 xu.',
         choices=[dict(id='return', label='Gọi báo anh Đạt và chuyển trả ngay', hint=''),
                  dict(id='wait', label='Ghi sổ, chờ anh hỏi rồi trả', hint='Không sai, nhưng có chậm không?'),
                  dict(id='keep', label='Im lặng, coi như tiền thưởng', hint='Biết đâu anh không để ý…')],
         apply=_ev_overpay),
    dict(id='bruised', emoji='🥀', title='Lô hồng đỏ mới về bị dập cánh', min_day=2,
         text='Mở thùng hồng đỏ sáng nay, bạn thấy nhiều bông dập mép cánh, vài bông thâm đầu.',
         choices=[dict(id='return', label='Chụp ảnh, gọi chợ sỉ đổi lô mới', hint='Được đổi hàng, khách trong tiệm chờ thêm chút.'),
                  dict(id='cull', label='Lọc bỏ bông dập, ghi hao hụt', hint='Mất vài cành, bó nào cũng đẹp.'),
                  dict(id='use', label='Tỉa cánh ngoài rồi dùng hết', hint='Không mất cành nào… nếu khách không để ý.')],
         apply=_ev_bruised),
    dict(id='power', emoji='🔌', title='Mất điện, tủ mát tắt', min_day=2,
         text='Cả dãy phố mất điện từ sáng. Tủ mát tắt, bên trong ấm dần lên.',
         choices=[dict(id='ice', label='Mua đá cây, chuyển hoa sang xô đá', hint='Tốn 12 xu.', cost=12),
                  dict(id='close', label='Đóng kín cửa tủ, hạn chế mở', hint='Không tốn gì, hoa hơi mềm cánh.'),
                  dict(id='ignore', label='Cứ mở tủ lấy hoa như thường', hint='')],
         apply=_ev_power),
    dict(id='photo', emoji='📸', title='Cặp đôi xin chụp ảnh cưới trong tiệm', min_day=2,
         text='Một cặp đôi mặc áo dài cưới xin mượn góc tiệm hoa chụp vài kiểu, thợ ảnh cần khoảng 15 phút.',
         choices=[dict(id='fee', label='Đồng ý, xin 20 xu phí dọn dẹp', hint='Khách đang chờ sẽ chờ thêm chút.'),
                  dict(id='free', label='Mời chụp thoải mái, tặng một nhánh baby làm đạo cụ', hint='Khách đang chờ sẽ chờ thêm chút.'),
                  dict(id='no', label='Từ chối vì tiệm đang đông khách', hint='')],
         apply=_ev_photo),
    dict(id='pins', emoji='📌', title='Đơn hoa cài áo gấp cho tiệc cưới', min_day=3, not_mods=('quiet',),
         text='Chị tổ chức tiệc cưới gọi gấp: cần hoa cài áo cho chú rể và phù rể, xong trong lúc tiệm giao thêm 3 đơn nữa. Mỗi cái 14 xu.',
         choices=[dict(id='all', label='Nhận 4 hoa cài áo', hint='Cần 4 hồng trắng, 4 nhánh baby, 4 đoạn ruy băng.'),
                  dict(id='half', label='Nhận 2 hoa cài áo', hint='Ít tiền hơn, nhẹ việc hơn.'),
                  dict(id='decline', label='Từ chối khéo vì đang kín đơn', hint='')],
         apply=_ev_pins),
    dict(id='funeral', emoji='🕯️', title='Nhà bên cạnh có tang', min_day=3,
         text='Sáng nay nhà bác Sáu cạnh tiệm có tang. Loa nhạc vui và kệ hoa khai trương màu đỏ vẫn bày trước cửa tiệm.',
         choices=[dict(id='quiet', label='Tắt nhạc, dời kệ hoa đỏ vào trong, sang chia buồn', hint=''),
                  dict(id='gift', label='Cắm tặng gia đình một giỏ hoa trắng chia buồn', hint='Tốn 20 xu hoa và giỏ.', cost=20),
                  dict(id='ignore', label='Buôn bán như thường, việc ai nấy lo', hint='')],
         apply=_ev_funeral),
    dict(id='sneeze', emoji='🤧', title='Khách dị ứng phấn hoa hỏi mua hoa để bàn', min_day=2,
         text='Một chị nhân viên văn phòng vừa vào tiệm đã hắt hơi liên tục. Chị muốn một bó nhỏ để bàn làm việc mà không bị dị ứng.',
         choices=[dict(id='rose', label='Gợi ý 3 cành hồng phấn ít phấn hoa', hint='Bán 30 xu.', check=_has_rose_pink(3)),
                  dict(id='lily', label='Bán bó ly trắng cho thơm phòng', hint='Bán 30 xu.', check=lambda s, c, p: None if kit.stock(c, 'lily') >= 2 else 'Tủ mát cần 2 cành ly.'),
                  dict(id='advise', label='Khuyên chị chọn một chậu cây xanh nhỏ thay hoa', hint='')],
         apply=_ev_sneeze),
    dict(id='leak', emoji='☔', title='Mái hiên dột ngay kệ giấy gói', min_day=2, mods=('rain',),
         text='Mưa to, nước dột xuống đúng kệ giấy gói và thiệp viết tay.',
         choices=[dict(id='move', label='Dời giấy, thiệp vào kệ trong, đặt xô hứng', hint='Khách đang chờ sẽ chờ thêm chút.'),
                  dict(id='cover', label='Phủ tạm nylon lên kệ', hint=''),
                  dict(id='ignore', label='Để đó, lát rảnh tính', hint='')],
         apply=_ev_leak),
    dict(id='influencer', emoji='📱', title='Bạn làm clip hoa xin quay bạn cắm hoa', min_day=2,
         text='Một bạn trẻ làm clip về hoa xin quay cảnh tiệm làm đơn tiếp theo, từ lúc chọn hoa tới lúc gói.',
         choices=[dict(id='welcome', label='Đồng ý, cứ quay tự nhiên', hint='Đơn tiếp theo mà hoàn hảo thì clip sẽ rất đẹp.'),
                  dict(id='later', label='Hẹn bạn ấy hôm khác', hint=''),
                  dict(id='paid', label='Trả 30 xu để clip đăng ngay, không cần ghi là quảng cáo', hint='', cost=30)],
         apply=_ev_influencer),
]
EVENT_INDEX = {e['id']: e for e in EVENTS}
RULE_KEYS = {'bruised', 'warm', 'pins', 'influencer', 'market_gift'}


# --- care loop: the cooler, pre-orders, the subscription, the regulars' card ------
# (docs/superpowers/specs/2026-09-29-florist-care-design.md)
BUDS = ('rose_red', 'rose_pink', 'rose_white', 'rose_yellow', 'lily')   # arrive as tight buds
STAGES = dict(bud='nụ', bloom='nở đẹp', wilt='sắp héo')
KEEP_MAX = 2       # nights one lot can be kept from ageing by fresh water
MAX_PRE = 3        # open pre-orders (offers + bookings) at once
PRE_STATUS = ('offer', 'booked', 'done', 'failed')
PRE = {
    'wedding': dict(id='wedding', npc=4, emoji='💒', title='Bó hoa cô dâu cho chị gái Linh', lead=3, price=240, deposit=80,
                    recipe={'rose_white': 9, 'rose_pink': 4, 'babys_breath': 4, 'paper_white': 1, 'ribbon': 1},
                    call='Chị gái em cưới vào ngày {due}! Tiệm làm giùm bó hoa cô dâu tông trắng – hồng nha, em đặt cọc trước.',
                    good='Bó hoa cô dâu nở đúng ngày, trắng – hồng tinh khôi. Chị em cầm lên là cả rạp trầm trồ!'),
    'opening': dict(id='opening', npc=3, emoji='🎉', title='Giỏ hoa khai trương tiệm bánh', lead=2, price=260, deposit=80,
                    recipe={'sunflower': 8, 'rose_yellow': 5, 'eucalyptus': 4, 'basket': 1, 'foam': 1},
                    call='Em gái anh mở tiệm bánh ngày {due}. Làm giùm anh một giỏ hướng dương thật rực rỡ, anh cọc trước.',
                    good='Giỏ hướng dương tươi rói đặt ngay cửa tiệm bánh, khách đi ngang ai cũng chụp hình.'),
    'funeral': dict(id='funeral', npc=2, emoji='🕊️', title='Kệ hoa viếng cụ Bảy xóm trên', lead=1, price=300, deposit=100,
                    recipe={'mum_white': 16, 'lily': 4, 'eucalyptus': 3, 'stand': 1, 'foam': 2, 'banner': 1},
                    banner='Thành kính phân ưu · Tổ dân phố 5',
                    call='Cụ Bảy xóm trên mất rồi con. Sáng ngày {due} làm giùm cô kệ hoa viếng của tổ dân phố, cô gửi cọc.',
                    good='Kệ hoa trắng trang nghiêm, băng rôn đúng từng chữ. Gia đình cụ Bảy cảm ơn tổ dân phố.'),
    'anniv': dict(id='anniv', npc=5, emoji='💞', title='Bó hồng kỷ niệm 30 năm ngày cưới', lead=2, price=200, deposit=60,
                  recipe={'rose_red': 11, 'babys_breath': 3, 'eucalyptus': 2, 'paper_pink': 1, 'ribbon': 1},
                  call='Ngày {due} là kỷ niệm 30 năm ngày cưới của chú. Lần này chú nhớ trước rồi nhé, 11 hồng đỏ!',
                  good='Vợ chú mở cửa thấy 11 bông hồng đỏ nở đẹp, cười như hồi mới cưới.'),
}
SUB_PRICE = 60
SUB_EVERY = 3      # days between two vases for Bà Tám
SUB_NPC = 6
SUB_STATUS = ('none', 'offer', 'on', 'off')
SUB_NOTES = {
    'fresh': 'Nhìn cánh là biết hoa mấy ngày: chỉ lấy hoa nở đẹp, không nụ chặt, không sắp héo.',
    'lily': 'Dị ứng phấn hoa ly: hắt hơi cả ngày.',
    'mum': 'Cúc trắng chỉ để bàn thờ, đừng cắm bình phòng khách.',
    'pink': 'Thích hồng phấn, cẩm chướng: nhìn là vui.',
}
TEMPLATES = [
    dict(id='pinkrose', name='Hồng phấn – baby', stems={'rose_pink': 5, 'babys_breath': 2, 'eucalyptus': 2}, tags=('pink',)),
    dict(id='whitepink', name='Hồng trắng – hồng phấn', stems={'rose_white': 3, 'rose_pink': 3, 'eucalyptus': 2}, tags=('pink',)),
    dict(id='carn', name='Cẩm chướng – hồng trắng', stems={'carnation': 5, 'rose_white': 2, 'eucalyptus': 2}, tags=('pink',)),
    dict(id='lily', name='Ly trắng thơm nức', stems={'lily': 3, 'eucalyptus': 3}, tags=('lily',)),
    dict(id='mum', name='Cúc trắng giản dị', stems={'mum_white': 7, 'eucalyptus': 2}, tags=('mum',)),
    dict(id='sun', name='Hướng dương rực rỡ', stems={'sunflower': 3, 'eucalyptus': 3}, tags=()),
    dict(id='redyel', name='Hồng đỏ – hồng vàng', stems={'rose_red': 3, 'rose_yellow': 3, 'babys_breath': 2}, tags=()),
]
TEMPLATE_INDEX = {x['id']: x for x in TEMPLATES}
SUB_WRAP = {'paper_kraft': 1, 'ribbon': 1}
# What regulars tell the shop: the first note after the first finished order, the second after the third.
NOTE_AT = (1, 3)
NOTES = {
    0: [('card', 'Luôn muốn kèm thiệp viết tay; anh đọc, tiệm viết giùm.'), ('redwhite', 'Người yêu anh mê hồng đỏ điểm chút trắng.')],
    1: [('cats', 'Mẹ chị nuôi 3 bé mèo: không hoa ly; baby, bạch đàn cũng nên tránh.'), ('pastel', 'Nhà chị chuộng tông pastel: hồng phấn, trắng.')],
    2: [('banner', 'Việc hiếu hỉ: đọc lại băng rôn với cô từng chữ trước khi in.'), ('early', 'Lễ viếng thường sáng sớm, hoa phải tới trước giờ.')],
    3: [('ontime', 'Chỉ cần đúng giờ, đúng việc, không cần nói nhiều.'), ('sun', 'Mê hướng dương: “nhìn là thấy nắng”.')],
    4: [('budget', 'Ngân sách mỏng: gợi ý cẩm chướng, baby thay hồng nhập.'), ('pollen', 'Dị ứng phấn hoa ly: hắt hơi cả ngày.')],
    5: [('forget', 'Hay quên ngày kỷ niệm: nhắc chú trước vài hôm.'), ('pink', 'Vợ chú thích hồng nhạt, nhẹ nhàng.')],
    6: [('fresh', SUB_NOTES['fresh']), ('mum', SUB_NOTES['mum'])],
}


def _care_defaults(day: int) -> dict:
    return dict(water=max(0, day - 1), kept={}, book={}, pre=[],
                sub=dict(status='none', next=0, round=0, misses=0, known=[], stars=[], retry=3))


def _name(npc: int) -> str:
    return PEOPLE[npc][0]


def _stage(day: int, lot: dict) -> str:
    """nụ on the day roses/lilies arrive, sắp héo on a lot's last day, nở đẹp otherwise."""
    if lot['expires'] <= day:
        return 'wilt'
    if lot['item'] in BUDS and lot['received'] >= day and lot.get('supplier') != 'opening':
        return 'bud'
    return 'bloom'


def _flower_lots(c: dict, item: str | None = None) -> list:
    return [l for l in c['ext']['inv']['lots'] if l['item'] in FLOWERS and (item is None or l['item'] == item)
            and l['expires'] >= c['day'] and l['qty'] > 0]


def _take_best(c: dict, item: str, qty: int) -> tuple[int, int]:
    """Take stems for a made-to-order piece: open ones first (oldest open first),
    then buds, then wilting. Returns (buds, wilting) used."""
    order = dict(bloom=0, bud=1, wilt=2)
    lots = sorted(_flower_lots(c, item), key=lambda l: (order[_stage(c['day'], l)], l['expires'], l['received']))
    buds = wilts = 0
    for lot in lots:
        if not qty:
            break
        used = min(qty, lot['qty'])
        st = _stage(c['day'], lot)
        buds += used if st == 'bud' else 0
        wilts += used if st == 'wilt' else 0
        lot['qty'] -= used
        qty -= used
    c['ext']['inv']['lots'] = [l for l in c['ext']['inv']['lots'] if l['qty'] > 0]
    return buds, wilts


def _short(c: dict, recipe: dict) -> list[str]:
    return [f'{q - kit.stock(c, k)} {ITEM_INDEX[k]["unit"]} {ITEM_INDEX[k]["name"].lower()}' for k, q in recipe.items() if kit.stock(c, k) < q]


def _use(c: dict, recipe: dict) -> tuple[int, int]:
    short = _short(c, recipe)
    kit.need(not short, 'Chưa đủ hàng: thiếu ' + ', '.join(short) + '. Mở Kho để nhập thêm.')
    buds = wilts = 0
    for k, q in recipe.items():
        if k in FLOWERS:
            b, w = _take_best(c, k, q)
            buds, wilts = buds + b, wilts + w
        else:
            kit.take(c, k, q)
    return buds, wilts


def _visit(d: dict, npc: int) -> list[str]:
    """One more finished order for a regular; returns what they told the shop today."""
    r = d['book'].setdefault(str(npc), dict(visits=0, notes=[]))
    r['visits'] = min(9999, r['visits'] + 1)
    told = []
    for i, at in enumerate(NOTE_AT):
        nid, text = NOTES[npc][i]
        if r['visits'] >= at and nid not in r['notes']:
            r['notes'].append(nid)
            told.append(text)
    return told


def _open_pre(d: dict) -> list:
    return [b for b in d['pre'] if b['status'] in ('offer', 'booked')]


def _pre_offer(day: int, mod: str) -> str | None:
    """Seeded by the day: does a customer call to book an event piece today?"""
    if day < 2:
        return None
    r = kit.rng(ID, 'pre', day)
    if r.random() >= (0.8 if mod == 'wedding' else 0.55):
        return None
    pool = sorted(PRE)
    return r.choices(pool, [3 if (mod == 'wedding' and k == 'wedding') else 1 for k in pool])[0]


def _sub_menu(c: dict, rnd: int) -> list[str]:
    """Three vases to choose from on a delivery round; at least one avoids all she dislikes."""
    pool = [x['id'] for x in TEMPLATES if all(FLOWERS[k]['unlock'] <= kit.level(c) for k in x['stems'])]
    r = kit.rng(ID, 'sub', rnd)
    menu = r.sample(pool, 3)
    good = [k for k in pool if TEMPLATE_INDEX[k]['tags'] == ('pink',)]
    if not any(k in good for k in menu):
        menu[r.randrange(3)] = r.choice(good)
    return menu


def _care_start(s: dict, c: dict, d: dict, pl: dict) -> None:
    day = c['day']
    if not any(b['id'] == f'pre-{day}' for b in d['pre']) and len(_open_pre(d)) < MAX_PRE:
        kind = _pre_offer(day, pl['mod'])
        if kind:
            d['pre'].append(dict(id=f'pre-{day}', kind=kind, day=day, due=day + PRE[kind]['lead'], status='offer', stars=None))
            kit.log(s, c, 'florist', f'{_name(PRE[kind]["npc"])} gọi đặt trước: {PRE[kind]["title"]}.')
    sub = d['sub']
    if sub['status'] in ('none', 'off') and day >= sub['retry']:
        sub['status'] = 'offer'


def _water(s: dict, c: dict, d: dict) -> dict:
    kit.need(d['water'] != c['day'], 'Hôm nay đã thay nước tủ mát rồi.')
    d['water'] = c['day']
    lots = _flower_lots(c)
    kept = sum(1 for l in lots if l['expires'] > c['day'] and d['kept'].get(l['id'], 0) < KEEP_MAX)
    kit.metric(c, 'cooler_care')
    tail = f' Đêm nay {kept} lô hoa không già thêm.' if kept else ' Các lô trong tủ đã được giữ đủ 2 đêm hoặc sắp héo.'
    return dict(message='Đã thay nước sạch, cắt lại gốc hoa trong tủ mát, bỏ lá úng.' + tail)


def _pre(s: dict, c: dict, d: dict, p: dict) -> dict:
    bid = p.get('id')
    b = next((x for x in d['pre'] if x['id'] == bid), None) if isinstance(bid, str) else None
    kit.need(b is not None, 'Không tìm thấy đơn đặt trước này.')
    do = _one_of(p.get('do'), ('accept', 'decline', 'make'), 'Chọn nhận, từ chối hoặc cắm đơn đặt trước.')
    sp = PRE[b['kind']]
    who = _name(sp['npc'])
    if do in ('accept', 'decline'):
        kit.need(b['status'] == 'offer', 'Đơn này đã trả lời rồi.')
        if do == 'decline':
            d['pre'].remove(b)
            return dict(message=f'Bạn từ chối khéo vì sợ không kịp. {who} cảm ơn và đặt chỗ khác.')
        kit.confirm(p, 'Xác nhận nhận đơn đặt trước và nhận tiền cọc.')
        kit.need(sum(x['status'] == 'booked' for x in d['pre']) < MAX_PRE, f'Tiệm chỉ nhận tối đa {MAX_PRE} đơn đặt trước cùng lúc.')
        b['status'] = 'booked'
        kit.money(s, c, sp['deposit'], f'Cọc đơn đặt trước: {sp["title"]}', b['id'], 'revenue')
        return dict(message=f'Đã nhận đơn “{sp["title"]}” cho ngày {b["due"]}, cọc {sp["deposit"]} xu. '
                            'Nhập hoa trước 1–2 ngày để hoa nở đúng ngày.')
    kit.need(b['status'] == 'booked', 'Đơn này chưa nhận hoặc đã xong.')
    kit.need(b['due'] == c['day'], f'Đơn hẹn ngày {b["due"]}. Cắm đúng ngày cho hoa tươi nhất.')
    kit.confirm(p, 'Xác nhận cắm và giao đơn đặt trước.')
    buds, wilts = _use(c, sp['recipe'])
    stars = 5 - (1 if buds else 0) - (1 if wilts else 0)
    notes = ([f'{buds} bông còn nụ chặt'] if buds else []) + ([f'{wilts} cành sắp héo'] if wilts else [])
    off = 10 * (5 - stars)
    pay = sp['price'] - sp['deposit'] - off
    kit.money(s, c, pay, f'Hoàn thành đơn đặt trước: {sp["title"]}', b['id'], 'revenue')
    text = sp['good'] if stars == 5 else f'Hoa tới đúng ngày nhưng {" và ".join(notes)}. Tiệm bớt cho {off} xu.'
    kit.review(s, c, kit.npc_id(ID, sp['npc']), stars, text, b['id'])
    b['status'], b['stars'] = 'done', stars
    c['xp'] += 6
    kit.metric(c, 'preorders_done')
    _drain_patience(c, 6)
    told = _visit(d, sp['npc'])
    msg = (f'Đã cắm và giao “{sp["title"]}” · +{pay} xu ({sp["price"]} − cọc {sp["deposit"]}'
           + (f' − bớt {off}' if off else '') + f'). {who}: {stars}★.')
    if notes:
        msg += ' ' + ' và '.join(notes).capitalize() + ' — lần sau nhập hoa trước 1–2 ngày.'
    if told:
        msg += ' 📒 Ghi vào sổ khách quen: ' + ' '.join(told)
    return dict(message=msg, celebrate=stars == 5)


def _sub(s: dict, c: dict, d: dict, p: dict) -> dict:
    sub = d['sub']
    do = _one_of(p.get('do'), ('accept', 'decline', 'stop', 'make'), 'Chọn thao tác với gói hoa định kỳ.')
    day = c['day']
    if do in ('accept', 'decline'):
        kit.need(sub['status'] == 'offer', 'Bà Tám chưa hỏi đặt gói hoa định kỳ.')
        if do == 'decline':
            sub.update(status='off', retry=day + 5)
            return dict(message='Bạn cảm ơn bà Tám, hẹn khi tiệm rảnh tay hơn.')
        kit.confirm(p, 'Xác nhận nhận gói hoa định kỳ.')
        sub.update(status='on', next=day + 1, misses=0)
        if 'fresh' not in sub['known']:
            sub['known'].append('fresh')
        return dict(message=f'Bà Tám đặt gói hoa: cứ {SUB_EVERY} ngày một bình nhỏ, {SUB_PRICE} xu/lần, bình đầu vào ngày {day + 1}. '
                            f'Bà dặn: “{SUB_NOTES["fresh"]}”')
    if do == 'stop':
        kit.need(sub['status'] == 'on', 'Chưa có gói hoa định kỳ nào.')
        kit.confirm(p, 'Xác nhận ngừng gói hoa định kỳ.')
        sub.update(status='off', retry=day + 5, misses=0)
        return dict(message='Đã báo bà Tám ngừng gói hoa. Bà hơi buồn nhưng hiểu.')
    kit.need(sub['status'] == 'on', 'Chưa có gói hoa định kỳ nào.')
    kit.need(sub['next'] == day, f'Bình hoa của bà Tám hẹn ngày {sub["next"]}.')
    menu = _sub_menu(c, sub['round'])
    pick = _one_of(p.get('pick'), menu, 'Chọn một trong ba mẫu bình hôm nay.')
    tp = TEMPLATE_INDEX[pick]
    buds, wilts = _use(c, {**tp['stems'], **SUB_WRAP})
    stars, said, learn = 5, [], []
    if 'lily' in tp['tags']:
        stars -= 2
        said.append('Bà hắt hơi cả buổi vì phấn hoa ly.')
        learn.append('lily')
    if 'mum' in tp['tags']:
        stars -= 2
        said.append('Cúc trắng để bàn thờ, cắm phòng khách bà thấy buồn.')
        learn.append('mum')
    if 'pink' not in tp['tags']:
        stars -= 1
        said.append('Bà thích hồng phấn, cẩm chướng hơn.')
        learn.append('pink')
    if buds:
        stars -= 1
        said.append('Vài bông còn nụ chặt, mai mới nở.')
    if wilts:
        stars -= 1
        said.append('Có bông sắp héo, bà nhìn là biết.')
    stars = max(1, stars)
    new = [k for k in learn if k not in sub['known']]
    sub['known'].extend(new)
    kit.money(s, c, SUB_PRICE, f'Gói hoa định kỳ của bà Tám (lần {sub["round"] + 1})', f'sub-{sub["round"] + 1}', 'revenue')
    text = ' '.join(said) if said else 'Bình hoa xinh, bông nào cũng nở đẹp. Bà để phòng khách ngắm cả tuần.'
    kit.review(s, c, kit.npc_id(ID, SUB_NPC), stars, text, f'sub-{sub["round"] + 1}')
    sub['stars'] = ar.last(sub['stars'] + [stars], 6, 'florist.sub_stars', c)
    sub.update(next=day + SUB_EVERY, round=sub['round'] + 1, misses=0)
    c['xp'] += 3
    kit.metric(c, 'sub_vases')
    msg = f'Đã giao bình “{tp["name"]}” cho bà Tám · +{SUB_PRICE} xu · {stars}★. {text}'
    if new:
        msg += ' 📒 Ghi vào thẻ của bà: ' + ' '.join(SUB_NOTES[k] for k in new)
    return dict(message=msg, celebrate=stars == 5)


def _care_close(s: dict, c: dict, d: dict) -> list[str]:
    """Night in the cooler, bookings and the subscription at day close."""
    day, lines = c['day'], []
    lots = [l for l in _flower_lots(c) if l['expires'] > day]
    if d['water'] == day:
        kept = 0
        for l in lots:
            k = d['kept'].get(l['id'], 0)
            if k < KEEP_MAX:
                l['expires'] += 1
                d['kept'][l['id']] = k + 1
                kept += 1
        if kept:
            lines.append(f'💧 Nước tủ mát sạch: {kept} lô hoa đêm nay không già thêm.')
    elif d['water'] <= day - 2:
        # Cloudy water: open lots age one day faster, but never straight from usable to gone.
        aged = [l for l in lots if l['expires'] > day + 1]
        for l in aged:
            l['expires'] -= 1
        if aged:
            lines.append(f'🫧 Nước tủ mát đục 2 ngày: {len(aged)} lô hoa già nhanh thêm 1 ngày. Mai nhớ thay nước.')
    live = {l['id'] for l in c['ext']['inv']['lots']}
    d['kept'] = {k: v for k, v in d['kept'].items() if k in live}
    for b in list(d['pre']):
        sp = PRE[b['kind']]
        if b['status'] == 'offer':
            d['pre'].remove(b)
        elif b['status'] == 'booked' and b['due'] <= day:
            b['status'] = 'failed'
            back = min(sp['deposit'], c['money'])
            if back:
                kit.money(s, c, -back, f'Hoàn cọc đơn đặt trước không làm kịp: {sp["title"]}', b['id'], 'refund')
            kit.review(s, c, kit.npc_id(ID, sp['npc']), 1, f'Đặt trước cả mấy ngày mà tới ngày {b["due"]} tiệm không giao. May mà còn kịp mua chỗ khác.', b['id'])
            lines.append(f'✗ Không kịp làm “{sp["title"]}”: hoàn {back} xu cọc, {_name(sp["npc"])} rất buồn.')
    closed = [b for b in d['pre'] if b['status'] in ('done', 'failed')]
    d['pre'] = _open_pre(d) + ar.last(closed, 4, 'florist.pre', c)
    sub = d['sub']
    if sub['status'] == 'offer':
        sub.update(status='none', retry=day + 2)
    elif sub['status'] == 'on' and sub['next'] <= day:
        kit.review(s, c, kit.npc_id(ID, SUB_NPC), 2, 'Bà chờ bình hoa cả ngày mà tiệm quên mất.', f'sub-miss-{day}')
        if sub['misses'] >= 1:
            sub.update(status='off', retry=day + 5, misses=0)
            lines.append('✗ Bà Tám ngừng gói hoa định kỳ vì tiệm quên giao hai lần liền.')
        else:
            sub.update(next=day + SUB_EVERY, misses=1)
            lines.append(f'✗ Quên bình hoa của bà Tám hôm nay. Lần tới: ngày {day + SUB_EVERY}.')
    soon = [PRE[b['kind']]['title'] for b in d['pre'] if b['status'] == 'booked' and b['due'] == day + 1]
    if sub['status'] == 'on' and sub['next'] == day + 1:
        soon.append('bình hoa của bà Tám')
    if soon:
        lines.append('📅 Ngày mai: ' + ', '.join(soon) + '.')
    return lines


def _plan_rows(c: dict, recipe: dict, due: int) -> list[dict]:
    """For each ingredient: needed, in stock now, and stems that will be open on the due day."""
    day, rows = c['day'], []
    for k, q in recipe.items():
        it = ITEM_INDEX[k]
        row = dict(item=k, name=it['name'], emoji=it['emoji'], unit=it['unit'], need=q, have=kit.stock(c, k), flower=k in FLOWERS)
        if k in FLOWERS:
            lots = _flower_lots(c, k)
            row['ready'] = sum(l['qty'] for l in lots if l['expires'] > due and not (due == day and _stage(day, l) == 'bud'))
            first = max(day, due - it['life'] + 2)
            last = due - 1 if k in BUDS else due
            row['buy'] = [first, last] if first <= last else None
        rows.append(row)
    return rows


def _public_care(c: dict, raw: dict) -> dict:
    """The care loop as the player may see it (unlearned notes stay here)."""
    day = c['day']
    base = _care_defaults(day)
    water = raw.get('water', base['water'])
    water = water if isinstance(water, int) else base['water']
    out = dict(water=dict(done=water == day, last=water, risk=water <= day - 1))
    pre = []
    for b in raw.get('pre') or []:
        sp = PRE.get(b.get('kind')) if isinstance(b, dict) else None
        if not sp:
            continue
        row = dict(id=b['id'], kind=sp['id'], emoji=sp['emoji'], title=sp['title'], npc=kit.npc_id(ID, sp['npc']), due=b['due'],
                   left=b['due'] - day, status=b['status'], stars=b.get('stars'), price=sp['price'], deposit=sp['deposit'],
                   call=sp['call'].format(due=b['due']), banner=sp.get('banner'))
        if b['status'] in ('offer', 'booked'):
            row['rows'] = _plan_rows(c, sp['recipe'], b['due'])
            row['short'] = _short(c, sp['recipe'])
        pre.append(row)
    out['pre'] = pre
    sub = raw.get('sub') if isinstance(raw.get('sub'), dict) else base['sub']
    sv = dict(status=sub.get('status', 'none'), next=sub.get('next', 0), left=sub.get('next', 0) - day, price=SUB_PRICE, every=SUB_EVERY,
              stars=list(sub.get('stars') or []), misses=sub.get('misses', 0), npc=kit.npc_id(ID, SUB_NPC),
              notes=[SUB_NOTES[k] for k in SUB_NOTES if k in (sub.get('known') or [])])
    if sv['status'] == 'on' and sv['next'] == day:
        sv['menu'] = [dict(id=k, name=TEMPLATE_INDEX[k]['name'], rows=_plan_rows(c, {**TEMPLATE_INDEX[k]['stems'], **SUB_WRAP}, day),
                           short=_short(c, {**TEMPLATE_INDEX[k]['stems'], **SUB_WRAP})) for k in _sub_menu(c, sub.get('round', 0))]
    out['sub'] = sv
    book = []
    for k, r in sorted((raw.get('book') or {}).items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 99):
        if not (str(k).isdigit() and int(k) in NOTES and isinstance(r, dict)):
            continue
        npc = int(k)
        texts = dict(NOTES[npc])
        notes = [texts[n] for n in r.get('notes', []) if n in texts]
        if npc == SUB_NPC:
            notes += [SUB_NOTES[n] for n in (sub.get('known') or []) if SUB_NOTES.get(n) not in notes]
        nxt = next((a for a in NOTE_AT if a > r.get('visits', 0)), None)
        book.append(dict(npc=kit.npc_id(ID, npc), visits=r.get('visits', 0), notes=notes, more=None if nxt is None else nxt - r.get('visits', 0)))
    out['book'] = book
    return out


def _valid_care(d: dict) -> None:
    need = kit.need
    kit.integer(d.get('water'), 0, 10**7)
    kept = d.get('kept')
    need(isinstance(kept, dict) and len(kept) <= 300, 'Sổ tủ mát sai.')
    for k, v in kept.items():
        need(isinstance(k, str) and len(k) <= 80, 'Sổ tủ mát sai.')
        kit.integer(v, 1, KEEP_MAX)
    book = d.get('book')
    need(isinstance(book, dict) and len(book) <= len(NOTES), 'Sổ khách quen sai.')
    for k, r in book.items():
        need(isinstance(k, str) and k.isdigit() and int(k) in NOTES, 'Sổ khách quen sai.')
        need(isinstance(r, dict) and set(r) == {'visits', 'notes'}, 'Sổ khách quen sai.')
        v = kit.integer(r['visits'], 0, 9999)
        allowed = [n for (n, _), at in zip(NOTES[int(k)], NOTE_AT) if v >= at]
        need(isinstance(r['notes'], list) and len(set(r['notes'])) == len(r['notes']) and set(r['notes']) <= set(allowed), 'Ghi chú khách quen sai.')
    pre = d.get('pre')
    need(isinstance(pre, list) and len(pre) <= 12, 'Đơn đặt trước sai.')
    ids = set()
    for b in pre:
        need(isinstance(b, dict) and set(b) == {'id', 'kind', 'day', 'due', 'status', 'stars'} and b['kind'] in PRE, 'Đơn đặt trước sai.')
        day = kit.integer(b['day'], 1, 10**7)
        need(b['id'] == f'pre-{day}' and b['id'] not in ids and b['due'] == day + PRE[b['kind']]['lead'], 'Đơn đặt trước sai.')
        ids.add(b['id'])
        need(b['status'] in PRE_STATUS, 'Trạng thái đơn đặt trước sai.')
        need((b['stars'] is None) if b['status'] != 'done' else (type(b['stars']) is int and 3 <= b['stars'] <= 5), 'Sao đơn đặt trước sai.')
    need(len(_open_pre(d)) <= MAX_PRE, 'Quá nhiều đơn đặt trước.')
    sub = d.get('sub')
    need(isinstance(sub, dict) and set(sub) == {'status', 'next', 'round', 'misses', 'known', 'stars', 'retry'}, 'Gói hoa định kỳ sai.')
    need(sub['status'] in SUB_STATUS, 'Gói hoa định kỳ sai.')
    for k in ('next', 'round', 'retry'):
        kit.integer(sub[k], 0, 10**7)
    kit.integer(sub['misses'], 0, 1)
    need(isinstance(sub['known'], list) and len(set(sub['known'])) == len(sub['known']) and set(sub['known']) <= set(SUB_NOTES), 'Thẻ của bà Tám sai.')
    need(isinstance(sub['stars'], list) and len(sub['stars']) <= 6 and all(type(x) is int and 1 <= x <= 5 for x in sub['stars']), 'Sao gói hoa sai.')


SITUATIONS = [
    dict(id='FL-S01', title='Tặng hoa giấu tên tới văn phòng', npc=0, tone='tense', min_day=1,
         opening='Anh Minh muốn gửi hồng đỏ giấu tên cho chị Vy ở tầng 7 tòa Mây Xanh. Anh nhờ tiệm “dò giùm giờ chị ấy đi làm, đặt hoa lên tận bàn, chụp lại phản ứng gửi anh”.',
         swap='Bạn là chị Vy — người nhận. Đây là lần thứ tư bạn nhận hoa không rõ ai gửi tại chỗ làm.',
         facts=[dict(id='policy', title='Quy định của tiệm', source='Sổ quy trình Tiệm Hoa Nắng', text='Tiệm không cung cấp thông tin của người nhận cho người gửi; người nhận có quyền từ chối và hoa sẽ mang về.'),
                dict(id='reception', title='Quy định tòa nhà', source='Lễ tân tòa Mây Xanh', text='Hoa, quà giao qua quầy lễ tân; người giao không được lên tầng khi người nhận chưa đồng ý.'),
                dict(id='history', title='Lịch sử đơn', source='Sổ giao hàng', text='Ba lần trước, lễ tân báo chị Vy không nhận và nhờ nhắn: “Xin đừng gửi nữa”.')],
         options=[dict(id='consent', label='Chỉ giao qua lễ tân, thiệp ghi tên thật của anh Minh; nếu chị Vy từ chối thì mang hoa về, không chụp ảnh, không dò lịch', requires=['policy', 'reception'], quality='good', stars=4,
                       review='Tiệm không chiều mình dò lịch người ta, hơi hụt hẫng, nhưng mình hiểu. Cách làm đàng hoàng.',
                       outcome='Chị Vy đọc tên trên thiệp, lịch sự từ chối. Hoa quay về tiệm; anh Minh nhận lại hoa và một lời khuyên chân thành.',
                       perspectives=[dict(who='Chị Vy', emoji='💼', text='Có tên người gửi, mình được quyền quyết định. Cảm ơn tiệm đã không lên tận bàn.'),
                                     dict(who='Anh Minh', emoji='🌹', text='Buồn thật, nhưng ít ra mình đã nói thẳng thay vì làm người ta sợ.'),
                                     dict(who='Lễ tân', emoji='🛎️', text='Tiệm này làm đúng quy trình, tôi yên tâm cho giao lần sau.')]),
                  dict(id='honest', label='Nói thật với anh Minh chuyện ba lần bị từ chối, khuyên anh dừng và hoàn tiền đơn', requires=['history'], quality='good', stars=3, cost=0,
                       review='Nghe khó chịu nhưng là sự thật. Tiệm nói thẳng mà không làm mình mất mặt.',
                       outcome='Anh Minh im lặng một lúc, cảm ơn rồi hủy đơn. Vài tuần sau anh quay lại đặt hoa sinh nhật cho mẹ.',
                       perspectives=[dict(who='Anh Minh', emoji='😔', text='Không ai nói với mình câu “người ta đã từ chối” rõ như vậy.'),
                                     dict(who='Chị Vy', emoji='😌', text='Không có bó hoa thứ tư nào xuất hiện. Nhẹ cả người.')]),
                  dict(id='sneak', label='Nhờ bảo vệ dẫn lên tận bàn, chụp ảnh phản ứng gửi anh Minh', quality='bad', stars=2,
                       review='Tiệm giao được nhưng tòa nhà cấm tiệm từ đó. Giờ mình mang tiếng luôn.',
                       outcome='Chị Vy hoảng khi thấy người lạ đứng cạnh bàn và chụp ảnh. Tòa nhà cấm Tiệm Hoa Nắng giao hàng.',
                       perspectives=[dict(who='Chị Vy', emoji='😨', text='Ai đó biết chỗ ngồi của mình và gửi ảnh mình cho người lạ. Đáng sợ.'),
                                     dict(who='Bảo vệ', emoji='👮', text='Tôi bị kỷ luật vì dẫn người lên tầng không đúng quy định.')]),
                  dict(id='leak', label='Hỏi lễ tân giờ đi làm và số điện thoại của chị Vy rồi gửi anh Minh', quality='bad',
                       outcome='Lễ tân từ chối và báo lại chị Vy. Chị gửi phản ánh tới tiệm về việc dò thông tin cá nhân.',
                       perspectives=[dict(who='Chị Vy', emoji='🚫', text='Tiệm hoa mà đi hỏi số điện thoại của mình cho người khác?'),
                                     dict(who='Lễ tân', emoji='🛎️', text='Thông tin nhân viên không phải thứ để trao đổi cùng bó hoa.')])],
         lesson='Giao hoa là trao một lời nhắn, không phải trao thông tin cá nhân: người nhận có quyền biết và quyền từ chối.'),
    dict(id='FL-S02', title='Giao nhầm địa chỉ', npc=1, tone='tense', min_day=2,
         opening='6 giờ chiều, chị Hạnh gọi: “Mẹ chị chưa nhận được hoa!” Khánh kiểm lại thì bó hoa đã giao cho nhà 15/2, còn nhà mẹ chị là 15/2A. Tiệc sinh nhật lúc 7 giờ.',
         facts=[dict(id='slip', title='Phiếu giao', source='Máy in phiếu', text='Phiếu in “15/2”. Tin nhắn sửa thành “15/2A” tới sau khi phiếu đã in, không ai cập nhật.'),
                dict(id='neighbor', title='Nhà 15/2', source='Khánh (giao hàng)', text='Chủ nhà 15/2 tưởng con gái gửi tặng, đã cắm hoa vào bình.'),
                dict(id='time', title='Tủ mát', source='Nhung (thợ cắm)', text='Tủ còn đủ hồng phấn và hồng trắng để làm bó mới trong 30 phút.')],
         options=[dict(id='remake', label='Xin lỗi chị Hạnh, làm bó mới giao đúng 15/2A trước 7 giờ; nhẹ nhàng nói với nhà 15/2 và để họ giữ bó hoa', requires=['slip', 'time'], cost=45, quality='good', stars=5,
                       review='Tiệm nhận lỗi ngay, 40 phút sau mẹ tôi có bó hoa đúng ý. Còn tặng luôn nhà hàng xóm, dễ thương!',
                       outcome='Mẹ chị Hạnh nhận hoa lúc 6 giờ 50. Nhà 15/2 giữ bó hoa “nhầm” và gửi lời chúc mừng sinh nhật sang nhà bên.',
                       perspectives=[dict(who='Chị Hạnh', emoji='📞', text='Sai thì ai cũng có lúc, quan trọng là sửa kịp giờ.'),
                                     dict(who='Mẹ chị Hạnh', emoji='👵', text='Bó hoa đẹp, còn kèm lời xin lỗi viết tay. Bà vui.'),
                                     dict(who='Nhà 15/2', emoji='🏠', text='Tưởng con gửi, hóa ra nhầm — tiệm còn để tụi tôi giữ hoa. Ngại mà vui.')]),
                  dict(id='retrieve', label='Qua nhà 15/2 xin lại bó hoa rồi mang sang 15/2A', requires=['neighbor'], quality='ok', stars=3,
                       review='Hoa tới kịp nhưng đã bị rút ra cắm vào bình, cánh dập vài bông.',
                       outcome='Nhà 15/2 ngượng ngùng trả hoa. Bó hoa tới 15/2A kịp giờ nhưng không còn đẹp như lúc gói.',
                       perspectives=[dict(who='Nhà 15/2', emoji='😳', text='Đang vui thì bị xin lại, hơi quê.'),
                                     dict(who='Chị Hạnh', emoji='😕', text='Kịp giờ, nhưng mẹ chị nhận một bó hoa đã qua tay người khác.')]),
                  dict(id='blame', label='Nói với chị Hạnh là do chị nhắn địa chỉ trễ', requires=['slip'], quality='bad', stars=2,
                       review='Tôi đã nhắn sửa địa chỉ trước 3 tiếng. Tiệm không cập nhật mà còn đổ cho tôi.',
                       outcome='Chị Hạnh gửi ảnh tin nhắn có giờ gửi. Tiệm vẫn phải làm bó mới, nhưng mất khách.',
                       perspectives=[dict(who='Chị Hạnh', emoji='😠', text='Tin nhắn của chị có giờ gửi rõ ràng.'),
                                     dict(who='Khánh (giao hàng)', emoji='🛵', text='Phải chi có bước gọi xác nhận trước khi đi.')]),
                  dict(id='refund', label='Hoàn tiền, không giao lại vì sợ trễ tiệc', cost=60, quality='ok', stars=2,
                       review='Nhận lại tiền, nhưng sinh nhật mẹ tôi không có hoa.',
                       outcome='Tiền hoàn đủ; mẹ chị Hạnh thổi nến mà không có bó hoa con gái đặt.',
                       perspectives=[dict(who='Chị Hạnh', emoji='😞', text='Tiền đâu phải thứ chị cần tối nay.'),
                                     dict(who='Nhung (thợ cắm)', emoji='💐', text='30 phút là kịp mà…')])],
         lesson='Giao sai thì sửa cho người nhận trước, rồi sửa quy trình: gọi xác nhận địa chỉ lần cuối trước khi xuất phát.'),
    dict(id='FL-S03', title='Giá sỉ tăng gấp ba trước 20/10', npc=4, tone='gentle', min_day=2,
         opening='Tuần lễ 20/10, chợ hoa sỉ Bến Mây báo hồng đỏ từ 5 lên 15 xu một cành. Linh ghé hỏi: “Sao bó hồng tuần trước 100 xu mà giờ ghi 180 vậy chị?”',
         facts=[dict(id='wholesale', title='Hóa đơn sỉ', source='Chợ hoa sỉ Bến Mây', text='Hồng đỏ 5 → 15 xu/cành, hồng phấn 4 → 11 xu; cẩm chướng và cúc họa mi gần như giữ giá.'),
                dict(id='preorders', title='Đơn đặt trước', source='Sổ đơn', text='12 đơn 20/10 đã đặt từ tuần trước với báo giá cũ, đa số của học sinh, sinh viên.'),
                dict(id='alt', title='Hoa thay thế', source='Nhung (thợ cắm)', text='Bó cẩm chướng + baby đẹp, ý nghĩa biết ơn, giá gần như không đổi.')],
         options=[dict(id='fair', label='Giữ giá cũ cho đơn đặt trước; đơn mới báo giá theo giá sỉ kèm lý do, gợi ý bó cẩm chướng giá mềm', requires=['wholesale', 'preorders', 'alt'], quality='good', stars=5,
                       review='Chị giải thích rõ vì sao hồng lên giá, còn chỉ em bó cẩm chướng xinh mà vừa túi. Đơn đặt trước vẫn giữ giá cũ. Uy tín!',
                       outcome='Đơn cũ giữ lời hứa; khách mới hiểu lý do, nhiều bạn chọn bó cẩm chướng. Lãi mùa lễ thấp hơn mơ ước nhưng khách quay lại.',
                       perspectives=[dict(who='Linh', emoji='🎓', text='Được giải thích và có lựa chọn vừa túi thì em vui vẻ mua.'),
                                     dict(who='Chợ hoa Bến Mây', emoji='🚛', text='Mùa lễ bên tôi cũng bị nhà vườn tăng giá, tiệm nói rõ với khách là đúng.'),
                                     dict(who='Nhung (thợ cắm)', emoji='💐', text='Cẩm chướng cắm lên xinh lắm, mà không ai phải trả giá “lễ”.')]),
                  dict(id='gouge', label='Nhân dịp tăng giá gấp năm, ai hỏi cũng nói “hết hàng giá cũ”', quality='bad', stars=1,
                       review='Tiệm đẩy giá gấp năm lần ngày lễ, còn bảo đơn đặt trước hết hàng. Chặt chém.',
                       outcome='Doanh thu tuần lễ cao vọt, nhưng nhóm sinh viên đăng bài cảnh báo, sau lễ tiệm vắng hẳn.',
                       perspectives=[dict(who='Linh', emoji='😤', text='Em đặt từ tuần trước mà giờ bị báo hết giá cũ?'),
                                     dict(who='Bà Tám', emoji='👵', text='Buôn bán mà ăn một mùa thì mất cả năm.')]),
                  dict(id='cancel', label='Báo khách đặt trước phải bù thêm tiền, không thì hủy đơn', requires=['preorders'], quality='bad', stars=2,
                       review='Đặt trước để chắc giá, cuối cùng bị đòi thêm tiền sát ngày.',
                       outcome='Một nửa đơn đặt trước bị hủy, học sinh phải chạy đi mua chỗ khác ngay sát ngày lễ.',
                       perspectives=[dict(who='Linh', emoji='😞', text='Tụi em tin lời báo giá mới đặt trước mà.'),
                                     dict(who='Chợ hoa Bến Mây', emoji='🚛', text='Giá tăng là thật, nhưng hợp đồng đã chốt thì phải giữ.')]),
                  dict(id='absorb', label='Giữ giá cũ cho tất cả mọi đơn, tiệm chịu lỗ', cost=60, quality='ok', stars=5,
                       review='Giá không đổi dù ngày lễ, tuyệt vời!',
                       outcome='Khách rất vui, nhưng tiệm lỗ cả mùa lễ và phải trễ tiền trả chợ sỉ.',
                       perspectives=[dict(who='Linh', emoji='😊', text='Không tăng giá luôn, quá đỉnh.'),
                                     dict(who='Sổ tiệm', emoji='📒', text='Tháng này tiền nhập vượt tiền bán; lương thợ phải lùi vài ngày.')])],
         lesson='Giá theo mùa là thật; giữ lời hứa với đơn cũ và minh bạch với đơn mới mới là công bằng.'),
    dict(id='FL-S04', title='Người nhận nuôi mèo, khách muốn hoa ly', npc=5, tone='gentle', min_day=1,
         opening='Chú Phúc chọn bó ly trắng thật thơm tặng con gái mới dọn nhà. Chú kể thêm: “Con bé nuôi hai bé mèo, hay nhảy lên bàn lắm.”',
         facts=[dict(id='toxic', title='Sổ tay an toàn thú cưng', source='Tủ sách tiệm', text='Mọi phần của cây ly — phấn hoa, lá, cánh, cả nước trong bình — đều rất độc với mèo, có thể gây hại thận nghiêm trọng.'),
                dict(id='cats', title='Thói quen của mèo', source='Chú Phúc', text='Hai bé mèo hay nhảy lên bàn, gặm lá cây trong nhà.'),
                dict(id='alt', title='Hoa an toàn hơn', source='Nhung (thợ cắm)', text='Hồng và hướng dương an toàn hơn cho nhà có mèo; bạch đàn, baby cũng nên tránh vì mèo gặm dễ đau bụng.')],
         options=[dict(id='explain', label='Giải thích hoa ly độc với mèo, đề xuất bó hồng trắng – hướng dương, bỏ bạch đàn và baby', requires=['toxic', 'alt'], quality='good', stars=5,
                       review='Suýt nữa tặng con một bó hoa nguy hiểm cho mèo. Tiệm tư vấn tận tâm, bó hồng – hướng dương còn đẹp hơn.',
                       outcome='Chú Phúc đổi sang bó hồng trắng – hướng dương. Con gái chú gửi ảnh hai bé mèo nằm cạnh bình hoa.',
                       perspectives=[dict(who='Chú Phúc', emoji='👴', text='Chú đâu biết hoa ly độc vậy. Cảm ơn tiệm nói trước.'),
                                     dict(who='Con gái chú Phúc', emoji='🐈', text='Mèo nhà em mà gặm phải ly là phải đi cấp cứu. Ba chọn bó này quá chuẩn.')]),
                  dict(id='pollen', label='Vẫn bán ly nhưng tỉa hết nhụy phấn cho “an toàn”', requires=['cats'], quality='bad', stars=3,
                       review='Hoa đẹp, tiệm có tỉa nhụy. Sau mới biết lá và nước bình ly cũng độc với mèo.',
                       outcome='Con gái chú Phúc đọc được thông tin, phải bỏ bó ly ra ban công ngay trong tối.',
                       perspectives=[dict(who='Con gái chú Phúc', emoji='😟', text='Tỉa nhụy chưa đủ, cả cây đều độc với mèo.'),
                                     dict(who='Chú Phúc', emoji='😕', text='Tưởng tiệm đã lo chu đáo rồi.')]),
                  dict(id='sell', label='Khách muốn gì bán nấy, không nói thêm', quality='bad', stars=4,
                       review='Hoa thơm, đẹp, đóng gói kỹ.',
                       outcome='Bó ly được đặt trên bàn. May mà con gái chú phát hiện kịp khi mèo bắt đầu gặm lá.',
                       perspectives=[dict(who='Con gái chú Phúc', emoji='😰', text='Không ai dặn con một câu nào về mèo cả.'),
                                     dict(who='Nhung (thợ cắm)', emoji='😬', text='Mình biết mà không nói, là lỗi của mình.')])],
         lesson='Tư vấn hoa là tư vấn cả an toàn: hoa ly rất độc với mèo, kể cả phấn và nước bình.'),
    dict(id='FL-S05', title='Kệ hoa viếng gấp, băng rôn in sai', npc=2, tone='tense', min_day=2,
         opening='6 giờ 30 sáng, kệ hoa viếng đã lên xe thì Khánh phát hiện băng rôn in “Cụ ông Nguyễn Văn Tư”, trong khi cáo phó ghi “Cụ bà Nguyễn Thị Tư”. Lễ viếng bắt đầu lúc 8 giờ.',
         facts=[dict(id='obituary', title='Cáo phó', source='Bảng tin đầu hẻm', text='Cáo phó ghi: “Cụ bà Nguyễn Thị Tư, hưởng thọ 88 tuổi”.'),
                dict(id='order', title='Phiếu đặt', source='Sổ đơn', text='Cô Lụa đặt đúng “Cụ bà”. Lỗi do tiệm gõ nhầm khi in băng rôn.'),
                dict(id='printer', title='Máy in băng rôn', source='Xưởng tiệm', text='In lại mất khoảng 15 phút; tiệm còn cuộn băng trắng.')],
         options=[dict(id='reprint', label='Cho xe quay lại, in lại băng rôn đúng, giao trước 7 giờ 30; gọi cô Lụa báo và xin lỗi', requires=['obituary', 'order', 'printer'], cost=10, quality='good', stars=5,
                       review='Tiệm tự phát hiện, tự sửa và gọi báo tôi trước khi tôi kịp biết. Kệ hoa trang nghiêm, đúng tên cụ.',
                       outcome='Kệ hoa tới lúc 7 giờ 20 với băng rôn đúng. Gia đình không hề biết đã có sai sót.',
                       perspectives=[dict(who='Cô Lụa', emoji='🙏', text='Chuyện hiếu thì một chữ cũng không được sai. Tiệm làm tôi yên tâm.'),
                                     dict(who='Gia đình cụ Tư', emoji='🕯️', text='Kệ hoa của tổ dân phố đặt ngay lối vào, đúng tên mẹ tôi.'),
                                     dict(who='Khánh (giao hàng)', emoji='🛵', text='May là đọc lại băng rôn trước khi đi. Từ giờ đó là bước bắt buộc.')]),
                  dict(id='tape', label='Dán đè chữ “ông” bằng băng keo trắng rồi viết tay chữ “bà”', quality='ok', stars=2,
                       review='Kệ hoa đến đúng giờ, nhưng băng rôn chắp vá. Nhà tang lễ ai nhìn cũng thấy.',
                       outcome='Kệ hoa tới đúng giờ nhưng miếng băng keo lộ rõ. Cô Lụa phải giải thích với gia đình.',
                       perspectives=[dict(who='Gia đình cụ Tư', emoji='😔', text='Thấy tên mẹ bị dán sửa, lòng nặng thêm.'),
                                     dict(who='Cô Lụa', emoji='😣', text='Tôi đại diện cả tổ dân phố mà tới viếng với băng rôn chắp vá.')]),
                  dict(id='go', label='Giao luôn, chắc không ai để ý', quality='bad', stars=1,
                       review='Băng rôn ghi sai giới tính người mất. Gia đình rất buồn. Không thể chấp nhận.',
                       outcome='Con cháu cụ nhìn thấy ngay. Cô Lụa phải tháo băng rôn giữa lễ viếng và xin lỗi gia đình.',
                       perspectives=[dict(who='Gia đình cụ Tư', emoji='💔', text='Người mất rồi mà còn bị ghi sai tên.'),
                                     dict(who='Cô Lụa', emoji='😞', text='Tôi mất mặt với cả hẻm.')]),
                  dict(id='blame', label='Gọi cô Lụa nói phiếu đặt viết không rõ', requires=['order'], quality='bad', stars=1,
                       review='Phiếu tôi ghi rõ ràng mà tiệm còn đổ lỗi, giữa lúc tang gia bối rối.',
                       outcome='Cô Lụa chụp phiếu đặt gửi lại. Kệ hoa vẫn phải in lại, trễ giờ lễ viếng.',
                       perspectives=[dict(who='Cô Lụa', emoji='😤', text='Giờ này mà còn cãi nhau chuyện phiếu.'),
                                     dict(who='Khánh (giao hàng)', emoji='⌛', text='Mất 20 phút gọi điện qua lại, lẽ ra đã in xong.')])],
         lesson='Với tang lễ, một chữ sai là nỗi đau của cả gia đình: dừng lại, sửa cho đúng, nhận lỗi.'),
    dict(id='FL-S06', title='Cô dâu đổi màu hoa trước một ngày', npc=4, tone='tense', min_day=3,
         opening='Linh gọi: “Chị em đổi ý rồi! Mai cưới mà giờ muốn đổi từ tông trắng – hồng sang đỏ rượu vang hết, hoa cầm tay lẫn 8 hoa cài áo.”',
         facts=[dict(id='contract', title='Hợp đồng', source='Sổ đơn cưới', text='Hợp đồng chốt tông trắng – hồng, đã cọc 50%; điều khoản: đổi thiết kế trước 48 giờ, sau đó tính phụ phí thực tế.'),
                dict(id='stock', title='Tủ mát', source='Kho', text='Có 20 hồng đỏ thường; hồng đỏ rượu vang phải gọi Giao hỏa tốc Mây Xanh, đắt hơn 35%.'),
                dict(id='time', title='Nhân lực', source='Nhung (thợ cắm)', text='Làm lại toàn bộ mất khoảng 5 tiếng tối nay; Yến có thể ở lại phụ.')],
         options=[dict(id='choices', label='Gọi lại đưa hai phương án: giữ trắng – hồng thêm điểm đỏ từ hồng sẵn có (không phụ phí), hoặc đổi hết sang đỏ rượu vang kèm phụ phí hỏa tốc ghi rõ', requires=['contract', 'stock'], quality='good', stars=5, reward=30,
                       review='Tiệm đưa lựa chọn rõ ràng, phụ phí minh bạch. Chị em chọn đổi hết, hoa cưới đẹp mê!',
                       outcome='Cô dâu chọn đổi toàn bộ và trả phụ phí. Nhung và Yến làm tới 11 giờ đêm; sáng hôm sau hoa lên xe đúng giờ.',
                       perspectives=[dict(who='Linh', emoji='👰', text='Chị em được chọn, biết trước chi phí, không ai khó xử.'),
                                     dict(who='Nhung (thợ cắm)', emoji='💐', text='Tăng ca có phụ phí thì tụi em làm vui vẻ.'),
                                     dict(who='Giao hỏa tốc Mây Xanh', emoji='⚡', text='Đơn gấp nhưng rõ ràng, giao lúc 7 giờ tối.')]),
                  dict(id='yes_free', label='Đồng ý hết, không thu thêm, cả tiệm thức trắng', cost=60, quality='ok', stars=5,
                       review='Tiệm chiều hết cỡ, không lấy thêm đồng nào. Cảm động!',
                       outcome='Hoa cưới đẹp, cô dâu vui; tiệm lỗ đơn này và cả ngày hôm sau thợ mệt rã rời.',
                       perspectives=[dict(who='Linh', emoji='🥹', text='Tiệm tốt quá trời.'),
                                     dict(who='Yến (thợ cắm)', emoji='😵', text='Thức trắng không phụ phí, mai em xin nghỉ.')]),
                  dict(id='no', label='Từ chối vì hợp đồng đã chốt', requires=['contract'], quality='ok', stars=2,
                       review='Đúng hợp đồng nhưng không một lời gợi ý nào. Hơi cứng.',
                       outcome='Cô dâu dùng tông cũ nhưng không vui; Linh kể lại với cả nhóm bạn.',
                       perspectives=[dict(who='Linh', emoji='😕', text='Biết là đổi trễ, nhưng ít nhất cũng cho em một lựa chọn.'),
                                     dict(who='Nhung (thợ cắm)', emoji='🤷', text='Thêm vài điểm đỏ là làm được mà.')]),
                  dict(id='fake_yes', label='Nhận lời cho qua, nhưng vẫn làm tông cũ vì không kịp', quality='bad', stars=1,
                       review='Nhận lời đổi màu rồi giao y như cũ. Ngày cưới mà bị lừa.',
                       outcome='Cô dâu mở hộp hoa trong phòng trang điểm và bật khóc. Nhóm bạn của Linh không bao giờ quay lại.',
                       perspectives=[dict(who='Linh', emoji='😢', text='Không làm được thì nói, sao lại hứa?'),
                                     dict(who='Nhung (thợ cắm)', emoji='😞', text='Mình bị bắt làm điều mình biết là sai.')])],
         lesson='Thay đổi phút chót: nói rõ điều làm được và chi phí thật để khách chọn — không hứa suông.'),
    dict(id='FL-S07', title='Khách đòi trả bó hoa héo sau 5 ngày', npc=6, tone='tense', min_day=2,
         opening='Bà Tám mang bó hồng đã rũ tới quầy: “Mua có năm ngày mà héo hết! Tiệm bán hoa cũ cho bà phải không?”',
         facts=[dict(id='sale', title='Sổ bán', source='Máy tính tiền', text='Bó hồng bán 5 ngày trước, dùng lô hồng nhập trước đó 2 ngày — lúc bán chỉ còn khoảng 2 ngày tươi.'),
                dict(id='photo', title='Ảnh bà gửi', source='Bà Tám', text='Bình để cạnh cửa sổ nắng, nước đục, gốc chưa được cắt lại lần nào.'),
                dict(id='card', title='Thẻ chăm hoa', source='Quầy gói', text='Tiệm có kèm thẻ: thay nước mỗi ngày, cắt lại gốc, tránh nắng gắt.')],
         options=[dict(id='share', label='Nhận phần lỗi về lô hoa hơi cũ, tặng voucher 50% bó sau, hướng dẫn lại cách chăm; đổi quy trình: bó quà chỉ dùng lô còn ≥ 3 ngày', requires=['sale', 'photo'], cost=15, quality='good', stars=4,
                       review='Tiệm nhận phần lỗi của tiệm, còn chỉ bà cách giữ hoa. Công bằng, lần sau bà ghé.',
                       outcome='Bà Tám cầm voucher, dặn “lần sau lấy hoa mới cho bà”. Tiệm dán quy định chọn lô tươi cho đơn quà.',
                       perspectives=[dict(who='Bà Tám', emoji='👵', text='Bà cũng có lỗi để nắng, nhưng tiệm chịu nhận phần của tiệm, vậy là được.'),
                                     dict(who='Tuấn (sơ chế)', emoji='✂️', text='Từ giờ em dán ngày nhập lên từng xô cho dễ chọn lô.')]),
                  dict(id='refund', label='Hoàn tiền toàn bộ cho êm chuyện', cost=40, quality='ok', stars=4,
                       review='Được hoàn tiền nhanh gọn.',
                       outcome='Bà Tám về vui, nhưng cách chăm hoa và cách chọn lô trong tiệm vẫn như cũ.',
                       perspectives=[dict(who='Bà Tám', emoji='🙂', text='Tiền về là được, lần sau tính.'),
                                     dict(who='Nhung (thợ cắm)', emoji='🤔', text='Lần sau vẫn có thể lặp lại y chang.')]),
                  dict(id='deny', label='Từ chối: “Hoa tươi chỉ giữ 3–5 ngày, bà để nắng là lỗi của bà”', requires=['photo'], quality='bad', stars=2,
                       review='Bán hoa gần hết hạn rồi đổ hết lỗi cho khách.',
                       outcome='Bà Tám kể với cả xóm; vài người để ý tiệm hay bán hoa lô cũ.',
                       perspectives=[dict(who='Bà Tám', emoji='😤', text='Bà lớn tuổi chứ không lẫn. Hoa cũ bà nhìn là biết.'),
                                     dict(who='Tuấn (sơ chế)', emoji='😬', text='Thật ra lô đó hôm bán đã hơi mềm cánh.')])],
         lesson='Hoa là hàng sống: bán lô tươi nhất cho đơn quà, kèm hướng dẫn chăm — và chia trách nhiệm công bằng khi có phàn nàn.'),
]

SPEC = dict(
    id=ID, prefix='fl_', category='shop',
    meta=dict(short='Tiệm hoa', place='Tiệm Hoa Nắng', tagline='Mỗi bó hoa kể đúng một câu chuyện.', icon='flower',
              color='#c2577a', light='#fdeef3', weather='Nắng nhẹ, gió mát', work='Đơn hoa', station='Cắm hoa',
              greeting='Hỏi dịp tặng và hỏi thêm điều khách chưa nói, chọn hoa đúng ý nghĩa, sơ chế cành, bó – gói – viết thiệp rồi giao đúng giờ nhé.',
              caption='Hoa tươi, lời thật, giao đúng hẹn', map_label='10 · TIỆM HOA NẮNG'),
    people=PEOPLE,
    staff=[('Nhung', 'designer', 'Bó xoắn ốc đều tay, phối màu có gu.', 78, 90), ('Tuấn', 'prep', 'Cắt gốc, tuốt lá nhanh như máy.', 88, 80),
           ('Khánh', 'courier', 'Thuộc từng con hẻm, luôn gọi xác nhận trước khi giao.', 85, 82), ('Yến', 'designer', 'Chậm mà chắc, cắm kệ viếng rất trang nghiêm.', 68, 94)],
    roles={'designer': 'Thợ cắm hoa', 'prep': 'Sơ chế hoa', 'courier': 'Giao hoa'},
    inventory=dict(items=ITEMS, capacity=40),
    prices={**{k: ITEM_INDEX[k]['price'] for k in FLOWERS}, 'bouquet': 25, 'vase': 40, 'basket': 45, 'wreath': 70},
    tip=3,
    physical=('fl_pick', 'fl_arrange', 'fl_wrap', 'fl_deliver', 'fl_dump', 'fl_base', 'fl_done', 'fl_pin'),
    free_actions=(),
    no_tick=('fl_lift', 'fl_remove', 'fl_push', 'fl_tab', 'fl_cover'),
    waste_items=('bouquet',),
    activity=('💐', 'Tủ hoa gọn gàng', [('Hồng đỏ', 'Tủ mát'), ('Giấy kraft', 'Kệ gói'), ('Baby trắng', 'Tủ mát'), ('Ruy băng', 'Kệ gói')],
              ['Hỏi dịp tặng', 'Chọn hoa và sơ chế', 'Bó, gói, viết thiệp', 'Giao đúng giờ']),
    stories=[('Bó hoa cầu hôn của anh Minh', ('Anh Minh ghé tiệm ba lần chỉ để hỏi “9 bông hay 11 bông thì ý nghĩa hơn”. Anh run tới mức làm rơi cả ví.',
                                              'Bạn cùng anh chọn 9 hồng đỏ, viết nháp lời thiệp, còn tập cho anh cách cầm bó hoa sao cho không che mặt.',
                                              'Tối đó anh gửi tiệm tấm ảnh chiếc nhẫn trên tay cô ấy, kèm dòng chữ: “Cô ấy nói có!”')),
             ('Ba bé mèo nhà mẹ chị Hạnh', ('Chị Hạnh kể mẹ chị từng suýt mất một bé mèo vì gặm lá cây lạ. Từ đó chị sợ tặng hoa cho mẹ.',
                                            'Bạn lập cho chị một danh sách “hoa an toàn cho nhà có mèo” dán ngay quầy.',
                                            'Mẹ chị Hạnh ghé tiệm lần đầu, mang theo ảnh ba bé mèo nằm cạnh bình hồng — không bé nào bị sao.')),
             ('Kệ hoa của tổ dân phố', ('Cô Lụa lo việc hiếu hỉ cho cả hẻm, muốn một kệ hoa viếng trang nghiêm mà vừa quỹ tổ dân phố.',
                                        'Bạn cùng cô chọn cúc trắng, ly trắng và băng rôn đọc lại ba lần trước khi in.',
                                        'Tổ dân phố giao tiệm làm hoa cho mọi việc hiếu hỉ trong năm, kèm câu dặn: “Cứ đúng từng chữ như lần đó”.'))],
    review_asides=['Hoa tươi rói, cắm bình ba ngày vẫn căng cánh 🌸', 'Thiệp viết đúng điều mình muốn nói mà không nói được.',
                   'Người nhận hỏi tên tiệm ngay khi mở giấy gói.', 'Giao đúng giờ, người nhận cười tít mắt!'],
    situations=SITUATIONS,
    guide='Dịp tặng → hỏi thêm màu, người nhận, giờ giao → chọn hoa đúng ý nghĩa & tông → cắt xéo, tuốt lá, ngâm nước → đế/mút → bó/cắm → gói, ruy băng, thiệp → giao đúng giờ.',
)
