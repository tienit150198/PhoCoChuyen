"""🤝 Phụ kiện đôi, the catalogue (game/friend_charms.py has the rules; public/js/v4/look.js draws each kind under the same id).
Pure data: live/charms.py imports it without the game's engine."""
from __future__ import annotations

from . import price_index as pi   # 💹 prices written as the base (before 07/10), indexed here


def _k(kid, emoji, name, item, price, desc, hint):
    return dict(id=kid, emoji=emoji, name=name, item=item, price=pi.price(price), desc=desc, hint=hint)


KINDS = [
    _k('chi_cot', '🏎️', 'Chí cốt', 'Móc khóa mô hình siêu xe', 200,
       'Hai chiếc siêu xe mô hình đỏ chót móc bên hông, đi đâu cũng thấy. Cho người anh em vào sinh ra tử.',
       'Hay tặng nhau giữa hai người bạn trai'),
    _k('ban_than', '👜', 'Bạn thân', 'Túi xách đôi', 160,
       'Hai chiếc túi xách hồng cùng kiểu, khóa hình trái tim, xách tay trái. Cho cô bạn thân nhất.',
       'Hay tặng nhau giữa hai cô bạn gái'),
    _k('tri_ki', '💐', 'Tri kỉ', 'Hoa vĩnh sinh cài áo', 120,
       'Hai đóa hồng vĩnh sinh cài ngực áo, giữ màu mãi không tàn. Cho người hiểu mình nhất.',
       'Hợp với mọi người bạn'),
]
INDEX = {k['id']: k for k in KINDS}
ORDER = tuple(k['id'] for k in KINDS)
