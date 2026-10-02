/** "📖 Hướng dẫn": the guide hub, in its own dialog (the work screen underneath stays as it was).
 *
 * Two tabs:
 * - "Hướng dẫn chơi" (tab id `play`): the game as a whole, short topics in groups (Bắt đầu, Hành trình,
 *   Xin việc, Tiền…), each a collapsible card with icons, an illustration where there is one and a
 *   button that opens the real screen;
 * - "Hướng dẫn nghề" (tab id `work`): one workplace at a time (defaults to the current one): its jobs,
 *   the steps with the real button names, what earns 5★, common mistakes and what they cost,
 *   restocking, surprises; plus the illustrated screenshot steps where the workplace has them.
 * A search box looks through both. "❓ Hỏi nhanh" (QUICK) sits first on "Hướng dẫn chơi": the questions players
 * ask most, 1–3 short lines each and a button that only opens the screen (the player does the step).
 *
 * Words come from the server catalogue (`api.content.guide`, game/guide_content.py); the screenshots
 * and their marks from ./guide-data.js. `[[Nút]]` in a line is a real button name, drawn as a chip.
 * Each line goes through the English pack whole (with its [[ ]] marks) before the marks become chips. */
import {OVERVIEW,CAREERS as SHOTS,IMG} from './guide-data.js';
import {dayArt} from './art.js';
import {t as tr} from '../v4/i18n.js';

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const X='<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';
const ART={day:dayArt};
let view={tab:'play',career:null,page:null,q:'',open:'',sec:''},ENV=null;

/** One mark: a dot on the control, an arrow, and a numbered badge placed
 * towards the middle of the picture (so it never falls off the edge). */
const DIRS={ne:[1,-1],nw:[-1,-1],se:[1,1],sw:[-1,1]};
function mark([x,y,n,dir],finger){
  const pulse='<circle class="tut-mark-pulse" r="12"/><circle class="tut-mark-dot" r="7"/>';
  // A lone mark: a finger tapping from below (from above near the bottom edge).
  if(finger)return `<svg class="tut-mark" style="--x:${x}%;--y:${y}%" viewBox="-60 -60 120 120" width="120" height="120" aria-hidden="true">${pulse}${y>72?'<text class="tut-mark-finger" x="-4" y="-12">👇</text>':'<text class="tut-mark-finger" x="-4" y="40">👆</text>'}</svg>`;
  const [sx,sy]=DIRS[dir]||[x<55?1:-1,y<45?1:-1],bx=sx*38,by=sy*32,L=Math.hypot(bx,by),ux=bx/L,uy=by/L;
  const P=k=>`${(ux*k).toFixed(1)},${(uy*k).toFixed(1)}`,px=-uy*5,py=ux*5,base=[ux*20,uy*20];
  const head=`${P(11)} ${(base[0]+px).toFixed(1)},${(base[1]+py).toFixed(1)} ${(base[0]-px).toFixed(1)},${(base[1]-py).toFixed(1)}`;
  return `<svg class="tut-mark" style="--x:${x}%;--y:${y}%" viewBox="-60 -60 120 120" width="120" height="120" aria-hidden="true">${pulse}`+
    `<polyline class="tut-mark-halo" points="${P(L-14)} ${P(18)}"/><polyline class="tut-mark-line" points="${P(L-14)} ${P(18)}"/><polygon class="tut-mark-head" points="${head}"/>`+
    `<g transform="translate(${bx} ${by})"><circle class="tut-mark-badge" r="13"/><text class="tut-mark-n" dy="5">${n}</text></g></svg>`;
}
/** A screenshot with its marks (percent coordinates). `finger`: a lone mark shows 👆 instead of "1". */
export function figure(p,alt='',{finger=false}={}){
  if(!p)return '';
  const one=finger&&p.marks?.length===1;
  const marks=(p.marks||[]).map(m=>mark(m,one)).join('');
  return `<figure class="tut-fig" style="--ratio:${p.w}/${p.h}"><img src="${IMG}${p.img}" width="${p.w}" height="${p.h}" alt="${esc(alt)}" loading="lazy" decoding="async">${marks}</figure>`;
}

/* ------------------------------------------------------------ data + text */
// The words (game/guide_content.py → ./guide-content.js) load the first time the hub opens.
let DATA=null,loading=null;
function loadData(){
  loading??=import('./guide-content.js').then(m=>{DATA=m.default||null;}).catch(error=>{console.error('guide:',error);DATA=false;});
  return loading;
}
const data=()=>DATA||null;
/** Workplaces that exist in this game (a guide written ahead for a place still being built stays hidden). */
function careerIds(){
  const g=data();if(!g)return Object.keys(SHOTS);
  const api=ENV?.api,known=new Set([...(api?.content?.catalogue||[]).map(c=>c.id),...Object.keys(api?.state?.careers||{})]);
  return (g.order||Object.keys(g.careers||{})).filter(id=>g.careers?.[id]&&(!known.size||known.has(id)));
}
const entry=id=>data()?.careers?.[id]||null;
const current=()=>ENV?.api?.state?.current||ENV?.api?.state?.focus||null;
/** A guide line: translated whole (English mode), then [[Nút]] → a button-name chip. */
function line(s){
  const text=esc(tr(String(s??'')));
  return text.replace(/\[\[(.+?)\]\]/g,'<b class="gh-btn">$1</b>');
}
const L=(tag,s,cls='')=>`<${tag}${cls?` class="${cls}"`:''} data-no-translate>${line(s)}</${tag}>`;
/** Search key: lower case, no diacritics, đ → d, [[ ]] dropped. */
const fold=s=>String(s??'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/g,'d').replace(/\[\[|\]\]/g,'');

/* ------------------------------------------------------------ Hướng dẫn chơi */
function topicCard(topic,{open=false}={}){
  const ov=topic.pic&&OVERVIEW.find(o=>o.id===topic.pic);
  const pic=ov?(ov.art&&ART[ov.art]?ART[ov.art]():'')+(ov.pic?figure(ov.pic,topic.title):''):'';
  const go=topic.go&&!topic.stub?`<button type="button" class="btn small gh-go" data-gh-go data-action="${esc(topic.go.action)}"${Object.entries(topic.go.data||{}).map(([k,v])=>` data-${esc(k)}="${esc(v)}"`).join('')}>${esc(topic.go.label||'Mở')} →</button>`:'';
  return `<details class="gh-topic${topic.stub?' stub':''}" id="gh-t-${esc(topic.id)}"${open?' open':''}><summary><span class="gh-ico" aria-hidden="true">${topic.emoji||'•'}</span><span class="grow">${esc(topic.title)}</span>${topic.stub?'<em class="gh-soon">Sắp có</em>':''}</summary>`+
    `<div class="gh-topic-body">${pic}<ul class="gh-points">${(topic.points||[]).map(p=>L('li',p)).join('')}</ul>${go}</div></details>`;
}
/** "❓ Hỏi nhanh": one folded card per question. Its button opens the screen (an app data-action) or the
 * "Hướng dẫn nghề" section of the workplace in hand; a menu-only screen (`nav`, e.g. Lịch cưới while weddings
 * are off) shows no button when the menu has no such entry. */
function quickGo(go){
  if(!go)return '';
  if(go.sec)return `<button type="button" class="btn small gh-go" data-tut-career="${esc(current()||'')}" data-gh-sec="${esc(go.sec)}">${esc(go.label||'Xem')} →</button>`;
  if(go.nav&&!document.querySelector(`#rail [data-action="${CSS.escape(go.action)}"]`))return '';
  return `<button type="button" class="btn small gh-go" data-gh-go data-action="${esc(go.action)}"${Object.entries(go.data||{}).map(([k,v])=>` data-${esc(k)}="${esc(v)}"`).join('')}>${esc(go.label||'Mở')} →</button>`;
}
function quickCard(x,{open=false}={}){
  return `<details class="gh-topic gh-qa" id="gh-q-${esc(x.id)}"${open?' open':''}><summary><span class="gh-ico" aria-hidden="true">${x.emoji||'❓'}</span>${L('span',x.q,'grow')}</summary>`+
    `<div class="gh-topic-body"><ul class="gh-points">${(x.a||[]).map(p=>L('li',p)).join('')}</ul>${quickGo(x.go)}</div></details>`;
}
function quickSection(){
  const rows=data()?.quick||[];
  if(!rows.length)return '';
  return `<section class="gh-quick" id="gh-quick" aria-labelledby="gh-quick-h"><h3 class="gh-faq-title" id="gh-quick-h"><span aria-hidden="true">❓</span> Hỏi nhanh</h3>${rows.map(x=>quickCard(x,{open:view.open===x.id})).join('')}</section>`;
}
function playTab(){
  const g=data();
  const replay=`<button type="button" class="btn primary full tut-replay" data-action="tutReplay">▶ Xem lại hướng dẫn (1 phút)</button>`;
  if(!g?.groups?.length){
    // Old catalogue (no guide words yet): the three illustrated cards.
    const cards=OVERVIEW.map((c,i)=>`<article class="tut-card"><header><span class="tut-card-n" aria-hidden="true">${i+1}</span><h3><span aria-hidden="true">${c.emoji}</span> ${esc(c.title)}</h3></header>`+
      `${c.art?ART[c.art]():''}${c.pic?figure(c.pic,c.title):''}<ul class="tut-points">${c.points.map(([n,t])=>`<li>${n?`<b class="tut-pn" aria-hidden="true">${n}</b>`:'<i class="tut-pn dot" aria-hidden="true"></i>'}${esc(t)}</li>`).join('')}</ul></article>`).join('');
    return replay+`<div class="tut-cards">${cards}</div>`;
  }
  // Top level: a few big parts (Bắt đầu, Tiền bạc, Việc làm, Các nghề…), each holding one or more topic groups.
  const byId=Object.fromEntries(g.groups.map(gr=>[gr.id,gr]));
  const parts=(g.index?.length?g.index:g.groups.map(gr=>({id:gr.id,emoji:gr.emoji,title:gr.title,groups:[gr.id]})));
  const toc=`<nav class="gh-toc" aria-label="Mục lục">${g.quick?.length?'<button type="button" class="chip" data-gh-jump="gh-quick"><span aria-hidden="true">❓</span> Hỏi nhanh</button>':''}${parts.map(pt=>`<button type="button" class="chip" ${pt.tab?`data-tut-tab="${esc(pt.tab)}"`:`data-gh-jump="gh-p-${esc(pt.id)}"`}><span aria-hidden="true">${pt.emoji}</span> ${esc(pt.title)}</button>`).join('')}</nav>`;
  const topics=Object.fromEntries(g.groups.flatMap(gr=>gr.topics.map(tp=>[tp.id,tp])));
  const faq=(g.faq||[]).map(id=>topics[id]).filter(Boolean);
  const ask=faq.length?`<section class="gh-faq" aria-labelledby="gh-faq-h"><h3 class="gh-faq-title" id="gh-faq-h"><span aria-hidden="true">❓</span> Hay được hỏi</h3>${faq.map(tp=>`<button type="button" class="gh-faq-q" data-gh-topic="${esc(tp.id)}"><span class="gh-ico" aria-hidden="true">${tp.emoji||'•'}</span><span class="grow">${esc(tp.title)}</span><span aria-hidden="true">→</span></button>`).join('')}</section>`:'';
  const group=(gr,sub)=>`<section class="gh-group" id="gh-g-${esc(gr.id)}">${sub?`<h4 class="gh-group-sub"><span aria-hidden="true">${gr.emoji}</span> ${esc(gr.title)}</h4>`:''}${gr.topics.map(tp=>topicCard(tp,{open:view.open===tp.id})).join('')}</section>`;
  const careers=()=>`<div class="gh-pick gh-all">${careerIds().map(id=>{const e=entry(id)||SHOTS[id]||{};return `<button type="button" class="chip" data-tut-career="${esc(id)}"><span aria-hidden="true">${e.emoji||'💼'}</span> ${esc(e.name||id)}</button>`;}).join('')}</div>`;
  const body=parts.map(pt=>{
    const grs=(pt.groups||[]).map(id=>byId[id]).filter(Boolean);
    const inner=pt.tab==='work'?`<p class="gh-part-lead">Chọn một nghề để xem cách làm từng việc, lỗi hay gặp, nhập hàng và mẹo được 5★.</p>${careers()}`:grs.map(gr=>group(gr,grs.length>1)).join('');
    return inner?`<section class="gh-part" id="gh-p-${esc(pt.id)}"><h3 class="gh-part-title"><span aria-hidden="true">${pt.emoji}</span> ${esc(pt.title)}</h3>${inner}</section>`:'';
  }).join('');
  return replay+toc+quickSection()+ask+body;
}

/* ------------------------------------------------------------ Hướng dẫn nghề */
const SECTIONS=[
  ['jobs','🧰','Công việc chính'],
  ['steps','👣','Các bước làm một việc'],
  ['stars','⭐','Mẹo được 5★'],
  ['mistakes','⚠️','Lỗi hay gặp & hậu quả'],
  ['prep','📦','Nhập hàng / chuẩn bị'],
  ['surprises','🎲','Tình huống bất ngờ'],
];
function sectionBody(key,e){
  const rows=e[key]||[];
  if(key==='jobs')return `<ul class="gh-jobs">${rows.map(j=>`<li><span class="gh-ico" aria-hidden="true">${j.emoji||'•'}</span><div>${L('b',j.name)}${L('p',j.how)}</div></li>`).join('')}</ul>`;
  if(key==='steps')return `<ol class="gh-steps">${rows.map((s,i)=>`<li><span class="tut-step-n" aria-hidden="true">${i+1}</span>${L('p',s)}</li>`).join('')}</ol>`;
  if(key==='mistakes')return `<ul class="gh-mistakes">${rows.map(m=>`<li>${L('b','❌ '+m.bad)}${L('p','→ '+m.result)}</li>`).join('')}</ul>`;
  return `<ul class="gh-points">${rows.map(p=>L('li',p)).join('')}</ul>`;
}
function section([key,emoji,title],e,open){
  if(!(e[key]||[]).length)return '';
  return `<details class="gh-sec" data-sec="${key}"${open?' open':''}><summary><span class="gh-ico" aria-hidden="true">${emoji}</span><span class="grow">${esc(title)}</span><small class="gh-count">${(e[key]||[]).length}</small></summary>${sectionBody(key,e)}</details>`;
}
/** The illustrated screenshot steps (guide-data.js), with extra pages as chips. */
function shots(cid){
  const c=SHOTS[cid];if(!c)return '';
  const pages=c.pages||[],page=pages.find(p=>p.id===view.page)||null;
  const sub=pages.length?`<div class="chip-row tut-chips tut-pages" role="tablist" aria-label="Trang">${[{id:'',emoji:c.emoji,name:c.main||'Bán hàng'},...pages].map(p=>{const on=(page?.id||'')===p.id;
    return `<button type="button" role="tab" class="chip${on?' selected':''}" aria-selected="${on}" data-tut-page="${esc(p.id)}"><span aria-hidden="true">${p.emoji}</span> ${esc(p.name)}</button>`;}).join('')}</div>`:'';
  const steps=(page||c).steps.map((s,i)=>`<li class="tut-step"><div class="tut-step-head"><span class="tut-step-n" aria-hidden="true">${i+1}</span><p>${esc(s.text)}</p></div>${figure(s,s.text,{finger:true})}</li>`).join('');
  return `<details class="gh-sec gh-shots" data-sec="shots"${view.page?' open':''}><summary><span class="gh-ico" aria-hidden="true">📸</span><span class="grow">Xem ảnh từng bước</span></summary>${sub}<ol class="tut-steps">${steps}</ol></details>`;
}
function pickerRow(cid){
  const ids=careerIds(),cur=current(),first=ids.includes(cur)?[cur,...ids.filter(x=>x!==cur)]:ids;
  return `<div class="gh-pick" role="tablist" aria-label="Chọn nghề">${first.map(id=>{const e=entry(id)||SHOTS[id]||{};const on=id===cid;
    return `<button type="button" role="tab" class="chip${on?' selected':''}" aria-selected="${on}" data-tut-career="${esc(id)}"><span aria-hidden="true">${e.emoji||'💼'}</span> ${esc(e.name||id)}${id===cur?' <small>· đang làm</small>':''}</button>`;}).join('')}</div>`;
}
/** Any workplace without words yet: the same rhythm everywhere. */
function generic(){
  const rows=['🙋 Chọn việc đang chờ','👆 Bấm nút nổi bật','✅ Kiểm rồi bàn giao','🌙 Hết việc: Khép ca'];
  return `<ol class="tut-steps plain">${rows.map((r,i)=>`<li class="tut-step"><div class="tut-step-head"><span class="tut-step-n" aria-hidden="true">${i+1}</span><p>${esc(r)}</p></div></li>`).join('')}</ol>`;
}
function workTab(){
  const ids=careerIds(),cid=ids.includes(view.career)?view.career:(ids.includes(current())?current():ids[0]);
  if(data())view.career=cid;   // while the words load, keep the asked workplace (only a few have pictures to show meanwhile)
  const e=entry(cid);
  if(!e)return pickerRow(cid)+(SHOTS[cid]?shots(cid).replace('<details class="gh-sec gh-shots" data-sec="shots"','<details class="gh-sec gh-shots" data-sec="shots" open'):generic());
  const head=`<header class="gh-career"><span class="gh-career-ico" aria-hidden="true">${e.emoji||'💼'}</span><div class="grow"><h3>${esc(e.name)}</h3>${e.place?`<small>${esc(e.place)}</small>`:''}</div>${cid===current()?'<em class="gh-now">Đang làm</em>':''}</header>${e.intro?L('p',e.intro,'gh-intro'):''}`;
  if(e.stub)return pickerRow(cid)+head+`<p class="notice gh-stub">🚧 Hướng dẫn chi tiết nghề này đang được viết. Tạm thời làm theo nhịp chung:</p>`+generic();
  // Open at first: the steps, and the job list when it is short (a long one stays folded).
  const body=SECTIONS.map(s=>section(s,e,view.sec?s[0]===view.sec:!view.page&&(s[0]==='steps'||s[0]==='jobs'&&(e.jobs||[]).length<=6))).join('');
  return pickerRow(cid)+head+body+shots(cid);
}

/* ------------------------------------------------------------ search */
function search(q){
  const g=data(),k=fold(q).trim();
  if(!g||k.length<2)return '';
  // Typed with accents ("thối"): match accents too, so "thời" is not a hit; typed without: match loosely.
  const exact=fold(q)!==q.toLowerCase().replace(/\[\[|\]\]/g,''),norm=s=>exact?String(s??'').toLowerCase().normalize('NFC'):fold(s);
  const words=norm(q).trim().split(/\s+/).filter(Boolean),hit=s=>{const f=norm(s);return words.every(w=>f.includes(w));};
  // Topics whose title matches come first ("rút tiền" → "Rút tiền về ví thế nào?"), then the other hits.
  const top=[],out=[];
  for(const x of g.quick||[])if(hit([x.q,...(x.a||[])].join(' ')))top.push(quickCard(x,{open:true}));
  for(const gr of g.groups||[])for(const tp of gr.topics||[])
    if(hit(tp.title))top.push(topicCard(tp,{open:true}));
    else if(hit([tp.title,...(tp.points||[])].join(' ')))out.push(topicCard(tp,{open:true}));
  out.unshift(...top);
  for(const id of careerIds()){
    const e=entry(id);if(!e||e.stub)continue;
    for(const s of SECTIONS){
      const rows=e[s[0]]||[];if(!rows.length)continue;
      const text=[e.name,s[2],...rows.map(r=>typeof r==='string'?r:Object.values(r).join(' '))].join(' ');
      if(hit(text))out.push(`<div class="gh-hit"><button type="button" class="gh-hit-head" data-tut-career="${esc(id)}" data-gh-sec="${s[0]}"><span aria-hidden="true">${e.emoji}</span> ${esc(e.name)} · ${esc(s[2])} →</button></div>`);
    }
  }
  if(!out.length)return `<p class="muted gh-none">Không thấy mục nào có “${esc(q)}”. Thử một từ khác, ví dụ: rút tiền, thối tiền, nhập hàng.</p>`;
  return `<p class="muted small gh-count-line">${out.length>30?'30+':out.length} mục</p>`+out.slice(0,30).join('');
}

/* ------------------------------------------------------------ dialog */
function html(){
  const tabs=[['play','📘','Hướng dẫn chơi'],['work','💼','Hướng dẫn nghề']];
  const nav=`<nav class="pill-tabs tut-tabs" role="tablist">${tabs.map(([id,em,l])=>`<button type="button" role="tab" aria-selected="${view.tab===id&&!view.q}" class="${view.tab===id&&!view.q?'active':''}" data-tut-tab="${id}"><span aria-hidden="true">${em}</span> ${l}</button>`).join('')}</nav>`;
  const box=data()?`<label class="gh-search"><span aria-hidden="true">🔎</span><input type="search" data-gh-q placeholder="Tìm: rút tiền, thối tiền, nhập hàng…" aria-label="Tìm trong hướng dẫn" value="${esc(view.q)}" autocomplete="off" enterkeyhint="search"></label>`:'';
  const body=view.q&&fold(view.q).trim().length>=2?search(view.q):view.tab==='work'?workTab():playTab();
  return `<header class="sheet-head"><div class="grow"><span class="eyebrow">📖 HƯỚNG DẪN</span><h2>${view.tab==='work'?'Hướng dẫn nghề':'Hướng dẫn chơi'}</h2></div><button class="icon-btn" type="button" data-tut-close aria-label="Đóng">${X}</button></header>`+
    `<div class="sheet-body tut-guide-body gh-hub">${nav}${box}<div class="gh-main">${body}</div></div>`;
}

function dialog(){
  let d=document.getElementById('tutGuide');
  if(d)return d;
  d=document.createElement('dialog');d.id='tutGuide';d.className='sheet medium tut-guide';d.setAttribute('aria-label','Hướng dẫn');
  d.innerHTML='<div class="tut-guide-inner"></div>';document.body.append(d);
  d.addEventListener('click',e=>{
    const t=e.target;
    if(t===d){d.close();return;}   // tap on the backdrop
    const tab=t.closest('[data-tut-tab]'),car=t.closest('[data-tut-career]'),page=t.closest('[data-tut-page]'),jump=t.closest('[data-gh-jump]'),ask=t.closest('[data-gh-topic]');
    if(t.closest('[data-tut-close]'))d.close();
    else if(ask){
      // A "Hay được hỏi" question: open that topic where it lives and bring it into view.
      const id=ask.dataset.ghTopic;view.tab='play';view.q='';view.open=id;
      if(!d.querySelector('#gh-t-'+CSS.escape(id)))render(false);
      const el=d.querySelector('#gh-t-'+CSS.escape(id));if(el){el.open=true;el.scrollIntoView({block:'start'});el.querySelector('summary')?.focus({preventScroll:true});}
    }
    else if(t.closest('[data-gh-go]'))d.close();   // the app's own click handler opens the screen
    else if(tab){view.tab=tab.dataset.tutTab;view.q='';view.page=null;view.sec='';render();}
    else if(car){
      const sec=car.dataset.ghSec||'';
      view.tab='work';view.career=car.dataset.tutCareer;view.page=null;view.sec='';view.q='';render();
      if(sec){const el=d.querySelector(`.gh-sec[data-sec="${CSS.escape(sec)}"]`);if(el){el.open=true;el.scrollIntoView({block:'start'});}}
      else d.querySelector('.gh-pick .selected')?.scrollIntoView({block:'nearest',inline:'center'});
    }
    else if(page){view.page=page.dataset.tutPage||null;render(false);}
    else if(jump){const el=d.querySelector('#'+CSS.escape(jump.dataset.ghJump));el?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}
  });
  d.addEventListener('input',e=>{
    const q=e.target.closest?.('[data-gh-q]');if(!q)return;
    view.q=q.value;
    // Only the results change: the search box keeps its focus and caret.
    const main=d.querySelector('.gh-main');if(!main)return;
    main.innerHTML=fold(view.q).trim().length>=2?search(view.q):view.tab==='work'?workTab():playTab();
    d.querySelectorAll('[data-tut-tab]').forEach(b=>{const on=!view.q&&b.dataset.tutTab===view.tab;b.classList.toggle('active',on);b.setAttribute('aria-selected',on);});
  });
  // Keep the app's toasts visible above this dialog while it is open.
  d.addEventListener('close',()=>{const t=document.getElementById('toasts');if(t&&d.contains(t))(document.querySelector('dialog[open]')||document.body).append(t);});
  return d;
}
function render(top=true){
  const d=dialog(),inner=d.querySelector('.tut-guide-inner'),y=d.scrollTop;
  inner.innerHTML=html();
  d.scrollTop=top?0:y;
}

/** Open the guide. `tab`: 'play' | 'work'; `career` picks the "Hướng dẫn nghề" page of that workplace,
 * `sec` one of its sections open (e.g. 'prep'), `page` one of its illustrated extra pages (e.g. 'restock');
 * `topic` opens one "Hướng dẫn chơi" topic or "Hỏi nhanh" question ('quick': the "Hỏi nhanh" list). */
export function openGuide(env,{career,tab,page,topic,sec}={}){
  if(env)ENV=env;
  const cur=current();
  view={tab:tab||(career||page||sec?'work':'play'),career:career||cur||null,page:page||null,q:'',open:topic||'',sec:sec||''};
  const d=dialog();render();
  if(!d.open)d.showModal();
  d.tabIndex=-1;d.focus({preventScroll:true});
  if(DATA===null){loadData().then(()=>{if(d.open){render();place(d,topic);}});return;}
  place(d,topic);
}
function place(d,topic){
  if(view.sec&&view.tab==='work')d.querySelector(`.gh-sec[data-sec="${CSS.escape(view.sec)}"]`)?.scrollIntoView({block:'start'});
  else if(view.page)d.querySelector('.gh-shots')?.scrollIntoView({block:'start'});
  else if(topic==='quick')d.querySelector('#gh-quick')?.scrollIntoView({block:'start'});
  else if(topic)d.querySelector('#gh-t-'+CSS.escape(topic)+',#gh-q-'+CSS.escape(topic))?.scrollIntoView({block:'start'});
  else if(view.tab==='work')d.querySelector('.gh-pick .selected')?.scrollIntoView({block:'nearest',inline:'center'});
}
export const closeGuide=()=>{const d=document.getElementById('tutGuide');if(d?.open)d.close();};

/** "?" for a work screen header: opens this workplace's guide (`page`: one of its illustrated extra pages). */
export function helpButton(career,page=''){
  return `<button type="button" class="icon-btn tut-help" data-action="tutGuide" data-career="${esc(career||'')}" data-tab="work"${page?` data-page="${esc(page)}"`:''} aria-label="Hướng dẫn nghề này">?</button>`;
}
