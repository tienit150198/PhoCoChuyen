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
 * while this stage is mounted, left on a stall page or when the sheet closes; silent (no "X vừa vào hội"). */
import {VIEW,plan,route,nearestFree,back as paintBack,props,marks,STALLS} from '../scenes/fair-place.js';
import {figure,paintPlayer,CANVAS} from './look.js';
import {t as tr} from './i18n.js';
import {crowd} from './fair-crowd.js';

const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');
const IDLE_MS=80,SAY_MS=4200,WALK_S=.85;

export function setup(ctx){
  const {S,F,go,list,bar,esc,food}=ctx;
  const W=S.walk={el:null,cv:null,c:null,say:null,bg:null,bgKey:'',port:false,k:1,ox:0,oy:0,dpr:1,cw:0,ch:0,
    me:null,arrive:null,raf:0,last:0,drawn:0,time:0,sayAt:0,ok:null,down:null,at:''};
  const has=()=>({dt:!!F().darts,loan:!!F().cash,xs:!!F().scratch});
  const pl=()=>plan(W.port,has());
  const CR=crowd({state:()=>S.env?.api?.state,redraw:()=>{W.drawn=0;},still});
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
    el.innerHTML=`<canvas class="fh-wcanvas" tabindex="0" role="img" aria-label="${esc(tr('Hội chợ: chạm vào gian hàng để đi tới'))}"></canvas><div class="fh-wsay" role="status" aria-live="polite" hidden></div>`;
    W.el=el;W.cv=el.querySelector('canvas');W.c=W.cv.getContext('2d');W.say=el.querySelector('.fh-wsay');
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
    if(W.el.parentNode!==slot){slot.append(W.el);size();}
    else W.drawn=0;   // the state may have changed (a game going on, a stall added): one fresh frame
    if(!W.raf){W.last=performance.now();W.drawn=0;W.raf=requestAnimationFrame(loop);}
    if(!W.hooked){W.hooked=true;S.dlg.addEventListener('close',()=>CR.leave());}
    if(W.me)CR.join(frac([W.me.x,W.me.y]));
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
    W.dpr=Math.min(2,globalThis.devicePixelRatio||1);W.cw=cw;W.ch=ch;
    const w=Math.round(cw*W.dpr),h=Math.round(ch*W.dpr);if(W.cv.width!==w)W.cv.width=w;if(W.cv.height!==h)W.cv.height=h;
    const [x0,y0,x1,y1]=VIEW[W.port?'port':'land'],k=Math.min(cw/(x1-x0),ch/(y1-y0));
    W.k=k;W.ox=(cw-(x1-x0)*k)/2-x0*k;W.oy=(ch-(y1-y0)*k)/2-y0*k;
    if(!W.me){const g=pl().entry.gate;place([g[0]+(Math.random()-.5)*90,g[1]+Math.random()*14]);}   // a little apart from whoever came in just before
    W.drawn=0;draw();
  }
  function place(p){const q=nearestFree(pl(),p)||p;W.me={x:q[0],y:q[1],path:null,step:0};}
  const toScene=(cx,cy)=>{const r=W.cv.getBoundingClientRect();return [(cx-r.left-W.ox)/W.k,(cy-r.top-W.oy)/W.k];};

  /* ---- walking ---- */
  function walkTo(p,then=null){
    const path=route(pl(),[W.me.x,W.me.y],p);W.arrive=then;
    if(!path||still()){const from=[W.me.x,W.me.y],end=path?path[path.length-1]:from;W.me.x=end[0];W.me.y=end[1];W.me.path=null;W.drawn=0;
      CR.walk([frac(from),frac(end)],0);arrived();return;}
    W.me.path=path.slice(1);
    let len=0;for(let i=1;i<path.length;i++)len+=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]);
    W.me.len=len/WALK_S;   // a long walk goes faster: no walk takes more than WALK_S
    CR.walk(path.map(frac),len/Math.max(W.port?380:440,W.me.len)*1000);   // the others see the same walk, as long
  }
  function arrived(){const f=W.arrive;W.arrive=null;W.me.path=null;if(f)f();}
  function hitSpot(p){let best=null,bd=Infinity;for(const s of pl().spots){const d=Math.hypot(s.hit[0]-p[0],s.hit[1]-p[1]);if(d<=s.r&&d<bd){bd=d;best=s;}}return best;}
  function tapAt(cx,cy){
    const p=toScene(cx,cy),spot=hitSpot(p);hush();
    if(spot)goSpot(spot);else walkTo(p);
  }
  function goSpot(s){
    if(!s)return;hush();
    walkTo(s.stand,()=>{if(s.kind==='stall'){W.at=s.id;go(s.tab);}else if(s.cart&&food?.(s.id))W.at=s.id;else speak(s);});   // a food cart opens its menu (else, an older server: its line)
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
  function loop(now){
    if(!W.el?.isConnected||!S.dlg?.open){W.raf=0;CR.leave();return;}   // a stall page or the sheet closed
    W.raf=requestAnimationFrame(loop);
    const dt=Math.min(.05,(now-W.last)/1000);W.last=now;W.time+=dt;
    const m=W.me;let moving=CR.busy();
    if(m?.path?.length){
      const sp=Math.max(W.port?380:440,m.len||0)*dt,[tx,ty]=m.path[0],dx=tx-m.x,dy=ty-m.y,d=Math.hypot(dx,dy);moving=true;
      if(d<=sp){m.x=tx;m.y=ty;m.path.shift();if(!m.path.length)arrived();}else{m.x+=dx/d*sp;m.y+=dy/d*sp;}
      m.step+=dt*9;
    }
    if(W.say&&!W.say.hidden&&now-W.sayAt>SAY_MS)hush();
    if(!moving&&(still()||document.hidden?W.drawn>0:now-W.drawn<IDLE_MS))return;
    W.drawn=now||1;draw();
  }
  function backdrop(){
    const key=[W.port,W.cv.width,W.cv.height,has().dt,has().loan].join('|');
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
    const f=F(),p=pl(),o={t:W.time,reduced:still(),live:{lt:f.loto?.stage==='play',oaq:f.oaq?.stage==='play'}};
    try{
      const items=props(c,p,o),fl=p.floor,base=W.port?.92:.78,depth=y=>.94+.12*(y-fl[1])/Math.max(1,fl[3]-fl[1]);
      items.push([W.me.y+.5,()=>drawMe(c,base*depth(W.me.y))]);
      items.push(...CR.items(c,{xy:(u,v)=>[fl[0]+u*(fl[2]-fl[0]),fl[1]+v*(fl[3]-fl[1])],scale:y=>base*depth(y),px:base*W.k*W.dpr,t:W.time,
        snap:q=>nearestFree(p,q),key:[W.port,p.has.dt,p.has.loan].join('|')}));
      items.sort((a,b)=>a[0]-b[0]);for(const [,fn] of items)fn();
      const near=p.spots.find(s=>s.kind==='stall'&&Math.hypot(W.me.x-s.stand[0],W.me.y-s.stand[1])<30);
      marks(c,p,o,near?.id||null);
      c.setTransform(W.dpr,0,0,W.dpr,0,0);
      CR.tags(c,{sx:x=>W.ox+x*W.k,sy:y=>W.oy+y*W.k,fallback:tr('Khách đi hội')});
    }catch(e){console.warn('hội chợ: draw',e);}
  }
  function drawMe(c,s){
    const m=W.me;c.save();c.translate(m.x,m.y);c.scale(s,s);
    if(m.path?.length&&!still())c.translate(0,-Math.abs(Math.sin(m.step))*3);
    try{paintPlayer(c,figure(S.env.api.state),CANVAS);}catch{/* look not ready */}
    c.restore();
  }

  /* ---- test hooks (scratch browser checks) ---- */
  globalThis.__fairWalk={state:()=>({on:!!W.el?.isConnected,port:W.port,me:W.me&&[W.me.x,W.me.y],walking:!!W.me?.path?.length,at:W.at,
    spots:pl().spots.map(s=>s.id),stage:W.el?.getBoundingClientRect().toJSON(),crowd:CR.state()}),
    screen:id=>{const s=pl().spots.find(q=>q.id===id);if(!s||!W.cv)return null;const r=W.cv.getBoundingClientRect();return [r.left+W.ox+s.hit[0]*W.k,r.top+W.oy+s.hit[1]*W.k];},
    go:id=>goSpot(pl().spots.find(s=>s.id===id)),walk:(u,v)=>{const f=pl().floor;walkTo([f[0]+u*(f[2]-f[0]),f[1]+v*(f[3]-f[1])]);}};

  return {active,html,mount,stalls:STALLS};
}
