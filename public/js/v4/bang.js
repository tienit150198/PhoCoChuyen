/** ⚔️ Bang (game/bang.py): find or found a guild, its members and roles, the deposit-only fund, the facilities, the
 * points-only shop, the bang's own Giờ vàng and the weekly ranking. Opened with data-action="bang" (Tiện ích › Bạn bè &
 * khu phố, Thêm › Khu phố, the old interface's rail). Every rule is on the server:
 *   GET  /api/bang (mine + my bang's page, or the list) · ?q= search · ?id= a bang's card · ?friends=1 · ?found=1 checklist
 *   POST /api/bang/<op> (join, accept, leave, invite, approve, kick, role, set, rules, disband, checkin, build, isle, buy,
 *        wear, fire, gh_set, gh_cancel): database only, the answer carries the new page;
 *   🏝️ Đảo bang (owner 21/10): bought (cấp 1, 1 triệu) then upgraded (cấp 2…5) from the fund by Phó bang and up
 *        (isle {to, confirm}); until it is bought the island, the pet arena and the Bang chiến are locked, and the
 *        home tab shows the offer first (members: ask an officer). The island card sits first in 🏗️ Công trình;
 *   🚪 how a bang takes people (owner 20/10): mode closed / ask / auto + optional requirements (a career from a title of
 *        its real ladder, a title step in any career, the account's age), set by Phó bang and up (⚙️), shown on its card;
 *        the career ladders come from GET /api/bang?careers=1 when ⚙️ opens.
 *   the commands jr_bang_found (5.000.000 xu) and jr_bang_give (the fund: no cap, any amount the player has since
 *        21/10, "Tất cả" = wallet + bank) go through the save like any payment.
 * Phone first: one bang a screen, emoji tabs, one main button in the sticky bar. Styles: /css/spend.css + /css/bang.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {qtyBox,QTY,qtyVal} from '../qty-input.js';
import {COLORS,ROLES,chip,setMine,tagLine} from './bang-tag.js';

const IN_TABS=[['home','🏯','Bang của tôi'],['members','👥','Thành viên'],['build','🏗️','Công trình'],['shop','🛍️','Cửa hàng bang'],['rank','👑','Xếp hạng tuần'],['more','⚙️','Cài đặt bang']];
const OUT_TABS=[['find','🔎','Tìm bang'],['found','⚔️','Lập bang'],['rank','👑','Xếp hạng tuần']];
const BIG=1_000_000;
const S={dlg:null,env:null,view:null,tab:'',flash:null,busy:false,q:'',list:null,found:null,form:null,amount:0,arm:'',armTimer:0,
  friends:null,sel:'',gh:null,timer:0,at:0,bang:null,ladder:null,rules:null};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const J=()=>S.env?.api?.state?.journey||{};
const cash=()=>Number(J().wallet)||0;
const ready=()=>cash()<0?0:cash()+(Number(J().bank?.balance)||0);
const CAT=()=>S.view?.catalogue||{};
const P=()=>S.view?.page||null;
const ME=()=>P()?.me||null;
const rank=r=>(CAT().roles?.[r]?.rank)||1;
const serverNow=()=>(Number(S.view?.now)||Date.now()/1000)+Math.max(0,Date.now()-S.at)/1000;
const hex=c=>(COLORS[c]||COLORS.do)[0];
const ink=c=>(COLORS[c]||COLORS.do)[1];
function left(sec){const t=Math.max(1,Math.ceil(Math.max(0,sec)/60)),h=Math.floor(t/60),m=t%60;return h?`${h} giờ${m&&h<10?` ${m} phút`:''}`:`${m} phút`;}   // never "5 giờ 60 phút"
const VN=7*3600;
const vnDate=t=>new Date((t+VN)*1000);
const hm=t=>{const d=vnDate(t);return `${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`;};
const DOW=['CN','T2','T3','T4','T5','T6','T7'];
const dayLabel=t=>{const d=vnDate(t),n=vnDate(serverNow());const same=(a,b)=>a.getUTCFullYear()===b.getUTCFullYear()&&a.getUTCMonth()===b.getUTCMonth()&&a.getUTCDate()===b.getUTCDate();
  if(same(d,n))return 'Hôm nay';const m=new Date(n.getTime()+86400e3);if(same(d,m))return 'Ngày mai';return `${DOW[d.getUTCDay()]} ${d.getUTCDate()}/${d.getUTCMonth()+1}`;};

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/spend.css','sd-css'),link('/css/bang.css','bg-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium sd-sheet bg-sheet';d.setAttribute('aria-labelledby','bg-title');
  d.innerHTML='<div class="sd-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-bg]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.bg,el.dataset,el);
  });
  d.addEventListener('input',e=>{
    const t=e.target;
    if(t.name==='bg-q'){S.q=t.value;clearTimeout(S.qTimer);S.qTimer=setTimeout(search,300);return;}
    if(t.name?.startsWith('f-')&&S.form){S.form[t.name.slice(2)]=t.type==='checkbox'?t.checked:t.value;return;}
    if(t.matches?.('input[data-qty]')){S.amount=clampGive(qtyVal(t));S.arm='';const b=d.querySelector('[data-bg="give"]');if(b)b.textContent=giveLabel();}
  });
  d.addEventListener('change',e=>{const t=e.target;if(t.name==='f-open'&&S.form)S.form.open=t.checked;
    if(t.name?.startsWith('rq-')){const r=draft(),k=t.name.slice(3);r[k]=k==='career'?t.value:Math.max(0,Math.floor(Number(t.value)||0));if(k==='career')r.rank=t.value?Math.max(1,r.rank||1):0;render();return;}if(t.name?.startsWith('gh-')&&S.gh){S.gh[t.name.slice(3)]=Number(t.value);render();}});
  d.addEventListener('close',()=>{S.flash=null;S.arm='';clearInterval(S.timer);S.timer=0;});
  S.dlg=d;return d;
}

export async function openBang(env,data={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  await ensureCss();
  const d=dialog();
  S.flash=null;S.arm='';S.sel='';
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  await load();
  if(data?.tab)S.tab=String(data.tab);
  if(data?.isle&&S.view?.mine)S.tab=isleLevel()?'build':'home';   // 🏯 Đảo bang tapped before the island is bought: the offer
  render();
  clearInterval(S.timer);S.timer=setInterval(tick,1000);
}

async function load(query=''){
  try{const v=await S.env.api.json('/api/bang'+query);accept(v);}
  catch(e){S.flash={text:e?.message||'Chưa tải được. Thử lại nhé.',kind:'bad'};}
}
function accept(v){
  if(!v||typeof v!=='object')return;
  S.view=v;S.at=Date.now();setMine(v.mine||null);
  if(!v.mine&&v.list)S.list=v.list;
  const tabs=(v.mine?IN_TABS:OUT_TABS).map(t=>t[0]);
  if(!tabs.includes(S.tab))S.tab=tabs[0];
}
async function search(){
  try{const v=await S.env.api.json('/api/bang?q='+encodeURIComponent(S.q.slice(0,30)));S.list=v.list||[];if(v.board&&S.view)S.view.board=v.board;}catch{/* keep the last list */}
  render();
}
async function post(op,data={}){
  if(S.busy)return null;S.busy=true;render();
  try{
    const r=await S.env.api.post('/api/bang/'+op,data);const done=r?.done||{};delete r.done;accept(r);
    if(['wear','buy','join','accept','leave','kick','disband','set'].includes(op))S.env.renderMain?.();   // the uniform, the tag: the town redraws me
    S.flash=done.message?{text:done.message,kind:'good'}:null;return done;
  }catch(e){S.flash={text:e?.message||'Chưa được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;S.arm='';render();}
}
async function command(name,payload){
  if(S.busy)return null;S.busy=true;render();
  try{
    const r=await S.env.api.command(name,payload);S.flash={text:r?.message||'Xong!',kind:'good'};S.env.renderMain?.();
    await load();return r;
  }catch(e){S.flash=e?.quiet?null:{text:e?.message||'Chưa được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;S.arm='';render();}
}
const rid=()=>'bg-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10);
/** A second tap within 5 s confirms (`key`: what is armed). */
function armed(key){
  if(S.arm===key){S.arm='';return true;}
  S.arm=key;clearTimeout(S.armTimer);S.armTimer=setTimeout(()=>{S.arm='';if(S.dlg?.open)render();},5000);render();return false;
}

function tick(){
  if(!S.dlg?.open)return;
  for(const el of S.dlg.querySelectorAll('[data-bg-until]'))el.textContent=left(Number(el.dataset.bgUntil)-serverNow());
  const due=(P()?.facilities||[]).some(f=>f.building&&f.ready<=serverNow())||Boolean(P()?.isle?.to&&P().isle.ready<=serverNow());
  if(due&&Date.now()-S.at>15000){S.at=Date.now();load().then(render);}
}

/* ---- the fund amount ---- */
const give=()=>CAT().give||{min:1000,max:1e12,presets:[1_000_000,10_000_000,100_000_000]};
/** 21/10: no cap on the fund nor on a gift: at most what I have (wallet then bank), whole thousands. */
const most=()=>Math.floor(Math.min(give().max,ready())/give().min)*give().min;
function clampGive(n){const g=give(),lo=g.min,hi=Math.max(lo,most());let v=Math.floor((Number(n)||0)/lo)*lo;return Math.max(lo,Math.min(hi,v||lo));}
const amount=()=>clampGive(S.amount||give().presets[0]);
const giveLabel=()=>S.arm==='give'?`Bấm lần nữa: góp ${fmt(amount())} xu`:`💰 Góp ${fmt(amount())} xu`;
function giveWhy(){
  if(!J().story)return 'Chỉ có trong hành trình';
  if(cash()<0)return 'Ví đang nợ';
  const n=amount();return ready()>=n?'':`Còn thiếu ${fmt(n-ready())} xu`;
}

/* ---- clicks ---- */
async function onClick(op,d,el){
  const p=P(),me=ME();
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=d.tab;S.flash=null;S.arm='';S.sel='';if(d.tab==='found'&&!S.found)loadFound();if(d.tab==='members'&&!S.friends&&rank(me?.role)>=3)loadFriends();if(d.tab==='more'&&rank(me?.role)>=4){S.rules=null;if(!S.ladder)loadLadder();}render();S.dlg.querySelector('.sd-body')?.scrollTo?.(0,0);return;
    case'join':await post('join',{bang:d.id});return;
    case'cancel':await post('cancel',{bang:d.id});return;
    case'accept':await post('accept',{bang:d.id});return;
    case'decline':await post('decline',{bang:d.id});return;
    case'peek':S.bang=d.id;try{S.bang={id:d.id,...await S.env.api.json('/api/bang?id='+encodeURIComponent(d.id))};}catch(e){S.flash={text:e?.message||'Không mở được.',kind:'bad'};S.bang=null;}render();return;
    case'unpeek':S.bang=null;render();return;
    case'checkin':await post('checkin');return;
    case'amount':S.amount=clampGive(d.n==='all'?most():Number(d.n));S.arm='';render();return;
    case'isle':{const to=Number(d.to)||1;if(!armed('isle:'+to))return;await post('isle',{to,confirm:true});if(to===1)S.env.renderMain?.();return;}
    case'give':{
      const n=amount();if(n>=BIG&&!armed('give'))return;
      await command('jr_bang_give',{bang:S.view.mine.bang,amount:n,confirm:true});S.amount=0;return;}
    case'chat':S.dlg.close();await S.env.act?.('liveChat',{ch:d.ch});return;
    case'island':if(!isleLevel()){S.tab='home';render();S.dlg.querySelector('.bg-isle')?.scrollIntoView?.({block:'nearest'});return;}
      S.dlg.close();await S.env.act?.('bangIsland',{});return;   // 🏯 Đảo bang (v4/bang-island.js)
    case'sel':S.sel=S.sel===d.pid?'':d.pid;S.arm='';render();return;
    case'role':{if(d.role==='chu'&&!armed('chu:'+d.pid))return;await post('role',{pid:d.pid,role:d.role,...(d.role==='chu'?{confirm:true}:{})});return;}
    case'kick':if(!armed('kick:'+d.pid))return;await post('kick',{pid:d.pid,confirm:true});S.sel='';return;
    case'approve':await post('approve',{pid:d.pid,ok:d.ok!=='0'});return;
    case'invite':{const v=(d.code||S.dlg.querySelector('input[name="bg-code"]')?.value||'').trim().toUpperCase();
      if(!/^PCC-[0-9A-Z]{6}$/.test(v)){S.flash={text:'Nhập mã người chơi dạng PCC-XXXXXX nhé.',kind:'bad'};render();return;}
      await post('invite',{code:v});return;}
    case'build':{const f=(p?.facilities||[]).find(x=>x.id===d.id);if(!f)return;if(!armed('build:'+f.id))return;await post('build',{fac:f.id,confirm:true});return;}
    case'buy':await post('buy',{item:d.id,rid:rid()});return;
    case'wear':await post('wear',{item:d.id,on:d.on==='1',...(d.style?{style:d.style}:{})});return;
    case'fire':{const r=await post('fire',{rid:rid()});if(r){try{(await import('./fireworks.js')).markMine?.('lon');}catch{/* the show comes anyway */}}return;}
    case'ghDay':S.gh={...ghDefault(),...S.gh,day:Number(d.n)};render();return;
    case'ghSet':{const t=ghStart();if(!t)return;await post('gh_set',{start:t});return;}
    case'ghCancel':if(!armed('ghc:'+d.id))return;await post('gh_cancel',{id:Number(d.id)});return;
    case'open':await post('set',{open:d.on==='1'});return;
    case'mode':await post('rules',{mode:d.mode});S.rules=null;return;
    case'rulesSave':{const r=draft();await post('rules',{career:r.rank?r.career:'',rank:r.career?r.rank:0,any:r.any,days:r.days});S.rules=null;return;}
    case'rulesClear':await post('rules',{career:'',rank:0,any:0,days:0});S.rules=null;return;
    case'emoji':if(S.form){S.form.emoji=d.e;render();}else await post('set',{emoji:d.e});return;
    case'color':if(S.form){S.form.color=d.c;render();}else await post('set',{color:d.c});return;
    case'motto':{const v=S.dlg.querySelector('input[name="bg-motto"]')?.value||'';await post('set',{motto:v});return;}
    case'leave':if(!armed('leave'))return;await post('leave',{confirm:true});return;
    case'disband':{const v=S.dlg.querySelector('input[name="bg-disband"]')?.value||'';if(!armed('disband'))return;await post('disband',{confirm:true,name:v});return;}
    case'found':{
      const f=S.form;if(!f)return;if(!armed('found'))return;
      const r=await command('jr_bang_found',{name:String(f.name||'').trim(),emoji:f.emoji,color:f.color,motto:String(f.motto||'').trim(),open:!!f.open,confirm:true});
      if(r){S.form=null;S.found=null;}return;}
    case'more':{S.list=null;render();return;}
    default:return;
  }
}
async function loadFound(){
  S.form??={name:'',emoji:(CAT().emojis||['⚔️'])[0],color:'do',motto:'',open:true};
  try{S.found=(await S.env.api.json('/api/bang?found=1')).found;}catch{S.found={};}
  render();
}
async function loadLadder(){
  try{S.ladder=(await S.env.api.json('/api/bang?careers=1')).careers||[];}catch{S.ladder=[];}
  render();
}
/** The requirement form being edited (starts from the bang's rules). */
function draft(){
  if(!S.rules){const r=P()?.rules||{};S.rules={career:r.career||'',rank:r.rank||0,any:r.any||0,days:r.days||0};}
  return S.rules;
}
async function loadFriends(){
  try{S.friends=(await S.env.api.json('/api/bang?friends=1')).friends||[];}catch{S.friends=[];}
  render();
}

/* ---- Giờ vàng picker ---- */
function ghDefault(){const t=serverNow()+2*3600,d=vnDate(t);return {day:0,h:d.getUTCHours(),m:0};}
function ghStart(){
  const g={...ghDefault(),...S.gh},n=vnDate(serverNow());
  const base=Date.UTC(n.getUTCFullYear(),n.getUTCMonth(),n.getUTCDate())/1000-VN;   // today's VN midnight
  return base+g.day*86400+g.h*3600+g.m*60;
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  const body=S.dlg.querySelector('.sd-body'),y=body?.scrollTop;
  const a=document.activeElement,keep=a&&S.dlg.contains(a)&&a.matches?.('input')?{name:a.name,qty:a.matches('[data-qty]'),value:a.value,pos:a.selectionStart}:null;
  S.dlg.querySelector('.sd-root').innerHTML=page();
  if(keep){const b=keep.qty?S.dlg.querySelector('input[data-qty]'):S.dlg.querySelector(`input[name="${keep.name}"]`);if(b&&b.type!=='checkbox'){b.value=keep.value;b.focus({preventScroll:true});try{b.setSelectionRange(keep.pos,keep.pos);}catch{/* not text */}}}
  if(y)S.dlg.querySelector('.sd-body').scrollTop=y;
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
const btn=(op,label,extra='',cls='btn')=>`<button type="button" class="${cls}" data-bg="${op}"${extra}${S.busy?' disabled':''}>${label}</button>`;
const crest=(e,c,size='')=>`<span class="bg-crest${size}" style="--bgc:${hex(c)};--bgi:${ink(c)}" aria-hidden="true">${esc(e||'⚔️')}</span>`;
const bar=(pct,cls='')=>`<div class="tp-bar ${cls}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${Math.max(0,Math.min(100,pct))}%"></i></div>`;

function page(){
  const v=S.view,inside=!!v?.mine,tabs=inside?IN_TABS:OUT_TABS,t=tabs.find(x=>x[0]===S.tab)||tabs[0];
  const m=v?.mine;
  const head=`<div class="bg-stick"><header class="sheet-head sd-head">${m?crest(m.emoji,m.color?.id):'<span class="sd-logo" aria-hidden="true">⚔️</span>'}<div class="grow"><h2 id="bg-title">${esc(inside?m.name:t[2])}</h2>${inside?`<small class="bg-sub">${esc(ROLES[m.role]||'')} · ⭐ ${fmt(m.points)}</small>`:''}</div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(Math.max(0,cash()))}</span><button class="icon-btn" type="button" data-bg="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  const nav=`<nav class="sd-tabs" role="tablist" aria-label="Bang">${tabs.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${t[0]===id}" aria-label="${esc(l)}" title="${esc(l)}" class="${t[0]===id?'on':''}" data-bg="tab" data-tab="${id}">${e}</button>`).join('')}</nav></div>`;
  if(!v)return head+`</div><div class="sheet-body sd-body"><p class="sd-empty">⏳</p></div>`;
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  if(!v.account)return head+`</div><div class="sheet-body sd-body">${flash}<section class="sd-card bg-center"><p class="tp-big">⚔️</p><h3>Đăng nhập để vào bang</h3><p class="tp-note">Bang cần tài khoản (như chat).</p></section></div>`;
  let inner='',foot='';
  const id=t[0];
  if(S.bang&&!inside||S.bang&&id==='rank')inner=peekView();
  else if(id==='find')inner=findTab();
  else if(id==='found'){inner=foundTab();foot=foundFoot();}
  else if(id==='rank')inner=rankTab();
  else if(id==='home'){inner=homeTab();foot=homeFoot();}
  else if(id==='members')inner=membersTab();
  else if(id==='build')inner=buildTab();
  else if(id==='shop')inner=shopTab();
  else if(id==='more')inner=moreTab();
  return head+nav+`<div class="sheet-body sd-body">${flash}${inner}</div>`+foot;
}

/* -- outside a bang -- */
function invitesCard(){
  const list=S.view?.invites||[];if(!list.length)return '';
  return `<section class="sd-card bg-invites"><h3>📨 Lời mời vào bang</h3>${list.map(x=>`<div class="bg-row">${crest(x.emoji,x.color)}<div class="grow"><b data-no-translate>${esc(x.name)}</b><small>${esc(x.by)} mời bạn</small></div>${btn('accept','Vào',` data-id="${esc(x.bang)}"`,'btn primary')}${btn('decline','✕',` data-id="${esc(x.bang)}" aria-label="Từ chối"`,'btn cream')}</div>`).join('')}</section>`;
}
function bangCard(c){
  const full=c.n>=c.cap;
  const act=c.asked?btn('cancel','Hủy đơn',` data-id="${esc(c.id)}"`,'btn cream'):full?'<span class="bg-full">Đủ người</span>':modeOf(c)==='closed'?'<span class="bg-full">Đang đóng</span>':btn('join',joinLabel(c),` data-id="${esc(c.id)}"`,'btn primary');
  return `<div class="bg-card"><button type="button" class="bg-peek" data-bg="peek" data-id="${esc(c.id)}" aria-label="Xem bang ${esc(c.name)}">${crest(c.emoji,c.color)}<span class="grow"><b data-no-translate>${esc(c.name)}</b>${c.motto?`<small data-no-translate>${esc(c.motto)}</small>`:''}<small>👥 ${c.n}/${c.cap} · ${esc(MODES[modeOf(c)])}${c.rank&&c.score?` · #${c.rank} tuần này`:''}</small>${reqLine(c)}</span></button>${act}</div>`;
}
function findTab(){
  const list=S.list||S.view?.list||[];
  const box=`<label class="bg-search">🔎<input type="search" name="bg-q" value="${esc(S.q)}" placeholder="Tìm tên bang" maxlength="30" autocomplete="off" enterkeyhint="search"></label>`;
  const rows=list.length?`<div class="bg-list">${list.map(bangCard).join('')}</div>`:`<section class="sd-card bg-center"><p class="tp-big">🏯</p><p class="tp-note">${S.q?'Không có bang nào tên như vậy.':'Chưa có bang nào. Lập bang đầu tiên của phố nhé!'}</p>${btn('tab','⚔️ Lập bang',' data-tab="found"','btn primary')}</section>`;
  return invitesCard()+box+rows+`<p class="tp-note">Vào bang miễn phí: mỗi bang tự chọn cách nhận người và yêu cầu (📋). Đổi bang lúc nào cũng được, tối đa 10 bang một ngày. Mỗi lúc ở một bang.</p>`;
}
function peekView(){
  const b=S.bang;if(!b||!b.bang)return '<p class="sd-empty">⏳</p>';
  const c=b.bang;
  const act=b.member?'':b.invited?btn('accept','Nhận lời mời',` data-id="${esc(c.id)}"`,'btn primary'):b.asked?btn('cancel','Hủy đơn xin vào',` data-id="${esc(c.id)}"`,'btn cream'):c.n>=c.cap?'<p class="tp-note">Bang đã đủ người.</p>':modeOf(c)==='closed'?'<p class="tp-note">🚫 Bang đang đóng, chỉ vào được khi được mời.</p>':btn('join',modeOf(c)==='auto'?'Vào bang':'Xin vào',` data-id="${esc(c.id)}"`,'btn primary');
  const lv=b.levels||{};
  return `<button type="button" class="btn cream bg-back" data-bg="unpeek">← Quay lại</button><section class="sd-card bg-hero" style="--bgc:${hex(c.color)}">${crest(c.emoji,c.color,' big')}<h3 data-no-translate>${esc(c.name)}</h3>${c.motto?`<p class="bg-motto" data-no-translate>“${esc(c.motto)}”</p>`:''}
    <p class="tp-line"><span>👑 ${esc(b.leader_name||'')}</span><span>👥 ${c.n}/${c.cap}</span><span>${esc(MODES[modeOf(c)])}</span></p>${(c.req||[]).length?`<ul class="bg-reqs">${c.req.map(x=>`<li>📋 ${esc(x)}</li>`).join('')}</ul>`:''}
    <p class="bg-levels">${(CAT().facilities||[]).filter(f=>lv[f.id]).map(f=>`<span title="${esc(f.name)}">${esc(f.emoji)} ${lv[f.id]}</span>`).join('')}</p>${act}</section>
    ${(b.members||[]).length?`<h4 class="tp-h">Thành viên</h4><ol class="sd-board">${b.members.map(x=>`<li><span>${esc(roleIcon(x.role))}</span><b data-no-translate>${esc(x.name)}</b><em>${esc(ROLES[x.role]||'')}</em></li>`).join('')}</ol>`:''}`;
}
function foundTab(){
  const f=S.form||{},ok=S.found;
  const fee=CAT().fee||5_000_000,days=CAT().account_days||14;
  const tick=(on,label)=>`<li class="${on?'ok':'no'}"><span aria-hidden="true">${on?'✅':'⬜'}</span>${label}</li>`;
  const checks=ok?`<ul class="bg-checks">${tick(ok.days_ok,`Tài khoản đủ ${days} ngày${Number.isFinite(ok.age)?` (đang ${ok.age} ngày)`:''}`)}${tick(ready()>=fee,`Có ${fmt(fee)} xu (ví + ngân hàng)`)}</ul>`:'<p class="sd-empty">⏳</p>';
  const emojis=(CAT().emojis||[]).map(e=>`<button type="button" class="bg-emo${f.emoji===e?' on':''}" data-bg="emoji" data-e="${esc(e)}" aria-pressed="${f.emoji===e}">${esc(e)}</button>`).join('');
  const colors=Object.keys(COLORS).map(c=>`<button type="button" class="bg-sw${f.color===c?' on':''}" data-bg="color" data-c="${c}" style="--bgc:${hex(c)}" aria-label="${esc((CAT().colors||[]).find(x=>x.id===c)?.name||c)}" aria-pressed="${f.color===c}"></button>`).join('');
  const preview=`<div class="bg-preview">${crest(f.emoji,f.color,' big')}<b data-no-translate>${esc(f.name||'Tên bang')}</b>${f.motto?`<small data-no-translate>“${esc(f.motto)}”</small>`:''}</div>`;
  return `<section class="sd-card"><h3>⚔️ Lập bang mới</h3>${checks}</section>
    <section class="sd-card">${preview}
    <label class="bg-field"><span>Tên bang</span><input name="f-name" value="${esc(f.name||'')}" maxlength="${(CAT().name||[2,20])[1]}" autocomplete="off" placeholder="Ví dụ: Rồng Đỏ"></label>
    <div class="bg-field"><span>Biểu tượng</span><div class="bg-emos">${emojis}</div></div>
    <div class="bg-field"><span>Màu bang</span><div class="bg-sws">${colors}</div></div>
    <label class="bg-field"><span>Khẩu hiệu</span><input name="f-motto" value="${esc(f.motto||'')}" maxlength="${CAT().motto||60}" autocomplete="off" placeholder="Một câu ngắn"></label>
    <label class="sd-toggle"><input type="checkbox" name="f-open"${f.open?' checked':''}><span>Ai cũng vào được (tắt: cần duyệt)</span></label>
    <p class="tp-note">Phí ${fmt(fee)} xu không hoàn lại. Tên bang theo luật tên người chơi, không trùng.</p></section>`;
}
function foundFoot(){
  const ok=S.found,fee=CAT().fee||5_000_000,f=S.form||{};
  const why=!ok?'':!ok.account?'Cần đăng nhập':!ok.days_ok?`Tài khoản chưa đủ ${CAT().account_days||14} ngày`:ready()<fee?`Còn thiếu ${fmt(fee-ready())} xu`:String(f.name||'').trim().length<2?'Đặt tên bang':'';
  const label=S.arm==='found'?`Bấm lần nữa: trả ${fmt(fee)} xu`:`⚔️ Lập bang · ${fmt(fee)} xu`;
  return `<footer class="sd-bar">${why?`<small class="sd-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big sd-main" data-bg="found"${S.busy||why||!ok?' disabled':''}>${esc(label)}</button></footer>`;
}
function rankTab(){
  const b=S.view?.board||P()?.board;
  const mine=S.view?.mine?.bang;
  const data=b||S.view?.page?.board;
  if(!data)return `<p class="sd-empty">⏳</p>`;
  const top=data.top||[];
  const rows=top.length?`<ol class="sd-board bg-board">${top.map(x=>`<li class="${x.id===mine?'me':''}"><span>${x.rank===1?'🥇':x.rank===2?'🥈':x.rank===3?'🥉':x.rank}</span><b data-no-translate>${esc(x.emoji)} ${esc(x.name)}${data.crown===x.id?' 👑':''}</b><em>${fmt(x.score)}</em></li>`).join('')}</ol>`:'<p class="tp-note">Tuần này chưa bang nào có điểm.</p>';
  return `<section class="sd-card"><h3>👑 Bang mạnh nhất tuần</h3><p class="tp-note">Điểm = điểm cống hiến cả bang kiếm trong tuần + cấp công trình + 🛡️ Bang chiến pet. Bang đứng đầu: cả bang mang danh hiệu “👑 Bang mạnh nhất tuần” suốt tuần sau.</p>
    <p class="tp-line"><span>Tuần kết thúc sau <b data-bg-until="${data.ends}">${esc(left(data.ends-serverNow()))}</b></span></p>${rows}</section>`;
}
const roleIcon=r=>({chu:'👑',pho:'🛡️',lao:'📜',tinh:'⭐',tv:'👤'})[r]||'👤';
const MODES={closed:'🚫 Đóng',ask:'🔒 Cần duyệt',auto:'🚪 Tự động duyệt'};
const modeOf=c=>c?.mode||(c?.open?'auto':'ask');
const reqLine=c=>(c?.req||[]).length?`<small class="bg-req">📋 Yêu cầu: ${esc(c.req.join(' · '))}</small>`:'';
const joinLabel=c=>modeOf(c)==='auto'?'Vào':'Xin vào';
const ago=t=>{if(!t)return '';const d=Math.floor((serverNow()-t)/86400);return d<=0?'hôm nay':d===1?'hôm qua':`${d} ngày trước`;};
const dmy=t=>{const d=vnDate(t),y=d.getUTCFullYear();return `${String(d.getUTCDate()).padStart(2,'0')}/${String(d.getUTCMonth()+1).padStart(2,'0')}${y!==vnDate(serverNow()).getUTCFullYear()?'/'+y:''}`;};

/* -- 🏝️ Đảo bang (owner 21/10) -- */
const isleLevel=()=>Number(P()?.isle?.level??S.view?.mine?.isle??1);
const mil=n=>n>=1e6&&n%1e6===0?`${fmt(n/1e6)} triệu`:fmt(n);
/** Before the island is bought: what it is, its price, one button for an officer (members: ask one). */
function isleOffer(){
  const p=P(),i=p?.isle;if(!i||i.level)return '';
  const can=rank(p.me.role)>=4,cost=i.cost||1_000_000,short=Math.max(0,cost-(p.fund||0));
  const why=!can?'Nhờ Bang chủ hoặc Phó bang mua đảo nhé':short?`Quỹ bang thiếu ${fmt(short)} xu: góp quỹ ở dưới`:'';
  return `<section class="sd-card bg-isle bg-isle-offer"><div class="bg-isle-art" aria-hidden="true">🏝️</div><h3>Mua Đảo bang</h3>
    <p class="tp-note">Đảo riêng của cả bang: gặp nhau, 🐾 Đấu trường, 🛡️ Bang chiến pet. Nâng dần tới cấp ${i.max||5}.</p>
    <p class="tp-line"><span>💰 ${mil(cost)} xu</span><span>👥 ${i.next_cap||30} người</span><span>⚡ Có ngay</span></p>
    ${can?btn('isle',S.arm==='isle:1'?`Bấm lần nữa: dùng ${mil(cost)} xu quỹ`:`🏝️ Mua đảo · ${mil(cost)} xu`,` data-to="1"${why?' disabled':''}`,'btn primary big'):''}${why?`<small class="sd-why">${esc(why)}</small>`:''}</section>`;
}
/** The island's card (🏗️ first): its level, who fits, the zones, the upgrade being built or the next one. */
function isleCard(){
  const p=P(),i=p?.isle;if(!i)return '';
  if(!i.level)return isleOffer();
  const can=rank(p.me.role)>=4,pips=Array.from({length:i.max},(_,k)=>`<i class="${k<i.level?'on':''}${i.to&&k===i.level?' go':''}"></i>`).join('');
  let foot='';
  if(i.to){const total=Math.max(1,i.ready-i.started),done=Math.floor((serverNow()-i.started)*100/total);
    foot=`<p class="tp-stage">🚧 Đang mở rộng lên cấp ${i.to}: ${esc(i.next_zone||'')}</p>${bar(done,'build')}<p class="tp-line"><span>Còn <b data-bg-until="${i.ready}">${esc(left(i.ready-serverNow()))}</b></span></p>`;}
  else if(i.next){
    const why=!can?'Phó bang trở lên mới nâng đảo':p.fund<i.cost?`Quỹ thiếu ${fmt(i.cost-p.fund)} xu`:'';
    foot=`<p class="bg-next">Cấp ${i.next}: ${esc(i.next_zone||'')} · 👥 ${i.next_cap} người</p><div class="bg-buy"><span>💰 ${mil(i.cost)} xu · ⏳ ${esc(left(i.secs))}</span>${btn('isle',S.arm==='isle:'+i.next?'Bấm lần nữa':`Nâng lên cấp ${i.next}`,` data-to="${i.next}"${why?' disabled':''}`,'btn primary')}</div>${why?`<small class="sd-why">${esc(why)}</small>`:''}`;
  }else foot='<p class="bg-next">✨ Đảo đã ở cấp cao nhất</p>';
  return `<section class="sd-card bg-fac bg-isle${i.to?' building':''}"><div class="bg-fac-head"><span class="bg-fac-ico" aria-hidden="true">🏝️</span><div class="grow"><b>Đảo bang</b><small>Cấp ${i.level}/${i.max} · 👥 ${i.cap} người cùng lúc</small></div>${btn('island','Ra đảo','','btn cream sm')}</div><div class="bg-pips" aria-hidden="true">${pips}</div>
    <p class="tp-note bg-zones">${(i.zones||[]).map(z=>esc(z)).join(' · ')}</p>${foot}</section>`;
}

/* -- inside a bang -- */
function homeTab(){
  const p=P(),m=S.view.mine;if(!p)return '<p class="sd-empty">⏳</p>';
  const c=p.bang,me=p.me;
  const crown=p.crowned?`<p class="bg-crown">👑 Bang mạnh nhất tuần</p>`:'';
  const g=give(),all=most(),n=amount();
  const chips=(g.presets||[]).map(x=>`<button type="button" class="sd-chip${n===x?' on':''}" data-bg="amount" data-n="${x}" aria-pressed="${n===x}"${x>all?' disabled':''}>${mil(x).replace(' triệu','tr')}</button>`).join('')
    +`<button type="button" class="sd-chip${n===all&&all>=g.min?' on':''}" data-bg="amount" data-n="all"${all<g.min?' disabled':''}>Tất cả</button>`;
  const gold=m.golden?`<p class="bg-gold">⏰ Giờ vàng của bang đang diễn ra: lãi tiệm và quầy ×2, còn <b data-bg-until="${m.golden.ends}">${esc(left(m.golden.ends-serverNow()))}</b></p>`:'';
  const hero=`<section class="sd-card bg-hero" style="--bgc:${hex(c.color)}">${crown}${c.motto?`<p class="bg-motto" data-no-translate>“${esc(c.motto)}”</p>`:''}
    <p class="tp-line"><span>👥 ${c.n}/${c.cap}</span><span>${esc(MODES[modeOf(c)])}</span>${p.channel?btn('chat','💬 Chat bang',` data-ch="${esc(p.channel)}"`,'btn cream bg-chat'):''}${S.env?.api?.content?.bang_island&&isleLevel()?btn('island',`🏯 Đảo bang · cấp ${isleLevel()}`,'','btn cream bg-chat'):''}</p></section>`;
  const fund=`<section class="sd-card"><h3>💰 Quỹ bang</h3><div class="tp-money"><b>${fmt(p.fund)}</b><span>xu</span></div>
    <div class="sd-chips sd-amounts">${chips}<label class="tp-typed">${qtyBox({value:n,min:g.min,max:Math.max(g.min,all),step:g.min,money:true,label:'Góp bao nhiêu xu',go:`data-bg="amount" data-n="${QTY}"`})}<small>xu</small></label></div>
    <p class="tp-note">Góp bao nhiêu cũng được, chỉ góp không rút: quỹ dùng mua đảo và xây công trình bang. ${fmt(g.per_point||1000)} xu = 1 điểm cống hiến (tối đa ${fmt(g.day_pts||50000)} điểm/ngày).</p></section>`;
  const pts=`<section class="sd-card bg-pts"><h3>⭐ ${fmt(me.points)} điểm cống hiến</h3>${bar(Math.floor(me.today*100/Math.max(1,me.today_max)),'bg-today')}
    <p class="tp-note">Hôm nay ${me.today}/${me.today_max} điểm hoạt động: 📅 điểm danh +${CAT().points?.checkin||20}, mỗi ngày làm việc +${CAT().points?.work||10}. Điểm đổi đồ ở 🛍️.</p></section>`;
  return gold+isleOffer()+hero+fund+pts+goldenCard()+logCard();
}
function homeFoot(){
  const me=ME();if(!me)return '';
  if(!me.checkin)return `<footer class="sd-bar"><button type="button" class="btn primary big sd-main" data-bg="checkin"${S.busy?' disabled':''}>📅 Điểm danh +${CAT().points?.checkin||20} điểm</button></footer>`;
  const why=giveWhy();
  return `<footer class="sd-bar">${why?`<small class="sd-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big sd-main${S.arm==='give'?' tp-arm':''}" data-bg="give"${S.busy||why?' disabled':''}>${esc(giveLabel())}</button></footer>`;
}
function goldenCard(){
  const p=P(),g=p.golden||{},me=p.me,lv=p.levels||{};
  const list=(g.list||[]).map(w=>{const on=w.start<=serverNow();return `<li><span>${on?'🔥':'⏰'}</span><b>${esc(dayLabel(w.start))} ${hm(w.start)}–${hm(w.ends)}</b>${on?`<em>còn <i data-bg-until="${w.ends}">${esc(left(w.ends-serverNow()))}</i></em>`:rank(me.role)>=4?btn('ghCancel',S.arm==='ghc:'+w.id?'Bấm lần nữa để hủy':'Hủy',` data-id="${w.id}"`,'btn cream sm'):''}</li>`;}).join('');
  if(!lv.den_vang)return `<section class="sd-card"><h3>⏰ Giờ vàng của bang</h3><p class="tp-note">Xây ⏰ Đền vàng (🏗️) để bang chủ chọn giờ vàng riêng: lãi tiệm và quầy của cả bang ×2.</p></section>`;
  let picker='';
  if(rank(me.role)>=4){
    const st={...ghDefault(),...S.gh},days=[0,1,2,3,4,5,6].map(i=>`<button type="button" class="sd-chip${st.day===i?' on':''}" data-bg="ghDay" data-n="${i}" aria-pressed="${st.day===i}">${esc(dayLabel(serverNow()+i*86400))}</button>`).join('');
    const hours=Array.from({length:24},(_,h)=>`<option value="${h}"${st.h===h?' selected':''}>${String(h).padStart(2,'0')}</option>`).join('');
    const mins=Array.from({length:12},(_,i)=>i*5).map(m=>`<option value="${m}"${st.m===m?' selected':''}>${String(m).padStart(2,'0')}</option>`).join('');
    const t=ghStart(),soon=t<serverNow()+3600;
    picker=`<div class="sd-chips bg-days">${days}</div><div class="bg-time"><label>Giờ <select name="gh-h">${hours}</select></label><label>Phút <select name="gh-m">${mins}</select></label>${btn('ghSet','Đặt giờ vàng',soon?' disabled':'','btn primary')}</div>${soon?'<small class="sd-why">Đặt trước ít nhất 1 tiếng nhé.</small>':''}`;
  }
  return `<section class="sd-card"><h3>⏰ Giờ vàng của bang</h3><p class="tp-note">${g.per_week>=7?'Mỗi ngày 1 lần':`${g.per_week} lần mỗi tuần`}, ${g.minutes} phút: lãi tiệm và quầy ×2 cho cả bang (không cộng dồn với giờ vàng của phố).</p>
    ${list?`<ol class="bg-gh">${list}</ol>`:'<p class="tp-note">Chưa đặt giờ nào.</p>'}${picker}</section>`;
}
function logCard(){
  const log=P()?.log||[];if(!log.length)return '';
  return `<details class="sd-card bg-log"><summary>📜 Chuyện trong bang</summary><ul>${log.slice(0,12).map(x=>`<li data-no-translate>${esc(x.text)}</li>`).join('')}</ul></details>`;
}
function membersTab(){
  const p=P(),me=p?.me;if(!p)return '<p class="sd-empty">⏳</p>';
  const my=rank(me.role),mine=S.view.mine;
  const rows=p.members.map(x=>{
    const self=x.pid===mineP(),open=S.sel===x.pid&&!self;
    let acts='';
    if(open){
      const can=[];
      if(me.role==='chu'){
        for(const r of ['pho','lao','tinh','tv'])if(r!==x.role)can.push(btn('role',ROLES[r],` data-pid="${x.pid}" data-role="${r}"`,'btn cream sm'));
        can.push(btn('role',S.arm==='chu:'+x.pid?'Bấm lần nữa: trao chức':'👑 Trao Bang chủ',` data-pid="${x.pid}" data-role="chu"`,'btn cream sm'));
      }
      if(my>=4&&rank(x.role)<my)can.push(btn('kick',S.arm==='kick:'+x.pid?'Bấm lần nữa: mời ra':'Mời ra khỏi bang',` data-pid="${x.pid}"`,'btn ghost sm bg-kick'));
      acts=can.length?`<div class="bg-acts">${can.join('')}</div>`:'';
    }
    const sub=`${esc(ROLES[x.role]||'')} · vào ${esc(dmy(x.joined))}${x.last?` · ${esc(self?'đang chơi':'chơi '+ago(x.last))}`:''}`;
    return `<li class="${self?'me':''}${open?' open':''}"><button type="button" class="bg-mem" data-bg="sel" data-pid="${x.pid}"${self?' disabled':''}><span aria-hidden="true">${roleIcon(x.role)}</span><span class="grow bg-mem-who"><b data-no-translate>${esc(x.name)}</b><small>${sub}</small></span><em title="Tuần này / tổng">⭐ ${fmt(x.week)}<small>/${fmt(x.earned)}</small></em></button>${acts}</li>`;
  }).join('');
  const asks=(p.asks||[]).length?`<section class="sd-card"><h3>🙋 Xin vào bang (${p.asks.length})</h3>${p.asks.map(a=>`<div class="bg-row"><div class="grow"><b data-no-translate>${esc(a.name)}</b></div>${btn('approve','Nhận',` data-pid="${a.pid}"`,'btn primary')}${btn('approve','✕',` data-pid="${a.pid}" data-ok="0" aria-label="Từ chối"`,'btn cream')}</div>`).join('')}</section>`:'';
  let invite='';
  if(my>=3){
    const fr=(S.friends||[]).filter(f=>f.bang!==mine.bang).slice(0,12);
    invite=`<section class="sd-card"><h3>📨 Mời người vào bang</h3>${S.friends===null?'<p class="sd-empty">⏳</p>':fr.length?`<div class="bg-list">${fr.map(f=>`<div class="bg-row"><div class="grow"><b data-no-translate>${esc(f.name)}</b>${f.bang?'<small>đang ở bang khác</small>':''}</div>${btn('invite','Mời',` data-code="${esc(f.code)}"`,'btn cream')}</div>`).join('')}</div>`:'<p class="tp-note">Chưa có bạn bè để mời.</p>'}
      <div class="bg-code"><input name="bg-code" placeholder="PCC-XXXXXX" maxlength="10" autocomplete="off" autocapitalize="characters">${btn('invite','Mời')}</div></section>`;
  }
  const seats=['pho','lao','tinh'].map(r=>`${ROLES[r]} ${p.members.filter(x=>x.role===r).length}/${CAT().roles?.[r]?.seats||'∞'}`).join(' · ');
  const how=me.role==='chu'?'. Chạm một người để phong chức hoặc mời ra.':my>=4?'. Chạm một người dưới chức Phó bang để mời ra.':'';
  return asks+`<section class="sd-card"><h3>👥 ${p.members.length}/${p.bang.cap} thành viên</h3><p class="tp-note">${esc(seats)}${esc(how)}</p><ol class="bg-members">${rows}</ol><p class="tp-note">⭐ điểm cống hiến tuần này / tổng. Không ai mời ra được người cùng hoặc cao chức hơn.</p></section>`+invite;
}
const mineP=()=>P()?.me?.pid||S.view?.mine?.pid||'';
function buildTab(){
  const p=P();if(!p)return '<p class="sd-empty">⏳</p>';
  const can=rank(p.me.role)>=4,busy=p.facilities.filter(f=>f.building).length,cat=Object.fromEntries((CAT().facilities||[]).map(f=>[f.id,f]));
  const cards=p.facilities.map(f=>{
    const c=cat[f.id]||{},pips=Array.from({length:f.max},(_,i)=>`<i class="${i<f.level?'on':''}${f.building&&i===f.level?' go':''}"></i>`).join('');
    let foot='';
    if(f.building){const total=Math.max(1,f.ready-f.started),done=Math.floor((serverNow()-f.started)*100/total);
      foot=`<p class="tp-stage">🚧 Đang lên cấp ${f.building}</p>${bar(done,'build')}<p class="tp-line"><span>Còn <b data-bg-until="${f.ready}">${esc(left(f.ready-serverNow()))}</b></span></p>`;}
    else if(f.next){
      const why=!can?'Phó bang trở lên mới xây':(p.levels[ 'dai_sanh']<f.hall)?`Cần Đại sảnh cấp ${f.hall}`:isleLevel()<(f.isle||0)?`Cần 🏝️ Đảo bang cấp ${f.isle}`:busy>=p.slots?`Đang xây ${busy}/${p.slots} công trình`:p.fund<f.cost?`Quỹ thiếu ${fmt(f.cost-p.fund)} xu`:'';
      foot=`<p class="bg-next">Cấp ${f.next}: ${esc(f.next_perk)}</p><div class="bg-buy"><span>💰 ${fmt(f.cost)} xu · ⏳ ${esc(left(f.secs))}</span>${btn('build',S.arm==='build:'+f.id?'Bấm lần nữa':'Nâng cấp',` data-id="${f.id}"${why?' disabled':''}`,'btn primary')}</div>${why?`<small class="sd-why">${esc(why)}</small>`:''}`;
    }else foot='<p class="bg-next">✨ Cấp cao nhất</p>';
    return `<section class="sd-card bg-fac${f.building?' building':''}"><div class="bg-fac-head"><span class="bg-fac-ico" aria-hidden="true">${esc(c.emoji||'🏗️')}</span><div class="grow"><b>${esc(c.name||f.id)}</b><small>Cấp ${f.level}/${f.max} · ${esc(f.perk)}</small></div></div><div class="bg-pips" aria-hidden="true">${pips}</div>${foot}</section>`;
  }).join('');
  return `<p class="tp-note bg-top">💰 Quỹ ${fmt(p.fund)} xu · xây cùng lúc ${busy}/${p.slots}</p>`+isleCard()+cards;
}
function shopTab(){
  const p=P();if(!p)return '<p class="sd-empty">⏳</p>';
  const me=p.me,items=Object.fromEntries((CAT().items||[]).map(i=>[i.id,i])),fac=Object.fromEntries((CAT().facilities||[]).map(f=>[f.id,f]));
  const bits={ao:1,huy:2,co:4,thuyen:8};
  const rows=p.shop.map(s=>{
    const it=items[s.id]||{},owned=s.owned>0,worn=bits[s.id]&&(me.wear&bits[s.id]);
    let act='';
    if(!s.unlocked)act=`<small class="sd-why">Cần ${esc(fac[it.needs?.[0]]?.name||'')} cấp ${it.needs?.[1]}</small>`;
    else if(it.kind==='use'){act=`${owned?btn('fire',`🎆 Bắn (${s.owned})`,'','btn cream'):''}${btn('buy',`⭐ ${fmt(s.price)}`,` data-id="${s.id}"${me.points<s.price?' disabled':''}`,'btn primary')}`;}
    else if(owned)act=btn('wear',worn?'Cất':'Dùng',` data-id="${s.id}" data-on="${worn?0:1}"`,worn?'btn cream':'btn primary');
    else act=btn('buy',`⭐ ${fmt(s.price)}`,` data-id="${s.id}"${me.points<s.price?' disabled':''}`,'btn primary');
    let extra='';
    if(s.id==='ao'&&owned){const ok=S.view.mine.uniforms||['polo'];extra=`<div class="sd-chips bg-uni">${(CAT().uniforms||[]).map(u=>`<button type="button" class="sd-chip${me.uniform===u.id?' on':''}" data-bg="wear" data-id="ao" data-on="1" data-style="${u.id}"${ok.includes(u.id)?'':' disabled'} aria-pressed="${me.uniform===u.id}">${esc(u.name)}</button>`).join('')}</div>`;}
    return `<div class="bg-item${worn?' on':''}"><span class="sd-ico" aria-hidden="true">${esc(it.emoji||'🎁')}</span><div class="grow"><b>${esc(it.name||s.id)}</b><small>${esc(itemNote(s.id))}${worn?' · đang dùng':''}</small>${extra}</div><div class="bg-item-act">${act}</div></div>`;
  }).join('');
  const others=(S.view.items||[]).filter(x=>x.bang!==S.view.mine.bang);
  const old=others.length?`<section class="sd-card"><h3>🎒 Đồ của bang cũ</h3><p class="tp-note">Vẫn trong túi, chỉ dùng được khi quay lại bang đó.</p><ul class="bg-old">${others.map(x=>`<li>${esc(items[x.item]?.emoji||'')} ${esc(items[x.item]?.name||x.item)} · <span data-no-translate>${esc(x.bang_emoji)} ${esc(x.bang_name)}</span></li>`).join('')}</ul></section>`:'';
  return `<section class="sd-card"><h3>🛍️ Cửa hàng bang</h3><p class="tp-note">Chỉ đổi bằng ⭐ điểm cống hiến (bạn có ${fmt(me.points)}). Đồ bang chỉ dùng khi đang ở bang này.</p><div class="bg-items">${rows}</div></section>`+old;
}
function itemNote(id){
  return {ao:'Áo màu bang trên nhân vật',huy:'Biểu tượng bang trước tên',co:'Cờ bang treo trong nhà',thuyen:'Du thuyền sơn màu bang',phao:'Bắn pháo hoa cả phố thấy'}[id]||'';
}
function rulesCard(){
  const p=P(),c=p.bang,mode=modeOf(c),r=draft(),lad=S.ladder;
  const modes=Object.entries(MODES).map(([k,l])=>btn('mode',l,` data-mode="${k}" aria-pressed="${mode===k}"`,`sd-chip${mode===k?' on':''}`)).join('');
  const what={closed:'Không ai vào hay xin vào được; người được mời vẫn vào.',ask:'Người đủ yêu cầu gửi đơn, Trưởng lão trở lên duyệt.',auto:'Người đủ yêu cầu vào ngay, không cần duyệt.'}[mode];
  let form='<p class="sd-empty">⏳</p>';
  if(lad){
    const job=lad.find(x=>x.id===r.career);
    const careers=`<option value="">Không yêu cầu nghề</option>`+lad.map(x=>`<option value="${esc(x.id)}"${x.id===r.career?' selected':''}>${esc(x.name)}</option>`).join('');
    const titles=job?job.titles.map((t,i)=>`<option value="${i+1}"${r.rank===i+1?' selected':''}>Từ ${esc(t)} (bậc ${i+1})</option>`).join(''):'';
    const anyOpts=[0,1,2,3,4,5,6,7].map(n=>`<option value="${n}"${r.any===n?' selected':''}>${n?`Từ bậc ${n} ở nghề bất kỳ`:'Không yêu cầu'}</option>`).join('');
    form=`<label class="bg-field"><span>Nghề</span><select name="rq-career">${careers}</select></label>
      ${job?`<label class="bg-field"><span>Chức danh tối thiểu</span><select name="rq-rank">${titles}</select></label>`:''}
      <label class="bg-field"><span>Hoặc chức danh ở mọi nghề</span><select name="rq-any">${anyOpts}</select></label>
      <label class="bg-field"><span>Tuổi tài khoản tối thiểu (ngày)</span><input type="number" name="rq-days" min="0" max="365" inputmode="numeric" value="${r.days||0}"></label>
      <div class="bg-row">${btn('rulesSave','Lưu yêu cầu','','btn primary')}${(c.req||[]).length?btn('rulesClear','Bỏ hết yêu cầu','','btn cream'):''}</div>`;
  }
  return `<section class="sd-card bg-rules"><h3>🚪 Cách nhận người</h3><div class="sd-chips">${modes}</div><p class="tp-note">${esc(what)}</p>
    <h4 class="tp-h">📋 Yêu cầu (tùy chọn, áp dụng cùng lúc)</h4>${(c.req||[]).length?`<ul class="bg-reqs">${c.req.map(x=>`<li>📋 ${esc(x)}</li>`).join('')}</ul>`:'<p class="tp-note">Chưa có yêu cầu nào.</p>'}${form}
    <p class="tp-note">Đổi yêu cầu không mời ra người đã ở trong bang.</p></section>`;
}
function moreTab(){
  const p=P(),me=p?.me;if(!p)return '<p class="sd-empty">⏳</p>';
  const c=p.bang,lead=me.role==='chu';
  let set='';
  if(lead){
    const emojis=(CAT().emojis||[]).map(e=>`<button type="button" class="bg-emo${c.emoji===e?' on':''}" data-bg="emoji" data-e="${esc(e)}" aria-pressed="${c.emoji===e}">${esc(e)}</button>`).join('');
    const colors=Object.keys(COLORS).map(k=>`<button type="button" class="bg-sw${c.color===k?' on':''}" data-bg="color" data-c="${k}" style="--bgc:${hex(k)}" aria-label="${esc((CAT().colors||[]).find(x=>x.id===k)?.name||k)}" aria-pressed="${c.color===k}"></button>`).join('');
    set=`<section class="sd-card"><h3>⚙️ Cài đặt bang</h3>
      <div class="bg-field"><span>Biểu tượng</span><div class="bg-emos">${emojis}</div></div><div class="bg-field"><span>Màu bang</span><div class="bg-sws">${colors}</div></div>
      <div class="bg-code"><input name="bg-motto" value="${esc(c.motto||'')}" maxlength="${CAT().motto||60}" placeholder="Khẩu hiệu">${btn('motto','Lưu')}</div></section>
      <section class="sd-card bg-danger"><h3>Giải tán bang</h3><p class="tp-note">Quỹ ${fmt(p.fund)} xu bị đốt, không trả lại ai. Gõ đúng tên bang để giải tán.</p><div class="bg-code"><input name="bg-disband" placeholder="${esc(c.name)}" autocomplete="off">${btn('disband',S.arm==='disband'?'Bấm lần nữa':'Giải tán','','btn ghost bg-kick')}</div></section>`;
  }
  const rules=rank(me.role)>=4?rulesCard():(c.req||[]).length||modeOf(c)!=='auto'?`<section class="sd-card"><h3>🚪 Cách nhận người</h3><p>${esc(MODES[modeOf(c)])}</p>${reqLine(c)}</section>`:'';
  set=rules+set;
  const leave=lead?'<p class="tp-note">Bang chủ muốn rời: trao chức ở 👥 trước.</p>':`<section class="sd-card"><h3>Rời bang</h3><p class="tp-note">Điểm và đồ bang vẫn giữ nếu quay lại. Rời là mất danh hiệu ngay.</p>${btn('leave',S.arm==='leave'?'Bấm lần nữa để rời':'Rời bang','','btn ghost bg-kick')}</section>`;
  const tag=`<section class="sd-card"><h3>🏷️ Thẻ tên của bạn</h3><p>${chip({n:c.name,e:c.emoji,c:c.color,r:me.role,k:p.crowned?1:0},false)}</p><p class="tp-note">Hiện cạnh tên bạn trên bản đồ, trong chat và hồ sơ: ${esc(tagLine({n:c.name,e:c.emoji,c:c.color,r:me.role}))}.</p></section>`;
  return tag+set+leave;
}
