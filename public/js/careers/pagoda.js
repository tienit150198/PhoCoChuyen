/** Chùa Gió Lành — a young monk's day at the pagoda by the river landing (server: game/careers/pagoda.py).
 * The morning (the schedule in order, the abbot's word), the yard, the main hall, visitors at the gate, the
 * vegetarian kitchen, the donation book (count the bills on the table, write the total), listening, the
 * full-moon ceremony, the old and the children, incidents. Every job is a short chain of steps: tap what to
 * do, put each thing in its place, tap in order, choose, count. The board (Bảng nội quy) is one tap away.
 * The server decides everything; one tap sends one command. */
import {nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,pane,notesPage,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput,tile} from './street_kit.js';

const steps=t=>t.needs?.steps||[];
const cur=t=>steps(t)[t.at]||null;
const kindEmoji=(x,k)=>(cc(x).kind_emoji||{})[k]||'🛕';
const kindLabel=(x,k)=>(cc(x).kinds||{})[k]||'';
const TYPE_ICON={pick:'👆',sort:'🗂️',order:'🔢',choose:'💬',tally:'📒'};

/* ------------------------------------------------------------ the board by the kitchen door */
const notes=x=>`<ul class="pg-notes">${(cc(x).notebook||[]).map(n=>`<li><span aria-hidden="true">${x.esc(n.emoji)}</span><div><b>${x.esc(n.who)}</b><small>${x.esc(n.text)}</small></div></li>`).join('')}</ul>`;
function notebook(x,auto=false){
  return pane(x,'pg-notebook','🔔 Bảng nội quy',notes(x),auto,'pg-notebook');
}

/* ------------------------------------------------------------ the job card */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Nghe dặn');
  const tag=`<span class="tag pg-kind">${x.esc(kindEmoji(x,t.kind))} ${x.esc(kindLabel(x,t.kind))}</span>`;
  return person(x,t,`<p class="muted small">${x.esc(t.opening)}</p>`,tag);
}
function progress(t,x){
  const ss=steps(t);if(ss.length<2)return '';
  const done=new Set(t.closed||[]),skip=new Set(t.skipped||[]);
  return `<ol class="pg-progress" aria-label="Các bước">${ss.map((s,i)=>{const st=done.has(s.id)?'done':skip.has(s.id)?'skip':i===t.at?'now':'';
    return `<li class="${st}" title="${x.esc(s.title)}"><span aria-hidden="true">${st==='done'?'✓':st==='skip'?'–':TYPE_ICON[s.type]||'•'}</span><small>${x.esc(s.title)}</small></li>`;}).join('')}</ol>`;
}
function linesCard(t,x){
  const ls=t.lines||[];if(!ls.length)return '';
  const last=ls.slice(-3).map(l=>`<li>${x.esc(l)}</li>`).join('');
  const all=ls.map(l=>`<li>${x.esc(l)}</li>`).join('');
  return ls.length>3?pane(x,`lines-${t.id}`,`🗒️ Đã làm · ${ls.length} dòng`,`<ul class="pg-lines">${all}</ul>`,false,'pg-lines-pane'):`<ul class="pg-lines">${last}</ul>`;
}

/* ------------------------------------------------------------ the step being worked on */
function pickStep(t,x,s){
  const got=new Set(t.work?.[s.id]||[]);
  const tiles=s.items.map(i=>tile(x,'chua_pick',{task:t.id,item:i.id},`<span class="tile-emoji">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b>${i.look?`<small>${x.esc(i.look)}</small>`:''}`,`pg-i-${i.id}${got.has(i.id)?' selected':''}`)).join('');
  return `<div class="tile-grid pg-picks">${tiles}</div><p class="small muted">Chạm để chọn, chạm lần nữa để bỏ. Đã chọn ${got.size}.</p>`;
}
function sortStep(t,x,s){
  const got=t.work?.[s.id]||{};
  const rows=s.items.map(i=>{const on=got[i.id];
    const chips=s.bins.map(b=>x.cmd(`${x.esc(b.emoji)} ${x.esc(b.label)}`,'chua_put',{task:t.id,item:i.id,bin:b.id},`small pg-bin ${on===b.id?'on':''}`)).join('');
    return `<li class="pg-sort ${on?'set':''}"><div class="pg-item"><span aria-hidden="true">${x.esc(i.emoji)}</span><div><b>${x.esc(i.name)}</b>${i.look?`<small>${x.esc(i.look)}</small>`:''}</div></div><div class="pg-bins">${chips}</div></li>`;}).join('');
  return `<ul class="pg-sorts">${rows}</ul><p class="small muted">Đã xếp ${Object.keys(got).length}/${s.items.length}.</p>`;
}
/** How many chores must go in the sequence (the server sends it; an older server: every chore). */
const orderNeed=s=>Number.isInteger(s.need)?s.need:s.items.length;
function orderStep(t,x,s){
  const got=t.work?.[s.id]||[],by=Object.fromEntries(s.items.map(i=>[i.id,i]));
  const seq=got.map((id,k)=>{const i=by[id];const last=k===got.length-1;
    return `<li><b>${k+1}</b><span aria-hidden="true">${x.esc(i.emoji)}</span><span class="grow">${x.esc(i.name)}</span>${last?x.cmd('↩︎','chua_seq',{task:t.id,item:id},'ghost small pg-undo',false):''}</li>`;}).join('');
  const left=s.items.filter(i=>!got.includes(i.id)).map(i=>tile(x,'chua_seq',{task:t.id,item:i.id},`<span class="tile-emoji">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b>`,`pg-i-${i.id}`)).join('');
  const n=orderNeed(s);
  return `${got.length?`<ol class="pg-seq">${seq}</ol>`:'<p class="small muted">Chạm việc làm trước tiên.</p>'}${left?`<div class="tile-grid pg-left">${left}</div>`:''}<p class="small muted pg-count" aria-live="polite">Đã xếp ${got.length}/${n}${got.length<n?` · còn ${n-got.length} việc nữa mới xong`:''}.</p>`;
}
function chooseStep(t,x,s){
  const opts=s.options.map(o=>x.cmd(`<span class="sk-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}`,'chua_choose',{task:t.id,option:o.id},`sk-opt pg-o-${o.id}`)).join('');
  return `<p class="pg-text">${x.esc(s.text)}</p><div class="sk-opts pg-opts">${opts}</div>`;
}
// The bills lie on the table; you count them yourself and write the total (the box starts empty).
function tallyStep(t,x,s){
  const bills=(s.bills||[]).map(b=>`<li class="pg-bill"><b>${x.fmt(b)}</b><small>xu</small></li>`).join('');
  return `<div class="pg-tally"><p class="small">${x.esc(s.who||'')} · ${(s.bills||[]).length} tờ</p><ul class="pg-bills">${bills}</ul>
    ${amountBox(x,`cd-${t.id}-${s.id}`,0,{min:0,max:10000,label:'Ghi vào sổ công đức',send:'📒 Ghi sổ công đức',cmd:'chua_tally',payload:{task:t.id},field:'amount'})}</div>`;
}
function stepCard(t,x){
  const s=cur(t);if(!s)return '';
  const body={pick:pickStep,sort:sortStep,order:orderStep,choose:chooseStep,tally:tallyStep}[s.type]?.(t,x,s)||'';
  return `<section class="card pg-step pg-${s.type}" data-step="${x.esc(s.id)}"><h4>${TYPE_ICON[s.type]||''} ${x.esc(s.title)}</h4>${s.lead?`<p class="small muted pg-lead">${x.esc(s.lead)}</p>`:''}${body}</section>`;
}

/* ------------------------------------------------------------ the guide */
function stepGuide(t,x){
  const s=cur(t);
  if(!s)return {steps:[],final:null};
  const row=(label,go,pulse)=>({ok:null,label,go,...(pulse!==undefined?{pulse}:{})});
  if(s.type==='pick')return {steps:[],final:{label:x.esc(s.go),go:{cmd:'chua_close',payload:{task:t.id}},ready:true}};
  if(s.type==='sort'){const got=t.work?.[s.id]||{},miss=s.items.find(i=>!got[i.id]);
    const steps=miss?[row(`Xếp chỗ cho ${miss.name}`,{sel:'.pg-sorts',label:`👉 Xếp ${x.esc(miss.name)}`},'')]:[];
    return {steps,final:{label:x.esc(s.go),go:finalGo(steps,'chua_close',{task:t.id}),ready:!miss,why:'xếp hết mọi thứ',can:t.can?.chua_close}};}
  if(s.type==='order'){const got=t.work?.[s.id]||[];
    // The first morning thầy Huệ Minh shows the order (s.tip): the next one glows.
    const tip=Array.isArray(s.tip)?s.tip.find(id=>!got.includes(id)):null,name=tip&&s.items.find(i=>i.id===tip)?.name;
    const steps=tip?[row(`Chạm: ${name}`,{sel:'.pg-left',label:'👉 Chạm việc tiếp theo'},`.pg-left .pg-i-${tip}`)]
      :got.length?[]:[row('Chạm việc làm trước tiên',{sel:'.pg-left',label:'👉 Chạm việc làm trước'},'')];
    // Ready only at k/n, exactly when the server takes the sequence (live 06/10: 68 refusals “Còn việc chưa xếp”).
    const n=orderNeed(s),k=got.length;
    if(!steps.length&&k<n)steps.push(row(`Xếp thêm ${n-k} việc (đã xếp ${k}/${n})`,{sel:'.pg-left',label:'👉 Chạm việc tiếp theo'},''));
    return {steps,final:{label:x.esc(s.go),go:finalGo(steps,'chua_close',{task:t.id}),ready:k>=n,why:`xếp đủ ${n} việc (đã xếp ${k}/${n})`,can:t.can?.chua_close}};}
  if(s.type==='choose')return {steps:[row(s.title,{sel:'.pg-opts',label:'👉 Chọn cách làm'},typeof s.tip==='string'?`.pg-opts .pg-o-${s.tip}`:'')],final:null};
  if(s.type==='tally')return {steps:[row('Đếm từng tờ, ghi tổng vào sổ',{sel:'.pg-tally',label:'👉 Đếm tiền công đức'},'')],final:null};
  return {steps:[],final:null};
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Lo chuyện ngoài sân',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'chua_intro',payload:{},label:'🔔 Vào việc thôi!'}}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Nghe dặn việc',go:{cmd:'ask',payload:{task:t.id},label:'👂 Nghe dặn'}}],final:null,pulse:'.sk-ask'};
  return stepGuide(t,x);
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

const wrap=inner=>`<div class="career-job sk pg">${inner}</div>`;
const top=x=>`${introCard(x,'chua_intro','🔔')}${deskCard(x,'chua_desk','Chuyện ngoài sân')}`;

export default {
  id:'pagoda',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return !t.known?'Nghe dặn việc':'Làm từng bước';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    if(d.desk?.ev||!d.intro||x.ui.intro)return wrap(`${hint}${top(x)}${bottom(x,g)}`);
    if(!t.known)return wrap(`${hint}${top(x)}${ticket(t,x)}${dayBar(x)}${bottom(x,g)}`);
    const n=t.needs||{};
    const note=n.note?`<p class="small muted pg-note">${x.esc(n.note)}</p>`:'';
    return wrap(`${hint}${top(x)}${ticket(t,x)}${progress(t,x)}${stepCard(t,x)}${linesCard(t,x)}${note}${notebook(x)}${dayBar(x)}${bottom(x,g)}`);
  },
  idle(x){
    const d=data(x);
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Lo chuyện ngoài sân',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'chua_intro',payload:{},label:'🔔 Vào việc thôi!'}}],final:null};
      return wrap(`${hintFor(g,x)}${top(x)}${bottom(x,g)}`);}
    return wrap(`${top(x)}${dayBar(x)}${notebook(x,true)}`);
  },
  input(el,x){return kitInput(el,x);},
  // The notebook opened from the scene, the bar or Thêm: a page of its own (app.js 'carPage').
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'pg',eyebrow:'Chùa Gió Lành',title:'🔔 Bảng nội quy',body:notes(x)}):'';},
  tick(root){keepBarAboveFooter(root);},
  actions:{...kitActions,async notes(d,el,x){(x.ui.pane??={})['pg-notebook']=true;x.render();setTimeout(()=>document.querySelector('.pg-notebook')?.scrollIntoView({block:'center'}),0);}},
  dock:[['car:notes','book','Bảng nội quy','Thời khóa, hương đèn, bếp chay'],['car:intro','question','Giới thiệu nghề','Công việc & sao']],
};
