"""Scheduled financial incidents debit only their own liquid pocket.

Old requested amounts remain valid, but current safety caps always apply.
Savings, investments, and workplace funds are never liquidated.
"""
from __future__ import annotations

from .loss_limits import bounded_loss

SUBS = ('hack', 'scam', 'phish', 'atm', 'tip', 'police', 'thug')
WALLET_SUBS = ('police', 'thug')
AMOUNT_MAX = 10**9
LABELS = dict(
    hack='Tài khoản ngân hàng bị hack',
    scam='Chuyển khoản theo cuộc gọi giả danh',
    phish='Đăng nhập qua đường link giả mạo',
    atm='Thẻ bị đánh cắp thông tin tại cây ATM',
    tip='Chuyển tiền theo "tin nội bộ" đầu tư',
    police='Công an xử phạt',
    thug='Côn đồ đến đòi tiền bảo kê',
)
SMS = dict(
    hack='{bank}: TK {no} -{amt} xu. Giao dịch từ thiết bị lạ. Nếu không phải bạn, đổi mã bảo mật ngay.',
    scam='{bank}: TK {no} -{amt} xu. ND: chuyen tien theo yeu cau "co quan chuc nang". Ngân hàng không bao giờ gọi yêu cầu chuyển tiền.',
    phish='{bank}: TK {no} -{amt} xu. Đăng nhập từ đường link lạ. Không bấm link trong tin nhắn lạ.',
    atm='{bank}: TK {no} -{amt} xu. Rút tiền bằng thẻ sao chép. Che tay khi nhập mã PIN.',
    tip='{bank}: TK {no} -{amt} xu. ND: gop von "du an noi bo". Cẩn thận lời mời lãi cao.',
)


def _fmt(n: int) -> str:
    return f'{n:,}'.replace(',', '.')


def apply_fx(s: dict, p: dict, amount: int) -> str:
    """Apply a bounded loss and record its actual amount in the live receipt."""
    from . import bank as bk
    from . import bank_content as K
    from . import journey as jr
    from . import rui
    from .engine import need
    j = s['journey']
    sub = p.get('sub')
    need(sub in SUBS, 'Loại sự cố không hợp lệ.')
    r = rui.get(s)
    gear = r.get('gear', []) if isinstance(r, dict) else []
    if sub == 'hack' and 'hai_lop' in gear:
        sub = 'scam'
    day = j['life_day']
    label = LABELS[sub]
    b = bk.get(s)
    cash = j['wallet'] if sub in WALLET_SUBS else b['balance'] if b else 0
    taken = bounded_loss(cash, amount, fine=sub == 'police')
    if sub == 'hack' and 'diet_virus' in gear:
        taken //= 2
    if taken and sub in WALLET_SUBS:
        jr._wallet(j, -taken, 'incident', label)
    elif taken and b is not None:
        b['balance'] -= taken
        bk._log(b, day, 'acc', label, -taken)
        bk._inbox(b, day, 'sms', SMS[sub].format(bank=K.BANK_NAME, no=b['no'][-4:].rjust(len(b['no']), '•')[-8:], amt=_fmt(taken)))
    p['_taken'] = taken
    return ''
