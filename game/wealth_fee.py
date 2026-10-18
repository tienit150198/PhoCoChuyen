"""🏛️ Phí giữ tài sản lớn (owner 18/10: "làm sao cho người giàu tốn tiền nhiều hơn… tăng càng nhiều thì phí nhiều đi").

Once per Vietnam calendar day (real time, not life days), a player whose assets (assets(): wealth_pricing.total —
wallet, bank, savings, coin, gold, homes, vehicles, counters' funds and tills — plus EVERY started workplace's fund,
the jobs one is employed at included: 19/10, a top player had moved 80M there) are above FREE pays
LOW_BP ‱ of the part between FREE and HIGH and HIGH_BP ‱ of the part above HIGH. Days away count too, at most
MAX_DAYS at a time. The fee is taken from the wallet, then the bank account, then the savings không kỳ hạn, then the
counters' tills (fullest first), then the workplaces' funds (fullest first, as 👛 Rút về ví allows: the 80 xu reserve
and the unpaid bills stay); it never makes a debt: what none of them holds is not charged. Each payment is
written in the book it came from ("🏛️ Phí giữ tài sản lớn").

journey[KEY] = {d: Vietnam day ordinal of the last charge, paid: total paid, last: the last charge}; optional, so an
older server keeps it as is (the journey keeps unknown keys). MNL_WEALTH_FEE_OFF=1 turns it off (engine hook).
"""
from __future__ import annotations

import datetime
import os
import time

KEY = 'wfee'
FREE = 30_000_000
HIGH = 100_000_000
LOW_BP, HIGH_BP = 50, 100      # 0.5 % a day of the part above FREE, 1 % a day of the part above HIGH
MAX_DAYS = 3
LABEL = '🏛️ Phí giữ tài sản lớn'
BACK = '🏛️ Hoàn phí giữ tài sản lớn (áp dụng từ 20/10)'
VN = datetime.timezone(datetime.timedelta(hours=7))
# Owner 19/10 "mai rồi trừ nhé, với thông báo cho người ta biết luôn": announced in Có gì mới 2.4.53, charged from
# 20/10 (Vietnam). What 2.4.52 took on 18–19/10 goes back to the wallet on the next command (settle()).
START = datetime.date(2026, 10, 20).toordinal()
START_TS = datetime.datetime(2026, 10, 20, tzinfo=VN).timestamp()


def off() -> bool:
    """MNL_WEALTH_FEE_OFF=1: nobody is charged (the admin's kill switch; the tests' default, tests/__init__.py)."""
    return os.environ.get('MNL_WEALTH_FEE_OFF', '') == '1'


def today(now: float | None = None) -> int:
    return datetime.datetime.fromtimestamp(time.time() if now is None else now, VN).date().toordinal()


def daily(wealth: int) -> int:
    """The fee of one day for `wealth` xu of assets."""
    w = max(0, int(wealth))
    return (max(0, min(w, HIGH) - FREE) * LOW_BP + max(0, w - HIGH) * HIGH_BP) // 10000


def assets(s: dict) -> int:
    from . import wealth_pricing
    from . import journey as jr
    extra = sum(max(0, c.get('money', 0)) for cid, c in (s.get('careers') or {}).items()
                if isinstance(c, dict) and c.get('started') and jr._employed(cid))   # wealth_pricing.total leaves these out
    return wealth_pricing.total(s) + extra


def settle(s: dict, now: float | None = None) -> bool:
    """Charge the days since the last charge (at most MAX_DAYS). Returns whether the save changed."""
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict) or j.get('story') is False:
        return False
    day = today(now)
    rec = j.get(KEY)
    if isinstance(rec, dict) and rec.get('d', 0) < START and rec.get('paid', 0) > 0:
        from . import journey as jr
        jr._wallet(j, int(rec['paid']), 'life', BACK)   # charged before the announced start: all of it back
        rec = j[KEY] = dict(d=START - 1, paid=0, last=0)
        if day < START:
            return True
    if day < START:
        return False
    if not isinstance(rec, dict):
        rec = dict(d=day - 1, paid=0, last=0)
    days = min(MAX_DAYS, day - int(rec.get('d', day)))
    if days <= 0:
        return False
    want = daily(assets(s)) * days
    if want <= 0 and KEY not in j:
        return False   # nobody under FREE carries the key
    got = _take(s, j, want) if want > 0 else 0
    j[KEY] = dict(d=day, paid=int(rec.get('paid', 0)) + got, last=got)
    return True


def _take(s: dict, j: dict, want: int) -> int:
    from . import journey as jr
    from . import bank as bk
    from . import quay as qy
    got = 0
    life = j['life_day']
    x = min(want, max(0, j.get('wallet', 0)))
    if x > 0:
        jr._wallet(j, -x, 'life', LABEL)
        got += x
    b = j.get('bank')
    if isinstance(b, dict):
        for field, acc in (('balance', 'acc'), ('demand', 'sav')):
            x = min(want - got, max(0, b.get(field, 0)))
            if x > 0:
                b[field] -= x
                bk._log(b, life, acc, LABEL, -x)
                got += x
    for st in sorted((qy.get(s) or {}).get('stalls', []), key=lambda st: -st.get('till', 0)):
        x = min(want - got, max(0, st.get('till', 0)))
        if x > 0:
            st['till'] -= x
            qy._log(st, life, LABEL, -x)
            got += x
    funds = [(c.get('money', 0), cid) for cid, c in (s.get('careers') or {}).items() if isinstance(c, dict) and c.get('started')]
    for _, cid in sorted(funds, reverse=True):
        c = s['careers'][cid]
        x = min(want - got, max(0, c['money'] - jr._unpaid(c) - jr.RESERVE))
        if x > 0:
            jr._transfer(s, c, -x, LABEL, 'owner_draw')
            got += x
    return got


def validate(j: dict) -> None:
    if KEY not in j:
        return
    from .engine import need, integer
    r = j[KEY]
    need(isinstance(r, dict) and set(r) == {'d', 'paid', 'last'}, 'Dữ liệu phí tài sản không hợp lệ.', 'invalid_save')
    integer(r['d'], 0, 10**7)
    integer(r['paid'], 0, 10**16)
    integer(r['last'], 0, 10**16)
