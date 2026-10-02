"""🎟️ Vé số cào at the fair (owner 03/10: "thêm trò cào xổ số", "mọi người cào bằng tay thật luôn", "giải thưởng ...
mọi người có cảm giác thắng thua, không lỗ quá hoặc không quá lời nhưng vẫn cuốn"). Pure functions; the command, the
wallet and the Sổ ví row are in game/fair.py (fair_xs), the stall (dì Hai's tray, the silver layer scratched by hand)
in public/js/v4/fair-scratch.js.

The player buys a vé of one TIERS price; the ticket is decided and paid on the server at the purchase: it wins with
game.fair.luck_p(…, 'xs', …, P_HI, P_LO) (today's fair net and the run of tickets), and a winning ticket's prize is a
multiple of its price drawn from PRIZES. layout() then draws the CELLS boxes under the silver: a winning ticket shows
its prize in exactly 3 boxes and every other amount at most twice, a losing one every amount at most twice (so the
rule on the ticket, "3 ô giống nhau trúng số đó", always reads the same as the result). The client only scratches it
open; nothing it sends decides anything.

The table (scratch simulation, scripts in the commit message; 100 000 tickets each):
  P_HI 43 %: wins 43 %, 104 xu back per 100 xu of tickets; at the floor (P_LO 39 %, today's net far up or one long
  run of tickets): wins 39 %, 95 xu back. About one ticket in two that wins only gives the price back (hoàn vé), so
  tickets that come out ahead are ~22 % (~20 % at the floor); 10× or more is ~1 ticket in 45, 50× ~1 in 1 200.
"""
from __future__ import annotations

TIERS = (2, 5, 10, 20)          # the vé's price, xu
NAMES = {2: 'Vé Lộc Nhỏ', 5: 'Vé Phát Tài', 10: 'Vé Như Ý', 20: 'Vé Đại Cát'}
CELLS = 9                       # a 3 × 3 grid under the silver
MATCH = 3                       # 3 boxes of the same amount: that amount is won
# (multiple of the price, weight per 1000 winning tickets): E[multiple | win] = 2.46
PRIZES = ((1, 470), (2, 280), (3, 115), (5, 85), (10, 40), (20, 8), (50, 2))
MULTS = tuple(m for m, _ in PRIZES)
# the odds a ticket wins anything: the shared taper (game.fair.odds) with the stall's own ends; a long run of tickets
# cools RUN_STEP a ticket (game.fair.RUN_RULES['xs']) down to P_LO too
P_HI, P_LO = .42, .39
RUN_STEP = .005


def win_p(net: int) -> float:
    """The odds a ticket wins given the player's fair net today (game.fair.odds, from P_HI down to P_LO)."""
    from .fair import odds
    return odds(net, P_HI, P_LO)


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
