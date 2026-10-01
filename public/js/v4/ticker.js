/** Bảng tin cả phố: a line that scrolls across the screen when a couple gets married (game/marriage.py
 * writes the news; display names only, and only when both spouses agreed). Cheap polling of
 * GET /api/news?since=<id> about once a minute, paused while the tab is hidden; the server caches the
 * answer. Each line plays a few times and goes away; the last line seen is remembered on this device.
 * prefers-reduced-motion (or Cài đặt → Giảm chuyển động) gets a still banner. Text goes in with
 * textContent only. The same answer carries my own alerts (badges on "Hôn nhân" and "Bạn bè", a toast
 * when someone proposes, asks to be friends, a plan arrives, the spouse sends something or the wedding day came). */
const SEEN='mnl.newsSeen',NOTE='mnl.mrNotice',POLL_MS=60000,PASSES=3,STILL_MS=9000;
const read=k=>{try{return Number(localStorage.getItem(k))||0;}catch{return 0;}};
const write=(k,v)=>{try{localStorage.setItem(k,String(v));}catch{/* storage blocked */}};
let getEnv=null,timer=0,since=0,queue=[],bar=null,playing=false,booted=false,inflight=false;

export function tickerBoot(envFn){
  if(booted)return;booted=true;getEnv=envFn;since=read(SEEN);
  document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(!document.hidden)timer=setTimeout(poll,1500);});
  timer=setTimeout(poll,4000);  // after the first paint
}

async function poll(){
  clearTimeout(timer);
  if(document.hidden||inflight)return;
  inflight=true;
  try{
    const r=await fetch(`/api/news?since=${since}`,{credentials:'same-origin',cache:'no-store'});
    if(r.ok)handle(await r.json());
  }catch{/* offline: try again later */}
  finally{inflight=false;timer=setTimeout(poll,POLL_MS);}
}

function handle(d){
  if(!d||!Array.isArray(d.items))return;
  for(const it of d.items)if(it&&typeof it.text==='string'&&!queue.some(q=>q.id===it.id))queue.push({id:Number(it.id)||0,text:it.text.slice(0,200)});
  if(typeof d.last==='number')since=d.last;  // polling cursor; SEEN (on this device) moves when a line has played
  if(queue.length&&!playing)next();
  const env=getEnv?.();if(!env)return;
  const me=d.me||null;
  let moved=false;
  for(const [action,key,n] of [['marriage','marriageAlerts',Number(me?.alerts)||0],['friends','friendAlerts',Number(me?.friends)||0]]){
    if((env.api[key]||0)===n)continue;
    env.api[key]=n;moved=true;
    document.querySelectorAll(`[data-action="${action}"]`).forEach(b=>{if(b.closest('.mr-sheet'))return;b.querySelector('em.badge')?.remove();if(n){const em=document.createElement('em');em.className='badge';em.textContent=String(n);b.append(em);}});
  }
  if(moved)document.dispatchEvent(new Event('mnl:badges'));   // the menu hub that holds them (app.js) shows the sum
  if(me?.notice&&me.notice_at>read(NOTE)){
    const first=!read(NOTE);write(NOTE,me.notice_at);
    if(!first||Date.now()/1000-me.notice_at<86400)env.toast(me.notice,'good');
    // The save may have changed on the server (engaged, a wedding day, a divorce): fetch it.
    env.api.refresh?.().catch(()=>{});
    window.dispatchEvent(new Event('mnl:marriage'));
  }
}

const still=()=>matchMedia('(prefers-reduced-motion: reduce)').matches||document.documentElement.classList.contains('reduce-motion');
// A modal (a sheet, the welcome card, a confirmation) covers the page: wait until the street is in sight.
const covered=()=>{try{return Boolean(document.querySelector('dialog:modal'));}catch{return Boolean(document.querySelector('dialog[open]'));}};
async function next(){
  if(!queue.length){playing=false;bar?.remove();bar=null;return;}
  playing=true;
  if(covered()||document.hidden){bar?.remove();bar=null;setTimeout(next,3000);return;}
  const item=queue.shift();if(item.id>read(SEEN))write(SEEN,item.id);
  try{const {ensureMarriageCss}=await import('./marriage.js');await ensureMarriageCss();}catch{/* plain banner */}
  if(!bar){
    bar=document.createElement('div');bar.className='mr-ticker';bar.setAttribute('role','status');bar.setAttribute('aria-live','polite');
    const ic=document.createElement('span');ic.className='mr-ticker-ic';ic.setAttribute('aria-hidden','true');ic.textContent='📣';
    const track=document.createElement('div');track.className='mr-ticker-track';
    const text=document.createElement('span');text.className='mr-ticker-text';track.append(text);
    const x=document.createElement('button');x.type='button';x.className='mr-ticker-x';x.setAttribute('aria-label','Ẩn bảng tin');x.textContent='×';
    x.addEventListener('click',()=>{queue=[];playing=false;bar?.remove();bar=null;});
    bar.append(ic,track,x);document.body.append(bar);
  }
  const text=bar.querySelector('.mr-ticker-text');
  text.textContent=item.text;
  bar.classList.toggle('still',still());
  text.getAnimations?.().forEach(a=>a.cancel());
  if(still()||!text.animate){setTimeout(next,STILL_MS);return;}
  const track=bar.querySelector('.mr-ticker-track'),w=track.clientWidth,tw=text.scrollWidth,ms=Math.max(7000,(w+tw)*16);
  const anim=text.animate([{transform:`translateX(${w}px)`},{transform:`translateX(${-tw}px)`}],{duration:ms,iterations:PASSES,easing:'linear'});
  anim.onfinish=()=>next();
}
