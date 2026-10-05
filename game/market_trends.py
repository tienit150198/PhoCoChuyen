"""Seeded fictional news calendars; reading a quote never advances a market.

Every 16-day window has a 75% chance of one 2–5-day episode, starting
between offsets 2 and 9. Windows therefore cannot overlap or touch.
Only public_news is sent to clients: duration and future news stay private.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import random

WINDOW = 16
HEADLINES = {
    'coin': {
        'up': ('Nhiều cửa hàng trong game nhận thanh toán bằng Mây Coin.',
               'Cộng đồng trong game hào hứng với bản nâng cấp Mây Coin.',
               'Sàn giao dịch trong game mở thêm chợ Mây Coin.'),
        'down': ('Một ví lớn trong game bán bớt Mây Coin.',
                 'Sàn giao dịch trong game bảo trì, người mua Mây Coin chờ đợi.',
                 'Nhà đầu tư trong game chốt lời Mây Coin.'),
    },
    'gold': {
        'up': ('Mùa cưới trong game làm nhu cầu mua vàng tăng.',
               'Các tiệm trong game tăng mua vàng để bổ sung hàng.',
               'Người dân trong game dành thêm tiền mua vàng.'),
        'down': ('Nhiều người trong game bán vàng để chốt lời.',
                 'Nguồn vàng trong game dồi dào, sức mua chậm lại.',
                 'Các tiệm trong game giảm mua sau mùa lễ hội.'),
    },
}


@dataclass(frozen=True)
class Episode:
    start: int
    end: int
    direction: str
    title: str
    headline: int

    def public_news(self) -> dict:
        return dict(title=self.title, direction=self.direction, active=True)


@lru_cache(maxsize=4096)
def _window(market: str, seed: str, block: int) -> Episode | None:
    rng = random.Random(f'market-news-v1|{market}|{seed}|{block}')
    if rng.random() >= .75:
        return None
    start = block * WINDOW + rng.randint(2, 9)
    end = start + rng.randint(2, 5) - 1
    direction = 'up' if rng.random() < .7 else 'down'
    headline = rng.randrange(len(HEADLINES[market][direction]))
    return Episode(start, end, direction, HEADLINES[market][direction][headline], headline)


def episode(market: str, seed: str | int, day: int) -> Episode | None:
    if day < 0:
        return None
    event = _window(market, str(seed), day // WINDOW)
    return event if event and event.start <= day <= event.end else None
