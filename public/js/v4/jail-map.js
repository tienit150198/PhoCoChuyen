/** 🚔 Trại tạm giữ as a place to walk (owner 09/10: "vô tù có map, di chuyển này kia được nữa đi chứ đừng mỗi cái
 * hình"). The jailed player's own character (outfit and all, v4/look.js) walks the camp of scenes/jail-place.js: tap
 * the yard to walk there, tap a place to walk up to it; on arrival ./jail.js opens that place's panel over the stage
 * (a công ích task where it is done, the bunk ends the day, the phòng thăm gặp asks the friends for bail, the cán bộ
 * trực and the Cổng trại say how long is left). Two inmates and a cán bộ stroll and chat in bubbles (cosmetic,
 * client only: nothing is sent, nothing is saved; where the player stands is forgotten when the page goes).
 * Like the pagoda's walk (v4/chua-visit.js): one persistent canvas, the pagoda's path finder; like the fair's
 * (v4/fair-walk.js): the backdrop is painted once per size and state into a cached bitmap, the player is one cached
 * sprite, frames run only while someone walks (else ~12 a second for the strollers; none with reduced motion, where
 * the player steps straight to where they tapped and the others stand still). Arrow keys walk, Enter uses the place
 * the player stands at. jail.js owns the dialog and passes its helpers in (setup). */
import {VIEW,PEOPLE,plan,route,nearestFree,back as paintBack,props,marks,bubble,cap,frame,portraitFor,folk} from '../scenes/jail-place.js';
import {figure,paintPlayer,CANVAS,lookOf} from './look.js';
import {t as tr} from './i18n.js';

const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
export const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');
const IDLE_MS=84,SAY_MS=4200,SPEED=260,NPC_SPEED=70;

/** Can this browser draw the camp? (else ./jail.js keeps its card page) */
let can=null;
export function canMap(){
  if(can===null){try{can=!!document.createElement('canvas').getContext('2d')&&typeof ResizeObserver==='function';}catch{can=false;}}
  return can;
}

export function setup(ctx){
  const {J,arrive,leave,panelBox,state}=ctx;
  const W={el:null,cv:null,c:null,port:false,k:1,ox:0,oy:0,dpr:1,cw:0,ch:0,cam:null,me:null,then:null,raf:0,timer:0,last:0,time:0,drawn:0,
    down:null,at:'',bg:null,bgKey:'',sprite:null,fig:null,figKey:'',people:[],say:null,talkAt:0,ro:null};
  const pl=()=>plan(W.port);
  const now=()=>performance.now();

  /* ---- the stage ---- */
  function build(){
    const el=document.createElement('div');el.className='jl-stage-in';
    el.innerHTML=`<canvas class="jl-canvas" tabindex="0" role="img" aria-label="${tr('Trại tạm giữ: chạm vào một chỗ để đi tới')}"></canvas>`;
    W.el=el;W.cv=el.querySelector('canvas');W.c=W.cv.getContext('2d');
    W.cv.addEventListener('pointerdown',e=>{W.down={x:e.clientX,y:e.clientY,t:now()};});
    W.cv.addEventListener('pointerup',e=>{const d=W.down;W.down=null;if(!d||Math.hypot(e.clientX-d.x,e.clientY-d.y)>14||now()-d.t>800)return;tapAt(e.clientX,e.clientY);});
    W.cv.addEventListener('keydown',onKey);
    let sizing=0;W.ro=new ResizeObserver(()=>{cancelAnimationFrame(sizing);sizing=requestAnimationFrame(size);});W.ro.observe(el);
  }
  /** Put the stage into its slot (after jail.js built the dialog); the frames start. */
  function mount(slot){
    if(!slot)return;
    if(!W.el)build();
    if(W.el.parentNode!==slot){slot.prepend(W.el);size();}
    W.drawn=0;wake();
  }
  function size(){
    if(!W.el?.isConnected)return;
    const r=W.el.getBoundingClientRect(),cw=Math.max(1,r.width),ch=Math.max(1,r.height),was=W.port;
    W.port=portraitFor(cw,ch);W.dpr=Math.min(W.port?1.5:2,globalThis.devicePixelRatio||1);W.cw=cw;W.ch=ch;
    const w=Math.round(cw*W.dpr),h=Math.round(ch*W.dpr);if(W.cv.width!==w)W.cv.width=w;if(W.cv.height!==h)W.cv.height=h;
    if(W.me&&was!==W.port){   // the other composition: keep the player where they were on the floor
      const a=plan(was).floor,b=pl().floor,u=(W.me.x-a[0])/(a[2]-a[0]),v=(W.me.y-a[1])/(a[3]-a[1]);place([b[0]+u*(b[2]-b[0]),b[1]+v*(b[3]-b[1])]);
      W.people=[];
    }
    if(!W.me)place(pl().entry.bunk);   // a jail morning starts by the bunk
    if(!W.people.length)W.people=pl().walkers.map((w,i)=>({who:w.who,path:w.path,idle:!!w.idle,i:0,x:w.path[0][0],y:w.path[0][1],route:null,wait:1.5+i*2.2,step:0,face:1,say:null,sayAt:0}));
    W.cam=null;view(0);W.bgKey='';W.drawn=0;draw();wake();
  }
  function place(p){const q=nearestFree(pl(),p)||p;W.me={x:q[0],y:q[1],path:null,step:0,face:1};}
  /** Scale and offset (scenes/jail-place.js frame): the camera follows the player on a phone and keeps them above a
   * panel that spans the stage. */
  function view(dt){
    if(!W.cw)return;
    const box=panelBox(),wide=box&&!box.hidden&&box.offsetWidth>W.cw*.8,band=wide?Math.max(W.ch*.3,box.offsetTop-6):W.ch;
    const want=[W.me.x,W.me.y-(W.port?110:90)];
    if(!W.cam||still()||!dt)W.cam=want;else{const a=Math.min(1,dt*4);W.cam=[W.cam[0]+(want[0]-W.cam[0])*a,W.cam[1]+(want[1]-W.cam[1])*a];}
    const f=frame(W.port,W.cw,W.ch,W.cam,band);W.k=f.k;W.ox=f.ox;W.oy=f.oy;
  }
  const toScene=(cx,cy)=>{const r=W.cv.getBoundingClientRect();return [(cx-r.left-W.ox)/W.k,(cy-r.top-W.oy)/W.k];};

  /* ---- walking ---- */
  function walkTo(p,then=null){
    wake();W.then=then;
    const path=route(pl(),[W.me.x,W.me.y],p);
    if(!path||still()){const end=path?path[path.length-1]:[W.me.x,W.me.y];W.me.x=end[0];W.me.y=end[1];W.me.path=null;W.drawn=0;arrived();return;}
    W.me.path=path.slice(1);
  }
  function arrived(){const f=W.then;W.then=null;if(W.me)W.me.path=null;if(f)f();}
  function hitSpot(p){let best=null,bd=Infinity;for(const s of pl().spots){const d=Math.hypot(s.hit[0]-p[0],s.hit[1]-p[1]);if(d<=s.r&&d<bd){bd=d;best=s;}}return best;}
  function hitPerson(p){const s=W.port?.9:.74;return W.people.find(q=>Math.abs(q.x-p[0])<26*s*1.4&&p[1]<q.y+8&&p[1]>q.y-150*s)||null;}
  function tapAt(cx,cy){
    const p=toScene(cx,cy),who=hitPerson(p),spot=who?null:hitSpot(p);hush();
    if(who){talkTo(who);return;}
    if(spot){go(spot.id);return;}
    W.at='';leave();walkTo(p);
  }
  /** Walk up to a place and open it (also the chips under the stage, the keyboard, the tests). */
  function go(id){
    const s=pl().spots.find(q=>q.id===id);if(!s)return;
    hush();if(W.at!==id)leave();
    walkTo(s.stand,()=>{W.at=s.id;if(s.kind==='look')speak(s.line);else arrive(s);});
  }
  /** One of the camp's people: walk up beside them, they stop and say a line. */
  function talkTo(q){
    leave();W.at='';
    const side=W.me.x<=q.x?-46:46;
    walkTo([q.x+side,q.y+6],()=>{q.route=null;q.wait=Math.max(q.wait,3.5);q.face=W.me.x<q.x?-1:1;W.me.face=-q.face;
      const lines=PEOPLE[q.who].lines;q.n=(q.n??Math.floor(Math.random()*lines.length))+1;q.say=lines[q.n%lines.length];q.sayAt=W.time;W.drawn=0;wake();});
  }
  function onKey(e){
    const k={ArrowLeft:[-60,0],ArrowRight:[60,0],ArrowUp:[0,-40],ArrowDown:[0,40]}[e.key];
    if(k){e.preventDefault();hush();W.at='';leave();walkTo([W.me.x+k[0],W.me.y+k[1]]);return;}
    if(e.key==='Enter'||e.key===' '){
      let best=null,bd=70;for(const s of pl().spots){const d=Math.hypot(s.stand[0]-W.me.x,s.stand[1]-W.me.y);if(d<bd){bd=d;best=s;}}
      if(best){e.preventDefault();go(best.id);}
    }
  }
  /** The player's own line in a bubble (a look spot). */
  function speak(text){W.say={text:tr(text),at:W.time};W.drawn=0;wake();}
  function hush(){if(W.say){W.say=null;W.drawn=0;}}

  /* ---- the camp's people stroll between their points, stop, chat ---- */
  function people(dt){
    let moving=false;if(still())return false;
    for(const q of W.people){
      if(q.say&&W.time-q.sayAt>SAY_MS/1000){q.say=null;W.drawn=0;}
      if(q.route?.length){
        const [tx,ty]=q.route[0],dx=tx-q.x,dy=ty-q.y,d=Math.hypot(dx,dy),sp=NPC_SPEED*dt;moving=true;q.step+=dt*7;
        if(Math.abs(dx)>1)q.face=dx<0?-1:1;
        if(d<=sp){q.x=tx;q.y=ty;q.route.shift();if(!q.route.length){q.route=null;q.wait=q.idle?4+Math.random()*6:2+Math.random()*5;}}
        else{q.x+=dx/d*sp;q.y+=dy/d*sp;}
        continue;
      }
      q.wait-=dt;
      if(q.wait<=0){
        if(!q.say&&Math.random()<.45){const lines=PEOPLE[q.who].lines;q.say=lines[Math.floor(Math.random()*lines.length)];q.sayAt=W.time;q.wait=SAY_MS/1000+1;W.drawn=0;continue;}
        q.i=(q.i+1)%q.path.length;q.route=(route(pl(),[q.x,q.y],q.path[q.i])||[]).slice(1);if(!q.route.length)q.wait=3;
      }
    }
    return moving;
  }

  /* ---- frames ---- */
  function sleep(){cancelAnimationFrame(W.raf);clearTimeout(W.timer);W.raf=0;W.timer=0;}
  function wake(){clearTimeout(W.timer);W.timer=0;if(!W.raf&&W.el?.isConnected&&!document.hidden){W.last=now();W.raf=requestAnimationFrame(loop);}}
  document.addEventListener('visibilitychange',()=>{if(document.hidden)sleep();else{W.drawn=0;wake();}});
  RM?.addEventListener?.('change',()=>{W.drawn=0;W.bgKey='';wake();});
  function loop(t){
    W.raf=0;
    if(!W.el?.isConnected||document.hidden)return;
    const el=Math.max(0,(t-W.last)/1000),dt=Math.min(.05,el);W.last=t;W.time+=Math.min(.25,el);
    const m=W.me;let moving=people(dt);
    if(m?.path?.length){
      const sp=SPEED*dt,[tx,ty]=m.path[0],dx=tx-m.x,dy=ty-m.y,d=Math.hypot(dx,dy);moving=true;m.step+=dt*9;
      if(Math.abs(dx)>1)m.face=dx<0?-1:1;
      if(d<=sp){m.x=tx;m.y=ty;m.path.shift();if(!m.path.length)arrived();}else{m.x+=dx/d*sp;m.y+=dy/d*sp;}
    }
    if(W.say&&W.time-W.say.at>SAY_MS/1000){W.say=null;W.drawn=0;}
    const was=[W.ox,W.oy,W.k];view(dt);const panned=Math.abs(was[0]-W.ox)+Math.abs(was[1]-W.oy)+Math.abs(was[2]-W.k)*100>.5;
    if(moving||panned||!W.drawn||!still()&&t-W.drawn>=IDLE_MS){W.drawn=t||1;draw();}
    if(!W.el?.isConnected||document.hidden||W.raf||W.timer)return;
    if(moving||panned)W.raf=requestAnimationFrame(loop);
    else if(!still())W.timer=setTimeout(()=>{W.timer=0;W.raf=requestAnimationFrame(loop);},IDLE_MS);
  }
  /** What the yard shows today: the tasks of the day, the ones done, the leaf piles, the days left. */
  function opts(){
    const j=J()||{},tasks=j.tasks||[],sw=tasks.find(x=>x.id==='sweep');
    return {t:W.time,reduced:still(),today:tasks.map(x=>x.id),done:tasks.filter(x=>x.done).map(x=>x.id),piles:sw?.pz?.piles||[],
      ready:(j.ready||0)*1000<=Date.now()+(state().skew||0),left:j.left|0,port:W.port};
  }
  function backdrop(o){
    const key=[W.port,W.cv.width,W.cv.height,W.k.toFixed(4),W.ox.toFixed(1),W.oy.toFixed(1),o.done.join(),o.reduced,document.documentElement.lang].join('|');
    if(W.bg&&W.bgKey===key)return W.bg;
    const bg=W.bg||document.createElement('canvas');bg.width=W.cv.width;bg.height=W.cv.height;
    const c=bg.getContext('2d');c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,bg.width,bg.height);
    c.setTransform(W.dpr*W.k,0,0,W.dpr*W.k,W.dpr*W.ox,W.dpr*W.oy);
    try{paintBack(c,W.port,{...o,t:0,reduced:true});}catch(e){console.warn('jail map: backdrop',e);}
    W.bg=bg;W.bgKey=key;return bg;
  }
  function draw(){
    const c=W.c;if(!c||!W.cw||!W.me)return;
    const o=opts(),p=pl();
    c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,W.cv.width,W.cv.height);
    // a moving camera repaints the backdrop (it is cached per view): only on phones, while the camera glides
    c.drawImage(backdrop(o),0,0);
    c.setTransform(W.dpr*W.k,0,0,W.dpr*W.k,W.dpr*W.ox,W.dpr*W.oy);
    try{
      const f=p.floor,base=W.port?.9:.74,depth=y=>.9+.18*(y-f[1])/Math.max(1,f[3]-f[1]);
      const items=props(c,p,o);
      for(const q of W.people)items.push([q.y,()=>person(c,q,base*depth(q.y))]);
      items.push([W.me.y+.5,()=>drawMe(c,base*depth(W.me.y))]);
      items.sort((a,b)=>a[0]-b[0]);for(const [,fn] of items)fn();
      const near=p.spots.find(s=>W.at===s.id&&Math.hypot(W.me.x-s.stand[0],W.me.y-s.stand[1])<30);
      marks(c,p,o,near?.id||null);
      const [v0,,v1]=VIEW[W.port?'port':'land'],big=W.port?1.25:1;
      for(const q of W.people)if(q.say)bubble(c,q.x,q.y-152*base*depth(q.y),tr(q.say),{x0:v0,x1:v1,size:13*big});
      if(W.say)bubble(c,W.me.x,W.me.y-158*base*depth(W.me.y),W.say.text,{x0:v0,x1:v1,size:13*big});
    }catch(e){console.warn('jail map: draw',e);}
  }
  function person(c,q,s){
    const P=PEOPLE[q.who],walking=!!q.route?.length&&!still();
    c.save();if(walking)c.translate(0,-Math.abs(Math.sin(q.step))*2.4);
    folk(c,q.x,q.y,s,P.seed,{t:W.time,reduced:still()||walking,top:P.top,hair:P.guard?'#2f2a28':null});
    if(P.guard)cap(c,q.x,q.y,s);
    else{c.save();c.translate(q.x,q.y);c.scale(s,s);c.fillStyle='#ffffffa0';for(let i=0;i<3;i++)c.fillRect(-17,-70+i*12,34,4);c.restore();}   // the striped camp shirt
    c.restore();
  }
  /** My figure (the outfit I wear), painted once per look and scale into a sprite. */
  function drawMe(c,s){
    const m=W.me,st=state().api?.state;if(!st)return;
    c.save();c.translate(m.x,m.y);
    if(m.path?.length&&!still())c.translate(0,-Math.abs(Math.sin(m.step))*3);
    try{
      const key=JSON.stringify([lookOf(st),st.journey?.gender]);
      if(key!==W.figKey){W.figKey=key;W.fig=figure(st);W.sprite=null;}
      const px=Math.max(.1,W.dpr*W.k*s),sk=`${key}|${Math.round(px*100)}`;
      if(W.sprite?.key!==sk){
        const cv=document.createElement('canvas');cv.width=Math.ceil(110*px);cv.height=Math.ceil(160*px);
        const q=cv.getContext('2d');q.setTransform(px,0,0,px,55*px,150*px);paintPlayer(q,W.fig,CANVAS);W.sprite={key:sk,cv};
      }
      c.scale(s,s);c.drawImage(W.sprite.cv,-55,-150,110,160);
    }catch{/* look not ready */}
    c.restore();
  }
  /** Out of the camp (the dialog closed, released): no frames. */
  function off(){sleep();}
  /** After a state: the yard may have changed (a task done, a new day): one fresh frame. */
  function redraw(){W.drawn=0;wake();}

  /* ---- test hooks (scratch browser checks) ---- */
  globalThis.__jailMap={state:()=>({on:!!W.el?.isConnected,port:W.port,me:W.me&&[Math.round(W.me.x),Math.round(W.me.y)],walking:!!W.me?.path?.length,at:W.at,
    spots:pl().spots.map(s=>s.id),people:W.people.map(q=>({who:q.who,x:Math.round(q.x),y:Math.round(q.y),say:q.say||''})),view:{k:W.k,ox:W.ox,oy:W.oy,cw:W.cw,ch:W.ch}}),
    screen:id=>{const s=pl().spots.find(q=>q.id===id);if(!s||!W.cv)return null;const r=W.cv.getBoundingClientRect();return [r.left+W.ox+s.hit[0]*W.k,r.top+W.oy+s.hit[1]*W.k];},
    go,walk:(u,v)=>{const f=pl().floor;walkTo([f[0]+u*(f[2]-f[0]),f[1]+v*(f[3]-f[1])]);}};

  return {mount,go,off,redraw,size,still,at:()=>W.at,clearAt:()=>{W.at='';}};
}
