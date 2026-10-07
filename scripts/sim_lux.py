#!/usr/bin/env python3
"""How fast 🛍️ Mua sắm (game/lux.py, game/estates.py) drains a player's xu over one real month, played through the
real engine (every price, cap, refusal and the monthly bills are the game's own).

Players, from DESIGN_0610 §0.1 (production 06/10): the wallet of their percentile, and an income per REAL day that
squares with how their wealth was built. The top balances (3.4 M, 1.9 M, 1.6 M) were made in about five weeks, so the
richest earn about 100,000 xu a real day and the 10th about 45,000; p99 saves reached life day ~207 in that time, so
the most engaged play about 6 life days a real day. Each profile is a plausible, engaged use of the shop (not a bot that
buys everything): what a player of that wealth would pick, within the game's caps (one trip, one party, one flight,
one lesson a life day).

"Gone for good" = what the month destroyed: start wealth + income − end wealth, every asset still owned counted at its
buy-back price (60 %), the 💰 board's own rule (game/wealth.py). No database: the commands' wallet and bank effects only
(the public sponsorships' slot and fireworks checks live in the database and never refuse here).

    python scripts/sim_lux.py [--days 30]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game import journey as jr  # noqa: E402
from game import lux  # noqa: E402
from game.engine import GameError, apply_action, new_state  # noqa: E402

CAREERS = ('florist', 'pho', 'milk_tea')


def save(wallet: int, bank: int) -> dict:
    s = new_state()
    jr.enable_story(s, 4242)
    j = s['journey']
    j['gender'], j['wallet'] = 'female', wallet + bank
    j['days'] = [dict(c=c, d=1, m='normal') for c in CAREERS]
    s, _ = apply_action(s, None, 'jr_bk_open', {})
    if bank:
        s, _ = apply_action(s, None, 'jr_bk_deposit', dict(amount=bank))
    return s


def worth(s: dict) -> int:
    j = s['journey']
    return j['wallet'] + j['bank']['balance'] + lux.worth(j)


class Player:
    def __init__(self, name, wallet, bank, per_day, pace, plan, **kw):
        self.name, self.s, self.pace, self.plan, self.kw = name, save(wallet, bank), pace, plan, kw
        self.income = per_day // pace            # a life day's share of a real day's income
        self.spent: dict[str, int] = {}

    def do(self, label, action, **p):
        before = worth(self.s)
        try:
            self.s, _ = apply_action(self.s, None, action, p)
        except GameError:
            return False
        self.spent[label] = self.spent.get(label, 0) + before - worth(self.s)
        return True

    def day(self, n):
        j = self.s['journey']
        jr._wallet(j, self.income, 'salary', 'Lương ngày')
        j['life_day'] += 1
        self.do('🧾 phí hạng sang', 'jr_seen', ids=['x'])   # the morning's bills (journey.after)
        self.plan(self, n, self.pace, **self.kw)


def visa(p, c):
    if lux.visa_left(p.s, c) < 2:
        co = lux.COUNTRY[c]
        short = co['bank'] * co['trip'] - p.s['journey']['bank']['balance']
        if short > 0 and p.s['journey']['wallet'] >= short:   # the bank statement: savings moved, not spent
            p.do('✈️ du lịch', 'jr_bk_deposit', amount=short)
        if lux.doc_problem(p.s, c, 'anh'):
            p.do('✈️ du lịch', 'jr_lux_photo')
        if c == 'chau_au' and p.s['journey']['lux']['ins'] != c:
            p.do('✈️ du lịch', 'jr_lux_insure', country=c)
        answers = [lux.C.INTERVIEW[q]['ok'] for q in lux.asked(p.s, c)]
        p.do('✈️ du lịch', 'jr_lux_visa', country=c, docs=list(lux.COUNTRY[c]['docs']), answers=answers, confirm=True)


def every(n, pace, real_days, at=1):
    """True on the life day n that falls `at` real days into each period of `real_days` real days."""
    return n % (real_days * pace) == at % (real_days * pace)


def p90(p, n, pace):
    if n == 1:
        p.do('🎓 khóa học', 'jr_lux_course', id='tieng_trung', confirm=True)
    p.do('🎓 khóa học', 'jr_lux_study', id='tieng_trung')
    if n == 10 * pace:   # a trip to China once its course is done
        visa(p, 'trung_quoc')
        p.do('✈️ du lịch', 'jr_lux_trip', country='trung_quoc', cls='pho_thong', confirm=True)
        p.do('✈️ du lịch', 'jr_lux_souv', id='am_tu_sa')
    if every(n, pace, 10, 5):
        p.do('🎉 tiệc', 'jr_lux_party', kind='sinh_nhat', tier='binh_dan', guests=10, confirm=True)
    if n == 20 * pace:
        p.do('💎 sưu tập', 'jr_lux_buy', id='tr_dong_ho', confirm=True)
    if n == 25 * pace:
        p.do('💎 sưu tập', 'jr_lux_buy', id='rv_da_lat', confirm=True)
        p.do('💎 sưu tập', 'jr_lux_open', id='rv_da_lat', confirm=True)


def p99(p, n, pace):
    if n == 1:
        p.do('🎓 khóa học', 'jr_lux_course', id='tieng_han', confirm=True)
    p.do('🎓 khóa học', 'jr_lux_study', id='tieng_han')
    if every(n, pace, 10, 4):
        c = ('han_quoc', 'nhat_ban', 'trung_quoc')[n // (10 * pace) % 3]
        visa(p, c)
        p.do('✈️ du lịch', 'jr_lux_trip', country=c, cls='pho_thong', confirm=True)
        p.do('✈️ du lịch', 'jr_lux_souv', id=lux.C.SOUVENIRS[c][1]['id'])
    if every(n, pace, 10, 8):
        p.do('🎉 tiệc', 'jr_lux_party', kind='sinh_nhat', tier='nha_hang', guests=20, confirm=True)
    if n == 12 * pace:
        p.do('💎 sưu tập', 'jr_lux_buy', id='dh_lan_bien', confirm=True)
    if n == 24 * pace:
        p.do('💎 sưu tập', 'jr_lux_buy', id='rv_phap_20', confirm=True)
        p.do('💎 sưu tập', 'jr_lux_open', id='rv_phap_20', confirm=True)


def rich(p, n, pace, villa, fly, pieces, trips=4, parties=15, sponsor=True):
    if n == 1:
        p.do('🏰 dinh thự', 'jr_lux_buy', id=villa, confirm=True)
        p.do('🏰 dinh thự', 'jr_lux_live', id=villa)
        if fly:
            p.do('🛫 phi cơ', 'jr_lux_buy', id=fly, confirm=True)
        p.do('🎓 khóa học', 'jr_lux_course', id='mba', confirm=True)
    p.do('🎓 khóa học', 'jr_lux_study', id='mba')
    if fly and every(n, pace, 2, 1):
        p.do('🛫 phi cơ', 'jr_lux_use', id=fly)
    if every(n, pace, trips, 2):   # a trip abroad every few days: royal class half the time
        k = n // (trips * pace)
        c = ('nhat_ban', 'chau_au', 'my', 'han_quoc')[k % 4]
        visa(p, c)
        p.do('✈️ du lịch', 'jr_lux_trip', country=c, cls='hoang_gia' if k % 4 in (1, 2) else 'thuong_gia', confirm=True)
        p.do('✈️ du lịch', 'jr_lux_souv', id=lux.C.SOUVENIRS[c][2]['id'])
    if every(n, pace, parties, 6):
        p.do('🎉 tiệc', 'jr_lux_party', kind='tan_gia', tier='sang', guests=60, confirm=True)
    if n == 10 * pace:
        p.do('🎆 Mạnh Thường Quân', 'jr_lux_give', kind='phao_hoa', size='lon', confirm=True)
        p.do('🎆 Mạnh Thường Quân', 'jr_lux_give', kind='cot_den', slot=2, msg='me', confirm=True)
    if n == 20 * pace and sponsor:
        p.do('🎆 Mạnh Thường Quân', 'jr_lux_give', kind='hoi_cho', confirm=True)
    for i, piece in enumerate(pieces):
        if n == (5 + 8 * i) * pace:
            p.do('💎 sưu tập', 'jr_lux_buy', id=piece, confirm=True)


def run(days: int) -> None:
    people = [
        Player('p90 · ví 3.300, ~1.400 xu/ngày thật, 2 ngày sống/ngày', 3300, 0, 1400, 2, p90),
        Player('p99 · ví 26.400, ~8.000 xu/ngày thật, 3 ngày sống/ngày', 26400, 0, 8000, 3, p99),
        Player('top-10 · 1.600.000, ~45.000 xu/ngày thật, 6 ngày sống/ngày, vừa phải', 400_000, 1_200_000, 45_000, 6, rich,
               villa='bt_dong_duong', fly='', pieces=('tui_ca_sau',), trips=7, parties=30, sponsor=False),
        Player('top-10 · như trên, chơi lớn', 400_000, 1_200_000, 45_000, 6, rich,
               villa='bt_dong_duong', fly='', pieces=('tui_ca_sau', 'tg_ky_lan')),
        Player('top-3 · 1.900.000, ~55.000 xu/ngày thật, 6 ngày sống/ngày', 400_000, 1_500_000, 55_000, 6, rich,
               villa='bt_bien', fly='truc_thang_vip', pieces=('dh_tourbillon',)),
        Player('top-1 · 3.400.000, ~100.000 xu/ngày thật, 6 ngày sống/ngày, vừa phải', 600_000, 2_800_000, 100_000, 6, rich,
               villa='penthouse_sky', fly='truc_thang_vip', pieces=('dh_tourbillon',), trips=7, parties=30, sponsor=False),
        Player('top-1 · như trên, chơi lớn (đảo riêng)', 600_000, 2_800_000, 100_000, 6, rich,
               villa='dinh_thu_dao', fly='truc_thang_vip', pieces=('dh_tourbillon', 'tr_son_dau')),
    ]
    print(f'Một tháng = {days} ngày thật.\n')
    for p in people:
        start = worth(p.s)
        income = 0
        for n in range(1, days * p.pace + 1):
            p.day(n)
            income += p.income
        end = worth(p.s)
        gone = start + income - end
        upk = p.s['journey'].get('lux', {}).get('upk') or {}
        print(f'{p.name}\n  đầu tháng {start:,} · thu nhập {income:,} · cuối tháng {end:,} (tài sản tính giá bán lại 60 %)')
        print(f'  mất hẳn {gone:,} xu = {100 * gone / start:.0f} % tài sản đầu tháng · {100 * gone / income:.0f} % thu nhập tháng'
              f' · tài sản {100 * (end - start) / start:+.0f} % · phí hạng sang {upk.get("paid", 0):,}')
        for k, v in sorted(p.spent.items(), key=lambda kv: -kv[1]):
            if v:
                print(f'    {k:22} {v:>12,}')
        print()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--days', type=int, default=30)
    run(ap.parse_args().days)
