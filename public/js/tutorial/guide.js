/** The illustrated guide ("Hướng dẫn"): a short "Cách chơi" overview in three
 * cards and a "Cách làm" quick guide for the first storefronts, with real screenshots
 * and numbered marks drawn as an overlay (they scale with the picture).
 * Opens in its own dialog, so the work screen underneath stays as it was. */
import {OVERVIEW,CAREERS,IMG} from './guide-data.js';
import {dayArt} from './art.js';

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const X='<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';
const ART={day:dayArt};
let view={tab:'play',career:null,page:null};

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

function playTab(){
  const cards=OVERVIEW.map((c,i)=>`<article class="tut-card"><header><span class="tut-card-n" aria-hidden="true">${i+1}</span><h3><span aria-hidden="true">${c.emoji}</span> ${esc(c.title)}</h3></header>`+
    `${c.art?ART[c.art]():''}${c.pic?figure(c.pic,c.title):''}<ul class="tut-points">${c.points.map(([n,t])=>`<li>${n?`<b class="tut-pn" aria-hidden="true">${n}</b>`:'<i class="tut-pn dot" aria-hidden="true"></i>'}${esc(t)}</li>`).join('')}</ul></article>`).join('');
  return `<button type="button" class="btn primary full tut-replay" data-action="tutReplay">▶ Xem lại hướng dẫn (1 phút)</button>`+
    `<div class="tut-cards">${cards}</div>`;
}

function workTab(){
  const ids=Object.keys(CAREERS),cid=ids.includes(view.career)?view.career:null;
  const chips=`<div class="chip-row tut-chips" role="tablist" aria-label="Chọn nghề">${ids.map(id=>{const c=CAREERS[id];return `<button type="button" role="tab" class="chip${id===cid?' selected':''}" aria-selected="${id===cid}" data-tut-career="${id}"><span aria-hidden="true">${c.emoji}</span> ${esc(c.name)}</button>`;}).join('')}</div>`;
  if(!cid)return chips+generic();
  const c=CAREERS[cid],pages=c.pages||[],page=pages.find(p=>p.id===view.page)||null;
  // A workplace with more than one page ("Nhập hàng & xếp kệ"): a second row of chips.
  const sub=pages.length?`<div class="chip-row tut-chips tut-pages" role="tablist" aria-label="Trang">${[{id:'',emoji:c.emoji,name:c.main||'Bán hàng'},...pages].map(p=>{const on=(page?.id||'')===p.id;
    return `<button type="button" role="tab" class="chip${on?' selected':''}" aria-selected="${on}" data-tut-page="${esc(p.id)}"><span aria-hidden="true">${p.emoji}</span> ${esc(p.name)}</button>`;}).join('')}</div>`:'';
  const steps=(page||c).steps.map((s,i)=>`<li class="tut-step"><div class="tut-step-head"><span class="tut-step-n" aria-hidden="true">${i+1}</span><p>${esc(s.text)}</p></div>${figure(s,s.text,{finger:true})}</li>`).join('');
  return chips+sub+`<ol class="tut-steps">${steps}</ol>`;
}
/** Any other workplace: the same rhythm, in words. */
function generic(){
  const rows=['🙋 Chọn việc đang chờ','👆 Bấm nút nổi bật','✅ Kiểm rồi bàn giao','🌙 Hết việc: Khép ca'];
  return `<ol class="tut-steps plain">${rows.map((r,i)=>`<li class="tut-step"><div class="tut-step-head"><span class="tut-step-n" aria-hidden="true">${i+1}</span><p>${esc(r)}</p></div></li>`).join('')}</ol>`;
}

function html(){
  const tabs=[['play','Cách chơi'],['work','Cách làm']];
  const nav=`<nav class="pill-tabs tut-tabs" role="tablist">${tabs.map(([id,l])=>`<button type="button" role="tab" aria-selected="${view.tab===id}" class="${view.tab===id?'active':''}" data-tut-tab="${id}">${l}</button>`).join('')}</nav>`;
  return `<header class="sheet-head"><div class="grow"><span class="eyebrow">HƯỚNG DẪN</span><h2>${view.tab==='work'?'Cách làm':'Cách chơi'}</h2></div><button class="icon-btn" type="button" data-tut-close aria-label="Đóng">${X}</button></header>`+
    `<div class="sheet-body tut-guide-body">${nav}${view.tab==='work'?workTab():playTab()}</div>`;
}

function dialog(){
  let d=document.getElementById('tutGuide');
  if(d)return d;
  d=document.createElement('dialog');d.id='tutGuide';d.className='sheet medium tut-guide';d.setAttribute('aria-label','Hướng dẫn');
  d.innerHTML='<div class="tut-guide-inner"></div>';document.body.append(d);
  d.addEventListener('click',e=>{
    const t=e.target;
    if(t===d){d.close();return;}   // tap on the backdrop
    const tab=t.closest('[data-tut-tab]'),car=t.closest('[data-tut-career]'),page=t.closest('[data-tut-page]');
    if(t.closest('[data-tut-close]'))d.close();
    else if(tab){view.tab=tab.dataset.tutTab;render();}
    else if(car){view.career=car.dataset.tutCareer;view.page=null;render();}
    else if(page){view.page=page.dataset.tutPage||null;render();}
  });
  // Keep the app's toasts visible above this dialog while it is open.
  d.addEventListener('close',()=>{const t=document.getElementById('toasts');if(t&&d.contains(t))(document.querySelector('dialog[open]')||document.body).append(t);});
  return d;
}
function render(){const d=dialog(),inner=d.querySelector('.tut-guide-inner');inner.innerHTML=html();d.scrollTop=0;}

/** Open the guide: `career` picks the "Cách làm" page of that workplace, `page` one of its extra pages. */
export function openGuide(env,{career,tab,page}={}){
  const cur=env?.api?.state?.current||env?.api?.state?.focus;
  view={tab:tab||(career?'work':'play'),career:career||cur||null,page:page||null};
  const d=dialog();render();
  if(!d.open)d.showModal();
  d.tabIndex=-1;d.focus({preventScroll:true});
}
export const closeGuide=()=>{const d=document.getElementById('tutGuide');if(d?.open)d.close();};

/** "?" for a work screen header: opens this workplace's quick guide (`page`: one of its extra pages). */
export function helpButton(career,page=''){
  return `<button type="button" class="icon-btn tut-help" data-action="tutGuide" data-career="${esc(career||'')}" data-tab="work"${page?` data-page="${esc(page)}"`:''} aria-label="Cách làm">?</button>`;
}
