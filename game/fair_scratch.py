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

Owner 16/10 (the rebalance): a ticket wins with game.fair.luck_p (.57 a ticket, .60 winning back a small loss, lower
once the day is well up or tickets are bought too fast; never below .40) and a won ticket pays PRIZES: 1.5× 800,
2× 140, 3× 40, 5× 15, 20× 5 per 1000 won tickets, a mean of 1.775× (no 1× "refund" prize any more), the prize
rounded down to whole xu (amount(): the 2-xu vé's 1.5× pays 3). A .57 ticket returns 101.2% before streak cooling,
police or Lộc. Four consecutive wins still cap the next draw at 45%, a 50k+ stake (none on this menu) at 40%.
Owner 22/10 ("tăng nhẹ tỷ lệ thắng"): every band +3 points, .60 a ticket (106.5%), .63 winning back, a 50k+ stake .43.
Already purchased tickets retain their layout and payment.
The temporary golden-days event uses only PRIZES multipliers above one for its winning draw (now all of them).
"""
from __future__ import annotations

TIERS = (2, 5, 10, 20, 50, 100, 200, 500, 1000)  # the vé's price, xu
NAMES = {2: 'Vé Lộc Nhỏ', 5: 'Vé Phát Tài', 10: 'Vé Như Ý', 20: 'Vé Đại Cát',
         50: 'Vé Tài Lộc', 100: 'Vé Phú Quý', 200: 'Vé Thịnh Vượng', 500: 'Vé Đại Lộc', 1000: 'Vé Ngàn Lộc'}
CELLS = 9                       # a 3 × 3 grid under the silver
MATCH = 3                       # 3 boxes of the same amount: that amount is won
# (multiple of price, weight per 1000 winning tickets): E[multiple | win] = 1.775 (owner 16/10; 08/10–15/10:
# (1, 655) (2, 230) (3, 62) (5, 32) (10, 14) (20, 5) (50, 2), 1.801 with refunds)
PRIZES = ((1.5, 800), (2, 140), (3, 40), (5, 15), (20, 5))
MULTS = tuple(m for m, _ in PRIZES)
# Historical API retained at the current base probability.
P_HI, P_LO = .60, .60   # game.fair.BASES['xs'] (owner 22/10: .57 → .60)
RUN_STEP = 0


def amount(price: int, mult) -> int:
    """What a ticket of `price` pays at multiple `mult` (0: nothing), rounded down to whole xu."""
    return int(price * mult) if mult else 0


def win_p(net: int) -> float:
    return P_HI


def prize_mult(rng, *, profit_only: bool = False):
    """A winning ticket's multiple (1.5 or a whole number); the golden event excludes break-even refunds (none left)."""
    prizes = tuple((m, w) for m, w in PRIZES if m > 1) if profit_only else PRIZES
    x = rng.randrange(sum(w for _, w in prizes))
    for m, w in prizes:
        if x < w:
            return m
        x -= w
    return prizes[0][0]


def layout(price: int, mult, rng) -> list[int]:
    """The CELLS amounts under the silver: amount(price, mult) (mult 0: a losing ticket) in exactly MATCH boxes, every
    other amount of the table at most MATCH - 1 times."""
    cells = [amount(price, mult)] * MATCH if mult else []
    left = {m: MATCH - 1 for m in MULTS if m != mult}
    while len(cells) < CELLS:
        pool = [m for m, n in left.items() if n > 0]
        m = rng.choice(pool)
        left[m] -= 1
        cells.append(amount(price, m))
    rng.shuffle(cells)
    return cells


def read(cells: list[int]) -> int:
    """What a grid pays: the amount found in MATCH boxes, else 0 (the rule printed on the ticket)."""
    for v in set(cells):
        if cells.count(v) >= MATCH:
            return v
    return 0
