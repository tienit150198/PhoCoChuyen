/** Drawing kit for the interiors of a workplace (scenes/areas.js): the frame every inside room sits in, a
 * geometry helper that places things by fractions so one description serves landscape (1200×790) and
 * portrait (700×890), doors with their sign, windows that follow the time of day and the career's weather,
 * announcement bubbles, little passers-by and slow background moments. Everything is canvas; nothing here
 * moves when reduced motion is on.
 *
 * geo(port): {f (frame), base (wall/floor line), bot, k (portrait scale), X(u) across the frame, Y(v) down the
 * floor (0 = wall foot, 1 = front edge), H(h) down the wall (0 = top, 1 = wall foot)}. An interior plan is
 * written once as spec(g) and built for both orientations with both(spec). */
import {R,E,L,T,P,fit,heart} from './kit.js';
import {t as tr} from '../v4/i18n.js';

const FR={land:{x:66,y:116,w:1068,h:622,r:32,base:452},port:{x:24,y:118,w:652,h:736,r:28,base:505}};
export function geo(port){
  const f=port?FR.port:FR.land,bot=f.y+f.h;
  return {port,f,base:f.base,bot,k:port?.82:1,X:u=>f.x+u*f.w,Y:v=>f.base+v*(bot-f.base),H:h=>f.y+h*(f.base-f.y)};
}
/** An interior plan for both orientations from spec(g); fills the keys the world reads with harmless defaults. */
export function both(spec){
  const make=port=>{const g=geo(port),pl=spec(g);
    return {kx:port?51:82,ky:port?57:45,sway:port?24:38,lane:pl.home[1],line:pl.home[1]+50,blocks:[],customers:[],event:pl.home,officer:pl.home,
      staff:{x:pl.home[0],step:100,y:pl.home[1]},counterSpan:[0,0],decor:{},sill:{},bench:[0,0,0,0],garden:[],cat:null,...pl,
      floor:pl.floor||[g.X(.03),g.Y(.1),g.X(.97),g.Y(.93)]};};
  return {land:make(false),port:make(true)};
}
/** Box [x0,y0,x1,y1] from floor fractions. */
export const box=(g,u0,v0,u1,v1)=>[g.X(u0),g.Y(v0),g.X(u1),g.Y(v1)];
/** A spot: hit point, range (scaled for portrait), approach points from floor fractions. */
export const spotAt=(g,hit,range,...go)=>[hit,Math.round(range*(g.port?.9:1)),go.map(([u,v])=>[g.X(u),g.Y(v)])];

/* ------------------------------------------------------------ the room shell */
/** Frame shadow and border, then (clipped to the frame) the wall and the floor; draw(c,g) paints the inside. */
export function shell(w,{wall,wallLow=null,floor,floor2=null,tile=0,rim='#b9a48f',trim=null},draw){
  const c=w.ctx,g=geo(w.isPortrait()),f=g.f;
  E(c,f.x+f.w/2,g.bot+12,f.w*.48,22,'#8b735322');R(c,f.x-8,f.y-6,f.w+16,f.h+14,rim,f.r+6);
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  R(c,f.x,f.y,f.w,g.base-f.y,wall,0);
  if(wallLow)R(c,f.x,g.base-(g.base-f.y)*.22,f.w,(g.base-f.y)*.22,wallLow,0);
  R(c,f.x,g.base,f.w,g.bot-g.base,floor,0);
  if(tile&&floor2){const s=tile*(g.port?.8:1);for(let y=g.base,j=0;y<g.bot;y+=s*.62,j++)for(let x=f.x-(j%2)*s/2,i=0;x<f.x+f.w;x+=s,i++)if((i+j)%2===0)R(c,x,y,s,s*.62,floor2,0);}
  if(trim)R(c,f.x,g.base-6,f.w,8,trim,0);
  E(c,f.x+f.w/2,g.base+4,f.w*.5,10,'#00000010');
  draw(c,g);
  c.restore();
  return g;
}
/** A doorway on the back wall at u (centre), its sign above: icon + where it goes. */
export function doorway(c,g,u,{label,icon='',color='#7d6a5a',frame='#d9cbb8',glass=null,open=false}={}){
  const k=g.k,wd=86*k,ht=(g.base-g.H(.36)),x=g.X(u)-wd/2,top=g.base-ht;
  R(c,x-8*k,top-8*k,wd+16*k,ht+8*k,frame,10*k);R(c,x,top,wd,ht,open?'#3c3732':color,8*k);
  if(glass)R(c,x+10*k,top+12*k,wd-20*k,ht*.42,glass,6*k,'#ffffff66',1.5);
  if(!open){E(c,x+wd-14*k,top+ht*.55,4*k,4*k,'#f2d48c');}
  else{R(c,x+6*k,top+6*k,wd-12*k,ht-6*k,'#ffeccb33',6*k);}
  if(label){const s=`${icon} ${label}`.trim(),sw=Math.max(wd+30*k,120*k);R(c,g.X(u)-sw/2,top-38*k,sw,26*k,'#2f3d4a',8*k);T(c,s,g.X(u),top-25*k,fit(c,s,sw-12,(g.port?15:12)),'#fdf6e8',800);}
}

/* ------------------------------------------------------------ outside light and weather */
/** The career's weather today, when its public data says: 'rain' | 'storm' | 'fog' | 'wind' | 'heat' | 'clear'. */
export function weatherOf(w){
  const d=w.c?.data||{},id=String(d.weather||d.mod?.id||d.road?.mod?.id||'').toLowerCase();
  if(/storm|giong/.test(id))return 'storm';if(/rain|mua|wet|flood/.test(id))return 'rain';
  if(/fog|early|mist|suong/.test(id))return 'fog';if(/wind|rough|gio/.test(id))return 'wind';if(/heat|hot|nang/.test(id))return 'heat';
  return 'clear';
}
/** Sky colours [top, bottom] at the workplace's clock (the daylight layer tints the room on top of this). */
export function skyAt(w){
  const m=Number(w.c?.day_clock?.minute??600),wx=weatherOf(w),grey=wx==='rain'||wx==='storm'||wx==='fog';
  const sky=m<300||m>1230?['#27315a','#4b4f7a']:m<420?['#f2b8a0','#fbe0c4']:m>1110?['#e9967a','#f7c99a']:['#9fd2ee','#e8f5fb'];
  return grey&&m>=300&&m<=1230?['#a9b4bf','#d9dee2']:sky;
}
/** A window: frame, the sky at this hour, an optional view drawn by view(c,x,y,wd,ht), rain, a sill. */
export function windowPane(c,w,x,y,wd,ht,{frame='#e8dccb',bars=2,barW=4,view=null,r=10,sill=true}={}){
  const [a,b]=skyAt(w),wx=weatherOf(w),g=c.createLinearGradient(0,y,0,y+ht);g.addColorStop(0,a);g.addColorStop(1,b);
  R(c,x-6,y-6,wd+12,ht+12,frame,r+4);c.save();c.beginPath();c.roundRect(x,y,wd,ht,r);c.clip();c.fillStyle=g;c.fillRect(x,y,wd,ht);
  const m=Number(w.c?.day_clock?.minute??600);if(m<300||m>1230)for(let i=0;i<6;i++)E(c,x+wd*hash(i+x)%wd,y+ht*.1+ht*.4*hash(i*3+y),1.4,1.4,'#fff8d8');
  if(view)view(c,x,y,wd,ht);
  if(wx==='rain'||wx==='storm'){const t=w.reduced?0:(w.time*240)%28;c.strokeStyle='#e8f1f8aa';c.lineWidth=1.4;for(let i=-2;i<wd/14+2;i++)for(let j=-1;j<ht/28+1;j++){const px=x+i*14+((j*7)%14),py=y+j*28+t;c.beginPath();c.moveTo(px,py);c.lineTo(px-4,py+10);c.stroke();}}
  if(wx==='fog'){c.fillStyle='#ffffff77';c.fillRect(x,y+ht*.4,wd,ht*.6);}
  if(wx==='storm'&&!w.reduced&&Math.sin(w.time*.9)>.985){c.fillStyle='#ffffffaa';c.fillRect(x,y,wd,ht);}
  L(c,x+12,y+8,x+wd*.35,y+ht-8,'#ffffff33',6);
  c.restore();
  for(let i=1;i<=bars;i++)L(c,x+wd*i/(bars+1),y,x+wd*i/(bars+1),y+ht,frame,barW);
  if(sill)R(c,x-10,y+ht+4,wd+20,9,frame,4);
}

/* ------------------------------------------------------------ life */
/** Deterministic 0…1 noise. */
export const hash=i=>{const v=Math.sin(i*127.1+311.7)*43758.5453;return v-Math.floor(v);};
/** A slow background moment: which one (n, fixed per period) and how far along it is (k 0…1, ½ when still). */
export function beat(w,period,seed=0){
  if(w.reduced)return {n:Math.floor(hash(seed)*1000),k:.5,on:false};
  const t=w.time+seed*7.3,slot=Math.floor(t/period);return {n:Math.floor(hash(slot+seed)*1000),k:(t-slot*period)/period,on:true};
}
/** An announcement bubble with the speaker icon: (x,y) is the tail tip. */
export function bubble(c,g,x,y,text,{color='#fffaf0',ink='#2f3d4a',max=null}={}){
  const size=g.port?16:12,maxW=max||(g.port?440:420);c.font=`700 ${size}px "Trebuchet MS", "Segoe UI", sans-serif`;
  const s='📢 '+tr(text),wd=Math.min(maxW,Math.max(120,c.measureText(s).width+28)),ht=size+18;
  const bx=Math.max(g.f.x+10,Math.min(g.f.x+g.f.w-wd-10,x-wd/2));
  R(c,bx,y-ht-8,wd,ht,color,ht/2,'#c9b49a',1.5);P(c,[[x-7,y-9],[x,y],[x+7,y-9]],color);
  T(c,s,bx+wd/2,y-8-ht/2+1,fit(c,s,wd-20,size),ink,700);
}
/** A suitcase standing at (x,y) (bottom middle). */
export function suitcase(c,x,y,s=1,col='#d07a5c'){R(c,x-11*s,y-30*s,22*s,28*s,col,4*s,'#00000033',1);L(c,x-5*s,y-30*s,x-5*s,y-38*s,'#6b6f76',2*s);L(c,x+5*s,y-30*s,x+5*s,y-38*s,'#6b6f76',2*s);L(c,x-5*s,y-38*s,x+5*s,y-38*s,'#6b6f76',2*s);
  L(c,x-6*s,y-24*s,x-6*s,y-8*s,'#ffffff44',2*s);E(c,x-7*s,y-1*s,2.6*s,2.6*s,'#3b3f45');E(c,x+7*s,y-1*s,2.6*s,2.6*s,'#3b3f45');}
const HAIR=['#4a3a33','#6e4f3c','#2f2a28','#8a6a50','#b9b1a8','#5b4636'],SKIN=['#f6d8bf','#eec7a6','#e2b48f','#f9dfc8'],TOP=['#9cc3d5','#e3a7b8','#b8d39c','#f0cf8a','#c4b2e0','#9fb0c4','#e8b48e'];
/** Someone sitting, seen from the front, from the chest up; (x,y) = seat top. kind: 'sleep' | 'kid' | 'read' | 'phone'. */
export function sitter(c,x,y,s,seed,kind=''){
  const n=Math.floor(hash(seed)*997),hair=HAIR[n%6],skin=SKIN[n%4],top=TOP[n%7],kid=kind==='kid',z=kid?.78:1;
  c.save();c.translate(x,y);c.scale(s*z,s*z);
  R(c,-17,-30,34,30,top,12);E(c,0,-46,16,17,hair);E(c,0,-42,13.5,13.5,skin);
  if(n%3===0)R(c,-15,-58,30,9,hair,5);else E(c,-6,-55,10,6,hair);
  if(kind==='sleep'){L(c,-7,-42,-3,-42,'#5a4438',1.6);L(c,3,-42,7,-42,'#5a4438',1.6);T(c,'z',15,-62,10,'#7f8fa0',800);T(c,'z',22,-72,8,'#7f8fa0',800);}
  else{E(c,-5,-42,1.8,2.2,'#4a3a33');E(c,5,-42,1.8,2.2,'#4a3a33');E(c,-9,-37,3,1.6,'#f0a3a0aa');E(c,9,-37,3,1.6,'#f0a3a0aa');}
  if(kind==='read')R(c,-14,-24,28,16,'#fff7e8',2,'#c9b49a',1);
  if(kind==='phone')R(c,6,-30,8,13,'#2f3d4a',2);
  c.restore();
}
/** A tiny walking passer-by drawn in local pixels at (x,y) (feet), facing dir (±1), step phase t. */
export function passer(c,x,y,s,seed,dir,t,{bag=true}={}){
  const n=Math.floor(hash(seed)*997),hair=HAIR[n%6],skin=SKIN[n%4],top=TOP[(n+2)%7],step=Math.sin(t*9)*4;
  c.save();c.translate(x,y);c.scale(s*dir,s);E(c,0,1,15,5,'#00000018');
  R(c,-8,-22+0,6,22,'#5b5f6a',3);R(c,2,-22,6,22,'#5b5f6a',3);
  c.save();c.translate(0,0);R(c,-8+step*.3,-6,7,6,'#3b3f45',2);R(c,2-step*.3,-6,7,6,'#3b3f45',2);c.restore();
  R(c,-12,-52,24,32,top,9);E(c,0,-64,12,12,skin);E(c,0,-70,12,8,hair);E(c,4,-64,1.6,2,'#4a3a33');
  if(bag){L(c,10,-36,18,-8,'#6b6f76',2);suitcase(c,22,4,.75,['#d07a5c','#5b8fb9','#e3b04b','#8fbf8a'][n%4]);}
  c.restore();
}
/** A label plate on the wall. */
export function plate(c,g,x,y,text,{bg='#2f3d4a',ink='#fdf6e8',size=null,pad=16}={}){
  const sz=size||(g.port?15:12);c.font=`800 ${sz}px "Trebuchet MS", "Segoe UI", sans-serif`;const wd=c.measureText(tr(text)).width+pad*2;
  R(c,x-wd/2,y-sz,wd,sz*2,bg,sz);T(c,text,x,y,sz,ink,800);return wd;
}
export {heart};
