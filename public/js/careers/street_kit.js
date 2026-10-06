/** Shared pieces of the three street trades' work screens: the fruit stall (fruit.js), the rubbish
 * round (garbage.js) and drain cleaning (drain.js). The intro card, the surprise card, a tap-to-open
 * line, the day bar and the sticky next-step bar. Layout lives in public/css/careers/street_kit.css;
 * each career draws its own stations and keeps its own look in public/css/careers/<id>.css. */
import {barParts} from '../v4/guide.js';
import {actBar,helpBtn,whyAttrs,clean,tip,headChip,few} from '../ui-kit.js';
export {tip,clean,headChip,few};

export const DONE=['completed','cancelled','referred'];
export const data=x=>x.room.data||{};
export const cc=x=>x.cc||{};
export const lower=s=>s?s[0].toLowerCase()+s.slice(1):'';
export const stockOf=(x,k)=>Number(x.room.inventory?.stock?.[k]||0);
export const pct=(v,max)=>Math.max(0,Math.min(100,v/Math.max(1,max)*100)).toFixed(1);
/** A button for a client action of the career module (data-action="car:<name>"). */
export const act=(x,label,action,d={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
/** A big square button that sends one server command. `can`: the server's pre-check for it (true | {why, fix}):
 * when it cannot go, the tile is dimmed but tappable and a tap says why (ui-kit whyAttrs). */
export const tile=(x,command,payload,inner,cls='',disabled=false,can=true)=>{const why=disabled?'':whyAttrs(can);
  return `<button type="button" class="tile sk-tile ${cls}${why?' is-why':''}" data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"${disabled?' disabled':''}${why}>${inner}</button>`;};
export const meter=(v,max,cls='')=>`<span class="sk-meter ${cls}"><i style="width:${pct(v,max)}%"></i></span>`;

/** One line that a tap opens; remembered per key in x.ui.pane. The body is drawn only while open. */
export function pane(x,key,summary,body,auto=false,cls=''){
  const open=(x.ui.pane??={})[key]??auto;
  return `<div class="sk-pane ${cls}${open?' open':''}"><button type="button" class="sk-pane-sum" data-action="car:pane" data-key="${x.esc(key)}" data-open="${open?1:0}" aria-expanded="${open}">${summary}</button>${open?`<div class="sk-pane-body">${body}</div>`:''}</div>`;
}

/** A career's notebook as a page of its own (app.js view 'carPage'): what its dock entry (Bảng nội quy, Sổ tay nhà)
 * opens from the scene, the bar or Thêm, where the work sheet and its pane are not on screen. `cls`: the career's
 * work-screen classes, so the list keeps its look. */
export function notesPage(x,{cls,eyebrow,title,body}){
  return `<header class="sheet-head"><div class="grow"><span class="eyebrow">${x.esc(eyebrow)}</span><h2>${title}</h2></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${x.icon('x',21)}</button></header>`+
    `<div class="sheet-body"><div class="career-job sk ${cls} sk-notes-page">${body}</div></div>`+
    `<footer class="sheet-foot"><p></p><div class="row wrap"><button type="button" class="btn ghost" data-action="close">Đóng</button><button type="button" class="btn primary" data-action="workbench">Vào việc</button></div></footer>`;
}

/** A long line cut to its first clause, ≤ `max` words: "Sáng: giặt khăn, châm đầy các chai" → "Giặt khăn". */
export function shortLine(s,max=5){
  let t=String(s||'').replace(/^[^:]{1,14}:\s*/,'');   // a "Sáng:" / "Chiều:" label
  t=t.split(/[,;(—–]|\s-\s/)[0].trim().split(/\s+/).slice(0,max).join(' ');
  return t?t[0].toUpperCase()+t.slice(1):'';
}
/** The intro's long parts (lead and the three lists) as "?" sheet sections. */
export function introHelp(x,i){
  const list=rows=>`<ul class="ui-rows">${(rows||[]).map(([e,s])=>`<li><span aria-hidden="true">${x.esc(e)}</span>${x.esc(s)}</li>`).join('')}</ul>`;
  return [{title:'Giới thiệu',body:`<p>${x.esc(i.lead||'')}</p>`,open:true},{title:'Công việc gồm…',body:list(i.work)},{title:'Bạn sẽ gặp…',body:list(i.meet)},{title:'Được khen khi…',body:list(i.stars)}];
}
/** The "what this job is" card: shown until the player starts (`go` = the career's intro command).
 * Short (≤ 30 words): the job's name, three icon rows of ≤ 5 words (intro.short, or the first three work lines cut
 * to their first clause) and a "?" with the lead and the three lists. The start button is the bar's main button
 * (the guide's intro step); the card keeps its own only as a fallback for a screen without that bar. */
export function introCard(x,go,icon){
  const d=data(x),i=cc(x).intro;if(!i||(d.intro&&!x.ui.intro))return '';
  const name=String(i.title||'').replace(/^Giới thiệu nghề:?\s*/,'')||String(i.title||'');
  const rows=(i.short||(i.work||[]).slice(0,3).map(([e,s])=>[e,shortLine(s)])).slice(0,3);
  const btn=d.intro?act(x,'Đã hiểu','introClose',{},'full'):x.cmd(`${icon} Vào việc thôi!`,go,{},'primary full sk-intro-go');
  const q=helpBtn(`intro-${x.state?.current||go}`,`${icon} ${name}`,introHelp(x,i),{label:'?',cls:'sk-intro-q'});
  return `<article class="sk-intro sk-intro-short card" role="dialog" aria-labelledby="sk-intro-title"><div class="sk-intro-head"><h3 id="sk-intro-title"><span aria-hidden="true">${icon}</span> ${x.esc(name.charAt(0).toUpperCase()+name.slice(1))}</h3>${q}</div>
    <ul class="sk-icons sk-intro-rows">${rows.map(([e,s])=>`<li><span aria-hidden="true">${x.esc(e)}</span>${x.esc(s)}</li>`).join('')}</ul>${btn}</article>`;
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

/** The day's weather/mood line (tap for the hint) and the "?". Classic layout: "?" reopens the intro card. Clean
 * layout: "?" opens the help sheet with what this screen folded away (ui-kit tip), the day's hint and the intro. */
export function dayBar(x,tail=''){
  const m=data(x).mod||{},i=cc(x).intro;
  const sum=`<span class="sk-sky" aria-hidden="true">${x.esc(m.emoji||'🌤️')}</span><b>${x.esc(m.label||'')}${tail}</b>`;
  const q=clean()&&i?helpBtn(`day-${x.state?.current||''}`,`${m.emoji||'❔'} ${String(i.title||'').replace(/^Giới thiệu nghề:?\s*/,'')}`,
    [...(m.hint?[{title:`${m.emoji||''} ${m.label||'Hôm nay'}`,body:`<p>${x.esc(m.hint)}</p>`}]:[]),...introHelp(x,i)],{tips:true,cls:'sk-help'})
    :act(x,'❔','intro',{},'ghost small sk-help',' aria-label="Giới thiệu nghề"');
  const line=clean()?`<div class="grow sk-day-line">${sum}</div>`:m.hint?pane(x,`day-${x.room.day}`,sum,`<small>${x.esc(m.hint)}</small>`,false,'grow'):`<div class="grow sk-day-line">${sum}</div>`;
  return `<div class="sk-day">${line}${clean()?'<span class="ui-chiprow"></span>':''}${q}</div>`;
}

/** The customer on the card: portrait, name, one line and the patience bar. */
export function person(x,t,inner='',tag=''){
  const who=x.npc(t.npc);
  return `<article class="card sk-ticket"><div class="row">${x.portrait(who,48)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3>${tag}</div>
    ${clean()&&(t.kind==='setup'||few(t.title,4,true)===String(t.title||'').trim())?'':`<p class="small"><b>${x.esc(t.title)}</b></p>`}${inner}
    <div class="patience" title="Kiên nhẫn"><div class="bar ${t.patience<50?'low':''}"><i style="width:${t.patience}%"></i></div><small>${t.patience}%</small></div></div></div></article>`;
}
/** Before the first question: who is here and the one button to ask. */
export function askCard(x,t,label){
  const who=x.npc(t.npc);
  return `<article class="card sk-ticket"><div class="row">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p>${x.esc(t.opening)}</p></div></div>${x.cmd(label,'ask',{task:t.id},'primary full sk-ask')}</article>`;
}

/** The sticky bottom bar (ui-kit actBar): the next step on the left, the one main button on the right.
 * g.final.can: the server's pre-check for the finishing action (dimmed with its reason when it cannot go).
 * `top`: an optional full-width row above (pho's pour gauge). */
export function bottom(x,g,{top=''}={}){
  if(!g.final&&!g.steps.length&&!top)return '';
  const {next,main}=barParts(x,g.steps,g.final||{label:'',go:null,ready:false});
  return actBar({next,main,top,cls:'sk-bar'});
}

/** Client actions every street trade uses; spread into the module's `actions`. */
export const kitActions={
  async seen(d,el,x){x.ui.seen=d.key;x.render();},
  async pane(d,el,x){(x.ui.pane??={})[d.key]=d.open!=='1';x.render();},
  async intro(d,el,x){x.ui.intro=true;x.render();},
  async introClose(d,el,x){x.ui.intro=false;x.render();},
};

/* ------------------------------------------------------------ the player's own move (0.9.16) */
const amtOf=(x,key,def)=>{const v=(x.ui.amt??={})[key];return v===undefined||v===''?def:Number(v);};
/** A number the player sets (− / typed / +) and one button that sends it: a price, a deposit, a fee. */
export function amountBox(x,key,def,{min=1,max=500,step=1,label='',send='Gửi',cmd,payload={},field='price',unit='xu'}={}){
  const v=Math.max(min,Math.min(max,amtOf(x,key,def)));
  const d=(n)=>act(x,n<0?'−':'+','amtStep',{key,delta:n*step,min,max,def},'ghost sk-step',` aria-label="${n<0?'Bớt':'Thêm'} ${step} ${unit}"`);
  return `<div class="sk-amt">${label?`<span class="sk-amt-label">${x.esc(label)}</span>`:''}<div class="sk-amt-row">${d(-1)}<label class="sk-amt-in"><input type="number" inputmode="numeric" min="${min}" max="${max}" value="${v}" data-sk-amt="${x.esc(key)}" aria-label="${x.esc(label||'Số tiền')}"><small>${x.esc(unit)}</small></label>${d(1)}</div>
    ${act(x,send,'amtSend',{key,def,cmd,field,extra:JSON.stringify(payload)},'primary sk-amt-go')}</div>`;
}
/** Keeps a typed amount (call from the module's input hook). */
export function kitInput(el,x){
  const key=el.dataset?.skAmt;if(!key)return false;
  (x.ui.amt??={})[key]=el.value===''?'':Math.floor(Number(el.value)||0);
  return true;
}
/** A card where someone is in your face: their words, and the ways to answer (and an amount box). */
export function choiceCard(x,cls,emoji,title,line,opts,extra=''){
  const btn=o=>x.cmd(`<span class="sk-opt-label">${o.label}</span>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}`,o.cmd,o.payload,`sk-opt ${o.cls||''}`,!!o.dis);
  return `<section class="sk-event tense sk-twist ${cls}" role="group"><div class="sk-ev-head"><span aria-hidden="true">${emoji}</span><div><small>${x.esc(title)}</small>${line?`<h3>${x.esc(line)}</h3>`:''}</div></div>
    <div class="sk-opts">${opts.map(btn).join('')}</div>${extra}</section>`;
}
/** The debt book: who owes what; chase (nhẹ / thẳng / người nhà, and how much now) or write off. */
export function debtBook(x,debts,cmd){
  const open=(debts||[]).filter(d=>d.state==='open');
  if(!(debts||[]).length)return '';
  const rows=open.map(d=>{const owe=d.owed-d.paid,today=d.on===x.room.day&&d.tries>0;
    const tone=(t,l)=>act(x,l,'debtChase',{debt:d.id,tone:t,key:`debt-${d.id}`,def:owe,cmd},'small');
    return `<li class="sk-debt"><div class="row spread"><b>${x.esc(d.who)}</b><span class="tag amber">${x.fmt(owe)} xu</span></div>
      <small class="muted">${x.esc(d.what)} · ngày ${d.day}${d.tries?` · đã đòi ${d.tries} lần`:''}</small>${d.last?`<p class="small">${x.esc(d.last)}</p>`:''}
      ${today?'<p class="small muted">Hôm nay đòi rồi, mai đòi tiếp.</p>':x.ui.debtRow!==d.id?`<div class="sk-go-end"><button type="button" class="btn small" data-action="car:debtRow" data-row="${x.esc(d.id)}">📒 Đòi nợ</button></div>`:`<div class="sk-amt-row">${act(x,'−','amtStep',{key:`debt-${d.id}`,delta:-1,min:1,max:owe,def:owe},'ghost sk-step')}<label class="sk-amt-in"><input type="number" inputmode="numeric" min="1" max="${owe}" value="${Math.min(owe,amtOf(x,`debt-${d.id}`,owe))}" data-sk-amt="debt-${x.esc(d.id)}" aria-label="Đòi bao nhiêu"><small>xu</small></label>${act(x,'+','amtStep',{key:`debt-${d.id}`,delta:1,min:1,max:owe,def:owe},'ghost sk-step')}</div>
      <div class="sk-row">${tone('soft','🙂 Nhắc nhẹ')}${tone('straight','🗣️ Nói thẳng')}${tone('family','👪 Nhờ người nhà')}${x.confirmCmd('🤝 Xóa nợ',cmd,{debt:d.id,forgive:true},`Xóa khoản ${owe} xu cho ${d.who}?`,'small ghost')}</div>`}</li>`;}).join('');
  const done=(debts||[]).filter(d=>d.state!=='open').slice(-3).map(d=>`<li class="muted small">${x.esc(d.who)} · ${d.state==='paid'?'✅ đã trả':d.state==='gone'?'👻 mất':'🤝 đã xóa'}</li>`).join('');
  const sum=open.reduce((s,d)=>s+d.owed-d.paid,0);
  return pane(x,'debts',`📒 Sổ nợ · ${open.length} người · ${x.fmt(sum)} xu`,`<ul class="sk-debts">${rows||'<li class="muted small">Không ai nợ.</li>'}${done}</ul>`,open.length>0,'sk-debtbook');
}
/** What came of the last trouble today (dismissable). */
export function troubleLast(x){
  const l=data(x).trouble?.last;if(!l||l.day!==x.room.day||x.ui.seenTr===l.id)return '';
  return `<div class="sk-last ${l.good===true?'good':l.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(l.emoji)}</span><p><b>${x.esc(l.title)}</b> · ${x.esc(l.outcome)}</p>${act(x,'✕','seenTr',{key:l.id},'ghost small sk-x',' aria-label="Đã đọc"')}</div>`;
}
Object.assign(kitActions,{
  async seenTr(d,el,x){x.ui.seenTr=d.key;x.render();},
  async debtRow(d,el,x){x.ui.debtRow=x.ui.debtRow===d.row?null:d.row;x.render();},
  async amtStep(d,el,x){const b=x.ui.amt??={},cur=Number(b[d.key]===undefined||b[d.key]===''?d.def:b[d.key])||0;
    b[d.key]=Math.max(Number(d.min),Math.min(Number(d.max),cur+Number(d.delta)));x.render();},
  async debtChase(d,el,x){const b=x.ui.amt??={},v=Number(b[d.key]===undefined||b[d.key]===''?d.def:b[d.key]);
    await x.send(d.cmd,{debt:d.debt,tone:d.tone,amount:Math.max(1,Math.min(Number(d.def),Math.floor(v)||Number(d.def)))});},
  async amtSend(d,el,x){const b=x.ui.amt??={},v=Number(b[d.key]===undefined||b[d.key]===''?d.def:b[d.key]);
    if(!(v>0)){x.toast?.('Điền một số đã nhé.');return;}
    await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:Math.floor(v)});},
});
