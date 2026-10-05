"""Public quote data only: no player reads, settlement, balances or writes.

The existing market remains the sole pricing authority. Real-time chart ranges
sample its historical ticks, bounded to 181 points including both endpoints.
Never sample before launch or after the current tick. A shared per-process
cache and lock coalesce simultaneous viewers; live callers use a worker thread.
"""
import copy
import functools
import math
import threading
from game import realtime_market as rm

RANGES={'1H':3600,'1D':86400,'3D':259200,'1W':604800,'1M':2592000}
_lock=threading.Lock()

@functools.lru_cache(maxsize=15)
def _snapshot(span,tick):
    at=rm.EPOCH+tick*rm.TICK_SECONDS
    start=max(0,tick-RANGES[span]//rm.TICK_SECONDS)
    step=max(1,math.ceil((tick-start)/180))
    ticks=list(range(start,tick+1,step))
    if ticks[-1]!=tick:ticks.append(tick)
    out={'range':span,'tick':tick,'as_of':at,'next_at':at+rm.TICK_SECONDS,
         'market_day':tick*rm.TICK_SECONDS//rm.DAY_SECONDS+1,
         'epoch':rm.EPOCH,'tick_seconds':rm.TICK_SECONDS,'day_seconds':rm.DAY_SECONDS}
    for asset in ('coin','gold'):
        q=rm.quote(asset,at)
        anchor=rm.base_price(asset)
        points=[[rm.EPOCH+t*rm.TICK_SECONDS,rm._price(asset,rm._salt(),anchor,t)] for t in ticks]
        out[asset]={'price':q['price'],'previous':q['previous'],'news':q['news'],'points':points}
    return out

def snapshot(span='1D',at=None):
    if not isinstance(span,str) or span not in RANGES:raise ValueError('Khung thời gian không hợp lệ.')
    tick=max(0,math.floor(((rm.now() if at is None else at)-rm.EPOCH)/rm.TICK_SECONDS))
    with _lock:return copy.deepcopy(_snapshot(span,tick))
