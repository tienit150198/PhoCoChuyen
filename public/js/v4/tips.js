/** Tip hên xui: a warm card when a customer leaves a tip or a thank-you gift (server: game/tips.py).
 *
 * The server writes today's tips to career.life.tip_day (one row per tipped task: emoji, head, line,
 * where, amount, kind cash|gift, to till|wallet|team, big). After each state update this module shows
 * the rows it has not seen yet, one card at a time, a moment after the job's own toast. Rows already
 * there when a career's state first arrives (a reload, another device) are not announced again.
 * tipSummary() is the "Tip hôm nay" block of the day summary (shift_summary.experiences.tip_day).
 * Render-only: every number and every word comes from the server. */
import {asset} from '../assets.js';

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const SHOW=5400,BIG_SHOW=7000,GAP=320,DELAY=550,MAX_QUEUE=3;

function card(r){
  const cls=['tip-pop',r.kind==='gift'?'gift':'cash',r.big?'big':'',r.to==='team'?'team':''].filter(Boolean).join(' ');
  const amt=r.kind==='cash'?`<strong class="tip-pop-amt">${r.to==='team'?'':'+'}${fmt(r.amount)}<span> xu</span></strong>`:'';
  return {cls,html:`<span class="tip-pop-emoji" aria-hidden="true">${esc(r.emoji)}</span>`
    +`<div class="tip-pop-body"><b class="tip-pop-head">${esc(r.head)}</b><span class="tip-pop-line">“${esc(r.line)}”</span>`
    +`<small class="tip-pop-where">${esc(r.where)}</small></div>${amt}`};
}

/** Where the card goes inside an open sheet, so it covers neither the sheet's header nor the controls of the screen.
 * Room under a centred sheet (tablet/desktop): the CSS spot there. A work screen with its button bar pinned (found
 * as guide.js finds it for its toasts): right above the bar and the note line on it (or just under a bar left halfway
 * up), as wide as the bar. Any other sheet: right above its footer, else at the bottom. Inside a sheet the card is
 * one compact line.
 * On the scene (phone): right above the task card. Measured while the card shows (a note comes or goes, the bar moves). */
function place(el,mount){
  if(!el.isConnected)return;
  if(mount===document.body){
    // The scene on a phone: right above the task card (its "Làm tiếp"), not over it.
    const hud=document.documentElement.dataset.layout==='phone'&&[...document.querySelectorAll('#taskHUD .note-card')].find(e=>e.getClientRects().length);
    const top=hud?hud.getBoundingClientRect().top:0;
    const v=top>120?`${Math.round(innerHeight-top+8)}px`:'';
    if(el.style.bottom!==v)el.style.bottom=v;
    return;
  }
  if(mount.id!=='sheet'||!mount.open)return;
  const H=innerHeight,h=el.offsetHeight||64,d=mount.getBoundingClientRect();
  const set=(top,bottom,{x='',w=''}={})=>{
    const at=n=>n==='css'?'':n==null?'auto':`${Math.round(n)}px`;   // 'css': the stylesheet's own spot
    const v={top:at(top),bottom:at(bottom),left:x,width:w};
    for(const [k,val] of Object.entries(v))if(el.style[k]!==val)el.style[k]=val;
  };
  if(H-d.bottom>=h+24){el.classList.remove('on-bar');set('css','css');return;}   // a centred sheet with room under it: the CSS spot, clear of the sheet
  const box=document.getElementById('toasts'),notes=box&&box.parentElement===mount?[...box.children].filter(t=>!t.classList.contains('leaving')).map(t=>t.getBoundingClientRect()).filter(r=>r.height):[];
  // The pinned bar that holds the work button, measured here (the sheet's data-gd-bar may be from before it was shown).
  const bar=barOf(mount),r=bar?.getBoundingClientRect();
  el.classList.add('on-bar');   // inside a sheet: always the short one-line card
  if(r&&r.height){
    const wide={x:`${Math.round(r.left+r.width/2)}px`,w:`min(${Math.round(r.width)-16}px,calc(100vw - 16px),640px)`};
    if(H-r.bottom>=72){const under=Math.max(r.bottom,...notes.map(n=>n.bottom));set(under+6,null,wide);}
    else{const over=Math.min(r.top,...notes.map(n=>n.top));set(null,H-over+6,wide);}
    return;
  }
  const foot=[...mount.querySelectorAll('.sheet-foot')].find(f=>f.getClientRects().length);
  const edge=Math.min(foot?foot.getBoundingClientRect().top:H-12,...notes.map(n=>n.top));
  set(null,H-edge+8);
}
/** The sticky/fixed bar around the sheet's main work button (as guide.js measures it), or null. */
function barOf(dialog){
  const cta=[...dialog.querySelectorAll('.gd-cta')].find(e=>e.getClientRects().length&&!e.closest('details:not([open])'));
  for(let e=cta;e&&e!==dialog;e=e.parentElement){const p=getComputedStyle(e).position;if(p==='sticky'||p==='fixed')return e;}
  return null;
}

export function tipsBoot({api,sound}){
  if(!document.querySelector('link[data-tips-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/tips.css');l.dataset.tipsCss='1';document.head.append(l);}
  const seen=new Map();   // career id -> Set of row keys already shown (or there before we looked)
  const queue=[];let busy=false;
  const key=r=>`${r.id}:${r.day}`;
  const reduced=()=>document.documentElement.classList.contains('reduce-motion')||matchMedia('(prefers-reduced-motion: reduce)').matches;

  function onState(){
    const st=api.state,id=st?.current,life=id&&st.careers?.[id]?.life;
    if(!life)return;
    const rows=Array.isArray(life.tip_day)?life.tip_day:[];   // no list yet: nobody has tipped here so far
    const known=seen.get(id);
    if(!known){seen.set(id,new Set(rows.map(key)));return;}
    for(const r of rows){
      const k=key(r);if(known.has(k))continue;known.add(k);
      if(queue.length<MAX_QUEUE)queue.push(r);
    }
    if(queue.length&&!busy){busy=true;setTimeout(next,DELAY);}
  }
  function next(){
    const r=queue.shift();if(!r){busy=false;return;}
    show(r,()=>setTimeout(next,GAP));
  }
  function show(r,done){
    const {cls,html}=card(r),el=document.createElement('div');
    el.className=cls;el.setAttribute('role','status');el.setAttribute('aria-live','polite');el.innerHTML=html;
    // Inside an open sheet the page underneath is inert: the card rides in the top layer, like the toasts.
    const mount=document.querySelector('#confirmDialog[open]')||document.querySelector('dialog[open]')||document.body;
    if(mount!==document.body)el.classList.add('in-dialog');
    mount.append(el);
    place(el,mount);el._place=setInterval(()=>place(el,mount),200);
    if(r.big){const s=api.state?.settings||{};if(s.sound!==false&&s.detailSfx!==false){try{sound.configure(s);sound.chime();}catch{/* silent */}}}
    let gone=false;
    const leave=()=>{if(gone)return;gone=true;el.classList.add('leaving');setTimeout(()=>{clearInterval(el._place);el.remove();done();},reduced()?0:320);};
    setTimeout(leave,r.big?BIG_SHOW:SHOW);
  }
  api.addEventListener('state',()=>{try{onState();}catch(error){console.warn('tips',error);}});
  return {show:r=>show(r,()=>{})};
}

/** Day summary: "Tip hôm nay" (null when nobody tipped). */
export function tipSummary(x){
  if(!x||!x.count)return '';
  const who=[x.tips?`${fmt(x.tips)} khách để lại tip`:'',x.gifts?`${fmt(x.gifts)} món quà cảm ơn`:''].filter(Boolean).join(' · ');
  const where=[x.till?`vào két ${fmt(x.till)} xu`:'',x.wallet?`về ví ${fmt(x.wallet)} xu`:'',x.team?`cả đội nhận ${fmt(x.team)} xu`:''].filter(Boolean).join(' · ');
  // The customer's words were on the tip card during the day: here only the sums (owner 03/10 "chữ ít thôi").
  return `<article class="notice tip-sum"><span class="tip-sum-ico" aria-hidden="true">💝</span><div class="grow">`
    +`<b>Tip hôm nay${x.cash?`: +${fmt(x.cash)} xu`:''}</b><p>${esc(who)}${where?` · ${esc(where)}`:''}</p></div></article>`;
}
