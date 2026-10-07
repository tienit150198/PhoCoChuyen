"""🎟️ Vé số cào at the fair (owner 03/10: "thêm trò cào xổ số", "mọi người cào bằng tay thật luôn", "giải thưởng ...
mọi người có cảm giác thắng thua, không lỗ quá hoặc không quá lời nhưng vẫn cuốn"). Pure functions; the command, the
wallet and the Sổ ví row are in game/fair.py (fair_xs), the stall (dì Hai's tray, the silver layer scratched by hand)
in public/js/v4/fair-scratch.js.

The player buys a vé of one TIERS price; the ticket is decided and paid on the server at the purchase: it wins with
game.fair.luck_p(…, 'xs', …, stake=price) (same base chance for every ticket), and a winning ticket's prize is a
multiple of its price drawn from PRIZES. layout() then draws the CELLS boxes under the silver: a winning ticket shows
its prize in exactly 3 boxes and every other amount at most twice, a losing one every amount at most twice (so the
rule on the ticket, "3 ô giống nhau trúng số đó", always reads the same as the result). The client only scratches it
open; nothing it sends decides anything.

Owner 07/10: about 55% of tickets win at every price in normal play (game.fair WIN_P, with its
cool-off to 50% after four wins and its spam decay to 40% for a long run of tickets; no sure
win after losses any more). Prize weights stay at
mean 1.59x conditional on a prize, including refunds; winning does not always mean
net profit. Already purchased tickets retain their layout and payment.
"""
from __future__ import annotations

TIERS = (2, 5, 10, 20, 50, 100, 200, 500, 1000)  # the vé's price, xu
NAMES = {2: 'Vé Lộc Nhỏ', 5: 'Vé Phát Tài', 10: 'Vé Như Ý', 20: 'Vé Đại Cát',
         50: 'Vé Tài Lộc', 100: 'Vé Phú Quý', 200: 'Vé Thịnh Vượng', 500: 'Vé Đại Lộc', 1000: 'Vé Ngàn Lộc'}
CELLS = 9                       # a 3 × 3 grid under the silver
MATCH = 3                       # 3 boxes of the same amount: that amount is won
# (multiple of price, weight per 1000 winning tickets): E[multiple | win] = 1.59
PRIZES = ((1, 675), (2, 230), (3, 60), (5, 25), (10, 8), (20, 1), (50, 1))
MULTS = tuple(m for m, _ in PRIZES)
# Historical API retained at the current fixed base probability.
P_HI, P_LO = .55, .55   # game.fair.WIN_P (07/10)
RUN_STEP = 0


def win_p(net: int) -> float:
    return P_HI


def prize_mult(rng) -> int:
    """A winning ticket's multiple of its price."""
    x = rng.randrange(sum(w for _, w in PRIZES))
    for m, w in PRIZES:
        if x < w:
            return m
        x -= w
    return MULTS[0]


def layout(price: int, mult: int, rng) -> list[int]:
    """The CELLS amounts under the silver: `mult` (0: a losing ticket) × price in exactly MATCH boxes, every other
    amount of the table at most MATCH - 1 times."""
    cells = [mult * price] * MATCH if mult else []
    left = {m: MATCH - 1 for m in MULTS if m != mult}
    while len(cells) < CELLS:
        pool = [m for m, n in left.items() if n > 0]
        m = rng.choice(pool)
        left[m] -= 1
        cells.append(m * price)
    rng.shuffle(cells)
    return cells


def read(cells: list[int]) -> int:
    """What a grid pays: the amount found in MATCH boxes, else 0 (the rule printed on the ticket)."""
    for v in set(cells):
        if cells.count(v) >= MATCH:
            return v
    return 0
