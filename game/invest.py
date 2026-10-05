"""Đầu tư cá nhân: savings at the neighbourhood bank, a fictional crypto
("Mây Coin") and the occasional too-good-to-be-true project (a scam).

Everything lives under `s['journey']['invest']` and moves money only between
the journey wallet and the invest holdings, through `journey._wallet` so the
wallet history, max_wallet, debt flags and titles keep working. Scam
offers and payouts are deterministic from `journey.seed` and the life day.
Coin quotes are shared wall-clock prices; savings and scams keep their life-day clock.
Server authoritative: the client renders `public()` and sends `iv_*` commands.
Design: docs/superpowers/specs/2026-09-29-invest-design.md

💧 Lãi bậc thang (owner 03/10, the xu sinks, docs/ECONOMY_SINKS.md): the savings pay RATE_MILLI (0,3 %/ngày) on the
first SAVE_TIER xu of the balance and RATE_HI_MILLI (0,1 %/ngày, about the bank's 7-day term) on the rest, so a large
pile of xu no longer earns more than the street's work. A term that began before the save's bills block
(upkeep.since) keeps the flat rate until it ends; the rule is shown with the rate (public rules save_tier, rate_hi_milli).
"""
from __future__ import annotations

import copy
import math
import random
from . import archive as ar
from . import market_trends as mt
from . import realtime_market as rm

VERSION = 1
UNLOCK = 500            # the wallet must have held this much once (stats.max_wallet)
BASE = 10000            # Mây Coin base price, hundredths of a xu (100 xu)
PRICE_MIN, PRICE_MAX = 100, 10_000_000
COIN = 1000             # units per coin (thousandths)
CENT = 100              # price scale
REALTIME_KEY = 'coin_realtime_v'  # optional journey sidecar, never part of legacy invest schema
MAX_UNITS = 10**15       # includes maximum valid legacy units redenominated at PRICE_MAX
FEE_PCT = 2
MIN_TRADE = 10
RATE_MILLI = 3          # 0.3 % a day: 3 thousandths of a xu per xu
SAVE_TIER = 20000       # ... on the first SAVE_TIER xu of the balance (lãi bậc thang, 03/10)
RATE_HI_MILLI = 1       # 0.1 % a day on the part above SAVE_TIER
TERM = 7
PREHISTORY = 20
HISTORY = 30
LOG_MAX = 20
SCAM_CHANCE = .08
SCAM_OPEN = 3           # an offer stays open this many life days
SCAM_ECHO = 4           # a declined/expired project collapses this long after the offer
SCAM_COOLDOWN = 10
SCAM_MIN = 20
SCAM_PAY_PCT = 4
AMOUNT_MAX = 10**7
KIND = 'invest'         # journey history kind (already in journey.HISTORY_KINDS)

SCAMS = {
    'moon': dict(name='MoonMây Token', emoji='🚀',
                 pitch='Lãi 30%/tuần, rút bất cứ lúc nào! Mời bạn bè tham gia nhận thêm 10% hoa hồng.'),
    'gold': dict(name='Vàng Số 4.0', emoji='🪙',
                 pitch='Chuyên gia bảo đảm lãi 30%/tuần, KHÔNG rủi ro. Chỉ còn 12 suất, vào ngay kẻo lỡ!'),
    'farm': dict(name='Nông Trại Ảo X100', emoji='🐔',
                 pitch='Nuôi gà ảo, mỗi ngày đẻ trứng vàng. Lãi 30%/tuần, mời càng nhiều người càng lãi.'),
    'boba': dict(name='Trà Sữa Coin', emoji='🧋',
                 pitch='Đồng coin của giới trẻ! Cam kết lãi 30%/tuần, mời 3 bạn nhận thưởng nóng.'),
}
RED_FLAGS = ['Hứa lãi rất cao và “cam kết” chắc chắn', 'Nói “không rủi ro”',
             'Thưởng khi rủ thêm người vào', 'Giục vào ngay, “chỉ còn vài suất”']
SCAM_STAGES = ('offer', 'joined', 'declined', 'expired')
LOG_KINDS = ('buy', 'sell', 'save', 'withdraw', 'interest', 'pump', 'crash',
             'scam_offer', 'scam_join', 'scam_pay', 'scam_gone', 'scam_decline', 'scam_news')
BADGES = {
    'first_coin': dict(emoji='🪙', name='Lần đầu thử coin', desc='Mua Mây Coin lần đầu.'),
    'first_interest': dict(emoji='🏦', name='Tiền đẻ ra tiền', desc='Nhận lãi tiết kiệm trọn một kỳ.'),
    'scam_spotter': dict(emoji='🛡️', name='Tỉnh táo trước lãi khủng', desc='Từ chối một dự án hứa lãi quá cao.'),
    'rug_lesson': dict(emoji='🕳️', name='Bài học đắt giá', desc='Gửi tiền vào dự án lãi khủng và mất trắng.'),
}
STATS = ('declined', 'joined', 'lost', 'next_scam')
LOCKED = f'Mục đầu tư mở khi ví của bạn từng có {UNLOCK} xu.'


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def accrual(balance: int, flat: bool = False) -> int:
    """One day's interest on `balance`, in thousandths of a xu: RATE_MILLI on the first SAVE_TIER xu, RATE_HI_MILLI on
    the rest (`flat`: RATE_MILLI on all of it, a term begun before the tier)."""
    balance = max(0, int(balance))
    if flat:
        return balance * RATE_MILLI
    return min(balance, SAVE_TIER) * RATE_MILLI + max(0, balance - SAVE_TIER) * RATE_HI_MILLI


def flat_term(s: dict, sv: dict) -> bool:
    """The current term began before the tier existed for this save (game/upkeep.py since): it keeps the flat rate."""
    from .upkeep import since
    start = since(s)
    return start is None or sv['term_day'] < start


def _fee(amount: int) -> int:
    return max(1, -(-amount * FEE_PCT // 100))


def _value(units: int, price: int) -> int:
    return units * price // (COIN * CENT)


def _live_units(j: dict, iv: dict) -> int:
    """Project legacy holdings at the fixed epoch, never at first-login's quote.

    Floor to a thousandth of a coin; retain one unit for nonzero dust so its
    cost basis survives. Epoch precision loss/gain is strictly below 0.1 xu.
    """
    units = iv['coin']['units']
    if j.get(REALTIME_KEY) == 1 or not units:
        return units
    return max(1, units * iv['price'] // rm.base_price('coin'))


def market_clock(q: dict) -> dict:
    return dict(tick=q['tick'], market_day=q['market_day'], as_of=q['as_of'], next_at=q['next_at'],
                tick_seconds=rm.TICK_SECONDS, day_seconds=rm.DAY_SECONDS, timestamps=list(q['timestamps']))


def sync_market(s: dict) -> dict:
    """Persist the one-time conversion and a current quote during a transaction."""
    iv = _state(s)
    q = rm.quote('coin')
    iv['coin']['units'] = _live_units(s['journey'], iv)
    s['journey'][REALTIME_KEY] = 1
    iv['price'], iv['prices'] = q['price'], list(q['history'])
    return q


def value(s: dict) -> int:
    """Read-only live coin valuation, including unconverted legacy holdings."""
    j = s.get('journey') or {}
    iv = j.get('invest')
    return _value(_live_units(j, iv), rm.quote('coin')['price']) if iv else 0


def _step(price: int, rng: random.Random) -> tuple[int, str]:
    """Legacy walk, retained verbatim for initial prehistory and old saves."""
    r = rng.random()
    if r < .04:
        move, kind = -rng.uniform(.30, .50), 'crash'
    elif r < .09:
        move, kind = rng.uniform(.25, .45), 'pump'
    else:
        move, kind = max(-.15, min(.15, rng.gauss(.004, .055))), ''
    move += .04 * math.log(BASE / price)
    return max(PRICE_MIN, min(PRICE_MAX, round(price * (1 + move)))), kind


def _market_step(price: int, seed: int, day: int) -> tuple[int, mt.Episode | None]:
    """Future life-day close: sustained news, otherwise a gently rising noisy market.

    The linear anchor avoids compounding into PRICE_MAX after a long journey.
    Mean reversion only acts on quiet days, so it cannot reverse a headline.
    """
    event = mt.episode('coin', seed, day)
    rng = random.Random(f'may-trend-v1|{seed}|{day}')
    if event:
        move = rng.uniform(.015, .04) * (1 if event.direction == 'up' else -1)
    else:
        anchor = min(PRICE_MAX / 4, BASE * (1 + .001 * day))
        pull = max(-.035, min(.035, .018 * math.log(anchor / price)))
        move = max(-.09, min(.09, rng.gauss(.0018, .018) + pull))
    return max(PRICE_MIN, min(PRICE_MAX, round(price * math.exp(move)))), event


def initial(seed: int = 0, day: int = 1) -> dict:
    price, prices = BASE, []
    for i in range(PREHISTORY):
        price, _ = _step(price, random.Random(f'may-pre|{seed}|{i}'))
        prices.append(price)
    return dict(version=VERSION, day=int(day), price=price, prices=prices,
                coin=dict(units=0, basis=0, realised=0, fees=0, trades=0),
                saving=dict(balance=0, term_day=int(day), pending=0, earned=0, forfeited=0),
                scam=None, log=[], stats=dict(declined=0, joined=0, lost=0, next_scam=0), badges=[])


def migrate(s: dict) -> dict:
    """Adds `s['journey']['invest']` (setdefault only). Call after journey.migrate/upgrade."""
    j = s.get('journey')
    if not isinstance(j, dict):
        return s
    base = initial(int(j.get('seed', 0)), int(j.get('life_day', 1)))
    iv = j.setdefault('invest', base)
    if isinstance(iv, dict):
        for k, v in base.items():
            iv.setdefault(k, copy.deepcopy(v))
        for k in ('coin', 'saving', 'stats'):
            if isinstance(iv[k], dict):
                for kk, vv in base[k].items():
                    iv[k].setdefault(kk, vv)
    return s


def _state(s: dict) -> dict:
    j = s['journey']
    if 'invest' not in j:
        migrate(s)
    return j['invest']


def unlocked(s: dict) -> bool:
    return int(s['journey'].get('stats', {}).get('max_wallet', 0)) >= UNLOCK


def _log(iv: dict, day: int, kind: str, text: str) -> None:
    iv['log'] = ar.last(iv['log'] + [dict(day=int(day), kind=kind, text=text[:160])], LOG_MAX, 'invest.log', ar.JOURNEY)


def _badge(iv: dict, bid: str) -> bool:
    if bid in iv['badges']:
        return False
    iv['badges'].append(bid)
    return True


def _wallet(s: dict, amount: int, label: str) -> None:
    jr = _jr()
    jr._wallet(s['journey'], amount, KIND, label)


def _price_text(price: int) -> str:
    return f'{price / CENT:,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def _coins_text(units: int) -> str:
    return f'{units / COIN:,.3f}'.rstrip('0').rstrip('.').replace(',', ' ').replace('.', ',').replace(' ', '.')


def _pct(a: int, b: int) -> int:
    return round((b - a) * 100 / a) if a else 0


# ---------------------------------------------------------------- daily tick
def _tick(s: dict, iv: dict, d: int, notes: list[str]) -> None:
    """Close life day `d`: accrue interest and run the scam clock."""
    j = s['journey']
    seed = j.get('seed', 0)
    # Savings: daily accrual, credited at the end of each 7-day term.
    sv = iv['saving']
    if sv['balance'] > 0:
        sv['pending'] += accrual(sv['balance'], flat_term(s, sv))
        if d + 1 - sv['term_day'] >= TERM:
            gain = sv['pending'] // 1000
            sv['pending'] %= 1000
            sv['term_day'] = d + 1
            if gain:
                sv['balance'] += gain
                sv['earned'] += gain
                _log(iv, d, 'interest', f'Ngân hàng phố cộng {gain} xu tiền lãi kỳ {TERM} ngày vào sổ tiết kiệm.')
                notes.append(f'🏦 Sổ tiết kiệm vừa nhận {gain} xu tiền lãi.')
                _badge(iv, 'first_interest')
    # Scam lifecycle.
    sc, st = iv['scam'], iv['stats']
    if sc and sc['stage'] == 'joined':
        name = SCAMS[sc['kind']]['name']
        if sc['paid_days'] < sc['pay_days']:
            pay = max(1, sc['stake'] * SCAM_PAY_PCT // 100)
            sc['paid'] += pay
            sc['paid_days'] += 1
            _wallet(s, pay, f'“Lãi” từ dự án {name}')
            _log(iv, d, 'scam_pay', f'{name} trả {pay} xu “tiền lãi” vào ví. Nhóm chat rộn ràng khoe lãi.')
            notes.append(f'💸 {name} vừa trả {pay} xu “lãi”.')
        else:
            lost = sc['stake'] - sc['paid']
            st['lost'] += lost
            _log(iv, d, 'scam_gone', f'{name} biến mất: trang web sập, nhóm chat bị xóa. {sc["stake"]} xu gửi vào không lấy lại được '
                                     f'(đã nhận lại {sc["paid"]} xu, lỗ {lost} xu).')
            notes.append(f'🕳️ Dự án {name} đã biến mất cùng {sc["stake"]} xu của bạn. Lãi hứa càng cao, rủi ro càng lớn.')
            _badge(iv, 'rug_lesson')
            iv['scam'] = None
            st['next_scam'] = d + 1 + SCAM_COOLDOWN
    elif sc and sc['stage'] == 'offer' and d + 1 >= sc['day'] + SCAM_OPEN:
        sc['stage'] = 'expired'
    elif sc and sc['stage'] in ('declined', 'expired') and d + 1 >= sc['day'] + SCAM_ECHO:
        name = SCAMS[sc['kind']]['name']
        _log(iv, d, 'scam_news', f'Tin phố: dự án {name} đã sập, ai gửi tiền vào đều mất trắng.'
                                 + (' May mà bạn đã tỉnh táo.' if sc['stage'] == 'declined' else ''))
        iv['scam'] = None
        st['next_scam'] = d + 1 + SCAM_COOLDOWN
    elif not sc and unlocked(s) and d + 1 >= st['next_scam']:
        rng = random.Random(f'scam|{seed}|{d}')
        if rng.random() < SCAM_CHANCE:
            kind = rng.choice(sorted(SCAMS))
            iv['scam'] = dict(kind=kind, stage='offer', day=d + 1, stake=0, paid=0, pay_days=rng.choice((1, 2)), paid_days=0)
            _log(iv, d + 1, 'scam_offer', f'Có người nhắn rủ bạn vào dự án {SCAMS[kind]["name"]}: “lãi 30%/tuần”.')
            notes.append(f'📣 Có lời mời đầu tư “{SCAMS[kind]["name"]}” lãi 30%/tuần. Xem ở mục Đầu tư.')


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Sync the real-time quote, then catch savings/scams up to `journey.life_day`.
    Idempotent within a quote tick; life days never drive coin prices.
    The existing 400-day replay safety cap also bounds exact batch/day equivalence.
    """
    j = s.get('journey')
    if not isinstance(j, dict):
        return []
    iv = _state(s)
    sync_market(s)
    notes: list[str] = []
    target = int(j['life_day'])
    iv['day'] = max(iv['day'], target - 400)
    while iv['day'] < target:
        _tick(s, iv, iv['day'], notes)
        iv['day'] += 1
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- commands
def _amount(p: dict, low: int, most: int, what: str) -> int:
    """`{amount:int}` or `{all:true}` (all = `most`)."""
    e = _core()
    e.need(isinstance(p, dict) and set(p) <= {'amount', 'all'} and ('amount' in p) != ('all' in p),
           'Chọn số xu hoặc “Tất cả” nhé.')
    if 'all' in p:
        e.need(p['all'] is True, 'Chọn số xu hoặc “Tất cả” nhé.')
        e.need(most >= low, f'{what} cần ít nhất {low} xu.')
        return most
    amount = p['amount']
    e.need(type(amount) is int and low <= amount <= AMOUNT_MAX, f'{what} cần là số xu nguyên, ít nhất {low} xu.')
    return amount


def apply(s: dict, name: str, p: dict) -> dict:
    """`iv_*` commands. Checks everything before changing anything."""
    e = _core()
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác đầu tư không hợp lệ.', 'unknown_action')
    need(unlocked(s), LOCKED, 'locked')
    iv = _state(s)
    # Stage price/quantity conversion until payload and funds checks succeed.
    # Failed direct calls, as well as failed engine transactions, keep the save.
    if name in ('iv_buy', 'iv_sell'):
        projected_units = _live_units(j, iv)
        iv = copy.deepcopy(iv)
        q = rm.quote('coin')
        iv['coin']['units'] = projected_units
        iv['price'], iv['prices'] = q['price'], list(q['history'])
    day, wallet = j['life_day'], j['wallet']
    coin, sv, sc = iv['coin'], iv['saving'], iv['scam']
    result = dict(message='', effects=[])
    if name == 'iv_save':
        amount = _amount(p, 1, max(0, wallet), 'Tiền gửi')
        need(amount <= wallet, 'Ví không đủ để gửi số này.')
        if sv['balance'] == 0:
            sv['term_day'], sv['pending'] = day, 0
        _wallet(s, -amount, 'Gửi tiết kiệm ở ngân hàng phố')
        sv['balance'] += amount
        _log(iv, day, 'save', f'Gửi {amount} xu vào sổ tiết kiệm.')
        tier = '' if sv['balance'] <= SAVE_TIER or flat_term(s, sv) else \
            f' cho {SAVE_TIER:,} xu đầu, phần trên lãi {RATE_HI_MILLI // 10},{RATE_HI_MILLI % 10}%/ngày'.replace(',', '.', 1)
        result['message'] = f'Đã gửi {amount} xu. Lãi {RATE_MILLI // 10},{RATE_MILLI % 10}%/ngày{tier}, cộng vào sổ mỗi {TERM} ngày.'
    elif name == 'iv_withdraw':
        need(sv['balance'] > 0, 'Sổ tiết kiệm đang trống.')
        amount = _amount(p, 1, sv['balance'], 'Tiền rút')
        need(amount <= sv['balance'], f'Sổ tiết kiệm chỉ có {sv["balance"]} xu.')
        lost = sv['pending'] // 1000
        sv['forfeited'] += lost
        sv['pending'] = 0
        sv['balance'] -= amount
        if sv['balance'] == 0:
            sv['term_day'] = day
        _wallet(s, amount, 'Rút tiền tiết kiệm')
        _log(iv, day, 'withdraw', f'Rút {amount} xu tiết kiệm' + (f', mất {lost} xu lãi kỳ này.' if lost else '.'))
        result['message'] = f'Đã rút {amount} xu về ví.' + (f' Rút trước kỳ hạn nên mất {lost} xu tiền lãi.' if lost else '')
    elif name == 'iv_buy':
        amount = _amount(p, MIN_TRADE, max(0, wallet), 'Lệnh mua')
        need(amount <= wallet, 'Ví không đủ để mua số này.')
        fee = _fee(amount)
        units = (amount - fee) * COIN * CENT // iv['price']
        need(units >= 1, 'Số tiền quá nhỏ để mua được coin.')
        _wallet(s, -amount, 'Mua Mây Coin')
        coin['units'] += units
        coin['basis'] += amount
        coin['fees'] += fee
        coin['trades'] += 1
        first = _badge(iv, 'first_coin')
        _log(iv, day, 'buy', f'Mua {_coins_text(units)} MÂY giá {_price_text(iv["price"])} xu (phí {fee} xu).')
        result['message'] = f'Đã mua Mây Coin bằng {amount} xu (phí {fee} xu).'
        if first:
            result['effects'].append('Giá coin cập nhật mỗi 10 phút thực. Chỉ dùng tiền nhàn rỗi nhé.')
    elif name == 'iv_sell':
        value = _value(coin['units'], iv['price'])
        need(coin['units'] > 0, 'Bạn chưa có Mây Coin để bán.')
        if p.get('all') is True and set(p) == {'all'}:
            units = coin['units']
        else:
            amount = _amount(p, MIN_TRADE, value, 'Lệnh bán')
            need(amount <= value, f'Coin của bạn chỉ trị giá khoảng {value} xu.')
            units = min(coin['units'], -(-amount * COIN * CENT // iv['price']))
        gross = _value(units, iv['price'])
        fee = _fee(gross)
        need(gross > fee, 'Số coin này bán ra không đủ trả phí.')
        part = coin['basis'] if units == coin['units'] else coin['basis'] * units // coin['units']
        proceeds = gross - fee
        coin['realised'] += proceeds - part
        coin['units'] -= units
        coin['basis'] -= part
        coin['fees'] += fee
        coin['trades'] += 1
        _wallet(s, proceeds, 'Bán Mây Coin')
        pnl = proceeds - part
        _log(iv, day, 'sell', f'Bán {_coins_text(units)} MÂY, nhận {proceeds} xu ({"lãi" if pnl >= 0 else "lỗ"} {abs(pnl)} xu).')
        result['message'] = f'Đã bán, nhận {proceeds} xu (phí {fee} xu). ' + (f'Lãi {pnl} xu.' if pnl >= 0 else f'Lỗ {-pnl} xu.')
    elif name == 'iv_scam_join':
        need(sc and sc['stage'] == 'offer', 'Lời mời này không còn nữa.')
        need(set(p) == {'amount'}, 'Chọn số xu nhé.')
        amount = p['amount']
        need(type(amount) is int and SCAM_MIN <= amount <= AMOUNT_MAX, f'Dự án nhận ít nhất {SCAM_MIN} xu.')
        need(amount <= wallet, 'Ví không đủ số này.')
        nm = SCAMS[sc['kind']]['name']
        _wallet(s, -amount, f'Chuyển vào dự án {nm}')
        sc.update(stage='joined', day=day, stake=amount, paid=0, paid_days=0)
        iv['stats']['joined'] += 1
        _log(iv, day, 'scam_join', f'Chuyển {amount} xu vào dự án {nm}.')
        result['message'] = f'Đã chuyển {amount} xu vào {nm}. Họ hứa trả lãi mỗi ngày.'
    elif name == 'iv_scam_decline':
        need(sc and sc['stage'] == 'offer', 'Lời mời này không còn nữa.')
        need(not p, 'Dữ liệu thao tác không hợp lệ.')
        nm = SCAMS[sc['kind']]['name']
        sc['stage'] = 'declined'
        iv['stats']['declined'] += 1
        first = _badge(iv, 'scam_spotter')
        _log(iv, day, 'scam_decline', f'Từ chối dự án {nm}.')
        result['message'] = 'Bạn đã từ chối. Lãi “cam kết” 30%/tuần, thưởng khi rủ người khác… là dấu hiệu lừa đảo quen thuộc.'
        if first:
            result['effects'].append(f'🛡️ Huy hiệu mới: {BADGES["scam_spotter"]["name"]}.')
    if name in ('iv_buy', 'iv_sell'):
        j['invest'] = iv
        j[REALTIME_KEY] = 1
    return result


def action(s: dict, name: str, p: dict) -> tuple[dict, dict]:
    """Engine entry point (like journey.action): apply, run journey hooks, validate."""
    e = _core()
    result = apply(s, name, p or {})
    _jr().after(s, None, name, p or {}, result)
    validate(s)
    e.validate_state(s)
    return s, result


COMMANDS = ('iv_save', 'iv_withdraw', 'iv_buy', 'iv_sell', 'iv_scam_join', 'iv_scam_decline')


# ---------------------------------------------------------------- views
def public(s: dict) -> dict:
    j = s['journey']
    iv = j.get('invest') or initial(int(j.get('seed', 0)), int(j.get('life_day', 1)))
    coin, sv, sc = iv['coin'], iv['saving'], iv['scam']
    flat = flat_term(s, sv) if sv['balance'] else False
    q = rm.quote('coin')
    units = _live_units(j, iv)
    value = _value(units, q['price'])
    prices = list(q['history'])
    scam = None
    if sc:
        meta = SCAMS[sc['kind']]
        scam = dict(kind=sc['kind'], stage=sc['stage'], name=meta['name'], emoji=meta['emoji'], pitch=meta['pitch'],
                    flags=list(RED_FLAGS), stake=sc['stake'], paid=sc['paid'],
                    days_left=max(0, sc['day'] + SCAM_OPEN - j['life_day']) if sc['stage'] == 'offer' else 0)
    return dict(
        unlocked=unlocked(s), need=UNLOCK, max_wallet=int(j['stats'].get('max_wallet', 0)), wallet=j['wallet'],
        life_day=j['life_day'],
        rules=dict(unlock=UNLOCK, fee_pct=FEE_PCT, min_trade=MIN_TRADE, rate_milli=RATE_MILLI, term=TERM, scam_min=SCAM_MIN,
                   coin=COIN, cent=CENT, save_tier=SAVE_TIER, rate_hi_milli=RATE_HI_MILLI),
        saving=dict(balance=sv['balance'], pending=sv['pending'] // 1000, earned=sv['earned'], forfeited=sv['forfeited'],
                    term_left=max(0, TERM - (j['life_day'] - sv['term_day'])) if sv['balance'] else TERM,
                    daily=accrual(sv['balance'], flat) // 1000, daily_milli=accrual(sv['balance'], flat), flat=flat),
        coin=dict(price=q['price'], prices=prices, change=round((q['price'] - q['previous']) * 100 / q['previous'], 2),
                  units=units, value=value, basis=coin['basis'], unrealised=value - coin['basis'] if units else 0,
                  realised=coin['realised'], fees=coin['fees'], trades=coin['trades'],
                  market_news=q['news'], market_clock=market_clock(q)),
        scam=scam, log=list(reversed(iv['log'])),
        badges=[dict(id=b, **BADGES[b]) for b in iv['badges']],
        stats=dict(declined=iv['stats']['declined'], joined=iv['stats']['joined'], lost=iv['stats']['lost']))


def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s.get('journey')
    if not isinstance(j, dict) or 'invest' not in j:
        return
    iv = j['invest']
    bad = 'Dữ liệu đầu tư không hợp lệ.'
    if REALTIME_KEY in j:
        need(type(j[REALTIME_KEY]) is int and j[REALTIME_KEY] == 1, bad, 'invalid_save')
    need(isinstance(iv, dict) and set(iv) == set(initial()), bad, 'invalid_save')
    need(iv['version'] == VERSION, bad, 'invalid_save')
    integer(iv['day'], 1, 10**6)
    need(iv['day'] <= j['life_day'], bad, 'invalid_save')
    integer(iv['price'], PRICE_MIN, PRICE_MAX)
    need(isinstance(iv['prices'], list) and 1 <= len(iv['prices']) <= HISTORY and iv['prices'][-1] == iv['price'], bad)
    for x in iv['prices']:
        integer(x, PRICE_MIN, PRICE_MAX)
    coin = iv['coin']
    need(isinstance(coin, dict) and set(coin) == {'units', 'basis', 'realised', 'fees', 'trades'}, bad)
    integer(coin['units'], 0, MAX_UNITS if j.get(REALTIME_KEY) == 1 else 10**12)
    integer(coin['basis'], 0, 10**9)
    integer(coin['realised'], -10**9, 10**9)
    integer(coin['fees'], 0, 10**9)
    integer(coin['trades'], 0, 10**7)
    need(coin['units'] or not coin['basis'], bad)
    sv = iv['saving']
    need(isinstance(sv, dict) and set(sv) == {'balance', 'term_day', 'pending', 'earned', 'forfeited'}, bad)
    integer(sv['balance'], 0, 10**9)
    integer(sv['term_day'], 1, 10**6)
    need(sv['term_day'] <= j['life_day'], bad)
    integer(sv['pending'], 0, 10**12)
    integer(sv['earned'], 0, 10**9)
    integer(sv['forfeited'], 0, 10**9)
    sc = iv['scam']
    if sc is not None:
        need(isinstance(sc, dict) and set(sc) == {'kind', 'stage', 'day', 'stake', 'paid', 'pay_days', 'paid_days'}, bad)
        need(sc['kind'] in SCAMS and sc['stage'] in SCAM_STAGES, bad)
        integer(sc['day'], 1, 10**6)
        integer(sc['stake'], 0, AMOUNT_MAX)
        integer(sc['paid'], 0, AMOUNT_MAX)
        integer(sc['pay_days'], 1, 2)
        integer(sc['paid_days'], 0, sc['pay_days'])
        need((sc['stage'] == 'joined') == (sc['stake'] >= SCAM_MIN), bad)
    need(isinstance(iv['log'], list) and len(iv['log']) <= LOG_MAX, bad)
    for row in iv['log']:
        need(isinstance(row, dict) and set(row) == {'day', 'kind', 'text'} and row['kind'] in LOG_KINDS, bad)
        integer(row['day'], 1, 10**6)
        txt(row['text'], 160)
    st = iv['stats']
    need(isinstance(st, dict) and set(st) == set(STATS), bad)
    for v in st.values():
        integer(v, 0, 10**9)
    need(isinstance(iv['badges'], list) and len(iv['badges']) == len(set(iv['badges'])) and set(iv['badges']) <= set(BADGES), bad)
