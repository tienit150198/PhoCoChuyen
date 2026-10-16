/** 🏗️ Công trình của phố (game/town_projects.py): the whole street pools money for six buildings, one at a time. Each
 * has a goal; when it is reached it takes 48 hours to build, then a plaque names its sponsors and the next one opens.
 * Opened with data-action="townProjects" (Tiện ích, Khu phố, a lot on either town map: data-id = its project).
 * The page is GET /api/town (v4/town-projects-data.js, shared with the maps); a contribution is the command
 * `jr_town_give {project, amount, anon, confirm}` (wallet then bank, never a loan). Every rule is on the server.
 * Phone first: one project a screen, quick amounts, one main button. Styles: /css/spend.css + /css/town-projects.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {qtyBox,QTY,afterTap,qtyVal} from '../qty-input.js';
import {loadTown,peekTown,serverNow,leftText} from './town-projects-data.js';

const TABS=[['now','🏗️','Công trình đang xây'],['board','🏆','Bảng vàng'],['done','🏛️','Công trình đã xong']];
const BIG=1_000_000;   // from this amount, a second tap confirms
const S={dlg:null,env:null,tab:'now',pick:'',amount:0,anon:false,busy:false,flash:null,arm:0,armTimer:0,timer:0,
  board:'all',pages:{},boardBusy:false};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const V=()=>peekTown();
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const projects=()=>V()?.projects||[];
const current=()=>projects().find(p=>p.id===V()?.current)||null;

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/spend.css','sd-css'),link('/css/town-projects.css','tp-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet tp-sheet';d.setAttribute('aria-labelledby','tp-title');
  d.innerHTML='<div class="sd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-tp]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.tp,el.dataset);
  });
  d.addEventListener('change',e=>{if(e.target.name==='anon')S.anon=e.target.checked;});
  // A typed amount: the main button says what it will give before the box commits.
  d.addEventListener('input',e=>{
    const p=current(),b=d.querySelector('[data-tp="go"]');if(!p||!b||!e.target.matches?.('input[data-qty]'))return;
    S.amount=clampGift(p,qtyVal(e.target));S.arm=0;b.textContent=mainLabel(p);
  });
  d.addEventListener('close',()=>{S.flash=null;S.arm=0;clearInterval(S.timer);S.timer=0;});
  S.dlg=d;return d;
}

export async function openTownProjects(env,data={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await ensureCss();
  const d=dialog();
  // A lot on a map: its own project (a finished one: its plaque; one still to come: its card).
  const id=String(data?.id||''),onLot=()=>{if(projects().find(x=>x.id===id)?.status==='done')S.tab='done';};
  S.tab='now';S.pick=id;S.flash=null;S.arm=0;onLot();
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  await loadTown(env.api,{force:true});
  onLot();render();
  clearInterval(S.timer);S.timer=setInterval(tick,1000);
}
let lastLoad=0;
/** The countdown, each second; once the time is up, the page again (at most every 15 s) for the opening. */
function tick(){
  if(!S.dlg?.open)return;
  const p=current();if(p?.status!=='building')return;
  const el=S.dlg.querySelector('[data-tp-clock]');if(el)el.textContent=leftText(p.ready-serverNow());
  if(p.ready<=serverNow()&&Date.now()-lastLoad>15000){lastLoad=Date.now();loadTown(S.env.api,{force:true}).then(render);}
}

/* ---- the amount ---- */
const left=p=>Math.max(0,(p?.goal||0)-(p?.raised||0));
const cap=p=>Math.min(Number(V()?.max)||10_000_000,left(p));
const floor=()=>Number(V()?.min)||1000;
/** Whole thousands from the minimum to what is left (and once allows). */
function clampGift(p,n){const lo=floor(),hi=cap(p);let v=Math.floor((Number(n)||0)/lo)*lo;return Math.max(lo,Math.min(hi,v||lo));}
const gift=p=>clampGift(p,S.amount||Math.min(cap(p),(V()?.presets||[10_000])[0]));
function why(p){
  if(!J().story)return 'Chỉ có trong hành trình';
  if(!p||p.status!=='funding')return 'Chưa mở góp';
  if(cash()<0)return 'Ví đang nợ';
  const n=gift(p);return ready()>=n?'':`Còn thiếu ${fmt(n-ready())} xu`;
}
const mainLabel=p=>S.arm&&S.arm===gift(p)?`Bấm lần nữa để góp ${fmt(gift(p))} xu`:`Góp ${fmt(gift(p))} xu`;

async function give(p){
  const amount=gift(p);
  if(amount>=BIG&&S.arm!==amount){
    S.arm=amount;clearTimeout(S.armTimer);S.armTimer=setTimeout(()=>{S.arm=0;if(S.dlg?.open)render();},5000);render();return;
  }
  S.arm=0;S.busy=true;render();
  const {api}=S.env;
  try{
    const r=await api.command('jr_town_give',{project:p.id,amount,anon:S.anon,confirm:true});
    S.flash={text:r?.message||`Đã góp ${fmt(amount)} xu. Cảm ơn bạn!`,kind:'good'};S.amount=0;
    S.env.renderMain?.();
  }catch(e){
    S.flash=e?.quiet?null:{text:e?.message||'Chưa góp được. Thử lại nhé.',kind:'bad'};
  }finally{
    S.busy=false;S.pages={};
    await loadTown(api,{force:true});render();
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.sd-body'),y=body?.scrollTop;
  const a=document.activeElement,typing=a?.matches?.('input[data-qty]')&&S.dlg.contains(a)?a.value:null;
  S.dlg.querySelector('.sd-root').innerHTML=page();
  if(typing!==null){const b=S.dlg.querySelector('input[data-qty]');if(b){b.value=typing;b.focus({preventScroll:true});try{b.setSelectionRange(typing.length,typing.length);}catch{/* not a text box */}}}
  if(y)S.dlg.querySelector('.sd-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
const chip=(op,id,label,on,extra='')=>`<button type="button" class="sd-chip${on?' on':''}" data-tp="${op}" data-id="${esc(id)}" aria-pressed="${on}"${extra}>${label}</button>`;
const bar=(pct,cls='')=>`<div class="tp-bar ${cls}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${Math.max(0,Math.min(100,pct))}%"></i></div>`;
const pctOf=p=>Math.max(0,Math.min(100,Math.floor((p.raised||0)*100/Math.max(1,p.goal||1))));
const day=t=>{if(!t)return '';const d=new Date(t*1000);return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}`;};
const rows=list=>list.map((x,i)=>`<li class="${x.me?'me':''}"><span>${x.rank||i+1}</span><b data-no-translate>${esc(x.name)}</b><em>${fmt(x.xu)}</em></li>`).join('');

function page(){
  const t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const head=`<header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">🏗️</span><div class="grow"><h2 id="tp-title">${esc(t[2])}</h2></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,cash()))}</span><button class="icon-btn" type="button" data-tp="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  const tabs=`<nav class="sd-tabs" role="tablist" aria-label="Công trình của phố">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${S.tab===id?'on':''}" data-tp="tab" data-tab="${id}">${e}</button>`).join('')}</nav>`;
  const v=V();
  if(!v)return head+tabs+`<div class="sheet-body sd-body"><p class="sd-empty">⏳</p></div>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  const inner=S.tab==='board'?boardTab():S.tab==='done'?doneTab():nowTab();
  let foot='';
  const p=current();
  if(S.tab==='now'&&p?.status==='funding'&&!soonPick()){const w=why(p);
    foot=`<footer class="sd-bar">${w?`<small class="sd-why">${esc(w)}</small>`:''}<button type="button" class="btn primary big sd-main${S.arm?' tp-arm':''}" data-tp="go"${S.busy||w?' disabled':''}>${esc(mainLabel(p))}</button></footer>`;}
  return head+tabs+`<div class="sheet-body sd-body">${flash}${inner}</div>`+foot;
}

const soonPick=()=>{const x=S.pick?projects().find(p=>p.id===S.pick):null;return x?.status==='soon'?x:null;};
function nowTab(){
  const v=V(),p=current(),pick=soonPick();
  if(pick)return soonCard(pick)+roadmap();
  if(!p)return `<section class="sd-card tp-card"><p class="tp-big" aria-hidden="true">🎉</p><h3>Phố đã xây xong cả ${projects().length} công trình</h3><p class="tp-note">Cảm ơn mọi người đã góp sức.</p></section>`+roadmap();
  const mine=Number(v.mine?.by?.[p.id])||0;
  const top=(p.top||[]).slice(0,5);
  const sponsors=top.length?`<h4>🏆 Góp nhiều nhất</h4><ol class="sd-board tp-board">${rows(top)}</ol>`:'';
  let state='';
  if(p.status==='funding'){
    const presets=(v.presets||[]).filter(x=>x<=cap(p)),n=gift(p);
    const chips=presets.map(x=>chip('amount',x,fmt(x),n===x)).join('')+(left(p)<=cap(p)&&!presets.includes(left(p))?chip('amount',left(p),`Đủ ${fmt(left(p))}`,n===left(p)):'');
    state=`<div class="tp-money"><b>${fmt(p.raised)}</b><span>/ ${fmt(p.goal)} xu</span></div>${bar(pctOf(p))}
      <p class="tp-line"><span>Còn thiếu <b>${fmt(left(p))} xu</b></span><span>👥 ${fmt(p.people)} người góp</span></p>
      <div class="sd-chips sd-amounts">${chips}<label class="tp-typed">${qtyBox({value:n,min:floor(),max:cap(p),step:floor(),money:true,label:'Góp bao nhiêu xu',go:`data-tp="typed" data-id="${QTY}"`})}<small>xu</small></label></div>
      <label class="sd-toggle"><input type="checkbox" name="anon"${S.anon?' checked':''}><span>Ẩn danh trên bảng vàng</span></label>
      <p class="tp-note">Tiền góp là của chung cả phố, không hoàn lại. Đủ tiền là khởi công, ${Math.round((v.build||172800)/3600)} giờ sau khánh thành.</p>`;
  }else if(p.status==='building'){
    const total=Math.max(1,p.ready-p.funded),done=Math.max(0,Math.min(100,Math.floor((serverNow()-p.funded)*100/total)));
    state=`<p class="tp-stage">🚧 Đang xây</p>${bar(done,'build')}<p class="tp-line"><span>Còn <b data-tp-clock>${esc(leftText(p.ready-serverNow()))}</b></span><span>💰 ${fmt(p.raised)} xu · 👥 ${fmt(p.people)}</span></p>
      <p class="tp-note">Khánh thành xong, công trình kế tiếp mở góp.</p>`;
  }
  return `<section class="sd-card tp-card"><h3><span aria-hidden="true">${esc(p.emoji)}</span> ${esc(p.name)}</h3><p class="tp-blurb">${esc(p.blurb)}</p>${state}
    ${mine?`<p class="sd-mine">🧱 Bạn đã góp ${fmt(mine)} xu</p>`:''}${sponsors}${titlesHelp()}</section>`+roadmap();
}
function soonCard(p){
  return `<section class="sd-card tp-card"><h3><span aria-hidden="true">${esc(p.emoji)}</span> ${esc(p.name)}</h3><p class="tp-blurb">${esc(p.blurb)}</p>
    <p class="tp-stage">🪧 Sắp xây</p><p class="tp-line"><span>Mục tiêu <b>${fmt(p.goal)} xu</b></span></p><p class="tp-note">Mở góp khi công trình trước khánh thành.</p>
    <button type="button" class="btn cream" data-tp="pick" data-id="">Xem công trình đang góp</button></section>`;
}
const titlesHelp=()=>`<details class="lx-help tp-help"><summary aria-label="Danh hiệu cho người góp">?</summary><ul>
  <li>Góp nhiều nhất: danh hiệu riêng của công trình.</li><li>Top 2–3: 🏗️ Nhà tài trợ vàng. Top 4–10: 🏗️ Nhà tài trợ bạc.</li>
  <li>Ai góp cũng có 🧱 Góp gạch xây phố khi khánh thành.</li><li>Mỗi lần góp từ 1.000 đến 10.000.000 xu.</li></ul></details>`;
function roadmap(){
  const mark={done:'✅',building:'🚧',funding:'💰',soon:'🔒'};
  const items=projects().map(p=>`<li class="tp-step ${p.status}"><span aria-hidden="true">${esc(p.emoji)}</span><div><b>${esc(p.name)}</b><small>${p.status==='done'?`Khánh thành ${day(p.done)}`:p.status==='building'?'Đang xây':p.status==='funding'?`${pctOf(p)}% · ${fmt(p.goal)} xu`:`${fmt(p.goal)} xu`}</small></div><em aria-hidden="true">${mark[p.status]||''}</em></li>`).join('');
  return `<h4 class="tp-h">🗺️ Lộ trình xây phố</h4><ol class="tp-road">${items}</ol>`;
}

function boardTab(){
  const v=V(),open=projects().filter(p=>p.status!=='soon');
  const chips=chip('board','all','Cả phố',S.board==='all')+open.map(p=>chip('board',p.id,`${esc(p.emoji)}`,S.board===p.id,` aria-label="${esc(p.name)}" title="${esc(p.name)}"`)).join('');
  const mine=Number(v.mine?.xu)||0;
  if(S.board==='all'){
    const list=v.all||[];
    return `<div class="sd-chips">${chips}</div><section class="sd-card"><h3>🏆 Bảng vàng cả phố</h3>
      <p class="tp-line"><span>💰 <b>${fmt(v.xu)} xu</b></span><span>👥 ${fmt(v.people)} người góp</span></p>
      ${list.length?`<ol class="sd-board tp-board">${rows(list)}</ol>`:'<p class="tp-note">Chưa ai góp. Bạn là người đầu tiên nhé!</p>'}
      ${mine?`<p class="sd-mine">🧱 Bạn đã góp tất cả ${fmt(mine)} xu</p>`:''}</section>`;
  }
  const p=projects().find(x=>x.id===S.board);if(!p){S.board='all';return boardTab();}
  const pg=S.pages[p.id];if(!pg&&!S.boardBusy)queueMicrotask(()=>loadBoard(p.id,0));
  const list=pg?.rows||[];
  const body=pg?.error?'<p class="tp-note" role="alert">Chưa tải được danh sách.</p><button class="btn" type="button" data-tp="more" data-id="0">Thử lại</button>'
    :!pg?'<p class="sd-empty">⏳</p>':list.length?`<ol class="sd-board tp-board">${rows(list)}</ol>${pg.more?`<button type="button" class="btn cream tp-more" data-tp="more" data-id="${pg.page+1}"${S.boardBusy?' disabled':''}>Xem thêm</button>`:''}`
    :'<p class="tp-note">Chưa ai góp cho công trình này.</p>';
  return `<div class="sd-chips">${chips}</div><section class="sd-card"><h3><span aria-hidden="true">${esc(p.emoji)}</span> ${esc(p.name)}</h3>
    <p class="tp-line"><span>💰 <b>${fmt(p.raised)} xu</b></span><span>👥 ${fmt(p.people)} người góp</span></p>${body}</section>`;
}
async function loadBoard(id,page){
  if(S.boardBusy)return;S.boardBusy=true;
  try{
    const d=await S.env.api.json(`/api/town/board?p=${encodeURIComponent(id)}&page=${page}`);
    const old=page>0?S.pages[id]?.rows||[]:[];
    S.pages[id]={rows:[...old,...(d.rows||[])],more:!!d.more,page:d.page||page};
  }catch{S.pages[id]={...(S.pages[id]||{rows:[]}),error:page===0,more:page>0};}
  finally{S.boardBusy=false;if(S.dlg?.open&&S.tab==='board')render();}
}

function doneTab(){
  const done=projects().filter(p=>p.status==='done');
  if(!done.length)return `<p class="sd-empty">🏛️</p><p class="tp-note tp-center">Công trình nào khánh thành sẽ có bia ghi danh người góp ở đây.</p>`;
  return `<ul class="tp-plaques">${done.map(p=>`<li class="tp-plaque${S.pick===p.id?' on':''}"><h3><span aria-hidden="true">${esc(p.emoji)}</span> ${esc(p.name)}</h3>
    <p class="tp-line"><span>Khánh thành ${day(p.done)}</span><span>💰 ${fmt(p.raised)} xu · 👥 ${fmt(p.people)}</span></p>
    ${(p.top||[]).length?`<ol class="sd-board tp-board">${rows((p.top||[]).slice(0,10))}</ol>`:''}
    <button type="button" class="btn cream tp-more" data-tp="full" data-id="${esc(p.id)}">Xem cả bia ghi danh</button></li>`).join('')}</ul>`;
}

async function onClick(op,data){
  const p=current();
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.pick='';S.flash=null;S.arm=0;render();S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);return;
    case'pick':S.pick=data.id||'';render();return;
    case'amount':S.amount=Number(data.id)||0;S.arm=0;render();return;
    case'typed':S.amount=p?clampGift(p,Number(data.id)):0;S.arm=0;afterTap(render);return;
    case'go':if(p&&!why(p)&&!S.busy)await give(p);return;
    case'board':S.board=data.id;render();return;
    case'more':{const id=S.board;if(Number(data.id)===0)delete S.pages[id];await loadBoard(id,Number(data.id)||0);return;}
    case'full':S.tab='board';S.board=data.id;render();S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);return;
  }
}
