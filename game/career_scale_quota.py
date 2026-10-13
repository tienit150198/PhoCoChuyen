"""Account-wide real-day management allowance. Reading never grants or spends it."""
from __future__ import annotations

import copy
import math
import re
import time

KEY = 'scale_quota'
PER_DAY = 4
CAP = 12
_REF = re.compile(r'[a-z_]+-[1-9][0-9]{0,11}')


def _need(ok, message='Dữ liệu suất quản lý không hợp lệ.'):
    from .engine import need
    need(ok, message)


def day(now=None):
    at = time.time() if now is None else now
    _need(type(at) in (int, float) and math.isfinite(at) and 0 <= at < 10**11)
    return int((at + 7 * 3600) // 86400)


def _read(s, now=None):
    today = day(now)
    r = copy.deepcopy(s['journey'].get(KEY))
    if r is None:
        return dict(v=1, day=today, tokens=1, reserved=None)
    elapsed = max(0, today - r['day'])
    r['tokens'] = min(CAP - int(r['reserved'] is not None), r['tokens'] + elapsed * PER_DAY)
    r['day'] = max(today, r['day'])
    return r


def public(s, now=None):
    r = _read(s, now)
    return dict(available=r['tokens'], reserved=r['reserved'], daily=PER_DAY, cap=CAP,
                next_at=(r['day'] + 1) * 86400 - 7 * 3600)


def reserve(s, ref, now=None):
    _need(type(ref) is str and _REF.fullmatch(ref) is not None)
    r = _read(s, now)
    _need(r['reserved'] is None, 'Đang giữ một hợp đồng. Tiếp tục hoặc hủy trước khi nhận hợp đồng khác.')
    _need(r['tokens'] > 0, 'Hết suất quản lý. Mỗi ngày thực nhận thêm 4 suất, tích tối đa 12 suất.')
    r['tokens'] -= 1
    r['reserved'] = ref
    s['journey'][KEY] = r


def _release(s, ref, refund, now=None):
    r = _read(s, now)
    _need(type(ref) is str and r['reserved'] == ref, 'Hợp đồng giữ suất đã thay đổi. Mở lại bảng quản lý nhé.')
    r['reserved'] = None
    r['tokens'] += int(refund)
    s['journey'][KEY] = r


def start(s, ref, now=None):
    _release(s, ref, False, now)


def cancel(s, ref, now=None):
    _release(s, ref, True, now)


def carry_reset(old, fresh, career=None):
    """Keep spent allowance through explicit resets; release only discarded offers."""
    r = copy.deepcopy(old.get('journey', {}).get(KEY))
    if r is None:
        return
    if r['reserved'] and (career is None or r['reserved'].startswith((career + '-',career + '_special-'))):
        r['tokens'] += 1
        r['reserved'] = None
    fresh['journey'][KEY] = r


def validate(s):
    r = s.get('journey', {}).get(KEY)
    if r is None:
        _need(KEY not in s.get('journey', {}))
        return
    _need(type(r) is dict and set(r) == {'v', 'day', 'tokens', 'reserved'})
    _need(type(r['v']) is int and r['v'] == 1)
    _need(type(r['day']) is int and 0 <= r['day'] < 1200000)
    _need(type(r['tokens']) is int and 0 <= r['tokens'] <= CAP)
    ref = r['reserved']
    _need(ref is None or type(ref) is str and _REF.fullmatch(ref) is not None)
    _need(r['tokens'] + int(ref is not None) <= CAP)
