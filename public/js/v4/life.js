/** Chuyện đời thường & tình làng nghĩa xóm. A life card (hard day → the
 * neighbours come round → blow off steam) pops up at a calm moment: after the
 * day summary is closed, on the journey home, or right after opening a shift.
 * Also: the spirit meter card on the journey home, an entry in the wallet, the
 * "Đời thường" sheet (xả stress, neighbours, nhật ký) and a line in the day
 * summary. Markup only: every rule and number lives in game/life.py
 * (state.life = life.public()). Buttons use data-action="lf…" (lifeAction).
 * Design: docs/superpowers/specs/2026-09-29-life-design.md */
import {icon,escapeHTML as esc} from '../icons.js';
import {quiet} from './onboard.js';
import {portrait} from './look.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${extra}>${label}</button>`;
const xu=n=>`${n>0?'+':'−'}${fmt(Math.abs(n))} xu`;
const sp=n=>`tinh thần ${n>0?'+':n<0?'−':'±'}${Math.abs(n)}`;

let E=null;
const later=new Set();   // cards put off with "Để sau" (this session): stay in the home card, no auto-popup
const stateOf=env=>(env||E)?.api.state?.life;

/* ------------------------------------------------------------------ bits */
function effect(c){
  if(c.id==='self')return 'Tự chọn cách xả stress';
  const out=[];
  if(c.money)out.push(`<span class="${c.money<0?'out':'in'}">${xu(c.money)}</span>`);
  if(c.spirit)out.push(`<span class="${c.spirit<0?'out':'up'}">${sp(c.spirit)}</span>`);
  if(c.risky)out.push('<span class="risk">hên xui</span>');
  return out.join(' · ')||'Không tốn xu';
}
function choice(v,c){
  return `<button type="button" class="lf-choice ${c.emoji?'has-emoji':''}" data-action="lfChoose" data-id="${esc(v.id)}" data-choice="${esc(c.id)}"${c.ok?'':' disabled'}>${c.emoji?`<span class="lf-ch-emoji" aria-hidden="true">${c.emoji}</span>`:''}<span class="lf-ch-text"><b>${esc(c.label)}</b><small>${effect(c)}</small>${c.why?`<em>${icon('lock',12)} ${esc(c.why)}</em>`:''}</span></button>`;
}
export function meter(L,{small=false}={}){
  const v=Math.max(0,Math.min(100,L.spirit|0)),tone=v>=60?'good':v>=35?'mid':'low';
  return `<div class="lf-meter ${tone} ${small?'small':''}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}" aria-label="Tinh thần ${v} trên 100, ${esc(L.mood.label)}"><span class="lf-mood" aria-hidden="true">${L.mood.emoji}</span><div class="grow"><div class="lf-meter-row"><b>Tinh thần</b><span>${v}/100 · ${esc(L.mood.label)}</span></div><div class="lf-bar"><i style="width:${Math.max(3,v)}%"></i></div></div></div>`;
}
function say(p,lines){
  if(!p)return '';
  return `<div class="lf-say"><span class="lf-face" aria-hidden="true">${p.emoji}</span><div class="lf-bubble"><b>${esc(p.name)}</b>${lines.map(t=>`<p>${esc(t)}</p>`).join('')}</div></div>`;
}
function hitChips(v){
  const c=[];
  if(v.hit)c.push(`<span class="lf-chip out">${sp(v.hit)}</span>`);
  if(v.loss)c.push(`<span class="lf-chip out">Ví −${fmt(v.loss)} xu</span>`);
  if(v.kind==='joy'&&v.spirit)c.push(`<span class="lf-chip up">${sp(v.spirit)}</span>`);
  return c.length?`<div class="lf-chips">${c.join('')}</div>`:'';
}

/* ------------------------------------------------------------------ the card */
function stageBody(v,L){
  const st=v.stage,ch=v.choices.map(c=>choice(v,c)).join('');
  if(st==='comfort')return say(v.speaker,v.say||[])+`<div class="lf-choices">${ch}</div>`;
  if(st==='gop'){
    const g=v.gop||{};
    const box=g.gift?`<div class="lf-gift"><span aria-hidden="true">${g.gift.emoji}</span><div><b>${esc(g.gift.name)}</b><p>${esc(g.gift.text)}</p></div></div>`
      :`<ul class="lf-gop">${g.rows.map(r=>`<li><span aria-hidden="true">${r.emoji}</span><span class="grow">${esc(r.name)}</span><b>${fmt(r.amount)} xu</b></li>`).join('')}<li class="total"><span aria-hidden="true">🏮</span><span class="grow">Cả xóm góp</span><b>${fmt(g.total)} xu</b></li></ul>`;
    const news=v.kind==='hard'&&v.loss?`<p class="lf-note">Mất ${fmt(v.loss)} xu. Tin lan khắp hẻm…</p>`:'';
    return `${news}<h3 class="lf-h">Cả xóm góp tay</h3>${box}<div class="lf-choices">${ch}</div>`;
  }
  if(st==='cope')return `<h3 class="lf-h">Xả stress kiểu gì đây?</h3><div class="lf-choices grid">${ch}</div>`;
  if(st==='joy')return `<div class="lf-actions">${btn('Dễ thương ghê 💛','lfClose',{id:v.id},'primary big full')}</div>`;
  if(st==='done'){
    const net=[];
    if(v.spirit)net.push(`<span class="lf-chip ${v.spirit<0?'out':'up'}">Cả chuyện: ${sp(v.spirit)}</span>`);
    if(v.money)net.push(`<span class="lf-chip ${v.money<0?'out':'in'}">Ví ${xu(v.money)}</span>`);
    return `<ul class="lf-trail">${v.trail.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>${net.length?`<div class="lf-chips">${net.join('')}</div>`:''}${meter(L,{small:true})}
      <div class="lf-actions">${btn(v.who.length?'Cảm ơn mọi người 💛':'Xong','lfClose',{id:v.id},'primary big full')}</div>`;
  }
  const ask=st==='react'?'Bạn làm gì?':st==='ask'?'Bạn giúp thế nào?':st==='impulse'?'Giờ sao?':st==='dorm'?'Bạn tính sao?':'';
  return `${ask?`<h3 class="lf-h">${ask}</h3>`:''}<div class="lf-choices">${ch}</div>`;
}

/* 🛏️ A Ký túc xá moment (game/life.py kind 'dorm'): the roommates in the scene, drawn like the player's portrait. */
function mates(v){
  const rows=(v.who||[]).filter(w=>w.look);
  return rows.length?`<ul class="lf-mates" aria-label="Bạn cùng phòng">${rows.map(w=>`<li>${portrait(w.look,w.gender,40,w.name)}<span><b>${esc(w.name)}</b><small>${esc(w.role)}</small></span></li>`).join('')}</ul>`:'';
}
function sceneHTML(v,L){
  const quiet=v.stage==='done'||v.stage==='joy';
  const hero=v.stage==='react'||v.stage==='ask'||v.stage==='impulse'||v.stage==='sick'||v.stage==='joy'||v.stage==='dorm'||(v.kind==='scam'&&v.stage==='gop');
  const lines=hero?`<ul class="lf-lines">${v.lines.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>`:'';
  const p=hero&&(v.gossip||v.speaker);
  const who=v.kind==='dorm'?mates(v):p?`<p class="lf-gossip"><span aria-hidden="true">${p.emoji}</span> ${esc(p.name)} · <small>${esc(p.role)}</small></p>`:'';
  return `<article class="lf-card lf-cat-${esc(v.cat)} lf-st-${esc(v.stage)}">
    <header class="lf-top"><span class="lf-portrait" aria-hidden="true">${v.emoji}</span><div class="grow"><span class="eyebrow">${v.cat_emoji} ${esc(v.cat_label)}</span><h2 id="lfSceneTitle">${esc(v.title)}</h2></div>
      ${quiet?'':btn(icon('x',18),'lfLater',{id:v.id},'ghost small lf-later','aria-label="Để sau"')}</header>
    ${who}${lines}${hero?hitChips(v):''}${stageBody(v,L)}
    ${quiet||v.stage==='done'?'':`<div class="lf-foot">${meter(L,{small:true})}</div>`}
  </article>`;
}

function dialog(){
  let d=document.getElementById('lfScene');
  if(!d){d=document.createElement('dialog');d.id='lfScene';d.className='jr-scene lf-scene';d.setAttribute('aria-labelledby','lfSceneTitle');
    d.innerHTML='<div id="lfSceneBody"></div>';document.body.appendChild(d);
    d.addEventListener('cancel',e=>{e.preventDefault();putOff();});}
  return d;
}
function render(){
  const L=stateOf(),d=document.getElementById('lfScene');
  if(!d?.open)return;
  if(!L?.pending){d.close();return;}
  d.querySelector('#lfSceneBody').innerHTML=sceneHTML(L.pending,L);
}
export function openLife(){
  const L=stateOf();if(!L?.pending)return;
  const d=dialog();d.querySelector('#lfSceneBody').innerHTML=sceneHTML(L.pending,L);
  if(!d.open)d.showModal();
  d.querySelector('.lf-choice:not([disabled]),.btn.primary')?.focus({preventScroll:true});
}
function putOff(){
  const L=stateOf(),d=document.getElementById('lfScene');
  if(L?.pending)later.add(L.pending.id+':'+L.pending.stage);
  if(d?.open)d.close();
  if(E?.ui?.view==='home'&&document.getElementById('sheet')?.open)E.renderSheet?.(false);
}

/** A calm moment: no other dialog, no day summary on screen, no live decision in the shift. */
function calm(){
  const api=E?.api,S=api?.state;if(!S)return false;
  if(['jrScene','stScene','confirmDialog','lfScene'].some(id=>document.getElementById(id)?.open))return false;
  if(S.journey?.story&&!S.journey.intro)return false;
  if(quiet(S))return false;   // a brand-new player's first 3 customers: nothing pops up
  if(document.getElementById('sheet')?.open&&E.ui?.view!=='home')return false;
  const c=S.current&&S.careers?.[S.current];
  if(c&&!c.summary&&c.open){
    if((c.day_completed|0)>0)return false;
    if(c.incidents?.active||c.happen?.live||(c.event&&c.event.stage!=='resolved'))return false;
  }
  return true;
}
function maybeLife(){
  const L=stateOf();
  if(!L?.enabled||!L.pending)return;
  if(document.getElementById('lfScene')?.open){render();return;}
  if(later.has(L.pending.id+':'+L.pending.stage))return;
  if(!calm())return;
  openLife();
}

/* ------------------------------------------------------------------ journey home + wallet */
/** Compact card for the journey home: spirit, warmth, a pending story, xả stress. */
export function lifeCard(env){
  const L=stateOf(env);if(!L?.enabled)return '';
  const p=L.pending;
  const wait=p?`<button type="button" class="lf-waiting" data-action="lfOpen"><span aria-hidden="true">${p.emoji}</span><span class="grow"><small>${p.stage==='done'?'Chuyện hôm nay':'Có chuyện đang chờ bạn'}</small><b>${esc(p.title)}</b></span>${icon('arrow',15)}</button>`:'';
  return `<section class="jr-card lf-home" aria-label="Đời thường">
    ${meter(L)}
    <div class="lf-warm"><span aria-hidden="true">🏮</span><span class="grow">Tình làng nghĩa xóm</span><b>${L.warmth} · ${esc(L.warmth_name)}</b></div>
    ${wait}
    <div class="lf-home-actions">${btn('🎈 Xả stress','jrView',{view:'life'},'cream small')}${btn(icon('book',14)+' Nhật ký đời thường','jrView',{view:'life'},'ghost small')}</div>
  </section>`;
}
/** One row in the wallet sheet. */
export function lifeEntry(env){
  const L=stateOf(env);if(!L?.enabled)return '';
  return `<button type="button" class="jr-card lf-entry" data-action="jrView" data-view="life"><span class="lf-mood" aria-hidden="true">${L.mood.emoji}</span><span class="grow"><b>Tinh thần ${L.spirit}/100 · ${esc(L.mood.label)}</b><small>Xả stress · Hàng xóm · Nhật ký đời thường${L.pending?' · 💬 có chuyện chờ':''}</small></span>${icon('arrow',16)}</button>`;
}

function head(title){
  return `<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại hành trình">${icon('back',18)}</button><div class="grow"><span class="eyebrow">HÀNH TRÌNH</span><h2>${title}</h2></div></header>`;
}
/** The "Đời thường" sheet (journey view 'life'). */
export function lifeView(env){
  const L=stateOf(env);
  if(!L?.enabled)return head('Đời thường')+`<div class="sheet-body jr-body"><p class="muted">Chuyện đời thường có trong hành trình.</p></div>`;
  const p=L.pending;
  const wait=p?`<button type="button" class="lf-waiting" data-action="lfOpen"><span aria-hidden="true">${p.emoji}</span><span class="grow"><small>${p.stage==='done'?'Chuyện hôm nay':'Có chuyện đang chờ bạn'}</small><b>${esc(p.title)}</b></span>${icon('arrow',15)}</button>`:'';
  const cope=L.cope.map(c=>`<button type="button" class="lf-choice has-emoji" data-action="lfCope" data-choice="${esc(c.id)}"${c.ok?'':' disabled'}><span class="lf-ch-emoji" aria-hidden="true">${c.emoji}</span><span class="lf-ch-text"><b>${esc(c.label)}</b><small>${effect(c)}</small>${c.why?`<em>${esc(c.why)}</em>`:''}</span></button>`).join('');
  const bonds=L.bonds.map(b=>`<li><span class="lf-face sm" aria-hidden="true">${b.emoji}</span><span class="grow"><b>${esc(b.name)}</b><small>${esc(b.role)}</small></span><span class="lf-hearts" aria-label="Thân thiết ${b.bond} trên 100">${'❤️'.repeat(Math.max(1,Math.round(b.bond/20)))}${'🤍'.repeat(Math.max(0,5-Math.max(1,Math.round(b.bond/20))))}</span></li>`).join('');
  const log=L.log.map(r=>`<li><span aria-hidden="true">${r.emoji}</span><span class="grow"><b>${esc(r.title)}</b><small>Ngày sống ${fmt(r.day)}${r.who.length?` · ${r.who.map(w=>`${w.emoji} ${esc(w.name)}`).join(', ')}`:''}</small>${r.text?`<p>${esc(r.text)}</p>`:''}</span><span class="lf-log-num">${r.spirit?`<i class="${r.spirit<0?'out':'up'}">${r.spirit>0?'+':'−'}${Math.abs(r.spirit)}</i>`:''}${r.money?`<i class="${r.money<0?'out':'in'}">${xu(r.money)}</i>`:''}</span></li>`).join('')||'<li class="muted">Chưa có chuyện gì. Cứ sống, chuyện sẽ tới.</li>';
  return head('Đời thường')+`<div class="sheet-body jr-body lf-view">
    <section class="jr-card lf-home">${meter(L)}<div class="lf-warm"><span aria-hidden="true">🏮</span><span class="grow">Tình làng nghĩa xóm</span><b>${L.warmth} · ${esc(L.warmth_name)}</b></div>${wait}</section>
    <h3 class="jr-sub">Xả stress ${L.cope_used?'<small>· hôm nay xả rồi</small>':'<small>· mỗi ngày một lần</small>'}</h3><div class="lf-choices grid">${cope}</div>
    <h3 class="jr-sub">Hàng xóm</h3><ul class="lf-bonds">${bonds}</ul>
    <h3 class="jr-sub">Nhật ký đời thường</h3><ul class="lf-log">${log}</ul></div>`;
}

/** A line for the end-of-day summary (summary.life). */
export function lifeSummary(x){
  if(!x)return '';
  const d=x.delta|0;
  return `<div class="notice lf-sum"><span class="lf-mood" aria-hidden="true">${x.emoji}</span><div><b>Tinh thần ${x.spirit}/100 · ${esc(x.label)}${d?` <small class="${d<0?'out':'up'}">(${d>0?'+':'−'}${Math.abs(d)})</small>`:''}</b>${(x.notes||[]).map(n=>`<p>${esc(n)}</p>`).join('')}${x.pending?`<p>${x.pending.emoji} Có chuyện chờ bạn: <b>${esc(x.pending.title)}</b></p>`:''}</div></div>`;
}

/* ------------------------------------------------------------------ wiring */
export function lifeBoot(env){
  E=env;dialog();
  env.api.addEventListener('state',()=>setTimeout(maybeLife,90));
  document.getElementById('sheet')?.addEventListener('close',()=>setTimeout(maybeLife,260));
  setTimeout(maybeLife,700);
}

export async function lifeAction(action,data,el,env){
  if(!action?.startsWith('lf'))return false;
  E=E||env;
  const {cmd}=env;
  switch(action){
    case'lfOpen':later.clear();openLife();return true;
    case'lfLater':putOff();return true;
    case'lfChoose':{await cmd('lf_choose',{id:data.id,choice:data.choice},{quiet:true});render();return true;}
    case'lfClose':{const r=await cmd('lf_close',{id:data.id},{quiet:true});if(r){const d=document.getElementById('lfScene');if(d?.open)d.close();}return true;}
    case'lfCope':{const r=await cmd('lf_cope',{choice:data.choice});if(r)env.renderSheet?.(false);return true;}
  }
  return false;
}
