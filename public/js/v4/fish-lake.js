/** 🎣 Hồ câu đông vui (owner 24/10: "map câu cá nhiều người vào vẫn thấy được nhé, thấy nhân vật như ở ngoài luôn … để ai
 * câu lên con gì mình nhìn được ấy"): the lake's live room (live/fish_lake.py) and how the other fishers are drawn on the
 * lake's canvas (v4/fishing.js calls drawLake each frame, then its own player and line on top).
 *
 * createLake({live, spot, trip, me, on}): join with the look (the carried fish apart as {sp, kg}, checked by the
 * service), keep the fishers there (a whole entry with the look for the ones near my view, a name and a place for the
 * rest), their hints (cast with its distance, bite, reel, lost), their catches (only the server's: after their
 * jr_fish_land committed) and bubbles, the lake's feed; act(k, extra) sends my own hints, view(cam) tells the service
 * where I look (a pan), card(pid) asks for a fisher's mini card, say(text) a bubble. Without a live socket (the service
 * off or down) it holds nobody and the lake is the single player's, as before.
 *
 * Drawing (60 fps on a phone with a crowd): each character is painted once into a small canvas (look.js paintPlayer, the
 * wings and the carried fish with it) and reused, the name tag likewise; the FULL_DRAW nearest the view's middle are
 * drawn whole, the others in sight as light silhouettes, nobody out of sight at all. Old-Safari safe, no library. */
import {posOf,spacing,figScale,screenX,extent,clampCam,inView,detailed,offscreen,waterPoint,arcPoint,hitPeer,tierOf,feedLine,merge,catchPose,VIEW_STEP} from './fish-lake-layout.js';
import {figureOf,figCanvas,withWings,withFish} from './look.js';
import {drawFish,fmtKg,RARITY_COLORS} from './fish-art.js';
import {drawRod,rodTipOf,rodLook,lineColor} from './fish-rod.js';
import {paint as stPaint} from './style-tag.js';
import {titles as hnTitles,icons as hnIcons} from './honours.js';
import {pick as hfPick} from './honour-frames.js';
import {exPill,exRain,exInk} from './exclusive.js';   // 🌧️ an exclusive honour's frame: its name tag rains
import {tagLine,badge as bgBadge} from './bang-tag.js';

export {posOf,spacing,figScale,screenX,extent,clampCam,offscreen,hitPeer,tierOf,feedLine};
const BUBBLE_S=6,CATCH_S=3.8,LEAP_S=1,FLY_S=1.1,FEED_MAX=20;
const FRAMES=['fl_in','fl_view','fl_act','fl_card','fl_say'];

export function createLake({live,spot,trip='',me={},clock=()=>performance.now()/1000,on={}}){
  const peers=new Map(),feed=[],offs=[],self={said:null};
  let room=null,myPid=null,mySlot=0,n=1,stopped=false,sentC=null;
  const fire=(k,...a)=>{try{on[k]?.(...a);}catch(e){console.warn('lake:',e);}};
  function join(){
    if(stopped||!live||!live.flags?.fish)return false;   // an older service: the lake stays mine alone
    const {fh,...bare}=me.look||{};   // 🎣 the carried fish goes apart as {sp, kg}: the service checks it (live/fish_carry.py)
    const f=me.fh||fh;
    return live.send({t:'fl_in',spot,...(trip?{trip}:{}),look:bare,g:me.gender||null,rod:me.rod||'tre',...(f?.sp?{fh:{sp:f.sp,kg:f.kg}}:{})});
  }
  function catchOf(e,p){
    const t=clock();
    if(p)p.a=null;
    if(e.pid!==myPid&&p)p.got={s:e.s||null,g:Number(e.g)||0,r:Number(e.r)||0,junk:e.junk||null,t0:t,from:p.lastLand||null};
    if(e.feed){feed.push(e.feed);if(feed.length>FEED_MAX)feed.splice(0,feed.length-FEED_MAX);}
    fire('catch',e,p||null,e.pid===myPid);
  }
  function event(e){
    const p=peers.get(e.pid),t=clock();
    if(e.k==='in'){if(e.pid===myPid)return;if(!p)n++;peers.set(e.pid,merge(p,e));fire('change','in');return;}
    if(e.k==='out'){if(p){peers.delete(e.pid);n=Math.max(1,n-1);fire('change','out');}return;}
    if(e.k==='catch'){catchOf(e,p);return;}
    if(e.k==='said'){const b={text:String(e.text||'').slice(0,160),t0:t};if(e.pid===myPid)self.said=b;else if(p)p.said=b;return;}
    if(e.k==='act'&&p){
      if(e.a==='idle'){p.a=null;return;}
      if(e.a==='lost'){p.a={k:'lost',t0:t,d:p.a?.d||0,x:p.a?.x||0};return;}
      if(e.rod)p.rod=e.rod;
      p.a=e.a==='cast'?{k:'cast',d:Number(e.d)||20,x:Number(e.x)||0,t0:t}:{...(p.a||{k:'cast',d:30,x:0}),k:e.a,t1:t};
    }
  }
  if(live){
    offs.push(live.on('fl_room',f=>{if(stopped||f.spot!==spot)return;room=f.room;myPid=f.me;mySlot=Number(f.s)||0;n=Number(f.n)||1;sentC=posOf(mySlot);
      peers.clear();for(const x of [...(f.people||[]),...(f.far||[])])if(x?.pid&&x.pid!==myPid)peers.set(x.pid,merge(null,x));
      feed.splice(0,feed.length,...(f.feed||[]).slice(-FEED_MAX));fire('change','room');}));
    offs.push(live.on('fl',f=>{if(stopped||f.room!==room)return;for(const e of f.ev||[])event(e);}));
    offs.push(live.on('fl_near',f=>{if(stopped||f.room!==room)return;for(const x of f.people||[])if(x?.pid&&x.pid!==myPid)peers.set(x.pid,merge(peers.get(x.pid),x));}));
    offs.push(live.on('fl_card',f=>{if(!stopped)fire('card',f);}));
    offs.push(live.on('fl_left',f=>{if(stopped||f.why==='out')return;room=null;peers.clear();fire('change','left');fire('left',f.why);}));
    offs.push(live.on('welcome',()=>{if(!stopped){room=null;join();}}));
    offs.push(live.on('down',()=>{room=null;peers.clear();fire('change','down');}));
    offs.push(live.on('error',f=>{if(!stopped&&FRAMES.includes(f.ref)&&f.code!=='slow')fire('error',f);}));
  }
  return {
    peers,feed,self,
    get online(){return Boolean(room);},get me(){return myPid;},get slot(){return mySlot;},get count(){return room?n:1;},
    get pos(){return posOf(mySlot);},
    start(){join();return this;},
    /** My hint: 'cast' {d, x, rod}, 'bite', 'reel', 'lost', 'idle'. */
    act(k,extra={}){if(room)live.send({t:'fl_act',k,...extra});},
    /** The view's middle moved: ask for the whole entries there once it is VIEW_STEP away from the last ask. */
    view(cam){if(!room)return;if(sentC!=null&&Math.abs(cam-sentC)<VIEW_STEP)return;sentC=Math.round(cam*100)/100;live.send({t:'fl_view',c:sentC});},
    card(pid){return room?live.send({t:'fl_card',pid}):false;},
    say(text){return room&&text?live.send({t:'fl_say',text}):false;},
    stop(){if(stopped)return;stopped=true;if(room)live.send({t:'fl_out'});room=null;peers.clear();offs.splice(0).forEach(off=>off());},
  };
}

/* ---------------------------------------------------------------- drawing */
const SPR=new Map();   // key → {cv, w, h, ox, oy}: a character painted once
const SPR_MAX=90;
/** The box of a plain character on the lake (look units, feet at 0, 0): wings and a carried fish grow it (look.js
 * figBounds), so a Huyền thoại pair or a 300 kg fish over the shoulder is never cut off (owner 25/10 "bị mất cái cánh"). */
export const LAKE_BOX=Object.freeze([-85,-160,85,15]);
/** A character's canvas at `scale` (css px per look unit) × dpr: feet at (ox, oy), w × h css px. */
export function sprite(lk,g,{wg=null,fh=null,rk=null}={},scale=.4,dpr=1,F0=null){
  const px=Math.round(scale*dpr*100)/100,key=JSON.stringify([F0?'me':'', F0?F0.L:lk,g,wg,fh,rk,px]);
  let s=SPR.get(key);if(s){SPR.delete(key);SPR.set(key,s);return s;}
  if(!globalThis.document?.createElement)return null;
  let F=null;try{F=F0||figureOf(withFish(withWings(lk||{},wg),fh),g==='male'||g==='female'?g:'none');if(rk&&!F0)F.rk=rk;}catch(e){console.warn('lake: look',e);}
  let b=null;try{b=F?figCanvas(F,px,LAKE_BOX):null;}catch(e){console.warn('lake: look',e);}
  if(!b){const cv=globalThis.document.createElement('canvas');cv.width=Math.ceil(170*px);cv.height=Math.ceil(175*px);b={cv,ox:85,oy:160,w:170,h:175};}
  const k=px/dpr;s={cv:b.cv,w:b.w*k,h:b.h*k,ox:b.ox*k,oy:b.oy*k};
  SPR.set(key,s);if(SPR.size>SPR_MAX)SPR.delete(SPR.keys().next().value);
  return s;
}
export const spriteCount=()=>SPR.size;

/** The name tag (a pill: the name with its bang badge and 🎨 colour / frame of the week, and a line of 🏅 titles) painted
 * once per look of it. */
function tagOf(p,api,dark,dpr){
  const bang=tagLine(p.bg,true),L=hnTitles(api,p.tt),lead=L.length?`${L[0].emoji} ${L[0].short}`:'',more=L.length?hnIcons(api,p.tt,lead):'';
  const title=[bang,lead&&(more?`${lead} ${more}`:lead)].filter(Boolean).join(' · ');
  const name=(bgBadge(p.bg)?`${bgBadge(p.bg)} `:'')+(p.name||'?');
  const ex=Boolean(p.tt&&hfPick(p.tt,p.st)?.ex);   // 🌧️ Mưa rơi (game/exclusive.py)
  const key=JSON.stringify([name,title,p.st,dark,dpr,ex]);
  if(p.tag?.key===key)return p.tag;
  const cv=globalThis.document?.createElement?.('canvas');if(!cv)return null;
  const c=cv.getContext('2d'),nf='700 11px "Trebuchet MS",sans-serif',tf='600 9px "Trebuchet MS",sans-serif';
  c.font=nf;const nw=c.measureText(name).width;c.font=tf;const tw=title?c.measureText(title).width:0;
  const w=Math.ceil(Math.min(170,Math.max(nw,tw))+12),h=title?27:16;
  cv.width=Math.ceil(w*dpr);cv.height=Math.ceil(h*dpr);c.setTransform(dpr,0,0,dpr,0,0);
  const sp=p.st?stPaint(api,p.st,dark):null;
  if(ex){   // 🌧️ the glass pill, its ink; the rain is drawn over it each frame (drawLake)
    exPill(c,1,1,w-2,h-2,dark,7);const ink=exInk(c,(w-nw)/2,(w+nw)/2,dark);
    c.textAlign='center';c.textBaseline='top';c.font=nf;c.fillStyle=ink.name;c.fillText(name,w/2,2.5,w-8);
    if(title){c.font=tf;c.fillStyle=ink.title;c.fillText(title,w/2,15,w-8);}
    p.tag={key,cv,w,h,ex};return p.tag;
  }
  c.fillStyle=dark?'rgba(24,24,34,.8)':'rgba(255,253,248,.88)';c.beginPath();(c.roundRect?c.roundRect(.5,.5,w-1,h-1,7):c.rect(.5,.5,w-1,h-1));c.fill();
  if(sp?.ring){c.strokeStyle=sp.ring;c.lineWidth=2;c.stroke();}
  let fill=dark?'#f1ede6':'#4a3b35';
  if(sp?.grad){const gr=c.createLinearGradient(6,0,6+nw,0);gr.addColorStop(0,sp.grad[0]);gr.addColorStop(1,sp.grad[1]);fill=gr;}else if(sp?.color)fill=sp.color;
  c.textAlign='center';c.textBaseline='top';c.font=nf;c.fillStyle=fill;c.fillText(name,w/2,2.5,w-8);
  if(title){c.font=tf;c.fillStyle=dark?'#c9c1b6':'#8a7a70';c.fillText(title,w/2,15,w-8);}
  p.tag={key,cv,w,h};return p.tag;
}

/** A speech bubble whose tail points at (x, bottom); returns its top. */
export function bubble(c,x,bottom,text,alpha,dark){
  c.font='600 12px "Trebuchet MS",sans-serif';
  const max=150,words=String(text).split(/\s+/),lines=[];let line='';
  for(const w of words){const t=line?line+' '+w:w;if(c.measureText(t).width<=max||!line)line=t;else{lines.push(line);line=w;}if(lines.length===2)break;}
  if(lines.length<2&&line)lines.push(line);
  const lw=Math.min(max,Math.max(...lines.map(l=>c.measureText(l).width))),w=lw+16,h=lines.length*15+8,top=bottom-h-5;
  c.globalAlpha=alpha;c.fillStyle=dark?'#2b2a36':'#fffdf8';c.strokeStyle=dark?'#4a4858':'#e3d6c6';c.lineWidth=1;
  c.beginPath();(c.roundRect?c.roundRect(x-w/2,top,w,h,9):c.rect(x-w/2,top,w,h));c.fill();c.stroke();
  c.beginPath();c.moveTo(x-5,top+h-.5);c.lineTo(x,bottom);c.lineTo(x+5,top+h-.5);c.closePath();c.fill();
  c.fillStyle=dark?'#f1ede6':'#3c302b';c.textAlign='center';c.textBaseline='top';
  lines.forEach((l,i)=>c.fillText(l,x,top+5+i*15));c.globalAlpha=1;
  return top;
}

/** The rod's tip for a fisher standing at (x, py) at `scale`: `a` radians right of straight up. */
export function rodOf(x,py,scale,a,id='tre'){const L=(60+70*scale)*rodLook(id).len,bx=x+24*scale,by=py-40*scale;return {bx,by,x:bx+Math.sin(a)*L,y:by-Math.cos(a)*L};}

/** The boardwalk along the bank, as long as the screen, its posts at each place in sight, a small jetty at each fisher. */
function boardwalk(c,g,view,night,list){
  const y=g.shore-30,{w}=g;
  c.fillStyle=night?'#463625':'#a5743f';c.fillRect(0,y,w,22);
  c.fillStyle=night?'#2e2416':'#6e4a26';c.fillRect(0,y+20,w,4);
  c.strokeStyle=night?'#382a1a':'#8a5e30';c.lineWidth=1;c.beginPath();for(let i=1;i<3;i++){c.moveTo(0,y+i*7);c.lineTo(w,y+i*7);}c.stroke();
  const off=((-view.cam*view.sp)%24+24)%24;c.fillStyle=night?'#32261a':'#7a5230';
  for(let x=off-24;x<w+24;x+=24)c.fillRect(x,y+22,3,8);
  for(const p of list){const x=screenX(posOf(p.s),view.cam,view.sp,w);if(x<-40||x>w+40)continue;
    c.fillStyle=night?'#4a3a28':'#9a6b3c';c.fillRect(x-view.sp*.32,y-6,view.sp*.64,10);}
}

/** The others at the lake, drawn under my own player and line (v4/fishing.js draw): lines, bobbers and leaping fish on
 * the water, the characters on the boardwalk, then their tags, bubbles and the fish held up. `view`: {cam, sp, scale,
 * py, dpr, dark, api, sp: spacing, spOf(id), rarOf(r), calm}. Returns how many were drawn whole. */
export function drawLake(c,g,lake,t,view){
  const list=[...lake.peers.values()],{w}=g,night=view.dark;
  boardwalk(c,g,view,night,list);
  if(!list.length)return 0;
  const whole=detailed(list,view.cam,view.sp,w),shown=[];
  for(const p of list){const x=screenX(posOf(p.s),view.cam,view.sp,w);if(x<-view.sp||x>w+view.sp)continue;shown.push([p,x]);}
  // the water first: each one's line and bobber, a fish fought or leaping
  for(const [p,x] of shown)if(whole.has(p.pid))water(c,g,p,x,t,view);
  for(const [p,x] of shown){
    if(!whole.has(p.pid)){silhouette(c,x,view.py,view.scale*.92,night);continue;}
    const s=sprite(p.lk,p.g,{wg:p.wg,fh:p.fh},view.scale,view.dpr);
    c.fillStyle='rgba(0,0,0,.22)';c.beginPath();c.ellipse(x,view.py+3,15*view.scale*2,4,0,0,7);c.fill();
    if(s)c.drawImage(s.cv,x-s.ox,view.py-s.oy,s.w,s.h);
    rod(c,p,x,t,view);
  }
  for(const [p,x] of shown){
    if(!whole.has(p.pid))continue;
    let top=view.py-128*view.scale-6;
    const held=p.got&&t-p.got.t0<CATCH_S?p.got:null;
    if(held)top=heldUp(c,p,held,x,top,t,view);
    const tg=tagOf(p,view.api,night,view.dpr);if(tg){c.drawImage(tg.cv,x-tg.w/2,top-tg.h,tg.w,tg.h);if(tg.ex)exRain(c,x-tg.w/2+1,top-tg.h+1,tg.w-2,tg.h-2,t,night,7);top-=tg.h+3;}
    if(p.said){const age=t-p.said.t0;if(age>BUBBLE_S)p.said=null;else bubble(c,x,top,p.said.text,age>BUBBLE_S-.5?(BUBBLE_S-age)/.5:1,night);}
  }
  return whole.size;
}
function silhouette(c,x,py,s,night){
  c.fillStyle=night?'rgba(200,215,240,.22)':'rgba(40,60,80,.28)';
  c.beginPath();c.arc(x,py-95*s,22*s,0,7);c.fill();
  c.beginPath();(c.roundRect?c.roundRect(x-20*s,py-70*s,40*s,62*s,12*s):c.rect(x-20*s,py-70*s,40*s,62*s));c.fill();
  c.strokeStyle=c.fillStyle;c.lineWidth=1.5;c.beginPath();c.moveTo(x+22*s,py-40*s);c.lineTo(x+55*s,py-150*s);c.stroke();
}
function angleOf(p,t){
  const a=p.a;if(!a)return .35;
  if(a.k==='cast')return t-a.t0<FLY_S?.08+.9*Math.max(0,.25-(t-a.t0))*4:.3;
  if(a.k==='reel')return .55+.12*Math.sin(t*14);
  if(a.k==='bite')return .4+.05*Math.sin(t*20);
  return .35;
}
/** Their own rod (p.rod on the wire), as it looks (v4/fish-rod.js). */
function rod(c,p,x,t,view){
  const r=rodOf(x,view.py,view.scale,angleOf(p,t),p.rod),bend=p.a?.k==='reel'?10+4*Math.sin(t*9):0;
  const R={bx:r.bx,by:r.by,cx:(r.bx+r.x)/2+bend*.3,cy:(r.by+r.y)/2-bend*.2,x:r.x+bend*.5,y:r.y+bend,s:.8,t,calm:view.calm};
  drawRod(c,p.rod,R);p.tip=rodTipOf(p.rod,R);
}
/** A fisher's line and bobber (the tip is last frame's: drawn before the rod so the character covers its butt). */
function water(c,g,p,x,t,view){
  const a=p.a,tip=p.tip||[x+40*view.scale,view.py-110*view.scale];
  if(!a||a.k==='lost'){if(a&&t-a.t0>1.2)p.a=null;return;}
  const land=waterPoint(g,x,a.d,a.x);p.lastLand=land;
  let b=land;
  if(a.k==='cast'&&t-a.t0<FLY_S){b=arcPoint(tip,land,(t-a.t0)/FLY_S,40+120*Math.min(1,a.d/(g.M||100)));}
  else if(a.k==='reel'){const k=Math.min(.85,(t-(a.t1||t))/8);b=[land[0]+(x-land[0])*k+Math.sin(t*3)*6,g.yOf(a.d*(1-k))];}
  else b=[land[0],land[1]+Math.sin(t*2.2)*1.2+(a.k==='bite'?4+3*Math.sin(t*16):0)];
  c.strokeStyle=lineColor(p.rod);c.lineWidth=1;c.beginPath();c.moveTo(tip[0],tip[1]);
  if(a.k==='reel')c.lineTo(b[0],b[1]);else c.quadraticCurveTo((tip[0]+b[0])/2,Math.max(tip[1],b[1])-Math.abs(b[1]-tip[1])*.25+18,b[0],b[1]);
  c.stroke();
  if(a.k==='reel'){c.globalAlpha=.4;c.fillStyle='#0a2233';c.beginPath();c.ellipse(b[0],b[1]+3,9,3,Math.sin(t*3)*.2,0,7);c.fill();c.globalAlpha=1;return;}
  const k=Math.max(.5,(b[1]-g.hor)/(g.shore-g.hor));
  c.fillStyle='#fff';c.beginPath();c.arc(b[0],b[1]-2,3*k+.6,Math.PI,0);c.fill();c.fillStyle='#e8392b';c.beginPath();c.arc(b[0],b[1]-2,3*k+.6,0,Math.PI);c.fill();
  if(a.k==='bite'){const s=1+.15*Math.sin(t*18);c.fillStyle='#fff';c.beginPath();c.arc(b[0],b[1]-16,8*s,0,7);c.fill();
    c.fillStyle='#e8392b';c.font=`900 ${Math.round(13*s)}px system-ui,sans-serif`;c.textAlign='center';c.textBaseline='middle';c.fillText('!',b[0],b[1]-15);}
}
/** 🐟 The catch: it leaps from the water into their hands, then is held up over their head with its name and weight (a
 * glow for 🟣 Hiếm and up, rays for 🟡 🔴). Returns the top it leaves for the tag. */
function heldUp(c,p,h,x,top,t,view){
  const age=t-h.t0,sp=h.s?view.spOf?.(h.s):null,pose=sp?catchPose(h.g,view.scale):{len:24,big:false,dx:0,dy:0};
  const len=pose.len,head=pose.big?[x+pose.dx,view.py+pose.dy]:[x,top-8],u=Math.min(1,age/LEAP_S),from=h.from||[x+20,view.py-150];
  const pt=u<1?arcPoint(from,head,u,90+(pose.big?len*.3:0)):[head[0],head[1]+(pose.big?0:Math.sin(t*5)*1.5)];
  const fade=age>CATCH_S-.5?(CATCH_S-age)/.5:1,tier=tierOf(h.r);
  c.globalAlpha=fade;
  if(sp&&tier!=='plain'){const col=RARITY_COLORS[h.r]||'#fff',R=Math.min(110,len*(tier==='legend'?1.5:1.1))*(1+.08*Math.sin(t*6));
    const gr=c.createRadialGradient(pt[0],pt[1],2,pt[0],pt[1],R);gr.addColorStop(0,col+'cc');gr.addColorStop(1,col+'00');c.fillStyle=gr;c.beginPath();c.arc(pt[0],pt[1],R,0,7);c.fill();
    if(tier==='legend'&&!view.calm){c.strokeStyle=col+'aa';c.lineWidth=2;c.beginPath();for(let i=0;i<10;i++){const an=t*1.4+i*Math.PI/5;c.moveTo(pt[0]+Math.cos(an)*R*.6,pt[1]+Math.sin(an)*R*.6);c.lineTo(pt[0]+Math.cos(an)*R*1.25,pt[1]+Math.sin(an)*R*1.25);}c.stroke();}
    if(!view.calm)for(let i=0;i<6;i++){const an=t*2+i*1.05,rr=R*(.5+.4*Math.sin(t*3+i));c.fillStyle='#fff';c.fillRect(pt[0]+Math.cos(an)*rr,pt[1]+Math.sin(an)*rr,2,2);}}
  if(sp)drawFish(c,sp,pt[0],pt[1],len,{angle:u<1?Math.sin(t*14)*.3:0,flip:pose.big,wiggle:u<1||pose.big?(t*(pose.big?.8:3))%1:0,glow:tier!=='plain'});
  else{c.font='22px system-ui,sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillText(view.junkEmoji?.(h.junk)||'🥾',pt[0],pt[1]);}
  let y=pose.big?top:pt[1]-len*.32-4;   // a big one lies beside them: its label over their head as usual
  if(u>=1&&sp){const R=view.rarOf?.(h.r)||{},label=`${R.emoji||''} ${sp.name} · ${fmtKg(h.g)}`;
    c.font='800 11px "Trebuchet MS",sans-serif';const tw=Math.min(190,c.measureText(label).width)+12;
    c.fillStyle=RARITY_COLORS[h.r]||'#556';c.beginPath();(c.roundRect?c.roundRect(x-tw/2,y-17,tw,16,8):c.rect(x-tw/2,y-17,tw,16));c.fill();
    c.fillStyle='#fff';c.textAlign='center';c.textBaseline='middle';c.fillText(label,x,y-9,tw-8);y-=20;}
  c.globalAlpha=1;
  return Math.min(top,y);
}
