"""🏠 Chuyện nhà thuê (feedback #261): authored content only (rules in game/tenancy.py).

Two sides of renting, light and mostly happy, each with two choices:
* THUE: you rent (Bà Tám's attic, the Phòng trọ khép kín, a home leased from another player): the landlord, the
  neighbours next door, a room that loses its power, a neighbour moving out.
* CHU: you let a home you own (game/housing.py jr_home_let): your tenant pays late, the power breaks, they think
  about moving out, a quarrel with the house next door, a plate of food, an invitation to eat together.

Text tokens: {chu} the landlord (LANDLORDS), {khach} your tenant (housing.TENANTS), {nha} the home they rent from you,
{anh} how a younger person calls you (life_content.TOKENS). `who`: 'chu' (the landlord), 'khach' (your tenant), a
neighbour of the journey CAST, or a one-off person (`person`: name, emoji, role). Each choice moves tinh thần by at
most 4, the wallet by a few xu, `bond` the closeness with `who` (and `also` with other neighbours). The default (taken
when the card is left until the next life day) never costs xu. `landlord`: the card names the landlord, so it never
comes while you rent from another player (they did not say any of it). Ids are stored in saves: append only.
"""
from __future__ import annotations


def C(cid: str, label: str, text: str, spirit: int = 0, money: int = 0, bond: int = 0, default: bool = False,
      also: dict | None = None) -> dict:
    return dict(id=cid, label=label, text=text, spirit=spirit, money=money, bond=bond, default=default, also=also or {})


CATS = {
    'thue': ('🏠', 'Chuyện nhà thuê'),
    'chu': ('🔑', 'Chuyện cho thuê nhà'),
}

# Who you rent from (game/housing.py where(): 'attic' or the rented room's kind). Bà Tám is a neighbour of the journey
# CAST: the closeness with her is the life layer's bond (game/life.py). The dorm has its own roommate moments.
LANDLORDS = {
    'attic': dict(cast='ba_tam', name='Bà Tám', emoji='👵', role='Chủ nhà trọ'),
    'tro_moi': dict(cast=None, name='Cô Hạnh', emoji='👩', role='Chủ phòng trọ Hẻm 12'),
}

THUE = [
    dict(id='thue_tre', who='chu', landlord=True, emoji='📅', title='Lương về trễ mấy hôm',
         lines=['Tuần này chỗ làm trả lương trễ, ví hơi mỏng.',
                '{chu} gõ cửa: “Tiền điện nước tháng này ghi sổ rồi nghe, khi nào tiện thì gửi.”'],
         choices=[C('xin', 'Xin khất vài hôm', '{chu} xua tay: “Có gì đâu, ai cũng có lúc kẹt. Cuối tuần gửi cũng được.”',
                    spirit=2, bond=2, default=True),
                  C('tra', 'Gom tiền lẻ gửi liền', '{chu} cầm xấp tiền lẻ, cười hiền rồi dúi lại cho {anh} mấy quả quýt.',
                    spirit=2, money=-3, bond=4)]),
    dict(id='thue_dien', who='chu', landlord=True, emoji='💡', title='Phòng bị cúp điện',
         lines=['Tối về bật đèn, nghe cái tạch: cả phòng tối om.', 'Chắc cầu chì lại nhảy rồi.'],
         choices=[C('tu', 'Soi đèn pin, tự thay cầu chì', 'Mò mẫm mười phút, đèn sáng lại. Thấy mình cũng ra dáng thợ điện ghê.',
                    spirit=3, default=True),
                  C('bao', 'Báo chủ nhà gọi thợ', '{chu} gọi Chú Tư qua sửa, thay luôn cái ổ cắm cũ. Không lấy đồng nào.',
                    spirit=2, bond=2, also={'chu_tu': 2})]),
    dict(id='thue_o_lau', who='chu', landlord=True, emoji='🪴', title='Chủ nhà hỏi chuyện ở lâu',
         lines=['{chu} vừa tưới cây vừa hỏi: “Tính ở đây lâu không, hay sắp dọn đi nơi khác?”'],
         choices=[C('o', 'Còn ở lâu lắm', '{chu} mừng ra mặt, hứa sơn lại khung cửa sổ cho phòng sáng hơn.',
                    spirit=2, bond=3, default=True),
                  C('mua', 'Đang để dành mua nhà riêng', '{chu} gật gù: “Giỏi! Có nhà rồi nhớ mời ăn tân gia nghe.”',
                    spirit=3, bond=1)]),
    dict(id='thue_canh', who='chu', landlord=True, emoji='🍲', title='Chủ nhà cho tô canh',
         lines=['Chiều về, {chu} bưng lên tô canh chua cá lóc còn nóng hổi.', '“Nấu dư nè, ăn cho vui nghe.”'],
         choices=[C('nhan', 'Nhận và cảm ơn rối rít', 'Tối đó cơm với canh chua mà ngon lạ, đỡ được một bữa mua ngoài.',
                    spirit=3, money=3, bond=3, default=True),
                  C('bieu', 'Biếu lại bịch trái cây mới mua', '{chu} cười tít mắt, ngồi kể chuyện hồi xưa tới tận tối.',
                    spirit=3, money=-2, bond=5)]),
    dict(id='thue_chuyen', who='', person=dict(name='Chị Thu phòng bên', emoji='📦', role='Hàng xóm cùng dãy trọ'),
         emoji='📦', title='Phòng bên chuyển đi',
         lines=['Sáng chủ nhật, Chị Thu phòng bên gọi xe tải nhỏ, đồ đạc chất đầy hành lang.',
                '“Chỗ làm mới xa quá, chị phải dọn rồi. Ở đây vui ghê, tiếc thiệt.”'],
         choices=[C('phu', 'Phụ khiêng đồ xuống xe', 'Khiêng xong mồ hôi nhễ nhại. Chị Thu dúi cho hộp bánh: “Cảm ơn nha, rảnh ghé chị chơi.”',
                    spirit=3, money=2, default=True),
                  C('chuc', 'Gửi lời chúc, hẹn ghé chơi', 'Chị Thu cười: “Nhà mới gần chợ lắm, bữa nào ghé chị nấu bún riêu.”',
                    spirit=2)]),
    dict(id='thue_xe', who='co_ba', emoji='🛵', title='Hàng xóm cự nhau chỗ để xe',
         lines=['Sáng sớm, Cô Ba với Bà Sáu lời qua tiếng lại vì chiếc xe dựng chắn lối đi.', 'Cả hẻm ló đầu ra coi.'],
         choices=[C('hoa', 'Ra dời xe, nói đỡ mỗi bên một câu', 'Xe dời gọn, hai bên bớt nóng. Trưa đó Cô Ba còn mời Bà Sáu ly trà đá.',
                    spirit=2, bond=2, default=True, also={'ba_sau': 2}),
                  C('cafe', 'Mời hai cô ly cà phê sữa đá', 'Ly cà phê làm dịu hết. Ba người ngồi đầu hẻm cười nói như chưa có gì.',
                    spirit=3, money=-3, bond=3, also={'ba_sau': 3})]),
    dict(id='thue_lau', who='anh_khoa', emoji='🍜', title='Hàng xóm rủ ăn lẩu',
         lines=['Anh Khoa gõ cửa: “Tối nay anh làm nồi lẩu, qua ăn chung cho vui!”'],
         choices=[C('di', 'Qua ăn liền', 'Nồi lẩu bốc khói, cả dãy trọ ngồi chật sân. Lâu rồi mới cười nhiều vậy.',
                    spirit=4, bond=3, default=True),
                  C('gop', 'Mang chai nước ngọt qua góp vui', 'Anh Khoa vỗ vai: “Lần sau tới lượt nấu nha!” Ai cũng vui.',
                    spirit=4, money=-2, bond=5)]),
]

CHU = [
    dict(id='chu_tre', who='khach', emoji='📅', title='Người thuê xin đóng tiền trễ',
         lines=['{khach} nhắn: “Tháng này lương về trễ, cho đóng tiền nhà {nha} trễ vài hôm được không?”'],
         choices=[C('thong_tha', 'Cứ thong thả, không sao', 'Hai hôm sau {khach} gửi đủ, kèm túi cam với lời cảm ơn.',
                    spirit=2, money=2, bond=4, default=True),
                  C('nhac', 'Nhắn nhắc nhẹ hạn cuối tuần', 'Đúng hẹn {khach} chuyển khoản, nhắn thêm: “Cảm ơn đã thông cảm nha.”',
                    spirit=1, bond=1)]),
    dict(id='chu_dien', who='khach', emoji='💡', title='Điện nhà cho thuê bị hư',
         lines=['{khach} gọi: “Nhà {nha} nhảy CB hoài, tối qua cúp điện cả tiếng.”'],
         choices=[C('tu', 'Xách đồ nghề qua tự sửa', 'Thay cái CB mới, đèn sáng trưng. {khach} pha ấm trà mời, ngồi nói chuyện tới tối.',
                    spirit=3, bond=3, default=True),
                  C('tho', 'Gọi thợ điện tới liền', 'Thợ tới trong nửa tiếng, đi lại dây gọn gàng. {khach} khen chủ nhà chu đáo.',
                    spirit=2, money=-4, bond=3)]),
    dict(id='chu_chuyen', who='khach', emoji='📦', title='Người thuê tính chuyển nhà',
         lines=['{khach} ngập ngừng: “Chỗ làm mới xa quá, chắc phải tìm nhà gần đó…”'],
         choices=[C('chuc', 'Chúc may mắn, hỏi giùm nhà gần chỗ mới', '{khach} cảm động, nghĩ lại thấy ở đây thoải mái quá, xin ở thêm ít lâu.',
                    spirit=2, bond=4, default=True),
                  C('giu', 'Bớt chút tiền tháng này để giữ chân', '{khach} cười tươi: “Vậy ở lại luôn!” Bớt chút xu mà giữ được người thuê dễ thương.',
                    spirit=2, money=-4, bond=5)]),
    dict(id='chu_xich_mich', who='khach', emoji='🧺', title='Người thuê xích mích với nhà bên',
         lines=['Nhà bên phàn nàn {khach} phơi đồ lấn sang ban công, hai bên cự nhau một trận.'],
         choices=[C('hoa', 'Qua nói chuyện, chia lại chỗ phơi', 'Gắn thêm cây sào phơi, hai bên bắt tay làm lành, chiều còn mời nhau đĩa xoài.',
                    spirit=3, bond=3, default=True),
                  C('qua', 'Mua bịch trái cây làm quà giảng hòa', 'Bịch trái cây làm ai cũng dịu giọng. Từ đó hai nhà hay qua lại.',
                    spirit=3, money=-3, bond=4)]),
    dict(id='chu_banh', who='khach', emoji='🥞', title='Người thuê mang đồ ăn sang',
         lines=['{khach} mang sang hộp bánh xèo mới đổ: “Ăn thử nha, làm nhiều lắm.”'],
         choices=[C('nhan', 'Nhận và cảm ơn', 'Bánh xèo giòn rụm, đỡ luôn bữa tối.', spirit=3, money=3, bond=3, default=True),
                  C('bieu', 'Biếu lại hũ mứt gừng', '{khach} thích lắm, hẹn tuần sau đổ bánh mời tiếp.', spirit=3, money=-2, bond=5)]),
    dict(id='chu_moi', who='khach', emoji='🍚', title='Người thuê mời ăn cơm',
         lines=['{khach} nhắn: “Cuối tuần làm mâm cơm tân gia muộn, mời chủ nhà qua chung vui!”'],
         choices=[C('di', 'Nhận lời qua ăn', 'Mâm cơm ấm cúng, ai cũng khen nhà sáng sủa dễ ở. Về nhà mà lòng vui ghê.',
                    spirit=4, bond=4, default=True),
                  C('hen', 'Bận rồi, hẹn bữa khác', '{khach} bảo không sao, hôm sau gửi qua một phần bánh.', spirit=2, bond=1)]),
]
