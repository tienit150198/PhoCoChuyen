/** Quote-only updates. Never refresh/modify the player's authoritative save. */
export const RANGES=['1H','1D','3D','1W','1M'];
export const rangeOf=env=>RANGES.includes(env.ui.ivRange)?env.ui.ivRange:'1D';
const controllers=new WeakMap(),pending=new WeakMap();
const selected=env=>env.ui.ivQuotes?.[rangeOf(env)];
export function acceptQuote(env,data){
 if(!RANGES.includes(data?.range)||!Number.isFinite(data.tick)||!data.coin?.points?.length||!data.gold?.points?.length)return false;
 const quotes=env.ui.ivQuotes??={};
 if(quotes[data.range]?.tick>data.tick)return false;
 quotes[data.range]=data;
 if(data.range===rangeOf(env)){env.ui.ivRefreshError='';if(!env.ui.ivBusy)env.renderSheet();}
 return true;
}
export async function refreshQuotes(env){
 if(env.ui.ivBusy)return;
 const span=rangeOf(env),key=pending.get(env.api);
 if(key?.span===span)return key.work;
 env.ui.ivRefreshing=true;env.ui.ivRefreshError='';env.renderSheet();
 const work=Promise.resolve().then(async()=>{
  try{acceptQuote(env,await env.api.json('/api/market?range='+span));}
  catch{if(rangeOf(env)===span)env.ui.ivRefreshError='Chưa cập nhật được giá. Bấm Cập nhật giá để thử lại.';}
  finally{if(pending.get(env.api)?.work===work){pending.delete(env.api);env.ui.ivRefreshing=false;env.renderSheet();}}
 });
 pending.set(env.api,{span,work});return work;
}
export function marketBoot(env){
 if(controllers.has(env.api))return;
 const doc=document,sheet=doc.getElementById('sheet');
 let socket=null,watching='',visibleBefore=false,timeout=0;
 const visible=()=>!doc.hidden&&sheet?.open&&env.ui.view==='home'&&env.ui.jrView==='invest';
 const stop=()=>{clearTimeout(timeout);if(watching)socket?.send({t:'market_watch',open:false});watching='';};
 function watch(force=false){
  const isVisible=visible(),entered=isVisible&&!visibleBefore;visibleBefore=isVisible;
  if(!isVisible){stop();return;}
  const span=rangeOf(env);
  if(socket?.state==='open'&&socket.flags.market){
   if(!force&&watching===span)return;
   watching=span;
   if(socket.send({t:'market_watch',range:span,open:true})){
    clearTimeout(timeout);
    // A single missed-reply fallback, never a polling loop.
    timeout=setTimeout(()=>{if(visible()&&rangeOf(env)===span)refreshQuotes(env);},8000);
   }
  }else if(entered||force){
   const q=selected(env),now=Date.now()/1000+(Number(env.api.clockOffset)||0);
   if(!q||q.next_at<=now)refreshQuotes(env);
  }
 }
 controllers.set(env.api,{watch});
 doc.addEventListener('sheetrender',()=>watch());
 doc.addEventListener('visibilitychange',()=>watch());
 sheet?.addEventListener('close',()=>{visibleBefore=false;stop();});
 doc.addEventListener('change',e=>{if(e.target.matches?.('[data-iv-point]')){env.ui.ivPoint=Number(e.target.value);env.renderSheet();}});
 const attach=s=>{
  socket=s;
  s.on('market_quote',data=>{if(data.range===rangeOf(env))clearTimeout(timeout);acceptQuote(env,data);});
  s.on('welcome',()=>{watching='';watch(true);});
  s.on('down',()=>{watching='';clearTimeout(timeout);});
  watch();
 };
 if(env.marketLive)attach(env.marketLive);
 else import('./live.js').then(m=>attach(m.live)).catch(()=>watch());
}
export function changeRange(env,range){
 env.ui.ivRange=RANGES.includes(range)?range:'1D';env.ui.ivPoint=null;
 controllers.get(env.api)?.watch(true);env.renderSheet();
}
/** Return display copies; do not corrupt API delta references or wallet balances. */
export function marketView(env){
 const I=env.api.state?.invest,G=env.api.state?.vang;
 const all=Object.values(env.ui.ivQuotes||{}),q=all.sort((a,b)=>b.tick-a.tick)[0];
 if(!I||!q)return {I,G};
 let copy=I,gold=G;
 if(q.tick>=(I.coin.market_clock?.tick??-1)){
  const c=I.coin,price=q.coin.price,value=Math.floor(c.units*price/(I.rules.coin*I.rules.cent));
  copy={...I,coin:{...c,price,value,unrealised:c.units?value-c.basis:0,change:(price-q.coin.previous)*100/q.coin.previous,market_news:q.coin.news,market_clock:q}};
 }
 if(G&&q.tick>=(G.market_clock?.tick??-1)){
  const p=q.gold.price,buy=Math.ceil(p*10250/10000),sell=Math.floor(p*9750/10000);
  gold={...G,p,buy,sell,y:q.gold.previous,value:Math.floor(G.phan*sell/10),market_news:q.gold.news,market_clock:q};
 }
 return {I:copy,G:gold};
}
