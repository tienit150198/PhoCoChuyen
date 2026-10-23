"""🪽 Cánh, the catalogue (game/wings.py has the rules; public/js/v4/look.js paintWings draws each style under the same id).
Pure data: live/wings.py imports it without the game's engine.

Owner 22/10: "tính xem thêm cánh cho người dùng nhé, cánh sẽ buff cho người chơi khi đánh pet", then "cánh này là làm đẹp
cho người dùng nhé, với tăng tiền kiếm được nữa", "cho nâng nữa, nâng lên như thú đi, D > C > B > A > S > SS > SSS >
Huyền thoại", "mua thì mặc định D hoặc C ngẫu nhiên, xong nâng lên như cơ chế hiện tại nhé".

* STYLES are looks only (a butterfly's, a fairy's, a bat's, an angel's, a dragon's, a phoenix's): each its price at 🛍️ Tiệm
  phụ kiện, base prices through game/price_index.price like every catalogue. The style never changes the bonuses.
* The TIER gives them (TIERS, the pets' ranks D…SSS of game/pet_tiers.py plus 🌟 Huyền thoại): EARN % of the player's own
  work earnings while worn (at most CAP xu a Vietnam day, like a pet's), and BATTLE % on the HP and attack of their pets in
  every pet battle (game/pet_battle.py `wg`). tests/test_wings.py Balance simulated 3 000 1-vs-1 fights a step: +1 % wins
  ~53 %, +3 % ~56 %, +6 % (Huyền thoại) ~62 %, while one pet rank up wins ~74–78 % and still wins ~61 % against a pet one
  rank lower that wears Huyền thoại wings: a wing never outweighs a rank.
"""
from __future__ import annotations

from . import price_index as pi

TIERS = ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS', 'HT')
TIER_NAME = ('Thường', 'Khá', 'Tốt', 'Hiếm', 'Quý', 'Siêu quý', 'Thần thoại', 'Huyền thoại')
TOP = len(TIERS) - 1                  # 🌟 Huyền thoại: three SSS
SSS = TOP - 1
# Owner 22/10 (after the first table, +1…+10 %, 5k…500k a day): "thu nhập trần/ngày sẽ tăng lên nữa", "SSS được 20% đi"
EARN = (2, 4, 6, 8, 11, 15, 20, 25)   # % of the work earnings (the pets give 2…30 %)
# then "tăng nữa nhé, tối đa đó gấp đôi đi": the daily caps ×2
CAP = (40_000, 100_000, 300_000, 800_000, 2_000_000, 6_000_000, 16_000_000, 30_000_000)   # xu a Vietnam day
BATTLE = (2, 3, 4, 6, 8, 10, 12, 14)   # % on every stat of the owner's pets, so 💪 lực chiến itself (owner 23/10 "tăng trực tiếp luôn")
# 🪽 Bay (owner 24/10 "bay được k nhỉ, sẽ có tăng tốc độ như xe ấy, nếu sử dụng cánh thì k lái xe được"): a flyer moves
# FLY_FAST times their walk on the walk maps, by tier, on the vehicles' scale (public/js/v4/ride.js FAST): D a bicycle
# (1.45), B an e-bike (1.6), S a motorbike (1.8), SS a small car (2.0), SSS a convertible (2.1), Huyền thoại a supercar
# (2.3). The same numbers in public/js/v4/wings-art.js WING_FLY_FAST (tests/test_wing_fly.py keeps them together).
FLY_FAST = (1.45, 1.5, 1.6, 1.7, 1.8, 2.0, 2.1, 2.3)


def _s(sid, emoji, name, price, desc):
    return dict(id=sid, emoji=emoji, name=name, price=pi.price(price), desc=desc)


STYLES = [
    _s('buom', '🦋', 'Cánh bướm', 8_000, 'Bốn cánh bướm mỏng, vân hoa văn như tranh kính, rung rinh mỗi bước đi.'),
    _s('tien', '🧚', 'Cánh tiên', 12_000, 'Cánh trong như sương sớm, gân bạc lấp lánh khi đứng dưới nắng.'),
    _s('doi', '🦇', 'Cánh dơi', 15_000, 'Cánh màng tím than, viền nhọn, đi đêm là ngầu nhất phố.'),
    _s('thien_than', '🪽', 'Cánh thiên thần', 20_000, 'Từng lớp lông vũ trắng muốt xếp tầng, mềm như mây.'),
    _s('rong', '🐉', 'Cánh rồng', 30_000, 'Cánh vảy rồng có xương cánh và móc vuốt, uy nghi như rồng thiêng.'),
    _s('phuong', '🔥', 'Cánh phượng hoàng', 45_000, 'Lông vũ đỏ cam như lửa, đuôi lông dài óng ánh vàng.'),
]
INDEX = {x['id']: x for x in STYLES}
ORDER = tuple(x['id'] for x in STYLES)
