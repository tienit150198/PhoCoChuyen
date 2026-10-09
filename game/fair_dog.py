"""🐕 Đua chó: a betting stall of the Chợ đen (owner 09/10: "trò đua chó"; the player only watches and cheers).

Pure functions; the command (fair_dg), the wallet, the Sổ ví row, the bảo kê gate and the police are in game/fair.py,
the track (the race played out, the crowd, the 📣 cổ vũ button, which changes nothing) in public/js/v4/fair-dog.js.

A race: LANES dogs from the RACERS roster (the pet system's breeds and coats, game/pets_content.py, drawn by
public/js/v4/pet-art.js). The lineup of a race is fixed by its number (race(), one every SLOT_S seconds, the same for
everyone): which dogs run and which payout each one has. A payout is a price (shown, like a bookmaker's board):
CLASSES[k] = (weight per 1000, payout in tenths of the stake, stake included). The player picks a dog and a stake,
the server draws the winner at once from the classes' weights (draw(); never shown, never sent) and the rest of the
finishing order (for the show), and pays a winning stake × payout / 10 (rounded down: the house's side).

House edge (owner 08/10 "đảm bảo nhà cái luôn thắng"): every dog returns weight × payout / 10000 per xu staked,
92.8% (the favourite) to 95.0% (the outsider), so no pick comes out ahead (scripts/sim_fair_odds.py,
docs/FAIR_HOUSE_EDGE.md). Honest fixed odds like the bầu cua's dice: no cool-off and no spam decay (nothing to lower),
the 🍀 Lộc gate as for the other paid luck stalls, the police as on every paid round.

No save: a race is settled in its one command (the receipt is the result; the Sổ ví row "🐕 Đua chó chợ đen · N lượt"
counts the races), so an older server has nothing new to validate.
"""
from __future__ import annotations

import random

from . import pets_content as pc

# (weight per 1000 races, payout in tenths of the stake): weight × payout ≤ 9500 per 10000 for every class
CLASSES = ((320, 29), (240, 39), (180, 52), (120, 78), (90, 105), (50, 190))
LANES = len(CLASSES)
TOP = max(m for _, m in CLASSES)        # the biggest payout, tenths
SLOT_S = 120                            # a new lineup every two minutes
SLOTS_AHEAD = 3                         # lineups sent ahead (the client's clock may run a little early or late)
DG_MIN = 10                             # the smallest stake (like chiếu trong)
PHOTO_P = .3                            # how often the show ends in a photo finish (cosmetic only)
# The roster: (name, breed id of game/pets_content.py, coat index)
RACERS = (
    ('Mực', 'cho_ta', 1), ('Vàng', 'cho_ta', 0), ('Vện', 'cho_ta', 2), ('Lu Lu', 'corgi', 0), ('Ki Ki', 'shiba', 0),
    ('Bông', 'samoyed', 0), ('Sói Con', 'husky', 0), ('Xúc Xích', 'lap_xuong', 0), ('Tia Chớp', 'phu_quoc', 0),
    ('Mây', 'bac_ha', 0), ('Bơ', 'golden', 0), ('Tôm', 'pom', 0), ('Ớt', 'chihuahua', 0), ('Gấu', 'alaska', 0),
)
RACE_LABEL = '🐕 Đua chó chợ đen'
OLD_RACE = 'Đàn chó đã vào lượt đua mới rồi, coi lại rồi chọn nha.'
BAD_LANE = 'Chọn một chú chó để cổ vũ nha.'


def race(t: float) -> int:
    """The race number at time t (one every SLOT_S seconds)."""
    return int(t // SLOT_S)


def lineup(n: int) -> list[list[int]]:
    """Race n's lanes, top to bottom: [racer index, class index]; the same on every server and for every player."""
    rng = random.Random(f'fair-dg|{n}')
    dogs = rng.sample(range(len(RACERS)), LANES)
    classes = list(range(LANES))
    rng.shuffle(classes)
    return [[d, k] for d, k in zip(dogs, classes)]


def pay(cls: int) -> int:
    """The payout of a class, tenths of the stake (stake included)."""
    return CLASSES[cls][1]


def back(stake: int, cls: int) -> int:
    """What a winning stake on a dog of class `cls` brings back (stake included, rounded down)."""
    return stake * pay(cls) // 10


def draw(lanes: list[list[int]], rng) -> list[int]:
    """The finishing order (lane indexes, the winner first): each place drawn from the classes' weights among the dogs
    still running. Only the first place pays; the rest is for the show."""
    left = list(range(len(lanes)))
    order = []
    while left:
        total = sum(CLASSES[lanes[i][1]][0] for i in left)
        x = rng.randrange(total)
        for i in left:
            w = CLASSES[lanes[i][1]][0]
            if x < w:
                break
            x -= w
        order.append(i)
        left.remove(i)
    return order


def racer(i: int) -> dict:
    name, breed, coat = RACERS[i]
    b = pc.BREEDS[breed]
    c = b['coats'][min(coat, len(b['coats']) - 1)]
    return dict(name=name, breed=b['name'], shape=b['shape'], size=b['size'], b=c['b'], m=c['m'], l=c['l'], e=c['e'])


def public(t: float) -> dict:
    """api.state.fair.dog: the roster, this race's lineup and the next ones (payouts are prices: shown), the stake
    bounds. No weight, no chance, nothing about the draw."""
    from .fair import STAKE_MAX
    n = race(t)
    return dict(min=DG_MIN, max=STAKE_MAX, slot=SLOT_S, dogs=[racer(i) for i in range(len(RACERS))],
                races=[[k, [[d, pay(c)] for d, c in lineup(k)]] for k in range(n, n + SLOTS_AHEAD + 1)])
