/** 🧧 Lì xì (game/lixi.py, live/lixi.py; owner 16/10 "cho phép người ta phát lì xì và giật lì xì, tiền ngẫu nhiên, phát
 * ở trên màn hình hoặc chat gì đó nhé … có cả map cũ và mới nhé").
 *
 * On every open page, both interfaces (the old sheets and strolls, the new isometric town: this is plain DOM over
 * either), when someone gives a packet (live `lixi`, or the welcome's `lx` just after):
 *  - an open screen (no dialog, the 🗺️ home sheet with the old town map, a 🚶 stroll): red envelopes fall over the page
 *    for RAIN_S seconds with a banner (who, the wish, Giật, ✕). A tap on an envelope or on Giật grabs one.
 *  - anything else (a work task, a fair game, a menu) or ⚙️ 🎆 "Chỉ báo nhỏ"/"Tắt": a small chip with Giật, never in
 *    the way. Like the fireworks (v4/fireworks.js), the layers live in the topmost modal dialog (a tap reaches them),
 *    only the envelopes, the banner and the chip take taps, Escape closes the rain only.
 *  - the card in Cả phố (v4/lixi-cards.js, v4/chat.js) for the whole day, until the last envelope.
 * Grabbing is POST /api/lixi/grab: the server draws the amount; the reply carries the new state (the wallet moved).
 * Its own dialog (data-action="lixi", the 🧧 in Cả phố, the menu): the packets of the day, giving one (jr_lixi_give:
 * total, envelopes, a wish), and one packet's "ai giật được bao nhiêu" (🏆 Hên nhất once it is finished).
 * Rules and numbers are the server's (content.journey.lixi); this file only shows them. */
import {icon,escapeHTML as esc} from '../icons.js';
import {LX,upsert,update,grabbed,refresh,list,ranked,grabbable,openNow,cardHTML,onChange} from './lixi-cards.js';
import {fwMode,topModal,idleScreen} from './fireworks.js';
import {qtyBox,qtyVal,afterTap} from '../qty-input.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const RAIN_S=9,CHIP_S=10,QUEUE_MAX=4,ENV_MAX=14,LATE_S=60,MINE_MS=30000;
const TOTALS=[10000,50000,100000,500000,1000000,5000000,10000000];
const COUNTS=[5,10,20,50,100];
const S={env:null,dlg:null,view:'list',pk:null,detail:null,busy:false,flash:null,won:null,
  form:{total:100000,n:20,wish:'an_khang',text:''},cur:null,queue:[],chip:null,seen:new Set(),grabbing:new Set(),mine:null,listening:false};

const J=()=>S.env?.api?.state?.journey||{};
const CAT=()=>S.env?.api?.content?.journey?.lixi||null;
const reduced=()=>{
  try{if(document.documentElement?.classList?.contains('reduce-motion')||S.env?.api?.state?.settings?.reduceMotion)return true;}catch{/* no page */}
  try{return matchMedia('(prefers-reduced-motion: reduce)').matches;}catch{return false;}
};

/* ---- what to show (pure: tests/lixi_ui.mjs) ---- */
/** 'rain' | 'chip' | 'none': my own packet and a blocked giver's never rain; ⚙️ 🎆 Tắt / Chỉ báo nhỏ or a busy screen: the chip. */
export function howToShow({mode='on',busy=false,own=false,no=false,open=true}={}){
  if(!open||no)return 'none';
  if(own)return 'chip';
  return mode==='on'&&!busy?'rain':'chip';
}
/** An open screen: no dialog, the home sheet (the old town map), or a 🚶 stroll. */
export function rainHere(top,env=S.env){
  return idleScreen(top,env)||Boolean(top?.classList?.contains?.('walk-sheet'));
}
/** The falling envelopes: [{x %, delay s, dur s, rot deg, size px}], as many as there are envelopes left (≤ ENV_MAX). */
export function planRain(left,secs=RAIN_S,rnd=Math.random){
  const n=Math.max(3,Math.min(ENV_MAX,Number(left)||0)),out=[];
  for(let i=0;i<n;i++)out.push({x:Math.round(4+((i+rnd()*.8)/n)*88),delay:+(rnd()*Math.max(.5,secs-4.5)).toFixed(2),dur:+(3.6+rnd()*2.4).toFixed(2),
    rot:Math.round(-25+rnd()*50),size:Math.round(40+rnd()*16)});
  return out;
}
/** The give form: [ok, why] with the server's own rules (content.journey.lixi) and what the player has. */
export function giveWhy({total,n,have=0,debt=false},c){
  if(!c)return [false,'⏳'];
  if(!Number.isInteger(total)||total<c.min||total>c.max)return [false,`Tổng từ ${fmt(c.min)} đến ${fmt(c.max)} xu`];
  if(!Number.isInteger(n)||n<c.n_min||n>c.n_max)return [false,`Từ ${c.n_min} đến ${c.n_max} bao`];
  if(total<n*c.env_min)return [false,`Mỗi bao ít nhất ${fmt(c.env_min)} xu`];
  if(debt)return [false,'Ví đang nợ'];
  if(total>have)return [false,`Còn thiếu ${fmt(total-have)} xu`];
  return [true,''];
}

/* ---- live frames (app.js bootLive) ---- */
export function onLixi(env,f){
  S.env=env||S.env;
  if(S.mine&&Date.now()<S.mine.until&&S.mine.total===f?.total&&S.mine.n===f?.n){f={...f,own:true};S.mine=null;}
  const p=upsert(f);if(!p)return;
  if(Number(f.ago)<LATE_S)show(p);
}
export function onWelcome(env,list_){
  S.env=env||S.env;
  if(!Array.isArray(list_))return;
  let last=null;
  for(const f of list_){const p=upsert(f);if(p&&Number(f.ago)<LATE_S)last=p;}
  if(last)show(last);
}
export function onUpdate(env,f){
  S.env=env||S.env;
  const p=update(f);if(!p)return;
  if(S.cur?.p.id===p.id){if(!openNow(p))endRain(S.cur,true,'Hết bao rồi!');else banner(S.cur);}
  if(S.chip?.p.id===p.id&&!openNow(p))hideChip();
  if(S.dlg?.open)render();
}
/** The giver's own page: the next packet of this size coming back is theirs (no Giật on it). */
export function markMine(total,n){S.mine=total?{total,n,until:Date.now()+MINE_MS}:null;}

function show(p){
  if(!p||S.seen.has(p.id))return;
  S.seen.add(p.id);
  if(S.cur&&!S.cur.done){if(S.queue.length>=QUEUE_MAX)S.queue.shift();S.queue.push(p);return;}
  route(p);
}
function route(p){
  const top=topModal(),how=howToShow({mode:fwMode(),busy:!rainHere(top),own:p.own,no:p.no||LX.got.has(p.id),open:openNow(p)});
  if(how==='rain')rain(p,top);
  else if(how==='chip')chip(p);
  else next();
}
function next(){const p=S.queue.shift();if(p)route(LX.packets.get(p.id)||p);}

/* ---- the layers ---- */
function css(){
  if(document.querySelector('style[data-lxi-css]'))return;
  const s=document.createElement('style');s.dataset.lxiCss='';
  s.textContent=`.lxi-root{position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;padding:0;border:0;background:transparent;overflow:hidden;pointer-events:none;z-index:2147482002;color:inherit}
.lxi-root::backdrop,.lxi-chip::backdrop{display:none}
.lxi-env{position:absolute;top:-80px;pointer-events:auto;border:0;padding:0;background:none;cursor:pointer;line-height:1;filter:drop-shadow(0 4px 6px rgba(80,0,0,.35));animation:lxi-fall linear forwards;touch-action:manipulation}
.lxi-env span{display:block;transform:rotate(var(--r,0deg))}
.lxi-env.got{animation:none;opacity:0;transition:opacity .3s}
@keyframes lxi-fall{0%{transform:translateY(0)}100%{transform:translateY(calc(100vh + 120px))}}
.lxi-banner{position:absolute;left:50%;bottom:calc(env(safe-area-inset-bottom,0px) + 14px);transform:translate(-50%,14px);opacity:0;transition:opacity .4s ease,transform .4s ease;
  width:min(460px,calc(100vw - 24px));box-sizing:border-box;display:flex;align-items:center;gap:10px;padding:9px 8px 10px 12px;border-radius:18px;pointer-events:auto;
  background:linear-gradient(135deg,#a3121a,#d22f27 60%,#ec6a2c);color:#fff;box-shadow:0 10px 28px rgba(90,10,10,.45),inset 0 0 0 1px rgba(255,214,102,.5);
  font:600 14px/1.35 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.lxi-root.on .lxi-banner{opacity:1;transform:translate(-50%,0)}
.lxi-root.out .lxi-banner{opacity:0;transform:translate(-50%,14px)}
.lxi-ico{font-size:30px;line-height:1;flex:none}
.lxi-text{flex:1;min-width:0}
.lxi-text b{color:#ffe08a;overflow-wrap:anywhere}
.lxi-text q{display:block;font-style:italic;color:#fff1cf;overflow-wrap:anywhere}
.lxi-text small{display:block;opacity:.9}
.lxi-go{flex:none;min-width:70px;min-height:40px;border:0;border-radius:99px;background:#ffd25e;color:#7a1410;font:800 15px/1 system-ui,sans-serif;cursor:pointer;padding:8px 14px}
.lxi-x{flex:none;align-self:flex-start;width:32px;height:32px;border:0;border-radius:50%;background:rgba(255,255,255,.18);color:#fff;font:700 16px/32px system-ui,sans-serif;cursor:pointer;padding:0}
.lxi-go:focus-visible,.lxi-x:focus-visible,.lxi-env:focus-visible,.lxi-chip button:focus-visible{outline:2px solid #fff;outline-offset:2px}
.lxi-won{position:absolute;left:50%;top:38%;transform:translate(-50%,-50%) scale(.6);opacity:0;transition:transform .35s cubic-bezier(.2,1.6,.4,1),opacity .25s;pointer-events:none;
  background:#c8231e;color:#ffe08a;border-radius:20px;padding:16px 22px;text-align:center;font:800 26px/1.2 system-ui,sans-serif;box-shadow:0 12px 30px rgba(90,10,10,.5),inset 0 0 0 2px #ffd25e}
.lxi-won small{display:block;font:600 13px/1.3 system-ui,sans-serif;color:#fff}
.lxi-won.on{opacity:1;transform:translate(-50%,-50%) scale(1)}
.lxi-chip{position:fixed;inset:auto;left:calc(env(safe-area-inset-left,0px) + 10px);bottom:calc(env(safe-area-inset-bottom,0px) + 12px);top:auto;right:auto;margin:0;z-index:2147482003;
  box-sizing:border-box;max-width:min(380px,calc(100vw - 20px));display:flex;align-items:center;gap:6px;padding:4px 4px 4px 10px;border:0;border-radius:99px;overflow:hidden;
  background:rgba(168,20,26,.95);color:#fff;box-shadow:0 4px 14px rgba(90,10,10,.35);font:600 13px/1.3 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;pointer-events:auto;
  opacity:0;transform:translateY(8px);transition:opacity .3s ease,transform .3s ease}
.lxi-chip.on{opacity:1;transform:none}
.lxi-chip-t{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lxi-chip-t b{color:#ffe08a}
.lxi-chip button{flex:none;border:0;border-radius:99px;font:800 12px/1 system-ui,sans-serif;cursor:pointer;padding:7px 11px;background:#ffd25e;color:#7a1410}
.lxi-chip .lxi-chip-x{width:26px;height:26px;padding:0;background:rgba(255,255,255,.18);color:#fff}
.lxi-sheet .lxi-big{font-size:28px;font-weight:800;color:#c8231e;text-align:center;margin:6px 0 2px}
.lxi-sheet .lxi-sub{text-align:center;margin:0 0 8px;color:var(--muted,#666);font-size:13px}
.lxi-sheet .lxi-grabs{list-style:none;margin:0;padding:0}
.lxi-sheet .lxi-grabs li{display:flex;align-items:center;gap:8px;padding:7px 4px;border-bottom:1px solid rgba(0,0,0,.07)}
.lxi-sheet .lxi-grabs li.me{background:rgba(255,210,94,.18);border-radius:8px}
.lxi-sheet .lxi-grabs b{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lxi-sheet .lxi-grabs em{font-style:normal;font-weight:800}
.lxi-sheet .lxi-best{font-size:12px;color:#a86b00;font-weight:700;white-space:nowrap}
.lxi-sheet .lxi-field{display:flex;align-items:center;gap:8px;margin:8px 0}
.lxi-sheet .lxi-field>span{min-width:76px;font-weight:600}
.lxi-sheet .lxi-field input[type=text]:not(.qty-in){flex:1;min-width:0}
.lxi-sheet .lxc{width:100%}
@media (prefers-reduced-motion:reduce){.lxi-banner{transition:opacity .4s ease}.lxi-chip{transition:opacity .3s ease;transform:none}.lxi-won{transition:opacity .25s}}`;
  document.head.append(s);
}
function mount(el,host){
  host.append(el);
  if(typeof el.showPopover==='function'){try{el.popover='manual';el.showPopover();}catch{/* fixed + z-index */}}
}
function unmount(el){try{el.hidePopover?.();}catch{/* not one */}el.remove();}
function own(el){for(const t of ['click','pointerdown','pointerup','mousedown','touchstart','touchend'])el.addEventListener(t,e=>e.stopPropagation());}
const who=p=>p.name?`<b data-no-translate>${esc(p.name)}</b>`:'<b>Một người hàng xóm</b>';

function rain(p,top){
  css();
  const root=document.createElement('div');root.className='lxi-root';
  const calm=reduced(),drops=calm?[]:planRain(p.left);
  root.innerHTML=drops.map((d,i)=>`<button type="button" class="lxi-env" data-lxi="grab" data-i="${i}" aria-label="Giật lì xì" style="left:${d.x}%;font-size:${d.size}px;animation-duration:${d.dur}s;animation-delay:${d.delay}s;--r:${d.rot}deg"><span aria-hidden="true">🧧</span></button>`).join('')+
    '<div class="lxi-banner" role="status" aria-live="polite"></div><div class="lxi-won" aria-live="polite"></div>';
  const host=top||document.body;mount(root,host);own(root);
  const cur=S.cur={p,root,host,top,done:false,timers:[],keys:null,watch:0};
  banner(cur);
  root.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-lxi]');if(!b)return;
    const what=b.dataset.lxi;
    if(what==='x'){endRain(cur,true);return;}
    if(what==='see'){endRain(cur,true);openLixi(S.env,'detail',p.id);return;}
    if(what==='grab'){if(b.classList?.contains('lxi-env'))b.classList.add('got');grab(p.id,cur);}
  });
  cur.keys=e=>{if((e.key==='Escape'||e.key==='Esc')&&!cur.done){e.preventDefault();e.stopPropagation();endRain(cur,true);}};
  document.addEventListener('keydown',cur.keys,true);
  requestAnimationFrame(()=>root.classList.add('on'));
  cur.timers.push(setTimeout(()=>endRain(cur,false),(RAIN_S+(calm?3:0))*1000));
  cur.watch=setInterval(()=>{   // the player opens a game or a sheet: the rain gives way (the chat card stays)
    if(cur.done)return;
    if(!cur.root.isConnected){endRain(cur,true);return;}
    const t=topModal();if(t!==cur.top&&!rainHere(t))endRain(cur,true);
  },400);
}
function banner(cur){
  const p=LX.packets.get(cur.p.id)||cur.p,el=cur.root.querySelector('.lxi-banner');if(!el)return;
  const got=LX.got.get(p.id),open=openNow(p);
  const act=got!=null?`<button type="button" class="lxi-go" data-lxi="see">+${fmt(got)} xu</button>`:open&&!p.own?'<button type="button" class="lxi-go" data-lxi="grab">Giật</button>':
    '<button type="button" class="lxi-go" data-lxi="see">Xem</button>';
  el.innerHTML=`<span class="lxi-ico" aria-hidden="true">🧧</span><div class="lxi-text"><div>${p.own?'<b>Bạn</b>':who(p)} <span>phát lì xì ${fmt(p.total)} xu</span></div>`+
    `${p.wish?`<q data-no-translate>${esc(p.wish)}</q>`:''}<small>${open?`Còn ${p.left}/${p.n} bao`:'Đã hết bao'}</small></div>${act}`+
    '<button type="button" class="lxi-x" data-lxi="x" aria-label="Đóng" title="Đóng">✕</button>';
}
function endRain(cur,quick,line=''){
  if(!cur||cur.done)return;cur.done=true;
  for(const t of cur.timers)clearTimeout(t);clearInterval(cur.watch);
  if(cur.keys)document.removeEventListener('keydown',cur.keys,true);
  if(line){const s=cur.root.querySelector('.lxi-text small');if(s)s.textContent=line;}
  cur.root.classList.add('out');
  for(const b of cur.root.querySelectorAll?.('.lxi-env')||[])b.classList.add('got');
  if(S.cur===cur)S.cur=null;
  setTimeout(()=>{unmount(cur.root);if(!S.cur)next();},quick?380:520);
}
function chip(p){
  css();hideChip();
  if(globalThis.document?.fullscreenElement)return next();
  const el=document.createElement('div');el.className='lxi-chip';el.setAttribute('role','status');el.setAttribute('aria-live','polite');
  el.innerHTML=`<span aria-hidden="true">🧧</span><span class="lxi-chip-t">${p.own?'<b>Bạn</b>':who(p)} <span>phát lì xì</span></span>`+
    (p.own?'<button type="button" data-lxi="see">Xem</button>':'<button type="button" data-lxi="grab">Giật</button>')+
    '<button type="button" class="lxi-chip-x" data-lxi="x" aria-label="Đóng" title="Đóng">✕</button>';
  own(el);
  const c=S.chip={el,p,timer:0};
  el.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-lxi]');if(!b)return;
    hideChip(c);
    if(b.dataset.lxi==='grab')grab(p.id);
    else if(b.dataset.lxi==='see')openLixi(S.env,'detail',p.id);
  });
  mount(el,topModal()||document.body);
  requestAnimationFrame(()=>el.classList.add('on'));
  c.timer=setTimeout(()=>hideChip(c),CHIP_S*1000);
}
function hideChip(c=S.chip){
  if(!c)return;clearTimeout(c.timer);
  if(S.chip===c){S.chip=null;setTimeout(()=>{if(!S.chip&&!S.cur)next();},340);}
  c.el.classList.remove('on');setTimeout(()=>unmount(c.el),320);
}

/* ---- grabbing ---- */
/** A card's button in Cả phố or the dialog: Giật, or Xem (who got how much). */
export function cardTap(env,id,what){
  S.env=env||S.env;
  if(what==='grab')return grab(id);
  return openLixi(S.env,'detail',id);
}
export async function grab(id,cur=null){
  const api=S.env?.api;if(!api||S.grabbing.has(id))return null;
  if(LX.got.has(id)){openLixi(S.env,'detail',id);return null;}
  S.grabbing.add(id);
  try{
    const r=await api.post('/api/lixi/grab',{id});
    if(r?.state&&typeof r.revision==='number')api.accept({state:r.state,revision:r.revision});
    grabbed(id,r.amount);
    const p=LX.packets.get(id);
    if(cur&&!cur.done){
      const w=cur.root.querySelector('.lxi-won');
      if(w){w.innerHTML=`+${fmt(r.amount)} xu<small>${p?.name?`lì xì của <b data-no-translate>${esc(p.name)}</b>`:'lì xì'}</small>`;w.classList.add('on');}
      banner(cur);
      cur.timers.push(setTimeout(()=>endRain(cur,false),2200));
    }else if(S.dlg?.open){S.won={id,amount:r.amount};S.view='detail';S.pk=id;loadDetail(id);}
    else if(rainHere(topModal())){S.won={id,amount:r.amount};openLixi(S.env,'detail',id);}
    else S.env?.toast?.(r.message||`🧧 +${fmt(r.amount)} xu`,'good');
    return r;
  }catch(e){
    if(e?.data?.code==='empty'||e?.code==='empty'){const p=LX.packets.get(id);if(p){p.left=0;p.status='done';update({id,left:0,done:true});}}
    const msg=e?.message||'Chưa giật được. Thử lại nhé.';
    if(cur&&!cur.done){const s=cur.root.querySelector('.lxi-text small');if(s)s.textContent=msg;cur.timers.push(setTimeout(()=>endRain(cur,false),1800));}
    else if(S.dlg?.open){S.flash={text:msg,kind:'bad'};render();}
    else S.env?.toast?.(msg,true);
    return null;
  }finally{S.grabbing.delete(id);}
}

/* ---- the dialog ---- */
let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=link('/css/spend.css','sd-css');

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet lxi-sheet';d.setAttribute('aria-labelledby','lxi-title');
  d.innerHTML='<div class="sd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-lxd]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.lxd,el.dataset);
  });
  d.addEventListener('change',e=>{
    const t=e.target;
    if(t.name==='total'){const n=qtyVal(t);if(n)S.form.total=n;afterTap(render);}
    else if(t.name==='n'){const n=qtyVal(t);if(n)S.form.n=n;afterTap(render);}
    else if(t.name==='wtext'){S.form.text=String(t.value||'').slice(0,CAT()?.text_max||40);}
  });
  d.addEventListener('input',e=>{if(e.target.name==='wtext')S.form.text=String(e.target.value||'').slice(0,CAT()?.text_max||40);});
  d.addEventListener('close',()=>{S.flash=null;S.won=null;});
  S.dlg=d;return d;
}
export async function openLixi(env,view='list',pk=null){
  S.env=env||S.env;
  if(!S.listening){S.listening=true;onChange(()=>{if(S.dlg?.open&&S.view==='list')render();});
    env.api?.addEventListener?.('state',()=>{if(S.dlg?.open&&S.view==='give'&&!S.busy)render();});}
  await ensureCss();css();
  const d=dialog();
  S.view=['list','give','detail'].includes(view)?view:'list';S.pk=pk||S.pk;
  if(S.view!=='detail')S.won=null;
  S.flash=null;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  refresh(S.env.api,S.view==='list'?0:15000);
  if(S.view==='detail'&&S.pk)loadDetail(S.pk);
}
async function loadDetail(pk){
  S.detail={id:pk,loading:true};render();
  try{
    const d=await S.env.api.json(`/api/lixi?id=${encodeURIComponent(pk)}`);
    for(const p of d?.packets||[])upsert(p,true);
    LX.me=d?.me||LX.me;
    S.detail=d?.packet?{...d.packet}:{id:pk,missing:true};
    if(d?.packet)upsert({...d.packet,grabs:undefined},true);
  }catch{S.detail={id:pk,error:true};}
  if(S.dlg?.open)render();
}
async function onClick(op,data){
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.view=data.tab;S.flash=null;S.won=null;if(S.view==='list')refresh(S.env.api,0);break;
    case'card':if(data.do==='grab'){await grab(data.id);return;}S.view='detail';S.pk=data.id;S.won=null;loadDetail(data.id);return;
    case'total':S.form.total=Number(data.n)||S.form.total;break;
    case'n':S.form.n=Number(data.n)||S.form.n;break;
    case'wish':S.form.wish=data.id;break;
    case'give':await give();return;
    case'back':S.view='list';S.won=null;break;
  }
  render();
}
function have(){const j=J();return Math.max(0,Number(j.wallet)||0)+Math.max(0,Number(j.bank?.balance)||0);}
async function give(){
  const c=CAT(),f=S.form,[ok,why]=giveWhy({total:f.total,n:f.n,have:have(),debt:(J().wallet||0)<0},c);
  if(!ok){S.flash={text:why,kind:'bad'};render();return;}
  const p={total:f.total,n:f.n,confirm:true};
  if(f.wish)p.wish=f.wish;
  const text=String(f.text||'').trim();if(text)p.text=text;
  S.busy=true;render();
  markMine(f.total,f.n);
  try{
    const r=await S.env.api.command('jr_lixi_give',p);
    S.flash={text:r?.message||'🧧 Đã phát!',kind:'good'};S.form.text='';
    S.view='list';refresh(S.env.api,0);
  }catch(e){markMine(null);S.flash=e?.quiet?null:{text:e?.message||'Chưa phát được. Thử lại nhé.',kind:'bad'};}
  finally{S.busy=false;render();}
}

function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.sd-body'),y=body?.scrollTop;
  S.dlg.querySelector('.sd-root').innerHTML=page();
  if(y)S.dlg.querySelector('.sd-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function page(){
  const c=CAT(),j=J();
  const head=`<header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">🧧</span><div class="grow"><h2 id="lxi-title">Lì xì</h2></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,j.wallet||0))}</span><button class="icon-btn" type="button" data-lxd="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  if(!c)return head+'<div class="sheet-body sd-body"><p class="sd-empty">⏳</p></div>';
  if(!j.story)return head+'<div class="sheet-body sd-body"><p class="sd-empty">Chỉ có trong hành trình.</p></div>';
  const tabs=`<nav class="sd-tabs" role="tablist" aria-label="Lì xì">${[['list','🧧','Đang phát'],['give','🎁','Phát lì xì']].map(([id,e,l])=>
    `<button type="button" role="tab" aria-selected="${S.view===id}" class="${S.view===id?'on':''}" data-lxd="tab" data-tab="${id}">${e} ${esc(l)}</button>`).join('')}</nav>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  if(S.view==='give'){
    const [ok,why]=giveWhy({total:S.form.total,n:S.form.n,have:have(),debt:(j.wallet||0)<0},c);
    const bar=`<footer class="sd-bar">${why?`<small class="sd-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big sd-main" data-lxd="give"${S.busy||!ok?' disabled':''}>🧧 Phát ${fmt(S.form.total)} xu · ${S.form.n} bao</button></footer>`;
    return head+tabs+`<div class="sheet-body sd-body">${flash}${giveForm(c)}</div>`+bar;
  }
  if(S.view==='detail')return head+tabs+`<div class="sheet-body sd-body">${flash}${detailView()}</div>`;
  return head+tabs+`<div class="sheet-body sd-body">${flash}${listView(c)}</div>`;
}
function listView(c){
  const me=LX.me,day=Number(j_day());
  const mine=me&&me.n?`<p class="lxi-sub">Hôm nay bạn đã giật ${fmt(me.n)}${c.grab_day?`/${c.grab_day}`:''} bao · ${fmt(me.xu)}${c.grab_day_xu?`/${fmt(c.grab_day_xu)}`:''} xu</p>`:'';
  const why=me&&!me.can?`<p class="lxi-sub">⚠ ${esc(me.why)}</p>`:day&&day<c.life_days?`<p class="lxi-sub">⚠ Giật lì xì mở từ ngày sống ${c.life_days}</p>`:'';
  const all=ranked(),n=all.filter(grabbable).length;
  const cards=all.map(p=>cardHTML(p,'data-lxd="card"')).join('');
  const wait=n&&!why?`<p class="lxi-sub lxi-wait">🧧 <b>${n}</b> bao đang chờ bạn giật</p>`:'';
  return mine+why+wait+(cards||`<div class="sd-empty"><p>Chưa ai phát lì xì hôm nay.</p><button type="button" class="btn primary" data-lxd="tab" data-tab="give">🧧 Phát lì xì đầu tiên</button></div>`);
}
const j_day=()=>J().life_day||0;
function giveForm(c){
  const f=S.form;
  const totals=`<div class="sd-chips sd-amounts">${TOTALS.filter(n=>n>=c.min&&n<=c.max).map(n=>`<button type="button" class="sd-chip${f.total===n?' on':''}" data-lxd="total" data-n="${n}" aria-pressed="${f.total===n}">${n>=1e6?`${n/1e6} triệu`:`${n/1000}k`}</button>`).join('')}</div>`;
  const counts=`<div class="sd-chips">${COUNTS.filter(n=>n>=c.n_min&&n<=c.n_max).map(n=>`<button type="button" class="sd-chip${f.n===n?' on':''}" data-lxd="n" data-n="${n}" aria-pressed="${f.n===n}">${n} bao</button>`).join('')}</div>`;
  const wishes=`<div class="sd-chips">${c.wishes.map(w=>`<button type="button" class="sd-chip${f.wish===w.id?' on':''}" data-lxd="wish" data-id="${esc(w.id)}" aria-pressed="${f.wish===w.id}">${esc(w.text)}</button>`).join('')}</div>`;
  const avg=f.n>0?Math.floor(f.total/f.n):0;
  return `<section class="sd-card"><h3>💰 Tổng tiền</h3>${totals}<label class="lxi-field"><span>Số khác</span>${qtyBox({value:f.total,min:c.min,max:c.max,money:true,label:'Tổng tiền lì xì',attrs:'name="total"'})}<small>xu</small></label></section>`+
    `<section class="sd-card"><h3>🧧 Số bao</h3>${counts}<label class="lxi-field"><span>Số khác</span>${qtyBox({value:f.n,min:c.n_min,max:c.n_max,label:'Số bao',attrs:'name="n"'})}<small>bao</small></label>`+
    `<p class="lxi-sub">Mỗi bao ngẫu nhiên, trung bình ~${fmt(avg)} xu. Ai nhanh tay người đó được!</p></section>`+
    `<section class="sd-card"><h3>💬 Lời chúc</h3>${wishes}<label class="lxi-field"><span>Lời riêng</span><input type="text" name="wtext" maxlength="${c.text_max}" value="${esc(f.text)}" placeholder="Không bắt buộc" autocomplete="off" data-no-translate></label></section>`+
    `<p class="lxi-sub">Hết ${c.hours} giờ, bao chưa ai giật sẽ về lại ví bạn.</p>`;
}
function detailView(){
  const d=S.detail&&S.detail.id===S.pk?S.detail:null;
  const back='<button type="button" class="btn ghost small" data-lxd="back">← Danh sách</button>';
  if(!d||d.loading)return back+'<p class="sd-empty">⏳</p>';
  if(d.error||d.missing)return back+`<p class="sd-empty">${d.error?'Chưa tải được. Thử lại nhé.':'Không thấy bao lì xì này.'}</p>`;
  const p=LX.packets.get(d.id)||d,won=S.won?.id===d.id?S.won.amount:LX.got.get(d.id);
  const top=won!=null?`<p class="lxi-big">+${fmt(won)} xu</p><p class="lxi-sub">Bạn giật được từ lì xì của ${d.name?`<b data-no-translate>${esc(d.name)}</b>`:'một người hàng xóm'}</p>`:'';
  const rows=(d.grabs||[]).map(g=>`<li class="${g.me?'me':''}"><span aria-hidden="true">🧧</span><b data-no-translate>${esc(g.name||'Một người hàng xóm')}</b>${g.best?'<span class="lxi-best">🏆 Hên nhất</span>':''}<em>${fmt(g.amount)} xu</em></li>`).join('');
  const left=openNow(p)?`Còn ${p.left}/${d.n} bao`:d.status==='expired'&&d.back>0?`Đã hết giờ · ${fmt(d.back)} xu về lại người phát`:'Đã giật hết';
  return back+top+cardHTML({...p,...d,left:p.left},'data-lxd="card"')+
    `<section class="sd-card"><h3>Ai giật được bao nhiêu</h3><p class="lxi-sub">${esc(left)} · đã giật ${fmt(d.taken||0)}/${fmt(d.total)} xu</p>`+
    (rows?`<ol class="lxi-grabs">${rows}</ol>`:'<p class="sd-empty">Chưa ai giật.</p>')+'</section>';
}
