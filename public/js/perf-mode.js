/** ⚡ Máy yếu (owner 23/10: "hiện tại lag lắm"): one switch the scenes share. On when a scene measured this device
 * drawing too slowly (World.watchCost, PhaserWorld's frame watch) or the browser reports ≤ 2 GB of memory; remembered
 * for 7 days (localStorage mnl.perf) so the next start begins light; `?perf=low|full` forces it (testing).
 * Low: html[data-perf=low] (no backdrop blur, css/app.css), classic canvas at ≤ 1.25× pixels and slower ambient
 * redraws (world.js), the 2.5D map capped at 30 frames a second (phaser-world.ts). Fast devices never see it. */
const KEY='mnl.perf',TTL=7*864e5;
const g=globalThis;
let low=false,why='';
function apply(){try{if(g.document?.documentElement){if(low)g.document.documentElement.dataset.perf='low';else delete g.document.documentElement.dataset.perf;}}catch{/* no DOM */}}
try{
  const q=/[?&]perf=(low|full)\b/.exec(g.location?.search||'')?.[1];
  if(q){low=q==='low';why='url';}
  else{
    const saved=JSON.parse(g.localStorage?.getItem(KEY)||'null');
    if(saved?.low&&Date.now()-saved.at<TTL){low=true;why=saved.why||'saved';}
    else if(Number(g.navigator?.deviceMemory)>0&&g.navigator.deviceMemory<=2){low=true;why='memory';}
  }
}catch{/* storage blocked: decide per page */}
apply();
const subs=new Set();
/** Is the light mode on? */
export const lowEnd=()=>low;
/** A scene measured slow drawing here: turn light mode on (once) and tell the others. */
export function markLowEnd(reason='slow'){
  if(low)return;low=true;why=reason;apply();
  try{g.localStorage?.setItem(KEY,JSON.stringify({low:true,at:Date.now(),why:reason}));}catch{/* private mode */}
  for(const fn of subs){try{fn(true);}catch{/* a listener's own problem */}}
}
/** Called once when light mode turns on later in the session; returns an unsubscribe. */
export function onLowEnd(fn){subs.add(fn);return ()=>subs.delete(fn);}
export const lowReason=()=>why;
