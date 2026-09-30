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
    if(r.big){const s=api.state?.settings||{};if(s.sound!==false&&s.detailSfx!==false){try{sound.configure(s);sound.chime();}catch{/* silent */}}}
    let gone=false;
    const leave=()=>{if(gone)return;gone=true;el.classList.add('leaving');setTimeout(()=>{el.remove();done();},reduced()?0:320);};
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
  const best=x.best?`<p class="tip-sum-best"><span aria-hidden="true">${esc(x.best.emoji)}</span> ${esc(x.best.head)}: “${esc(x.best.line)}”</p>`:'';
  return `<article class="notice tip-sum"><span class="tip-sum-ico" aria-hidden="true">💝</span><div class="grow">`
    +`<b>Tip hôm nay${x.cash?`: +${fmt(x.cash)} xu`:''}</b><p>${esc(who)}${where?` · ${esc(where)}`:''}</p>${best}</div></article>`;
}
