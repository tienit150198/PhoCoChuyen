/** 🎣 Hồ câu đông vui, the plain numbers (no DOM: tests/fishing-lake.mjs): where each fisher stands along the lake's
 * boardwalk, how close a crowd packs, what the camera shows, who is drawn whole and who as a light silhouette, where a
 * cast lands on the shared water in perspective, and the feed's lines. The live room (live/fish_lake.py) gives every
 * fisher a slot `s`; slot 0 is the middle, then right and left in turn (posOf, the service's pos()). One lake per spot
 * with no cap (owner 24/10 "hồ k tối đa lượng người mỗi bến"): the boardwalk is as long as the crowd, the view pans. */
import {fmtKg,fishSpan,PERSON} from './fish-art.js';

export const FULL_DRAW=24;     // fishers drawn whole (the nearest to the view's middle); the rest as silhouettes
export const VIEW_STEP=6;      // pos units the view moves before asking the service for the whole entries there
export const SP_MIN=46,SP_MAX=84;
const clamp=(v,a,b)=>v<a?a:v>b?b:v;

/** Slot → place along the boardwalk: 0, 1, -1, 2, -2, … */
export const posOf=s=>{s=Math.max(0,Math.floor(Number(s)||0));return s===0?0:s%2?(s+1)/2:-(s/2);};
/** Px between two places: wide for a few people, packed (never under SP_MIN) for a crowd. */
export const spacing=(n,w)=>clamp(w/Math.max(4,(Number(n)||1)+1),SP_MIN,SP_MAX);
/** The characters' scale for that spacing (paintPlayer units: about 125 tall). */
export const figScale=sp=>clamp(sp/150,.31,.5);
/** A place's x on screen with the view's middle at `cam`. */
export const screenX=(pos,cam,sp,w)=>w/2+(pos-cam)*sp;
/** The places the boardwalk holds now: [lo, hi] (pos units) over everyone there. */
export function extent(list){let lo=0,hi=0;for(const p of list){const x=posOf(p.s);if(x<lo)lo=x;if(x>hi)hi=x;}return [lo,hi];}
/** The view's middle kept over the boardwalk. */
export const clampCam=(cam,[lo,hi])=>clamp(Number(cam)||0,lo,hi);
/** In sight (with `pad` places to spare). */
export const inView=(pos,cam,sp,w,pad=1)=>Math.abs(pos-cam)<=w/2/sp+pad;
/** The pids drawn whole: the `max` in sight nearest to the view's middle (whose look we have). */
export function detailed(list,cam,sp,w,max=FULL_DRAW){
  const seen=list.filter(p=>p.lk&&inView(posOf(p.s),cam,sp,w)).sort((a,b)=>Math.abs(posOf(a.s)-cam)-Math.abs(posOf(b.s)-cam)||a.s-b.s);
  return new Set(seen.slice(0,max).map(p=>p.pid));
}
/** How many fishers stand past each edge, and the nearest place there: the ◀ ▶ buttons. */
export function offscreen(list,cam,sp,w){
  const half=w/2/sp,out={left:0,right:0,lp:null,rp:null};
  for(const p of list){const x=posOf(p.s);
    if(x<cam-half){out.left++;if(out.lp==null||x>out.lp)out.lp=x;}
    else if(x>cam+half){out.right++;if(out.rp==null||x<out.rp)out.rp=x;}}
  return out;
}
/** Where a bobber `d` metres out sits on the shared water: the lake narrows to the horizon, so a cast from a place off
 * the middle leans toward it. g: fishing.js geo() (yOf, half, shore, w); xs the fisher's x on screen; lat sideways, a
 * share of the lake's half width there (fishing.js casts within ±.275). */
export function waterPoint(g,xs,d,lat=0){
  const y=g.yOf(d),k=g.half(y)/g.half(g.shore),cx=g.w/2;
  return [cx+(xs-cx)*k+lat*g.half(y),y];
}
/** The arc of a cast in flight: u 0 → 1 from the rod's tip to where it lands, `lift` px at the top. */
export function arcPoint(tip,land,u,lift){u=clamp(u,0,1);return [tip[0]+(land[0]-tip[0])*u,tip[1]+(land[1]-tip[1])*u-Math.sin(Math.PI*u)*lift];}
/** The fisher under a tap (x, y on the canvas), or null: places within half a spacing, from the feet to the hat. */
export function hitPeer(list,x,y,{cam,sp,w,py,scale}){
  let best=null,bd=1e9;
  for(const p of list){const sx=screenX(posOf(p.s),cam,sp,w),dx=Math.abs(x-sx);
    if(dx>sp/2||y>py+12||y<py-140*scale)continue;if(dx<bd){bd=dx;best=p;}}
  return best;
}
/** How loud a catch is: 'legend' (🟡 Huyền thoại, 🔴 Cổ đại: the lake-wide banner), 'rare' (🟣 Hiếm and up: a glow and
 * sparkles), 'plain'. */
export const tierOf=r=>r>=5?'legend':r>=3?'rare':'plain';
/** The feed's line: "🎣 Lan vừa câu được 🟣 Cá Ngừ Vây Xanh 34 kg!" (sp: the species, R: its rarity). */
export function feedLine(e,sp,R){
  const who=String(e?.name||'Một người').slice(0,24);
  return `🎣 ${who} vừa câu được ${R?.emoji||''} ${sp?.name||'một con cá'} ${fmtKg(Number(e?.g)||0)}!`.replace(/\s+/g,' ');
}
/** A fisher from the wire (a whole entry or a compact {pid, name, s}), merged over what we had. */
export function merge(old,x){
  const p=old||{pid:x.pid,a:null,said:null,got:null,spr:null,sprKey:''};
  p.name=String(x.name||p.name||'');p.s=Math.max(0,Math.floor(Number(x.s)||0));
  if(x.lk&&typeof x.lk==='object'){
    for(const k of ['lk','g','fc','fh','wg','st','tt','bg','rod'])p[k]=x[k]??null;
    if(x.a&&typeof x.a==='object')p.a={...x.a,t0:-1e9};   // already out: no flight, the bobber on the water
  }
  return p;
}
/** 🐋 A landed fish next to its fisher drawn at `scale` (css px per look unit; owner 25/10 "cá to thì nhìn to thật"):
 * {len: px long, as its weight says (fish-art.js fishSpan × the character's height), big: too big to hold up over the
 * head (it lands lying on the boardwalk beside them instead), dx, dy: its middle from their feet when it rests}. */
export function catchPose(g,scale){
  const span=fishSpan((Number(g)||0)/1000),len=Math.max(14,span*PERSON*scale),big=span>=1.05;
  return big?{len,big,dx:len*.5+18*scale,dy:-Math.max(6,len*.13)}:{len,big,dx:0,dy:-128*scale-14-len*.15};
}
/* ↔️ Owner 25/10 "cho người ta là scroll ngang nếu nhiều người nhé": the boardwalk scrolls. A drag on the lake pans the
 * view (with momentum when let go), the wheel / a trackpad too, and a thin bar under the boardwalk shows where the view
 * is along the whole crowd (its thumb drags). The numbers, in pos units (one place per fisher). */
/** The view after a finger moved `dx` px since it went down at `cam0` (a drag right looks left), kept over the boardwalk. */
export const panBy=(cam0,dx,sp,ext)=>clampCam((Number(cam0)||0)-(Number(dx)||0)/Math.max(1,sp),ext);
/** A fling's speed (pos units / s) dying out after `dt` seconds; 0 once slow. */
export function glide(v,dt){const n=(Number(v)||0)*Math.exp(-3.2*Math.max(0,dt));return Math.abs(n)<.25?0:n;}
/** The wheel's step in px (lines and pages turned into px; a vertical wheel pans sideways too). */
export function wheelPx(e){
  const k=e?.deltaMode===1?16:e?.deltaMode===2?400:1,dx=Number(e?.deltaX)||0,dy=Number(e?.deltaY)||0;
  return (Math.abs(dx)>Math.abs(dy)?dx:dy)*k;
}
/** The bar: the whole boardwalk with half a view of room at each end. {total (pos units), left, width: the thumb's
 * share of the bar, me: my place's share, can: the crowd is wider than the view}. */
export function scrollOf(cam,[lo,hi],sp,w,me=0){
  const half=w/2/Math.max(1,sp),total=(hi-lo)+2*half,c=clampCam(cam,[lo,hi]);
  return {total,left:(c-lo)/total,width:2*half/total,me:(me-lo+half)/total,can:hi-lo+1>2*half};
}
/** The view's middle for the thumb's left edge at `left` (a share of the bar). */
export function camAt(left,[lo,hi],sp,w){const half=w/2/Math.max(1,sp),total=(hi-lo)+2*half;return clampCam(lo+(Number(left)||0)*total,[lo,hi]);}
/** My place is out of sight (📍 Về chỗ tôi). */
export const farFromMe=(cam,me,sp,w)=>Math.abs((Number(cam)||0)-(Number(me)||0))>w/2/Math.max(1,sp)-.5;
