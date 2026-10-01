/** 💍 Lịch cưới: the weddings the whole phố is invited to (live/wedding.py `wed_list`), opened from the Khu phố hub.
 * A party opens 5 minutes before its time and lasts 10 minutes; "Vào dự" walks in (./walk.js, the same scene kit
 * as Đi dạo). Also the couple's group photos in Kỷ niệm (GET /api/wedding/photos, fillAlbum). No guide, no tips:
 * the list says what is on, the button says what to do. */
import {icon,escapeHTML as esc} from '../icons.js';
import {live} from './live.js';
import {stylesheet} from '../lazy.js';

const S={dlg:null,env:null,list:null,got:0,skew:0,open:0,timer:0,bound:false,photos:null,photosAt:0,asked:0};
const fmtLeft=s=>{s=Math.max(0,Math.round(s));const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;return h?`${h} giờ ${m} phút`:`${m}:${String(x).padStart(2,'0')}`;};
const VN=new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',weekday:'short',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});
const when=at=>{const p=Object.fromEntries(VN.formatToParts(new Date(at*1000)).map(x=>[x.type,x.value]));return `${p.hour}:${p.minute} · ${p.weekday} ${p.day}/${p.month}`;};
const now=()=>Date.now()/1000+S.skew;

function bind(){
  if(S.bound)return;S.bound=true;
  live.on('wed_list',f=>{S.list=f.parties||[];S.open=f.open_before||600;S.skew=(f.now||Date.now()/1000)-Date.now()/1000;S.got=Date.now();if(S.dlg?.open)render();});
  live.on('welcome',()=>{if(S.dlg?.open)live.send({t:'wed_list'});});
}
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');d.className='sheet v4-sheet medium wd-sheet';d.setAttribute('aria-label','Lịch cưới');
  d.innerHTML=`<header class="wk-head"><div class="wk-where wk-wed"><b>💍 Lịch cưới</b></div><span class="grow"></span>
    <button type="button" class="icon-btn" data-wd="close" aria-label="Đóng">${icon('x',20)}</button></header><div class="wd-body"></div>`;
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-wd]');if(!el||el.disabled)return;
    act(el.dataset.wd,el.dataset);
  });
  d.addEventListener('close',()=>clearInterval(S.timer));
  document.body.append(d);S.dlg=d;return d;
}

/** The hub entry "Lịch cưới". */
export async function openWeddings(env){
  S.env=env;bind();await stylesheet('/css/walk.css');
  const d=dialog();if(!d.open)d.showModal();
  live.send({t:'wed_list'});S.asked=Date.now();render();
  clearInterval(S.timer);
  S.timer=setInterval(()=>{if(!d.open)return clearInterval(S.timer);if(Date.now()-S.asked>20000){S.asked=Date.now();live.send({t:'wed_list'});}render();},1000);
}

function render(){
  const body=S.dlg?.querySelector('.wd-body');if(!body)return;
  if(live.state!=='open'&&!S.list){body.innerHTML=`<p class="wd-empty">${icon('refresh',16)} Đang kết nối…</p>`;return;}
  if(!S.list){body.innerHTML='<div class="mnl-skel" role="status" aria-busy="true"><i></i><i></i><i></i></div>';return;}
  const t=now();
  const rows=S.list.filter(p=>p.end>t).map(p=>{
    const opens=p.at-S.open,going=t>=opens;
    const state=going?(t<p.at?`Sắp bắt đầu · ${fmtLeft(p.at-t)}`:`Đang diễn ra · còn ${fmtLeft(p.end-t)}`):(opens-t<3600?`Mở sau ${fmtLeft(opens-t)}`:'');
    return `<li class="wd-row${going?' live':''}"><div class="wd-ico" aria-hidden="true">💍</div><div class="grow">
      <b data-no-translate>${esc(p.a)} & ${esc(p.b)}</b>${p.mine?' <span class="tag">Của bạn</span>':''}
      <small>${esc(when(p.at))}${state?` · ${esc(state)}`:''}</small></div>
      ${going?`<button type="button" class="wk-pill primary" data-wd="go" data-id="${p.id}">Vào dự${p.n?` · ${p.n}`:''}</button>`:''}</li>`;
  });
  body.innerHTML=(rows.length?`<ul class="wd-list">${rows.join('')}</ul>`:`<p class="wd-empty">Chưa có đám cưới nào sắp tới.</p>`)+
    `<button type="button" class="wd-race" data-wd="race">🏆 Khách mời của tuần</button>`;
}

async function act(a,d){
  switch(a){
    case'close':S.dlg.close();return;
    case'go':{S.dlg.close();const m=await import('./walk.js');m.openWalk(S.env,{wedding:Number(d.id)});return;}
    case'race':{S.dlg.close();S.env.ui.lb={...(S.env.ui.lb||{data:{},busy:{}}),kind:'wed'};S.env.act('rank');return;}
  }
}

/* ---- Kỷ niệm: the couple's group photos (app.js albumView leaves a [data-wed-album] slot) ---- */
export function fillAlbum(env){
  const slot=document.querySelector('[data-wed-album]');if(!slot)return;
  const paint=()=>{const el=document.querySelector('[data-wed-album]');if(!el||!S.photos?.length)return;
    el.innerHTML=`<h3 class="space-top">💍 Ảnh cưới</h3><div class="album-grid">${S.photos.map(p=>`<article class="polaroid"><img src="${esc(p.image)}" alt="Ảnh cưới ${esc(p.date)}" loading="lazy"><p>${esc(p.date)}</p></article>`).join('')}</div>`;};
  if(S.photos&&Date.now()-S.photosAt<60000)return paint();
  S.photosAt=Date.now();
  env.api.json('/api/wedding/photos').then(d=>{S.photos=d.photos||[];paint();}).catch(()=>{});
}
