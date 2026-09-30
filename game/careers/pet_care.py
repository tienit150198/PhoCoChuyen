"""Pet Care Mèo Mập — grooming table, boarding kennel and feeding rounds (plugin career).

Real work of the job:
* Intake: the owner's form gives species, breed, weight, age, vaccinations,
  temperament and instructions — but some facts only show when you look at the
  animal (scale, coat, skin, ears, nails, body, gait, mood) or read the vaccine
  book. Owners are not always right (or honest).
* Grooming in order: brush/detangle → bath at 36–39 °C with the right shampoo
  (puppy, sensitive; medicated only with a vet prescription) → rinse fully
  (real seconds) → dry at a safe heat (real seconds) → trim only the tip of dark
  nails (cutting short nicks the quick: stop the bleeding, tell the owner) →
  clean healthy ears (skip sore ears and refer to a vet).
* Temperament: a stress meter rises with each step. A calm voice, a towel wrap
  (cats), a break or a treat (unless the owner said no treats) lower it; from 80
  you must calm the pet or stop. A muzzle only for a biting dog and only with the
  owner's consent — never for a cat.
* Boarding: the vaccine book must be seen (no valid book, no boarding), a
  coughing dog is not admitted, pen by species and size, feeding plan by the
  chart (weight × life stage ÷ meals, ±10%), the owner's food when there is an
  allergy, solo play for a dog that fights other dogs.
* Feeding rounds: portion by the chart, walk dogs with a poop bag or clean the
  litter, notice warning signs (not eating, lethargy, limping, lumps) and tell
  the owner to see a vet — never diagnose or give medicine.

v0.5 (tasks with gen=2; saved tasks keep the first generator):
* Body language: the stress number is hidden on new grooming tasks — the table
  shows what the pet does (licking lips, ears pinned, tail tucked…) and the
  stylist reads it. Messages speak in cues too.
* Escapes: a runner (and, from day 6, any pet pushed near panic) may leap off the
  table. A table loop prevents it; once loose, cornering calmly or luring with a
  treat works, grabbing makes things worse.
* Special cases: flat-faced breeds (cool dryer only), an owner hiding a fever
  (thermometer at intake), a vaccine that runs out before pick-up day, a
  prescribed pill on the feeding round, and adoption interviews (match a family
  to a rescue by home, hours alone, small children, other pets and allergies).
* Luck of the day (heat, rain, moulting season, holiday rush, adoption day) and
  surprises at the counter with real consequences (kit desk engine).
"""
from __future__ import annotations
import copy
from ..jsoncopy import tree_copy
import math
from . import kit
from .. import consequences as cq
from .. import archive as ar

ID = 'pet_care'
TEMP = dict(low=36, high=39, burn=42)      # bath water °C: comfortable window, scald from `burn`
RINSE_MIN = 8                              # seconds of running water to rinse all shampoo out
DRY_NEED = dict(short=6, long=12)          # seconds at 'warm' for a fully dry coat; 'cool' needs 1.5×
DRY_OVER = 3                               # drying longer than 3× the need dries skin and stresses the pet
STRESS_STOP = 80
TOL = 10                                   # feeding portion tolerance, %
VET = 'Phòng khám Thú y Cỏ May'

# Game-rule feeding chart: grams of dry food per kg per day by weight band.
CHART = dict(dog=[[10, 25], [25, 20], [999, 15]], cat=[[999, 15]])
STAGE_PCT = dict(young=150, adult=100, senior=90)
MEALS = dict(young=3, adult=2, senior=2)
STAGE_NAMES = dict(young='Con non (< 12 tháng)', adult='Trưởng thành', senior='Lớn tuổi')
SPECIES_NAMES = dict(dog='Chó', cat='Mèo')

PENS = [
    dict(id='d1', name='Chuồng nhỏ 1', emoji='🏠', zone='dog', max_kg=10, unlock=1),
    dict(id='d2', name='Chuồng nhỏ 2', emoji='🏠', zone='dog', max_kg=10, unlock=1),
    dict(id='d3', name='Chuồng lớn', emoji='🏡', zone='dog', max_kg=60, unlock=1),
    dict(id='c1', name='Tầng mèo 1', emoji='🧺', zone='cat', max_kg=12, unlock=1),
    dict(id='c2', name='Tầng mèo 2', emoji='🧺', zone='cat', max_kg=12, unlock=1),
    dict(id='c3', name='Tầng mèo view cửa sổ', emoji='🪟', zone='cat', max_kg=12, unlock=2),
]
PEN_INDEX = {x['id']: x for x in PENS}

SHAMPOOS = [
    dict(id='normal', item='sh_normal', name='Sữa tắm thường', emoji='🧴', note='Cho chó trưởng thành da khỏe. Không dùng cho mèo.'),
    dict(id='puppy', item='sh_puppy', name='Sữa tắm cún con', emoji='🍼', note='Dịu nhẹ, không cay mắt, cho chó mèo dưới 12 tháng.'),
    dict(id='sensitive', item='sh_sensitive', name='Sữa tắm da nhạy cảm', emoji='🌿', note='Không mùi, cho da dễ kích ứng và cho mèo.'),
    dict(id='medicated', item=None, name='Sữa tắm trị liệu (chủ mang)', emoji='💊', note='Chỉ dùng khi có đơn của bác sĩ thú y.'),
]
SHAMPOO_INDEX = {x['id']: x for x in SHAMPOOS}

STEPS = [
    dict(id='brush', name='Chải, gỡ rối', emoji='🪮'),
    dict(id='bath', name='Tắm nước ấm', emoji='🛁'),
    dict(id='rinse', name='Xả sạch bọt', emoji='🚿'),
    dict(id='dry', name='Lau, sấy khô', emoji='💨'),
    dict(id='nails', name='Cắt móng', emoji='✂️'),
    dict(id='ears', name='Vệ sinh tai', emoji='👂'),
]
SERVICE_NAMES = dict(brush='Chải lông', bath='Tắm sấy', nails='Cắt móng', ears='Vệ sinh tai')

BASE_STRESS = dict(calm=10, nervous=35, bitey=30, dog_aggressive=15)
STRESS_MULT = dict(calm=0.5, nervous=1.5, bitey=1.0, dog_aggressive=0.5)   # how strongly each step upsets the pet
STEP_STRESS = dict(brush=5, flea=5, bath=10, rinse=5, warm=10, cool=5, nails=15, ears=10)
CALM = [
    dict(id='voice', name='Nói nhỏ, vuốt ve', emoji='🗣️', drop=15),
    dict(id='wrap', name='Quấn khăn (mèo)', emoji='🌯', drop=20),
    dict(id='treat', name='Cho bánh thưởng', emoji='🍪', drop=25),
    dict(id='break', name='Cho nghỉ 5 phút', emoji='⏸️', drop=30),
]
CALM_INDEX = {x['id']: x for x in CALM}

PARTS = dict(
    vaccine=dict(emoji='📒', label='Xem sổ tiêm'), scale=dict(emoji='⚖️', label='Cân bé'),
    coat=dict(emoji='🪮', label='Vạch lông'), skin=dict(emoji='🔎', label='Xem da'),
    ears=dict(emoji='👂', label='Soi tai'), nails=dict(emoji='🐾', label='Xem móng'),
    body=dict(emoji='🤲', label='Sờ nắn thân'), gait=dict(emoji='🚶', label='Cho bé đi vài bước'),
    mood=dict(emoji='💬', label='Làm quen, xem phản ứng'), bowl=dict(emoji='🥣', label='Xem bát tối qua'),
    energy=dict(emoji='⚡', label='Quan sát tinh thần'),
    temp=dict(emoji='🌡️', label='Đo nhiệt độ'),
    home=dict(emoji='🏠', label='Hỏi chỗ ở'), time=dict(emoji='⏰', label='Hỏi giờ vắng nhà'),
    kids=dict(emoji='🧒', label='Hỏi về trẻ nhỏ'), pets=dict(emoji='🐾', label='Hỏi thú đang nuôi'),
    allergy=dict(emoji='🤧', label='Hỏi dị ứng lông'),
)
JOB_PARTS = dict(groom=['scale', 'coat', 'skin', 'ears', 'nails', 'body', 'gait', 'mood'],
                 board=['vaccine', 'scale', 'mood', 'body', 'gait', 'temp'],
                 feed=['bowl', 'energy', 'gait', 'body'],
                 adopt=['home', 'time', 'kids', 'pets', 'allergy'])

SIGNS = dict(
    ears=dict(part='ears', label='Tai đỏ, có mùi hôi'), lump=dict(part='body', label='Cục u nhỏ dưới da'),
    limp=dict(part='gait', label='Đi khập khiễng'), fleas=dict(part='coat', label='Có bọ chét'),
    appetite=dict(part='bowl', label='Bỏ ăn từ tối qua'), lethargy=dict(part='energy', label='Lờ đờ, mệt'),
    cough=dict(part='body', label='Ho khan, chảy nước mũi'),
    fever=dict(part='temp', label='Sốt 39,8°C'),
)
REPORTS = [
    dict(id='done', text='Kể lại các bước đã làm, dặn chăm lông ở nhà', jobs=['groom', 'feed']),
    dict(id='nick', text='Xin lỗi thật lòng: lỡ cắt chạm tủy móng, đã cầm máu, không tính tiền cắt móng', jobs=['groom']),
    dict(id='stopped', text='Bé quá căng thẳng nên tiệm dừng giữa chừng, chỉ tính phần đã làm', jobs=['groom']),
    dict(id='vet_ears', text='Tai đỏ, có mùi — nên đưa bé đi bác sĩ thú y kiểm tra', jobs=['groom']),
    dict(id='vet_fleas', text='Có bọ chét — hỏi bác sĩ thú y thuốc trị hợp loài và cân nặng', jobs=['groom']),
    dict(id='vet_lump', text='Có cục u nhỏ dưới da — nên cho bác sĩ thú y xem sớm', jobs=['groom', 'feed']),
    dict(id='vet_limp', text='Bé đi khập khiễng — nên cho bác sĩ thú y khám chân', jobs=['groom', 'feed']),
    dict(id='vet_appetite', text='Bé bỏ ăn từ tối qua — báo chủ, nếu kéo dài nên đi khám', jobs=['feed']),
    dict(id='vet_lethargy', text='Bé lờ đờ bất thường — báo chủ ngay, đề nghị đưa đi khám', jobs=['feed']),
    dict(id='diagnose', text='“Chắc bé bị nấm/viêm rồi, mua thuốc về cho uống là khỏi”', jobs=['groom', 'feed']),
]
REPORT_INDEX = {x['id']: x for x in REPORTS}

ITEMS = [
    dict(id='sh_normal', name='Sữa tắm thường (chó)', emoji='🧴', group='sữa tắm', unit='lần', cost=1, start=12),
    dict(id='sh_puppy', name='Sữa tắm cún con', emoji='🍼', group='sữa tắm', unit='lần', cost=1, start=8),
    dict(id='sh_sensitive', name='Sữa tắm da nhạy cảm', emoji='🌿', group='sữa tắm', unit='lần', cost=2, start=8),
    dict(id='conditioner', name='Dầu xả gỡ rối', emoji='✨', group='sữa tắm', unit='lần', cost=2, unlock=2),
    dict(id='towel', name='Khăn tắm thú cưng', emoji='🧺', group='lau sấy', unit='chiếc', cost=1, start=16),
    dict(id='cotton', name='Bông vệ sinh tai', emoji='☁️', group='vệ sinh', unit='miếng', cost=1, start=20),
    dict(id='styptic', name='Bột cầm máu móng', emoji='🩹', group='vệ sinh', unit='lần', cost=2, start=4),
    dict(id='poop_bag', name='Túi nhặt phân', emoji='🛍️', group='vệ sinh', unit='cái', cost=1, start=12),
    dict(id='dog_food', name='Hạt cho chó (vị gà)', emoji='🦴', group='thức ăn', unit='bữa', cost=2, life=30, start=12, allergen='chicken'),
    dict(id='cat_food', name='Hạt cho mèo (vị cá)', emoji='🐟', group='thức ăn', unit='bữa', cost=2, life=30, start=10, allergen='fish'),
    dict(id='treat', name='Bánh thưởng', emoji='🍪', group='thức ăn', unit='cái', cost=1, life=20, start=15),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}
HOUSE_FOOD = dict(dog='dog_food', cat='cat_food')
ALLERGY_NAMES = dict(chicken='thịt gà', fish='cá')

PEOPLE = [
    ('Chị Ngân', 'Chủ bé Poodle', 'Chăm chó như con, hỏi kỹ từng loại sữa tắm.', 'picky'),
    ('Anh Khoa', 'Sinh viên nuôi Corgi', 'Vui tính, hay quên giấy tờ, câu cửa miệng “không sao đâu”.', 'genz'),
    ('Cô Hạnh', 'Chủ mèo già', 'Nhẹ nhàng, thương con Mướp 12 tuổi hơn cả cháu nội.', 'warm'),
    ('Chú Sơn', 'Chủ chó lớn', 'Hay chỉ đạo, đi công tác liên tục.', 'bossy'),
    ('Bé Na', 'Cô bé 9 tuổi (đi cùng mẹ)', 'Lần đầu nuôi mèo, hỏi rất nhiều câu.', 'genz'),
    ('Bà Tư', 'Hàng xóm đầu hẻm', 'Nói thẳng, chó nhà bà “chưa ai tắm nổi”.', 'sour'),
    ('Anh Duy', 'Nhân viên văn phòng', 'Ít nói, đọc kỹ hóa đơn, mèo Ba Tư khó tính.', 'quiet'),
    ('Chị Vy', 'Chủ chó Jack Russell', 'Chạy bộ mỗi sáng, nói nhanh, chó nhà cũng nhanh như chủ.', 'genz'),
    ('Anh Bảo', 'Chủ chó Pug', 'Hiền, thương con Pug mập như con ruột.', 'warm'),
    ('Cô Lài', 'Chủ chó Poodle', 'Hay vội, ngại tốn tiền đi khám.', 'sour'),
    ('Anh Tín', 'Bố của hai bé', 'Nhiệt tình, hứa hơi nhanh.', 'bossy'),
    ('Chị Quyên', 'Nhân viên ngân hàng', 'Sống một mình, đi làm giờ hành chính, thương mèo.', 'quiet'),
    ('Ông Sáu', 'Hưu trí có vườn', 'Chậm rãi, thích đi bộ buổi sáng.', 'warm'),
    ('Bác sĩ Hòa', 'Thú y phường', 'Nghiêm, kiểm sổ sách kỹ.', 'picky'),
    ('Chị Diễm', 'Đại lý sữa tắm', 'Nói ngọt, hàng rẻ bất ngờ.', 'genz'),
    ('Chị Mây', 'Nhóm cứu hộ thú lạc', 'Lúc nào cũng ôm theo một lồng mèo con.', 'warm'),
]

JOB_ORDER = ('groom', 'board', 'groom', 'feed')
JOB_NAMES = dict(groom='Tắm & cắt tỉa', board='Nhận lưu trú', feed='Chăm bé lưu trú', adopt='Nhận nuôi')

# name, species, breed, coat, kg said, kg, months, mood said, mood, skin, rx, ears, nails, matted, signs, services, short nails, no treat, note
GROOMS = [
    dict(npc=0, name='Bông', species='dog', breed='Poodle', coat='long', kg_said=5, kg=6, months=36, mood_said='calm', mood='calm', skin='ok', rx=False,
         ears='dirty', nails='clear', matted=True, signs=[], services=['brush', 'bath', 'nails', 'ears'], short_nails=True, no_treat=False,
         note='Cắt móng ngắn giúp chị nha, bé hay cào sofa. Tai hơi bẩn, em vệ sinh luôn.', min_day=1),
    dict(npc=1, name='Bơ', species='dog', breed='Corgi', coat='long', kg_said=11, kg=13, months=24, mood_said='calm', mood='nervous', skin='sensitive', rx=False,
         ears='ok', nails='dark', matted=False, signs=[], services=['brush', 'bath', 'nails'], short_nails=True, no_treat=False,
         note='Bé hiền lắm, tắm nhanh giúp em nha! Móng cắt thật ngắn vào.', min_day=1),
    dict(npc=3, name='Lu', species='dog', breed='Golden', coat='long', kg_said=28, kg=30, months=108, mood_said='calm', mood='calm', skin='ok', rx=False,
         ears='dirty', nails='dark', matted=False, signs=['ears', 'lump'], services=['brush', 'bath', 'ears'], short_nails=False, no_treat=True,
         note='Lu đang giảm cân, tuyệt đối không bánh thưởng. Tai hay ngứa, vệ sinh thật kỹ vào.', min_day=1),
    dict(npc=4, name='Mochi', species='cat', breed='Mèo Anh lông ngắn', coat='short', kg_said=2, kg=2, months=5, mood_said='nervous', mood='nervous', skin='ok', rx=False,
         ears='ok', nails='clear', matted=False, signs=[], services=['brush', 'bath', 'nails'], short_nails=False, no_treat=False,
         note='Mochi lần đầu đi tắm, con sợ bé khóc lắm.', min_day=1),
    dict(npc=5, name='Vện', species='dog', breed='Chó ta', coat='short', kg_said=12, kg=12, months=60, mood_said='bitey', mood='bitey', skin='ok', rx=False,
         ears='ok', nails='dark', matted=False, signs=['fleas'], services=['brush', 'bath', 'nails'], short_nails=False, no_treat=False,
         note='Nó hay đớp người lạ lắm, cháu cẩn thận. Dạo này nó gãi suốt.', min_day=1),
    dict(npc=2, name='Mướp', species='cat', breed='Mèo ta', coat='short', kg_said=4, kg=4, months=150, mood_said='calm', mood='nervous', skin='ok', rx=False,
         ears='ok', nails='clear', matted=False, signs=['limp'], services=['brush', 'nails'], short_nails=False, no_treat=False,
         note='Mướp già rồi, chỉ chải lông với cắt móng thôi con.', min_day=1),
    dict(npc=6, name='Xám', species='cat', breed='Mèo Ba Tư', coat='long', kg_said=5, kg=5, months=48, mood_said='nervous', mood='bitey', skin='ok', rx=True,
         ears='ok', nails='clear', matted=True, signs=[], services=['brush', 'bath', 'nails'], short_nails=False, no_treat=False,
         note='Bác sĩ kê sữa tắm trị nấm cho Xám, tôi gửi kèm đơn và chai.', min_day=2),
    dict(npc=0, name='Mít', species='dog', breed='Phốc sóc', coat='long', kg_said=2, kg=2, months=4, mood_said='nervous', mood='nervous', skin='ok', rx=False,
         ears='dirty', nails='clear', matted=False, signs=[], services=['brush', 'bath', 'ears'], short_nails=False, no_treat=False,
         note='Cún mới về nhà hai tuần, tắm lần đầu đó em.', min_day=2),
]
# name, species, breed, kg said, kg, months, mood said, mood, vaccine said, vaccine, signs, nights, own food, allergy, note
BOARDS = [
    dict(npc=3, name='Lu', species='dog', breed='Golden', kg_said=28, kg=30, months=108, mood_said='calm', mood='calm', vax='valid', signs=[],
         nights=2, food_own=True, allergy=None, note='Tôi đi công tác 2 ngày, gửi kèm túi hạt của Lu. Sổ tiêm trong ba lô.', min_day=1),
    dict(npc=1, name='Bơ', species='dog', breed='Corgi', kg_said=11, kg=13, months=24, mood_said='calm', mood='nervous', vax='expired', signs=[],
         nights=3, food_own=False, allergy=None, note='Em về quê 3 ngày. Tiêm đủ hết rồi anh, yên tâm!', min_day=1),
    dict(npc=2, name='Mướp', species='cat', breed='Mèo ta', kg_said=4, kg=4, months=150, mood_said='calm', mood='calm', vax='valid', signs=[],
         nights=2, food_own=True, allergy=None, note='Mướp chỉ ăn hạt quen, cô gửi kèm. Nhờ con để bé chỗ yên tĩnh.', min_day=1),
    dict(npc=5, name='Vện', species='dog', breed='Chó ta', kg_said=9, kg=12, months=60, mood_said='calm', mood='dog_aggressive', vax='valid', signs=[],
         nights=1, food_own=False, allergy=None, note='Gửi nó một đêm, bà đi ăn cưới. Nó hiền với người lắm.', min_day=1),
    dict(npc=6, name='Xám', species='cat', breed='Mèo Ba Tư', kg_said=5, kg=5, months=48, mood_said='nervous', mood='nervous', vax='valid', signs=[],
         nights=2, food_own=False, allergy=None, note='Xám sợ tiếng chó sủa. Tôi cần hóa đơn ghi rõ số đêm.', min_day=1),
    dict(npc=0, name='Bông', species='dog', breed='Poodle', kg_said=5, kg=6, months=36, mood_said='calm', mood='calm', vax='valid', signs=['cough'],
         nights=2, food_own=False, allergy=None, note='Bé hơi hắt hơi chút xíu thôi, không sao đâu em.', min_day=2),
    dict(npc=4, name='Mochi', species='cat', breed='Mèo Anh lông ngắn', kg_said=2, kg=2, months=5, mood_said='nervous', mood='nervous', vax='valid', signs=[],
         nights=1, food_own=True, allergy='fish', note='Mochi dị ứng cá, con gửi hạt riêng cho mèo con. Bé ăn mấy bữa ạ?', min_day=2),
    dict(npc=5, name='Vàng', species='dog', breed='Chó ta', kg_said=8, kg=8, months=30, mood_said='calm', mood='calm', vax='none', signs=[],
         nights=2, food_own=True, allergy='chicken', note='Con Vàng dị ứng thịt gà, bà gửi bao hạt cá. Sổ tiêm ở nhà, mà tiêm rồi đó.', min_day=1),
]
# name, species, breed, kg, months, food, no treat, signs, note
FEEDS = [
    dict(npc=3, name='Ki', species='dog', breed='Béc-giê', kg=32, months=84, food='own', no_treat=False, signs=[], note='Ki quen ăn lúc 7 giờ, dắt đi dạo xong mới ăn.', min_day=1),
    dict(npc=2, name='Mun', species='cat', breed='Mèo ta', kg=4, months=132, food='house', no_treat=False, signs=['appetite'], note='Mun kén ăn, nhờ tiệm để ý giúp cô.', min_day=1),
    dict(npc=5, name='Mực', species='dog', breed='Chó ta', kg=12, months=60, food='house', no_treat=False, signs=['limp'], note='Thằng Mực ham chạy, dắt nó đi một vòng.', min_day=1),
    dict(npc=6, name='Khói', species='cat', breed='Mèo Anh lông ngắn', kg=5, months=48, food='house', no_treat=False, signs=[], note='Gửi tôi ảnh Khói ăn sáng nếu được.', min_day=1),
    dict(npc=0, name='Kem', species='dog', breed='Poodle', kg=6, months=36, food='house', no_treat=False, signs=['lethargy'], note='Kem hay làm nũng, nhớ nói chuyện với bé nha.', min_day=2),
    dict(npc=4, name='Bánh Bao', species='cat', breed='Mèo ta', kg=2, months=5, food='own', no_treat=False, signs=[], note='Bánh Bao ăn hạt mèo con con gửi. Bé ăn nhiều bữa nhỏ ạ.', min_day=1),
    dict(npc=1, name='Sữa', species='dog', breed='Corgi', kg=13, months=24, food='house', no_treat=True, signs=['lump'], note='Sữa đang ăn kiêng, đừng cho bánh thưởng nha anh.', min_day=2),
]
TEMPLATES = dict(groom=GROOMS, board=BOARDS, feed=FEEDS)

# ================================================================ v0.5 — second generator
GEN = 2
TODAY = [
    dict(id='steady', title='Ngày thường', emoji='☀️', weight=3, text='Khách đều đều, làm kỹ từng bé.'),
    dict(id='heat', title='Nắng nóng 37°C', emoji='🥵', min_day=2, weight=2, text='Bé nào cũng dễ mệt: mỗi bước làm bé căng thẳng hơn thường lệ.'),
    dict(id='rain', title='Mưa dầm, trời ẩm', emoji='🌧️', min_day=2, weight=2, text='Trời ẩm: lông lâu khô, cần sấy lâu gấp rưỡi.'),
    dict(id='shed', title='Mùa thay lông', emoji='🌬️', min_day=2, weight=2, text='Lông rụng từng mảng: bé lông dài nào cũng dễ rối cục, nhớ gỡ trước khi tắm.'),
    dict(id='holiday', title='Cao điểm gửi lưu trú dịp lễ', emoji='🧳', min_day=2, weight=2, text='Nhiều chủ đi xa gửi bé; ai cũng vội hơn một chút.'),
    dict(id='adopt', title='Ngày hội nhận nuôi', emoji='🏡', min_day=3, weight=2, text='Nhóm cứu hộ mang các bé tới tìm nhà; nhiều gia đình ghé phỏng vấn.'),
]
TODAY_INDEX = {x['id']: x for x in TODAY}
SPECIAL_P = (0.3, 0.4, 0.5, 0.6)           # chance a later slot is a special case, by difficulty tier
SHOWN_CASES = ('escape', 'flat', 'med', 'adopt')   # hidden twists ('hidden', 'vax_short') stay off the ticket
CASES = dict(escape=dict(emoji='🏃', label='Bé hay trốn khỏi bàn'), flat=dict(emoji='😮‍💨', label='Giống mặt ngắn'),
             med=dict(emoji='💊', label='Cho uống thuốc theo đơn'), adopt=dict(emoji='🏡', label='Phỏng vấn nhận nuôi'))
MOOD_BANDS = [dict(id='relaxed', top=29, name='Thư thái'), dict(id='uneasy', top=59, name='Hơi lo'),
              dict(id='stressed', top=79, name='Căng thẳng'), dict(id='panic', top=100, name='Hoảng sợ')]
BAND_NAME = {x['id']: x['name'] for x in MOOD_BANDS}
CUES = dict(
    dog=dict(relaxed=['Đuôi vẫy thả lỏng', 'Miệng hé, thở đều', 'Thân mềm, dựa vào tay bạn'],
             uneasy=['Liếm mép liên tục', 'Ngáp dù không buồn ngủ', 'Quay mặt tránh nhìn'],
             stressed=['Tai cụp ra sau', 'Đuôi kẹp giữa hai chân', 'Thở hổn hển, rụng lông nhiều'],
             panic=['Lộ tròng trắng mắt', 'Run bắn, cố giật khỏi bàn', 'Gầm gừ, nhe răng']),
    cat=dict(relaxed=['Đuôi dựng nhẹ', 'Mắt lim dim, chớp chậm', 'Dụi má vào tay bạn'],
             uneasy=['Đuôi quất qua lại', 'Tai xoay ngang', 'Liếm mũi, nuốt khan'],
             stressed=['Tai ép dẹt', 'Đồng tử giãn to', 'Gầm gừ trầm trong cổ'],
             panic=['Xù lông, cong lưng', 'Thở há miệng', 'Rít lên, vung vuốt']))
RUNNER_CUE = 'Liếc về phía cửa, chân sau co lại như chực nhảy'
BOLT_AT = dict(runner=55, other=75)        # stress from which a pet may leap off the table
BOLT_P = dict(runner=0.75, other=0.35)
BOLT_STEPS = ('pc_brush', 'pc_bath', 'pc_nails', 'pc_ears')
CATCH = [dict(id='corner', emoji='🚪', name='Đóng cửa, ngồi thấp, gọi tên nhỏ nhẹ', note='Chậm mà chắc — chủ phải chờ thêm một lúc.'),
         dict(id='lure', emoji='🍪', name='Lắc túi bánh dụ bé về', note='Nhanh, tốn một bánh thưởng.'),
         dict(id='grab', emoji='🫳', name='Lao tới chụp lấy bé', note='Nhanh nhất, nhưng bé đang hoảng.')]
CORNER_WAIT = 6                              # patience the owner loses while the pet comes back by itself
CATCH_IDS = [x['id'] for x in CATCH]
DOSES = [dict(id='half', name='Nửa viên'), dict(id='one', name='Một viên'), dict(id='two', name='Hai viên cho mau khỏi')]
DOSE_IDS = [x['id'] for x in DOSES]
DOSE_NAME = {x['id']: x['name'] for x in DOSES}
RULES = [
    'Đọc tín hiệu cơ thể trước mỗi bước: liếm mép, ngáp, tai cụp, đuôi kẹp là bé đang lo — dỗ hoặc cho nghỉ rồi mới làm tiếp.',
    'Bé hay trốn: đeo vòng giữ cổ mềm trên bàn trước khi làm, và không rời bé khi bé đang trên bàn.',
    'Bé nhảy khỏi bàn: đừng đuổi, đừng chụp — đóng cửa, ngồi thấp, gọi nhỏ, hoặc dụ bằng bánh nếu chủ cho.',
    'Giống mặt ngắn (Pug, Ba Tư mặt tịt): chỉ sấy nấc mát — hơi ấm phả vào mặt làm bé khó thở.',
    'Nhận lưu trú: đo nhiệt độ; chó mèo trên 39,2°C là sốt — không nhận, mời đi khám.',
    'Sổ tiêm phải còn hạn tới ngày chủ đón bé, không chỉ còn hạn hôm nay.',
    'Thuốc cho bé lưu trú: đúng liều trên nhãn bác sĩ thú y, cho cùng bữa ăn; không tăng liều theo lời dặn miệng.',
    'Nhận nuôi: hỏi chỗ ở, giờ vắng nhà, trẻ nhỏ, thú đang nuôi, dị ứng lông rồi mới giao bé hợp nếp nhà. Nhà có người dị ứng lông thì chưa giao.',
    'Bé lưu trú: mỗi ngày đủ bữa theo thẻ chuồng, dắt đi dạo hoặc dọn khay cát, thuốc đúng nhãn; bé lạ thì vỗ về, gọi báo chủ khi bé mệt.',
    'Khách quen: đọc thẻ của bé trước khi làm; nhắc chủ lịch tiêm, tẩy giun đúng hạn — nhưng vẫn xem sổ tiêm thật khi bé ghé.',
]
ADOPTEES = [
    dict(id='dom', name='Đốm', species='dog', emoji='🐕', age='1 tuổi', note='Chó ta năng động, cần sân chạy nhảy mỗi ngày.',
         yard=True, alone=4, kids=True, cats=False, dogs=True),
    dict(id='may', name='Mây', species='cat', emoji='🐈', age='8 tuổi', note='Mèo lớn tuổi hiền lành, thích nằm cửa sổ.',
         yard=False, alone=10, kids=True, cats=True, dogs=False),
    dict(id='tom', name='Tôm', species='cat', emoji='🐈‍⬛', age='4 tháng', note='Mèo con nhút nhát, sợ tiếng ồn và tay trẻ nhỏ.',
         yard=False, alone=6, kids=False, cats=True, dogs=True),
    dict(id='bi', name='Bi', species='dog', emoji='🦮', age='5 tuổi', note='Chó điềm tĩnh, quen trẻ nhỏ, đi dạo ngắn là đủ.',
         yard=False, alone=6, kids=True, cats=True, dogs=True),
]
ADOPTEE_INDEX = {x['id']: x for x in ADOPTEES}

# ================================================================ care loop — regulars, boarding days, reminders, follow-up
# (docs/superpowers/specs/2026-09-29-pet-care-design.md)
TRUST_NAMES = ['Khách mới', 'Quen mặt', 'Quen tay', 'Thân thiết', 'Khách ruột', 'Như người nhà']
TRUST_MAX = len(TRUST_NAMES) - 1
TRUST_CALM = 3              # a pet that knows the shop starts this much calmer per trust level
FAV_AT = 2                  # trust from which the pet's favourite comfort works on the table
FAV_DROP = 30
GREET_PATIENCE = 8
VAX_CYCLE = 12              # game rule: game days between combined-booster reminders
WORM_CYCLE = 8              # game rule: game days between deworming reminders
REMIND_EARLY = 2            # a reminder may go out this many days before the due day …
REMIND_LATE = 2             # … and still counts as on time this many days after it
REMIND_TRUST = 3            # reminders build trust up to “thân thiết”; beyond that only good visits do
WORM_FIRST = (4, 9)         # the first deworming reminder, days after the first visit (seeded)
BOOK_MAX = 80
FOLLOW_AFTER = 2            # days after an adoption before the follow-up call
FOLLOW_KEEP = 3             # days the call waits before the rescue group calls instead
FOLLOW_MAX = 12
STAY_LOG = 3
MOOD_FLOOR, HEALTH_FLOOR = 25, 45     # a missed day never sinks a boarder below these
MOOD_WORDS = [(75, 'Vui vẻ'), (55, 'Ổn'), (40, 'Hơi buồn'), (0, 'Buồn bã')]
HEALTH_WORDS = [(80, 'Khỏe'), (60, 'Hơi mệt'), (0, 'Mệt')]
# What each pet loves most: kind (treat | toy | touch), text. Owners tell it after a good first visit.
FAV = {
    'Bông': ('treat', 'bánh quy phô mai'), 'Bơ': ('toy', 'quả bóng cao su kêu chít chít'), 'Lu': ('touch', 'được gãi sau tai'),
    'Mochi': ('toy', 'cần câu lông vũ'), 'Vện': ('touch', 'giọng nói trầm, thật chậm'), 'Mướp': ('touch', 'được vuốt dọc sống lưng'),
    'Xám': ('toy', 'chiếc khăn có mùi của chủ'), 'Mít': ('toy', 'con thú bông hình cà rốt'), 'Tia': ('toy', 'trò ném bóng'),
    'Mập': ('touch', 'được xoa bụng'), 'Bánh Mì': ('toy', 'cọng lông vũ'), 'Vàng': ('treat', 'bánh quy vị cá'),
    'Bắp': ('touch', 'được bế như em bé'), 'Sushi': ('toy', 'cái hộp giấy cũ'), 'Ổi': ('treat', 'bánh quy bí đỏ'),
    'Ki': ('touch', 'được chải lông bằng bàn chải mềm'), 'Mun': ('touch', 'nằm phơi nắng cạnh cửa sổ'), 'Mực': ('toy', 'khúc gỗ gặm'),
    'Khói': ('toy', 'quả bóng lục lạc'), 'Kem': ('touch', 'được nói chuyện nhỏ nhẹ'), 'Bánh Bao': ('toy', 'que cù lông'),
    'Sữa': ('touch', 'được gãi cằm'),
}
FAV_DEFAULT = ('touch', 'được gãi cằm')
# Standing prescriptions a boarder keeps taking while it stays (label = the vet's label; dose stays on the server).
STAY_MEDS = {'Mướp': dict(name='Thuốc hỗ trợ thận (đơn bác sĩ thú y)', label='Một viên mỗi sáng, trộn vào bữa ăn.', dose='one'),
             'Lu': dict(name='Viên bổ khớp (đơn bác sĩ thú y)', label='Nửa viên mỗi sáng, cho cùng bữa ăn.', dose='half')}
WARNS = dict(appetite=dict(emoji='🥺', label='Nhớ nhà, ăn ít', fix='Vỗ về, chơi với bé rồi mới cho ăn'),
             upset=dict(emoji='💩', label='Đi ngoài hơi lỏng', fix='Gọi báo chủ, theo dõi, cho uống đủ nước'),
             bored=dict(emoji='🌀', label='Bồn chồn, cào cửa chuồng', fix='Chơi với bé hoặc dắt đi dạo'))
STAY_DO = ('feed', 'walk', 'litter', 'play', 'med', 'call')
FOLLOW = {
    'dom': dict(q='Đốm gặm nát chân ghế lúc cả nhà đi vắng. Nhà mình phải làm sao?', options=[
        dict(id='run', label='Cho Đốm chạy nhảy nhiều hơn mỗi sáng, mua đồ gặm riêng, khen khi bé gặm đúng đồ', good=True,
             outcome='Một tuần sau, chân ghế còn nguyên. Đốm ngủ say sau mỗi buổi chạy.'),
        dict(id='balcony', label='Nhốt Đốm ngoài ban công khi đi vắng', good=None, outcome='Đỡ hỏng đồ, nhưng Đốm sủa suốt buổi, hàng xóm phàn nàn.'),
        dict(id='scold', label='Mắng thật to, xịt nước mỗi lần bắt gặp', good=False, outcome='Đốm sợ cả nhà, lén gặm nhiều hơn khi không ai thấy.')]),
    'may': dict(q='Mây trốn dưới gầm giường hai ngày rồi, ăn rất ít. Có sao không?', options=[
        dict(id='room', label='Để Mây một phòng yên tĩnh, đặt bát ăn, nước, khay cát gần chỗ trốn; đừng lôi bé ra', good=True,
             outcome='Ngày thứ tư, Mây tự ra nằm cửa sổ, dụi đầu vào tay chủ.'),
        dict(id='pate', label='Mua pate thơm dụ bé ra', good=None, outcome='Mây ăn pate nhưng vẫn giật mình mỗi khi có tiếng động.'),
        dict(id='hug', label='Kéo Mây ra ôm cho quen hơi người', good=False, outcome='Mây cào người rồi trốn kỹ hơn, bỏ ăn thêm một ngày.')]),
    'tom': dict(q='Tôm chạy loạn, cào rèm lúc nửa đêm. Cả nhà mất ngủ.', options=[
        dict(id='play', label='Chơi cần câu lông vũ mười lăm phút trước giờ ngủ, thêm trụ cào móng', good=True,
             outcome='Tôm chơi mệt rồi ngủ tới sáng. Rèm cửa được tha.'),
        dict(id='door', label='Đóng cửa phòng của Tôm ban đêm', good=None, outcome='Nhà yên hơn, nhưng Tôm kêu cửa gần sáng.'),
        dict(id='clip', label='Cắt móng thật sát cho hết cào', good=False, outcome='Móng chảy máu, Tôm sợ ai chạm vào chân.')]),
    'bi': dict(q='Bi hay đi vệ sinh trong nhà mấy hôm nay.', options=[
        dict(id='routine', label='Dắt Bi ra ngoài đúng giờ sau khi ăn, khen khi đi đúng chỗ, lau sạch mùi cũ', good=True,
             outcome='Sau năm ngày, Bi tự ra cửa đứng chờ tới giờ đi dạo.'),
        dict(id='pads', label='Lót tã khắp nhà cho dễ dọn', good=None, outcome='Dễ dọn hơn, nhưng Bi vẫn chưa biết đi đâu mới đúng.'),
        dict(id='nose', label='Dí mũi Bi vào chỗ bẩn cho nhớ', good=False, outcome='Bi sợ, lén đi vệ sinh sau ghế.')]),
}
BOOK_KEYS = ('name', 'species', 'breed', 'npc', 'visits', 'first', 'last', 'trust', 'mood', 'allergy', 'nails', 'kg', 'fav', 'told',
             'job', 'stars', 'vax_due', 'worm_due')
STAY_KEYS = ('pet', 'key', 'npc', 'own', 'mood', 'health', 'meals', 'chore', 'played', 'med', 'called', 'told', 'warn', 'nights', 'good', 'log')
FOLLOW_KEYS = ('id', 'pet', 'family', 'npc', 'day', 'due', 'state', 'pick')


def _v2rows(rows: list, notes: dict | None = None) -> list:
    """Everyday templates of the first generator, with text that no longer assumes who serves the customer."""
    out = []
    for r in rows:
        r = dict(r, case=None)
        if notes and r['name'] in notes:
            r['note'] = notes[r['name']]
        out.append(r)
    return out


GROOMS2 = _v2rows(GROOMS) + [
    dict(npc=7, name='Tia', species='dog', breed='Jack Russell', coat='short', kg_said=6, kg=6, months=18, mood_said='calm', mood='nervous',
         skin='ok', rx=False, ears='ok', nails='clear', matted=False, signs=[], services=['brush', 'bath', 'nails'], short_nails=False,
         no_treat=False, note='Tia lanh lắm, ở nhà nhảy qua hàng rào như chơi. Tắm thơm giúp chị nha!', min_day=2, case='escape', runner=True),
    dict(npc=8, name='Mập', species='dog', breed='Pug', coat='short', kg_said=8, kg=9, months=48, mood_said='calm', mood='calm',
         skin='sensitive', rx=False, ears='ok', nails='dark', matted=False, signs=[], services=['bath', 'nails'], short_nails=False,
         no_treat=False, note='Mập hay thở khò khè, trời nóng là mệt. Tắm sấy nhẹ nhàng giúp anh nha.', min_day=2, case='flat', flat=True),
    dict(npc=6, name='Bánh Mì', species='cat', breed='Mèo Ba Tư mặt tịt', coat='long', kg_said=4, kg=4, months=30, mood_said='calm',
         mood='nervous', skin='ok', rx=False, ears='ok', nails='clear', matted=True, signs=[], services=['brush', 'bath'], short_nails=False,
         no_treat=False, note='Bánh Mì mặt tịt, sấy xong hay thở phì phò. Nhờ tiệm nhẹ tay.', min_day=3, case='flat', flat=True),
]
BOARDS2 = _v2rows(BOARDS, {'Bơ': 'Em về quê 3 ngày. Tiêm đủ hết rồi mà, yên tâm!'}) + [
    dict(npc=9, name='Bắp', species='dog', breed='Poodle', kg_said=5, kg=5, months=30, mood_said='calm', mood='calm', vax='valid',
         signs=['fever'], nights=2, food_own=False, allergy=None, note='Bắp hơi mệt do đi xe đường xa thôi, không sao đâu. Gửi hai đêm nha.',
         min_day=2, case='hidden'),
    dict(npc=11, name='Sushi', species='cat', breed='Mèo Anh lông ngắn', kg_said=4, kg=4, months=40, mood_said='calm', mood='calm',
         vax='valid', signs=['fever'], nights=2, food_own=True, allergy=None, note='Sushi lười ăn chút xíu thôi, chắc nhớ nhà. Hạt của bé đây nha.',
         min_day=3, case='hidden'),
    dict(npc=1, name='Ổi', species='dog', breed='Corgi', kg_said=12, kg=12, months=30, mood_said='calm', mood='calm', vax='valid',
         vax_left=1, signs=[], nights=3, food_own=False, allergy=None, note='Ổi tiêm năm ngoái, sổ còn hạn mà. Gửi ba đêm nha!',
         min_day=3, case='vax_short'),
]
FEEDS2 = _v2rows(FEEDS, {'Sữa': 'Sữa đang ăn kiêng, đừng cho bánh thưởng nha.'}) + [
    dict(npc=3, name='Lu', species='dog', breed='Golden', kg=30, months=108, food='own', no_treat=True, signs=[],
         note='Lu mới mổ u hôm kia. Thuốc để trong túi; nếu Lu kêu đau thì cho cả viên cũng được.', min_day=2, case='med',
         med=dict(name='Thuốc kháng viêm giảm đau (đơn bác sĩ thú y)', label='Nửa viên mỗi sáng, cho cùng bữa ăn. Không tự tăng liều.'),
         dose='half'),
    dict(npc=2, name='Mướp', species='cat', breed='Mèo ta', kg=4, months=150, food='own', no_treat=False, signs=[],
         note='Mướp uống thuốc thận mỗi sáng. Bé khó uống lắm, bữa nào quên thì bù hai viên luôn cho đủ nha con.', min_day=3, case='med',
         med=dict(name='Thuốc hỗ trợ thận (đơn bác sĩ thú y)', label='Một viên mỗi sáng, trộn vào bữa ăn. Quên một liều thì bỏ qua, không uống bù.'),
         dose='one'),
]
FAMILIES = [
    dict(npc=10, family='Gia đình anh Tín', opening='Nhà mình muốn nhận nuôi một bé, tiệm tư vấn giúp nha! Tụi nhỏ mê chó lắm.',
         note='Nhà rộng lắm, bọn trẻ mê chó, chiều nào cũng muốn dắt đi chơi.', candidates=['dom', 'may', 'bi'], min_day=3,
         profile=dict(home='apartment', hours=8, kids=True, pets='none', allergy=False),
         say=dict(home='Căn hộ chung cư tầng 9, ba phòng ngủ, không có sân.', time='Hai vợ chồng đi làm từ 8 giờ tới 5 giờ chiều, tụi nhỏ đi học cả ngày.',
                  kids='Hai bé, một bé 4 tuổi, một bé 7 tuổi.', pets='Chưa nuôi con gì hết.', allergy='Không ai dị ứng lông.')),
    dict(npc=11, family='Chị Quyên', opening='Chị ở một mình, muốn có một bé làm bạn. Bé nào cũng được!',
         note='Chị thương mèo lắm, nhà có một bé mèo rồi.', candidates=['may', 'tom', 'bi'], min_day=3,
         profile=dict(home='apartment', hours=9, kids=False, pets='cat', allergy=False),
         say=dict(home='Căn hộ nhỏ, có ban công.', time='Chị đi làm từ 8 giờ sáng tới 5 giờ chiều, cuối tuần ở nhà.',
                  kids='Không có trẻ nhỏ.', pets='Có một bé mèo 3 tuổi, hơi khó tính.', allergy='Không ai dị ứng.')),
    dict(npc=12, family='Ông bà Sáu', opening='Ông bà già rồi, muốn có một đứa làm bạn đi bộ buổi sáng.',
         note='Nhà có vườn, có con chó già hiền khô.', candidates=['dom', 'tom', 'may'], min_day=3,
         profile=dict(home='yard', hours=2, kids=False, pets='dog', allergy=False),
         say=dict(home='Nhà mặt đất, có vườn rào kín.', time='Ông bà ở nhà cả ngày, đi chợ chừng hai tiếng.',
                  kids='Cuối tuần cháu nội 10 tuổi mới về.', pets='Có con chó ta 9 tuổi, hiền, không đuổi mèo.', allergy='Không ai dị ứng.')),
    dict(npc=4, family='Nhà bé Na', opening='Con xin nuôi thêm một bạn mèo nữa được không ạ? Mẹ con cho rồi đó!',
         note='Mẹ con cho nuôi rồi, nhà con ai cũng thương mèo.', candidates=['tom', 'may', 'bi'], min_day=3,
         profile=dict(home='apartment', hours=5, kids=False, pets='none', allergy=True),
         say=dict(home='Nhà phố nhỏ, không có sân.', time='Mẹ con làm ở nhà buổi chiều, vắng nhà chừng năm tiếng buổi sáng.',
                  kids='Nhà có con thôi, con 9 tuổi rồi.', pets='Chưa nuôi bé nào ạ.',
                  allergy='Bố con ôm mèo nhà bạn là hắt hơi, ngứa mắt suốt… nhưng bố nói chịu được mà!')),
]
TEMPLATES2 = dict(groom=GROOMS2, board=BOARDS2, feed=FEEDS2)


# ---------------------------------------------------------------- rules
def _r(v: float) -> int:
    return int(v + 0.5)


def _stage(species: str, months: int) -> str:
    if months < 12:
        return 'young'
    return 'senior' if months >= (96 if species == 'dog' else 120) else 'adult'


def _gpk(species: str, kg: int) -> int:
    return next(g for top, g in CHART[species] if kg <= top)


def _daily(species: str, kg: int, months: int) -> int:
    return _r(kg * _gpk(species, kg) * STAGE_PCT[_stage(species, months)] / 100)


def _portion(species: str, kg: int, months: int, meals: int) -> int:
    return _r(_daily(species, kg, months) / meals)


def _within(grams: int, target: int) -> bool:
    return abs(grams - target) * 100 <= TOL * target


def _tier(species: str, kg: int) -> str:
    if species == 'cat':
        return 'groom_cat'
    return 'groom_s' if kg <= 10 else 'groom_m' if kg <= 25 else 'groom_l'


def _age_text(months: int) -> str:
    return f'{months} tháng tuổi' if months < 12 else f'{months // 12} tuổi'


# ---------------------------------------------------------------- tasks
def _make_v1(day: int, slot: int, serial: int) -> dict:
    """First generator — kept word for word so saved tasks still validate."""
    rng = kit.rng(ID, day, slot)
    job = JOB_ORDER[(slot + (day - 1) * 2) % len(JOB_ORDER)]
    pool = [x for x in TEMPLATES[job] if x['min_day'] <= day]
    tpl = pool[((day - 1) * 3 + slot + rng.randrange(len(pool))) % len(pool)]
    return BUILD[job](day, slot, serial, tpl)


def _groom_state(tpl: dict) -> dict:
    stress = BASE_STRESS[tpl['mood']] + (10 if _stage(tpl['species'], tpl['months']) == 'senior' else 0)
    return dict(stress=stress, peak=stress, brush=False, flea=False, shampoo=None, temp=None, cond=False, rinse=None, rinse_s=0.0,
                dry=None, heat=None, dry_s=0.0, dry_pct=0, towels=False, nails=None, nick=False, stanched=False, ears=None,
                consent=False, muzzle=False, wrap=False, bites=0, stopped=False, residue=False, temp_bad=False, shampoo_bad=False,
                ears_hurt=False, slip=False, overdry=False, treats=0, cost=0)


def _groom_task(day, slot, serial, tpl):
    stage = _stage(tpl['species'], tpl['months'])
    needs = dict(name=tpl['name'], species=tpl['species'], breed=tpl['breed'], coat=tpl['coat'], kg_said=tpl['kg_said'], months=tpl['months'],
                 stage=stage, mood_said=tpl['mood_said'], services=list(tpl['services']), short_nails=tpl['short_nails'],
                 no_treat=tpl['no_treat'], rx=tpl['rx'], note=tpl['note'])
    hidden = dict(kg=tpl['kg'], mood=tpl['mood'], skin=tpl['skin'], ears=tpl['ears'], nails=tpl['nails'], matted=tpl['matted'], signs=list(tpl['signs']))
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Tắm & cắt tỉa · bé {tpl["name"]}',
                         f'Chào em, chị/anh gửi bé {tpl["name"]} làm đẹp nhé!' if tpl['npc'] != 4 else f'Cô chú ơi, bé {tpl["name"]} nhà con cần đi tắm ạ!',
                         job='groom', needs=needs, _x=hidden, g=_groom_state(tpl), report=[])


def _board_task(day, slot, serial, tpl):
    stage = _stage(tpl['species'], tpl['months'])
    needs = dict(name=tpl['name'], species=tpl['species'], breed=tpl['breed'], kg_said=tpl['kg_said'], months=tpl['months'], stage=stage,
                 mood_said=tpl['mood_said'], nights=tpl['nights'], food_own=tpl['food_own'], allergy=tpl['allergy'], note=tpl['note'])
    hidden = dict(kg=tpl['kg'], mood=tpl['mood'], vax=tpl['vax'], signs=list(tpl['signs']))
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Nhận lưu trú · bé {tpl["name"]}', f'Tiệm còn chỗ gửi bé {tpl["name"]} vài hôm không?',
                         job='board', needs=needs, _x=hidden, pen=None, plan=None, reason=None, flags=[])


def _feed_task(day, slot, serial, tpl):
    stage = _stage(tpl['species'], tpl['months'])
    needs = dict(name=tpl['name'], species=tpl['species'], breed=tpl['breed'], kg=tpl['kg'], months=tpl['months'], stage=stage,
                 meals=MEALS[stage], food=tpl['food'], no_treat=tpl['no_treat'], note=tpl['note'])
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Chăm bé lưu trú · {tpl["name"]}', f'Nhờ tiệm cho bé {tpl["name"]} ăn sáng và chăm giúp nhé.',
                         job='feed', needs=needs, _x=dict(signs=list(tpl['signs'])), pen=None, bound=False, bowl=None, fed=False,
                         walked=False, litter=False, treats=0, cost=0, report=[])


BUILD = dict(groom=_groom_task, board=_board_task, feed=_feed_task)
FIXED = ('job', 'needs', '_x', 'gen')


def today(day: int) -> dict:
    return kit.daily(ID, day, TODAY)


def _shown(case):
    return case if case in SHOWN_CASES else None


def _job2(day: int, slot: int) -> str:
    mod = today(day)['id']
    job = JOB_ORDER[(slot + (day - 1) * 2) % len(JOB_ORDER)]
    if day >= 3 and slot == 1 and mod == 'adopt':
        return 'adopt'
    if day >= 4 and slot == 3 and kit.rng(ID, 'adopt-slot', day).random() < 0.35:
        return 'adopt'
    if mod == 'holiday' and job == 'groom' and slot >= 2:
        return 'board'
    return job


def _special2(day: int, slot: int, job: str) -> bool:
    if job == 'adopt':
        return True
    has = any(x['case'] and x['min_day'] <= day for x in TEMPLATES2[job])
    return slot > 0 and has and kit.rng(ID, 'pick2', day, slot).random() < SPECIAL_P[kit.tier(day)]


def _pool2(day: int, job: str, special: bool) -> list:
    if job == 'adopt':
        pool = [x for x in FAMILIES if x['min_day'] <= day]
    else:
        pool = [x for x in TEMPLATES2[job] if x['min_day'] <= day and bool(x['case']) == special]
    kit.rng(ID, 'perm2', job, special, len(pool)).shuffle(pool)
    return pool


def _step2(pool: list) -> int:
    return next(x for x in (3, 2, 5, 7) if math.gcd(x, len(pool)) == 1)


def _pick2(day: int, slot: int, job: str) -> dict:
    """Days walk a shuffled pool in steps, so the same pet does not come twice in one day and every pet takes its turn."""
    special = _special2(day, slot, job)
    pool = _pool2(day, job, special)
    k = sum(1 for sl in range(slot) if _job2(day, sl) == job and _special2(day, sl, job) == special)
    return pool[((day - 1) * _step2(pool) + k) % len(pool)]


PLAN2_SLOTS = 12   # a day's first visits are planned together; later extra slots use the plain walk
_PLAN2: dict = {}


def _who2(x: dict) -> str:
    return x.get('name') or x.get('family') or ''


def _plan2(day: int) -> list:
    """Same walk, but a visit skips ahead past a pet or an owner who already came in today."""
    if day not in _PLAN2:
        out, npcs, pets, jobs, seen = [], set(), set(), set(), {}
        for slot in range(PLAN2_SLOTS):
            job = _job2(day, slot)
            special = _special2(day, slot, job)
            pool = _pool2(day, job, special)
            k = seen.get((job, special), 0)
            seen[(job, special)] = k + 1
            base = (day - 1) * _step2(pool) + k
            walk = [pool[(base + i) % len(pool)] for i in range(len(pool))]
            pick = (next((x for x in walk if x['npc'] not in npcs and _who2(x) not in pets), None)
                    or next((x for x in walk if _who2(x) not in pets), None)
                    or next((x for x in walk if (job, _who2(x)) not in jobs), None) or walk[0])
            out.append(pick)
            npcs.add(pick['npc'])
            pets.add(_who2(pick))
            jobs.add((job, _who2(pick)))
        _PLAN2[day] = out
    return _PLAN2[day]


def _groom_task2(day, slot, serial, tpl, mod):
    stage = _stage(tpl['species'], tpl['months'])
    matted = tpl['matted'] or (mod == 'shed' and tpl['coat'] == 'long')
    needs = dict(name=tpl['name'], species=tpl['species'], breed=tpl['breed'], coat=tpl['coat'], kg_said=tpl['kg_said'], months=tpl['months'],
                 stage=stage, mood_said=tpl['mood_said'], services=list(tpl['services']), short_nails=tpl['short_nails'],
                 no_treat=tpl['no_treat'], rx=tpl['rx'], note=tpl['note'], case=_shown(tpl['case']), flat=bool(tpl.get('flat')),
                 humid=mod == 'rain', today=mod)
    hidden = dict(kg=tpl['kg'], mood=tpl['mood'], skin=tpl['skin'], ears=tpl['ears'], nails=tpl['nails'], matted=matted,
                  signs=list(tpl['signs']), runner=bool(tpl.get('runner')), case=tpl['case'])
    g = _groom_state(tpl)
    g['stress'] = g['peak'] = min(60, g['stress'] + 3 * kit.tier(day))
    g.update(loop=False, bolt=False, bolts=0, grabbed=False, breath=False)
    opening = (f'Chào em, gửi bé {tpl["name"]} làm đẹp giúp nhé!' if tpl['npc'] != 4
               else f'Cô chú ơi, bé {tpl["name"]} nhà con cần đi tắm ạ!')
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Tắm & cắt tỉa · bé {tpl["name"]}', opening,
                         job='groom', needs=needs, _x=hidden, g=g, report=[], gen=GEN)


def _board_task2(day, slot, serial, tpl, mod):
    stage = _stage(tpl['species'], tpl['months'])
    needs = dict(name=tpl['name'], species=tpl['species'], breed=tpl['breed'], kg_said=tpl['kg_said'], months=tpl['months'], stage=stage,
                 mood_said=tpl['mood_said'], nights=tpl['nights'], food_own=tpl['food_own'], allergy=tpl['allergy'], note=tpl['note'],
                 case=_shown(tpl['case']), today=mod)
    hidden = dict(kg=tpl['kg'], mood=tpl['mood'], vax=tpl['vax'], signs=list(tpl['signs']), vax_left=tpl.get('vax_left'), case=tpl['case'])
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Nhận lưu trú · bé {tpl["name"]}', f'Tiệm còn chỗ gửi bé {tpl["name"]} vài hôm không?',
                         job='board', needs=needs, _x=hidden, pen=None, plan=None, reason=None, flags=[], gen=GEN)


def _feed_task2(day, slot, serial, tpl, mod):
    stage = _stage(tpl['species'], tpl['months'])
    needs = dict(name=tpl['name'], species=tpl['species'], breed=tpl['breed'], kg=tpl['kg'], months=tpl['months'], stage=stage,
                 meals=MEALS[stage], food=tpl['food'], no_treat=tpl['no_treat'], note=tpl['note'], case=_shown(tpl['case']),
                 med=dict(tpl['med']) if tpl.get('med') else None, today=mod)
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Chăm bé lưu trú · {tpl["name"]}', f'Nhờ tiệm cho bé {tpl["name"]} ăn sáng và chăm giúp nhé.',
                         job='feed', needs=needs, _x=dict(signs=list(tpl['signs']), dose=tpl.get('dose'), case=tpl['case']), pen=None,
                         bound=False, bowl=None, fed=False, walked=False, litter=False, treats=0, cost=0, report=[], med=None, gen=GEN)


def _adopt_task(day, slot, serial, tpl, mod):
    needs = dict(family=tpl['family'], note=tpl['note'], candidates=list(tpl['candidates']), case='adopt', today=mod)
    hidden = dict(profile=dict(tpl['profile']), say=dict(tpl['say']), case='adopt')
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Nhận nuôi · {tpl["family"]}', tpl['opening'],
                         job='adopt', needs=needs, _x=hidden, match=None, flags=[], gen=GEN)


BUILD2 = dict(groom=_groom_task2, board=_board_task2, feed=_feed_task2, adopt=_adopt_task)


def _make_v2(day: int, slot: int, serial: int) -> dict:
    job = _job2(day, slot)
    tpl = _plan2(day)[slot] if slot < PLAN2_SLOTS else _pick2(day, slot, job)
    return BUILD2[job](day, slot, serial, tpl, today(day)['id'])


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        return _make_v1(day, slot, serial)
    return _make_v2(day, slot, serial)


DATA_V2 = dict(sanitize_day=0, adopted=0, returned=0, bolts=0, fevers=0, meds=0, day_done=0, day_bolts=0, day_adopted=0)
DATA_V3 = dict(reminders=0, follows=0, stays_good=0)       # care-loop counters


def initial() -> dict:
    pens = {p['id']: None for p in PENS}
    pens['d3'] = _pet('Ki', 'dog', 32, 84, 2, 'Chú Sơn', 'own', 2, 240)
    pens['c1'] = _pet('Mun', 'cat', 4, 132, 3, 'Cô Hạnh', 'house', 2, 27)
    return _migrate(dict(pens=pens, admitted=0, refused=0, walks=0, nicks=0, referrals=0, departed=0, desk=kit.desk_initial(), **DATA_V2))


def _migrate(d: dict) -> dict:
    """Old saves gain the v0.5 counters, the desk book and the care loop (book, stays, follow-ups) — idempotent.
    Stays follow the pens: an occupied pen without a stay gets a neutral one, an empty pen loses its stay."""
    for k, v in {**DATA_V2, **DATA_V3}.items():
        d.setdefault(k, v)
    d.setdefault('desk', kit.desk_initial())
    d.setdefault('book', {})
    d.setdefault('stay', {})
    d.setdefault('follow', [])
    pens, stay = d.get('pens'), d['stay']
    if isinstance(pens, dict) and isinstance(stay, dict):
        for pid in list(stay):
            v = pens.get(pid)
            if not isinstance(v, dict) or not isinstance(stay[pid], dict) or stay[pid].get('pet') != v.get('pet'):
                del stay[pid]
        for pid, v in pens.items():
            if pid in PEN_INDEX and isinstance(v, dict) and pid not in stay:
                stay[pid] = _stay_new(v)
    return d


def _data(c: dict) -> dict:
    """Career data with the v0.5 counters, the desk book and the care loop (old saves get them on first touch)."""
    return _migrate(kit.data(c))


def _case(t: dict) -> str | None:
    return t['_x'].get('case') if t.get('gen') else None


def _band(stress: int) -> str:
    return next(b['id'] for b in MOOD_BANDS if stress <= b['top'])


def _cues(t: dict) -> list:
    """What the pet shows on the table right now — the stress number itself stays with the server."""
    g, n = t['g'], t['needs']
    rows = CUES[n['species']][_band(g['stress'])]
    pick = kit.rng(ID, 'cue', t['id'], g['stress'] // 10).sample(rows, 2)
    if t['_x'].get('runner') and g['stress'] >= 45 and not g['loop'] and not g['stopped']:
        pick = [RUNNER_CUE] + pick[:1]
    return pick


def _mood_line(t: dict) -> str:
    return ', '.join(c[0].lower() + c[1:] for c in _cues(t))


def _fits(a: dict, pr: dict) -> bool:
    """Adoption rule: the rescue suits the home, the hours alone, small children, the pets already there; no fur allergy."""
    return ((not a['yard'] or pr['home'] == 'yard') and pr['hours'] <= a['alone'] and (a['kids'] or not pr['kids'])
            and (pr['pets'] != 'cat' or a['cats']) and (pr['pets'] != 'dog' or a['dogs']) and not pr['allergy'])


def _fit_list(t: dict) -> list:
    return [a for a in t['needs']['candidates'] if _fits(ADOPTEE_INDEX[a], t['_x']['profile'])]


def _vax_until(t: dict):
    left = t['_x'].get('vax_left')
    return None if left is None else t['day'] + left


def _vax_short(c: dict, t: dict) -> bool:
    until = _vax_until(t)
    return until is not None and until < c['day'] + t['needs']['nights']


def _pet(name, species, kg, months, until, owner, food, meals, grams, task=None) -> dict:
    return dict(pet=name, species=species, kg=kg, months=months, until=until, owner=owner, food=food, meals=meals, grams=grams, task=task)


def _npc_index(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


# ---------------------------------------------------------------- care loop helpers
def _key(npc: int, name: str) -> str:
    """One pet of one owner: the same Bông of Chị Ngân comes back for a bath, a stay or a feeding round."""
    return f'{npc}:{name}'


def _task_key(t: dict) -> str:
    return _key(_npc_index(t), t['needs']['name'])


def _owner_npc(owner) -> int:
    return next((i for i, p in enumerate(PEOPLE) if p[0] == owner), -1)


def _owner_name(npc: int) -> str:
    return PEOPLE[npc][0] if 0 <= npc < len(PEOPLE) else 'Chủ bé'


def _word(words: list, v: int) -> str:
    return next(w for top, w in words if v >= top)


def _fav(name: str) -> tuple:
    return FAV.get(name, FAV_DEFAULT)


def _stay_new(v: dict, own: bool = False, mood: int = 70, warn=None) -> dict:
    npc = _owner_npc(v.get('owner'))
    return dict(pet=v.get('pet'), key=_key(npc, v.get('pet')), npc=npc, own=own, mood=mood, health=90, meals=0, chore=False, played=False,
                med=None, called=False, told=False, warn=warn, nights=0, good=0, log=[])


def _roll(key: str, day: int, first: bool, trust: int):
    """Today's issue for a boarder, from the seed: homesick on the first night unless the pet knows the shop."""
    r = kit.rng(ID, 'stay', key, day)
    if first and trust < FAV_AT:
        return 'appetite' if r.random() < 0.6 else None
    return r.choice(('upset', 'bored', 'appetite')) if r.random() < 0.25 else None


def _warn_ok(st: dict) -> bool:
    w = st['warn']
    return (w is None or (w == 'appetite' and st['played']) or (w == 'upset' and st['called'])
            or (w == 'bored' and (st['played'] or st['chore'])))


def _stay_todo(v: dict, st: dict) -> int:
    rx = STAY_MEDS.get(v['pet'])
    return (max(0, v['meals'] - st['meals']) + (not st['chore']) + bool(rx and st['med'] is None)
            + (0 if _warn_ok(st) else 1))


def _owner(t: dict) -> str:
    return PEOPLE[_npc_index(t)][0]


def _pen_ok(c: dict, pid: str, species: str, kg: int) -> bool:
    p = PEN_INDEX[pid]
    return p['unlock'] <= kit.level(c) and p['zone'] == species and kg <= p['max_kg'] and kit.data(c)['pens'][pid] is None


def _bind_feed(c: dict, t: dict) -> None:
    """Find the pen of this boarder (pens are shared state); the night shift may have admitted it."""
    pens = kit.data(c)['pens']
    n = t['needs']
    pick = next((pid for pid, v in pens.items() if v and v['pet'] == n['name'] and not v['task']), None)
    if pick is None:
        pick = next((p['id'] for p in PENS if _pen_ok(c, p['id'], n['species'], n['kg'])), None)
        if pick:
            portion = _portion(n['species'], n['kg'], n['months'], n['meals'])
            pens[pick] = _pet(n['name'], n['species'], n['kg'], n['months'], c['day'] + 1, _owner(t), n['food'], n['meals'], portion)
    if pick:
        pens[pick]['task'] = t['id']
    t['pen'] = pick
    t['bound'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['job'] == 'feed' and not t['bound']:
        _bind_feed(c, t)
        _data(c)                                   # a pen filled for this round gets its stay card
    if t.get('gen') and t['status'] == 'new' and t.get('patience') == 100:
        # Later days and the holiday rush make owners a little less patient.
        t['patience'] = max(60, 100 - 4 * kit.tier(t['day']) - (8 if t['needs'].get('today') == 'holiday' else 0))
    if t.get('gen') and t['job'] != 'adopt' and 'regular' not in t:
        # A pet the shop has met before: the card remembers it, and it starts calmer on the table.
        rec = _data(c)['book'].get(_task_key(t)) if t['status'] == 'new' else None
        t['regular'] = rec['trust'] if rec else None
        if rec and t['job'] == 'groom' and rec['trust']:
            g = t['g']
            g['stress'] = g['peak'] = max(0, g['stress'] - TRUST_CALM * rec['trust'])


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    left = []
    for pid, v in d['pens'].items():
        if v and not v['task'] and v['until'] <= c['day']:
            st = d['stay'].pop(pid, None)
            left.append(f'{v["pet"]} ({v["owner"]}' + (f', {_word(MOOD_WORDS, st["mood"]).lower()})' if st else ')'))
            if st:
                _pickup(s, c, v, st)
            d['pens'][pid] = None
            d['departed'] += 1
    if left:
        kit.log(s, c, 'pet_care', 'Sáng nay chủ đã đón: ' + ', '.join(left) + '. Chuồng đã trống, nhớ khử khuẩn.')
    for f in d['follow']:
        if f['state'] == 'open' and c['day'] > f['due'] + FOLLOW_KEEP:
            f['state'] = 'lapsed'
            kit.log(s, c, 'pet_care', f'Chị Mây đã gọi hỏi thăm bé {ADOPTEE_INDEX[f["pet"]]["name"]} ở nhà {f["family"]} thay tiệm.')
    for t in c['tasks']:
        if t['career'] == ID and t['status'] not in ('completed', 'cancelled', 'referred'):
            on_task(s, c, t)
    d = _data(c)
    mod = today(c['day'])
    if c['day'] >= 2:
        kit.log(s, c, 'pet_care', f'{mod["emoji"]} Hôm nay: {mod["title"]}. {mod["text"]}')
    kit.desk_start(s, c, ID, d['desk'], DESK, mod['id'])


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    staying = [v['pet'] for v in d['pens'].values() if v]
    if staying:
        kit.log(s, c, 'pet_care', 'Tối nay ở lại tiệm: ' + ', '.join(staying) + '. Camera chuồng đã bật cho chủ xem.')
    lines = [f'Hôm nay xong {d["day_done"]} việc.']
    nights = [_night(c, pid, st) for pid, st in d['stay'].items() if d['pens'].get(pid)]
    if nights:
        lines.append('Khu lưu trú: ' + ' · '.join(nights) + '.')
    if d['day_bolts']:
        lines.append(f'Bé nhảy khỏi bàn: {d["day_bolts"]} lần — nhớ đeo vòng giữ cho bé hay trốn.')
    if d['day_adopted']:
        lines.append(f'Bé tìm được nhà mới hôm nay: {d["day_adopted"]}.')
    note = kit.desk_close(s, c, ID, d['desk'], DESK, _desk_hook)
    if note:
        lines.append(note)
    nxt = today(c['day'] + 1)
    lines.append(f'Dự báo ngày mai: {nxt["emoji"]} {nxt["title"]} — {nxt["text"]}')
    d['day_done'] = d['day_bolts'] = d['day_adopted'] = 0
    return dict(staying=staying, free=[PEN_INDEX[k]['name'] for k, v in d['pens'].items() if v is None and PEN_INDEX[k]['unlock'] <= kit.level(c)],
                lines=lines)


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['job'] == 'adopt':
        names = ', '.join(f'{ADOPTEE_INDEX[a]["name"]} ({ADOPTEE_INDEX[a]["age"]})' for a in n['candidates'])
        return f'{n["family"]} muốn nhận nuôi. Các bé đang chờ nhà: {names}. Họ kể: “{n["note"]}”'
    pet = f'{n["name"]} ({SPECIES_NAMES[n["species"]].lower()} {n["breed"]}, {_age_text(n["months"])}'
    if t['job'] == 'groom':
        mood = dict(calm='bé hiền', nervous='bé hơi nhát', bitey='bé hay cắn/cào')[n['mood_said']]
        text = f'Phiếu nhận: {pet}, chủ khai khoảng {n["kg_said"]} kg; {mood}). Dịch vụ: ' + ', '.join(SERVICE_NAMES[x].lower() for x in n['services']) + '.'
        if n['rx']:
            text += ' Có đơn bác sĩ thú y kê sữa tắm trị liệu, chủ gửi kèm chai.'
        if n['no_treat']:
            text += ' Không cho ăn bánh thưởng.'
        return text + f' Chủ dặn: “{n["note"]}”'
    if t['job'] == 'board':
        food = 'chủ gửi kèm thức ăn' if n['food_own'] else 'ăn hạt của tiệm'
        allergy = f' Dị ứng {ALLERGY_NAMES[n["allergy"]]}.' if n['allergy'] else ''
        return (f'Gửi lưu trú: {pet}, chủ khai khoảng {n["kg_said"]} kg), {n["nights"]} đêm, {food}.{allergy} '
                f'Chủ nói đã tiêm phòng đầy đủ. “{n["note"]}”')
    food = 'thức ăn chủ gửi' if n['food'] == 'own' else 'hạt của tiệm'
    med = f' Thuốc theo đơn: {n["med"]["name"]} — nhãn ghi “{n["med"]["label"]}”' if n.get('med') else ''
    return (f'Thẻ lưu trú: {pet}), cân lúc nhận {n["kg"]} kg, {STAGE_NAMES[n["stage"]].lower()}, {n["meals"]} bữa/ngày, {food}.'
            + (' Không bánh thưởng.' if n['no_treat'] else '') + med + f' Chủ nhắn: “{n["note"]}”')


# ---------------------------------------------------------------- dispatch
def _task(s: dict, c: dict, p: dict) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm thú cưng.')
    kit.need(t['known'], 'Đọc phiếu của chủ trước đã nhé (bấm “Nhận phiếu”).')
    if not t.get('bound', True):
        on_task(s, c, t)
    return t


ACTION_JOBS = {
    'pc_inspect': ('groom', 'board', 'feed', 'adopt'), 'pc_report': ('groom', 'feed'), 'pc_handover': ('groom', 'feed'),
    'pc_loop': ('groom',), 'pc_catch': ('groom',), 'pc_med': ('feed',), 'pc_match': ('adopt',),
    'pc_consent': ('groom',), 'pc_muzzle': ('groom',), 'pc_calm': ('groom',), 'pc_brush': ('groom',), 'pc_bath': ('groom',),
    'pc_rinse': ('groom',), 'pc_dry': ('groom',), 'pc_nails': ('groom',), 'pc_styptic': ('groom',), 'pc_ears': ('groom',), 'pc_stop': ('groom',),
    'pc_pen': ('board',), 'pc_plan': ('board',), 'pc_admit': ('board',), 'pc_refuse': ('board',),
    'pc_feed': ('feed',), 'pc_walk': ('feed',), 'pc_litter': ('feed',), 'pc_treat': ('feed',),
    'pc_greet': ('groom', 'board', 'feed'),
}
CARE_ACTIONS = ('pc_stay', 'pc_remind', 'pc_follow')     # the kennel, the phone: no ticket needed


DESK_FREE = ('pc_rinse', 'pc_dry')     # a running tap or dryer can always be turned off


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'pc_desk':
        return kit.desk_choose(s, c, ID, d['desk'], DESK, p.get('option'), _desk_hook)
    if not (name in DESK_FREE and p.get('mode') == 'stop'):
        kit.desk_block(d['desk'], 'Có chuyện ở quầy cần quyết trước (vòi nước, máy sấy đang chạy vẫn tắt được).')
    out = _handle(s, c, name, p)
    had = d['desk']['ev']
    kit.desk_tick(s, c, ID, d['desk'], DESK, today(c['day'])['id'])
    ev = d['desk']['ev']
    if ev is not None and had is None:
        x = kit.desk_script(DESK, ev['script'])
        out = dict(out, message=(out.get('message') or '') + f' 🔔 {x["emoji"]} {x["title"]} — ra quầy quyết giúp nhé.', surprise=True)
    return out


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    if key == 'sanitize':
        d['sanitize_day'] = c['day']
        return 'Chuồng và bàn tắm đã khử khuẩn, ký sổ.'
    if key == 'returned':
        d['returned'] += int(v)
        return None
    if key == 'inspect':
        if d['sanitize_day'] == c['day']:
            c['xp'] += 10
            return 'Sổ khử khuẩn hôm nay đủ chữ ký — đạt.'
        fine = min(15, c['money'])
        if fine:
            kit.money(s, c, -fine, 'Phạt vệ sinh chuồng trại', None, 'event_cost')
        return f'Hôm nay chưa khử khuẩn chuồng — phạt {fine} xu, hẹn kiểm lại.'
    return None


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'pc_sanitize':
        kit.need(d['sanitize_day'] != c['day'], 'Hôm nay đã khử khuẩn chuồng rồi.')
        d['sanitize_day'] = c['day']
        kit.metric(c, 'pc_sanitized')
        return dict(message=f'Đã rửa chuồng, ngâm lược kéo, phun khử khuẩn bàn tắm; ký sổ vệ sinh ngày {c["day"]}.')
    if name == 'pc_stay':
        return _stay_act(s, c, p)
    if name == 'pc_remind':
        return _remind(c, p)
    if name == 'pc_follow':
        return _follow(s, c, p)
    jobs = ACTION_JOBS.get(name)
    if jobs is None:
        raise kit.eng().GameError('Thao tác tiệm thú cưng không hợp lệ.')
    t = _task(s, c, p)
    kit.need(t['job'] in jobs, f'Thao tác này không dùng cho việc “{JOB_NAMES[t["job"]]}”.')
    if name == 'pc_inspect':
        return _inspect(s, c, t, p)
    if name == 'pc_report':
        return _report(t, p)
    if name == 'pc_greet':
        return _greet(c, t)
    if name == 'pc_handover':
        return _groom_handover(s, c, t, p) if t['job'] == 'groom' else _feed_handover(s, c, t, p)
    out = dict(groom=_groom, board=_board, feed=_feed, adopt=_adopt)[t['job']](s, c, t, name, p)
    if name in BOLT_STEPS and not out.get('refused') and p.get('how') != 'skip':
        extra = _maybe_bolt(c, t, name)
        if extra:
            out = dict(out, message=out['message'] + extra)
    return out


def _maybe_bolt(c: dict, t: dict, step: str) -> str:
    """A pet on the edge may leap off the table (runners early, any pet from day 6) — unless it wears the table loop."""
    g, x = t['g'], t['_x']
    if not t.get('gen') or g['loop'] or g['bolt'] or g['stopped'] or t['status'] in ('completed', 'referred'):
        return ''
    kind = 'runner' if x.get('runner') else 'other'
    if kind == 'other' and kit.tier(t['day']) < 2:
        return ''
    if g['stress'] < BOLT_AT[kind] or kit.rng(ID, 'bolt', t['id'], step, g['bolts']).random() >= BOLT_P[kind]:
        return ''
    g['bolt'] = True
    return ' ⚠️ Bé giật mạnh, nhảy khỏi bàn và lao về phía cửa!'


# ---------------------------------------------------------------- inspection
def _found(t: dict, part: str) -> str:
    n, x = t['needs'], t['_x']
    if t['job'] == 'adopt':
        return x['say'].get(part, '')
    signs = x.get('signs', [])
    cat = n['species'] == 'cat'
    if part == 'temp':
        if 'fever' in signs:
            return 'Nhiệt kế: 39,8°C — bé đang sốt (chó mèo bình thường 38–39,2°C).'
        return 'Nhiệt kế: 38,6°C — bình thường.'
    if part == 'vaccine' and x['vax'] == 'valid' and x.get('vax_left') is not None:
        return f'Sổ tiêm: mũi dại còn hạn; mũi phối hợp hết hạn cuối ngày {t["day"] + x["vax_left"]}.'
    if part == 'vaccine':
        return {'valid': 'Sổ tiêm: mũi dại và mũi phối hợp còn hạn, có dấu phòng khám.',
                'expired': 'Sổ tiêm: mũi phối hợp đã hết hạn 4 tháng, chưa tiêm nhắc lại.',
                'none': 'Chủ không mang sổ tiêm, cũng không có giấy xác nhận nào.'}[x['vax']]
    if part == 'scale':
        kg = x.get('kg', n.get('kg'))
        said = n.get('kg_said')
        return f'Cân: {kg} kg' + (f' (chủ khai {said} kg).' if said is not None and said != kg else ', đúng như chủ khai.')
    if part == 'coat':
        text = 'Lông rối cục sau tai và dưới nách.' if x['matted'] else 'Lông không rối.'
        return text + (' Có bọ chét ở gốc đuôi!' if 'fleas' in signs else ' Không thấy bọ chét.')
    if part == 'skin':
        if n.get('rx'):
            return 'Vùng da lưng đang điều trị nấm theo đơn bác sĩ thú y.'
        return 'Da ửng đỏ, dễ kích ứng.' if x['skin'] == 'sensitive' else 'Da hồng, khỏe.'
    if part == 'ears':
        if 'ears' in signs:
            return 'Tai đỏ, có mùi hôi, bé lắc đầu và kêu khi chạm vào.'
        return 'Tai có ít ráy nâu, không đỏ.' if x['ears'] == 'dirty' else 'Tai sạch.'
    if part == 'nails':
        return 'Móng đen, không nhìn thấy phần tủy.' if x['nails'] == 'dark' else 'Móng trắng, thấy rõ phần tủy hồng bên trong.'
    if part == 'body':
        if 'cough' in signs:
            return 'Bé ho khan vài tiếng, mũi chảy nước trong.'
        if 'fever' in signs:
            return 'Mũi khô, tai và bụng nóng hầm hập; bé nằm lì không muốn đứng.'
        return 'Sờ thấy một cục u nhỏ bằng hạt đậu dưới da ngực.' if 'lump' in signs else 'Không sờ thấy gì bất thường.'
    if part == 'gait':
        return 'Bé đi khập khiễng chân sau trái.' if 'limp' in signs else 'Đi lại bình thường.'
    if part == 'mood':
        return {'calm': 'Bé hiền, dụi đầu vào tay bạn.' if cat else 'Bé hiền, vẫy đuôi, cho sờ cả chân.',
                'nervous': 'Bé run, nép sát vào chủ, tim đập nhanh.',
                'bitey': 'Bé xù lông, cào khi bị giữ chân.' if cat else 'Bé gầm gừ, đớp khi bị chạm vào chân.',
                'dog_aggressive': 'Hiền với người, nhưng thấy chó khác là sủa dữ và lao tới.'}[x['mood']] + (
                    ' Bé cứ liếc về phía cửa, chân sau co lại như chực nhảy.' if x.get('runner') else '')
    if part == 'bowl':
        return 'Bát tối qua còn nguyên, bé không đụng miếng nào.' if 'appetite' in signs else 'Bát tối qua sạch trơn.'
    if part == 'energy':
        return 'Bé nằm lì, mắt lờ đờ, không buồn đứng dậy.' if 'lethargy' in signs else 'Bé nhanh nhẹn, mừng rỡ khi thấy bạn.'
    return ''


def _inspect(s: dict, c: dict, t: dict, p: dict) -> dict:
    part = kit.one_of(p.get('part'), JOB_PARTS[t['job']], 'Không kiểm được phần này trong việc hiện tại.')
    kit.need(part not in t['inspected'], 'Đã kiểm phần này rồi.')
    t['inspected'].append(part)
    kit.start_work(t)
    kit.metric(c, 'pc_checks')
    return dict(message=_found(t, part))


def _known_bitey(t: dict) -> bool:
    return t['needs']['mood_said'] == 'bitey' or ('mood' in t['inspected'] and t['_x']['mood'] == 'bitey')


def _kg_known(t: dict) -> int:
    n = t['needs']
    return t['_x']['kg'] if 'scale' in t['inspected'] else n['kg_said']


# ---------------------------------------------------------------- grooming
def _add_stress(t: dict, base: int) -> None:
    g = t['g']
    if base > 0 and t.get('gen') and t['needs'].get('today') == 'heat':
        base += 5
    inc = _r(base * STRESS_MULT[t['_x']['mood']])
    g['stress'] = min(100, g['stress'] + inc)
    g['peak'] = max(g['peak'], g['stress'])


def _calm_enough(t: dict) -> None:
    g = t['g']
    if t.get('gen'):
        kit.need(g['stress'] < STRESS_STOP, f'Bé đang hoảng: {_mood_line(t)}. Dỗ dành, cho nghỉ, hoặc dừng dịch vụ.')
    kit.need(g['stress'] < STRESS_STOP, f'Bé đang quá căng thẳng (stress {g["stress"]}). Dỗ dành, cho nghỉ, hoặc dừng dịch vụ.')


def _no_timer(g: dict) -> None:
    kit.need(g['rinse'] is None, 'Vòi sen đang chạy — khóa vòi trước.')
    kit.need(g['dry'] is None, 'Máy sấy đang chạy — tắt máy trước.')


def _wet(t: dict) -> bool:
    g = t['g']
    return g['shampoo'] is not None and g['dry_pct'] < 100 and not g['stopped']


def _shampoo_verdict(n: dict, x: dict, sid: str) -> tuple[str, str]:
    if sid == 'medicated':
        return ('ok', '') if n['rx'] else ('refuse', 'Không có đơn của bác sĩ thú y thì không dùng sữa tắm trị liệu cho bé.')
    if n['rx']:
        return 'bad', 'Bác sĩ thú y đã kê sữa tắm trị liệu — phải dùng đúng đơn.'
    if n['species'] == 'cat':
        return ('bad', 'Sữa tắm cho chó có thể gây hại cho mèo.') if sid == 'normal' else ('ok', '')
    if n['stage'] == 'young':
        return ('bad', 'Sữa tắm thường quá mạnh, cay mắt cún con.') if sid == 'normal' else ('ok', '')
    if x['skin'] == 'sensitive' and sid == 'normal':
        return 'bad', 'Da bé nhạy cảm, sữa tắm thường làm nổi mẩn.'
    return 'ok', ''


def _groom(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n, x, g = t['needs'], t['_x'], t['g']
    services = n['services']
    kit.need(not g.get('bolt') or name == 'pc_catch' or (name in DESK_FREE and p.get('mode') == 'stop'),
             'Bé đang chạy khỏi bàn — đưa bé về an toàn trước đã!')
    if name in ('pc_loop', 'pc_catch'):
        kit.need(t.get('gen'), 'Phiếu này làm theo quy trình cũ.')
    kit.need(not g['stopped'] or name in ('pc_styptic',), 'Đã dừng dịch vụ. Báo lại cho chủ và bàn giao bé.')
    cat = n['species'] == 'cat'
    if name == 'pc_loop':
        kit.need(not g['loop'], 'Bé đã đeo vòng giữ rồi.')
        g['loop'] = True
        kit.start_work(t)
        _add_stress(t, 5)
        return dict(message='Đeo vòng giữ cổ mềm nối vào giá trên bàn: bé đứng thoải mái nhưng không nhảy xuống được. Không rời bé nửa bước.'
                    + _stress_note(g, t))
    if name == 'pc_catch':
        kit.need(g['bolt'], 'Bé vẫn đang ở trên bàn.')
        how = kit.one_of(p.get('how'), CATCH_IDS, 'Chọn cách đưa bé về.')
        if how == 'lure':
            kit.need(kit.stock(c, 'treat') >= 1, 'Hết bánh thưởng trong túi — chọn cách khác.')
        g['bolt'] = False
        g['bolts'] += 1
        _data(c)['bolts'] += 1
        _data(c)['day_bolts'] += 1
        kit.metric(c, 'pc_escapes')
        if how == 'corner':
            g['stress'] = max(0, g['stress'] - 10)
            if 'patience' in t:
                t['patience'] = max(25, t['patience'] - CORNER_WAIT)
            return dict(message='Bạn khép cửa phòng tắm, ngồi thấp xuống, gọi tên bé thật nhỏ. Một lúc sau bé tự rón rén quay lại, dụi vào tay bạn.'
                        + ' Nhớ đeo vòng giữ trước khi làm tiếp.')
        if how == 'lure':
            g['cost'] += kit.take(c, 'treat', 1)
            g['treats'] += 1
            g['stress'] = max(0, g['stress'] - 15)
            msg = 'Bạn lắc túi bánh: bé quay ngoắt lại, ngồi ngoan chờ phần.'
            if n['no_treat']:
                t['mistakes'] += 1
                msg += ' Nhưng chủ đã dặn không cho bánh thưởng!'
            return dict(message=msg)
        t['mistakes'] += 1
        g['grabbed'] = True
        _add_stress(t, 20)
        msg = 'Bạn lao tới chụp: bé hoảng, giãy tung, trượt chân va vào tủ.'
        if x['mood'] == 'bitey':
            g['bites'] += 1
            msg += ' Bé quay lại cắn trúng tay bạn!'
        return dict(message=msg + _stress_note(g, t))
    if name == 'pc_consent':
        kit.need(not cat, 'Không dùng rọ mõm cho mèo, nên không cần hỏi.')
        kit.need(_known_bitey(t), 'Bé chưa có dấu hiệu cắn — không cần rọ mõm.')
        kit.need(not g['consent'], 'Chủ đã đồng ý rồi.')
        g['consent'] = True
        kit.start_work(t)
        return dict(message=f'{_owner(t)} đồng ý cho đeo rọ mõm mềm khi cắt móng, miễn là bé vẫn thở và uống nước được.')
    if name == 'pc_muzzle':
        if cat:
            t['mistakes'] += 1
            return dict(message='Không bao giờ rọ mõm mèo: mèo hoảng sẽ thở bằng miệng, dễ ngạt. Quấn khăn nhẹ nhàng thay thế.', refused=True)
        kit.need(_known_bitey(t), 'Bé không có dấu hiệu cắn, không đeo rọ mõm.')
        kit.need(g['consent'], 'Hỏi ý chủ trước khi đeo rọ mõm cho bé.')
        kit.need(not g['muzzle'], 'Bé đã đeo rọ mõm.')
        g['muzzle'] = True
        _add_stress(t, 5)
        return dict(message='Đeo rọ mõm mềm vừa khít, vẫn đủ chỗ thở hổn hển. Chỉ đeo trong lúc làm, tháo ngay khi xong.')
    if name == 'pc_calm' and p.get('how') == 'fav':
        return _calm_fav(c, t)
    if name == 'pc_calm':
        how = kit.one_of(p.get('how'), CALM_INDEX, 'Cách dỗ bé không hợp lệ.')
        kit.start_work(t)
        extra = ''
        if how == 'wrap':
            kit.need(cat, 'Quấn khăn là cách giữ mèo; với chó hãy nói nhỏ hoặc cho nghỉ.')
            g['cost'] += kit.take(c, 'towel', 1)
            g['wrap'] = True
            extra = ' Bé nằm gọn như cuộn bánh, chân được giữ nhẹ.'
        elif how == 'treat':
            g['cost'] += kit.take(c, 'treat', 1)
            g['treats'] += 1
            if n['no_treat']:
                t['mistakes'] += 1
                extra = ' Nhưng chủ đã dặn không cho bánh thưởng!'
        elif how == 'break':
            _no_timer(g)
            extra = ' Cho bé xuống bàn, uống nước, đi lại vài vòng.'
        before = g['stress']
        g['stress'] = max(0, g['stress'] - CALM_INDEX[how]['drop'])
        if t.get('gen'):
            return dict(message=f'{CALM_INDEX[how]["name"]}: bé dịu lại — {_mood_line(t)}.' + extra)
        return dict(message=f'{CALM_INDEX[how]["name"]}: stress {before} → {g["stress"]}.' + extra)
    if name == 'pc_stop':
        kit.confirm(p, 'Xác nhận dừng dịch vụ giữa chừng.')
        _no_timer(g)
        g['stopped'] = True
        kit.start_work(t)
        return dict(message='Đã dừng. Lau khô, vuốt ve cho bé bình tĩnh. Báo thật với chủ và chỉ tính phần đã làm.')
    if name == 'pc_styptic':
        kit.need(g['nick'] and not g['stanched'], 'Không có móng nào chảy máu.')
        g['cost'] += kit.take(c, 'styptic', 1)
        g['stanched'] = True
        return dict(message='Rắc bột cầm máu, ấn nhẹ 30 giây. Máu đã cầm. Nhớ nói thật với chủ lúc trả bé.')
    if name == 'pc_brush':
        tool = kit.one_of(p.get('tool'), ('brush', 'flea'), 'Chọn lược chải hoặc lược bọ chét.')
        kit.need('brush' in services, 'Chủ không đặt chải lông.')
        kit.need(g['shampoo'] is None, 'Chải trước khi tắm: lông ướt chải dễ đứt, rối càng chặt.')
        _calm_enough(t)
        kit.start_work(t)
        if tool == 'flea':
            kit.need(not g['flea'], 'Đã chải bọ chét rồi.')
            g['flea'] = True
            _add_stress(t, STEP_STRESS['flea'])
            if 'fleas' in x['signs']:
                if 'coat' not in t['inspected']:
                    t['inspected'].append('coat')
                return dict(message='Lược bọ chét bắt được vài con ở gốc đuôi. Nhúng lược vào nước xà phòng. Nhớ báo chủ hỏi bác sĩ thú y thuốc trị.')
            return dict(message='Chải lược bọ chét: không thấy con nào.')
        kit.need(not g['brush'], 'Đã chải gỡ rối rồi.')
        g['brush'] = True
        _add_stress(t, STEP_STRESS['brush'] + (15 if x['matted'] else 0))
        msg = 'Gỡ từng cục rối bằng tay trước, rồi chải theo chiều lông.' if x['matted'] else 'Chải lông mượt, rụng lông chết.'
        return dict(message=msg + _stress_note(g, t))
    if name == 'pc_bath':
        kit.need('bath' in services, 'Chủ không đặt tắm.')
        kit.need(g['shampoo'] is None, 'Đã tắm rồi.')
        _calm_enough(t)
        sid = kit.one_of(p.get('shampoo'), SHAMPOO_INDEX, 'Chọn loại sữa tắm.')
        temp = kit.integer(p.get('temp'), 30, 45)
        kit.need(type(p.get('cond', False)) is bool, 'Lựa chọn dầu xả không hợp lệ.')
        cond = p.get('cond', False)
        kit.start_work(t)
        if temp >= TEMP['burn']:
            t['mistakes'] += 1
            t['scald'] = True          # the owner sees the red skin at pick-up (a slip at the hand-off)
            return dict(message=f'Nước {temp}°C làm bỏng da bé! Thử nước bằng cổ tay, pha lại trong khoảng {TEMP["low"]}–{TEMP["high"]}°C.', refused=True)
        verdict, why = _shampoo_verdict(n, x, sid)
        if verdict == 'refuse':
            t['mistakes'] += 1
            return dict(message=why, refused=True)
        item = SHAMPOO_INDEX[sid]['item']
        if item:
            kit.need(kit.stock(c, item) >= 1, f'Hết {ITEM_INDEX[item]["name"]}. Mở Kho để nhập thêm.')
        if cond:
            kit.need(kit.level(c) >= ITEM_INDEX['conditioner']['unlock'], f'Dầu xả mở ở cấp {ITEM_INDEX["conditioner"]["unlock"]}.')
            kit.need(kit.stock(c, 'conditioner') >= 1, 'Hết dầu xả. Mở Kho để nhập thêm.')
        if item:
            g['cost'] += kit.take(c, item, 1)
        if cond:
            g['cost'] += kit.take(c, 'conditioner', 1)
        g.update(shampoo=sid, temp=temp, cond=cond)
        msgs = []
        if not g['brush'] and 'brush' in services:
            g['slip'] = True
            if x['matted']:
                t['mistakes'] += 1
                msgs.append('Chưa gỡ rối mà đã tắm: cục rối gặp nước bết chặt thành nùi.')
            else:
                msgs.append('Quên chải trước khi tắm — lông rụng bám đầy bồn.')
        if verdict == 'bad':
            g['shampoo_bad'] = True
            t['mistakes'] += 1
            msgs.append(why)
        heat = 15 if not TEMP['low'] <= temp <= TEMP['high'] else 0
        if heat:
            g['temp_bad'] = True
            t['mistakes'] += 1
            msgs.append('Nước lạnh làm bé run cầm cập.' if temp < TEMP['low'] else 'Nước hơi nóng, bé giãy khỏi vòi.')
        _add_stress(t, STEP_STRESS['bath'] + heat)
        base = f'Tắm {SHAMPOO_INDEX[sid]["name"].lower()} ở {temp}°C' + (', ủ dầu xả' if cond else '') + '. Tránh nước vào tai và mắt.'
        return dict(message=' '.join([base] + msgs) + _stress_note(g, t))
    if name == 'pc_rinse':
        mode = kit.one_of(p.get('mode'), ('start', 'stop'), 'Mở hoặc khóa vòi.')
        kit.need(g['shampoo'] is not None, 'Chưa tắm, chưa cần xả.')
        if mode == 'start':
            kit.need(g['rinse'] is None, 'Vòi đang chạy rồi.')
            kit.need(g['dry'] is None and g['dry_pct'] == 0, 'Đã sấy rồi, không xả lại.')
            _calm_enough(t)
            g['rinse'] = round(kit.now(), 3)
            _add_stress(t, STEP_STRESS['rinse'] if g['rinse_s'] == 0 else 0)
            return dict(message=f'Mở vòi, xả từ đầu xuống đuôi, kỹ nách, bụng, kẽ chân. Cần xả ít nhất {RINSE_MIN} giây.')
        kit.need(g['rinse'] is not None, 'Vòi đang khóa.')
        secs = max(0.0, kit.now() - g['rinse'])
        g['rinse'] = None
        g['rinse_s'] = round(min(600.0, g['rinse_s'] + secs), 1)
        if g['rinse_s'] < RINSE_MIN:
            return dict(message=f'Đã xả {g["rinse_s"]:.1f} giây — sờ lông vẫn còn nhờn bọt. Xả thêm cho sạch.')
        return dict(message=f'Xả {g["rinse_s"]:.1f} giây: nước chảy trong, lông kêu “kin kít”. Sạch bọt!')
    if name == 'pc_dry':
        mode = kit.one_of(p.get('mode'), ('start', 'stop'), 'Bật hoặc tắt máy sấy.')
        kit.need(g['shampoo'] is not None, 'Chưa tắm, chưa cần sấy.')
        if mode == 'start':
            kit.need(g['rinse'] is None, 'Khóa vòi trước khi sấy.')
            kit.need(g['rinse_s'] > 0, 'Xả sạch bọt trước khi sấy.')
            kit.need(g['dry'] is None, 'Máy sấy đang chạy.')
            heat = kit.one_of(p.get('heat'), ('cool', 'warm', 'hot'), 'Chọn nấc sấy.')
            if heat == 'hot':
                t['mistakes'] += 1
                return dict(message='Nấc nóng dễ làm bỏng da thú cưng. Tiệm chỉ sấy nấc ấm hoặc mát, để máy cách da một gang tay.', refused=True)
            _calm_enough(t)
            if t.get('gen') and n.get('flat') and heat == 'warm':
                t['mistakes'] += 1
                g['breath'] = True
                _add_stress(t, 20)
                return dict(message='Hơi ấm phả vào mặt, bé mặt ngắn thở khò khè, lưỡi thè dài! Tắt ngay — giống mặt ngắn chỉ sấy nấc mát.'
                            + _stress_note(g, t), refused=True)
            msgs = []
            if g['rinse_s'] < RINSE_MIN and not g['residue']:
                g['residue'] = True
                t['mistakes'] += 1
                msgs.append('Còn sót bọt dưới lông — da sẽ ngứa.')
            if not g['towels']:
                need = 1 if n['species'] == 'cat' or _kg_known(t) <= 10 else 2
                g['cost'] += kit.take(c, 'towel', need)
                g['towels'] = True
                msgs.insert(0, f'Lau khăn ({need} chiếc) cho ráo nước.')
            g.update(dry=round(kit.now(), 3), heat=heat)
            _add_stress(t, STEP_STRESS[heat] + (5 if n['species'] == 'cat' else 0))
            return dict(message=' '.join(msgs + [f'Bật máy sấy nấc {"ấm" if heat == "warm" else "mát"}, sấy ngược chiều lông tới tận chân lông.']) + _stress_note(g, t))
        kit.need(g['dry'] is not None, 'Máy sấy đang tắt.')
        secs = max(0.0, kit.now() - g['dry'])
        need = DRY_NEED[n['coat']] * (1.5 if g['heat'] == 'cool' else 1) * (1.5 if n.get('humid') else 1)
        g['dry'] = None
        g['dry_s'] = round(min(3600.0, g['dry_s'] + secs), 1)
        g['dry_pct'] = min(1000, g['dry_pct'] + int(secs / need * 100))
        if g['dry_s'] > need * DRY_OVER and not g['overdry']:
            g['overdry'] = True
            _add_stress(t, 15)
            return dict(message='Sấy quá lâu: lông khô xơ, bé nóng và cáu. Lần sau tắt sớm hơn.' + _stress_note(g, t))
        if g['dry_pct'] < 100:
            return dict(message=f'Khô khoảng {g["dry_pct"]}%. Chân lông còn ẩm — để ẩm dễ bị nấm da. Sấy tiếp.')
        return dict(message='Lông khô tơi tới chân lông, thơm phức!')
    if name == 'pc_nails':
        kit.need('nails' in services, 'Chủ không đặt cắt móng.')
        kit.need(g['nails'] is None, 'Đã cắt móng rồi.')
        kit.need(not _wet(t), 'Bé còn ướt, sấy khô rồi mới cắt móng.')
        _no_timer(g)
        _calm_enough(t)
        cut = kit.one_of(p.get('cut'), ('tip', 'short'), 'Chọn tỉa đầu móng hoặc cắt ngắn.')
        kit.start_work(t)
        if not cat and x['mood'] == 'bitey' and not g['muzzle']:
            g['bites'] += 1
            t['mistakes'] += 1
            _add_stress(t, 20)
            return dict(message='Bé đớp trúng tay bạn khi bị nắm chân! Hỏi ý chủ về rọ mõm mềm, hoặc dừng lại.' + _stress_note(g, t), refused=True)
        if cat and x['mood'] == 'bitey' and not g['wrap']:
            g['bites'] += 1
            t['mistakes'] += 1
            _add_stress(t, 15)
            return dict(message='Bé cào một đường dài trên tay bạn! Quấn khăn giữ bé trước khi cắt.' + _stress_note(g, t), refused=True)
        if 'nails' not in t['inspected']:
            t['inspected'].append('nails')
        g['nails'] = cut
        _add_stress(t, STEP_STRESS['nails'])
        if cut == 'short' and x['nails'] == 'dark':
            g['nick'] = True
            t['mistakes'] += 1
            kit.metric(c, 'pc_nicks')
            kit.data(c)['nicks'] += 1
            return dict(message='Móng đen không thấy tủy — cắt ngắn chạm tủy, móng chảy máu! Rắc bột cầm máu ngay.' + _stress_note(g, t))
        if cut == 'short':
            return dict(message='Móng trắng thấy rõ tủy hồng: cắt ngắn cách tủy 2 mm, dũa mịn.' + _stress_note(g, t))
        return dict(message='Tỉa từng chút đầu móng, dừng trước phần lõi. An toàn.' + _stress_note(g, t))
    if name == 'pc_ears':
        kit.need('ears' in services, 'Chủ không đặt vệ sinh tai.')
        kit.need(g['ears'] is None, 'Đã xử lý tai rồi.')
        kit.need(not _wet(t), 'Bé còn ướt, sấy khô rồi mới vệ sinh tai.')
        _no_timer(g)
        how = kit.one_of(p.get('how'), ('clean', 'skip'), 'Lau tai hoặc bỏ qua.')
        kit.start_work(t)
        if how == 'skip':
            g['ears'] = 'skip'
            return dict(message='Không lau tai hôm nay. Nếu tai có vấn đề, báo chủ đưa bé đi bác sĩ thú y.')
        _calm_enough(t)
        if not cat and x['mood'] == 'bitey' and not g['muzzle']:
            g['bites'] += 1
            t['mistakes'] += 1
            _add_stress(t, 20)
            return dict(message='Bé quay lại đớp khi bạn chạm vào tai!' + _stress_note(g, t), refused=True)
        g['cost'] += kit.take(c, 'cotton', 2)
        g['ears'] = 'clean'
        if 'ears' not in t['inspected']:
            t['inspected'].append('ears')
        if 'ears' in x['signs']:
            g['ears_hurt'] = True
            t['mistakes'] += 1
            _add_stress(t, 30)
            return dict(message='Bé kêu đau và giật đầu: tai đỏ, có mùi — lau sâu làm bé đau hơn. Dừng lại, báo chủ đưa bé đi bác sĩ thú y.' + _stress_note(g, t))
        _add_stress(t, STEP_STRESS['ears'])
        return dict(message='Nhỏ dung dịch, xoa gốc tai, lau phần vành bằng bông. Không chọc sâu.' + _stress_note(g, t))
    raise kit.eng().GameError('Thao tác tắm tỉa không hợp lệ.')


def _stress_note(g: dict, t: dict | None = None) -> str:
    if t is not None and t.get('gen'):
        if g['stress'] >= STRESS_STOP:
            return f' ⚠️ Bé: {_mood_line(t)} — dừng tay, dỗ dành hoặc dừng dịch vụ.'
        if g['stress'] >= 60:
            return f' Bé: {_mood_line(t)}.'
        return ''
    if g['stress'] >= STRESS_STOP:
        return f' ⚠️ Stress {g["stress"]}: bé hoảng rồi — dừng tay, dỗ dành hoặc dừng dịch vụ.'
    if g['stress'] >= 60:
        return f' Stress {g["stress"]}: bé bắt đầu run.'
    return ''


def _required(t: dict) -> list:
    n, g = t['needs'], t['g']
    miss = []
    sv = n['services']
    if 'brush' in sv and not g['brush']:
        miss.append('chải lông')
    if 'bath' in sv:
        if g['shampoo'] is None:
            miss.append('tắm')
        elif g['rinse_s'] <= 0:
            miss.append('xả')
        elif g['dry_pct'] <= 0:
            miss.append('sấy')
    if 'nails' in sv and g['nails'] is None:
        miss.append('cắt móng')
    if 'ears' in sv and g['ears'] is None:
        miss.append('xử lý tai')
    return miss


def _report(t: dict, p: dict) -> dict:
    allowed = [r['id'] for r in REPORTS if t['job'] in r['jobs']]
    say = kit.id_list(p.get('say'), allowed, len(allowed), 'Chọn các ý muốn báo cho chủ.')
    t['report'] = [r for r in allowed if r in say]
    return dict(message=f'Đã soạn {len(t["report"])} ý để báo chủ.' if t['report'] else 'Chưa chọn ý nào để báo chủ.')


def _report_eval(t: dict) -> dict:
    """What the owner learns vs what really happened (signs, nick, stop, diagnosis)."""
    signs = t['_x'].get('signs', [])
    relevant = [s for s in signs if s != 'cough']
    found = [s for s in relevant if SIGNS[s]['part'] in t['inspected']]
    said = set(t['report'])
    missing = [s for s in found if 'vet_' + s not in said]
    false = [r for r in said if r.startswith('vet_') and r[4:] not in signs]
    unseen = [s for s in relevant if s not in found]
    g = t.get('g') or {}
    return dict(found=found, missing=missing, false=false, unseen=unseen, diagnose='diagnose' in said,
                nick_hidden=bool(g.get('nick')) and 'nick' not in said, nick_false='nick' in said and not g.get('nick'),
                stop_hidden=bool(g.get('stopped')) and 'stopped' not in said, stop_false='stopped' in said and not g.get('stopped'),
                done='done' in said)


# ---------------------------------------------------------------- mistakes the owner finds (consequences)
def _off(grams: int, target: int) -> int:
    """How far a portion is from the chart, in %."""
    return abs(grams - target) * 100 // max(1, target)


def _portion_slip(t: dict, grams: int, target: int) -> None:
    if _within(grams, target):
        return
    name = t['needs']['name']
    sev = 1 if _off(grams, target) <= 30 else 2
    if grams > target:
        cq.slip(t, 'portion', sev, f'Khẩu phần của bé {name} nhiều quá so với cân nặng, ăn vậy dễ béo phì.', 'khẩu phần dư so với bảng')
    else:
        cq.slip(t, 'portion', sev, f'Khẩu phần của bé {name} ít quá so với cân nặng, bé đói meo.', 'khẩu phần thiếu so với bảng')


def _treat_slip(t: dict, treats: int) -> None:
    if t['needs'].get('no_treat') and treats:
        cq.slip(t, 'treat', 1 if treats == 1 else 2, f'Tôi dặn không cho bánh thưởng mà tiệm vẫn cho bé {t["needs"]["name"]} ăn.',
                'dặn không bánh thưởng mà vẫn cho')


def _report_slips(t: dict, ev: dict) -> None:
    """What the owner was told against what really happened (shared by grooming and feeding rounds)."""
    name = t['needs']['name']
    if ev['missing']:
        signs = ', '.join(SIGNS[x]['label'].lower() for x in ev['missing'])
        cq.slip(t, 'untold', 2, f'Tiệm thấy bé {name} có dấu hiệu lạ ({signs}) mà không báo, về nhà tôi mới biết.', 'thấy dấu hiệu bệnh mà không báo')
    if ev['diagnose']:
        cq.slip(t, 'diagnose', 2, 'Tiệm tự đoán bệnh rồi khuyên tôi mua thuốc về cho bé uống, không bảo đi bác sĩ thú y.', 'tự chẩn đoán, khuyên mua thuốc')
    if ev['false'] or ev['nick_false'] or ev['stop_false']:
        cq.slip(t, 'mismatch', 1, f'Lời tiệm báo không khớp với những gì đã xảy ra với bé {name}.', 'lời báo không khớp')


def _groom_slips(t: dict, ev: dict) -> None:
    n, x, g = t['needs'], t['_x'], t['g']
    name = n['name']
    # Hurt: 1★ and the owner refuses to pay (safety).
    if t.get('scald'):
        cq.slip(t, 'scald', 3, f'Nước tắm nóng quá làm bỏng da bé {name}, về nhà da bé đỏ rát.', 'nước tắm nóng làm bỏng da bé', safety=True)
    if g.get('grabbed'):
        cq.slip(t, 'grabbed', 3, f'Bé {name} nhảy khỏi bàn rồi bị chụp giật, va vào tủ, về nhà còn run bần bật.', 'bé bị chụp giật, va vào tủ', safety=True)
    if ev['nick_hidden']:
        cq.slip(t, 'nick_hidden', 3, f'Tiệm cắt móng chảy máu mà giấu, về nhà tôi mới thấy vết máu khô ở chân bé {name}.', 'cắt chạm tủy móng mà giấu',
                safety=True)
    elif g['nick']:
        cq.slip(t, 'nick', 2, f'Tiệm cắt móng bé {name} chạm tủy, chảy máu. Có nói thật và cầm máu, nhưng tôi xót lắm.', 'cắt móng chạm tủy, chảy máu')
    # Clear mistakes against the ticket or the pet's needs.
    if g.get('breath'):
        cq.slip(t, 'breath', 2, f'Sấy hơi ấm phả vào mặt làm bé {name} thở khò khè, tôi đã dặn nhẹ tay mà.', 'sấy ấm làm bé mặt ngắn khó thở')
    if g['shampoo_bad']:
        if n['rx']:
            cq.slip(t, 'shampoo', 2, 'Bác sĩ kê sữa tắm trị liệu, tôi gửi kèm chai mà tiệm lại dùng loại khác.', 'không dùng sữa tắm theo đơn')
        elif n['species'] == 'cat':
            cq.slip(t, 'shampoo', 2, f'Tiệm tắm bé {name} bằng sữa tắm cho chó, mèo đâu dùng được loại đó.', 'tắm mèo bằng sữa tắm cho chó')
        elif n['stage'] == 'young':
            cq.slip(t, 'shampoo', 2, f'Bé {name} còn nhỏ mà tiệm dùng sữa tắm thường, cay mắt bé.', 'sữa tắm quá mạnh cho bé nhỏ')
        else:
            cq.slip(t, 'shampoo', 2, f'Da bé {name} nhạy cảm mà tiệm dùng sữa tắm thường, về nhà nổi mẩn đỏ.', 'sai sữa tắm cho da nhạy cảm')
    if g['ears_hurt']:
        cq.slip(t, 'ears_hurt', 2, f'Tai bé {name} đang đau mà tiệm vẫn lau sâu, bé kêu cả buổi.', 'lau sâu tai đang đau')
    if g['slip'] and x['matted']:
        cq.slip(t, 'matted', 2, f'Lông bé {name} rối mà không gỡ trước khi tắm, giờ bết thành nùi.', 'không gỡ rối trước khi tắm')
    if ev['stop_hidden']:
        cq.slip(t, 'stop_hidden', 2, f'Tiệm làm dở dang rồi trả bé {name} mà không nói gì.', 'làm dở mà không báo')
    elif g['stopped'] and g['peak'] < 70 and _required(t):
        # Stopping is right when the pet panics — not as a way to skip what the owner paid for.
        cq.slip(t, 'skipped', 2, f'Tôi đặt {", ".join(_required(t))} cho bé {name} mà tiệm làm dở rồi trả bé.', 'bỏ dở dịch vụ đã đặt')
    _report_slips(t, ev)
    # Small slips a careful owner notices.
    if g['temp_bad']:
        if (g['temp'] or 0) < TEMP['low']:
            cq.slip(t, 'water', 1, f'Nước tắm lạnh làm bé {name} run cầm cập.', 'nước tắm lạnh')
        else:
            cq.slip(t, 'water', 1, f'Nước tắm hơi nóng, bé {name} giãy suốt.', 'nước tắm hơi nóng')
    if g['residue']:
        cq.slip(t, 'residue', 1, f'Lông bé {name} còn sót bọt, về nhà bé gãi suốt.', 'lông còn sót bọt')
    if g['shampoo'] is not None and g['dry_pct'] < 100:
        cq.slip(t, 'damp', 1, f'Bé {name} về nhà lông còn ẩm, sờ chân lông vẫn ướt.', 'lông còn ẩm')
    if g['overdry']:
        cq.slip(t, 'overdry', 1, f'Sấy lâu quá, lông bé {name} khô xơ.', 'sấy quá lâu, lông khô xơ')
    if g['ears'] == 'skip' and 'ears' in n['services'] and 'ears' not in x['signs']:
        cq.slip(t, 'ears_skip', 1, f'Tôi dặn vệ sinh tai cho bé {name} mà tiệm bỏ qua.', 'dặn vệ sinh tai mà bỏ qua')
    if n['short_nails'] and g['nails'] == 'tip' and x['nails'] == 'clear':
        cq.slip(t, 'nails_long', 1, f'Tôi dặn cắt móng ngắn mà móng bé {name} vẫn còn dài.', 'dặn cắt ngắn mà móng còn dài')
    if g.get('bolts') and not g.get('grabbed'):
        cq.slip(t, 'bolt', 1, f'Bé {name} nhảy khỏi bàn chạy ra tới cửa, may mà không sao.', 'để bé nhảy khỏi bàn')
    if g['peak'] >= 95 and not g['stopped']:
        cq.slip(t, 'panic', 1, f'Bé {name} về nhà còn run, chắc bị làm cho hoảng lắm.', 'làm bé hoảng sợ')
    _treat_slip(t, g['treats'])


def _feed_slips(t: dict, ev: dict) -> None:
    n, x = t['needs'], t['_x']
    name = n['name']
    given, right = t.get('med'), x.get('dose')
    if t.get('gen') and n.get('med') and given and right and given != right:
        if DOSE_IDS.index(given) > DOSE_IDS.index(right):
            cq.slip(t, 'dose', 3, f'Nhãn ghi {DOSE_NAME[right].lower()} mà tiệm cho bé {name} uống {DOSE_NAME[given].lower()}, quá liều bác sĩ kê.',
                    'cho thuốc quá liều trên nhãn', safety=True)
        else:
            cq.slip(t, 'dose', 3, f'Nhãn ghi {DOSE_NAME[right].lower()} mà tiệm chỉ cho bé {name} {DOSE_NAME[given].lower()}, thiếu liều thuốc.',
                    'cho thuốc thiếu liều trên nhãn', safety=True)
    bowl = t['bowl'] or {}
    if bowl and bowl['food'] != n['food']:
        cq.slip(t, 'food', 2, f'Tôi gửi hạt riêng mà tiệm cho bé {name} ăn hạt của tiệm, đổi món vậy bé dễ đau bụng.', 'không dùng thức ăn chủ gửi')
    if not (t['walked'] or t['litter']):
        if n['species'] == 'dog':
            cq.slip(t, 'care', 2, f'Nhờ dắt bé {name} đi dạo mà tiệm để bé nằm chuồng cả buổi.', 'không dắt bé đi dạo')
        else:
            cq.slip(t, 'care', 2, f'Khay cát của bé {name} cả buổi không ai dọn.', 'không dọn khay cát')
    _report_slips(t, ev)
    if bowl:
        _portion_slip(t, bowl['grams'], _portion(n['species'], n['kg'], n['months'], n['meals']))
    _treat_slip(t, t['treats'])


def _board_slips(t: dict) -> None:
    n, x, f = t['needs'], t['_x'], t['flags']
    name = n['name']
    if 'fever' in f:
        cq.slip(t, 'fever', 3, f'Bé {name} đang sốt mà tiệm vẫn nhận, nửa đêm phải gọi tôi đưa bé đi cấp cứu.', 'nhận bé đang sốt', safety=True)
    if 'cough' in f:
        cq.slip(t, 'cough', 3, f'Bé {name} đang ho mà tiệm vẫn nhận vào khu chuồng chung, mấy bé khác lây ho cả.', 'nhận bé đang ho vào chuồng chung',
                safety=True)
    if 'allergy' in f:
        what = ALLERGY_NAMES[n['allergy']]
        cq.slip(t, 'allergy', 3, f'Tôi dặn bé {name} dị ứng {what} mà tiệm cho ăn hạt có {what}.', 'cho ăn thức ăn gây dị ứng', safety=True)
    if 'cramped' in f:
        cq.slip(t, 'cramped', 2, f'Bé {name} nặng {x["kg"]} kg mà tiệm xếp chuồng nhỏ, chật không xoay người được.', 'xếp chuồng quá chật')
    if 'solo' in f:
        cq.slip(t, 'solo', 2, f'Bé {name} hay gây với chó khác mà tiệm cho chơi chung, suýt đánh nhau.', 'cho chơi chung, suýt đánh nhau')
    plan = t['plan']
    if plan:
        _portion_slip(t, plan['grams'], _portion(n['species'], x['kg'], n['months'], plan['meals']))
    if 'meals' in f:
        cq.slip(t, 'meals', 1, f'Bé {name} ăn {MEALS[n["stage"]]} bữa một ngày mà thẻ chuồng ghi {plan["meals"]} bữa.', 'sai số bữa ăn')
    if 'food' in f:
        cq.slip(t, 'food', 1, f'Tôi gửi kèm hạt quen của bé {name} mà tiệm cho ăn hạt của tiệm.', 'không dùng thức ăn chủ gửi')


def _settle(s: dict, c: dict, t: dict, price: int) -> dict:
    """Once, at the hand-off: how the owner takes the recorded mistakes (no job here is paid in advance)."""
    return cq.react(s, c, t, price, who=_owner(t))


def _with(msg: str, r: dict) -> str:
    return f'{msg} {r["message"]}'.strip() if r['message'] else msg


def _unpaid(msg: str, t: dict) -> str:
    """A turned-away visit costs nothing, so there is no money to take back: the owner just says what went wrong
    (the review still names it and loses stars)."""
    rows = cq.slips(t)
    return f'{msg} {_owner(t)}: “{rows[0]["text"]}”' if rows else msg


def _groom_charge(c: dict, t: dict) -> dict:
    n, g = t['needs'], t['g']
    lines = {}
    if 'bath' in n['services'] and g['dry_pct'] > 0 and (not g['stopped'] or g['dry_pct'] >= 100):
        key = _tier(n['species'], _kg_known(t))
        lines[key] = kit.price(c, key, SPEC['prices'][key])
    elif g['brush']:
        lines['brush'] = kit.price(c, 'brush', SPEC['prices']['brush'])
    if g['nails'] and not (g['nick'] and 'nick' in t['report']):
        lines['nails'] = kit.price(c, 'nails', SPEC['prices']['nails'])
    if g['ears'] == 'clean':
        lines['ears'] = kit.price(c, 'ears', SPEC['prices']['ears'])
    return lines


def _groom_handover(s: dict, c: dict, t: dict, p: dict) -> dict:
    kit.confirm(p, 'Xác nhận trả bé và thu tiền.')
    g = t['g']
    kit.need(not g.get('bolt'), 'Bé đang chạy khỏi bàn — đưa bé về an toàn trước đã!')
    _no_timer(g)
    miss = _required(t)
    kit.need(g['stopped'] or not miss, 'Còn bước chưa làm: ' + ', '.join(miss) + '. Làm tiếp hoặc dừng dịch vụ.')
    kit.need(not g['nick'] or g['stanched'], 'Móng còn rỉ máu — cầm máu trước khi trả bé.')
    ev = _report_eval(t)
    t['mistakes'] += len(ev['missing']) + len(ev['false']) + ev['diagnose'] + ev['nick_hidden'] + ev['nick_false'] + ev['stop_hidden'] + ev['stop_false']
    if g['shampoo'] is not None and g['rinse_s'] < RINSE_MIN and not g['residue']:
        g['residue'] = True           # handed back with shampoo still in the coat
        t['mistakes'] += 1
    if g['shampoo'] is not None and g['dry_pct'] < 100:
        t['mistakes'] += 1
    lines = _groom_charge(c, t)
    total = sum(lines.values())
    # An honest nick already waives the nail fee: that waiver is part of the owner's cut, never on top of it.
    waived = kit.price(c, 'nails', SPEC['prices']['nails']) if g['nails'] and g['nick'] and 'nick' in t['report'] else 0
    _groom_slips(t, ev)
    r = _settle(s, c, t, total + waived)
    pay = min(r['pay'], total)
    kit.metric(c, 'pc_grooms')
    _data(c)['day_done'] += 1
    kit.complete(s, c, t, pay, f'Bạn đã tắm tỉa cho bé {t["needs"]["name"]} của {_owner(t)}.')
    note = ' Chủ về nhà mới thấy móng bé có vết máu khô…' if ev['nick_hidden'] else ''
    card = _visit(c, t)
    if not cq.slips(t):
        return dict(message=f'Trả bé {t["needs"]["name"]} thơm tho · thu {pay} xu.{note}{card}', celebrate=t['mistakes'] == 0)
    return dict(message=_with(f'Trả bé {t["needs"]["name"]} · thu {pay} xu.{note}', r) + card, celebrate=False, reaction=r['kind'])


# ---------------------------------------------------------------- boarding
def _board(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n, x = t['needs'], t['_x']
    d = kit.data(c)
    if name == 'pc_pen':
        pid = kit.one_of(p.get('pen'), PEN_INDEX, 'Chuồng không tồn tại.')
        pen = PEN_INDEX[pid]
        kit.need(pen['unlock'] <= kit.level(c), f'{pen["name"]} mở ở cấp {pen["unlock"]}.')
        kit.need(d['pens'][pid] is None, f'{pen["name"]} đang có bé khác.')
        kit.need(pen['zone'] == n['species'], 'Khu chó ồn ào làm mèo hoảng — xếp mèo ở tầng mèo.' if n['species'] == 'cat' else 'Tầng mèo không dành cho chó.')
        if 'scale' in t['inspected']:
            kit.need(x['kg'] <= pen['max_kg'], f'{pen["name"]} chỉ hợp bé tới {pen["max_kg"]} kg; bé nặng {x["kg"]} kg.')
        t['pen'] = pid
        kit.start_work(t)
        return dict(message=f'Chọn {pen["name"]} cho bé {n["name"]}.')
    if name == 'pc_plan':
        food = kit.one_of(p.get('food'), ('own', 'house'), 'Chọn thức ăn của chủ hoặc của tiệm.')
        meals = kit.integer(p.get('meals'), 1, 4)
        grams = kit.integer(p.get('grams'), 5, 900)
        kit.need(type(p.get('solo', False)) is bool, 'Lựa chọn chơi riêng không hợp lệ.')
        kit.need(food == 'house' or n['food_own'], 'Chủ không gửi kèm thức ăn.')
        t['plan'] = dict(food=food, meals=meals, grams=grams, solo=p.get('solo', False))
        kit.start_work(t)
        return dict(message=f'Kế hoạch ăn: {meals} bữa/ngày × {grams} g ({"thức ăn chủ gửi" if food == "own" else "hạt của tiệm"})'
                    + (', chơi riêng.' if t['plan']['solo'] else '.'))
    if name == 'pc_admit':
        kit.confirm(p, 'Xác nhận nhận bé vào lưu trú và thu tiền.')
        kit.need('vaccine' in t['inspected'], 'Theo nội quy, phải xem sổ tiêm trước khi nhận lưu trú.')
        kit.need(t['pen'] and t['plan'], 'Chọn chuồng và lập kế hoạch ăn trước.')
        kit.need(d['pens'][t['pen']] is None, 'Chuồng vừa có bé khác vào. Chọn chuồng khác.')
        if x['vax'] != 'valid':
            t['mistakes'] += 1
            return dict(message='Sổ tiêm không hợp lệ — không nhận lưu trú: các bé khác có thể lây bệnh. Mời chủ đi tiêm ở '
                        + VET + ' rồi quay lại.', refused=True)
        if _vax_short(c, t):
            t['mistakes'] += 1
            return dict(message=f'Mũi phối hợp hết hạn cuối ngày {_vax_until(t)}, trước ngày đón bé (ngày {c["day"] + n["nights"]}) — '
                        f'không nhận: sổ tiêm phải còn hạn suốt kỳ lưu trú. Mời chủ tiêm nhắc ở {VET}.', refused=True)
        if 'fever' in x['signs'] and 'temp' in t['inspected']:
            t['mistakes'] += 1
            return dict(message='Bé đang sốt 39,8°C — không nhận lưu trú: bé cần bác sĩ, và có thể lây cho cả khu chuồng. Mời chủ đưa bé đi khám.',
                        refused=True)
        if 'cough' in x['signs'] and 'body' in t['inspected']:
            t['mistakes'] += 1
            return dict(message='Bé đang ho, chảy nước mũi — có thể lây cả khu chuồng. Không nhận; mời chủ cho bé đi khám.', refused=True)
        flags = []
        if 'cough' in x['signs']:
            flags.append('cough')
            t['mistakes'] += 1
        if 'fever' in x['signs']:
            flags.append('fever')
            t['mistakes'] += 1
        if x['kg'] > PEN_INDEX[t['pen']]['max_kg']:
            flags.append('cramped')
            t['mistakes'] += 1
        plan = t['plan']
        if plan['meals'] != MEALS[n['stage']]:
            flags.append('meals')
            t['mistakes'] += 1
        if not _within(plan['grams'], _portion(n['species'], x['kg'], n['months'], plan['meals'])):
            flags.append('portion')
            t['mistakes'] += 1
        if n['allergy'] and plan['food'] == 'house' and ITEM_INDEX[HOUSE_FOOD[n['species']]].get('allergen') == n['allergy']:
            flags.append('allergy')
            t['mistakes'] += 1
        if x['mood'] == 'dog_aggressive' and not plan['solo']:
            flags.append('solo')
            t['mistakes'] += 1
        if n['food_own'] and plan['food'] == 'house' and 'allergy' not in flags:
            flags.append('food')           # the owner brought the pet's usual food
            t['mistakes'] += 1
        t['flags'] = flags
        d['pens'][t['pen']] = _pet(n['name'], n['species'], x['kg'], n['months'], c['day'] + n['nights'], _owner(t), plan['food'], plan['meals'], plan['grams'])
        rec = _data(c)['book'].get(_task_key(t))
        trust = rec['trust'] if rec else 0
        d['stay'][t['pen']] = _stay_new(d['pens'][t['pen']], own=True, mood=75 if trust >= FAV_AT else 60,
                                        warn=_roll(_task_key(t), c['day'], True, trust))
        d['stay'][t['pen']]['meals'] = min(1, plan['meals'] - 1)     # the owner fed breakfast at home
        d['admitted'] += 1
        key = 'board_dog' if n['species'] == 'dog' else 'board_cat'
        total = kit.price(c, key, SPEC['prices'][key]) * n['nights']
        kit.metric(c, 'pc_boarded')
        _board_slips(t)
        r = _settle(s, c, t, total)
        kit.complete(s, c, t, r['pay'], f'Bạn đã nhận bé {n["name"]} của {_owner(t)} vào lưu trú {n["nights"]} đêm.')
        extra = ' Hôm sau vài bé cùng khu bắt đầu ho…' if 'cough' in flags else ''
        if 'fever' in flags:
            extra += ' Nửa đêm bé sốt cao, li bì — phải gọi chủ đưa đi cấp cứu.'
        d['day_done'] += 1
        msg = f'Bé {n["name"]} vào {PEN_INDEX[t["pen"]]["name"]}, dán thẻ ăn {plan["meals"]} × {plan["grams"]} g. Thu {r["pay"]} xu.{extra}'
        msg = _with(msg, r) + _visit(c, t) + ' Thẻ chăm bé đã có ở khu lưu trú.'
        return dict(message=msg, celebrate=not flags, **({'reaction': r['kind']} if cq.slips(t) else {}))
    # pc_refuse
    kit.confirm(p, 'Xác nhận từ chối nhận lưu trú.')
    reason = kit.one_of(p.get('reason'), ('vaccine', 'sick', 'full'), 'Chọn lý do từ chối.')
    right = dict(vaccine=x['vax'] != 'valid' or _vax_short(c, t), sick='cough' in x['signs'] or 'fever' in x['signs'],
                 full=not any(_pen_ok(c, pid, n['species'], x['kg']) for pid in PEN_INDEX))[reason]
    t['reason'] = reason
    if not right:
        t['mistakes'] += 1
        t['flags'] = t['flags'] + ['wrong_reason']
        sick = 'cough' in x['signs'] or 'fever' in x['signs']
        if x['vax'] != 'valid' or _vax_short(c, t) or sick:
            cq.slip(t, 'reason', 1, f'Tiệm không nhận bé {n["name"]} mà nói sai lý do, tôi chẳng biết nên đi tiêm hay đi khám.', 'từ chối sai lý do')
        else:
            cq.slip(t, 'turned_away', 2, f'Bé {n["name"]} khỏe mạnh, sổ tiêm đủ mà tiệm không nhận, tôi phải chạy đi tìm chỗ khác.', 'từ chối oan bé khỏe mạnh')
    d['refused'] += 1
    d['day_done'] += 1
    if 'fever' in x['signs'] and reason == 'sick':
        d['fevers'] += 1
    kit.metric(c, 'pc_refused')
    text = dict(vaccine=f'Chưa đủ giấy tiêm phòng. Tiệm gửi chủ địa chỉ {VET} để tiêm nhắc, có sổ là nhận ngay.',
                sick=f'Bé có dấu hiệu bệnh. Mời chủ đưa bé đến {VET}; khỏi bệnh tiệm nhận ngay.',
                full='Chuồng phù hợp đã kín. Tiệm giới thiệu chỗ gửi quen và hẹn lần sau.')[reason]
    kit.complete(s, c, t, 0, f'Bạn đã từ chối nhận lưu trú bé {n["name"]} ({text})', status='referred')
    _visit(c, t)
    return dict(message=_unpaid(text + ('' if right else ' (Lý do này chưa đúng với tình trạng của bé…)'), t))


# ---------------------------------------------------------------- feeding round
def _feed(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n, x = t['needs'], t['_x']
    if name == 'pc_feed':
        kit.need(not t['fed'], 'Bé đã được cho ăn bữa này.')
        food = kit.one_of(p.get('food'), ('own', 'house'), 'Chọn thức ăn của chủ hoặc của tiệm.')
        grams = kit.integer(p.get('grams'), 5, 900)
        kit.need(food == 'house' or n['food'] == 'own', 'Chủ không gửi thức ăn cho bé — dùng hạt của tiệm.')
        msgs = []
        cost = 0
        if food == 'house':
            cost = kit.take(c, HOUSE_FOOD[n['species']], 1)
            t['cost'] += cost
        if food != n['food']:
            t['mistakes'] += 1
            msgs.append('Thẻ ghi dùng thức ăn chủ gửi — đổi món đột ngột dễ làm bé đau bụng.')
        target = _portion(n['species'], n['kg'], n['months'], n['meals'])
        if not _within(grams, target):
            t['mistakes'] += 1
            msgs.append('Khẩu phần lệch bảng quá 10%: ' + ('dư, dễ béo phì.' if grams > target else 'thiếu, bé sẽ đói.'))
        t['bowl'] = dict(food=food, grams=grams, cost=cost)
        t['fed'] = True
        kit.start_work(t)
        st = _stay_of(c, t)
        if st:
            st['meals'] = min(kit.data(c)['pens'][t['pen']]['meals'], st['meals'] + 1)
        eat = 'Bé ngửi rồi quay đi, không ăn.' if 'appetite' in x['signs'] else 'Bé ăn ngon lành, liếm sạch bát.'
        return dict(message=f'Cân {grams} g cho vào bát. {eat} ' + ' '.join(msgs))
    if name == 'pc_walk':
        kit.need(n['species'] == 'dog', 'Mèo không dắt đi dạo — hãy dọn khay cát.')
        kit.need(not t['walked'], 'Đã dắt bé đi dạo.')
        kit.need(kit.stock(c, 'poop_bag') >= 1, 'Hết túi nhặt phân — không dắt bé ra đường khi không dọn được. Nhập thêm túi.')
        t['cost'] += kit.take(c, 'poop_bag', 1)
        t['walked'] = True
        kit.data(c)['walks'] += 1
        kit.start_work(t)
        _stay_chore(c, t)
        if 'limp' in x['signs']:
            if 'gait' not in t['inspected']:
                t['inspected'].append('gait')
            return dict(message='Đi được nửa vòng thì bé đi khập khiễng chân sau. Cho bé về nghỉ, nhặt phân bằng túi. Nên báo chủ.')
        return dict(message='Dắt bé đi một vòng quanh công viên, nhặt phân bằng túi, bỏ đúng thùng rác.')
    if name == 'pc_litter':
        kit.need(n['species'] == 'cat', 'Chó không dùng khay cát — hãy dắt đi dạo.')
        kit.need(not t['litter'], 'Đã dọn khay cát.')
        t['litter'] = True
        kit.start_work(t)
        _stay_chore(c, t)
        return dict(message='Xúc khay cát, thêm cát mới, rửa bát nước. Mèo thích khay sạch.')
    if name == 'pc_med':
        kit.need(n.get('med') and t.get('gen'), 'Bé này không có thuốc theo đơn.')
        kit.need(t['med'] is None, 'Đã cho thuốc liều sáng nay rồi.')
        kit.need(t['fed'], 'Nhãn thuốc ghi cho cùng bữa ăn — cho bé ăn trước đã.')
        dose = kit.one_of(p.get('dose'), DOSE_IDS, 'Chọn liều thuốc.')
        t['med'] = dose
        kit.start_work(t)
        st = _stay_of(c, t)
        if st and STAY_MEDS.get(n['name']) and st['med'] is None:
            st['med'] = dose
        right = x['dose']
        if dose == right:
            _data(c)['meds'] += 1
            kit.metric(c, 'pc_meds')
            return dict(message=f'{DOSE_NAME[dose]} trộn vào bữa ăn, đúng nhãn bác sĩ thú y. Ghi giờ cho thuốc vào thẻ chuồng.')
        t['mistakes'] += 1
        more = DOSE_IDS.index(dose) > DOSE_IDS.index(right)
        return dict(message=f'Cho {DOSE_NAME[dose].lower()} — ' + ('vượt liều trên nhãn! Thuốc kháng viêm, thuốc thận quá liều hại dạ dày, hại thận. Gọi bác sĩ thú y hỏi cách theo dõi.'
                                                               if more else 'thiếu liều so với nhãn, thuốc không đủ tác dụng.'))
    # pc_treat
    kit.need(t['treats'] < 3, 'Đủ bánh thưởng rồi.')
    t['cost'] += kit.take(c, 'treat', 1)
    t['treats'] += 1
    kit.start_work(t)
    if n['no_treat']:
        t['mistakes'] += 1
        return dict(message='Bé ăn ngon, nhưng chủ đã dặn không cho bánh thưởng vì đang ăn kiêng!')
    return dict(message='Bé ngồi ngoan nhận bánh, vẫy đuôi rối rít.')


def _feed_handover(s: dict, c: dict, t: dict, p: dict) -> dict:
    kit.confirm(p, 'Xác nhận gửi cập nhật cho chủ.')
    n, x = t['needs'], t['_x']
    kit.need(t['fed'], 'Cho bé ăn trước đã.')
    kit.need(not (t.get('gen') and n.get('med')) or t['med'] is not None, 'Còn liều thuốc buổi sáng theo đơn chưa cho.')
    ev = _report_eval(t)
    t['mistakes'] += len(ev['missing']) + len(ev['false']) + ev['diagnose']
    if not (t['walked'] or t['litter']):
        t['mistakes'] += 1
    if 'appetite' in x['signs'] and t['bowl']['food'] == 'house':
        kit.waste(c, HOUSE_FOOD[n['species']], 1, t['bowl']['cost'], 'Bé bỏ ăn, đổ bát thức ăn')
    d = kit.data(c)
    if t['pen'] and d['pens'][t['pen']] and d['pens'][t['pen']]['task'] == t['id']:
        d['pens'][t['pen']]['task'] = None
    reward = kit.price(c, 'care', SPEC['prices']['care'])
    kit.metric(c, 'pc_rounds')
    d['day_done'] += 1
    _feed_slips(t, ev)
    r = _settle(s, c, t, reward)
    kit.complete(s, c, t, r['pay'], f'Bạn đã chăm bé {n["name"]} và nhắn cập nhật cho {_owner(t)}.')
    card = _visit(c, t)
    if not cq.slips(t):
        return dict(message=f'Đã gửi ảnh và lời nhắn cho {_owner(t)} · phí chăm sóc {reward} xu.{card}', celebrate=t['mistakes'] == 0)
    return dict(message=_with(f'Đã gửi ảnh và lời nhắn cho {_owner(t)} · phí chăm sóc {r["pay"]} xu.', r) + card, celebrate=False, reaction=r['kind'])


# ---------------------------------------------------------------- adoption day
def _adopt(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    kit.confirm(p, 'Xác nhận quyết định nhận nuôi.')
    kit.need(t['inspected'], 'Phỏng vấn gia đình trước đã — hỏi ít nhất một câu.')
    pick = kit.one_of(p.get('pet'), n['candidates'] + ['none'], 'Chọn một bé trong danh sách, hoặc chưa giao bé nào.')
    fits = _fit_list(t)
    d = _data(c)
    t['match'] = pick
    d['day_done'] += 1
    who = _owner(t)
    if pick == 'none':
        if fits:
            t['mistakes'] += 1
            t['flags'] = ['turned_away']
            cq.slip(t, 'turned_away', 2, 'Có bé hợp với nhà tôi mà tiệm bảo chưa có bé nào, cả nhà về tay không.', 'từ chối oan, có bé hợp nếp nhà')
        kit.metric(c, 'pc_adopt_declined')
        kit.complete(s, c, t, 0, f'Bạn tư vấn cho {n["family"]} và hẹn ngày hội sau, chưa giao bé nào.', status='referred')
        if fits:
            return dict(message=_unpaid(f'Bạn hẹn {n["family"]} ngày hội sau. Họ về, hơi buồn — nhìn lại phiếu phỏng vấn, có một bé khá hợp nếp nhà họ…', t))
        return dict(message=f'Bạn giải thích thật lòng: hôm nay chưa có bé nào hợp nếp nhà mình. {who} cảm ơn vì được tư vấn kỹ, hẹn ngày hội sau.',
                    celebrate=True)
    a = ADOPTEE_INDEX[pick]
    fee = kit.price(c, 'adopt', SPEC['prices']['adopt'])
    ok = pick in fits
    if not ok:
        t['mistakes'] += 1
        t['flags'] = ['mismatch']
        d['desk']['marks']['adopt_bad'] = c['day']
        if t['_x']['profile']['allergy']:
            cq.slip(t, 'mismatch', 3, f'Nhà có người dị ứng lông mà tiệm vẫn giao bé {a["name"]}, về nhà hắt hơi suốt.', 'giao bé cho nhà có người dị ứng lông')
        else:
            cq.slip(t, 'mismatch', 3, f'Tiệm giao bé {a["name"]} mà không hợp nếp nhà tôi, giờ cả người lẫn bé đều khổ.', 'giao bé không hợp nếp nhà')
    r = _settle(s, c, t, fee)
    d['adopted'] += 1
    d['day_adopted'] += 1
    kit.metric(c, 'pc_adopted')
    kit.complete(s, c, t, r['pay'], f'Bạn đã giao bé {a["name"]} cho {n["family"]}.')
    tail = ' Cả nhà ôm bé không rời, hẹn gửi ảnh mỗi tuần.' if ok else ' Có điều… nếp nhà này hình như không hợp với bé lắm.'
    if ok:
        # The first weeks in a new home bring questions: the shop calls back.
        opened = [f for f in d['follow'] if f['state'] == 'open'][-(FOLLOW_MAX - 1):]
        closed = [f for f in d['follow'] if f['state'] != 'open']
        room = FOLLOW_MAX - 1 - len(opened)
        d['follow'] = (closed[-room:] if room > 0 else []) + opened
        d['follow'].append(dict(id=kit.next_id(c, 'fu'), pet=pick, family=n['family'], npc=_npc_index(t), day=c['day'],
                                due=c['day'] + FOLLOW_AFTER, state='open', pick=None))
        tail += f' Hẹn ngày {c["day"] + FOLLOW_AFTER} tiệm gọi hỏi thăm bé.'
    return dict(message=_with(f'{a["emoji"]} {a["name"]} về nhà mới với {n["family"]} · phí nhận nuôi {r["pay"]} xu (tiêm phòng, triệt sản).' + tail, r),
                celebrate=ok)


# ---------------------------------------------------------------- care loop: regulars' book
def _stars(c: dict, t: dict) -> int:
    """The fair stars of this visit's review (a reviewer who misremembers does not move trust)."""
    post = next((p for p in c['feed'] if p.get('source') == t['id'] and p.get('kind') == 'review'), None)
    if not post:
        return 0
    fb = post.get('feedback') or {}
    return int(fb.get('fair') or post.get('stars') or 0)


def _visit(c: dict, t: dict) -> str:
    """After a finished visit: write what the shop learned about this pet into the book, and move trust."""
    if t['job'] not in ('groom', 'board', 'feed'):
        return ''
    d = _data(c)
    n, x = t['needs'], t['_x']
    npc, key = _npc_index(t), _task_key(t)
    book = d['book']
    rec = book.get(key)
    if rec is None:
        while len(book) >= BOOK_MAX:
            gone = min(book, key=lambda k: (book[k]['last'], book[k]['visits']))
            ar.record([dict(key=gone, pet=book[gone])], 'pet.book', c)
            del book[gone]
        rec = book[key] = dict(name=n['name'], species=n['species'], breed=n['breed'], npc=npc, visits=0, first=c['day'], last=c['day'],
                               trust=0, mood=None, allergy=None, nails=None, kg=None, fav=False, told=[], job=t['job'], stars=0,
                               vax_due=None, worm_due=c['day'] + kit.rng(ID, 'worm', key).randint(*WORM_FIRST))
    stars = _stars(c, t)
    rec.update(visits=min(10 ** 6, rec['visits'] + 1), last=c['day'], job=t['job'], stars=stars)
    insp = t['inspected']
    if 'mood' in insp and x.get('mood') in BASE_STRESS:
        rec['mood'] = x['mood']
    if t['job'] == 'feed':
        rec['kg'] = n['kg']
    elif 'scale' in insp:
        rec['kg'] = x['kg']
    if 'nails' in insp and x.get('nails') in ('dark', 'clear'):
        rec['nails'] = x['nails']
    if n.get('allergy'):
        rec['allergy'] = n['allergy']
    signs = x.get('signs', [])
    told = [r[4:] for r in t.get('report') or [] if r.startswith('vet_') and r[4:] in signs]
    if t['job'] == 'board' and t.get('reason') == 'sick':
        told += [sg for sg in ('fever', 'cough') if sg in signs and SIGNS[sg]['part'] in insp]
    rec['told'] = ar.first(list(dict.fromkeys(told)), 4, 'pet.told', c)
    if t['job'] == 'board' and 'vaccine' in insp:
        if x['vax'] != 'valid':
            rec['vax_due'] = c['day']
        elif x.get('vax_left') is not None:
            rec['vax_due'] = t['day'] + x['vax_left']
        else:
            rec['vax_due'] = c['day'] + VAX_CYCLE - kit.rng(ID, 'vax', key).randrange(6)
    good = t['status'] == 'completed' and stars >= 4 and not cq.slips(t)
    msg = ''
    if cq.safety(t):
        if rec['trust']:
            rec['trust'] -= 1
            msg = f' Thẻ khách quen: {_owner(t)} bớt tin tiệm một chút.'
    elif good:
        if rec['trust'] < TRUST_MAX:
            rec['trust'] += 1
            msg = f' Thẻ khách quen: bé {n["name"]} thêm quen tiệm — {TRUST_NAMES[rec["trust"]].lower()}.'
        if not rec['fav']:
            rec['fav'] = True
            msg += f' {_owner(t)} kể: bé mê {_fav(n["name"])[1]} nhất.'
    return msg


def _greet(c: dict, t: dict) -> dict:
    kit.need(t.get('regular') is not None, 'Bé đến lần đầu — chưa có thẻ khách quen.')
    kit.need(not t.get('greeted'), 'Đã chào bé rồi.')
    t['greeted'] = True
    if 'patience' in t:
        t['patience'] = min(100, t['patience'] + GREET_PATIENCE)
    n = t['needs']
    rec = _data(c)['book'].get(_task_key(t)) or {}
    trust = rec.get('trust', t['regular'])
    react = ('vẫy đuôi rối rít' if n['species'] == 'dog' else 'chớp mắt chậm') if trust >= FAV_AT else 'ngửi tay bạn, nhận ra mùi quen'
    msg = f'“{n["name"]} ơi, lại gặp nhau rồi!” — bé {react}. {_owner(t)} cười: “Tiệm nhớ cả tên bé luôn!”'
    if rec.get('told'):
        what = ', '.join(SIGNS[sg]['label'].lower() for sg in rec['told'] if sg in SIGNS)
        msg += f' Bạn hỏi thăm chuyện lần trước ({what}): chủ kể đã cho bé đi bác sĩ thú y, giờ đỡ nhiều rồi.'
    return dict(message=msg)


def _calm_fav(c: dict, t: dict) -> dict:
    """From trust 2 the groomer knows what this pet loves most — the gentlest way to calm it."""
    n, g = t['needs'], t['g']
    rec = _data(c)['book'].get(_task_key(t)) or {}
    kit.need(t.get('gen') and (t.get('regular') or 0) >= FAV_AT and rec.get('fav'),
             f'Chưa đủ quen để biết bé mê gì — cần bé “{TRUST_NAMES[FAV_AT].lower()}” trở lên.')
    kind, text = _fav(n['name'])
    extra = ''
    if kind == 'treat':
        kit.need(kit.stock(c, 'treat') >= 1, 'Hết bánh thưởng trong túi.')
        g['cost'] += kit.take(c, 'treat', 1)
        g['treats'] += 1
        if n['no_treat']:
            t['mistakes'] += 1
            extra = ' Nhưng chủ đã dặn không cho bánh thưởng!'
    kit.start_work(t)
    g['stress'] = max(0, g['stress'] - FAV_DROP)
    return dict(message=f'Món bé mê — {text}: bé dịu hẳn, {_mood_line(t)}.' + extra)


# ---------------------------------------------------------------- care loop: boarding days
def _stay_of(c: dict, t: dict):
    d = _data(c)
    v = d['pens'].get(t.get('pen')) if t.get('pen') else None
    st = d['stay'].get(t['pen']) if v else None
    return st if st and v['pet'] == t['needs']['name'] else None


def _stay_chore(c: dict, t: dict) -> None:
    st = _stay_of(c, t)
    if st:
        st['chore'] = True


def _assist_kennel(c: dict) -> str | None:
    """Kennel staff take one pending walk or litter tray off the stay cards."""
    d = _data(c)
    for pid, st in d['stay'].items():
        v = d['pens'].get(pid)
        if not v or st['chore']:
            continue
        if v['species'] == 'dog':
            if not kit.stock(c, 'poop_bag'):
                continue
            kit.take(c, 'poop_bag', 1)
            d['walks'] += 1
            st['chore'] = True
            return f'Đã dắt bé {v["pet"]} ({PEN_INDEX[pid]["name"]}) đi dạo, nhặt phân sạch sẽ.'
        st['chore'] = True
        return f'Đã dọn khay cát cho bé {v["pet"]} ({PEN_INDEX[pid]["name"]}).'
    return None


def _stay_act(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    pid = kit.one_of(p.get('pen'), PEN_INDEX, 'Chuồng không tồn tại.')
    v = d['pens'][pid]
    kit.need(v is not None, 'Chuồng này đang trống.')
    st = d['stay'][pid]
    do = kit.one_of(p.get('do'), STAY_DO, 'Chọn việc chăm bé.')
    name, cat = v['pet'], v['species'] == 'cat'
    kit.metric(c, 'pc_stay_care')
    if do == 'feed':
        kit.need(st['meals'] < v['meals'], f'Bé {name} đã ăn đủ {v["meals"]} bữa hôm nay theo thẻ chuồng.')
        if v['food'] == 'house':
            item = HOUSE_FOOD[v['species']]
            kit.need(kit.stock(c, item) >= 1, f'Hết {ITEM_INDEX[item]["name"]}. Mở Kho để nhập thêm.')
            kit.take(c, item, 1)
        st['meals'] += 1
        food = 'đồ chủ gửi' if v['food'] == 'own' else 'hạt của tiệm'
        if st['warn'] == 'appetite' and not st['played']:
            return dict(message=f'Cân {v["grams"]} g {food} cho vào bát. Bé {name} chỉ ngửi rồi nằm quay mặt vào tường — bé nhớ nhà. '
                                'Ngồi vỗ về, chơi với bé một lúc nhé.')
        return dict(message=f'Cân {v["grams"]} g {food} cho vào bát (bữa {st["meals"]}/{v["meals"]}). Bé {name} ăn sạch bát.')
    if do == 'walk':
        kit.need(not cat, 'Mèo không dắt đi dạo — hãy dọn khay cát.')
        kit.need(not st['chore'], f'Đã dắt bé {name} đi dạo hôm nay.')
        kit.need(kit.stock(c, 'poop_bag') >= 1, 'Hết túi nhặt phân — không dắt bé ra đường khi không dọn được. Nhập thêm túi.')
        kit.take(c, 'poop_bag', 1)
        d['walks'] += 1
        st['chore'] = True
        calm = ' Bé hết bồn chồn, về chuồng nằm ngủ ngon.' if st['warn'] == 'bored' else ''
        return dict(message=f'Dắt bé {name} đi một vòng quanh công viên, nhặt phân bằng túi, bỏ đúng thùng rác.{calm}')
    if do == 'litter':
        kit.need(cat, 'Chó không dùng khay cát — hãy dắt đi dạo.')
        kit.need(not st['chore'], f'Đã dọn khay cát của bé {name} hôm nay.')
        st['chore'] = True
        return dict(message=f'Xúc khay cát, thêm cát mới, rửa bát nước cho bé {name}.')
    if do == 'play':
        kit.need(not st['played'], f'Hôm nay đã chơi với bé {name} rồi — để bé nghỉ.')
        st['played'] = True
        rec = d['book'].get(st['key']) or {}
        how = _fav(name)[1] if rec.get('fav') else ('trò ném bóng' if not cat else 'cần câu lông vũ')
        tail = {'appetite': ' Bé dụi vào tay bạn, chịu ăn lại rồi.', 'bored': ' Bé chạy mệt, nằm ngủ ngon lành.'}.get(st['warn'] or '', '')
        return dict(message=f'Ngồi với bé {name} mười phút: {how}.{tail}')
    if do == 'med':
        rx = STAY_MEDS.get(name)
        kit.need(rx, f'Bé {name} không có thuốc theo đơn.')
        kit.need(st['med'] is None, 'Hôm nay đã cho thuốc rồi.')
        kit.need(st['meals'] >= 1, 'Nhãn ghi cho cùng bữa ăn — cho bé ăn trước đã.')
        dose = kit.one_of(p.get('dose'), DOSE_IDS, 'Chọn liều thuốc.')
        st['med'] = dose
        if dose == rx['dose']:
            d['meds'] += 1
            kit.metric(c, 'pc_meds')
            return dict(message=f'{DOSE_NAME[dose]} trộn vào bữa ăn của bé {name}, đúng nhãn bác sĩ thú y. Ghi giờ vào thẻ chuồng.')
        more = DOSE_IDS.index(dose) > DOSE_IDS.index(rx['dose'])
        return dict(message=f'Cho {DOSE_NAME[dose].lower()} — ' + ('vượt liều trên nhãn! Gọi bác sĩ thú y hỏi cách theo dõi.' if more
                                                                 else 'thiếu liều so với nhãn, thuốc không đủ tác dụng.'))
    # call
    kit.need(not st['called'], 'Hôm nay đã gọi cho chủ rồi.')
    st['called'] = True
    owner = v['owner']
    if st['warn'] == 'upset':
        st['told'] = True
        return dict(message=f'Bạn gọi báo {owner}: bé {name} đi ngoài hơi lỏng, tiệm đang theo dõi và cho uống đủ nước. '
                            'Chủ cảm ơn, dặn nếu kéo dài thì đưa bé đi bác sĩ thú y.')
    if st['health'] < 60:
        st['told'] = True
        return dict(message=f'Bạn báo thật với {owner}: bé {name} hơi mệt, tiệm đề nghị cho bé đi {VET} kiểm tra. Chủ cảm ơn vì được biết sớm.')
    return dict(message=f'Bạn gửi {owner} ảnh bé {name} đang {"nằm phơi nắng" if cat else "gặm đồ chơi"}. Chủ thả tim.')


def _night(c: dict, pid: str, st: dict) -> str:
    """Day close: today's chores move mood and health; floors keep one missed day recoverable."""
    v = _data(c)['pens'][pid]
    rx = STAY_MEDS.get(v['pet'])
    need = v['meals']
    missed = max(0, need - st['meals'])
    warn_ok = _warn_ok(st)
    med_ok = not rx or st['med'] == rx['dose']
    good = missed == 0 and st['chore'] and med_ok and warn_ok
    portion_ok = _within(v['grams'] * v['meals'], _daily(v['species'], v['kg'], v['months']))
    mood = (st['mood'] + (15 if good else 0) + (10 if st['played'] else 0) - 12 * missed - (0 if st['chore'] else 10)
            - (10 if not warn_ok and st['warn'] != 'upset' else 0))
    health = (st['health'] + (10 if good else 0) - (15 if missed >= need else 0) - (0 if med_ok else 15 if st['med'] else 12)
              - (10 if st['warn'] == 'upset' and not st['called'] else 0) - (0 if portion_ok else 4))
    miss = ([f'thiếu {missed} bữa'] if missed else []) + ([] if st['chore'] else ['chưa dắt đi dạo' if v['species'] == 'dog' else 'khay cát bẩn'])
    miss += ([] if med_ok else ['sai/thiếu thuốc']) + ([] if warn_ok else [WARNS[st['warn']]['label'].lower()])
    st.update(mood=max(MOOD_FLOOR, min(100, mood)), health=max(HEALTH_FLOOR, min(100, health)), nights=st['nights'] + 1,
              good=st['good'] + good, meals=0, chore=False, played=False, med=None, called=False)
    if good:
        _data(c)['stays_good'] += 1
    word = f'{_word(MOOD_WORDS, st["mood"]).lower()}, {_word(HEALTH_WORDS, st["health"]).lower()}'
    st['log'] = ar.last(st['log'] + [f'Ngày {c["day"]}: ' + ('chăm đủ' if good else ', '.join(miss) or 'ổn') + f' — {word}.'], STAY_LOG, 'pet.stay_log', c)
    rec = _data(c)['book'].get(st['key']) or {}
    st['warn'] = _roll(st['key'], c['day'] + 1, False, rec.get('trust', 0))
    return f'{v["pet"]} {word}' + (f' ({", ".join(miss)})' if miss else '')


def _pickup(s: dict, c: dict, v: dict, st: dict) -> None:
    """The owner takes the pet home and sees how it is; pets the player admitted bring a review."""
    m, h = st['mood'], st['health']
    stars = 5 if m >= 75 and h >= 80 else 4 if m >= 55 and h >= 60 else 3 if h >= 60 or st['told'] else 2
    name = v['pet']
    rec = _data(c)['book'].get(st['key'])
    if rec:
        rec['trust'] = min(TRUST_MAX, rec['trust'] + 1) if stars >= 4 else max(0, rec['trust'] - 1) if stars <= 2 else rec['trust']
    if not st['own'] or st['npc'] < 0:
        return
    text = {5: f'Đón bé {name} về, bé vui như vừa đi nghỉ mát. Nhật ký chăm sóc ghi kỹ từng bữa, từng lần đi dạo!',
            4: f'Bé {name} về khỏe, chỉ hơi nhớ nhà. Tiệm chăm chu đáo.',
            3: (f'Bé {name} có hôm hơi mệt, may tiệm gọi báo sớm.' if st['told'] else f'Bé {name} ở tiệm có bữa bị trễ, về nhà ăn ngấu nghiến.'),
            2: f'Đón bé {name} về thấy bé lờ đờ, buồn thiu; tiệm không báo gì.'}[stars]
    kit.review(s, c, kit.npc_id(ID, st['npc']), stars, text, f'stay-{st["key"]}-{c["day"]}')
    kit.metric(c, 'pc_stay_reviews')


# ---------------------------------------------------------------- care loop: reminders and adoption follow-up
def _due_list(d: dict, day: int) -> list:
    out = []
    for key, r in d['book'].items():
        for kind in ('vax', 'worm'):
            due = r[kind + '_due']
            if due is not None and due <= day + REMIND_EARLY:
                out.append(dict(pet=key, name=r['name'], species=r['species'], owner=_owner_name(r['npc']), kind=kind, due=due,
                                late=max(0, day - due)))
    return sorted(out, key=lambda x: (x['due'], x['name']))


def _remind(c: dict, p: dict) -> dict:
    d = _data(c)
    key = kit.one_of(p.get('pet'), d['book'], 'Không có bé này trong sổ khách quen.')
    kind = kit.one_of(p.get('kind'), ('vax', 'worm'), 'Chọn nhắc tiêm hay tẩy giun.')
    rec = d['book'][key]
    due = rec[kind + '_due']
    what = 'tiêm nhắc mũi phối hợp' if kind == 'vax' else 'tẩy giun'
    kit.need(due is not None, 'Chưa biết lịch tiêm của bé — xem sổ tiêm khi bé ghé.')
    kit.need(due <= c['day'] + REMIND_EARLY, f'Chưa tới hạn {what} (ngày {due}) — nhắc sớm quá chủ dễ quên.')
    late = c['day'] - due
    rec[kind + '_due'] = c['day'] + (VAX_CYCLE if kind == 'vax' else WORM_CYCLE)
    d['reminders'] += 1
    kit.metric(c, 'pc_reminders')
    owner = _owner_name(rec['npc'])
    msg = f'Đã nhắn {owner}: bé {rec["name"]} tới lịch {what} (hạn ngày {due}). Chủ hẹn đưa bé tới {VET}.'
    if late > REMIND_LATE:
        return dict(message=msg + f' Nhắc trễ {late} ngày — chủ hơi tiếc, nhưng vẫn cảm ơn.')
    c['xp'] += 3
    if rec['trust'] < REMIND_TRUST:
        rec['trust'] += 1
    return dict(message=msg + ' Chủ cảm ơn vì tiệm nhớ giùm.')


def _follow(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    f = next((x for x in d['follow'] if x['id'] == p.get('id')), None)
    kit.need(f is not None and f['state'] == 'open', 'Cuộc gọi hỏi thăm này không còn.')
    kit.need(f['due'] <= c['day'], f'Hẹn ngày {f["due"]} mới gọi — để gia đình quen bé vài hôm đã.')
    script = FOLLOW[f['pet']]
    opt = kit.one_of(p.get('option'), [o['id'] for o in script['options']], 'Chọn lời khuyên.')
    o = next(x for x in script['options'] if x['id'] == opt)
    f.update(state='done', pick=opt)
    d['follows'] += 1
    kit.metric(c, 'pc_follows')
    name = ADOPTEE_INDEX[f['pet']]['name']
    npc = kit.npc_id(ID, f['npc'])
    if o['good']:
        c['xp'] += 8
        kit.review(s, c, npc, 5, f'Tiệm gọi hỏi thăm bé {name}, chỉ cách rất dễ làm. Cả nhà cảm ơn!', f'follow-{f["id"]}')
    elif o['good'] is None:
        c['xp'] += 3
    else:
        kit.review(s, c, npc, 2, f'Tiệm khuyên cách làm bé {name} càng sợ hơn.', f'follow-{f["id"]}')
    return dict(message=f'📞 {f["family"]}: {o["outcome"]}', celebrate=bool(o['good']))


# ---------------------------------------------------------------- feedback
def _join(parts, default: str) -> str:
    return ' · '.join(x for x in parts if x) or default


def _speed(t: dict) -> dict:
    p = t.get('patience', 100)
    return dict(key='speed', label='Thời gian chờ', score=5 if p >= 90 else 4 if p >= 70 else 3 if p >= 50 else 2, note=f'kiên nhẫn còn {p}%')


def _honesty_row(ev: dict, allow_nick=True) -> dict:
    if allow_nick and ev['nick_hidden']:
        return dict(key='honesty', label='Nói thật với chủ', score=1, note='giấu chuyện cắt chạm tủy móng')
    if ev['missing']:
        return dict(key='honesty', label='Nói thật với chủ', score=2, note='thấy ' + ', '.join(SIGNS[s]['label'].lower() for s in ev['missing']) + ' mà không báo')
    if ev['diagnose']:
        return dict(key='honesty', label='Nói thật với chủ', score=2, note='tự chẩn đoán, khuyên mua thuốc')
    if ev['false'] or ev['nick_false'] or ev['stop_false'] or ev['stop_hidden']:
        return dict(key='honesty', label='Nói thật với chủ', score=3, note='lời báo không khớp với những gì đã xảy ra')
    if ev['unseen']:
        return dict(key='honesty', label='Nói thật với chủ', score=3, note='về nhà mới thấy ' + ', '.join(SIGNS[s]['label'].lower() for s in ev['unseen']))
    note = 'kể rõ từng bước' + (', khuyên đi bác sĩ thú y' if ev['found'] else '') + (', nhận lỗi cắt móng' if allow_nick and not ev['nick_false'] and ev.get('nick') else '')
    return dict(key='honesty', label='Nói thật với chủ', score=5 if ev['done'] or ev['found'] else 4, note=note if ev['done'] or ev['found'] else 'hơi ít lời')


def feedback(c: dict, t: dict) -> dict:
    job = t['job']
    n, x = t['needs'], t['_x']
    rows = []
    cap = 5
    if job == 'adopt':
        fits = _fit_list(t)
        pick = t['match']
        right = (not fits) if pick == 'none' else pick in fits
        if pick == 'none':
            mnote = 'chưa có bé hợp, từ chối khéo' if right else 'từ chối oan, có bé hợp nếp nhà'
        else:
            mnote = f'bé {ADOPTEE_INDEX[pick]["name"]} hợp nếp nhà' if right else f'bé {ADOPTEE_INDEX[pick]["name"]} không hợp nếp nhà, dễ bị trả lại'
        rows.append(dict(key='match', label='Bé về đúng nhà', score=5 if right else 1, note=mnote))
        asked = len(t['inspected'])
        rows.append(dict(key='interview', label='Phỏng vấn kỹ', score=5 if asked >= 5 else 4 if asked >= 4 else 3 if asked >= 3 else 2,
                         note=f'hỏi {asked}/5 điều quan trọng'))
        rows.append(_speed(t))
        return dict(criteria=rows, cap=5 if right else 2)
    if job == 'groom':
        g = t['g']
        ev = _report_eval(t)
        ev['nick'] = g['nick']
        hurt = g['bites'] + g['nick'] + g['ears_hurt'] + g['temp_bad'] + g.get('grabbed', False) + g.get('breath', False)
        rows.append(dict(key='gentle', label='Nhẹ tay, an toàn', score=max(1, 5 - hurt),
                         note=_join(['bị cắn/cào' if g['bites'] else '', 'móng chảy máu' if g['nick'] else '', 'lau tai đau' if g['ears_hurt'] else '',
                                     'nước không đúng độ' if g['temp_bad'] else '', 'chụp giật khi bé trốn' if g.get('grabbed') else '',
                                     'sấy ấm làm bé mặt ngắn khó thở' if g.get('breath') else ''], 'bé được nâng niu')))
        if g['shampoo'] is not None:
            damp = g['dry_pct'] < 100
            sc = 5 - g['shampoo_bad'] - g['residue'] - damp - g['overdry'] - (1 if g['slip'] and x['matted'] else 0)
            note = _join(['sai sữa tắm' if g['shampoo_bad'] else '', 'còn bọt' if g['residue'] else '', 'lông còn ẩm' if damp else '',
                          'khô xơ' if g['overdry'] else '', 'lông bết nùi' if g['slip'] and x['matted'] else ''], 'sạch thơm')
            if sc >= 5 and n['coat'] == 'long':
                note = 'mượt thơm' + (', có dầu xả' if g['cond'] else '')
            rows.append(dict(key='coat', label='Lông sạch thơm', score=max(1, sc), note=note))
        elif 'brush' in n['services']:
            fleas = 'fleas' in x['signs'] and not g['flea']
            rows.append(dict(key='coat', label='Lông gọn gàng', score=4 if fleas or not g['brush'] else 5, note='còn bọ chét' if fleas else 'chải mượt'))
        peak = g['peak']
        calm = 2 if peak >= 95 else 3 if peak >= STRESS_STOP else 4 if peak >= 60 else 5
        if g['stopped'] and peak >= 70:
            calm = max(calm, 4)
        if t.get('gen'):
            cnote = 'dừng đúng lúc bé hoảng' if g['stopped'] and peak >= 70 else f'lúc căng nhất: {BAND_NAME[_band(peak)].lower()}'
            if g['bolts']:
                cnote += ' · bé nhảy khỏi bàn' + ('' if g['grabbed'] else ', được dỗ về bình tĩnh')
                calm = max(1, calm - 1)
            elif g['loop'] and x.get('runner'):
                cnote += ' · đeo vòng giữ từ đầu'
            rows.append(dict(key='calm', label='Bé thoải mái', score=calm, note=cnote))
        else:
            rows.append(dict(key='calm', label='Bé thoải mái', score=calm,
                             note='dừng đúng lúc bé hoảng' if g['stopped'] and peak >= 70 else f'stress cao nhất {peak}'))
        rows.append(_honesty_row(ev))
        if n['short_nails'] and g['nails']:
            if x['nails'] == 'clear':
                wish = 5 if g['nails'] == 'short' else 3
                wnote = 'móng ngắn gọn như dặn' if wish == 5 else 'móng còn hơi dài'
            else:
                wish = 4 if g['nails'] == 'tip' and ev['done'] else 3 if g['nails'] == 'tip' else 2
                wnote = 'móng đen nên chỉ tỉa đầu, được giải thích' if wish == 4 else 'móng vẫn dài, không ai giải thích' if wish == 3 else 'cắt ngắn tới chảy máu'
            rows.append(dict(key='wish', label='Làm đúng lời dặn', score=wish, note=wnote))
        if n['no_treat']:
            rows.append(dict(key='rules', label='Giữ chế độ ăn', score=2 if g['treats'] else 5, note='bị cho ăn bánh' if g['treats'] else 'không ăn vặt'))
        if g['bites'] >= 2:
            cap = 3
    elif job == 'board':
        if t['status'] == 'referred':
            right = 'wrong_reason' not in t['flags']
            rows.append(dict(key='honesty', label='Từ chối đúng lý do', score=5 if right else 2,
                             note=dict(vaccine='cần tiêm nhắc trước', sick='bé cần đi khám trước', full='chuồng kín thật').get(t['reason'], '')
                             if right else 'lý do không khớp tình trạng bé'))
            rows.append(dict(key='care', label='Hướng dẫn chủ', score=5, note='có địa chỉ ' + VET if t['reason'] != 'full' else 'giới thiệu chỗ gửi khác'))
        else:
            f = t['flags']
            rows.append(dict(key='safety', label='An toàn cả khu chuồng', score=1 if 'cough' in f or 'fever' in f else 5,
                             note='nhận bé đang ho, lây cho bé khác' if 'cough' in f else 'nhận bé đang sốt, nửa đêm phải cấp cứu'
                             if 'fever' in f else 'kiểm sổ tiêm, đo nhiệt độ kỹ' if 'temp' in t['inspected'] else 'kiểm sổ tiêm kỹ'))
            rows.append(dict(key='fit', label='Chuồng phù hợp', score=max(1, 5 - 2 * ('cramped' in f) - 2 * ('solo' in f)),
                             note=_join(['chuồng chật' if 'cramped' in f else '', 'cho chơi chung, suýt đánh nhau' if 'solo' in f else ''], 'rộng rãi, đúng khu')))
            rows.append(dict(key='plan', label='Khẩu phần & thức ăn', score=max(1, 5 - 2 * ('portion' in f) - ('meals' in f) - 2 * ('allergy' in f) - ('food' in f)),
                             note=_join(['sai khẩu phần' if 'portion' in f else '', 'sai số bữa' if 'meals' in f else '',
                                         'thức ăn gây dị ứng' if 'allergy' in f else '', 'không dùng thức ăn chủ gửi' if 'food' in f else ''],
                                        'đúng bảng khẩu phần')))
            if 'cough' in f or 'fever' in f:
                cap = 2
    else:
        ev = _report_eval(t)
        bowl = t['bowl'] or {}
        target = _portion(n['species'], n['kg'], n['months'], n['meals'])
        ok = _within(bowl.get('grams', 0), target)
        rows.append(dict(key='portion', label='Khẩu phần đúng bảng', score=5 if ok and bowl.get('food') == n['food'] else 3 if ok or bowl.get('food') == n['food'] else 2,
                         note=f'{bowl.get("grams", 0)} g/bữa' + ('' if bowl.get('food') == n['food'] else ' · sai loại thức ăn')))
        done = t['walked'] or t['litter']
        rows.append(dict(key='care', label='Vận động & vệ sinh', score=5 if done else 2,
                         note=('được dắt đi dạo' if t['walked'] else 'khay cát sạch') if done else 'không được dắt đi/dọn khay'))
        rows.append(_honesty_row(ev, allow_nick=False) | dict(key='notice', label='Để ý sức khỏe'))
        if n['no_treat']:
            rows.append(dict(key='rules', label='Giữ chế độ ăn', score=2 if t['treats'] else 5, note='bị cho ăn bánh' if t['treats'] else 'không ăn vặt'))
        if t.get('gen') and n.get('med'):
            given, right = t.get('med'), x.get('dose')
            over = given is not None and DOSE_IDS.index(given) > DOSE_IDS.index(right)
            rows.append(dict(key='med', label='Cho thuốc đúng đơn', score=5 if given == right else 1 if over else 2,
                             note='đúng liều trên nhãn, cùng bữa ăn' if given == right else 'vượt liều bác sĩ kê' if over else 'thiếu liều'))
            if given != right:
                cap = min(cap, 3)
    if t.get('regular') is not None:
        rows.append(dict(key='regular', label='Nhớ bé', score=5 if t.get('greeted') else 4,
                         note='gọi tên bé, hỏi thăm lần trước' if t.get('greeted') else 'không nhận ra khách quen'))
    rows.append(_speed(t))
    return dict(criteria=rows, cap=cap)


# ---------------------------------------------------------------- projection & validation
def public_task(t: dict) -> dict:
    v = tree_copy(t)
    x = v.pop('_x', {})
    if not t['known']:
        v['needs'] = None
        return v
    v['found'] = {part: _found(t, part) for part in t['inspected']}
    facts = {}
    if 'scale' in t['inspected']:
        facts['kg'] = x['kg']
    if 'mood' in t['inspected']:
        facts['mood'] = x['mood']
    if 'nails' in t['inspected'] and 'nails' in x:
        facts['nails'] = x['nails']
    if 'skin' in t['inspected'] and 'skin' in x:
        facts['skin'] = x['skin']
    if 'vaccine' in t['inspected']:
        facts['vax'] = x['vax']
    if 'coat' in t['inspected'] and 'matted' in x:
        facts['matted'] = x['matted']
    facts['signs'] = [s for s in x.get('signs', []) if SIGNS[s]['part'] in t['inspected']]
    if 'vaccine' in t['inspected'] and x.get('vax_left') is not None:
        facts['vax_until'] = t['day'] + x['vax_left']
    v['facts'] = facts
    if t['job'] == 'feed' and t['fed']:
        v['ate'] = 'appetite' not in x['signs']
    if t.get('gen') and t['job'] == 'groom':
        # Body language instead of a number: the stylist reads the pet.
        v['g']['stress'] = None
        v['g']['peak'] = None
        v['cues'] = _cues(t)
    return v


def _public_care(d: dict, day: int) -> None:
    """Book, stay cards, reminders and follow-up calls as the client shows them (doses stay on the server)."""
    book = {}
    for key, r in d['book'].items():
        kind, fav = _fav(r['name'])
        book[key] = dict(r, key=key, owner=_owner_name(r['npc']), trust_name=TRUST_NAMES[r['trust']],
                         fav_text=fav if r['fav'] else None, fav_kind=kind if r['fav'] else None)
    stays = {}
    for pid, st in d['stay'].items():
        v = d['pens'].get(pid)
        if not v:
            continue
        rx = STAY_MEDS.get(v['pet'])
        rec = d['book'].get(st['key']) or {}
        stays[pid] = dict(st, need=v['meals'], mood_word=_word(MOOD_WORDS, st['mood']), health_word=_word(HEALTH_WORDS, st['health']),
                          rx=dict(name=rx['name'], label=rx['label']) if rx else None, todo=_stay_todo(v, st),
                          warn_info=WARNS[st['warn']] if st['warn'] else None, warn_ok=_warn_ok(st),
                          fav_text=_fav(v['pet'])[1] if rec.get('fav') else None, trust=rec.get('trust', 0))
    d['book'] = book
    d['stay'] = stays
    d['due'] = _due_list(dict(book=book), day)
    calls = []
    for f in d['follow']:
        if f['state'] != 'open':
            continue
        opts = [dict(id=o['id'], label=o['label']) for o in FOLLOW[f['pet']]['options']]
        kit.rng(ID, 'follow-order', f['id']).shuffle(opts)       # the careful answer is not always the first button
        calls.append(dict(f, name=ADOPTEE_INDEX[f['pet']]['name'], emoji=ADOPTEE_INDEX[f['pet']]['emoji'], ready=f['due'] <= day,
                          q=FOLLOW[f['pet']]['q'], options=opts))
    d['follow'] = calls


def public_data(c: dict) -> dict:
    d = _migrate(tree_copy(kit.data(c)))
    desk = d.pop('desk', None) or kit.desk_initial()
    _public_care(d, c['day'])
    d['today'] = c['day']
    d['level'] = kit.level(c)
    mod = today(c['day'])
    d['mod'] = dict(id=mod['id'], title=mod['title'], emoji=mod['emoji'], text=mod['text'])
    d['desk'] = kit.desk_public(desk, DESK, ID)
    if d['desk']['ev']:
        # Options come in a shuffled order so the careful answer is not always the first button.
        kit.rng(ID, 'desk-order', d['desk']['ev']['id'], c['day']).shuffle(d['desk']['ev']['options'])
    d['tier'] = kit.tier(c['day'])
    d['sanitized_today'] = d['sanitize_day'] == c['day']
    return d


def _bool(v) -> None:
    kit.need(type(v) is bool, 'Trạng thái không hợp lệ.')


def _num(v, high) -> None:
    kit.need(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= high, 'Số liệu không hợp lệ.')


def validate_task(t: dict, original: dict) -> None:
    job = t['job']
    kit.need(job in JOB_PARTS, 'Loại việc tiệm thú cưng không hợp lệ.')
    if job == 'adopt':
        kit.need(t.get('gen') == GEN, 'Phiếu nhận nuôi sai.')
        kit.integer(t.get('mistakes', 0), 0, 100000)
        kit.need(isinstance(t['inspected'], list) and len(set(t['inspected'])) == len(t['inspected'])
                 and all(x in JOB_PARTS[job] for x in t['inspected']), 'Danh sách câu hỏi sai.')
        kit.need(t['match'] is None or t['match'] in t['needs']['candidates'] + ['none'], 'Lựa chọn nhận nuôi sai.')
        kit.need(isinstance(t['flags'], list) and len(t['flags']) <= 2 and all(f in ('mismatch', 'turned_away') for f in t['flags']),
                 'Ghi chú nhận nuôi sai.')
        return
    kit.integer(t.get('mistakes', 0), 0, 100000)
    kit.need(t.get('regular') is None or (type(t['regular']) is int and 0 <= t['regular'] <= TRUST_MAX), 'Thẻ khách quen sai.')
    kit.need(type(t.get('greeted', False)) is bool and (not t.get('greeted') or t.get('regular') is not None), 'Lời chào sai.')
    kit.need(type(t.get('scald', False)) is bool and (not t.get('scald') or job == 'groom'), 'Ghi chú nước tắm sai.')
    kit.need(isinstance(t['inspected'], list) and len(set(t['inspected'])) == len(t['inspected'])
             and all(x in JOB_PARTS[job] for x in t['inspected']), 'Danh sách kiểm tra sai.')
    if job in ('groom', 'feed'):
        allowed = [r['id'] for r in REPORTS if job in r['jobs']]
        kit.need(isinstance(t['report'], list) and len(set(t['report'])) == len(t['report']) and all(r in allowed for r in t['report']), 'Lời báo sai.')
    if job == 'groom':
        g = t['g']
        kit.need(isinstance(g, dict) and set(g) == set(original['g']), 'Phiếu tắm tỉa thiếu dữ liệu.')
        for k in ('brush', 'flea', 'cond', 'towels', 'nick', 'stanched', 'consent', 'muzzle', 'wrap', 'stopped', 'residue', 'temp_bad',
                  'shampoo_bad', 'ears_hurt', 'slip', 'overdry'):
            _bool(g[k])
        kit.integer(g['stress'], 0, 100)
        kit.integer(g['peak'], 0, 100)
        kit.need(g['shampoo'] is None or g['shampoo'] in SHAMPOO_INDEX, 'Sữa tắm sai.')
        kit.need(g['temp'] is None or 30 <= kit.integer(g['temp'], 30, 45), 'Nhiệt độ sai.')
        kit.need(g['heat'] in (None, 'cool', 'warm'), 'Nấc sấy sai.')
        kit.need(g['nails'] in (None, 'tip', 'short') and g['ears'] in (None, 'clean', 'skip'), 'Bước làm sai.')
        for k in ('rinse', 'dry'):
            kit.need(g[k] is None or (isinstance(g[k], (int, float)) and not isinstance(g[k], bool) and 0 <= g[k] < 10**11), 'Đồng hồ sai.')
        _num(g['rinse_s'], 600)
        _num(g['dry_s'], 3600)
        kit.integer(g['dry_pct'], 0, 1000)
        kit.integer(g['bites'], 0, 100)
        kit.integer(g['treats'], 0, 100)
        kit.integer(g['cost'], 0, 100000)
        kit.need(not g['stanched'] or g['nick'], 'Cầm máu sai.')
        kit.need(not g['muzzle'] or (g['consent'] and t['needs']['species'] == 'dog'), 'Rọ mõm sai.')
        if t.get('gen'):
            for k in ('loop', 'bolt', 'grabbed', 'breath'):
                _bool(g[k])
            kit.integer(g['bolts'], 0, 100)
            kit.need(not g['breath'] or t['needs']['flat'], 'Ghi chú sấy sai.')
    elif job == 'board':
        kit.need(t['pen'] is None or t['pen'] in PEN_INDEX, 'Chuồng sai.')
        pl = t['plan']
        kit.need(pl is None or (isinstance(pl, dict) and set(pl) == {'food', 'meals', 'grams', 'solo'}), 'Kế hoạch ăn sai.')
        if pl:
            kit.need(pl['food'] in ('own', 'house'), 'Thức ăn sai.')
            kit.integer(pl['meals'], 1, 4)
            kit.integer(pl['grams'], 5, 900)
            _bool(pl['solo'])
        kit.need(t['reason'] in (None, 'vaccine', 'sick', 'full'), 'Lý do sai.')
        kit.need(isinstance(t['flags'], list) and len(t['flags']) <= 8
                 and all(f in ('cough', 'fever', 'cramped', 'meals', 'portion', 'allergy', 'solo', 'food', 'wrong_reason') for f in t['flags']), 'Ghi chú sai.')
    else:
        kit.need(t['pen'] is None or t['pen'] in PEN_INDEX, 'Chuồng sai.')
        for k in ('bound', 'fed', 'walked', 'litter'):
            _bool(t[k])
        b = t['bowl']
        kit.need(b is None or (isinstance(b, dict) and set(b) == {'food', 'grams', 'cost'} and b['food'] in ('own', 'house')), 'Bát ăn sai.')
        if b:
            kit.integer(b['grams'], 5, 900)
            kit.integer(b['cost'], 0, 10000)
        kit.integer(t['treats'], 0, 3)
        kit.integer(t['cost'], 0, 100000)
        if t.get('gen'):
            kit.need(t['med'] is None or (t['med'] in DOSE_IDS and t['needs']['med'] and t['fed']), 'Liều thuốc sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.mark_legacy(c, ID)
    for k in DATA_V2:
        kit.integer(d[k], 0, 10**9)
    kit.desk_validate(d['desk'], DESK)
    kit.need(isinstance(d.get('pens'), dict) and set(d['pens']) == set(PEN_INDEX), 'Sơ đồ chuồng sai.')
    for pid, v in d['pens'].items():
        if v is None:
            continue
        kit.need(isinstance(v, dict) and set(v) == set(_pet('x', 'dog', 1, 1, 1, 'x', 'own', 1, 1)), 'Chuồng thiếu dữ liệu.')
        kit.text(v['pet'], 40)
        kit.text(v['owner'], 80)
        kit.need(v['species'] == PEN_INDEX[pid]['zone'], 'Sai khu chuồng.')
        kit.integer(v['kg'], 1, 99)
        kit.integer(v['months'], 0, 400)
        kit.integer(v['until'], 0, 10**7)
        kit.need(v['food'] in ('own', 'house'), 'Thức ăn sai.')
        kit.integer(v['meals'], 1, 4)
        kit.integer(v['grams'], 1, 900)
        kit.need(v['task'] is None or (isinstance(v['task'], str) and len(v['task']) <= 80), 'Liên kết chuồng sai.')
    for k in ('admitted', 'refused', 'walks', 'nicks', 'referrals', 'departed'):
        kit.integer(d.get(k), 0, 10**9)
    _validate_care(d)


def _day_or_none(v) -> None:
    kit.need(v is None or (type(v) is int and 0 <= v <= 10 ** 7), 'Ngày hẹn sai.')


def _validate_care(d: dict) -> None:
    for k in DATA_V3:
        kit.integer(d[k], 0, 10 ** 9)
    book = d['book']
    kit.need(isinstance(book, dict) and len(book) <= BOOK_MAX, 'Sổ khách quen sai.')
    for key, r in book.items():
        kit.text(key, 60)
        kit.need(isinstance(r, dict) and set(r) == set(BOOK_KEYS), 'Thẻ khách quen thiếu dữ liệu.')
        kit.text(r['name'], 40)
        kit.need(key == _key(r['npc'], r['name']) and r['species'] in SPECIES_NAMES, 'Thẻ khách quen sai.')
        kit.text(r['breed'], 60)
        kit.integer(r['npc'], 0, len(PEOPLE) - 1)
        kit.integer(r['visits'], 0, 10 ** 6)
        kit.integer(r['first'], 1, 10 ** 7)
        kit.integer(r['last'], r['first'], 10 ** 7)
        kit.integer(r['trust'], 0, TRUST_MAX)
        kit.integer(r['stars'], 0, 5)
        kit.need(r['mood'] is None or r['mood'] in BASE_STRESS, 'Tính khí sai.')
        kit.need(r['allergy'] is None or r['allergy'] in ALLERGY_NAMES, 'Dị ứng sai.')
        kit.need(r['nails'] in (None, 'dark', 'clear') and r['job'] in ('groom', 'board', 'feed'), 'Thẻ khách quen sai.')
        kit.need(r['kg'] is None or (type(r['kg']) is int and 1 <= r['kg'] <= 99), 'Cân nặng sai.')
        _bool(r['fav'])
        kit.need(isinstance(r['told'], list) and len(r['told']) <= 4 and len(set(r['told'])) == len(r['told'])
                 and all(x in SIGNS for x in r['told']), 'Ghi chú sức khỏe sai.')
        _day_or_none(r['vax_due'])
        _day_or_none(r['worm_due'])
    stay, pens = d['stay'], d['pens']
    kit.need(isinstance(stay, dict), 'Thẻ lưu trú sai.')
    for pid, st in stay.items():
        v = pens.get(pid) if pid in PEN_INDEX else None
        kit.need(v is not None and isinstance(st, dict) and set(st) == set(STAY_KEYS) and st['pet'] == v['pet'], 'Thẻ lưu trú không khớp chuồng.')
        kit.text(st['key'], 60)
        kit.integer(st['npc'], -1, len(PEOPLE) - 1)
        for k in ('own', 'chore', 'played', 'called', 'told'):
            _bool(st[k])
        kit.integer(st['mood'], 0, 100)
        kit.integer(st['health'], 0, 100)
        kit.integer(st['meals'], 0, 4)
        kit.integer(st['nights'], 0, 10 ** 6)
        kit.integer(st['good'], 0, st['nights'])
        kit.need(st['med'] is None or st['med'] in DOSE_IDS, 'Liều thuốc sai.')
        kit.need(st['warn'] is None or st['warn'] in WARNS, 'Ghi chú lưu trú sai.')
        kit.need(isinstance(st['log'], list) and len(st['log']) <= STAY_LOG, 'Nhật ký lưu trú sai.')
        for row in st['log']:
            kit.text(row, 200)
    follow = d['follow']
    kit.need(isinstance(follow, list) and len(follow) <= FOLLOW_MAX, 'Lịch hỏi thăm sai.')
    for f in follow:
        kit.need(isinstance(f, dict) and set(f) == set(FOLLOW_KEYS) and f['pet'] in FOLLOW, 'Lịch hỏi thăm thiếu dữ liệu.')
        kit.text(f['id'], 20)
        kit.text(f['family'], 80)
        kit.integer(f['npc'], 0, len(PEOPLE) - 1)
        kit.integer(f['day'], 1, 10 ** 7)
        kit.integer(f['due'], f['day'], 10 ** 7)
        kit.need(f['state'] in ('open', 'done', 'lapsed'), 'Trạng thái hỏi thăm sai.')
        kit.need((f['pick'] is None) == (f['state'] != 'done')
                 and (f['pick'] is None or f['pick'] in [o['id'] for o in FOLLOW[f['pet']]['options']]), 'Lời khuyên sai.')


# ---------------------------------------------------------------- staff, hints, content
def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e['role']
    ok = t and t['career'] == ID and t['known'] and t['status'] not in ('completed', 'referred', 'cancelled')
    if role == 'kennel':
        if ok and t['job'] == 'feed' and t['needs']['species'] == 'dog' and not t['walked'] and kit.stock(c, 'poop_bag'):
            t['cost'] += kit.take(c, 'poop_bag', 1)
            t['walked'] = True
            kit.data(c)['walks'] += 1
            _stay_chore(c, t)
            if 'limp' in t['_x']['signs'] and 'gait' not in t['inspected']:
                t['inspected'].append('gait')
                return f'Đã dắt bé {t["needs"]["name"]} đi dạo. Bé đi khập khiễng chân sau, em báo để mình nhắn chủ.'
            return f'Đã dắt bé {t["needs"]["name"]} đi dạo và nhặt phân sạch sẽ.'
        return _assist_kennel(c) or 'Đã lau chuồng, thay nước uống, phơi khăn.'
    if not ok:
        return None
    if role == 'bather' and t['job'] == 'groom':
        g = t['g']
        if not g.get('bolt') and 'brush' in t['needs']['services'] and not g['brush'] and g['shampoo'] is None and g['stress'] < STRESS_STOP and not g['stopped']:
            g['brush'] = True
            _add_stress(t, STEP_STRESS['brush'] + (15 if t['_x']['matted'] else 0))
            if t.get('gen'):
                return f'Đã chải gỡ rối cho bé {t["needs"]["name"]}. Bé đang: {_mood_line(t)}.'
            return f'Đã chải gỡ rối cho bé {t["needs"]["name"]}. Stress bé đang {g["stress"]}.'
    if role == 'front' and t['job'] == 'board' and 'vaccine' not in t['inspected']:
        t['inspected'].append('vaccine')
        return 'Em đã xem sổ tiêm: ' + _found(t, 'vaccine')
    return None


def hint(c: dict, t: dict) -> str:
    if t['job'] == 'adopt':
        return ('Hỏi đủ năm điều: chỗ ở, giờ vắng nhà, trẻ nhỏ, thú đang nuôi, dị ứng lông → so với nhu cầu từng bé → '
                'giao bé hợp nếp nhà, hoặc thật lòng hẹn ngày hội sau.')
    tip = {'escape': ' Bé hay trốn: đeo vòng giữ trên bàn trước khi làm.', 'flat': ' Giống mặt ngắn: chỉ sấy nấc mát.',
           'hidden': ' Chủ nói “không sao đâu” thì càng nên đo nhiệt độ.', 'vax_short': ' So hạn sổ tiêm với ngày chủ đón bé.',
           'med': ' Thuốc theo đơn: đúng liều trên nhãn, cho cùng bữa ăn.'}.get(_case(t) or '', '')
    if t.get('regular') is not None:
        tip += ' Khách quen: xem thẻ của bé, gọi tên bé và hỏi thăm lần trước.'
    calm = ('Đọc tín hiệu cơ thể của bé: tai cụp, đuôi kẹp, run là phải dỗ hoặc cho nghỉ; hoảng hẳn thì dừng.' if t.get('gen')
            else 'Stress ≥80 thì dỗ hoặc dừng.')
    return {'groom': 'Kiểm bé trước (cân, lông, da, tai, móng, tính khí) → chải → tắm 36–39°C đúng sữa tắm → xả ≥8 giây → sấy ấm/mát đến khô → '
                     f'tỉa đầu móng đen, lau tai khỏe. {calm} Báo thật với chủ.',
            'board': 'Xem sổ tiêm (bắt buộc), cân bé, xem tính khí và sức khỏe → chuồng đúng khu, đúng cỡ → khẩu phần theo bảng '
                     '(cân nặng × g/kg × giai đoạn ÷ số bữa) → nhận bé. Sổ tiêm hết hạn hoặc bé ho: từ chối, giới thiệu phòng khám.',
            'feed': 'Xem bát tối qua, tinh thần, dáng đi → cho ăn đúng loại và đúng bảng (±10%) → dắt đi dạo có túi nhặt phân / dọn khay cát → '
                    'báo chủ điều bất thường, khuyên đi bác sĩ thú y, không tự chẩn đoán.'}[t['job']] + tip


def content() -> dict:
    return dict(pens=PENS, shampoos=SHAMPOOS, steps=STEPS, temp=TEMP, rinse_min=RINSE_MIN, dry_need=DRY_NEED, dry_over=DRY_OVER,
                stress_stop=STRESS_STOP, chart=CHART, stage_pct=STAGE_PCT, meals=MEALS, tol=TOL, stage_names=STAGE_NAMES,
                species_names=SPECIES_NAMES, parts=PARTS, job_parts=JOB_PARTS, signs=SIGNS, reports=REPORTS, calm=CALM,
                services=SERVICE_NAMES, jobs=JOB_NAMES, allergy_names=ALLERGY_NAMES, house_food=HOUSE_FOOD, vet=VET,
                today=[dict(id=x['id'], title=x['title'], emoji=x['emoji'], text=x['text']) for x in TODAY],
                cases=CASES, bands=MOOD_BANDS, cues=CUES, catch=CATCH, doses=DOSES, adoptees=ADOPTEES, rules=RULES,
                trust_names=TRUST_NAMES, fav_at=FAV_AT, warns=WARNS, remind_early=REMIND_EARLY, remind_late=REMIND_LATE,
                vax_cycle=VAX_CYCLE, worm_cycle=WORM_CYCLE, prices=SPEC['prices'])


def _p(who, emoji, text):
    return dict(who=who, emoji=emoji, text=text)


SITUATIONS = [
    dict(id='PC-S01', title='“Tiêm đủ hết rồi mà!”', npc=1, tone='tense', min_day=1,
         opening='Anh Khoa đặt Bơ lên quầy: “Gửi 3 ngày nha. Sổ tiêm hả? Tiêm đủ hết rồi, sổ để ở quê, tin mình đi!”',
         swap='Bạn là chủ nuôi bận rộn, chuyến xe về quê chạy sau 40 phút nữa.',
         facts=[dict(id='rule', title='Nội quy lưu trú', source='Bảng ở quầy', text='Mọi bé lưu trú phải có sổ tiêm còn hạn (dại + phối hợp). Không có sổ: không nhận.'),
                dict(id='app', title='Ứng dụng phòng khám', source='Anh Khoa mở điện thoại', text='App ' + VET + ' ghi mũi phối hợp của Bơ đã quá hạn 4 tháng.'),
                dict(id='friend', title='Phương án khác', source='Sổ tay của tiệm', text=VET + ' mở tới 20h, tiêm nhắc trong 15 phút. Cô Hạnh hàng xóm nhận trông chó tại nhà.')],
         options=[dict(id='clinic', label='Từ chối nhẹ nhàng, chỉ cho anh Khoa tiêm nhắc ở phòng khám gần đó, giữ chỗ cho Bơ tới 20h', requires=['rule', 'app'], quality='good', stars=5,
                       review='Tưởng bị làm khó, hóa ra được chỉ chỗ tiêm ngay gần, giữ chỗ luôn cho Bơ. Quá xịn!',
                       outcome='Bơ tiêm nhắc lúc 17h, vào chuồng lúc 18h. Anh Khoa bắt chuyến xe sau.',
                       perspectives=[_p('Anh Khoa', '🙇', 'Tui quên thiệt. Cũng may tiệm không nhận bừa.'), _p('Chủ bé Kem (đang gửi)', '🐩', 'Biết tiệm kỹ vậy tôi yên tâm gửi Kem lâu dài.'),
                                     _p('Bác sĩ thú y', '🩺', 'Parvo lây rất nhanh ở nơi đông chó. Sổ tiêm là hàng rào đầu tiên.')]),
                  dict(id='accept', label='Nhận luôn cho vui lòng khách, “chắc không sao đâu”', quality='bad', stars=2, cost=30,
                       review='Gửi chó ở đây xong con tôi bị lây bệnh. Tiệm nhận cả chó chưa tiêm!',
                       outcome='Ngày thứ hai hai bé trong khu chuồng bị tiêu chảy. Tiệm phải khử khuẩn và trả chi phí khám.',
                       perspectives=[_p('Chủ bé Kem', '😡', 'Tôi gửi vì tin tiệm kiểm tra kỹ.'), _p('Anh Khoa', '😬', 'Tui tưởng tiệm linh động giúp tui, ai dè…')]),
                  dict(id='friend', label='Không nhận, giới thiệu cô Hạnh trông tại nhà', requires=['rule', 'friend'], quality='ok', stars=4,
                       review='Không gửi được ở tiệm nhưng có người trông giúp. Ổn.',
                       outcome='Bơ ở nhà cô Hạnh ba ngày, nhưng vẫn chưa được tiêm nhắc.',
                       perspectives=[_p('Anh Khoa', '🙂', 'Có chỗ gửi là mừng rồi.'), _p('Cô Hạnh', '👵', 'Trông giúp được, nhưng con nhớ đi tiêm cho nó nha.')])],
         lesson='Nội quy tiêm phòng bảo vệ mọi bé trong chuồng — từ chối kèm một lối đi rõ ràng.'),
    dict(id='PC-S02', title='Lỡ cắt chạm tủy móng', npc=0, tone='tense', min_day=1,
         opening='Cắt tới móng thứ ba của Bông thì máu rỉ ra. Chị Ngân đang trên đường tới đón, còn 10 phút.',
         facts=[dict(id='first', title='Sơ cứu', source='Hộp sơ cứu', text='Bột cầm máu + ấn nhẹ 30–60 giây. Chạm tủy nhẹ thường tự lành sau vài ngày.'),
                dict(id='policy', title='Chính sách tiệm', source='Sổ quy trình', text='Có sự cố: báo chủ ngay khi trả bé, ghi sổ, không tính tiền phần dịch vụ gặp sự cố.'),
                dict(id='sign', title='Dấu hiệu cần khám', source='Tờ hướng dẫn', text='Nếu máu chảy hơn 10 phút hoặc bé đi khập khiễng hôm sau, chủ nên đưa bé đi bác sĩ thú y.')],
         options=[dict(id='honest', label='Cầm máu, kể thật với chị Ngân, không tính tiền cắt móng, đưa tờ dấu hiệu cần theo dõi', requires=['first', 'policy'], quality='good', stars=4,
                       review='Bé bị chảy máu móng, nhưng em nhân viên nói thật ngay, chỉ cách theo dõi. Tôi vẫn quay lại.',
                       outcome='Tối đó chị Ngân nhắn: “Bông chạy nhảy bình thường rồi em.” Sổ sự cố ghi đủ.',
                       perspectives=[_p('Chị Ngân', '😮‍💨', 'Hơi xót, nhưng được nói thật thì tôi tin tiệm.'), _p('Bạn (thợ tắm)', '✂️', 'Lần sau móng đen chỉ tỉa từng chút đầu móng.'),
                                     _p('Bông', '🐩', 'Gâu! (đã quên từ lúc được ăn bánh)')]),
                  dict(id='hide', label='Lau sạch, đi tất cho bé, không nói gì', quality='bad', stars=1,
                       review='Về nhà thấy vết máu khô ở chân Bông. Tiệm không nói một lời. Không bao giờ quay lại.',
                       outcome='Chị Ngân phát hiện vết máu, đăng bài kể lại. Uy tín tiệm giảm mạnh.',
                       perspectives=[_p('Chị Ngân', '😠', 'Sự cố nhỏ, nhưng giấu mới là chuyện lớn.'), _p('Hàng xóm đọc bài', '📱', 'Tiệm này giấu lỗi à?')]),
                  dict(id='blame', label='Nói thật nhưng đổ tại bé “giãy quá”', requires=['first'], quality='ok', stars=3,
                       review='Có nói nhưng đổ lỗi cho con tôi. Hơi khó chịu.',
                       outcome='Chị Ngân biết chuyện nhưng không vui vì bị đổ lỗi.',
                       perspectives=[_p('Chị Ngân', '😒', 'Bé giãy thì người làm nghề phải biết giữ chứ.'), _p('Chị Mơ (phụ tắm)', '🧼', 'Nhận lỗi đơn giản hơn nhiều.')])],
         lesson='Sự cố nhỏ cần sự thật lớn: sơ cứu, nói thật, không tính tiền phần lỗi.'),
    dict(id='PC-S03', title='Bé sổng chuồng ra đường', npc=3, tone='tense', min_day=2,
         opening='Lúc khách mở cửa, Lu lao vụt ra hẻm. Ngoài kia là đường lớn đang giờ tan tầm.',
         facts=[dict(id='chase', title='Hành vi chó sổng', source='Khóa huấn luyện', text='Đuổi theo làm chó chạy nhanh hơn. Ngồi xuống, gọi tên vui vẻ, lắc túi bánh thì dễ dụ về.'),
                dict(id='chip', title='Thẻ tên', source='Hồ sơ Lu', text='Lu đeo thẻ tên có số của tiệm, chủ là chú Sơn đang đi công tác.'),
                dict(id='door', title='Hai lớp cửa', source='Sơ đồ tiệm', text='Tiệm có cổng phụ nhưng hôm nay chốt bị lỏng.')],
         options=[dict(id='calm', label='Chặn cửa còn lại, một người ngồi xuống gọi tên và lắc túi bánh; báo ngay chú Sơn; sửa chốt cổng', requires=['chase', 'chip'], quality='good', stars=4,
                       review='Lu sổng chuồng nhưng tiệm gọi báo tôi ngay, 5 phút sau đã bắt lại an toàn. Tiệm sửa cổng ngay hôm đó.',
                       outcome='Lu quay lại vì mùi bánh. Chú Sơn nhận cuộc gọi báo ngay và cảm ơn vì được biết sự thật.',
                       perspectives=[_p('Chú Sơn', '📞', 'Nghe tin thì hết hồn, nhưng tôi quý vì được báo ngay.'), _p('Người đi đường', '🛵', 'May là không ai đuổi nó ra giữa đường.'),
                                     _p('Lu', '🐕', 'Ơ, bánh! (quên mất mình đang trốn)')]),
                  dict(id='run', label='Cả tiệm đổ ra đuổi theo, la hét gọi Lu', quality='bad', stars=2, cost=20,
                       review='Chó tôi bị đuổi chạy ra đường lớn, xe suýt tông. Tiệm cần quy trình.',
                       outcome='Lu hoảng chạy ra đường, một xe máy thắng gấp. May không ai bị thương, nhưng Lu trầy chân.',
                       perspectives=[_p('Chú Sơn', '😨', 'Sao lại đuổi một con chó đang hoảng?'), _p('Anh xe máy', '😤', 'Tôi suýt ngã!')]),
                  dict(id='wait', label='Đứng chờ bé tự về, chưa báo chủ vội', quality='bad', stars=2,
                       review='Chó tôi sổng mà hai tiếng sau tiệm mới báo.',
                       outcome='Lu được bà bán nước bắt giúp sau 1 tiếng. Chú Sơn biết chuyện qua camera.',
                       perspectives=[_p('Chú Sơn', '😠', 'Tôi phải tự xem camera mới biết.'), _p('Bà bán nước', '🧃', 'Nó chạy lung tung ngoài chợ cả buổi.')])],
         lesson='Bé sổng: không đuổi, dụ về bằng giọng vui và đồ ăn, báo chủ ngay, sửa chỗ hở.'),
    dict(id='PC-S04', title='Chủ đến muộn 5 tiếng', npc=6, tone='gentle', min_day=2,
         opening='20h tiệm đóng cửa. Anh Duy hẹn đón Xám lúc 17h, không nghe máy, tin nhắn chưa đọc.',
         facts=[dict(id='policy', title='Chính sách trễ hẹn', source='Phiếu gửi', text='Trễ quá 2 tiếng: bé ở lại lưu trú qua đêm, tính phí 1 đêm, có báo trước qua tin nhắn.'),
                dict(id='pen', title='Chuồng trống', source='Sơ đồ chuồng', text='Tầng mèo 2 còn trống, yên tĩnh, xa khu chó.'),
                dict(id='msg', title='Tin nhắn mới', source='Điện thoại', text='21h: “Xin lỗi tiệm, tôi bị kẹt ca mổ ở bệnh viện, mai 7h tôi đến.” (anh Duy là y tá)')],
         options=[dict(id='stay', label='Chuyển Xám vào Tầng mèo 2, nhắn anh Duy phí lưu trú theo phiếu, gửi ảnh Xám ăn tối', requires=['policy', 'pen'], quality='good', stars=5,
                       review='Kẹt ca trực mà tiệm lo cho Xám chu đáo, gửi cả ảnh. Phí đúng như phiếu ghi.',
                       outcome='Xám ngủ ngon trong tầng mèo. Sáng anh Duy đến, cảm ơn và thanh toán đúng phí.',
                       perspectives=[_p('Anh Duy', '😮‍💨', 'Tôi lo nhất là Xám đói. Thấy ảnh là yên tâm.'), _p('Bé Thư (chăm chuồng)', '🧹', 'Làm đúng phiếu nên không ai khó xử.')]),
                  dict(id='door', label='Để Xám trong lồng trước cửa tiệm, dán giấy nhắn', quality='bad', stars=1, cost=10,
                       review='Tôi đến thì thấy mèo mình trong lồng ngoài hiên cả đêm. Không thể chấp nhận.',
                       outcome='Xám hoảng loạn cả đêm ngoài trời lạnh, sáng ra bỏ ăn.',
                       perspectives=[_p('Anh Duy', '😡', 'Đó là một sinh mạng, không phải gói hàng.'), _p('Bảo vệ khu phố', '🔦', 'Nửa đêm nghe mèo kêu thảm thiết.')]),
                  dict(id='fine', label='Giữ lại nhưng tính phí phạt gấp ba', requires=['policy'], quality='ok', stars=3,
                       review='Mèo được giữ an toàn, nhưng phí phạt cao hơn phiếu ghi.',
                       outcome='Anh Duy trả tiền nhưng không vui vì phí không đúng như đã ký.',
                       perspectives=[_p('Anh Duy', '😕', 'Tôi sai vì đến trễ, nhưng phí phải như phiếu chứ.'), _p('Chủ tiệm', '🧮', 'Làm đúng phiếu thì khách mới quay lại.')])],
         lesson='Chủ trễ hẹn: an toàn của bé trước, phí đúng như đã thỏa thuận, báo tin thường xuyên.'),
    dict(id='PC-S05', title='Mèo con đi lạc', npc=4, tone='gentle', min_day=1,
         opening='Bé Na ôm một bé mèo con gầy nhom, mắt kèm nhèm: “Con nhặt ở bãi xe, cô chú cứu bé với!”',
         facts=[dict(id='quarantine', title='Cách ly', source='Quy trình tiệm', text='Thú chưa rõ bệnh phải cách ly, không cho gần khu lưu trú. Dùng lồng riêng, găng tay riêng.'),
                dict(id='rescue', title='Nhóm cứu hộ', source='Bảng tin', text='Nhóm Cứu Hộ Mèo Mây nhận mèo lạc, đưa đi khám và tìm nhà mới.'),
                dict(id='vet', title='Mèo con mắt kèm nhèm', source='Tờ hướng dẫn', text='Mèo con chảy ghèn mắt cần bác sĩ thú y khám; không tự nhỏ thuốc người.')],
         options=[dict(id='care', label='Cho mèo con vào lồng cách ly, sưởi ấm, gọi nhóm cứu hộ đưa đi khám; rủ Na cùng theo dõi', requires=['quarantine', 'rescue'], quality='good', stars=5, cost=8,
                       review='Tiệm giúp mèo con rất tận tình, còn dạy con tôi cách cứu mèo đúng cách.',
                       outcome='Mèo con được nhóm cứu hộ đưa đi khám, hai tuần sau có nhà mới. Na được gửi ảnh bé mèo khỏe mạnh.',
                       perspectives=[_p('Bé Na', '🥹', 'Con được đặt tên cho bé là Bánh Bèo!'), _p('Nhóm cứu hộ', '🐾', 'Được cách ly sớm nên không lây cho ai.'),
                                     _p('Mẹ bé Na', '👩', 'Con bé học được cách giúp mà không liều.')]),
                  dict(id='mix', label='Thả mèo con vào tầng mèo lưu trú cho có bạn', quality='bad', stars=1, cost=25,
                       review='Mèo tôi gửi bị lây viêm mắt từ một con mèo lạc. Tiệm quá ẩu.',
                       outcome='Hai bé mèo lưu trú bị lây viêm kết mạc, phải đi khám.',
                       perspectives=[_p('Cô Hạnh (chủ Mướp)', '😢', 'Mướp già rồi, lây bệnh là mệt lắm.'), _p('Bé Na', '😟', 'Con chỉ muốn cứu bé thôi…')]),
                  dict(id='away', label='Bảo Na mang về, tiệm không nhận mèo lạc', quality='ok', stars=2,
                       review='Con tôi khóc vì bị từ chối, cũng không được chỉ chỗ nào giúp.',
                       outcome='Na mang mèo con về, mẹ phải tự tìm phòng khám.',
                       perspectives=[_p('Bé Na', '😭', 'Không ai giúp bé mèo hết.'), _p('Mẹ bé Na', '😕', 'Chỉ cần một số điện thoại thôi mà.')])],
         lesson='Cứu thú lạc: cách ly trước, chuyển tới người có chuyên môn, và đừng để lòng tốt thành nguy cơ.'),
    dict(id='PC-S06', title='“Cho nó uống thuốc ngủ đi em”', npc=5, tone='tense', min_day=1,
         opening='Bà Tư chìa vỉ thuốc ngủ của bà: “Thằng Vện dữ lắm, cháu cho nó uống nửa viên rồi tắm cho dễ.”',
         facts=[dict(id='law', title='Thuốc cho thú', source='Quy định nghề', text='Tiệm cắt tỉa không được cho thú uống thuốc an thần; chỉ bác sĩ thú y kê và theo dõi.'),
                dict(id='danger', title='Thuốc người cho chó', source='Tài liệu bác sĩ thú y', text='Nhiều thuốc ngủ của người gây ngộ độc, tụt huyết áp ở chó.'),
                dict(id='plan', title='Kế hoạch ít stress', source='Sổ tay thợ', text='Chia buổi ngắn, rọ mõm mềm có đồng ý của chủ, cho bé làm quen bàn tắm trước.')],
         options=[dict(id='refuse', label='Từ chối cho thuốc; đề nghị bà hỏi bác sĩ thú y, hôm nay làm buổi ngắn với rọ mõm mềm nếu bà đồng ý', requires=['law', 'plan'], quality='good', stars=5,
                       review='Cháu nó không chịu cho thuốc, lại có cách tắm cho thằng Vện êm ru. Được!',
                       outcome='Vện chỉ tắm và chải hôm nay, cắt móng hẹn buổi sau. Bà Tư hỏi bác sĩ thú y về cách giúp Vện bớt sợ.',
                       perspectives=[_p('Bà Tư', '👵', 'Bà cứ tưởng thuốc của bà dùng được cho chó.'), _p('Bác sĩ thú y', '🩺', 'Suýt nữa là ca cấp cứu ngộ độc.'),
                                     _p('Vện', '🐕', 'Gừ… (nhưng đã chịu đứng yên)')]),
                  dict(id='pill', label='Cho uống nửa viên như bà dặn', quality='bad', cost=40,
                       outcome='Vện lừ đừ, thở chậm, phải đưa đi cấp cứu. Tiệm chịu chi phí và bị nhắc nhở.',
                       perspectives=[_p('Bà Tư', '😱', 'Bà đâu biết nó nguy hiểm vậy!'), _p('Bác sĩ thú y', '🚑', 'Thuốc người không phải thuốc chó.')]),
                  dict(id='no', label='Từ chối cả thuốc lẫn dịch vụ: “Chó dữ tiệm không nhận”', requires=['law'], quality='ok', stars=2,
                       review='Không cho thuốc thì thôi, còn đuổi cả bà với con chó.',
                       outcome='Vện không được tắm, bà Tư tự tắm ở nhà và bị cắn nhẹ.',
                       perspectives=[_p('Bà Tư', '😤', 'Vậy ai tắm cho nó?'), _p('Chị Mơ (phụ tắm)', '🧼', 'Chó sợ vẫn tắm được, chỉ cần cách khác.')])],
         lesson='Không bao giờ cho thú uống thuốc thay bác sĩ; giảm stress bằng cách làm, không bằng thuốc.'),
    dict(id='PC-S07', title='Hai bé đánh nhau ở sân chơi', npc=5, tone='tense', min_day=2,
         opening='Giờ chơi chung, Vện và Kem lao vào nhau, tiếng gầm vang cả tiệm.',
         facts=[dict(id='hands', title='Tách chó đánh nhau', source='Khóa huấn luyện', text='Không thò tay vào giữa. Dùng tấm chắn, dội nước, hoặc hai người kéo chân sau cùng lúc.'),
                dict(id='file', title='Ghi chú lưu trú', source='Hồ sơ Vện', text='Lúc nhận: “Vện hiền với người nhưng ghét chó khác — nên chơi riêng.” Ai đó đã bỏ qua.'),
                dict(id='wound', title='Vết thương', source='Kiểm tra sau', text='Kem có vết răng nhỏ ở tai, đã cầm máu. Vết cắn nên được bác sĩ thú y xem.')],
         options=[dict(id='safe', label='Tách bằng tấm chắn, kiểm tra vết thương, báo thật cả hai chủ, đưa Kem đi khám, từ nay Vện chơi riêng', requires=['hands', 'wound'], quality='good', stars=4, cost=15,
                       review='Có sự cố, nhưng tiệm báo ngay, đưa Kem đi khám, nhận trách nhiệm. Tôi thấy tin được.',
                       outcome='Kem được khám và khâu một mũi nhỏ. Tiệm sửa quy trình: đọc ghi chú trước giờ chơi.',
                       perspectives=[_p('Chị Ngân (chủ Kem)', '😟', 'Buồn, nhưng tôi được biết mọi thứ.'), _p('Bà Tư', '😔', 'Bà đã dặn mà, nhưng tiệm nhận lỗi đàng hoàng.'),
                                     _p('Bé Thư (chăm chuồng)', '🧹', 'Em sẽ đọc thẻ trước mỗi giờ chơi.')]),
                  dict(id='hand', label='Lao vào kéo bằng tay không', quality='bad', stars=2, cost=20,
                       review='Hai con chó đánh nhau, nhân viên bị cắn, sau đó mới báo cho tôi.',
                       outcome='Nhân viên bị cắn vào tay phải đi tiêm phòng. Kem vẫn bị thương.',
                       perspectives=[_p('Nhân viên', '🤕', 'Phản xạ thôi, nhưng giờ tay tôi băng kín.'), _p('Chị Ngân', '😠', 'Không có quy trình gì à?')]),
                  dict(id='silent', label='Tách xong, lau vết máu, không báo chủ', quality='bad', stars=1,
                       review='Đón Kem về mới phát hiện vết cắn ở tai. Tiệm giấu tôi.',
                       outcome='Vết cắn bị nhiễm trùng vì không được khám sớm.',
                       perspectives=[_p('Chị Ngân', '😡', 'Sự cố thì có thể xảy ra, giấu thì không.'), _p('Kem', '🐩', 'Ư ử… tai đau quá.')])],
         lesson='Đọc ghi chú tính khí, tách chó bằng dụng cụ không bằng tay, và nói thật với mọi chủ nuôi.'),
    dict(id='PC-S08', title='Cắt kiểu sư tử cho mèo già', npc=2, tone='gentle', min_day=3,
         opening='Cô Hạnh muốn cạo kiểu “sư tử” cho Mướp 12 tuổi cho mát. Mướp run bần bật trên bàn, thở nhanh.',
         swap='Bạn là chủ mèo già, thấy hình mèo cắt kiểu sư tử trên mạng rất dễ thương.',
         facts=[dict(id='stress', title='Stress của Mướp', source='Quan sát', text='Mướp thở há miệng, đồng tử giãn — dấu hiệu hoảng rất cao ở mèo.'),
                dict(id='skin', title='Da mèo già', source='Tài liệu thợ', text='Da mèo già mỏng, dễ trầy khi cạo sát; cạo toàn thân mất nhiều thời gian giữ bé.'),
                dict(id='option', title='Phương án nhẹ', source='Bảng dịch vụ', text='Tỉa vệ sinh (bụng, đùi sau) + chải gỡ rối, chia hai buổi ngắn. Nếu cần cạo toàn thân: làm tại phòng khám có bác sĩ theo dõi.')],
         options=[dict(id='gentle', label='Dừng lại, giải thích cho cô Hạnh; hôm nay chỉ tỉa vệ sinh ngắn, hẹn buổi hai; muốn cạo toàn thân thì làm ở phòng khám', requires=['stress', 'option'], quality='good', stars=5,
                       review='Cháu nó thương Mướp như mèo nhà. Tỉa nhẹ thôi mà Mướp mát, không hoảng nữa.',
                       outcome='Mướp tỉa vệ sinh trong 10 phút, về nhà ăn ngon. Cô Hạnh đổi ý không cạo toàn thân.',
                       perspectives=[_p('Cô Hạnh', '🥰', 'Cô chỉ muốn Mướp mát, không muốn bé sợ.'), _p('Chị Mơ (phụ tắm)', '🧼', 'Biết dừng đúng lúc là tay nghề.'),
                                     _p('Mướp', '🐈', 'Meo… (ngủ ngay trên đường về)')]),
                  dict(id='force', label='Giữ chặt, cạo cho xong kiểu sư tử như khách yêu cầu', quality='bad', stars=2, cost=20,
                       review='Mướp về nhà trốn gầm giường hai ngày, da có vết trầy. Tôi hối hận.',
                       outcome='Mướp bị trầy da, stress, bỏ ăn một ngày.',
                       perspectives=[_p('Cô Hạnh', '😢', 'Đẹp đâu chẳng thấy, chỉ thấy con sợ.'), _p('Bác sĩ thú y', '🩺', 'Mèo già stress kéo dài rất hại tim.')]),
                  dict(id='refuse', label='Từ chối làm, trả bé về', requires=['stress'], quality='ok', stars=3,
                       review='Không cắt được, nhưng ít ra tiệm không ép Mướp.',
                       outcome='Mướp về nhà vẫn rối lông ở bụng, cô Hạnh chưa biết làm sao.',
                       perspectives=[_p('Cô Hạnh', '😕', 'Vậy lông rối của Mướp tính sao đây?'), _p('Mướp', '🐈', 'Hừ.')])],
         lesson='Phúc lợi của thú trước kiểu tóc: dừng khi bé hoảng, đề xuất cách nhẹ hơn.'),
]

# ---------------------------------------------------------------- surprises at the counter (kit desk engine)
DESK = [
    dict(id='storm', title='Giông lớn, cả khu chuồng hoảng', emoji='⛈️', npc=3, min_day=2, tone='tense', weight=2,
         text='Sấm nổ liên hồi, mấy bé lưu trú sủa, run, cào cửa chuồng. Chú Sơn nhắn hỏi Ki có sao không.',
         options=[dict(id='stay', label='Kéo rèm, bật nhạc êm, ngồi với các bé; gửi chú Sơn ảnh Ki', hint='Khách đang chờ mất kiên nhẫn một chút',
                       effects=dict(patience=-8, review=[5, 'Giông to mà tiệm ngồi với Ki, gửi ảnh liền. Yên tâm ghê.']), good=True,
                       outcome='Các bé dịu dần theo tiếng nhạc. Chú Sơn thả tim ảnh Ki ngủ gục trên chăn.'),
                  dict(id='close', label='Đóng cửa kho, để các bé tự quen', effects=dict(review=[2, 'Ki về nhà giật mình mỗi khi có tiếng động.']),
                       good=False, outcome='Tiếng cào cửa kéo dài cả tiếng. Một bé tự cắn chân tới trầy.'),
                  dict(id='pill', label='Xin thuốc an thần của người cho các bé ngủ', hint='−30 xu', effects=dict(money=-30, review=[1, 'Tiệm cho chó uống thuốc của người!']),
                       good=False, outcome='Một bé lừ đừ, thở chậm, phải chở đi khám gấp. Thuốc người không phải thuốc thú.')],
         default='close'),
    dict(id='stray', title='Mèo con lạc trước cửa', emoji='🐈', npc=15, min_day=2, tone='gentle', weight=2,
         text='Một bé mèo con gầy nhom, mắt kèm nhèm, nằm co trong hộp giấy trước cửa tiệm.',
         options=[dict(id='rescue', label='Cho vào lồng cách ly, sưởi ấm, gọi nhóm cứu hộ đưa đi khám', hint='−6 xu', effects=dict(money=-6, xp=10),
                       good=True, outcome='Chị Mây tới đón bé đi khám. Tuần sau bé có tên là Bánh Bèo và một mái nhà.'),
                  dict(id='mix', label='Thả lên tầng mèo lưu trú cho có bạn', effects=dict(mark='stray_mix'), good=False,
                       outcome='Mèo con được sưởi ấm, ăn ngon. Các bé mèo lưu trú xúm lại ngửi ngửi…'),
                  dict(id='away', label='Đặt hộp ra xa, tiệm không nhận mèo lạc', effects=dict(review=[2, 'Thấy mèo con lạc mà tiệm làm ngơ.']),
                       good=False, outcome='Chiều đó hàng xóm chụp ảnh hộp mèo con, đăng nhóm cư dân.')],
         default='away'),
    dict(id='sneeze', title='Tầng mèo hắt hơi hàng loạt', emoji='🤧', npc=2, min_day=2, need_mark='stray_mix', tone='tense',
         text='Từ hôm có mèo con lạc, ba bé mèo lưu trú chảy nước mắt, hắt hơi liên tục. Cô Hạnh gọi hỏi Mướp ăn uống sao rồi.',
         options=[dict(id='vet', label='Mời bác sĩ khám cả tầng, báo thật từng chủ', hint='−25 xu', effects=dict(money=-25, unmark='stray_mix',
                       review=[4, 'Tiệm báo thật và mời bác sĩ ngay. Lần sau cách ly kỹ hơn nha.']), good=True,
                       outcome='Bác sĩ kê thuốc nhỏ mắt, các bé khỏi sau năm ngày. Tiệm mua thêm lồng cách ly.'),
                  dict(id='hide', label='Lau dọn, không nói với ai', effects=dict(unmark='stray_mix', review=[1, 'Mèo tôi về nhà viêm mắt, tiệm im re.']),
                       good=False, outcome='Cô Hạnh đón Mướp, thấy mắt bé sưng đỏ. Cô không gửi nữa.')],
         default='hide'),
    dict(id='rep', title='Đại lý mời sữa tắm không nhãn', emoji='🧴', npc=14, min_day=2, no_mark='no_label', tone='gentle',
         text='Chị Diễm mở thùng sữa tắm: “Hàng xách tay, không nhãn phụ, giá bằng một nửa. Lấy thử sáu chai đi em!”',
         options=[dict(id='decline', label='Cảm ơn, tiệm chỉ nhập hàng có nhãn, có hạn dùng', good=True, effects=dict(xp=6),
                       outcome='Chị Diễm bĩu môi rồi đi. Kệ sữa tắm của tiệm vẫn đủ nhãn, đủ hạn.'),
                  dict(id='buy', label='Lấy sáu chai giá rẻ', hint='−3 xu · +6 chai', effects=dict(money=-3, stock={'sh_normal': 6}, mark='no_label'),
                       good=None, outcome='Sáu chai không nhãn lên kệ. Mùi thơm hơi gắt.')],
         default='decline'),
    dict(id='itch', title='Chủ báo bé nổi mẩn sau khi tắm', emoji='😣', npc=0, min_day=2, need_mark='no_label', tone='tense',
         text='Chị Ngân gửi ảnh: bụng Bông nổi mẩn đỏ sau lần tắm hôm trước ở tiệm, bé gãi suốt đêm.',
         options=[dict(id='own', label='Nhận lỗi, hoàn tiền, hủy hết sữa tắm không nhãn', hint='−18 xu', effects=dict(money=-18, stock={'sh_normal': -6},
                       unmark='no_label', review=[4, 'Tiệm nhận lỗi, hoàn tiền, bỏ luôn lô sữa tắm lạ. Tôi vẫn tin.']), good=True,
                       outcome='Bông đỡ ngứa sau hai ngày. Kệ sữa tắm chỉ còn hàng có nhãn.'),
                  dict(id='deny', label='Chối: chắc bé dị ứng thứ gì khác', effects=dict(unmark='no_label', review=[1, 'Bé nổi mẩn mà tiệm chối phăng.']),
                       good=False, outcome='Chị Ngân kể chuyện trong nhóm nuôi chó. Tuần đó lịch tắm vắng hẳn.')],
         default='deny'),
    dict(id='inspect', title='Thú y phường kiểm tra vệ sinh chuồng', emoji='🩺', npc=13, min_day=3, tone='tense',
         text='Bác sĩ Hòa đưa phiếu kiểm tra: “Cho xem sổ khử khuẩn chuồng trại hôm nay.”',
         options=[dict(id='log', label='Đưa sổ khử khuẩn hôm nay', effects=dict(inspect=True), good=None,
                       outcome='Bác sĩ Hòa lật từng trang.'),
                  dict(id='clean', label='Xin mười phút khử khuẩn ngay rồi mời kiểm', hint='Khách chờ lâu hơn', effects=dict(patience=-10, sanitize=True, inspect=True),
                       good=True, outcome='Bạn phun khử khuẩn chuồng, ngâm lược kéo, ký sổ trước mặt bác sĩ.'),
                  dict(id='gift', label='Mời nước, xin “thông cảm” cho qua', luck=dict(
                      p=0.3, win=dict(outcome='Bác sĩ Hòa lắc đầu, nhắc lần sau phải đủ sổ.', good=None),
                      lose=dict(effects=dict(money=-20, review=[2, 'Tiệm thú cưng bị phạt vì vệ sinh chuồng.']), outcome='Bác sĩ Hòa từ chối, lập biên bản phạt.',
                                good=False)))],
         default='log'),
    dict(id='outage', title='Cúp điện cả dãy phố', emoji='🔌', npc=5, min_day=2, at='any', tone='tense',
         text='Máy sấy tắt phụt, quạt chuồng ngừng quay. Điện lực báo hai tiếng nữa mới có lại.',
         options=[dict(id='gen', label='Thuê máy phát của tiệm bên', hint='−10 xu', effects=dict(money=-10), good=True,
                       outcome='Máy phát nổ giòn, máy sấy chạy lại, chuồng có quạt.'),
                  dict(id='towel', label='Lau khăn thật kỹ, mở cửa thông gió, chờ có điện', hint='Khách chờ lâu hơn', effects=dict(patience=-12), good=None,
                       outcome='Các bé được lau khô bằng khăn, nằm chỗ thoáng. Khách phải chờ khá lâu.'),
                  dict(id='wet', label='Trả bé luôn dù lông còn ẩm', effects=dict(review=[2, 'Bé về nhà lông còn ẩm, hôm sau nổi nấm da.']), good=False,
                       outcome='Chủ ôm bé về, lông ẩm bết. Ba hôm sau bé nổi nấm.')],
         default='towel'),
    dict(id='yard', title='Hai bé gầm gừ ở sân chơi', emoji='🐕', npc=5, min_day=2, tone='tense',
         text='Giờ chơi chung, hai bé lưu trú dựng lông, gầm gừ, chỉ chực lao vào nhau.',
         options=[dict(id='board', label='Chắn tấm ván giữa hai bé, dắt từng bé về chuồng riêng', effects=dict(xp=6), good=True,
                       outcome='Tấm ván chắn tầm nhìn, hai bé dịu lại. Từ nay giờ sân chia ca.'),
                  dict(id='hands', label='Thò tay kéo hai bé ra', hint='−15 xu', effects=dict(money=-15, review=[2, 'Chó đánh nhau, nhân viên bị cắn, tiệm không có quy trình.']),
                       good=False, outcome='Bạn bị cắn trúng cổ tay, phải đi tiêm phòng.'),
                  dict(id='watch', label='Đứng xem, chắc tụi nó giỡn', effects=dict(review=[1, 'Chó tôi bị cắn rách tai ở sân chơi của tiệm.']), good=False,
                       outcome='Hai bé lao vào nhau. Một bé rách tai.')],
         default='watch'),
    dict(id='night', title='Chủ gọi video lúc 22 giờ', emoji='📱', npc=6, min_day=2, at='open', tone='gentle',
         text='Tối qua anh Duy gọi video ba lần, muốn xem Xám ngủ chưa. Sáng nay anh nhắn hỏi sao không ai bắt máy.',
         options=[dict(id='answer', label='Gọi lại ngay, mở camera chuồng cho anh xem Xám; từ nay hẹn giờ gọi', hint='Khách chờ lâu hơn một chút',
                       effects=dict(patience=-5, review=[5, 'Tiệm gọi lại liền, cho xem Xám ngủ ngon. Còn hẹn giờ gọi mỗi tối nữa.']), good=True,
                       outcome='Anh Duy thấy Xám cuộn tròn ngủ, thở phào. Tiệm lập giờ gọi video 20h mỗi tối.'),
                  dict(id='photo', label='Nhắn xin lỗi, gửi ảnh Xám ăn sáng', good=None, effects=dict(xp=3),
                       outcome='Anh Duy thả tim, nhưng vẫn hơi lo.'),
                  dict(id='ignore', label='Không trả lời, việc sáng còn nhiều', effects=dict(review=[2, 'Gửi mèo mà gọi không ai nghe.']), good=False,
                       outcome='Anh Duy chạy tới tiệm lúc 7h sáng, mặt đầy lo lắng.')],
         default='ignore'),
    dict(id='lost', title='Chó lạc đeo vòng cổ, không số điện thoại', emoji='🏷️', npc=5, min_day=3, tone='gentle',
         text='Bà Tư dắt vào một bé chó lông xù, vòng cổ đẹp nhưng không có số điện thoại: “Nó lang thang đầu hẻm từ sáng.”',
         options=[dict(id='chip', label='Đưa tới phòng khám quét chip tìm chủ', hint='−5 xu', effects=dict(money=-5, xp=12,
                       review=[5, 'Tiệm quét chip tìm được chủ cho con chó lạc. Tử tế ghê!']), good=True,
                       outcome='Chip hiện số của chủ ở phường bên. Chiều đó cậu chủ nhỏ ôm bé khóc nức nở.'),
                  dict(id='post', label='Giữ bé ở lồng cách ly, đăng nhóm cư dân', hint='Bận thêm một chút', effects=dict(patience=-6), good=None,
                       outcome='Hai ngày sau mới có người nhận.'),
                  dict(id='keep', label='Giữ luôn, ai hỏi thì tính', effects=dict(review=[1, 'Tiệm giữ chó lạc của người ta không trả.']), good=False,
                       outcome='Chủ bé tìm tới qua ảnh camera, to tiếng ngay trước quầy.')],
         default='post'),
    dict(id='kol', title='Người có tiếng xin tắm miễn phí', emoji='📸', npc=1, min_day=3, tone='gentle',
         text='Anh Khoa dẫn theo một bạn làm video thú cưng hai trăm nghìn người theo dõi: “Tắm miễn phí cho con Corgi này, bạn ấy đăng bài cho tiệm!”',
         options=[dict(id='deal', label='Giảm 30%, ghi rõ “có hợp tác” khi đăng', hint='+10 xu', effects=dict(money=10, xp=6), good=True,
                       outcome='Video ghi rõ hợp tác, người xem khen tiệm minh bạch.'),
                  dict(id='free', label='Làm miễn phí đổi bài đăng', luck=dict(
                      p=0.5, win=dict(effects=dict(review=[5, 'Xem video xong tôi đặt lịch liền!']), outcome='Video nổi, tuần sau lịch tắm kín.', good=True),
                      lose=dict(effects=dict(review=[3, 'Video quảng cáo mà không ghi hợp tác.']), outcome='Video bị chê giấu quảng cáo.', good=False))),
                  dict(id='refuse', label='Cảm ơn, tiệm làm giá như mọi khách', good=None, outcome='Bạn ấy gật đầu, hẹn khi nào cần sẽ đặt lịch.')],
         default='refuse'),
    dict(id='return', title='Bé nhận nuôi bị mang trả', emoji='💔', npc=15, min_day=3, need_mark='adopt_bad', tone='tense',
         text='Chị Mây gọi: “Gia đình nhận bé hôm trước vừa mang bé trả lại nhóm, nói bé không hợp nếp nhà. Tiệm tư vấn sao vậy em?”',
         options=[dict(id='take', label='Nhận lỗi, hoàn phí cho gia đình, ghi rõ nếp nhà để lần sau hỏi kỹ', hint='−20 xu',
                       effects=dict(money=-20, unmark='adopt_bad', returned=1,
                                    review=[3, 'Bé không hợp, nhưng tiệm nhận lỗi và hoàn phí đàng hoàng.']), good=True,
                       outcome='Bé về lại nhóm cứu hộ, được chăm kỹ chờ nhà mới. Phiếu phỏng vấn nhận nuôi in thêm năm câu hỏi bắt buộc.'),
                  dict(id='refuse', label='Không nhận trách nhiệm: “giao rồi là xong”', effects=dict(unmark='adopt_bad', returned=1,
                       review=[1, 'Tư vấn ẩu, bé bị trả mà tiệm phủi tay.']),
                       good=False, outcome='Chị Mây im lặng một lúc lâu. Nhóm cứu hộ tạm ngưng gửi bé qua tiệm.')],
         default='refuse'),
    dict(id='heat', title='Chó lớn thở dốc ngoài hiên', emoji='🥵', npc=3, min_day=2, mods=('heat',), at='any', tone='tense',
         text='Giữa trưa nắng, bé Ki nằm bẹp ngoài hiên, thở dốc, lưỡi đỏ sậm.',
         options=[dict(id='shade', label='Đưa vào chỗ mát, cho uống nước từng ngụm, lau khăn ẩm', good=True, effects=dict(xp=6),
                       outcome='Mười phút sau Ki thở đều, ngóc đầu xin bánh.'),
                  dict(id='ice', label='Dội nước đá cho mau mát', effects=dict(review=[2, 'Chó say nắng mà tiệm dội nước đá.']), good=False,
                       outcome='Ki run bắn vì lạnh đột ngột, phải đưa đi khám.'),
                  dict(id='leave', label='Để yên, chiều mát là khỏe', effects=dict(review=[1, 'Chó tôi bị say nắng ở tiệm.']), good=False,
                       outcome='Ki lả đi, phải chở đi cấp cứu.')],
         default='leave'),
    dict(id='lonely', title='Bé lưu trú bỏ ăn đêm đầu', emoji='🌙', npc=2, min_day=2, at='open', tone='gentle',
         text='Sáng ra bát của bé mèo mới gửi còn nguyên. Bé nằm quay mặt vào tường cả đêm.',
         options=[dict(id='shirt', label='Xin chủ gửi áo cũ có mùi, ngồi đút tay từng hạt', hint='Bận thêm một chút',
                       effects=dict(patience=-6, review=[5, 'Tiệm xin áo cũ của tôi cho bé đỡ nhớ nhà. Chu đáo quá!']), good=True,
                       outcome='Có mùi áo chủ, bé chịu ăn nửa bát, chiều ra ngồi cửa sổ.'),
                  dict(id='pate', label='Đổi sang pate thơm cho ăn bằng được', hint='−4 xu', effects=dict(money=-4), good=None,
                       outcome='Bé liếm vài miếng pate, nhưng vẫn buồn.'),
                  dict(id='wait', label='Để bé tự ăn khi đói', effects=dict(review=[3, 'Mèo tôi bỏ ăn hai ngày mà tiệm không báo.']), good=False,
                       outcome='Bé nhịn tới tối hôm sau. Mèo nhịn ăn lâu rất dễ bệnh gan.')],
         default='wait'),
]
DESK_INDEX = {x['id']: x for x in DESK}

SPEC = dict(
    id=ID, prefix='pc_', category='service',
    meta=dict(short='Chăm sóc thú cưng', place='Pet Care Mèo Mập', tagline='Tắm thơm, sấy ấm, không để bé nào sợ.', icon='paw',
              color='#c07a5a', light='#fbeee6', weather='Nắng nhẹ 29°C', work='Bé cưng', station='Bàn tắm tỉa',
              greeting='Kiểm bé trước khi làm, giữ bé bình tĩnh, và luôn nói thật với chủ nhé.',
              caption='Tiệm nhỏ đầu hẻm, tiếng máy sấy rì rì cả ngày', map_label='14 · PET CARE MÈO MẬP'),
    people=PEOPLE,
    staff=[('Chị Mơ', 'bather', 'Tắm sấy khéo, nói chuyện với chó như với em bé.', 78, 90),
           ('Bé Thư', 'kennel', 'Thương mèo, dọn chuồng sạch bong, nhớ tên từng bé.', 82, 86),
           ('Anh Lộc', 'front', 'Đọc sổ tiêm nhanh, giải thích nội quy nhẹ nhàng.', 84, 88),
           ('Tí Nị', 'kennel', 'Chạy bộ giỏi, dắt chó lớn đi dạo không mệt.', 90, 74)],
    roles={'bather': 'Phụ tắm sấy', 'kennel': 'Chăm chuồng', 'front': 'Lễ tân'},
    inventory=dict(items=ITEMS, capacity=40),
    prices={'groom_s': 18, 'groom_m': 24, 'groom_l': 32, 'groom_cat': 22, 'brush': 8, 'nails': 6, 'ears': 5,
            'board_dog': 20, 'board_cat': 16, 'care': 6, 'adopt': 20},
    tip=2,
    physical=('pc_bath', 'pc_nails', 'pc_ears', 'pc_walk', 'pc_admit', 'pc_handover'),
    free_actions=(),
    no_tick=('pc_report', 'pc_plan', 'pc_pen', 'pc_desk', 'pc_greet', 'pc_remind', 'pc_follow'),
    waste_items=(),
    activity=('🐾', 'Tiệm thú cưng ngăn nắp', [('Sữa tắm cún con', 'Kệ sữa tắm'), ('Bột cầm máu', 'Hộp sơ cứu'), ('Hạt cho mèo', 'Tủ thức ăn'), ('Túi nhặt phân', 'Móc dây dắt')],
              ['Chải gỡ rối', 'Tắm nước ấm, xả sạch', 'Sấy ấm tới chân lông', 'Tỉa móng, lau tai']),
    stories=[('Nỗi sợ bồn tắm của Vện', ('Bà Tư bảo thằng Vện “chưa ai tắm nổi”. Lần nào tới tiệm nó cũng gầm gừ từ ngoài cổng.',
                                         'Bạn cho Vện làm quen bàn tắm mỗi ngày năm phút: chỉ ngửi, ăn một miếng, rồi về. Không tắm gì cả.',
                                         'Tuần thứ ba, Vện tự nhảy lên bàn. Bà Tư đứng xem, lần đầu tiên bà nói: “Giỏi.”')),
             ('Cuốn sổ của Bé Na', ('Bé Na ghi chép mọi thứ về Mochi vào một cuốn sổ hồng: ăn gì, ngủ mấy tiếng, sợ tiếng gì.',
                                   'Bạn chỉ Na cách đọc bảng khẩu phần và nhận biết khi mèo sợ: tai cụp, đuôi quấn.',
                                   'Cuốn sổ của Na được photo làm “Sổ tay chủ nuôi nhí”, tiệm tặng mỗi bé mèo con lần đầu đến.')),
             ('Mướp và cái cửa sổ', ('Mướp 12 tuổi lưu trú lần đầu, cả ngày nằm quay mặt vào tường, bỏ nửa bát ăn.',
                                    'Bạn để ý Mướp chỉ ngóc đầu khi có nắng. Bạn dời Mướp sang tầng có cửa sổ, đặt chiếc khăn có mùi cô Hạnh.',
                                    'Chiều hôm đó Mướp ăn hết bát. Tầng mèo view cửa sổ trở thành chỗ đặt trước của các bé lớn tuổi.'))],
    review_asides=['Giờ bé nhà tôi thấy cổng tiệm là vẫy đuôi 🐾', 'Tiệm gửi ảnh bé mỗi ngày, xem mà thương muốn xỉu.',
                   'Phiếu ghi rõ từng việc, tôi yên tâm gửi gắm.', 'Nhân viên nói chuyện với bé còn dịu dàng hơn cả tôi.'],
    situations=SITUATIONS,
    guide='Kiểm bé → chải → tắm đúng nhiệt độ, đúng sữa tắm → xả sạch → sấy ấm → tỉa móng, lau tai → báo thật với chủ.',
)
