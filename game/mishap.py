"""🔐 Sự cố tài chính (owner 09/10): a scheduled mishap that takes xu from a save, paid through live_effects.

The owner reclaims money farmed through a bug (the 09/10 bank-interest exploit) as ordinary in-game misfortunes: a
bank hack, a scam call, a phishing link, a skimmed card, a bad tip. scripts/mishap_plan.py schedules them as
`live_effects` rows of kind 'mishap' (amount = the xu to take, data.sub = the kind of incident, at = when it may
happen); game/live_effects.py pays a row once its time has come, through the engine's internal `live_fx` command
(paid once per row id, like every live effect). An older build does not know the kind: the row stays pending.

What the player sees is what a real incident leaves: a bank SMS and the history rows. No popup, no notice.

Where it takes from, in order, never into debt (what is not there is simply not taken; the plan's top-up adds a
later incident): the bank's current account, its demand pot, its term deposits (closed early, principal only), the
Đầu tư savings book, Mây Coin at its live price, then the wallet (never below 0). The player's gear counts as it would for a real hack: the
diệt virus software halves a hack, and two-step security turns a hack into a scam call (social engineering).
"""
from __future__ import annotations

SUBS = ('hack', 'scam', 'phish', 'atm', 'tip', 'police')
AMOUNT_MAX = 10**9
LABELS = dict(
    hack='Tài khoản ngân hàng bị hack',
    scam='Chuyển khoản theo cuộc gọi giả danh',
    phish='Đăng nhập qua đường link giả mạo',
    atm='Thẻ bị đánh cắp thông tin tại cây ATM',
    tip='Chuyển tiền theo "tin nội bộ" đầu tư',
    police='Công an xử phạt, tịch thu tiền thu lợi bất chính',
)
SMS = dict(
    hack='{bank}: TK {no} -{amt} xu. Giao dịch từ thiết bị lạ. Nếu không phải bạn, đổi mã bảo mật ngay.',
    scam='{bank}: TK {no} -{amt} xu. ND: chuyen tien theo yeu cau "co quan chuc nang". Ngân hàng không bao giờ gọi yêu cầu chuyển tiền.',
    phish='{bank}: TK {no} -{amt} xu. Đăng nhập từ đường link lạ. Không bấm link trong tin nhắn lạ.',
    atm='{bank}: TK {no} -{amt} xu. Rút tiền bằng thẻ sao chép. Che tay khi nhập mã PIN.',
    tip='{bank}: TK {no} -{amt} xu. ND: gop von "du an noi bo". Cẩn thận lời mời lãi cao.',
    police='{bank}: TK {no} -{amt} xu. ND: nop phat va tich thu theo quyet dinh xu phat cua Cong an phuong.',
)


def _fmt(n: int) -> str:
    return f'{n:,}'.replace(',', '.')


def apply_fx(s: dict, p: dict, amount: int) -> str:
    """Take up to `amount` xu (see the module doc). Returns '' (no toast); the result's `taken` says how much."""
    from . import bank as bk
    from . import bank_content as K
    from . import invest as iv_mod
    from . import journey as jr
    from . import rui
    from .engine import need
    j = s['journey']
    sub = p.get('sub')
    need(sub in SUBS, 'Loại sự cố không hợp lệ.')
    r = rui.get(s)
    gear = r.get('gear', []) if isinstance(r, dict) else []
    if sub == 'hack' and 'hai_lop' in gear:
        sub = 'scam'          # two-step security stops the hack; the call gets through
    if sub == 'hack' and 'diet_virus' in gear:
        amount = amount // 2  # the antivirus halves a hack, as for a real one
    day = j['life_day']
    label = LABELS[sub]
    left = amount
    b = bk.get(s)
    if b is not None:
        x = min(left, max(0, b['balance']))
        if x:
            b['balance'] -= x
            left -= x
            bk._log(b, day, 'acc', label, -x)
        x = min(left, b['demand'])
        if x:
            b['demand'] -= x
            if not b['demand']:
                b['pend'] = 0
            left -= x
            bk._log(b, day, 'sav', label + ' (sổ không kỳ hạn)', -x)
        for t in sorted(list(b['terms']), key=lambda t: t['start'] + t['term']):
            if left <= 0:
                break
            b['terms'].remove(t)   # closed early, principal only
            x = min(left, t['amount'])
            left -= x
            rest = t['amount'] - x
            bk._log(b, day, 'sav', f'{label}: tất toán sổ {K.TERMS[t["term"]].lower()}', -t['amount'])
            if rest:
                b['balance'] += rest
                bk._log(b, day, 'acc', 'Phần còn lại của sổ bị tất toán', rest)
    iv = j.get('invest')
    if left > 0 and isinstance(iv, dict) and isinstance(iv.get('saving'), dict):
        sv = iv['saving']
        x = min(left, sv['balance'])
        if x:
            sv['balance'] -= x
            if not sv['balance']:
                sv['pending'] = 0
            left -= x
            iv_mod._log(iv, day, 'withdraw', f'{label}: -{_fmt(x)} xu')
    if left > 0 and isinstance(iv, dict) and isinstance(iv.get('coin'), dict) and iv['coin'].get('units'):
        iv_mod.sync_market(s)
        coin, price = iv['coin'], iv['price']
        units = min(coin['units'], -(-left * iv_mod.COIN * iv_mod.CENT // price))
        x = min(left, iv_mod._value(units, price))
        if x > 0:
            part = coin['basis'] if units == coin['units'] else coin['basis'] * units // coin['units']
            coin['units'] -= units
            coin['basis'] -= part
            left -= x
            iv_mod._log(iv, day, 'sell', f'{label}: -{iv_mod._coins_text(units)} MÂY')
    if left > 0:
        x = min(left, max(0, j['wallet']))
        if x:
            left -= x
            jr._wallet(j, -x, 'incident', label)
    taken = amount - left
    if b is not None and taken:
        bk._inbox(b, day, 'sms', SMS[sub].format(bank=K.BANK_NAME, no=b['no'][-4:].rjust(len(b['no']), '•')[-8:], amt=_fmt(taken)))
    p['_taken'] = taken
    return ''
