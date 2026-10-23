/** 🔎 Đổi nghề (owner 23/10: "mục đổi nghề/công việc nên cho người dùng search được nhé, và chọn được dễ hơn đi … nhiều
 * người k biết tại sao mình k đc chơi nghề này nghề kia nữa"): its own page in the home sheet (ui.jrView 'pick'), opened by
 * every "Đổi nghề" (the rail, the button by the shop name) and by "Công việc" on the 2.5D bar.
 * - one search box on top, no accents needed ("ban hoa" → Tiệm hoa, "cong an", "y ta"), the group and a few everyday
 *   words count too (KEYS); typing and the chips only show or hide rows already drawn (pickApply), 72 rows stay quick;
 * - chips: Tất cả · Làm được · Đã làm · Bị khóa, then the groups and 💰 Nhiều xu trước;
 * - the place you are at first, the last places worked next (journey.recent), then what you can start now, then the rest;
 * - a place you cannot pick or work says why on its card and, tapped, what opens it (lockOf: the server's own reason,
 *   journey.locks from game/career_locks.py; the plain chapter rule is said here in the same words, chapterLock). */
import {icon,escapeHTML as esc} from '../icons.js';
import {acctPlace,COURSE} from './acct-jobs.js';
import {foldVi,emojiOf,catOf,payOf,CATS} from './journey.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const colour=v=>/^#[0-9a-f]{3,8}$/i.test(v||'')?v:'#c44b30';
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const tag=(t,kind='')=>`<span class="tag ${kind}">${t}</span>`;
const meta=(api,cid)=>api.content.catalogue.find(m=>m.id===cid)||{id:cid,short:cid,place:cid};

/** Everyday words a player types for a career (already without accents), besides its name and group. */
export const KEYS={mother_baby:'me be so sinh do choi',pharmacy:'thuoc duoc si',accounting:'ke toan so sach',customer_care:'cskh tong dai cham soc khach',
  teacher:'giao vien co giao day hoc',tour_guide:'du lich huong dan vien',milk_tea:'tra sua tran chau',restaurant:'mi cay nha hang',cafe_bakery:'ca phe cafe banh ngot',
  florist:'ban hoa cam hoa',grocery:'tap hoa',repair:'sua do sua chua',farm:'nong trai rau ga nong dan',delivery:'shipper giao hang ship',homestay:'nha nghi phong',
  pet_care:'thu cung cho meo spa',salon:'cat toc toc',corp_accounting:'ke toan',tax_payroll:'ke toan thue luong',group_accounting:'ke toan tap doan',clothing:'quan ao thoi trang',
  pet_shop:'thu cung cho meo',tra_da:'tra da via he',fruit:'trai cay hoa qua',garbage:'rac ve sinh moi truong',drain:'cong ong cong',homemaker:'noi tro giup viec',
  ice_cream:'kem',nail:'nail mong',pagoda:'chua thay tu su',pho:'pho bo',com:'com tam',photobooth:'chup anh',giupviec:'giup viec don nha',naucom:'nau an dau bep',
  babysitter:'trong tre bao mau',library:'thu vien sach',pilot:'may bay phi cong',flight_attendant:'may bay tiep vien',oil:'dau khi gian khoan',hr_admin:'nhan su hanh chinh van phong',
  secretary:'thu ky van phong',it_helpdesk:'it may tinh cong nghe',railway:'duong sat tau hoa',nurse:'y ta dieu duong benh vien',lighthouse:'hai dang',rescue:'cuu ho 112 cap cuu',
  lifeguard:'ho boi boi loi cuu ho',police:'cong an canh sat',zpop:'album kpop nhac',art_studio:'ve tranh hoa si',lawyer:'luat su toa an',laundry:'giat ui giat do',
  post_office:'buu dien thu buu pham',customs:'hai quan',hotel:'khach san',banquet:'tiec cuoi nha hang',reception:'le tan khach san',teller:'ngan hang giao dich vien',
  restore:'phuc che do co',research:'nghien cuu khoa hoc',radio:'phat thanh mc',moto:'sua xe may',vet:'thu y bac si',kol:'tiktok youtube kol livestream',singer:'ca si hat',
  actor:'dien vien phim',tuning:'do xe',jewelry:'vang trang suc',car_dealer:'o to xe hoi ban xe',canteen:'can tin truong',stationery:'van phong pham but sach vo'};

/** The search key of a career: its place, what it is, its group, its id and its everyday words, without accents. */
export const keyOf=(m,cid)=>foldVi(`${m.place||''} ${m.short||''} ${CATS[catOf(m)]||''} ${cid} ${KEYS[cid]||''}`);

/** The chapter rule, in the very words of game/career_locks.py chapter_lock (its `t`, `how`, `act`). */
export function chapterLock(J,n,cid=''){
  const ch=J.chapter||1,goals=J.goals||[],done=goals.filter(g=>g.done).length,total=goals.length;
  if(!n||n<=ch)return {k:'chapter',t:'🔒 Chưa mở',how:'Nơi này chưa mở trong câu chuyện của bạn.'};
  const L=n===ch+1?{k:'chapter',t:`🔒 Xong chương ${ch} là mở`,how:`Làm xong việc cần làm của chương ${ch} (đã xong ${done}/${total}) là sang chương ${n} và mở nơi này.`}
    :{k:'chapter',t:`🔒 Mở ở chương ${n}`,how:`Mở khi tới chương ${n}; bạn đang ở chương ${ch} (đã xong ${done}/${total} việc cần làm). Xong việc cần làm của từng chương là đi tiếp.`};
  if(COURSE[cid])Object.assign(L,{how:`${L.how} Hoặc thi đạt chứng nhận “${COURSE[cid]}” ở Học kế toán để vào làm sớm.`,act:'accountingSchool'});   // 💼 the exam opens it early
  return L;
}
/** Why `cid` cannot be picked (or, soft, worked) now, or null: {k, t, how, act?, soft?}. The server's reason first
 * (journey.locks); else the chapter rule (not in journey.unlocked, the list journey.gate checks); else the exam of an
 * accounting place (an older server without locks). Outside the story every place is open. */
export function lockOf(api,cid){
  const J=api.state?.journey;if(!J?.story)return null;
  const L=J.locks?.[cid];if(L&&L.t)return L;
  if(!(J.unlocked||[]).includes(cid))return chapterLock(J,(api.content.journey?.unlock_chapter||{})[cid],cid);
  const a=acctPlace(api,cid);if(a&&!a.ok)return {k:'cert',t:'🔒 Cần thi chứng nhận',how:a.why,act:'accountingSchool'};
  return null;
}

/* ---------------------------------------------------------------- the plan: which rows show */
const FOLD={open:10,lock:6};   // a long section folds behind "Xem thêm" until a search or a chip
export const PICK_ST=[['','Tất cả'],['ok','Làm được'],['done','Đã làm'],['lock','Bị khóa']];
const stOK=(r,st)=>!st||(st==='ok'?r.ok:st==='done'?r.done:!r.ok);
/** rows [{k, sec, ok, done, cat}], f {q (folded), st, cat, more: {sec: true}} → {show: [bool], n: {sec: shown+folded},
 * more: {sec: folded}, total}. Every typed word must be in the key; whole words win ("pho" is Quán phở, not Văn phòng
 * phẩm), the words side by side first ("ban hoa"), else the start of a word, else anywhere. */
export function pickPlan(rows,f){
  const words=f.q?f.q.split(' '):[],n={},more={},seen={};
  const tests=[w=>k=>` ${k} `.includes(` ${w} `),w=>k=>` ${k}`.includes(` ${w}`),w=>k=>k.includes(w)];
  const chip=r=>stOK(r,f.st)&&(!f.cat||f.cat===r.cat);
  const phrase=words.length>1?[r=>` ${r.k} `.includes(` ${f.q} `)]:[];   // "ban hoa": Tiệm hoa (bán hoa), not Tạp hóa (buôn bán)
  const fit=[...phrase,...tests.map(t=>{const ts=words.map(t);return r=>ts.every(x=>x(r.k));})].find(ok=>rows.some(r=>chip(r)&&ok(r)))||(()=>!words.length);
  let total=0;
  const show=rows.map(r=>{
    if(!chip(r)||!fit(r))return false;
    n[r.sec]=(n[r.sec]||0)+1;total++;
    if(f.q||f.st||f.cat||f.more?.[r.sec]||!FOLD[r.sec]||(seen[r.sec]=(seen[r.sec]||0)+1)<=FOLD[r.sec])return true;
    more[r.sec]=(more[r.sec]||0)+1;return false;
  });
  return {show,n,more,total};
}
const filterOf=ui=>({q:foldVi(ui.cpQ),st:ui.cpSt||'',cat:ui.cpCat||'',more:ui.cpMore||{}});

/** Sections, in order: [id, title, ids]. Each career is in exactly one. */
export function pickSections(api,ui={}){
  const J=api.state.journey||{},cs=api.state.careers,cur=api.state.current;
  const all=api.content.catalogue.map(m=>m.id).filter(id=>cs[id]);
  const order=id=>(api.content.journey?.unlock_chapter||{})[id]||9,rank=id=>order(id)*1000+all.indexOf(id);
  const lock=Object.fromEntries(all.map(id=>[id,lockOf(api,id)]));
  const now=cur&&cs[cur]?[cur]:[];
  const recent=(J.recent||[]).filter(id=>id!==cur&&cs[id]?.started&&all.includes(id)).slice(0,3);
  const used=new Set([...now,...recent]),rest=all.filter(id=>!used.has(id));
  const open=rest.filter(id=>!lock[id]).sort((a,b)=>(!!cs[b].started-!!cs[a].started)||(cs[b].day||0)-(cs[a].day||0)||rank(a)-rank(b));
  if(ui.cpPay){const n=id=>payOf(api,id)?.n??-Infinity;open.sort((a,b)=>n(b)-n(a)||rank(a)-rank(b));}   // 💰 #406
  const shut=rest.filter(id=>lock[id]).sort((a,b)=>(!!lock[b].soft-!!lock[a].soft)||rank(a)-rank(b));   // opened but waiting first, then by chapter
  return {lock,secs:[['now','📍 Đang làm',now],['recent','🕘 Gần đây',recent],['open','✅ Làm được ngay',open],['lock','🔒 Chưa làm được',shut]]};
}

/* ---------------------------------------------------------------- the page */
const NEXT={chapter:['📋 Xem việc cần làm','jrView',{view:'home'}],customs:['📋 Xem việc cần làm','jrView',{view:'home'}],accountingSchool:['🎓 Đi học kế toán','accountingSchool',{}],abroad:['🌏 Làm việc ở nước ngoài','abroad',{}]};
/** The explanation under a card you cannot use now: what opens it, and the one or two buttons that help. */
function whyBox(api,cid,L){
  const go=[];
  const n=NEXT[L.act]||NEXT[L.k];if(n)go.push(btn(n[0],n[1],n[2],'cream small'));
  if(L.soft&&L.k!=='abroad')go.push(btn(`Vẫn ghé xem ${icon('arrow',13)}`,'choose',{career:cid},'ghost small'));
  return `<div class="cp-why" id="cp-why-${esc(cid)}" role="region" aria-label="${esc(`Vì sao chưa làm được ${meta(api,cid).place||cid}`)}" hidden><p>${esc(L.how||L.t)}</p>${go.length?`<div class="cp-why-go">${go.join('')}</div>`:''}</div>`;
}
function card(env,cid,sec,L,hidden){
  const {api}=env,J=api.state.journey||{},m=meta(api,cid),c=api.state.careers[cid],p=J.places?.[cid],job=c.job||{},cur=cid===api.state.current;
  const tags=[];
  if(!L){
    if(p?.paused)tags.push(tag('⏸ Tạm đóng · mở lại miễn phí','amber'));
    if(job.status==='offer')tags.push(tag('💌 Có thư mời','blue'));
    else if(job.required&&job.status!=='hired')tags.push(tag(`${icon('briefcase',12)} Xin việc trước khi làm`,'amber'));
    if(!c.started&&J.story&&(api.content.journey?.unlock_chapter||{})[cid]===J.chapter&&J.chapter>1)tags.push(tag('Mới mở','green'));
  }
  if(api.state.x3?.today?.includes(cid))tags.push(tag(`🔥 Lời x${api.state.x3.x} hôm nay`,'amber'));   // game/x3_week.py
  {const pay=payOf(api,cid);if(pay&&pay.n)tags.push(tag(esc(pay.text),'cp-pay'));}   // a first day that broke even says nothing
  const sub=[m.short||'',c.started?`Ngày ${c.day} · Cấp ${c.level||1}`:''].filter(Boolean).join(' · ');
  const go=L?`<span class="cp-go lock" aria-hidden="true">Vì sao?</span>`:`<span class="cp-go" aria-hidden="true">${p?.paused?'Mở lại':cur&&c.started?'Vào tiếp':c.started?'Vào làm':job.required&&job.status!=='hired'?'Xin việc':'Bắt đầu'} ${icon('arrow',13)}</span>`;
  const act=L?` data-action="jrPickWhy" data-career="${esc(cid)}" aria-expanded="false" aria-controls="cp-why-${esc(cid)}"`:p?.paused?` data-action="jrReopen" data-career="${esc(cid)}" data-go="1"`:` data-action="choose" data-career="${esc(cid)}"`;
  const label=[m.place||m.short,sub,L?L.t:'',cur?'nơi bạn đang làm':''].filter(Boolean).join(' · ');
  return `<li class="cp-item" data-k="${esc(keyOf(m,cid))}" data-sec="${sec}" data-ok="${L?0:1}" data-done="${c.started?1:0}" data-cat="${esc(catOf(m))}"${hidden?' hidden':''}>
    <button type="button" class="cp-card${L?' locked':''}${L?.soft?' soft':''}${cur?' current':''}"${act} aria-label="${esc(label)}" style="--career:${colour(m.color)}"><span class="cp-emoji" aria-hidden="true">${emojiOf(m)}</span>
    <span class="cp-text"><b>${esc(m.place||m.short)}</b><small>${esc(sub)}</small>${L?`<span class="cp-lock">${esc(L.t)}</span>`:''}${tags.length?`<span class="cp-tags">${tags.join('')}</span>`:''}</span>${go}</button>${L?whyBox(api,cid,L):''}</li>`;
}

export function pickView(env,{iso=false}={}){
  const {api,ui}=env,J=api.state.journey||{};wire(env);
  const {lock,secs}=pickSections(api,ui),f=filterOf(ui);
  const rows=secs.flatMap(([sec,,ids])=>ids.map(id=>({id,sec,k:keyOf(meta(api,id),id),ok:!lock[id],done:!!api.state.careers[id].started,cat:catOf(meta(api,id))})));
  const plan=pickPlan(rows,f),all=rows.length,ok=rows.filter(r=>r.ok).length;
  const count={'':all,ok,done:rows.filter(r=>r.done).length,lock:all-ok};
  const chip=(act,key,val,text,n,on)=>`<button type="button" class="chip ${on?'active':''}" data-action="${act}" data-${key}="${val}" aria-pressed="${on}">${text}${n==null?'':` <em>${n}</em>`}</button>`;
  const cats=Object.keys(CATS).filter(k=>rows.some(r=>r.cat===k));
  const st=PICK_ST.filter(([s])=>!s||count[s]).map(([s,l])=>chip('jrPickSt','st',s,l,count[s],(f.st||'')===s)).join('');
  const gr=chip('jrPickCat','cat','','Mọi nhóm',null,!f.cat)+cats.map(k=>chip('jrPickCat','cat',k,CATS[k],null,f.cat===k)).join('')+chip('jrPickPay','pay','1','💰 Nhiều xu trước',null,!!ui.cpPay);
  let i=0;
  const sec=([id,title,ids])=>{
    if(!ids.length)return '';
    const html=ids.map(cid=>card(env,cid,id,lock[cid],!plan.show[i++])).join(''),n=plan.n[id]||0,m=plan.more[id]||0;
    return `<section class="cp-sec" data-sec="${id}"${n?'':' hidden'}><h3>${title} <small class="cp-n">${n}</small></h3><ul class="cp-list" role="list">${html}</ul><button type="button" class="btn ghost small full cp-more" data-action="jrPickMore" data-sec="${id}"${m?'':' hidden'}>Xem thêm ${m} nơi</button></section>`;
  };
  const close=api.state.current||iso?btn(icon('x',20),'close',{},'ghost small cp-x'):'';
  const q=esc(ui.cpQ||'');
  // The title row scrolls away; the search under it stays on top (a phone's one-row header has no room for it).
  const head=`<header class="sheet-head cp-head"><div class="grow"><span class="eyebrow">Công việc</span><h2>Đổi nghề</h2><p>${ok}/${all} nơi làm được</p></div>${J.story?`<button type="button" class="btn cream small cp-jr" data-action="jrView" data-view="home" aria-label="Hành trình: việc cần làm của chương" title="Hành trình">🧭<span class="cp-word"> Hành trình</span></button>`:''}${close}</header>`;
  const bar=`<div class="cp-bar"><div class="cp-q" role="search"><label class="sr-only" for="cp-q">Tìm nghề</label>${icon('search',17)}<input id="cp-q" type="search" class="input" data-cp-q data-preserve enterkeyhint="search" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="Tìm nghề: phở, bán hoa, công an…" value="${q}" aria-describedby="cp-found"><button type="button" class="cp-clear" data-action="jrPickClear" aria-label="Xóa chữ đang tìm"${q?'':' hidden'}>${icon('x',16)}</button></div></div>`;
  return `${head}<div class="cp">${bar}
    <nav class="home-filters cp-chips" aria-label="Lọc theo tình trạng">${st}</nav><nav class="home-filters cp-chips cp-cats" aria-label="Nhóm nghề">${gr}</nav>
    <p class="cp-found" id="cp-found" aria-live="polite">${foundText(plan.total,f)}</p>
    ${secs.map(sec).join('')}
    <div class="cp-none"${plan.total?' hidden':''}><p>Không thấy nghề nào. Thử chữ khác hay bỏ bớt lọc nhé.</p>${btn('Bỏ lọc, xem tất cả','jrPickReset',{},'cream small')}</div>
    <p class="cp-foot muted">Đổi nghề không mất gì: quỹ, cấp và đồ ở từng nơi vẫn giữ nguyên.</p></div>`;
}
const foundText=(n,f)=>f.q||f.st||f.cat?`Thấy ${n} nơi`:'';

/** The rows on screen follow the plan: hidden rows, each section's count and "Xem thêm", the found line, the empty box. */
export function pickApply(root,ui){
  const box=root?.querySelector?.('.cp');if(!box)return;
  const els=[...box.querySelectorAll('.cp-item')],f=filterOf(ui);
  const p=pickPlan(els.map(e=>({k:e.dataset.k||'',sec:e.dataset.sec,ok:e.dataset.ok==='1',done:e.dataset.done==='1',cat:e.dataset.cat})),f);
  els.forEach((e,i)=>{if(e.hidden===p.show[i])e.hidden=!p.show[i];});
  for(const s of box.querySelectorAll('.cp-sec')){const id=s.dataset.sec,n=p.n[id]||0,m=p.more[id]||0;
    s.hidden=!n;const c=s.querySelector('.cp-n');if(c)c.textContent=n;
    const b=s.querySelector('.cp-more');if(b){b.hidden=!m;b.textContent=`Xem thêm ${m} nơi`;}}
  const none=box.querySelector('.cp-none');if(none)none.hidden=p.total>0;
  const found=box.querySelector('.cp-found');if(found)found.textContent=foundText(p.total,f);
  const clear=root.querySelector('.cp-clear');if(clear)clear.hidden=!ui.cpQ;
}
function syncChips(root,ui){
  for(const c of root?.querySelectorAll?.('.cp-chips .chip')||[]){
    if(c.dataset.action==='jrPickPay')continue;
    const on=c.dataset.action==='jrPickSt'?(c.dataset.st||'')===(ui.cpSt||''):(c.dataset.cat||'')===(ui.cpCat||'');
    c.classList.toggle('active',on);c.setAttribute('aria-pressed',String(on));
  }
}

let wired=false;
function wire(env){
  if(wired||typeof document==='undefined'||!document.addEventListener)return;wired=true;
  document.addEventListener('input',e=>{const t=e.target;if(!t?.matches?.('input[data-cp-q]'))return;
    env.ui.cpQ=t.value;env.ui.cpMore={};pickApply(document.getElementById('sheet'),env.ui);});
  // Enter: to the first card shown (the keyboard goes away on a phone); Escape: the search is cleared first.
  document.addEventListener('keydown',e=>{const t=e.target;if(!t?.matches?.('input[data-cp-q]'))return;
    if(e.key==='Enter'){e.preventDefault();document.querySelector('#sheet .cp-item:not([hidden]) .cp-card')?.focus();}
    else if(e.key==='Escape'&&t.value){e.preventDefault();e.stopPropagation();t.value='';env.ui.cpQ='';pickApply(document.getElementById('sheet'),env.ui);}
  },true);
}

/** Open the page (fresh search and chips) from anywhere: the sheet if it is open, else a new one. */
export function openPick(env,{iso=false}={}){
  const {ui}=env;wire(env);
  Object.assign(ui,{homeMode:'list',jrView:'pick',cpQ:'',cpSt:'',cpCat:'',cpMore:{}});
  if(iso)ui.isoTab='isoCareers';
  if(ui.view==='home'&&document.getElementById('sheet')?.open){env.renderSheet(false);document.getElementById('sheet')?.scrollTo?.(0,0);}
  else env.openSheet('home',{homeMode:'list',jrView:'pick'});
}

/** jrPick* actions (journey.js journeyAction hands them here). */
export function pickAction(action,data,el,env){
  const {ui}=env,sheet=document.getElementById('sheet');wire(env);
  switch(action){
    case'jrPick':openPick(env);return true;
    case'jrPickSt':ui.cpSt=data.st||'';ui.cpMore={};syncChips(sheet,ui);pickApply(sheet,ui);return true;
    case'jrPickCat':ui.cpCat=data.cat&&ui.cpCat!==data.cat?data.cat:'';ui.cpMore={};syncChips(sheet,ui);pickApply(sheet,ui);return true;
    case'jrPickMore':ui.cpMore={...(ui.cpMore||{}),[data.sec]:true};pickApply(sheet,ui);return true;
    case'jrPickPay':ui.cpPay=!ui.cpPay;ui.cpMore={};env.renderSheet(false);return true;
    case'jrPickClear':case'jrPickReset':{
      ui.cpQ='';if(action==='jrPickReset'){ui.cpSt=ui.cpCat='';syncChips(sheet,ui);}ui.cpMore={};
      const q=sheet?.querySelector('input[data-cp-q]');if(q){q.value='';if(action==='jrPickClear')q.focus();}
      pickApply(sheet,ui);return true;}
    case'jrPickWhy':{   // one explanation open at a time; its card says open or closed
      const card=el?.closest?.('.cp-card')||el,box=sheet?.querySelector(`#cp-why-${CSS.escape(data.career||'')}`);if(!box)return true;
      const open=box.hidden;
      for(const b of sheet.querySelectorAll('.cp-why:not([hidden])')){b.hidden=true;sheet.querySelector(`[aria-controls="${b.id}"]`)?.setAttribute('aria-expanded','false');}
      box.hidden=!open;card?.setAttribute?.('aria-expanded',String(open));
      if(open)box.scrollIntoView?.({block:'nearest',behavior:'smooth'});
      return true;}
  }
  return false;
}
