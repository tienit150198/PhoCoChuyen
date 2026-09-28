/** Chuyện bất ngờ trong ca: what the player sees when something happens in
 * the shift. The server opens a live happening (a thief, a broken window, a
 * break-in found at opening…); the scene animates it (v4/scene-events.js),
 * a reaction card offers what you can do right now, and the result shows a
 * big loss banner ("−120 xu · Trộm lấy tiền trong ngăn kéo") or a green one
 * when you stopped it. Police results days later arrive as a news banner.
 * Render-only: every roll, amount and outcome comes from game/happenings.py. */
import {icon,escapeHTML as esc} from '../icons.js';
import {SceneFx} from './scene-events.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const signed=n=>`${n<0?'−':'+'}${fmt(Math.abs(n))}`;
const WHERE={fund:'Quỹ nơi làm',wallet:'Ví của bạn',stock:'Hàng trong kho'};
const CAT={theft_loss:'Mất trộm',damage:'Hư hỏng',compensation:'Bồi thường',recovery:'Thu hồi',insurance_recovery:'Bảo hiểm chi trả',medical:'Tiền thuốc'};
const store={get(k){try{return sessionStorage.getItem(k);}catch{return null;}},set(k,v){try{sessionStorage.setItem(k,v);}catch{}}};

function lineRow(x){return `<li class="${x.amount<0?'out':'in'}"><span>${esc(WHERE[x.where]||x.where)} · ${esc(CAT[x.cat]||'Chuyện bất ngờ')}</span><b>${signed(x.amount)} xu</b></li>`;}
/** One row per place and reason: two stolen goods read as one line. */
const group=lines=>{const out=[];for(const x of lines||[]){const k=x.where+'|'+x.cat+'|'+(x.amount<0);const hit=out.find(y=>y.k===k);if(hit)hit.amount+=x.amount;else out.push({...x,k});}return out;};
const lost=lines=>lines.filter(x=>x.amount<0).reduce((a,x)=>a+x.amount,0);
const gained=lines=>lines.filter(x=>x.amount>0).reduce((a,x)=>a+x.amount,0);

function beforeAfter(rows){
  if(!rows?.length)return '';
  return `<div class="hap-ba" role="table" aria-label="Trước và sau"><div class="hap-ba-head" role="row"><span role="columnheader">Món</span><span role="columnheader">Trước</span><span role="columnheader">Sau</span></div>${rows.map(r=>`<div class="hap-ba-row" role="row"><span role="cell">${esc(r.emoji)} ${esc(r.name)}</span><span role="cell">${r.before}</span><b role="cell">${r.after}</b></div>`).join('')}</div>`;
}

function panelHTML(x){
  const btns=x.reactions.map(r=>`<button type="button" class="hap-choice" data-hap="${esc(r.id)}"${r.enabled?'':' disabled'}><strong>${esc(r.label)}</strong><small>${esc(r.enabled?r.hint:r.why)}</small></button>`).join('');
  const already=x.morning&&x.lines?.length?`<ul class="hap-lines">${group(x.lines).map(lineRow).join('')}</ul>`:'';
  return `<header class="hap-head"><span class="hap-emoji" aria-hidden="true">${esc(x.emoji)}</span><div class="grow"><span class="eyebrow">${esc(x.kind_emoji)} ${esc(x.kind_label).toUpperCase()}</span><h2 id="hapTitle">${esc(x.title)}</h2></div><button type="button" class="icon-btn hap-min" data-hap-min aria-label="Thu nhỏ để nhìn cảnh">${icon('x',19)}</button></header>
    <p class="hap-text">${esc(x.text)}</p>${beforeAfter(x.before)}${already}
    <h3 class="hap-ask">${x.morning?'Bạn xử lý thế nào?':'Làm gì ngay bây giờ?'}</h3><div class="hap-choices" role="group" aria-label="Cách phản ứng">${btns}</div>
    <p class="hap-foot">${icon('clock',13)} Quay lại làm việc khác thì chuyện sẽ tự trôi qua.</p>`;
}

function bannerHTML(r){
  const loss=lost(r.lines),back=gained(r.lines),bad=loss<0&&!(r.won);
  const items=r.items?.length?`<p class="hap-items">${r.items.map(i=>`${esc(i.emoji)} ${esc(i.name)} ${i.before!=null?`<span>${i.before} → ${i.after}</span>`:`<span>×${i.qty}</span>`}`).join(' · ')}</p>`:'';
  const head=loss<0?`<strong class="hap-big">${signed(loss)} xu</strong><span class="hap-what">${esc(r.label)}</span>`:
    `<strong class="hap-big">${r.kind==='den'?'Xong chuyện':'Giữ được rồi!'}</strong><span class="hap-what">${esc(r.title)}</span>`;
  const extra=[r.hurt?`<p class="hap-hurt">${icon('alert',14)} ${esc(r.hurt_text)}</p>`:'',r.case?`<p class="hap-case">🚓 Đã báo công an. Vài hôm nữa sẽ có tin.</p>`:'',
    r.insurance?`<p class="hap-ins">🛡️ Bảo hiểm tài sản chi trả +${fmt(r.insurance)} xu.</p>`:'',r.auto?`<p class="hap-auto">Bạn bận việc khác nên không kịp phản ứng.</p>`:''].join('');
  const lines=r.lines?.length?`<ul class="hap-lines">${group(r.lines).map(lineRow).join('')}</ul>`:'';
  return `<div class="hap-banner-card ${bad||loss<0?'bad':'good'}"><span class="hap-banner-emoji" aria-hidden="true">${esc(r.emoji)}</span><div class="grow"><div class="hap-banner-top">${head}</div><p class="hap-outcome">${esc(r.outcome)}</p>${items}${lines}${extra}${back&&loss<0?`<p class="hap-back">Được bù lại +${fmt(back)} xu.</p>`:''}<div class="hap-banner-foot"><button type="button" class="btn small" data-hap-close>Đã hiểu</button></div></div></div>`;
}

function newsHTML(n){
  const back=gained(n.lines),items=n.items?.length?`<p class="hap-items">Trả lại: ${n.items.map(i=>`${esc(i.emoji)} ${esc(i.name)} ×${i.qty}`).join(' · ')}</p>`:'';
  return `<div class="hap-news-card ${n.outcome==='cold'?'cold':'solved'}"><span class="hap-banner-emoji" aria-hidden="true">${esc(n.emoji)}</span><div class="grow"><span class="eyebrow">${esc(n.about_emoji)} ${esc(n.about)}</span><strong class="hap-news-title">${esc(n.title)}</strong><p>${esc(n.text)}</p>${items}${back?`<p class="hap-back">+${fmt(back)} xu được trả về${n.insurance?` (có ${fmt(n.insurance)} xu bảo hiểm)`:''}.</p>`:''}${n.insurance_text&&!back?`<p>${esc(n.insurance_text)}</p>`:''}<div class="hap-banner-foot"><button type="button" class="btn small primary" data-hap-ack="${esc(n.id)}">Đã xem</button></div></div></div>`;
}

/** Day summary block. */
export function happenSummary(x){
  if(!x||(!x.items?.length&&!x.news?.length))return '';
  const rows=(x.items||[]).map(h=>{const total=(h.fund||0)+(h.wallet||0)+(h.stock||0);return `<li class="${h.good===true?'good':total<0?'bad':'mid'}"><span aria-hidden="true">${esc(h.emoji)}</span><span class="grow"><b>${esc(h.title)}</b><small>${h.auto?'Không kịp phản ứng · ':''}${esc(h.choice)}${h.case?' · đã báo công an':''}</small></span>${total?`<b class="${total<0?'out':'in'}">${signed(total)} xu</b>`:'<b class="in">Giữ được</b>'}</li>`;}).join('');
  const news=(x.news||[]).map(n=>`<li class="${n.outcome==='cold'?'mid':'good'}"><span aria-hidden="true">${esc(n.emoji)}</span><span class="grow"><b>${esc(n.title)}</b><small>${esc(n.about)}</small></span>${gained(n.lines)?`<b class="in">+${fmt(gained(n.lines))} xu</b>`:''}</li>`).join('');
  return `<article class="notice hap-sum">${icon('alert',17)}<div class="grow"><b>Chuyện bất ngờ hôm nay</b><ul>${rows}${news}</ul></div></article>`;
}

export function happenBoot(env){
  if(!document.querySelector('link[data-happen-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href='/css/happenings.css';l.dataset.happenCss='1';document.head.append(l);}
  const world=env.world,fx=new SceneFx();world.fx=fx;
  const layer=document.createElement('div');layer.className='hap-layer';layer.innerHTML=`<div class="hap-top"><div class="hap-banner" role="alert" hidden></div><div class="hap-news" role="status" aria-live="polite" hidden></div><button type="button" class="hap-pill" hidden></button></div><section class="hap-panel" role="dialog" aria-modal="false" aria-labelledby="hapTitle" hidden></section>`;
  document.body.append(layer);
  const pill=layer.querySelector('.hap-pill'),panel=layer.querySelector('.hap-panel'),banner=layer.querySelector('.hap-banner'),newsBox=layer.querySelector('.hap-news');
  let liveId=null,openTimer=0,busy=false,bannerTimer=0;
  const cur=()=>{const s=env.api.state;return s?.current?s.careers?.[s.current]:null;};
  // Results already on screen before this page load are not announced again.
  const seen=new Set((store.get('hap-seen')||'').split(',').filter(Boolean));
  const markSeen=id=>{seen.add(id);store.set('hap-seen',[...seen].slice(-30).join(','));};
  const key=r=>`${env.api.state?.current}:${r.id}:${r.script}:${r.day}`;
  const boot=cur()?.happen?.last;if(boot)markSeen(key(boot));
  const mount=()=>{const m=document.querySelector('#confirmDialog[open]')||document.querySelector('#sheet[open]')||document.body;if(layer.parentNode!==m)m.append(layer);};
  const openPanel=()=>{const x=cur()?.happen?.live;if(!x)return;clearTimeout(openTimer);panel.innerHTML=panelHTML(x);panel.hidden=false;pill.hidden=true;opened(true);mount();panel.querySelector('.hap-choice:not([disabled])')?.focus({preventScroll:true});};
  const minimize=()=>{const x=cur()?.happen?.live;panel.hidden=true;opened(false);if(x){pill.hidden=false;pill.innerHTML=`<span aria-hidden="true">${esc(x.emoji)}</span> ${esc(x.title)} · <b>Xử lý</b>`;}};
  // Helper hint toasts step aside while the reaction card is up.
  const opened=on=>document.documentElement.classList.toggle('hap-open',on);
  fx.onTap=()=>openPanel();
  pill.addEventListener('click',openPanel);
  panel.addEventListener('click',async e=>{
    if(e.target.closest('[data-hap-min]')){minimize();return;}
    const b=e.target.closest('[data-hap]');if(!b||b.disabled||busy)return;
    const x=cur()?.happen?.live;if(!x)return;busy=true;panel.querySelectorAll('button').forEach(v=>v.disabled=true);
    const r=await env.cmd('hap_react',{id:x.id,choice:b.dataset.hap},{quiet:true});busy=false;
    if(!r){openPanel();}
  });
  const hideBanner=()=>{banner.hidden=true;banner.innerHTML='';clearTimeout(bannerTimer);};
  banner.addEventListener('click',e=>{if(e.target.closest('[data-hap-close]'))hideBanner();});
  newsBox.addEventListener('click',async e=>{const b=e.target.closest('[data-hap-ack]');if(!b)return;newsBox.hidden=true;await env.cmd('hap_ack',{id:b.dataset.hapAck},{quiet:true});});
  const showBanner=r=>{banner.innerHTML=bannerHTML(r);banner.hidden=false;mount();clearTimeout(bannerTimer);bannerTimer=setTimeout(hideBanner,14000);};
  const check=()=>{
    const c=cur(),h=c?.happen;
    if(!h){fx.clear();panel.hidden=true;pill.hidden=true;opened(false);liveId=null;return;}
    if(h.live){
      if(h.live.id!==liveId){
        liveId=h.live.id;fx.start(world,h.live);
        // The scene must be visible: step out of the work sheet (the task is kept on the server).
        if(document.querySelector('#sheet[open]')&&!document.querySelector('#confirmDialog[open]'))env.closeSheet();
        minimize();clearTimeout(openTimer);openTimer=setTimeout(()=>{if(cur()?.happen?.live?.id===liveId&&panel.hidden&&!document.querySelector('#sheet[open],#confirmDialog[open]'))openPanel();},env.api.state.settings?.reduceMotion?200:1700);
      }else if(!panel.hidden){const focus=document.activeElement?.dataset?.hap;panel.innerHTML=panelHTML(h.live);if(focus)panel.querySelector(`[data-hap="${focus}"]`)?.focus({preventScroll:true});}
    }else{
      if(liveId){fx.finish(world,h.last&&h.last.id===liveId?h.last:null);liveId=null;}
      panel.hidden=true;pill.hidden=true;opened(false);
    }
    if(h.last&&!seen.has(key(h.last))){markSeen(key(h.last));showBanner(h.last);}
    const n=h.news?.[0];
    if(n&&!panel.hidden){newsBox.hidden=true;newsBox.dataset.id='';}
    else if(n&&newsBox.dataset.id!==n.id){newsBox.innerHTML=newsHTML(n);newsBox.dataset.id=n.id;newsBox.hidden=false;mount();}
    else if(!n){newsBox.hidden=true;newsBox.dataset.id='';}
  };
  env.api.addEventListener('state',check);check();
  return {check,openPanel};
}
