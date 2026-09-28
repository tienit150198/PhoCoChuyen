/** Truyện nghề: every workplace has its own little story (game/career_stories.py).
 * A due beat opens as a scene (own <dialog>, same frame and speech bubbles as
 * the journey scenes); the journey home lists each arc's progress. Markup only:
 * the server decides when a beat is due and what a choice does. Wired through
 * journey.js (boot, home card, `jrArc*` actions), so app.js stays untouched. */
import {icon,escapeHTML as esc} from '../icons.js';
import {avatar,emojiOf} from './journey.js';

let E=null;
let cur=null;              // {id, shown, answered:{reply,note,label}|null, keepsake}
const snoozed=new Set();   // due beats dismissed with Esc: they wait on the journey home

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const colour=v=>/^#[0-9a-f]{3,8}$/i.test(v||'')?v:'#c44b30';
const meta=cid=>E?.api.content.catalogue.find(m=>m.id===cid)||{id:cid,place:cid};
const still=()=>document.documentElement.classList.contains('reduce-motion')||E?.api.state?.settings?.reduceMotion||matchMedia('(prefers-reduced-motion: reduce)').matches;
const stories=()=>E?.api.state?.stories;
const dueOf=id=>(stories()?.due||[]).find(d=>d.id===id);

function dialog(){
  let d=document.getElementById('stScene');
  if(!d){
    d=document.createElement('dialog');d.id='stScene';d.className='jr-scene st-scene';d.setAttribute('aria-labelledby','stSceneTitle');
    d.innerHTML='<div id="stSceneBody"></div>';document.body.appendChild(d);
    d.addEventListener('cancel',e=>{e.preventDefault();dismiss();});
  }
  return d;
}

/* ------------------------------------------------------------------ scene */
function line(l,cls=''){
  const me=l.who==='me',g=E.api.state.journey?.gender;
  const face=me?`<span class="jr-face st-me-face" aria-hidden="true">${avatar(g,40)}</span>`:`<span class="jr-face" aria-hidden="true">${esc(l.emoji)}</span>`;
  return `<div class="jr-line st-line ${me?'me':''} ${cls}">${face}<div class="jr-bubble"><b>${esc(l.name)}</b><p>${esc(l.text)}</p></div></div>`;
}
const pips=(step,total)=>`<ol class="st-pips" aria-label="Đoạn ${step} trên ${total}">${Array.from({length:total},(_,i)=>`<li class="${i+1<step?'past':i+1===step?'now':''}"></li>`).join('')}</ol>`;
const keep=k=>k?`<div class="jr-award st-keep"><span aria-hidden="true">${esc(k.emoji)}</span><div><small>Kỷ vật của câu chuyện</small><b>${esc(k.name)}</b><small>${esc(k.desc||'')}</small></div></div>`:'';
const btn=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}>${label}</button>`;

function sceneHTML(d){
  const m=meta(d.career),lines=d.lines.slice(0,cur.shown),more=cur.shown<d.lines.length,a=cur.answered;
  let foot='';
  if(more)foot=`<div class="st-actions">${btn('Xem hết','jrArcAll',{},'ghost')}${btn(`Tiếp ${icon('arrow',15)}`,'jrArcNext',{},'primary')}</div>`;
  else if(d.choice&&!a)foot=`<div class="st-choice" role="group" aria-labelledby="stPrompt"><p id="stPrompt" class="st-prompt">${esc(d.choice.prompt)}</p>
    ${d.choice.options.map((o,i)=>`<button type="button" class="st-option ${i?'':'first'}" data-action="jrArcChoose" data-option="${esc(o.id)}"><span class="st-opt-key" aria-hidden="true">${i?'B':'A'}</span><span class="grow">${esc(o.label)}</span>${icon('arrow',15)}</button>`).join('')}</div>`;
  else{
    const reply=a?`${line({who:'me',name:E.api.state.name,text:a.label})}${a.reply.map(l=>line(l,'reply')).join('')}`:'';
    const note=a?.note?`<p class="st-note">${icon('heart',15)} ${esc(a.note)}</p>`:'';
    foot=`${reply?`<div class="jr-lines st-lines">${reply}</div>`:''}${note}${d.last?keep(d.keepsake||cur.keepsake):''}
      <div class="st-actions">${btn(d.last?'Khép lại câu chuyện':'Khép lại',a?'jrArcClose':'jrArcSeen',{},'primary big full')}</div>`;
  }
  return `<article class="st-card" style="--career:${colour(m.color)}">
    <header class="st-head"><span class="st-art" aria-hidden="true">${esc(d.emoji)}</span>
      <div class="st-head-text"><span class="eyebrow">${emojiOf(m)} ${esc(d.place)}</span><h2 id="stSceneTitle">${esc(d.title)}</h2>
        <p class="st-sub">Truyện nghề · ${esc(d.arc)} · ${d.step}/${d.total}</p>${pips(d.step,d.total)}</div>
      <button type="button" class="btn ghost small st-x" data-action="jrArcDismiss" aria-label="Để sau">${icon('x',18)}</button></header>
    <div class="st-body"><div class="jr-lines st-lines" aria-live="polite">${lines.map((l,i)=>line(l,i===cur.shown-1&&!still()?'fresh':'')).join('')}</div>${foot}</div></article>`;
}

function render(){
  const d=cur&&dueOf(cur.id);if(!d&&!cur?.answered)return close();
  const view=d||cur.view,box=dialog();
  box.querySelector('#stSceneBody').innerHTML=sceneHTML(view);
  if(!box.open)box.showModal();
  (box.querySelector('.st-option.first')||box.querySelector('.st-actions .btn.primary'))?.focus({preventScroll:true});
  const last=box.querySelector('.st-lines .st-line:last-of-type');
  if(last&&cur.shown>1)last.scrollIntoView({block:'nearest',behavior:still()?'auto':'smooth'});
}

function open(id){
  const d=dueOf(id);if(!d)return false;
  snoozed.delete(id);
  cur={id,shown:still()?d.lines.length:1,answered:null,view:d};
  render();return true;
}
function close(){
  const d=document.getElementById('stScene');cur=null;
  if(d?.open)d.close();
  setTimeout(maybeStory,160);
}
function dismiss(){if(cur&&!cur.answered)snoozed.add(cur.id);close();}

/** Called by the journey after its own scenes: show the next due beat, if any. */
export function maybeStory(){
  const st=stories();if(!st||!E)return;
  const J=E.api.state.journey;
  if(J?.story&&!J.intro)return;                     // the first-run intro comes first
  if(document.getElementById('stScene')?.open||document.getElementById('jrScene')?.open)return;
  if(J?.news?.length)return;                        // a chapter or title scene is about to open
  if(document.getElementById('confirmDialog')?.open){setTimeout(maybeStory,400);return;}
  // Only the workplace you are at tells its story; the others wait on the journey home.
  const here=st.due.find(d=>d.career===E.api.state.current&&!snoozed.has(d.id));
  if(here)open(here.id);
}

export function storiesBoot(env){E=env;dialog();}

export async function storiesAction(action,data,el,env){
  E=E||env;
  switch(action){
    case'jrArcOpen':if(!open(data.id))env.toast?.('Câu chuyện này đã khép lại rồi.');return true;
    case'jrArcNext':if(cur){cur.shown++;render();}return true;
    case'jrArcAll':if(cur){cur.shown=cur.view.lines.length;render();}return true;
    case'jrArcDismiss':dismiss();return true;
    case'jrArcClose':close();return true;
    case'jrArcSeen':{
      if(!cur)return true;const id=cur.id;el&&(el.disabled=true);
      const r=await env.cmd('st_seen',{id},{quiet:true});
      if(r){close();}else if(el)el.disabled=false;
      return true;}
    case'jrArcChoose':{
      if(!cur||cur.answered)return true;const id=cur.id,view=dueOf(id)||cur.view;
      document.querySelectorAll('#stScene .st-option').forEach(b=>b.disabled=true);
      const r=await env.cmd('st_choose',{id,option:data.option},{quiet:true});
      if(!r?.story){document.querySelectorAll('#stScene .st-option').forEach(b=>b.disabled=false);return true;}
      cur={...cur,view,shown:view.lines.length,keepsake:r.story.keepsake,answered:{label:r.story.label,reply:r.story.reply||[],note:r.story.note}};
      render();return true;}
  }
  return false;
}

/* ------------------------------------------------------------------ journey home card */
export function storiesCard(env){
  E=E||env;
  const st=env.api.state.stories;if(!st)return '';
  const careers=env.api.state.careers||{};
  const rows=st.arcs.filter(a=>careers[a.career]&&(careers[a.career].started||a.seen||a.pending));
  const done=st.arcs.filter(a=>a.done).length;
  const rank=a=>a.pending?0:a.done?2:1;
  rows.sort((a,b)=>rank(a)-rank(b)||b.seen-a.seen);
  const row=a=>{
    const m=meta(a.career),dots=Array.from({length:a.total},(_,i)=>`<i class="${i<a.seen?'on':''}"></i>`).join('');
    const lead=a.pending?`<p class="st-row-note due">✨ Có chuyện mới</p>`:a.done?`<p class="st-row-note done">${esc(a.keepsake?.emoji||'🎁')} ${esc(a.keepsake?.name||'')}</p>`:`<p class="st-row-note">${esc(a.hint||'')}</p>`;
    const past=a.beats.length?`<details class="st-past"><summary>Đã qua ${a.beats.length} đoạn</summary><ol>${a.beats.map(b=>`<li><span aria-hidden="true">${esc(b.emoji)}</span><span>${esc(b.title)}${b.pick?`<small>Bạn chọn: ${esc(b.pick)}</small>`:''}</span></li>`).join('')}</ol></details>`:'';
    const go=a.pending?btn(`Xem ${icon('arrow',13)}`,'jrArcOpen',{id:a.pending},'primary small'):'';
    return `<li class="st-row ${a.pending?'due':''} ${a.done?'done':''}" style="--career:${colour(m.color)}"><span class="jr-place-emoji" aria-hidden="true">${esc(a.emoji)}</span>
      <div class="st-row-text"><span class="eyebrow">${esc(m.place||m.short||a.career)}</span><h3>${esc(a.title)}</h3>
        <span class="st-dots" role="img" aria-label="${a.seen}/${a.total} đoạn">${dots}</span>${lead}${past}</div>${go}</li>`;
  };
  const body=rows.length?`<ul class="st-rows">${rows.map(row).join('')}</ul>`:`<p class="muted small st-empty">Làm việc ở một nơi, câu chuyện của nơi đó sẽ bắt đầu.</p>`;
  return `<section class="jr-card st-home" aria-labelledby="stHomeTitle"><div class="jr-sec-head"><h2 id="stHomeTitle">${icon('book',18)} Truyện nghề</h2><small>${fmt(done)}/${fmt(st.arcs.length)} trọn truyện</small></div>
    <p class="muted small st-lead">Mỗi nơi làm việc có một câu chuyện riêng, mở dần khi bạn làm ở đó.</p>${body}</section>`;
}
