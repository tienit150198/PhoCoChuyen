/** 🎪 Hội chợ việc làm (game/town_fair.py): the fair's status shared by the menu (app.js), the 2.5D signpost (iso-guide.js,
 * isometric/town-utilities.js) and the sheet (v4/town-fair.js). Seeded from /api/bootstrap `ui.tfair`, then kept fresh by
 * the ticker's poll (/api/news `tfair`, v4/ticker.js). Untrusted input becomes {state, id, kind, starts, ends, skew}; a
 * change fires 'mnl:tfair' (and 'mnl:badges', so the rail and dock redraw). Nothing here touches the save. */
let cur=null;
const STATES=['open','soon','closed','off'];
function norm(v){
  if(!v||typeof v!=='object'||!STATES.includes(v.state))return null;
  const n=x=>Number.isFinite(Number(x))?Number(x):0;
  return {state:v.state,id:String(v.id||'').slice(0,40),kind:v.kind==='special'?'special':'week',starts:n(v.starts),ends:n(v.ends),skew:v.now?n(v.now)-Date.now()/1000:0};
}
const same=(a,b)=>JSON.stringify(a&&{...a,skew:0})===JSON.stringify(b&&{...b,skew:0});
/** The bootstrap's copy, without events (app.js reads it while it draws the menu). */
export function seedFair(v){if(cur===null)cur=norm(v);}
export function setFair(v){
  const n=norm(v);if(same(n,cur)){if(n)cur.skew=n.skew;return;}
  cur=n;
  if(typeof document!=='undefined'){document.dispatchEvent(new Event('mnl:tfair'));document.dispatchEvent(new Event('mnl:badges'));}
}
export const serverNow=()=>Date.now()/1000+(cur?.skew||0);
/** The status now: a fair that ended (or began) since the last poll is seen as such at once. */
export function fairNow(){
  if(!cur)return null;
  const t=serverNow();
  if(cur.state==='open'&&t>=cur.ends)return {...cur,state:'closed'};
  if(cur.state==='soon'&&t>=cur.starts&&t<cur.ends)return {...cur,state:'open'};
  return cur;
}
export const fairOpen=()=>fairNow()?.state==='open';
export const fairShown=()=>['open','soon'].includes(fairNow()?.state);
/** "1:02:09" / "4 phút" until a moment (epoch seconds, the server's clock). */
export function leftText(at){
  const s=Math.max(0,Math.round(at-serverNow())),h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;
  return h?`${h}:${String(m).padStart(2,'0')}:${String(x).padStart(2,'0')}`:`${m}:${String(x).padStart(2,'0')}`;
}
