/** 🎆 Pháo hoa cả phố: the show every online player sees, on whatever screen they are (owner 08/10: "phải có bắn toàn
 * server cho mọi người thấy chứ k phải là chỉ có chữ nhé. Và có thông báo dài luôn").
 *
 * The live service (live/fireworks.py) sends `fireworks {id, size, name, wish, ago}` to every open page when someone
 * buys a show in Mua sắm → 🎆 Mạnh Thường Quân (game/lux.py); a page that connects just after gets it in its welcome
 * (`fw`). This draws bursts over the whole page on a canvas (pointer-events: none: play goes on underneath) and shows
 * a long banner at the top: who, which size, their wish (a fixed list, game/lux_content.py FW_WISHES), a ✕ and a
 * "🎆 Bắn pháo hoa" button that opens the shop on it (#274 "bắn pháo hoa chỗ nào z?"). Bigger sizes: more rockets,
 * longer, a finale; the banner stays 12 / 16 / 20 s. A blocked giver arrives without name and wish (the sky only).
 *
 * Top layer (popover="manual") so an open sheet does not hide it; older browsers: fixed with a very high z-index.
 * prefers-reduced-motion: a few slow blooms that fade in place, no rising rockets, no trails, no flash. Silent (no
 * recording fits; the game's audio must be CC0). Shows queue (at most QUEUE_MAX waiting), one id plays once per tab. */
import {escapeHTML as esc} from '../icons.js';

const SIZES={
  nho:{verb:'vừa bắn pháo hoa nhỏ mừng cả phố!',sky:'Pháo hoa nhỏ đang nở trên phố!',show:7,banner:12,rockets:9,sparks:30,r:.2,finale:0},
  lon:{verb:'vừa bắn pháo hoa lớn mừng cả phố!',sky:'Pháo hoa lớn đang nở trên phố!',show:11,banner:16,rockets:20,sparks:40,r:.27,finale:6},
  dai_tiec:{verb:'vừa mở đại tiệc pháo hoa mừng cả phố!',sky:'Đại tiệc pháo hoa trên phố!',show:17,banner:20,rockets:38,sparks:48,r:.32,finale:14},
};
/** Names the server writes for a guest or an anonymous giver: words to translate, not a player's name. */
const PLAIN_NAMES=new Set(['Một người hàng xóm','Một người hàng xóm giấu tên','Bạn']);
const COLORS=['#ff5d73','#ffd25e','#6fe3a8','#6ec8ff','#c792ff','#ff9f5a','#ffffff','#ff7ad9'];
const QUEUE_MAX=6,SPARK_MAX=1600,SEEN_KEY='mnl-fw-seen';
const S={env:null,cur:null,queue:[],seen:new Set()};
try{for(const k of JSON.parse(sessionStorage.getItem(SEEN_KEY)||'[]'))if(typeof k==='string')S.seen.add(k);}catch{/* storage blocked */}

const reduced=()=>{try{return matchMedia('(prefers-reduced-motion: reduce)').matches;}catch{return false;}};
const sizeOf=id=>SIZES[id]||SIZES.lon;
function remember(id){
  S.seen.add(id);
  try{sessionStorage.setItem(SEEN_KEY,JSON.stringify([...S.seen].slice(-8)));}catch{/* storage blocked */}
}

/** A `fireworks` frame (or a welcome's `fw`): play it now, or after the one on screen. */
export function onFireworks(env,f){
  S.env=env||S.env;
  if(!f||typeof f.id!=='string'||!f.id||S.seen.has(f.id)||S.cur?.f.id===f.id||S.queue.some(x=>x.id===f.id))return;
  const z=sizeOf(f.size),ago=Math.max(0,Number(f.ago)||0);
  if(ago>=z.banner-3)return;   // over already
  remember(f.id);
  if(S.cur){if(S.queue.length>=QUEUE_MAX)S.queue.shift();S.queue.push({...f,ago:0});return;}
  play({...f,ago});
}
/** The buyer's own page when the live socket is not open (no broadcast will come back to it). */
export function playLocal(env,size,wish=''){
  S.env=env||S.env;onFireworks(env,{id:`local-${Date.now()}`,size,name:'Bạn',wish,ago:0});
}

function css(){
  if(document.querySelector('style[data-fw-css]'))return;
  const s=document.createElement('style');s.dataset.fwCss='';
  s.textContent=`.fw-root{position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;padding:0;border:0;background:transparent;overflow:hidden;pointer-events:none;z-index:2147482000;color:inherit}
.fw-root::backdrop{display:none}
.fw-tint{position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,14,52,.86) 0%,rgba(22,18,70,.74) 42%,rgba(28,20,74,.38) 68%,rgba(28,20,74,0) 88%);opacity:0;transition:opacity .9s ease}
.fw-root.on .fw-tint{opacity:1}
.fw-root canvas{position:absolute;inset:0;width:100%;height:100%}
.fw-banner{position:absolute;left:50%;top:calc(env(safe-area-inset-top,0px) + 12px);transform:translate(-50%,-14px);opacity:0;transition:opacity .45s ease,transform .45s ease;
  width:min(520px,calc(100vw - 24px));box-sizing:border-box;display:flex;align-items:center;gap:10px;padding:10px 8px 10px 12px;border-radius:18px;pointer-events:auto;
  background:linear-gradient(135deg,#3b2468,#7a2f63 60%,#b5532f);color:#fff;box-shadow:0 10px 30px rgba(20,8,40,.45),inset 0 0 0 1px rgba(255,230,160,.35);
  font:600 15px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.fw-root.on .fw-banner{opacity:1;transform:translate(-50%,0)}
.fw-root.out .fw-banner{opacity:0;transform:translate(-50%,-14px)}
.fw-ico{font-size:30px;line-height:1;flex:none;animation:fw-pop 1.6s ease-in-out infinite}
.fw-text{flex:1;min-width:0}
.fw-text b{color:#ffe08a;font-weight:800;overflow-wrap:anywhere}
.fw-wish{display:block;margin-top:2px;font-weight:600;font-style:italic;color:#ffeccc}
.fw-go{display:inline-block;margin-top:6px;padding:5px 11px;border:0;border-radius:99px;background:#ffd25e;color:#4a2412;font-family:inherit;font-weight:700;font-size:13px;line-height:1.2;cursor:pointer}
.fw-x{flex:none;align-self:flex-start;width:32px;height:32px;border:0;border-radius:50%;background:rgba(255,255,255,.16);color:#fff;font:700 16px/32px system-ui,sans-serif;cursor:pointer;padding:0}
.fw-x:focus-visible,.fw-go:focus-visible{outline:2px solid #fff;outline-offset:2px}
.fw-bar{position:absolute;left:14px;right:14px;bottom:4px;height:3px;border-radius:2px;background:rgba(255,255,255,.22);overflow:hidden}
.fw-bar i{display:block;height:100%;background:#ffd25e;transform-origin:left;animation:fw-bar linear forwards}
.fw-big .fw-banner{font-size:16px;padding:12px 8px 13px 14px}
.fw-big .fw-ico{font-size:36px}
@keyframes fw-pop{0%,100%{transform:scale(1)}50%{transform:scale(1.18) rotate(-6deg)}}
@keyframes fw-bar{from{transform:scaleX(1)}to{transform:scaleX(0)}}
@media (prefers-reduced-motion:reduce){.fw-ico{animation:none}.fw-banner{transition:opacity .45s ease}}`;
  document.head.append(s);
}

/** What the giver may do next: the shop on fireworks (story mode only, where Mua sắm exists). */
const canShoot=()=>{const j=S.env?.api?.state?.journey;return Boolean(j?.story&&j.lux&&S.env?.act);};

function banner(f,z,secs){
  const name=String(f.name||'').trim(),wish=String(f.wish||'').trim();
  const who=name?(PLAIN_NAMES.has(name)?`<b>${esc(name)}</b>`:`<b data-no-translate>${esc(name)}</b>`):'';
  const line=name?`${who} <span>${esc(z.verb)}</span>`:`<span>${esc(z.sky)}</span>`;
  return `<div class="fw-banner" role="status" aria-live="polite"><span class="fw-ico" aria-hidden="true">🎆</span>
    <div class="fw-text"><div>${line}</div>${wish?`<q class="fw-wish">${esc(wish)}</q>`:''}${canShoot()&&f.name!=='Bạn'?'<button type="button" class="fw-go" data-fw="go">🎆 Bắn pháo hoa</button>':''}</div>
    <button type="button" class="fw-x" data-fw="x" aria-label="Đóng" title="Đóng">✕</button><span class="fw-bar" aria-hidden="true"><i style="animation-duration:${secs}s"></i></span></div>`;
}

function play(f){
  css();
  const z=sizeOf(f.size),calm=reduced(),ago=f.ago||0;
  const root=document.createElement('div');root.className='fw-root'+(f.size==='dai_tiec'?' fw-big':'');
  const bannerSecs=Math.max(5,z.banner-ago),showSecs=Math.max(3,z.show-ago);
  root.innerHTML=`<div class="fw-tint"></div><canvas aria-hidden="true"></canvas>${banner(f,z,bannerSecs)}`;
  document.body.append(root);
  if(typeof root.showPopover==='function'){try{root.popover='manual';root.showPopover();}catch{/* fixed + z-index */}}
  const cur=S.cur={f,root,raf:0,timers:[],done:false};
  root.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-fw]');if(!b)return;
    if(b.dataset.fw==='go'){finish(cur,true);S.env?.act?.('luxFw');}
    else finish(cur,true);
  });
  requestAnimationFrame(()=>root.classList.add('on'));
  sky(cur,root.querySelector('canvas'),z,showSecs,calm,ago);
  cur.timers.push(setTimeout(()=>root.querySelector('.fw-tint')?.style.setProperty('opacity','0'),showSecs*1000));
  cur.timers.push(setTimeout(()=>finish(cur,false),bannerSecs*1000));
}

function finish(cur,quick){
  if(cur.done)return;cur.done=true;
  for(const t of cur.timers)clearTimeout(t);
  cancelAnimationFrame(cur.raf);
  cur.root.classList.add('out');cur.root.querySelector('.fw-tint')?.style.setProperty('opacity','0');
  const cv=cur.root.querySelector('canvas');if(cv)cv.style.cssText+=';transition:opacity .4s;opacity:0';
  setTimeout(()=>{try{cur.root.hidePopover?.();}catch{/* not shown as one */}cur.root.remove();
    if(S.cur===cur)S.cur=null;
    const next=S.queue.shift();if(next)play(next);},quick?420:520);
}

/* ---- the sky ---- */
function plan(z,secs,calm,ago){
  // Rockets spread over the show (the last ~2.5 s left for the sparks to fall), a finale for the bigger sizes.
  const n=Math.max(2,Math.round(z.rockets*(calm?.35:1)*Math.min(1,secs/z.show))),span=Math.max(1,secs-2.6),out=[];
  for(let i=0;i<n;i++)out.push({t:(i+.3*Math.random())*span/n,kind:i%5===4?'willow':i%3===2?'ring':'peony'});
  const fin=calm?Math.ceil(z.finale/4):z.finale;
  if(fin&&secs>=z.show-1)for(let i=0;i<fin;i++)out.push({t:span-.9+Math.random()*.9,kind:i%2?'ring':'peony'});
  if(ago<.5&&!calm)out.unshift({t:.05,kind:'peony'});   // something right away
  return out.sort((a,b)=>a.t-b.t);
}

function sky(cur,cv,z,secs,calm,ago){
  const c=cv.getContext('2d');if(!c)return;
  const dpr=Math.min(1.5,window.devicePixelRatio||1);let W=0,H=0;
  const fit=()=>{W=window.innerWidth||360;H=window.innerHeight||640;cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);c.setTransform(dpr,0,0,dpr,0,0);c.lineCap='round';};
  fit();
  const rockets=plan(z,secs,calm,ago),sparks=[],flying=[];let next=0,start=0,last=0;
  const R=()=>Math.min(W,H*1.1)*z.r;
  // under the banner (it covers the top of a phone), never lower than the middle of the screen or so (the darker part)
  const top0=()=>{const b=cur.root.querySelector('.fw-banner');const r=b?.getBoundingClientRect?.();return r&&r.bottom>0?r.bottom:H*.08;};
  function burst(x,y,kind){
    const col=COLORS[(Math.random()*COLORS.length)|0],col2=COLORS[(Math.random()*COLORS.length)|0],n=calm?Math.round(z.sparks*.6):z.sparks,r=R()*(.75+Math.random()*.4);
    for(let i=0;i<n&&sparks.length<SPARK_MAX;i++){
      const a=i/n*Math.PI*2+Math.random()*.12,sp=(kind==='ring'?1:.35+Math.random()*.65)*r*(calm?.55:1);
      sparks.push({x,y,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp,life:0,max:(kind==='willow'?2.6:1.7)+Math.random()*.5,col:kind==='willow'?'#ffd77a':i%3===0?col2:col,w:kind==='willow'?1.8:2.6,
        drag:kind==='willow'?1.6:2.4,g:kind==='willow'?40:70});
    }
    if(!calm)sparks.push({x,y,vx:0,vy:0,life:0,max:.3,flash:R()*.42});
  }
  function frame(ts){
    if(cur.done)return;
    if(!start){start=ts;last=ts;}
    const t=(ts-start)/1000,dt=Math.min(.05,(ts-last)/1000);last=ts;
    if(W!==window.innerWidth||H!==window.innerHeight)fit();
    while(next<rockets.length&&rockets[next].t<=t){
      const k=rockets[next++],top=Math.min(H*.4,top0()+R()*.55),x=W*(.12+Math.random()*.76),y=top+Math.random()*Math.max(20,H*.56-top);
      if(calm)burst(x,y,k.kind);else flying.push({x,y0:H+10,y,tx:x+(Math.random()-.5)*30,age:0,dur:.75+Math.random()*.35,kind:k.kind});
    }
    // fade what was drawn (trails), keeping the page visible under it
    c.globalCompositeOperation='destination-out';c.fillStyle=calm?'rgba(0,0,0,1)':'rgba(0,0,0,.24)';c.fillRect(0,0,W,H);
    c.globalCompositeOperation='source-over';
    for(let i=flying.length-1;i>=0;i--){
      const r=flying[i];r.age+=dt;const p=Math.min(1,r.age/r.dur),e=1-(1-p)*(1-p),y=r.y0+(r.y-r.y0)*e,x=r.x+(r.tx-r.x)*(1-e);
      c.fillStyle='#fff3c4';c.globalAlpha=1;c.beginPath();c.arc(x,y,2.2,0,Math.PI*2);c.fill();
      c.fillStyle='rgba(255,200,120,.55)';c.fillRect(x-1,y+3,2,12);
      if(p>=1){flying.splice(i,1);burst(x,y,r.kind);}
    }
    for(let i=sparks.length-1;i>=0;i--){
      const s=sparks[i];s.life+=dt;if(s.life>=s.max){sparks.splice(i,1);continue;}
      const a=1-s.life/s.max;
      if(s.flash){const r=s.flash*(1.2-a*.5),g=c.createRadialGradient(s.x,s.y,0,s.x,s.y,r);g.addColorStop(0,'rgba(255,250,225,.9)');g.addColorStop(.35,'rgba(255,220,150,.35)');g.addColorStop(1,'rgba(255,200,120,0)');
        c.globalAlpha=a;c.fillStyle=g;c.fillRect(s.x-r,s.y-r,r*2,r*2);continue;}
      const k=Math.exp(-s.drag*dt);s.vx*=k;s.vy=s.vy*k+s.g*dt;s.x+=s.vx*dt;s.y+=s.vy*dt;
      c.globalAlpha=calm?Math.min(1,s.life*3)*a:a;
      if(calm){const w=s.w*1.6;c.fillStyle=s.col;c.fillRect(s.x-w/2,s.y-w/2,w,w);continue;}
      // a short streak along the motion, a bright head; the last moments twinkle
      c.strokeStyle=s.col;c.lineWidth=s.w*(.7+a*.9);c.beginPath();c.moveTo(s.x-s.vx*.045,s.y-s.vy*.045);c.lineTo(s.x,s.y);c.stroke();
      if(a<.35&&Math.random()<.5)continue;
      c.fillStyle=a>.6?'#fffbe8':s.col;const w=s.w*(1+a);c.fillRect(s.x-w/2,s.y-w/2,w,w);
    }
    c.globalAlpha=1;
    if(t<secs+.5||sparks.length||flying.length)cur.raf=requestAnimationFrame(frame);
    else c.clearRect(0,0,W,H);
  }
  cur.raf=requestAnimationFrame(frame);
}
