/** 📺 Quảng cáo có thưởng (game/ads.py is the authority: the 7 views a day, the places, the rewards).
 *
 * watch(env, place, {restore}) is the whole flow behind every 📺 button:
 *  1. `ad_ticket {place}`: the server checks the day's views and that the place has something to give;
 *  2. the ad: Google's rewarded break (AdSense H5 games, adBreak({type:'reward'})) when <meta name="mnl-bonus">
 *     carries a publisher id, else (ADS_FAKE, local play and browser tests) a stand-in with a countdown;
 *  3. adViewed → `ad_claim {ticket}`: the server pays (at least MIN_WATCH_S after the ticket).
 * The player tapped the 📺 button, so that tap is the reward prompt: beforeReward shows the ad at once. No ad to show
 * (none filled, an ad blocker, the script refused) → a short line, nothing counted.
 *
 * Google's ad is a fixed full-screen frame, under the browser's top layer where every open <dialog> sits: the open
 * dialogs close while it plays and `restore()` (the caller's own way back: openSheet, openJail…) reopens them after.
 * The stand-in is a modal dialog of its own, on top of the others, so nothing closes for it.
 *
 * openBonus(env): the "📺 Quà xem quảng cáo" sheet (☰ Thêm): the day's 7 dots, the chests, ⏰ Giờ vàng riêng, the
 * closed shift's bonus, 🧩 Ghép ba boosters. File name: no "ad" word (blockers hide such files, tests/test_asset_names.py). */
import {escapeHTML as esc} from '../icons.js';
import {duck} from '../audio.js';
import {stylesheet} from '../lazy.js';

const B={cfg:undefined,load:null,busy:false,dlg:null,env:null,timer:0};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const NO_AD='Hiện chưa có quảng cáo để xem. Thử lại sau ít phút nhé.';

export function config(){
  if(B.cfg===undefined){try{B.cfg=JSON.parse(document.querySelector('meta[name="mnl-bonus"]')?.content||'null');}catch{B.cfg=null;}}
  return B.cfg;
}
/** state.ads (null while off). */
export const info=env=>(config()&&env?.api?.state?.ads)||null;
/** A 📺 button may show: ads on and views left today. */
export const can=env=>Boolean(info(env)?.left>0);
export const hhmm=t=>{const d=new Date(t*1000);return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;};

/** Google's loader, once (preloads rewarded breaks); false when there is none to load. */
export function warm(){
  if(B.load)return B.load;
  const c=config();
  if(!c||c.fake||!c.client){B.load=Promise.resolve(false);return B.load;}
  window.adsbygoogle=window.adsbygoogle||[];
  B.load=new Promise(res=>{
    const s=document.createElement('script');
    s.async=true;s.crossOrigin='anonymous';
    s.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='+encodeURIComponent(c.client);
    if(c.test)s.setAttribute('data-adbreak-test','on');
    s.onload=()=>res(true);s.onerror=()=>res(false);
    document.head.append(s);
    window.adsbygoogle.push({preloadAdBreaks:'on',sound:'on'});   // adConfig
  });
  return B.load;
}

function hush(on){
  try{duck('bonus',on);}catch{/* no audio */}
}
/** Close the open dialogs (Google's frame sits under the top layer); the list, to reopen when there is no restore. */
function clearTop(){
  const open=[...document.querySelectorAll('dialog[open]')];
  for(const d of open)try{d.close();}catch{/* closing already */}
  return open;
}
function reopen(list,restore){
  if(restore){try{restore();}catch{/* the caller's own */}return;}
  for(const d of list)if(d.isConnected&&!d.open)try{d.showModal();}catch{/* gone */}
}

/** Google's rewarded break: {shown, viewed}. */
async function googleAd(place,restore){
  if(!(await warm()))return {shown:false,viewed:false};
  return new Promise(res=>{
    let shown=false,viewed=false,done=false,hidden=null;
    const finish=()=>{if(done)return;done=true;clearTimeout(wait);hush(false);if(hidden)reopen(hidden,restore);res({shown,viewed});};
    const wait=setTimeout(()=>{if(!shown)finish();},10000);   // no answer at all: give the screen back
    try{
      window.adsbygoogle.push({type:'reward',name:'mnl-'+place,
        beforeReward(showAdFn){hidden=clearTop();showAdFn();},
        beforeAd(){shown=true;hush(true);},
        afterAd(){hush(false);},
        adDismissed(){viewed=false;},
        adViewed(){viewed=true;},
        adBreakDone(){finish();}});
    }catch{finish();}
  });
}

/** The stand-in (ADS_FAKE): a countdown in a modal dialog of its own. */
function fakeAd(seconds){
  return new Promise(res=>{
    const d=document.createElement('dialog');d.className='sheet v4-sheet narrow bv-fake';d.setAttribute('aria-label','Quảng cáo');
    let left=seconds+1;
    const paint=()=>{d.innerHTML=`<div class="bv-fake-box"><p class="eyebrow">QUẢNG CÁO THỬ</p><div class="bv-fake-tv" aria-hidden="true">📺</div>
      <p class="bv-fake-count" role="status">${left>0?`Còn ${left} giây`:'Xem xong rồi!'}</p>
      <button type="button" class="btn ${left>0?'ghost':'primary big'}" data-bv="${left>0?'skip':'done'}">${left>0?'Bỏ qua (không nhận thưởng)':'Nhận thưởng'}</button></div>`;};
    paint();document.body.append(d);d.showModal();hush(true);
    const t=setInterval(()=>{left--;paint();if(left<=0)clearInterval(t);},1000);
    const end=v=>{clearInterval(t);hush(false);d.close();d.remove();res({shown:true,viewed:v});};
    d.addEventListener('click',e=>{const b=e.target.closest('[data-bv]');if(b)end(b.dataset.bv==='done');});
    d.addEventListener('cancel',e=>{e.preventDefault();if(left<=0)end(true);});
  });
}

function toastResult(env,r){
  const lines=[r?.message,...(r?.effects||[])].filter(Boolean);
  for(const x of lines)env.toast?.(x,'good');
}

/** The whole flow: the server's result of ad_claim, or null (nothing shown, not watched, refused). */
export async function watch(env,place,{restore}={}){
  if(B.busy||!config())return null;
  B.busy=true;
  try{
    let tk;
    try{tk=(await env.api.command('ad_ticket',{place}))?.ad?.ticket;}
    catch(e){if(e?.message)env.toast?.(e.message,'error');return null;}
    if(!tk)return null;
    const c=config();
    if(c.fake)await stylesheet('/css/bonus-video.css');
    const seen=c.fake?await fakeAd(Math.max(1,Number(c.min)||8)):await googleAd(place,restore);
    if(!seen.viewed){env.toast?.(seen.shown?'Chưa xem hết quảng cáo nên chưa có thưởng.':NO_AD,'hint');return null;}
    for(let i=0;i<4;i++){
      try{const r=await env.api.command('ad_claim',{ticket:tk});toastResult(env,r);return r;}
      catch(e){
        if(e?.data?.code==='ads_fast'){await sleep(2500);continue;}   // a short ad: the server's minimum is not over yet
        if(e?.conflict){await sleep(400);continue;}
        if(e?.message)env.toast?.(e.message,'error');
        return null;
      }
    }
    return null;
  }finally{B.busy=false;if(B.dlg?.open)paint();}
}

/** The 📺 button of a place (data-bv-place: the caller's own click handler calls watch()). */
export function button(env,place,label,cls='primary small'){
  const a=info(env);if(!a||a.left<=0)return '';
  warm();
  return `<button type="button" class="btn ${cls} bv-btn" data-action="bonusVideo" data-place="${esc(place)}">📺 ${label} <small>· còn ${a.left}/${a.max}</small></button>`;
}

/* ---------------------------------------------------------------- the sheet (☰ Thêm → 📺 Quà xem quảng cáo) */
function dialog(){
  if(B.dlg)return B.dlg;
  const d=document.createElement('dialog');d.className='sheet v4-sheet narrow bv-sheet';d.setAttribute('aria-labelledby','bv-title');
  d.innerHTML='<div class="bv-root"></div>';document.body.append(d);
  d.addEventListener('click',async e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-bv-go],[data-place],[data-bv-close]');if(!el||!d.contains(el))return;
    e.preventDefault();
    if(el.dataset.bvClose!==undefined){d.close();return;}
    if(el.dataset.place){await watch(B.env,el.dataset.place,{restore:()=>openBonus(B.env)});paint();return;}
    if(el.dataset.bvGo==='tile'){d.close();await (await import('./tile-match.js')).openTileMatch(B.env);}
  });
  d.addEventListener('close',()=>{clearInterval(B.timer);B.timer=0;});
  B.dlg=d;return d;
}
function dots(a){return `<div class="bv-dots" role="img" aria-label="Đã xem ${a.n} trên ${a.max} lượt hôm nay">${Array.from({length:a.max},(_,i)=>`<i class="${i<a.n?'on':''}${i===2||i===6?' gift':''}">${i===2||i===6?'🎁':''}</i>`).join('')}</div>`;}
function row(icon,title,text,btn){return `<article class="bv-row"><span class="bv-ico" aria-hidden="true">${icon}</span><div><b>${title}</b><p>${text}</p>${btn||''}</div></article>`;}
function paint(){
  const root=B.dlg?.querySelector('.bv-root');if(!root)return;
  const env=B.env,a=info(env);
  if(!a){root.innerHTML=`<header class="sheet-head"><h2 id="bv-title">📺 Quà xem quảng cáo</h2><button type="button" class="icon-btn" data-bv-close aria-label="Đóng">✕</button></header><div class="sheet-body"><p>Quà xem quảng cáo đang tạm nghỉ.</p></div>`;return;}
  const now=Date.now()/1000+(B.skew||0),gold=a.gold>now?a.gold:0,left=a.left>0;
  const chest=a.chest?`Lượt thứ ${a.chest.at} mở 🎁 rương ${fmt(a.chest.lo)}–${fmt(a.chest.hi)} xu.`:'Hôm nay đã mở đủ rương rồi!';
  const go=(place,label)=>left?`<button type="button" class="btn primary small" data-place="${place}">📺 ${label}</button>`:'';
  root.innerHTML=`<header class="sheet-head"><h2 id="bv-title">📺 Quà xem quảng cáo</h2><button type="button" class="icon-btn" data-bv-close aria-label="Đóng">✕</button></header>
    <div class="sheet-body bv-body">
      <section class="bv-top">${dots(a)}<p><b>Hôm nay: ${a.n}/${a.max} lượt.</b> ${left?chest:'Mai xem tiếp nhé!'}</p></section>
      ${row('⏰','Giờ vàng riêng',`Lãi tiệm và quầy của bạn ×${String(a.mult/100).replace('.',',')} trong 1 giờ.${gold?` <b>Đang bật tới ${hhmm(gold)}</b> (<span data-bv-left>${Math.ceil((gold-now)/60)}</span> phút).`:''}`,go('gold',gold?'Thêm 1 giờ':'Bật 1 giờ'))}
      ${a.shift?row('💼','Thưởng khép ca',`Ca vừa khép được thưởng thêm <b>+${fmt(a.shift)} xu</b>.`,go('shift','Nhận thưởng')):''}
      ${row('🧩','Ghép ba',`Khay đầy? Xem quảng cáo để hồi sinh. Hoặc nhận ngay +1 Hoàn tác, +1 Xáo, +1 Đẩy ô.`,`${go('tile','Nhận trợ giúp')} <button type="button" class="btn ghost small" data-bv-go="tile">Chơi Ghép ba</button>`)}
      <p class="bv-note">Xem hết quảng cáo mới có thưởng. Mỗi tài khoản ${a.max} lượt một ngày, 0 giờ đêm làm mới.</p>
    </div>`;
}
export async function openBonus(env){
  B.env=env;
  const a=info(env);if(a&&typeof a.now==='number')B.skew=a.now-Date.now()/1000;
  await stylesheet('/css/bonus-video.css');
  const d=dialog();
  if(!d.open){for(const x of document.querySelectorAll('dialog[open]'))if(x!==d)try{x.close();}catch{/* closing */}d.showModal();}
  paint();warm();
  clearInterval(B.timer);B.timer=setInterval(()=>{if(!d.open)return;const el=d.querySelector('[data-bv-left]');const g=info(B.env)?.gold||0;if(el&&g)el.textContent=String(Math.max(0,Math.ceil((g-Date.now()/1000-(B.skew||0))/60)));},20000);
}
