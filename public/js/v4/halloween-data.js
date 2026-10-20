/** 🎃 Lễ hội Ma Phố (game/halloween.py): the season's status shared by the menu (app.js), Tiện ích (isometric/town-utilities.js),
 * the start card and the sheet (v4/halloween.js) and the 2.5D town's decor (v4/halloween-town.js). Seeded from /api/bootstrap
 * `ui.hween`, then kept fresh by the ticker's poll (/api/news `hween`, v4/ticker.js). The server decides the dates (nothing
 * before 26/10/2026 00:00 Vietnam time, MNL_HALLOWEEN_OFF); untrusted input becomes {state, starts, ends, until, night, day,
 * title, icon, skew}. A change fires 'mnl:hween' (and 'mnl:badges', so the rail and dock redraw). Nothing here touches the save. */
let cur=null;
const STATES=['open','grace'];
function norm(v){
  if(!v||typeof v!=='object'||!STATES.includes(v.state))return null;
  const n=x=>Number.isFinite(Number(x))?Number(x):0;
  return {state:v.state,starts:n(v.starts),ends:n(v.ends),until:n(v.until),night:n(v.night),day:Math.max(0,Math.min(6,n(v.day)|0)),
    title:String(v.title||'').slice(0,60),icon:String(v.icon||'🎃').slice(0,8),skew:v.now?n(v.now)-Date.now()/1000:0};
}
const same=(a,b)=>JSON.stringify(a&&{...a,skew:0})===JSON.stringify(b&&{...b,skew:0});
/** The bootstrap's copy, without events (app.js reads it while it draws the menu). */
export function seedHween(v){if(cur===null)cur=norm(v);}
export function setHween(v){
  const n=norm(v);if(same(n,cur)){if(n&&cur)cur.skew=n.skew;return;}
  cur=n;
  if(typeof document!=='undefined'){document.dispatchEvent(new Event('mnl:hween'));document.dispatchEvent(new Event('mnl:badges'));}
}
export const serverNow=()=>Date.now()/1000+(cur?.skew||0);
/** The status now: a season that moved on since the last poll is seen as such at once (open → grace → gone). */
export function hwNow(){
  if(!cur)return null;
  const t=serverNow();
  if(t>=cur.until)return null;
  if(cur.state==='open'&&t>=cur.ends)return {...cur,state:'grace',day:0};
  return cur;
}
export const hwOpen=()=>hwNow()?.state==='open';
export const hwShown=()=>Boolean(hwNow());
/** 🎭 Đêm hội hóa trang (31/10 from 19:00 until midnight). */
export const hwNight=()=>{const h=hwNow(),t=serverNow();return Boolean(h&&h.state==='open'&&t>=h.night&&t<h.ends);};
/** The Vietnam day of the server's clock ('2026-10-26'): the start card shows once a day on a device. */
export function vnDay(t=serverNow()){return new Date(t*1000+7*3600e3).toISOString().slice(0,10);}
/** For tests: forget the seeded status. */
export function _reset(){cur=null;}
