"""🤝 Phụ kiện đôi, the catalogue (game/friend_charms.py has the rules; public/js/v4/look.js draws each kind under the same id).
Pure data: live/charms.py imports it without the game's engine.

💹 Prices (owner 22/10 "thêm nhiều món nữa đi, với giá như này rẻ quá, tăng nhẹ tí nữa"): base prices through
game/price_index.price like every catalogue. 2.5.3 sold the three first pairs at 220 / 175 / 130 xu, about half a day of a
median player's work (a day ≈ 170 xu measured 21/10, ≈ 250 with 📈 Thu nhập tăng thêm since 22/10), cheaper than a mũ len.
They now cost +50 % (Chí cốt 330, Bạn thân 265, Tri kỉ 200) and the ten pairs sit in three steps that follow the
relationships they open (RELS): 165–220 xu (about a day: a small gift anyone can make), 265–330 xu (a day and a half: a
real present), 440–570 xu (two days of work: what a sworn brother gives, about a 24K gold ring of game/wedding_content.py). A pair is bought once for two people, so each friend's half costs half of that.

💞 Relationships (owner 22/10 "set mối quan hệ trong game được, kiểu bạn bè, tri kỉ,... và muốn set thì phải mua mấy cái
này"): RELS, each opened by the pairs listed under it (a pair of a dearer step opens every label of the steps below it,
and each of the three first pairs also opens the label it is named after). Bạn bè is the default (every friend) and needs
nothing. Labels are gender-free: anyone picks any (Anh em kết nghĩa / Chị em kết nghĩa are both offered).
"""
from __future__ import annotations

from . import price_index as pi   # 💹 prices written as the base (before 07/10), indexed here


def _k(kid, emoji, name, item, price, step, desc, hint):
    return dict(id=kid, emoji=emoji, name=name, item=item, price=pi.price(price), step=step, desc=desc, hint=hint)


KINDS = [
    _k('chi_cot', '🏎️', 'Chí cốt', 'Móc khóa mô hình siêu xe', 300, 2,
       'Hai chiếc siêu xe mô hình đỏ chót móc bên hông, đi đâu cũng thấy. Cho người anh em vào sinh ra tử.',
       'Hay tặng nhau giữa hai người bạn trai'),
    _k('ban_than', '👜', 'Bạn thân', 'Túi xách đôi', 240, 2,
       'Hai chiếc túi xách hồng cùng kiểu, khóa hình trái tim, xách tay trái. Cho cô bạn thân nhất.',
       'Hay tặng nhau giữa hai cô bạn gái'),
    _k('tri_ki', '💐', 'Tri kỉ', 'Hoa vĩnh sinh cài áo', 180, 1,
       'Hai đóa hồng vĩnh sinh cài ngực áo, giữ màu mãi không tàn. Cho người hiểu mình nhất.',
       'Hợp với mọi người bạn'),
    # owner 22/10 "thêm nhiều món nữa đi … tính toán thêm vài món nữa"
    _k('chi_do', '🧶', 'Chỉ đỏ', 'Vòng tay chỉ đỏ', 150, 1,
       'Hai sợi chỉ đỏ thắt nút may mắn, xâu một hạt vàng nhỏ, đeo cổ tay trái. Buộc vào là thành một đôi.',
       'Món quà nhỏ cho người mới thân'),
    _k('huy_hieu', '⭐', 'Đồng đội', 'Huy hiệu ngôi sao', 160, 1,
       'Hai huy hiệu ngôi sao vàng cài ngực phải, viền xanh như áo đội bóng. Cùng một đội, cùng một phố.',
       'Hợp với bạn cùng chỗ làm, cùng bang'),
    _k('gau_bong', '🧸', 'Gấu bông', 'Móc khóa gấu bông', 200, 1,
       'Hai chú gấu bông nâu đeo nơ, kẹp trên vai áo như đang ngồi chơi. Ai nhìn cũng muốn bẹo má.',
       'Hợp với mọi người bạn'),
    _k('bong_bay', '🎈', 'Bay cao', 'Bóng bay trái tim', 260, 2,
       'Hai quả bóng bay hình trái tim buộc cổ tay phải, bay lơ lửng trên vai. Đi giữa phố là thấy nhau ngay.',
       'Cho người bạn vui tính nhất'),
    _k('quat', '🪭', 'Tri âm', 'Quạt giấy đôi', 280, 2,
       'Hai chiếc quạt giấy vẽ hoa sen, xòe cầm tay phải. Một người phe phẩy, người kia hiểu ý.',
       'Cho người nghe mình nói hết'),
    _k('day_chuyen', '💞', 'Nửa trái tim', 'Dây chuyền nửa trái tim', 400, 3,
       'Mỗi người giữ nửa trái tim bạc trên dây chuyền, ghép lại mới thành một. Cho người không thể thiếu.',
       'Cho người bạn quan trọng nhất'),
    _k('ngoc_boi', '🟢', 'Kết nghĩa', 'Ngọc bội đeo hông', 520, 3,
       'Hai miếng ngọc bội xanh tua đỏ đeo bên hông, như lời thề kết nghĩa ngày xưa: có phúc cùng hưởng.',
       'Cho anh em, chị em kết nghĩa'),
]
INDEX = {k['id']: k for k in KINDS}
ORDER = tuple(k['id'] for k in KINDS)


def _opens(step: int, own: str = '') -> tuple:
    """The kinds that open a label of this step: every pair of that step or dearer, and the pair named after it."""
    return tuple(k['id'] for k in KINDS if k['step'] >= step or k['id'] == own)


RELS = [
    dict(id='ban_than', emoji='💛', name='Bạn thân', step=1, kinds=_opens(1)),
    dict(id='ca_cung', emoji='🤜', name='Cạ cứng', step=1, kinds=_opens(1)),
    dict(id='chi_cot', emoji='🔥', name='Chí cốt', step=2, kinds=_opens(2, 'chi_cot')),
    dict(id='tri_ki', emoji='💐', name='Tri kỉ', step=3, kinds=_opens(3, 'tri_ki')),
    dict(id='anh_em', emoji='🐉', name='Anh em kết nghĩa', step=3, kinds=_opens(3)),
    dict(id='chi_em', emoji='🌸', name='Chị em kết nghĩa', step=3, kinds=_opens(3)),
]
REL_INDEX = {r['id']: r for r in RELS}
REL_ORDER = tuple(r['id'] for r in RELS)
DEFAULT_REL = dict(id='ban_be', emoji='🤝', name='Bạn bè')
