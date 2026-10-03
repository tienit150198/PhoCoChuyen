/** Bỏ dở việc: leaving a workplace mid-work to try another one.
 * Before a switch the confirm dialog shows the server's preview (state.abandon.preview:
 * the same numbers game/abandon.py applies); "Ở lại làm nốt" is the default. After a
 * switch the red banner shows what it cost ("−X xu · Bỏ dở việc"). The day summary
 * block and the employer-trust line on the journey place card live here too.
 * Render-only: the server refuses the switch without confirm and applies the penalty. */
import {escapeHTML as esc} from '../icons.js';
import {asset} from '../assets.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const $=s=>document.querySelector(s);
let banner=null,timer=0;

function css(){
  if(document.querySelector('link[data-abandon-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/abandon.css');l.dataset.abandonCss='1';document.head.append(l);
}
css();

const pocketText=x=>x.pocket==='wallet'?'trừ vào ví của bạn':`trừ vào quỹ ${x.place} (quỹ thiếu thì trừ ví)`;

function dialogHTML(x){
  const stakes=[
    `<li><span aria-hidden="true">💸</span><span class="grow">Phạt <b>${fmt(x.fine)} xu</b> <small>${esc(pocketText(x))}</small></span></li>`,
    `<li><span aria-hidden="true">💔</span><span class="grow">Mất <b>${fmt(x.trust)} ${esc(x.trust_name)}</b> <small>đang ${fmt(x.trust_now)}/100</small></span></li>`,
    `<li><span aria-hidden="true">🚶</span><span class="grow">${x.leaving?`<b>${fmt(x.leaving)} khách</b> đang chờ sẽ bỏ về`:'Việc đã hẹn vẫn giữ, nhưng khách sẽ phật lòng'}</span></li>`].join('');
  const warn=x.warn?`<p class="ab-warn">Hôm nay đã bỏ dở ở đây rồi. Lần này tiền phạt gấp ${x.offence}${x.pocket==='wallet'?' và chủ sẽ nhắc “lần sau cho nghỉ”':', khách quen bắt đầu kháo nhau'}.</p>`:'';
  return `<span class="eyebrow ab-eyebrow">ĐANG LÀM DỞ</span><h2>Bỏ dở việc ở ${esc(x.place)}?</h2><p>${esc(x.what||x.text)}</p><ul class="ab-stakes">${stakes}</ul>${warn}
    <div class="row ab-row"><button type="button" class="btn ghost ab-go" data-ab="go">Vẫn đi</button><button type="button" class="btn primary ab-stay" data-ab="stay">Ở lại làm nốt</button></div>`;
}

/** Before a switch to `target`. Resolves the payload for select_career ({} or {confirm:true}),
 * or null when the player stays. */
export function abandonGate(api,target){
  const x=api.state?.abandon?.preview;
  if(!x||x.soft||x.career===target)return Promise.resolve({});
  const dlg=$('#confirmDialog'),box=$('#confirmContent');
  if(!dlg||!box)return Promise.resolve(null);  // never walk off without the player seeing the cost
  box.innerHTML=dialogHTML(x);dlg.classList.add('ab-dialog');
  return new Promise(resolve=>{
    let done=false;
    const finish=go=>{if(done)return;done=true;dlg.removeEventListener('click',click);dlg.removeEventListener('close',closed);dlg.classList.remove('ab-dialog');if(dlg.open)dlg.close();resolve(go?{confirm:true}:null);};
    const click=e=>{const b=e.target.closest('[data-ab]');if(b)finish(b.dataset.ab==='go');};
    const closed=()=>finish(false);  // Escape / backdrop: stay
    dlg.addEventListener('click',click);dlg.addEventListener('close',closed);
    dlg.showModal();dlg.querySelector('.ab-stay')?.focus();
  });
}

function bannerHTML(x){
  const trust=x.trust?`<p>💔 −${fmt(x.trust)} ${esc(x.trust_name)} <small>(còn ${fmt(x.trust_after)}/100)</small></p>`:'';
  const walked=x.walked||x.jobs?`<p>🚶 ${fmt(x.walked+x.jobs)} khách đã bỏ về.</p>`:'';
  return `<div class="ab-card" role="alert"><span class="ab-emoji" aria-hidden="true">🏃</span><div class="grow"><div class="ab-top"><strong class="ab-big">−${fmt(x.fine)} xu</strong><span class="ab-what">${esc(x.label||'Phạt bỏ dở ca')} ở ${esc(x.place)}</span></div>
    ${trust}${walked}<p class="ab-line">${esc(x.text||'')}</p>${x.warn?`<p class="ab-warn">⚠️ ${x.pocket==='wallet'?'Lần sau còn bỏ ngang là bị cho nghỉ.':'Bỏ quầy nữa là mất khách quen.'}</p>`:''}<div class="ab-foot"><button type="button" class="btn small" data-ab-close>Đã hiểu</button></div></div></div>`;
}
function soft(x){return `<div class="ab-card soft" role="status"><span class="ab-emoji" aria-hidden="true">⏸️</span><div class="grow"><p>${esc(x.text)}</p><div class="ab-foot"><button type="button" class="btn small" data-ab-close>Đã hiểu</button></div></div></div>`;}

/** After select_career: the red money banner (or the sandbox's soft note). */
export function abandonAfter(r){
  const x=r?.abandon;if(!x)return;
  if(!banner){banner=document.createElement('div');banner.className='ab-layer';banner.addEventListener('click',e=>{if(e.target.closest('[data-ab-close]'))hide();});}
  const mount=$('#confirmDialog[open]')||$('#sheet[open]')||document.body;mount.append(banner);
  banner.innerHTML=x.soft?soft(x):bannerHTML(x);banner.hidden=false;
  clearTimeout(timer);timer=setTimeout(hide,x.soft?6000:14000);
}
function hide(){if(banner){banner.hidden=true;banner.innerHTML='';}clearTimeout(timer);}

/** Day summary block (summary.abandon). */
export function abandonSummary(x){
  if(!x?.count)return '';
  return `<article class="notice ab-sum"><span aria-hidden="true">🏃</span><div class="grow"><b>Bỏ dở việc hôm nay: ${fmt(x.count)} lần</b><ul>
    <li>Tiền phạt: <b class="out">−${fmt(x.fine)} xu</b></li><li>${esc(x.trust_name)}: <b class="out">−${fmt(x.trust)}</b> (còn ${fmt(x.trust_now)}/100)</li>
    ${x.walked+x.jobs?`<li>${fmt(x.walked+x.jobs)} khách đã bỏ về</li>`:''}</ul>${x.warn?`<p class="small">${x.pocket==='wallet'?'Chủ đã nhắc: lần sau còn bỏ ngang là cho nghỉ.':'Hàng xóm đã nhắc: bỏ quầy hoài là mất khách quen.'}</p>`:''}</div></article>`;
}

/** Journey place card: "Chủ tin bạn 64/100" for places you work at for someone else. */
export function abandonTrust(api,cid){
  const v=api.state?.abandon?.trust?.[cid];
  return v==null?'':` · Chủ tin bạn ${fmt(v)}/100`;
}
