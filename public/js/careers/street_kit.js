/** Shared pieces of the three street trades' work screens: the fruit stall (fruit.js), the rubbish
 * round (garbage.js) and drain cleaning (drain.js). The intro card, the surprise card, a tap-to-open
 * line, the day bar and the sticky next-step bar. Layout lives in public/css/careers/street_kit.css;
 * each career draws its own stations and keeps its own look in public/css/careers/<id>.css. */
import {stepCta} from '../v4/guide.js';

export const DONE=['completed','cancelled','referred'];
export const data=x=>x.room.data||{};
export const cc=x=>x.cc||{};
export const lower=s=>s?s[0].toLowerCase()+s.slice(1):'';
export const stockOf=(x,k)=>Number(x.room.inventory?.stock?.[k]||0);
export const pct=(v,max)=>Math.max(0,Math.min(100,v/Math.max(1,max)*100)).toFixed(1);
/** A button for a client action of the career module (data-action="car:<name>"). */
export const act=(x,label,action,d={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
/** A big square button that sends one server command. */
export const tile=(x,command,payload,inner,cls='',disabled=false)=>`<button type="button" class="tile sk-tile ${cls}" data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${inner}</button>`;
export const meter=(v,max,cls='')=>`<span class="sk-meter ${cls}"><i style="width:${pct(v,max)}%"></i></span>`;

/** One line that a tap opens; remembered per key in x.ui.pane. The body is drawn only while open. */
export function pane(x,key,summary,body,auto=false,cls=''){
  const open=(x.ui.pane??={})[key]??auto;
  return `<div class="sk-pane ${cls}${open?' open':''}"><button type="button" class="sk-pane-sum" data-action="car:pane" data-key="${x.esc(key)}" data-open="${open?1:0}" aria-expanded="${open}">${summary}</button>${open?`<div class="sk-pane-body">${body}</div>`:''}</div>`;
}

/** The "what this job is" card: shown until the player starts (`go` = the career's intro command). */
export function introCard(x,go,icon){
  const d=data(x),i=cc(x).intro;if(!i||(d.intro&&!x.ui.intro))return '';
  const list=(title,rows)=>`<section><h4>${x.esc(title)}</h4><ul class="sk-icons">${rows.map(([e,s])=>`<li><span aria-hidden="true">${x.esc(e)}</span>${x.esc(s)}</li>`).join('')}</ul></section>`;
  const btn=d.intro?act(x,'Đã hiểu','introClose',{},'primary full'):x.cmd(`${icon} Vào việc thôi!`,go,{},'primary full sk-intro-go');
  return `<article class="sk-intro card" role="dialog" aria-labelledby="sk-intro-title"><h3 id="sk-intro-title">${icon} ${x.esc(i.title)}</h3><p>${x.esc(i.lead)}</p>
    <div class="sk-intro-grid">${list('Công việc gồm…',i.work)}${list('Bạn sẽ gặp…',i.meet)}${list('Được khen khi…',i.stars)}</div>${btn}</article>`;
}

/** A surprise waiting for a decision, or the last one's outcome (dismissable). */
export function deskCard(x,cmd,where='Chuyện giữa ca'){
  const desk=data(x).desk;if(!desk)return '';
  const ev=desk.ev;
  if(ev){
    const opts=ev.options.map(o=>{
      const poor=o.cost>(Number(x.room.money)||0);
      const inner=`<span class="sk-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}${o.cost?`<em>−${x.fmt(o.cost)} xu${poor?' · chưa đủ tiền':''}</em>`:''}`;
      return x.cmd(inner,cmd,{option:o.id},'sk-opt',poor);
    }).join('');
    return `<section class="sk-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="sk-ev-title"><div class="sk-ev-head"><span aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>${x.esc(where)}</small><h3 id="sk-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="sk-opts">${opts}</div></section>`;
  }
  const last=desk.last,key=last?`${last.script}-${last.choice}-${last.day}-${(desk.log||[]).length}`:'';
  if(last&&last.day===x.room.day&&x.ui.seen!==key)
    return `<div class="sk-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji)}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p>${act(x,'✕','seen',{key},'ghost small sk-x',' aria-label="Đã đọc"')}</div>`;
  return '';
}

/** The day's weather/mood line (tap for the hint) and the "?" that reopens the intro. */
export function dayBar(x,tail=''){
  const m=data(x).mod||{};
  const sum=`<span class="sk-sky" aria-hidden="true">${x.esc(m.emoji||'🌤️')}</span><b>${x.esc(m.label||'')}${tail}</b>`;
  return `<div class="sk-day">${m.hint?pane(x,`day-${x.room.day}`,sum,`<small>${x.esc(m.hint)}</small>`,false,'grow'):`<div class="grow sk-day-line">${sum}</div>`}
    ${act(x,'❔','intro',{},'ghost small sk-help',' aria-label="Giới thiệu nghề"')}</div>`;
}

/** The customer on the card: portrait, name, one line and the patience bar. */
export function person(x,t,inner='',tag=''){
  const who=x.npc(t.npc);
  return `<article class="card sk-ticket"><div class="row">${x.portrait(who,48)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3>${tag}</div>
    <p class="small"><b>${x.esc(t.title)}</b></p>${inner}
    <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div></article>`;
}
/** Before the first question: who is here and the one button to ask. */
export function askCard(x,t,label){
  const who=x.npc(t.npc);
  return `<article class="card sk-ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>${x.esc(t.opening)}</p></div></div>${x.cmd(label,'ask',{task:t.id},'primary full sk-ask')}</article>`;
}

/** The sticky bottom bar: the next step, or the finishing button. */
export function bottom(x,g){
  if(!g.final)return g.steps.length?`<div class="sk-bar">${stepCta(x,g.steps,{label:'',go:null,ready:false})}</div>`:'';
  return `<div class="sk-bar">${stepCta(x,g.steps,g.final)}</div>`;
}

/** Client actions every street trade uses; spread into the module's `actions`. */
export const kitActions={
  async seen(d,el,x){x.ui.seen=d.key;x.render();},
  async pane(d,el,x){(x.ui.pane??={})[d.key]=d.open!=='1';x.render();},
  async intro(d,el,x){x.ui.intro=true;x.render();},
  async introClose(d,el,x){x.ui.intro=false;x.render();},
};
