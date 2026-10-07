/** Nội trợ nhà chị Thảo — a home helper's day (server: game/careers/homemaker.py).
 * The morning (count the market money, order the day's chores), the market (read the list, go, pick
 * fresh goods, haggle, write the market book), cooking for each person, washing up, laundry, cleaning,
 * bà's pills, the children, the fridge, the plants, incidents and the Tết clean-up. Every job is a
 * short chain of steps: tap what to take, put each thing in its place, tap in order, choose, haggle,
 * write the book. The family notebook (Sổ tay nhà) is one tap away.
 * The awkward people: surprises in the house, chị Thảo paying late (a debt book), and chị Thảo
 * asking about the market book again days later.
 * The server decides everything; one tap sends one command. */
import {nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,pane,notesPage,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput,choiceCard,debtBook,troubleLast,tile,tip,clean} from './street_kit.js';

/** The morning note: on a plain day it only repeats the steps ("?" on the clean layout); on a rain, outage or hot day
 * it is the day's cue (ủng, bạt, đèn pin…) and stays on screen. */
const dayNote=(x,s,title)=>!s?'':clean()&&(data(x).mod?.id||'normal')==='normal'?tip(x.esc(s),title,'p'):`<p class="small muted">${x.esc(s)}</p>`;

const steps=t=>t.needs?.steps||[];
const cur=t=>steps(t)[t.at]||null;
const isMarket=t=>t.kind==='market';
const kindEmoji=(x,k)=>(cc(x).kind_emoji||{})[k]||'🏠';
const kindLabel=(x,k)=>(cc(x).kinds||{})[k]||'';
const TYPE_ICON={pick:'👆',sort:'🗂️',order:'🔢',choose:'💬',haggle:'🤝',receipt:'📒'};

/* ------------------------------------------------------------ the family notebook */
const notes=x=>`<ul class="nt-notes">${(cc(x).notebook||[]).map(n=>`<li><span aria-hidden="true">${x.esc(n.emoji)}</span><div><b>${x.esc(n.who)}</b><small>${x.esc(n.text)}</small></div></li>`).join('')}</ul>`;
function notebook(x,auto=false){
  return pane(x,'nt-notebook','📒 Sổ tay nhà',notes(x),auto,'nt-notebook');
}

/* ------------------------------------------------------------ the job card */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Nghe dặn');
  const tag=`<span class="tag nt-kind">${x.esc(kindEmoji(x,t.kind))} ${x.esc(kindLabel(x,t.kind))}</span>`;
  // Clean layout: the morning hand-over is a scene (it folds to "?"); a chore's opening is the ask and stays.
  // Clean layout: the morning hand-over is a scene ("?"), and the morning has no customer card at all; a chore's
  // opening is the ask and stays.
  if(clean()&&t.kind==='setup')return tip(x.esc(t.opening),'Chị Thảo dặn','p');
  return person(x,t,`<p class="muted small">${x.esc(t.opening)}</p>`,clean()?'':tag);
}
function progress(t,x){
  const ss=steps(t);if(ss.length<2)return '';
  const done=new Set(t.closed||[]),skip=new Set(t.skipped||[]);
  return `<ol class="nt-progress" aria-label="Các bước">${ss.map((s,i)=>{const st=done.has(s.id)?'done':skip.has(s.id)?'skip':i===t.at?'now':'';
    return `<li class="${st}" title="${x.esc(s.title)}" aria-label="${x.esc(s.title)}"><span aria-hidden="true">${st==='done'?'✓':st==='skip'?'–':TYPE_ICON[s.type]||'•'}</span>${clean()?'':`<small>${x.esc(s.title)}</small>`}</li>`;}).join('')}</ol>`;
}
function shopList(t,x){
  const n=t.needs||{};if(!isMarket(t))return '';
  const list=n.shop;
  if(!t.out)return `<section class="card nt-shop"><h4>📝 Danh sách đi chợ</h4><ul class="nt-list">${(list||[]).map(s=>`<li>☐ ${x.esc(s)}</li>`).join('')}</ul>
    <p class="small muted">Tiền chợ: ${x.fmt(n.budget||0)} xu. Ra tới chợ là phải nhớ đấy.</p></section>`;
  if(list)return pane(x,`shop-${t.id}`,'📝 Danh sách (chị Thảo nhắn lại)',`<ul class="nt-list">${list.map(s=>`<li>☐ ${x.esc(s)}</li>`).join('')}</ul>`,false,'nt-shop-pane');
  return `<div class="nt-call">${x.cmd('📞 Gọi chị Thảo hỏi lại danh sách','nt_call',{task:t.id},'ghost small')}</div>`;
}
function linesCard(t,x){
  const ls=t.lines||[];if(!ls.length)return '';
  const last=ls.slice(-3).map(l=>`<li>${x.esc(l)}</li>`).join('');
  const all=ls.map(l=>`<li>${x.esc(l)}</li>`).join('');
  // Clean layout: the result of the last step, then the whole log one tap away.
  if(clean())return `<ul class="nt-lines"><li>${x.esc(ls[ls.length-1])}</li></ul>${ls.length>1?pane(x,`lines-${t.id}`,`🗒️ ${ls.length}`,`<ul class="nt-lines">${all}</ul>`,false,'nt-lines-pane'):''}`;
  return ls.length>3?pane(x,`lines-${t.id}`,`🗒️ Đã làm · ${ls.length} dòng`,`<ul class="nt-lines">${all}</ul>`,false,'nt-lines-pane'):`<ul class="nt-lines">${last}</ul>`;
}

/* ------------------------------------------------------------ the step being worked on */
function pickStep(t,x,s){
  const got=new Set(t.work?.[s.id]||[]);
  const tiles=s.items.map(i=>tile(x,'nt_pick',{task:t.id,item:i.id},`<span class="tile-emoji">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b>${i.look?`<small>${x.esc(i.look)}</small>`:''}${i.price?`<em class="nt-price">${x.fmt(i.price)} xu</em>`:''}`,`nt-i-${i.id}${got.has(i.id)?' selected':''}`)).join('');
  return `<div class="tile-grid nt-picks">${tiles}</div>${clean()?`<p class="small muted">✓ ${got.size}</p>${tip('Chạm để chọn, chạm lần nữa để bỏ.','Chọn món')}`:`<p class="small muted">Chạm để chọn, chạm lần nữa để bỏ. Đã chọn ${got.size}.</p>`}`;
}
function sortStep(t,x,s){
  const got=t.work?.[s.id]||{};
  const rows=s.items.map(i=>{const on=got[i.id];
    const chips=s.bins.map(b=>x.cmd(`${x.esc(b.emoji)} ${x.esc(b.label)}`,'nt_put',{task:t.id,item:i.id,bin:b.id},`small nt-bin ${on===b.id?'on':''}`)).join('');
    return `<li class="nt-sort ${on?'set':''}"><div class="nt-item"><span aria-hidden="true">${x.esc(i.emoji)}</span><div><b>${x.esc(i.name)}</b>${i.look?`<small>${x.esc(i.look)}</small>`:''}</div></div><div class="nt-bins">${chips}</div></li>`;}).join('');
  const n=Object.keys(got).length;
  return `<ul class="nt-sorts">${rows}</ul><p class="small muted">${clean()?'✓':'Đã xếp'} ${n}/${s.items.length}</p>`;
}
function orderStep(t,x,s){
  const got=t.work?.[s.id]||[],by=Object.fromEntries(s.items.map(i=>[i.id,i]));
  const seq=got.map((id,k)=>{const i=by[id];const last=k===got.length-1;
    return `<li><b>${k+1}</b><span aria-hidden="true">${x.esc(i.emoji)}</span><span class="grow">${x.esc(i.name)}</span>${last?x.cmd('↩︎','nt_seq',{task:t.id,item:id},'ghost small nt-undo',false):''}</li>`;}).join('');
  const left=s.items.filter(i=>!got.includes(i.id)).map(i=>tile(x,'nt_seq',{task:t.id,item:i.id},`<span class="tile-emoji">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b>`,`nt-i-${i.id}`)).join('');
  return `${got.length?`<ol class="nt-seq">${seq}</ol>`:tip('Chạm việc làm trước tiên.','Xếp thứ tự','p')}${left?`<div class="tile-grid nt-left">${left}</div>`:''}`;
}
/** Clean layout, "who says it, then what they ask" (docs/UI_KIT.md): a scene before the colon that carries no number
 * folds to "?"; the quote and what follows it ("Một xấp 4 tờ gấp đôi") stay whole. */
function sceneText(x,text){
  const m=clean()&&String(text||'').match(/^([^:“"0-9]{6,80}):\s*(“.+)$/s);
  if(!m)return `<p class="nt-text">${x.esc(text)}</p>`;
  return `${tip(x.esc(m[1]),'Bối cảnh')}<p class="nt-text">${x.esc(m[2])}</p>`;
}
/** Curated short forms for the clean layout (docs/UI_KIT.md "curated short labels keep the deciding part"): the
 * morning money keeps its amount and its bills, each answer keeps what it does. A step or answer not in the map shows
 * in full. The full text stays the control's label for readers. */
const SHORT_TEXT={tien:s=>{const a=s.match(/“(\d+) xu/),b=s.match(/(\d+) tờ gấp đôi/);return a&&b?`💵 “${a[1]} xu” · ${b[1]} tờ gấp đôi`:'';}};
const SHORT_OPT={tien:{count:()=>'Đếm lại trước mặt chị',pocket:()=>'Nhét túi quần',msg:l=>{const m=l.match(/(\d+) xu/);return m?`Cất ví riêng, nhắn “nhận ${m[1]} xu”`:'';}}};
const optLabel=(s,o)=>clean()&&SHORT_OPT[s.id]?.[o.id]?.(o.label)||o.label;
function chooseStep(t,x,s){
  const short=clean()&&SHORT_TEXT[s.id]?.(s.text);
  const opts=s.options.map(o=>x.cmd(`<span class="sk-opt-label" aria-label="${x.esc(o.label)}">${x.esc(optLabel(s,o))}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}`,'nt_choose',{task:t.id,option:o.id},`sk-opt nt-o-${o.id}`)).join('');
  return `${short?`<p class="nt-text" aria-label="${x.esc(s.text)}">${x.esc(short)}</p>${tip(x.esc(s.text),s.title)}`:sceneText(x,s.text)}<div class="sk-opts nt-opts">${opts}</div>`;
}
function haggleStep(t,x,s){
  const b=t.bid||{ask:s.quote,tries:0,firm:false},people=cc(x).people||[],who=people[s.seller]?.name||'Người bán';
  const offer=b.firm?'<p class="small muted">Không bớt được nữa rồi.</p>':amountBox(x,`offer-${t.id}-${s.id}`,Math.max(1,b.ask-2),{min:1,max:Math.max(1,b.ask-1),label:'Hoặc trả giá',send:'🤝 Trả giá',cmd:'nt_offer',payload:{task:t.id}});
  return `<div class="nt-haggle"><p><b>${x.esc(who)}</b> · ${x.esc(s.goods)}</p><p class="nt-ask">🗣️ “<b>${x.fmt(b.ask)} xu</b>”${b.tries?` <small class="muted">· đã trả giá ${b.tries} lần</small>`:''}</p>
    ${x.cmd(`💵 Mua giá này · ${x.fmt(b.ask)} xu`,'nt_buy',{task:t.id},'primary full nt-buy')}${offer}</div>`;
}
function receiptStep(t,x,s){
  const n=t.needs||{};
  return `<div class="nt-receipt"><p>💰 Tiền chợ: <b>${x.fmt(n.budget||0)} xu</b> · 🧾 Hóa đơn cộng lại: <b>${x.fmt(t.spent||0)} xu</b></p>
    ${!t.spent?x.cmd('📒 Không tiêu gì, trả lại đủ tiền chợ','nt_receipt',{task:t.id,amount:0},'primary full'):''}
    ${amountBox(x,`so-${t.id}`,t.spent||0,{min:0,max:n.budget||0,label:'Ghi vào sổ chợ: đã tiêu',send:'📒 Ghi sổ chợ, trả tiền thừa',cmd:'nt_receipt',payload:{task:t.id},field:'amount'})}</div>`;
}
function stepCard(t,x){
  const s=cur(t);if(!s)return '';
  const body={pick:pickStep,sort:sortStep,order:orderStep,choose:chooseStep,haggle:haggleStep,receipt:receiptStep}[s.type]?.(t,x,s)||'';
  // Clean layout: a choice's heading is its icon (the bar says "Chọn cách làm"; readers get the title).
  const h4=clean()&&s.type==='choose'?`<h4 aria-label="${x.esc(s.title)}">${TYPE_ICON[s.type]||''}</h4>`:`<h4>${TYPE_ICON[s.type]||''} ${x.esc(s.title)}</h4>`;
  return `<section class="card nt-step nt-${s.type}" data-step="${x.esc(s.id)}">${h4}${s.lead?tip(x.esc(s.lead),s.title,'p'):''}${body}</section>`;
}

/* ------------------------------------------------------------ the awkward moments */
function lateCard(t,x){
  const tw=t.twist;if(!tw||tw.state!=='on')return '';
  const o=(choice,label,sub)=>({cmd:'nt_late',payload:{task:t.id,choice},label,sub});
  return choiceCard(x,'nt-late','💸','Chị Thảo khất tiền công',tw.line,[
    o('ok','🙂 Dạ, chị gửi sau cũng được','ghi vào sổ nợ'),o('ask','🙏 Nhẹ nhàng xin công hôm nay','em cần tiền chợ cho nhà mình')]);
}
function troubleCard(x){
  const ev=data(x).trouble?.ev;if(!ev||ev.kind!=='audit')return '';
  const f=ev.facts,o=(choice,label,sub)=>({cmd:'nt_trouble',payload:{choice},label,sub});
  return choiceCard(x,'sk-trouble','📒','Chị Thảo cầm sổ chợ',`“Hôm trước em ghi lệch ${f.diff} xu so với giá cô Năm nói. Em xem lại giúp chị.”`,[
    o('refund',`💵 Nhận sai, trả lại ${f.diff} xu`,'nói thật'),o('explain','🗣️ Bảo hôm đó giá tăng','chị Thảo có thể hỏi lại cô Năm'),o('deny','🙅 Chối','em ghi đúng mà')]);
}

/* ------------------------------------------------------------ the guide */
function stepGuide(t,x){
  const s=cur(t);
  if(isMarket(t)&&!t.out)return {steps:[{ok:null,label:'Nhớ danh sách, ra chợ',go:{cmd:'nt_out',payload:{task:t.id},label:'🛵 Ra chợ'}}],final:null};
  if(!s)return {steps:[],final:null};
  const row=(label,go,pulse)=>({ok:null,label,go,...(pulse!==undefined?{pulse}:{})});
  if(s.type==='pick')return {steps:[],final:{label:x.esc(s.go),go:{cmd:'nt_close',payload:{task:t.id}},ready:true}};
  if(s.type==='sort'){const got=t.work?.[s.id]||{},miss=s.items.find(i=>!got[i.id]);
    const steps=miss?[row(`Xếp chỗ cho ${miss.name}`,{sel:`.nt-sorts`,label:`👉 Xếp ${x.esc(miss.name)}`},'')]:[];
    return {steps,final:{label:x.esc(s.go),go:finalGo(steps,'nt_close',{task:t.id}),ready:!miss,why:'xếp hết các món',can:t.can?.nt_close}};}
  if(s.type==='order'){const got=t.work?.[s.id]||[];
    // The first morning chị Thảo shows the order (s.tip): the next chore glows.
    const tip=Array.isArray(s.tip)?s.tip.find(id=>!got.includes(id)):null,name=tip&&s.items.find(i=>i.id===tip)?.name;
    const steps=tip?[row(`Chạm: ${name}`,{sel:'.nt-left',label:'👉 Chạm việc tiếp theo'},`.nt-left .nt-i-${tip}`)]
      :got.length?[]:[row('Chạm việc làm trước tiên',{sel:'.nt-left',label:'👉 Chạm việc làm trước'},'')];
    // can.nt_close: the server's own rule (every chore that belongs in the day is in the sequence).
    return {steps,final:{label:x.esc(s.go),go:{cmd:'nt_close',payload:{task:t.id}},ready:got.length>0,why:'xếp thứ tự các việc',can:t.can?.nt_close}};}
  if(s.type==='choose')return {steps:[row(s.title,{sel:'.nt-opts',label:'👉 Chọn cách làm'},typeof s.tip==='string'?`.nt-opts .nt-o-${s.tip}`:'')],final:null};
  if(s.type==='haggle')return {steps:[row(s.title,{sel:'.nt-haggle',label:'👉 Mua hay trả giá'},'')],final:null};
  if(s.type==='receipt')return {steps:[row(s.title,{sel:'.nt-receipt',label:'👉 Ghi sổ chợ'},'')],final:null};
  return {steps:[],final:null};
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện trong nhà',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(d.trouble?.ev)return {steps:[{ok:null,label:'Chị Thảo hỏi lại sổ chợ',go:{sel:'.sk-trouble',label:'👉 Trả lời chị Thảo'},pulse:''}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'nt_intro',payload:{},label:'🏠 Vào việc thôi!'}}],final:null};
  if(t.twist?.state==='on')return {steps:[{ok:null,label:'Chị Thảo khất tiền công',go:{sel:'.sk-twist',label:'👉 Trả lời chị Thảo'},pulse:''}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Nghe dặn việc',go:{cmd:'ask',payload:{task:t.id},label:'👂 Nghe dặn'}}],final:null,pulse:'.sk-ask'};
  return stepGuide(t,x);
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

const wrap=inner=>`<div class="career-job sk nt">${inner}</div>`;
const top=x=>`${introCard(x,'nt_intro','🏠')}${deskCard(x,'nt_desk','Chuyện trong nhà')}${troubleCard(x)}${troubleLast(x)}`;

export default {
  id:'homemaker',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return !t.known?'Nghe dặn việc':isMarket(t)&&!t.out?'Ra chợ':'Làm từng bước';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    if(d.desk?.ev||d.trouble?.ev||!d.intro||x.ui.intro)return wrap(`${hint}${top(x)}${bottom(x,g)}`);
    if(t.twist?.state==='on')return wrap(`${hint}${top(x)}${ticket(t,x)}${linesCard(t,x)}${lateCard(t,x)}${bottom(x,g)}`);
    if(!t.known)return wrap(`${hint}${top(x)}${ticket(t,x)}${dayBar(x)}${bottom(x,g)}`);
    const n=t.needs||{};
    const note=!n.note?'':t.kind==='setup'?dayNote(x,n.note,'Hôm nay'):`<p class="small muted nt-note">${x.esc(n.note)}</p>`;
    const main=isMarket(t)&&!t.out?shopList(t,x):`${isMarket(t)?shopList(t,x):''}${stepCard(t,x)}`;
    return wrap(`${hint}${top(x)}${ticket(t,x)}${progress(t,x)}${main}${linesCard(t,x)}${note}${notebook(x)}${dayBar(x)}${bottom(x,g)}`);
  },
  idle(x){
    const d=data(x);
    if(d.trouble?.ev){const g={steps:[{ok:null,label:'Chị Thảo hỏi lại sổ chợ',go:{sel:'.sk-trouble',label:'👉 Trả lời chị Thảo'},pulse:''}],final:null};return wrap(`${hintFor(g,x)}${top(x)}${bottom(x,g)}`);}
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện trong nhà',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'nt_intro',payload:{},label:'🏠 Vào việc thôi!'}}],final:null};
      return wrap(`${hintFor(g,x)}${top(x)}${bottom(x,g)}`);}
    return wrap(`${top(x)}${dayBar(x)}${notebook(x,true)}${debtBook(x,d.debts,'nt_chase')}`);
  },
  input(el,x){return kitInput(el,x);},
  // The notebook opened from the scene, the bar or Thêm: a page of its own (app.js 'carPage').
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'nt',eyebrow:'Nhà chị Thảo',title:'📒 Sổ tay nhà',body:notes(x)}):'';},
  tick(root){keepBarAboveFooter(root);},
  actions:{...kitActions,async notes(d,el,x){(x.ui.pane??={})['nt-notebook']=true;x.render();setTimeout(()=>document.querySelector('.nt-notebook')?.scrollIntoView({block:'center'}),0);}},
  dock:[['car:notes','book','Sổ tay nhà','Ai ăn gì, uống thuốc gì'],['car:intro','question','Giới thiệu nghề','Công việc & sao']],
};
