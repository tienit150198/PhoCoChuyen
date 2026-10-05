/** 🏮 Đi dạo hội chợ: the fair's gate (Cổng hội) as a fairground to walk (scenes/fair-place.js). The player walks
 * up to a stall and its page (the same stall pages as before, v4/fair.js) opens; "← Ra lối đi" brings them back to
 * where they stood. The two food carts open their menu (v4/fair.js Hàng ăn vặt); the gate and the crowd say a line. A small "Danh sách trò" list under the
 * fairground opens any stall straight away (and is the keyboard's way in; the canvas also walks with the arrows).
 * fair.js owns the dialog and passes its helpers in (setup); its render() patches the page in place and calls
 * mount() after, which puts the one persistent stage (canvas + bubble) back into the page's data-fh-live slot, so a
 * render never rebuilds or blanks the canvas and the page never changes height under the player's finger.
 * Light on phones: the backdrop is painted once per size into a cached bitmap, a frame is the bitmap, the floor's
 * things and the player; frames run only while someone walks, else ~12 per second for the crowd's sway (none at
 * all with reduced motion: the player steps straight to where they tapped) and none while the stall pages are up.
 * 🧑‍🤝‍🧑 The other players on the fairground right now walk around it too (./fair-crowd.js, the live socket): joined
 * while this stage is mounted, left when the sheet closes (or the fair does); silent (no "X vừa vào hội"). On a stall
 * page the player stays there for the others, standing at that stall with its badge (play(); owner, 03/10: nobody
 * vanishes while they play); back on the walk, the badge goes.
 * 🛵 A player who owns a two-wheeler (game/garage.py; a car is too big for the fair's lanes: they walk) rides it here
 * (./ride.js), like in the town: faster, parked beside a stall while they play it, hopped back on for the next walk;
 * the "🛵 Đi xe / 🚶 Đi bộ" button on the stage changes it. The others see it: the crowd's walks carry `r`. */
import {VIEW,plan,route,nearestFree,back as paintBack,props,marks,STALLS} from '../scenes/fair-place.js';
import {figure,figureOf,paintPlayer,CANVAS,lookOf} from './look.js';
import {t as tr} from './i18n.js';
import {crowd} from './fair-crowd.js';
import {choice,next as nextRide,canRide,label as rideLabel,speedOf,drawRide,rider,steer,halfOf,topOf,wire,spouse as spouseOf,loadSpouse} from './ride.js';

const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');
const IDLE_MS=80,SAY_MS=4200,WALK_S=.85,CARTS={candy:'🍡',cane:'🥤'},TWO={two:true};

export function setup(ctx){
  const {S,F,go,list,bar,esc,food}=ctx;
  const W=S.walk={el:null,cv:null,c:null,say:null,bg:null,bgKey:'',port:false,k:1,ox:0,oy:0,dpr:1,cw:0,ch:0,
    me:null,arrive:null,raf:0,timer:0,last:0,drawn:0,time:0,sayAt:0,ok:null,down:null,at:'',playing:'',avatar:null,
    ride:null,rideKey:'',rv:rider(),park:null,legs:[],leg:null,btn:null,fig:null,figKey:'',back:null,taken:null,blocked:'',co:null};
  const has=()=>({dt:!!F().knife,loan:!!F().cash,xs:!!F().scratch,pb:!!F().photo});   // dt: anh Sáu's stall, the phóng dao since it replaced the phi tiêu
  const pl=()=>plan(W.port,has());
  const pixels=new Map();let pixelsKey='',fontEpoch=0;
  document.fonts?.addEventListener?.('loadingdone',()=>{fontEpoch++;W.bgKey='';W.drawn=0;wake();});
  const CR=crowd({state:()=>S.env?.api?.state,content:()=>S.env?.api?.content,redraw:()=>{W.drawn=0;paintCo();wake();},still,onBack,onTaken});
  /** Scene point → fractions of the floor (what the others get: their fairground may be the other layout). */
  const frac=([x,y])=>{const f=pl().floor;return [(x-f[0])/(f[2]-f[0]),(y-f[1])/(f[3]-f[1])];};

  /** Can this browser draw it? (else the list stays, as before) */
  function ok(){
    if(W.ok===null){try{W.ok=!!document.createElement('canvas').getContext('2d')&&typeof ResizeObserver==='function';}catch{W.ok=false;}}
    return W.ok;
  }
  const active=()=>ok()&&!!F().open;

  /** The gate's page: the fairground (a slot the stage is put into after the render) and the list under it. */
  function html(){
    return `<section class="fh-walk" aria-label="Hội chợ">
      <div class="fh-wslot" data-fh-live data-fh-key="wslot"></div>
      <div class="fh-wbar">${bar()}</div>
      <details class="fh-wlist" data-fh-key="wlist"><summary data-fh-key="wlistsum">📋 Danh sách trò</summary>${list()}</details>
    </section>`;
  }
  function build(){
    const el=document.createElement('div');el.className='fh-wstage';
    el.innerHTML=`<canvas class="fh-wcanvas" tabindex="0" role="img" aria-label="${esc(tr('Hội chợ: chạm vào gian hàng để đi tới'))}"></canvas><div class="fh-wsay" role="status" aria-live="polite" hidden></div><button type="button" class="rd-toggle" hidden></button><div class="rd-co" hidden></div>`;
    W.el=el;W.cv=el.querySelector('canvas');W.c=W.cv.getContext('2d');W.say=el.querySelector('.fh-wsay');
    W.btn=el.querySelector('.rd-toggle');W.btn.addEventListener('click',()=>{W.blocked='';W.taken=null;nextRide(S.env.api.state,S.env.api.content,TWO);setRide(true);if(W.me){const h=frac([W.me.x,W.me.y]);CR.walk([h,h],0,null,wire(W.ride));}paintCo();});
    W.co=el.querySelector('.rd-co');W.co.addEventListener('click',e=>{const a=e.target.closest('[data-co]')?.dataset.co;
      if(a==='back'){const sp=spouseOf();W.taken=null;if(sp)CR.back(sp.pid);}
      else if(a==='off'){if(W.me)CR.back(null,frac([W.me.x,W.me.y]));}
      else if(a==='untake'){W.taken=null;}
      paintCo();});
    W.cv.addEventListener('pointerdown',e=>{W.down={x:e.clientX,y:e.clientY,t:performance.now()};});
    W.cv.addEventListener('pointerup',e=>{const d=W.down;W.down=null;if(!d||Math.hypot(e.clientX-d.x,e.clientY-d.y)>14||performance.now()-d.t>800)return;tapAt(e.clientX,e.clientY);});
    W.cv.addEventListener('keydown',onKey);
    let sizing=0;new ResizeObserver(()=>{cancelAnimationFrame(sizing);sizing=requestAnimationFrame(size);}).observe(el);
  }
  /** After every render of fair.js: the stage back into its slot, the frames going. */
  function mount(){
    const slot=S.dlg?.querySelector('.fh-wslot');
    if(!slot||!active())return;
    if(!W.el)build();
    setRide(false);
    loadSpouse(S.env?.api).then(()=>{setRide(false);paintCo();});   // 💑 the spouse's vehicles and live id (none: unchanged)
    if(W.el.parentNode!==slot){slot.append(W.el);size();}
    else W.drawn=0;   // the state may have changed (a game going on, a stall added): one fresh frame
    W.drawn=0;wake();
    hook();
    if(W.me){const here=frac([W.me.x,W.me.y]);if(W.playing){W.playing='';CR.walk([here,here],0,null,wire(W.ride));}CR.join(here,wire(W.ride));}   // off the stall: no badge
  }
  function hook(){if(!W.hooked&&S.dlg){W.hooked=true;S.dlg.addEventListener('close',off);}}
  /** The sheet closed or the fair is over: out of the room. */
  function off(){W.playing='';CR.leave();sleep();}
  /** After every render of fair.js on a stall page (`id`: the stall's tab, or the food cart): for the others the player
   * stands at that stall, its badge over them, until they come back to the walk or leave. Opened from the list, the
   * walk there is played to them; the player stands there too when they come back. "Vay nóng" shows no badge (who
   * borrows stays their own business), a page without a place on the fairground keeps them where they stood. */
  function play(id){
    if(!active()||!S.dlg?.open)return;
    hook();
    const spot=pl().spots.find(q=>q.id===id&&(q.kind==='stall'||q.cart)),key=spot?.id||'-';
    if(W.playing===key)return;
    W.playing=key;
    if(W.back&&W.me){CR.back(null,frac([W.me.x,W.me.y]));W.back=null;}   // 💑 off the vehicle to play
    setRide(false);
    if(!spot){if(W.me)CR.join(frac([W.me.x,W.me.y]),wire(W.ride));return;}
    const end=nearestFree(pl(),spot.stand)||spot.stand;
    if(!W.me)W.me={x:end[0],y:end[1],path:null,step:0};   // straight onto a stall page: the fairground was never drawn
    const from=[W.me.x,W.me.y],far=Math.hypot(end[0]-from[0],end[1]-from[1])>2,path=far&&!still()?route(pl(),from,end):null;
    let len=0;if(path)for(let i=1;i<path.length;i++)len+=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]);
    if(W.ride&&W.park?.id!==spot.id){const q=parkSpot(end,from[0]);W.park={x:q[0],y:q[1],id:spot.id,face:from[0]<=end[0]?1:-1};}   // the vehicle waits by the stall
    W.me.x=end[0];W.me.y=end[1];W.me.path=null;W.arrive=null;W.legs=[];W.leg=null;W.at=spot.id;
    CR.walk((path||[from,end]).map(frac),path?len/Math.max(base()*speedOf(W.ride),len/WALK_S)*1000:0,id==='loan'?null:spot.id,wire(W.ride));
    CR.join(frac(end),wire(W.ride));
  }

  /* ---- layout: the whole fairground fits the stage (its shape follows the width, so it never jumps) ---- */
  function size(){
    if(!W.el?.isConnected)return;
    const wide=W.el.parentNode.getBoundingClientRect().width,port=wide<560;
    if(port!==W.port||!W.el.classList.contains(port?'port':'land')){
      const was=W.port;W.port=port;W.el.classList.toggle('port',port);W.el.classList.toggle('land',!port);
      if(W.me){const a=plan(was,has()).floor,b=pl().floor,u=(W.me.x-a[0])/(a[2]-a[0]),v=(W.me.y-a[1])/(a[3]-a[1]);place([b[0]+u*(b[2]-b[0]),b[1]+v*(b[3]-b[1])]);}
    }
    const r=W.el.getBoundingClientRect(),cw=Math.max(1,r.width),ch=Math.max(1,r.height);
    // Bound the phone fairground's raster area; movement still runs at the display's frame rate.
    W.dpr=Math.min(port?1.5:2,globalThis.devicePixelRatio||1);W.cw=cw;W.ch=ch;
    const w=Math.round(cw*W.dpr),h=Math.round(ch*W.dpr);if(W.cv.width!==w)W.cv.width=w;if(W.cv.height!==h)W.cv.height=h;
    const [x0,y0,x1,y1]=VIEW[W.port?'port':'land'],k=Math.min(cw/(x1-x0),ch/(y1-y0));
    W.k=k;W.ox=(cw-(x1-x0)*k)/2-x0*k;W.oy=(ch-(y1-y0)*k)/2-y0*k;
    if(!W.me){const g=pl().entry.gate;place([g[0]+(Math.random()-.5)*90,g[1]+Math.random()*14]);}   // a little apart from whoever came in just before
    W.drawn=0;draw();wake();
  }
  function place(p){const q=nearestFree(pl(),p)||p;W.me={x:q[0],y:q[1],path:null,step:0};W.park=null;W.legs=[];W.leg=null;}

  /* ---- 🛵 riding (./ride.js; two-wheelers only here) ---- */
  const base=()=>W.port?380:440;   // walking speed, scene units a second
  const riding=()=>!!W.ride&&!W.park&&!W.back;
  /** The vehicle ridden now and the button; `fresh` (a tap on the button): hop on here, or off (it goes home). */
  function setRide(fresh){
    const st=S.env?.api?.state,ct=S.env?.api?.content;if(!st)return;
    let v=choice(st,ct,TWO);if(v&&v.key===W.blocked)v=null;   // 💑 the spouse drives that one now
    const key=v?`${v.key}|${v.hex}`:'';
    if(W.btn){const own=canRide(st,ct,TWO)&&!W.back;W.btn.hidden=!own;
      if(own){const t=tr(rideLabel(v));if(W.btn.textContent!==t)W.btn.textContent=t;W.btn.setAttribute('aria-pressed',String(!!v));W.btn.title=tr(v?v.owner?`Xe của ${v.owner}`:v.name:'Đi bộ');}}
    if(key===W.rideKey)return;
    const had=W.ride;W.ride=v;W.rideKey=key;
    if(!v||!had||fresh)W.park=null;
    W.drawn=0;
    wake();
  }
  /* ---- 💑 sitting behind the spouse (live/coride.py) ---- */
  /** The room says I sit behind `b` now (null: on foot again, at `end`, fractions). */
  function onBack(b,end){
    if(b){W.back=b;W.taken=null;if(W.me){W.me.path=null;}W.legs=[];W.leg=null;W.arrive=null;W.park=null;}
    else if(W.back){W.back=null;
      if(end&&W.me){const f=pl().floor,q=nearestFree(pl(),[f[0]+end[0]*(f[2]-f[0]),f[1]+end[1]*(f[3]-f[1])]);if(q){W.me.x=q[0];W.me.y=q[1];}}
      if(W.me&&!W.playing){const h=frac([W.me.x,W.me.y]);CR.walk([h,h],0,null,wire(W.ride));}}   // my own vehicle (if any) again, for the others too
    setRide(false);W.drawn=0;paintCo();wake();
  }
  /** The spouse drives the vehicle I asked for: on foot until another pick, and a little question. */
  function onTaken(f){W.taken={by:f.by,name:String(f.name||'')};W.blocked=W.ride?.key||W.blocked;setRide(false);W.drawn=0;paintCo();}
  /** The line under the toggle (written only when it changes): sitting behind, a vehicle taken, or "🛵 Ngồi sau". */
  function paintCo(){
    const el=W.co;if(!el)return;
    const sp=CR.coride()?spouseOf():null,d=sp?CR.where(sp.pid):null,here=Boolean(CR.me());   // an older live service: none of it
    const free=here&&!W.back&&!W.playing&&d&&d.r&&!d.b&&!CR.pillion(sp.pid);
    let html='';
    if(W.back){const dd=CR.where(W.back);html=`<span class="rd-co-msg">🛵 ${esc('Đang ngồi sau xe của '+(dd?.name||sp?.name||''))}</span><button type="button" data-co="off">Xuống xe</button>`;}
    else if(W.taken&&here)html=`<span class="rd-co-msg">${esc((W.taken.name||'Người ấy')+' đang lái xe này — ngồi sau nhé?')}</span>${free?'<button type="button" class="primary" data-co="back">Ngồi sau</button>':''}<button type="button" data-co="untake" aria-label="Đóng">×</button>`;
    else if(free)html='<button type="button" class="primary" data-co="back">🛵 Ngồi sau</button>';
    if(el.dataset.k!==html){el.dataset.k=html;el.innerHTML=html;el.hidden=!html;}
  }
  /** The character's size at depth y (the floor's far edge is a little smaller). */
  function scaleAt(y){const fl=pl().floor;return (W.port?.92:.78)*(.94+.12*(y-fl[1])/Math.max(1,fl[3]-fl[1]));}
  /** Where the vehicle waits beside a stand point, on the side the player came from (on free floor). */
  function parkSpot(stand,fromX){
    const side=fromX<=stand[0]?-1:1,off=halfOf(W.ride)*scaleAt(stand[1])+14;
    return nearestFree(pl(),[stand[0]+side*off,stand[1]+10])||[stand[0]+side*off,stand[1]+10];
  }
  const toScene=(cx,cy)=>{const r=W.cv.getBoundingClientRect();return [(cx-r.left-W.ox)/W.k,(cy-r.top-W.oy)/W.k];};

  /* ---- walking (riding: back to the vehicle on foot, ride, park by the stall, the last steps on foot) ---- */
  function walkTo(p,then=null,spot=null){
    wake();
    if(W.back&&CR.where(W.back)){W.co?.querySelector('.rd-co-msg')?.animate?.([{transform:'scale(1)'},{transform:'scale(1.06)'},{transform:'scale(1)'}],{duration:260});return;}   // 💑 the driver drives
    W.arrive=then;
    const legs=[];
    if(!W.ride)legs.push({to:p});
    else if(spot&&W.park?.id===spot.id)legs.push({to:p});   // parked at this very stall
    else{
      if(W.park)legs.push({to:[W.park.x,W.park.y],mount:true});
      if(spot){const from=W.park?W.park.x:W.me.x;legs.push({to:parkSpot(p,from),ride:true,park:spot.id},{to:p});}
      else legs.push({to:p,ride:true});
    }
    W.legs=legs;W.leg=null;
    if(still()){const from=[W.me.x,W.me.y];
      while(W.legs.length){const g=W.legs.shift(),path=route(pl(),[W.me.x,W.me.y],g.to),end=path?path[path.length-1]:[W.me.x,W.me.y];W.me.x=end[0];W.me.y=end[1];legEnd(g);}
      W.me.path=null;W.drawn=0;CR.walk([frac(from),frac([W.me.x,W.me.y])],0,null,wire(W.ride));arrived();return;}
    nextLeg();
  }
  /** The next leg of the walk (none left: arrived); the others see each leg as it starts. */
  function nextLeg(){
    for(;;){
      const g=W.legs.shift();W.leg=g||null;
      if(!g){arrived();return;}
      const path=route(pl(),[W.me.x,W.me.y],g.to);
      let len=0;if(path)for(let i=1;i<path.length;i++)len+=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]);
      if(!path||len<.5){legEnd(g);continue;}
      W.me.path=path.slice(1);
      W.me.len=Math.max(base()*(g.ride?speedOf(W.ride):1),len/(g.ride?WALK_S/1.4:WALK_S));   // a long walk goes faster: none takes more than WALK_S
      CR.walk(path.map(frac),len/W.me.len*1000,null,wire(W.ride));   // the others see the same walk, as long
      return;
    }
  }
  function legEnd(g){
    if(g.mount&&W.park){W.rv=rider(W.park.face??W.rv.face);W.park=null;}
    if(g.park&&W.ride)W.park={x:W.me.x,y:W.me.y,id:g.park,face:W.rv.face};
  }
  function arrived(){const f=W.arrive;W.arrive=null;W.legs=[];W.leg=null;W.me.path=null;if(f)f();}
  function hitSpot(p){let best=null,bd=Infinity;for(const s of pl().spots){const d=Math.hypot(s.hit[0]-p[0],s.hit[1]-p[1]);if(d<=s.r&&d<bd){bd=d;best=s;}}return best;}
  function tapAt(cx,cy){
    const p=toScene(cx,cy),spot=hitSpot(p);hush();
    if(spot)goSpot(spot);else walkTo(p);
  }
  function goSpot(s){
    if(!s)return;hush();
    walkTo(s.stand,()=>{if(s.kind==='stall'){W.at=s.id;go(s.tab);}else if(s.cart&&food?.(s.id))W.at=s.id;else speak(s);},s.kind==='stall'||s.cart?s:null);   // a food cart opens its menu (else, an older server: its line)
  }
  /** Arrows walk, Enter / Space opens what the player stands at. */
  function onKey(e){
    const k={ArrowLeft:[-60,0],ArrowRight:[60,0],ArrowUp:[0,-40],ArrowDown:[0,40]}[e.key];
    if(k){e.preventDefault();hush();walkTo([W.me.x+k[0],W.me.y+k[1]]);return;}
    if(e.key==='Enter'||e.key===' '){
      let best=null,bd=70;for(const s of pl().spots){const d=Math.hypot(s.stand[0]-W.me.x,s.stand[1]-W.me.y);if(d<bd){bd=d;best=s;}}
      if(best){e.preventDefault();goSpot(best);}
    }
  }
  /** A line from what the player walked up to, in a bubble over it. */
  function speak(s){
    const [x,y]=s.hit,sx=W.ox+x*W.k,sy=W.oy+(y-20)*W.k;
    W.say.textContent=tr(s.line||'');W.say.hidden=false;
    W.say.style.left=`${Math.max(70,Math.min(W.cw-70,sx))}px`;W.say.style.top=`${Math.max(44,sy)}px`;
    W.sayAt=performance.now();
  }
  function hush(){if(W.say&&!W.say.hidden){W.say.hidden=true;W.say.textContent='';}}

  /* ---- frames ---- */
  function sleep(){cancelAnimationFrame(W.raf);clearTimeout(W.timer);W.raf=0;W.timer=0;}
  function wake(){
    clearTimeout(W.timer);W.timer=0;
    if(!W.raf&&W.el?.isConnected&&S.dlg?.open&&!document.hidden){W.last=performance.now();W.raf=requestAnimationFrame(loop);}
  }
  document.addEventListener('visibilitychange',()=>{if(document.hidden)sleep();else{W.drawn=0;wake();}});
  RM?.addEventListener?.('change',()=>{W.drawn=0;wake();});
  function loop(now){
    W.raf=0;
    if(!W.el?.isConnected||!S.dlg?.open){W.raf=0;if(!S.dlg?.open)off();return;}   // a stall page (still in the room) or the sheet closed
    if(document.hidden)return;
    const elapsed=Math.max(0,(now-W.last)/1000),dt=Math.min(.05,elapsed);W.last=now;W.time+=Math.min(.25,elapsed);
    const m=W.me;let moving=CR.busy();
    const dr=W.back&&m?CR.where(W.back):null;
    if(dr){const f=pl().floor;m.x=f[0]+dr.x*(f[2]-f[0]);m.y=f[1]+dr.y*(f[3]-f[1]);m.path=null;}   // 💑 where the driver takes me
    else if(m?.path?.length){
      const sp=Math.max(base(),m.len||0)*dt,[tx,ty]=m.path[0],dx=tx-m.x,dy=ty-m.y,d=Math.hypot(dx,dy),x0=m.x;moving=true;
      if(d<=sp){m.x=tx;m.y=ty;m.path.shift();}else{m.x+=dx/d*sp;m.y+=dy/d*sp;}
      m.step+=dt*9;
      if(riding())steer(W.rv,m.x-x0,Math.min(d,sp)/scaleAt(m.y),dt,still());
      if(!m.path.length){m.path=null;const g=W.leg;if(g){legEnd(g);nextLeg();}else arrived();}
    }
    else if(W.rv.turn<1){steer(W.rv,0,0,dt,still());moving=true;}
    if(W.say&&!W.say.hidden&&now-W.sayAt>SAY_MS)hush();
    if(moving||!W.drawn||!still()&&now-W.drawn>=IDLE_MS){W.drawn=now||1;draw();}
    if(!W.el?.isConnected||!S.dlg?.open||document.hidden||W.raf||W.timer)return;
    if(moving)W.raf=requestAnimationFrame(loop);
    else if(!still())W.timer=setTimeout(()=>{W.timer=0;W.raf=requestAnimationFrame(loop);},IDLE_MS);
    else if(W.say&&!W.say.hidden)W.timer=setTimeout(()=>{W.timer=0;wake();},Math.max(1,SAY_MS-(now-W.sayAt)));
  }
  function backdrop(){
    const key=[W.port,W.cv.width,W.cv.height,has().dt,has().loan,has().xs,has().pb].join('|');
    if(W.bg&&W.bgKey===key)return W.bg;
    const bg=W.bg||document.createElement('canvas');bg.width=W.cv.width;bg.height=W.cv.height;
    const c=bg.getContext('2d');c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,bg.width,bg.height);
    c.setTransform(W.dpr*W.k,0,0,W.dpr*W.k,W.dpr*W.ox,W.dpr*W.oy);
    try{paintBack(c,W.port,has(),{t:0,reduced:true});}catch(e){console.warn('hội chợ: backdrop',e);}
    W.bg=bg;W.bgKey=key;return bg;
  }
  function draw(){
    const c=W.c;if(!c||!W.cw||!W.me)return;
    c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,W.cv.width,W.cv.height);c.drawImage(backdrop(),0,0);
    c.setTransform(W.dpr*W.k,0,0,W.dpr*W.k,W.dpr*W.ox,W.dpr*W.oy);
    const f=F(),p=pl(),o={t:W.time,reduced:still(),bitmap,live:{lt:f.loto?.stage==='play',oaq:f.oaq?.stage==='play'}};
    const key=[W.port,W.dpr,W.k,fontEpoch,document.documentElement.lang].join('|');
    if(key!==pixelsKey){pixels.clear();pixelsKey=key;}
    try{
      const items=props(c,p,o),fl=p.floor,base=W.port?.92:.78,depth=y=>.94+.12*(y-fl[1])/Math.max(1,fl[3]-fl[1]);
      items.push([W.me.y+.5,()=>drawMe(c,base*depth(W.me.y))]);
      const pk=W.ride&&W.park;
      if(pk)items.push([pk.y+.4,()=>drawRide(c,{x:pk.x,y:pk.y,s:base*depth(pk.y),px:W.k*W.dpr,v:W.ride,r:{face:pk.face??1,from:pk.face??1,turn:1,ang:0}})]);
      items.push(...CR.items(c,{xy:(u,v)=>[fl[0]+u*(fl[2]-fl[0]),fl[1]+v*(fl[3]-fl[1])],scale:y=>base*depth(y),px:base*W.k*W.dpr,unit:W.k*W.dpr,t:W.time,
        snap:q=>nearestFree(p,q),key:[W.port,p.has.dt,p.has.loan,p.has.xs,p.has.pb].join('|'),stand:id=>p.spots.find(q=>q.id===id)?.stand||null,me:W.back?myFig():null}));
      items.sort((a,b)=>a[0]-b[0]);for(const [,fn] of items)fn();
      const near=p.spots.find(s=>s.kind==='stall'&&Math.hypot(W.me.x-s.stand[0],W.me.y-s.stand[1])<30);
      marks(c,p,o,near?.id||null);
      c.setTransform(W.dpr,0,0,W.dpr,0,0);
      CR.tags(c,{sx:x=>W.ox+x*W.k,sy:y=>W.oy+y*W.k,fallback:tr('Khách đi hội'),badge,dpr:W.dpr});
    }catch(e){console.warn('hội chợ: draw',e);}
  }
  /** Small transparent sprites keep each static prop at its original depth; markers translate them as they bob. */
  function bitmap(id,box,paint){
    let entry=pixels.get(id);
    if(!entry){
      const [x,y,w,h]=box,px=W.dpr*W.k,cv=document.createElement('canvas');
      cv.width=Math.ceil(w*px);cv.height=Math.ceil(h*px);
      const c=cv.getContext('2d');c.setTransform(px,0,0,px,-x*px,-y*px);paint(c);
      entry={cv,box};pixels.set(id,entry);
    }
    const [x,y,w,h]=entry.box;W.c.drawImage(entry.cv,x,y,w,h);
  }
  /** The badge over someone playing stall `id` (the stall's own, a snack for the carts; none for the lender). */
  const badge=id=>id==='loan'?'':STALLS[id]?.icon||CARTS[id]||'';
  /** My figure for a vehicle (mine, or my spouse's when I sit behind), cached on my look. */
  function myFig(){
    const st=S.env.api.state,key=JSON.stringify([lookOf(st),st.journey?.gender]);
    if(key!==W.figKey){W.figKey=key;W.fig=figure(st);}
    return {F:W.fig,fk:key};
  }
  function drawMe(c,s){
    const m=W.me;
    if(W.back&&CR.where(W.back))return;   // 💑 the crowd draws me behind my driver
    if(riding()){
      const me=myFig(),q=CR.me()?CR.pillion(CR.me()):null;
      if(q){q.fig??=figureOf(q.lk,q.g);q.byMe=true;q.sx=m.x;q.sy=m.y;q.top=m.y-(topOf(W.ride)+16)*s;}   // her name over mine
      drawRide(c,{x:m.x,y:m.y,s,px:W.k*W.dpr,F:me.F,fkey:me.fk,F2:q?.fig||null,fkey2:q?.fk||'',v:W.ride,r:W.rv});return;
    }
    c.save();c.translate(m.x,m.y);c.scale(s,s);
    if(m.path?.length&&!still())c.translate(0,-Math.abs(Math.sin(m.step))*3);
    try{
      const me=myFig(),px=Math.max(.1,W.dpr*W.k*s),key=`${me.fk}|${Math.round(px*100)}`;
      if(W.avatar?.key!==key){
        const cv=document.createElement('canvas');cv.width=Math.ceil(110*px);cv.height=Math.ceil(160*px);
        const q=cv.getContext('2d');q.setTransform(px,0,0,px,55*px,150*px);paintPlayer(q,me.F,CANVAS);W.avatar={key,cv};
      }
      c.drawImage(W.avatar.cv,-55,-150,110,160);
    }catch{/* look not ready */}
    c.restore();
  }

  /* ---- test hooks (scratch browser checks) ---- */
  globalThis.__fairWalk={state:()=>({on:!!W.el?.isConnected,port:W.port,me:W.me&&[W.me.x,W.me.y],walking:!!W.me?.path?.length,at:W.at,
    ride:W.ride?.id||null,riding:riding(),back:W.back,co:W.co&&!W.co.hidden?W.co.textContent:null,park:W.park&&[Math.round(W.park.x),Math.round(W.park.y)],toggle:W.btn&&!W.btn.hidden?W.btn.textContent:null,
    spots:pl().spots.map(s=>s.id),stage:W.el?.getBoundingClientRect().toJSON(),crowd:CR.state()}),
    screen:id=>{const s=pl().spots.find(q=>q.id===id);if(!s||!W.cv)return null;const r=W.cv.getBoundingClientRect();return [r.left+W.ox+s.hit[0]*W.k,r.top+W.oy+s.hit[1]*W.k];},
    go:id=>goSpot(pl().spots.find(s=>s.id===id)),walk:(u,v)=>{const f=pl().floor;walkTo([f[0]+u*(f[2]-f[0]),f[1]+v*(f[3]-f[1])]);}};

  return {active,html,mount,play,off,stalls:STALLS};
}
