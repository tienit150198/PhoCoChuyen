"""Market subscriptions share existing sockets; no player database work."""
import asyncio
from market_data import RANGES,snapshot
from game.market_wild import ASSETS
from game import realtime_market as rm
from game.market_wild import warm as rm_warm
from .protocol import Feature,LiveError,on

class MarketFeature(Feature):
    name='market'

    def __init__(self,app):
        super().__init__(app)
        self.viewers={}

    async def start(self):
        self.cfg.flags_extra['market']=True
        # 🎢 step the wild market (game/market_wild.py) up to now once, in a thread, without delaying the start
        self._warm=asyncio.get_running_loop().run_in_executor(None,rm_warm)

    @on('market_watch',rate=(20,10))
    async def watch(self,conn,f):
        if f.get('open') is False:
            self.viewers.pop(conn,None)
            return
        span=f.get('range','1D')
        if not isinstance(span,str) or span not in RANGES:raise LiveError('range','Khung thời gian không hợp lệ.')
        asset=f.get('asset') or ''   # 🎢 Sàn Phố: the asset whose chart is open (market_data.snapshot `sel`)
        if not isinstance(asset,str) or (asset and asset not in ASSETS):raise LiveError('asset','Mã tài sản không hợp lệ.')
        data=await asyncio.to_thread(snapshot,span,None,asset)
        self.viewers[conn]=(span,data['tick'],asset)
        return dict(t='market_quote',**data)

    async def on_close(self,conn):
        self.viewers.pop(conn,None)

    async def tick(self,now):
        tick=max(0,int((now-rm.EPOCH)//rm.TICK_SECONDS))
        groups={}
        for conn,(span,seen,asset) in list(self.viewers.items()):
            if conn.closing:self.viewers.pop(conn,None)
            elif seen!=tick:groups.setdefault((span,asset),[]).append(conn)
        for (span,asset),conns in groups.items():
            data=await asyncio.to_thread(snapshot,span,now,asset)
            # A close or changed range can arrive while computation is in flight.
            targets=[c for c in conns if not c.closing and self.viewers.get(c,(None,0,''))[0::2]==(span,asset) and self.viewers[c][1]<data['tick']]
            for c in targets:self.viewers[c]=(span,data['tick'],asset)
            if targets:self.hub.send_many(targets,dict(t='market_quote',**data))
