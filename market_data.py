"""Public quote data only: no player reads, settlement, balances or writes.

The existing market remains the sole pricing authority. Real-time chart ranges
sample its historical ticks, bounded to 181 points including both endpoints.
Never sample before launch or after the current tick. A shared per-process
cache and lock coalesce simultaneous viewers; live callers use a worker thread.

🎢 Sàn Phố (game/market_wild.py, 24/10): every quote also carries `board` (all
assets: price, 1 h / 24 h change, 24 hourly points, headline, listing state, and
the market's ticker) and, when `asset` names a new asset, `sel` with its chart
points for the range. Mây Coin and gold keep their own `coin` / `gold` entries.
"""
import copy
import functools
import math
import threading
from game import realtime_market as rm
from game import market_wild as mw

RANGES={'1H':3600,'1D':86400,'3D':259200,'1W':604800,'1M':2592000}
_lock=threading.Lock()

def _ticks(span,tick,first=0):
    start=max(first,tick-RANGES[span]//rm.TICK_SECONDS)
    step=max(1,math.ceil((tick-start)/180))
    ticks=list(range(start,tick+1,step))
    if ticks[-1]!=tick:ticks.append(tick)
    return ticks

@functools.lru_cache(maxsize=48)
def _snapshot(span,tick,asset=''):
    at=rm.EPOCH+tick*rm.TICK_SECONDS
    ticks=_ticks(span,tick)
    out={'range':span,'tick':tick,'as_of':at,'next_at':at+rm.TICK_SECONDS,
         'market_day':tick*rm.TICK_SECONDS//rm.DAY_SECONDS+1,
         'epoch':rm.EPOCH,'tick_seconds':rm.TICK_SECONDS,'day_seconds':rm.DAY_SECONDS}
    for name in ('coin','gold'):
        q=rm.quote(name,at)
        points=[[rm.EPOCH+t*rm.TICK_SECONDS,mw.adjusted(name,t,tick) if t>=mw.WILD_TICK else
                 round(rm.price_at(name,t)*10.**mw.exp_at(name,tick))] for t in ticks]   # split-adjusted (Mây Coin)
        out[name]={'price':q['price'],'previous':q['previous'],'news':q['news'],'points':points,'e':q.get('e',0)}
    out['board']=mw.board(at)
    if asset and asset not in ('coin','gold') and tick>=mw.WILD_TICK:
        out['sel']={'id':asset,'points':[[rm.EPOCH+t*rm.TICK_SECONDS,mw.adjusted(asset,t,tick)] for t in _ticks(span,tick,mw.WILD_TICK)],
                    'epoch':rm.EPOCH+mw.WILD_TICK*rm.TICK_SECONDS}
    return out

def snapshot(span='1D',at=None,asset=None):
    if not isinstance(span,str) or span not in RANGES:raise ValueError('Khung thời gian không hợp lệ.')
    if asset in (None,''):asset=''
    elif not isinstance(asset,str) or asset not in mw.ASSETS:raise ValueError('Mã tài sản không hợp lệ.')
    tick=max(0,math.floor(((rm.now() if at is None else at)-rm.EPOCH)/rm.TICK_SECONDS))
    with _lock:return copy.deepcopy(_snapshot(span,tick,asset))
