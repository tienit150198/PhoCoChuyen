/** Bảng tin cả phố: a line that scrolls across the screen when a couple gets married (game/marriage.py
 * writes the news; display names only, and only when both spouses agreed). Cheap polling of
 * GET /api/news?since=<id> about once a minute, paused while the tab is hidden; the server caches the
 * answer. Each line plays a few times and goes away; the last line seen is remembered on this device.
 * prefers-reduced-motion (or Cài đặt → Giảm chuyển động) gets a still banner. Text goes in with
 * textContent only. The same answer carries my own alerts (badges on "Hôn nhân" and "Bạn bè", a toast
 * when someone proposes, asks to be friends, a plan arrives, the spouse sends something or the wedding day came). */
import {language} from './i18n.js';
const SEEN='mnl.newsSeen',NOTE='mnl.mrNotice',GOLD='mnl.goldenSeen',EVENT='mnl.eventSeen',TFAIR='mnl.tfairSeen',PAYWEEK='mnl.payweekSeen',POLL_MS=60000,PASSES=3,STILL_MS=9000;
const read=k=>{try{return Number(localStorage.getItem(k))||0;}catch{return 0;}};
const write=(k,v)=>{try{localStorage.setItem(k,String(v));}catch{/* storage blocked */}};
let lastPoll=0,getEnv=null,timer=0,since=0,queue=[],bar=null,playing=false,booted=false,inflight=false,hold=0;
// 📻 Players' ads and songs on air (game/radio_station.py ticker: at most a few at once, each with its end time): a line plays
// once when it shows up, then at most every `replay` seconds on this device while it is on air; one pass, not three.
const AIRED=new Map(),AIRED_MAX=32;
// 🎵 A song line (game/radio_station.py line_text) in English: the frame is translated here and the song's title and the
// buyer's own words stay as they were written (the pack's pattern gives up on a lowercase Vietnamese message).
const SONG=/^🎵 (.+?) gửi tặng bài “(.+?)” qua DJ (.+?): “([\s\S]*)”$/u;
const songEn=text=>{if(language()!=='en')return null;const m=SONG.exec(text);return m?`🎵 ${m[1]} dedicates “${m[2]}” via DJ ${m[3]}: “${m[4]}”`:null;};

export function tickerBoot(envFn){
  if(booted)return;booted=true;getEnv=envFn;since=read(SEEN);
  // Back to the tab: the next poll 1.5 s on, or when the last one is 30 s old (a phone flipping between apps, 23/10 lag).
  document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(!document.hidden)timer=setTimeout(poll,Math.max(1500,lastPoll+30000-Date.now()));});
  timer=setTimeout(poll,4000);  // after the first paint
}

async function poll(){
  clearTimeout(timer);
  if(document.hidden||inflight)return;
  inflight=true;lastPoll=Date.now();
  try{
    const r=await fetch(`/api/news?since=${since}`,{credentials:'same-origin',cache:'no-store'});
    if(r.ok)handle(await r.json());
  }catch{/* offline: try again later */}
  finally{inflight=false;timer=setTimeout(poll,POLL_MS);}
}

function handle(d){
  if(!d||!Array.isArray(d.items))return;
  for(const it of d.items)if(it&&typeof it.text==='string'&&!queue.some(q=>q.id===it.id))queue.push({id:Number(it.id)||0,text:it.text.slice(0,200)});
  // ⏰ Giờ vàng / 🌟 Ngày vàng (game/golden_hour.py): its line plays once a window on this device (id 0: not a news row)
  const g=d.golden;if(g&&typeof g.text==='string'&&Number(g.ends)>read(GOLD)){write(GOLD,Number(g.ends));queue.unshift({id:0,text:g.text.slice(0,200)});}
  // 💐 a season's line (game/event2010.py news_line: Thiệp 20/10): once per key (a day) on this device
  const ev=d.event;if(ev&&typeof ev.text==='string'&&typeof ev.key==='string'){let k='';try{k=localStorage.getItem(EVENT)||'';}catch{k=ev.key;}
    if(k!==ev.key){write(EVENT,ev.key);queue.push({id:0,text:ev.text.slice(0,200)});}}
  // 🎉 Tuần lễ tay nghề (game/pay_boost.py news_line): once per key (a day) on this device
  const pw=d.payweek;if(pw&&typeof pw.text==='string'&&typeof pw.key==='string'){let k='';try{k=localStorage.getItem(PAYWEEK)||'';}catch{k=pw.key;}
    if(k!==pw.key){write(PAYWEEK,pw.key);queue.push({id:0,text:pw.text.slice(0,200)});}}
  if(Array.isArray(d.radio)){const t=Date.now();
    for(const r of d.radio.slice(0,8)){if(!r||typeof r.text!=='string'||typeof r.id!=='string'||!(Number(r.until)*1000>t))continue;
      const gap=Math.max(60,Number(r.replay)||480)*1000,last=AIRED.get(r.id)||0;
      if(t-last<gap||queue.some(q=>q.radio===r.id))continue;
      AIRED.delete(r.id);AIRED.set(r.id,t);while(AIRED.size>AIRED_MAX)AIRED.delete(AIRED.keys().next().value);
      queue.push({id:0,text:r.text.slice(0,200),radio:r.id,passes:1});}}
  // 🎪 Hội chợ việc làm (game/town_fair.py news_line): its status for the menu and the 2.5D signpost, and its line once per key
  if('tfair' in d){const tf=d.tfair;import('./town-fair-data.js').then(m=>m.setFair(tf)).catch(()=>{});
    if(tf&&typeof tf.text==='string'&&typeof tf.key==='string'){let k='';try{k=localStorage.getItem(TFAIR)||'';}catch{k=tf.key;}
      if(k!==tf.key){write(TFAIR,tf.key);queue.push({id:0,text:tf.text.slice(0,200)});}}}
  // 🎃 Lễ hội Ma Phố (game/halloween.py hint): its status for the menu, Tiện ích, the start card and the town's decor
  if('hween' in d)import('./halloween-data.js').then(m=>m.setHween(d.hween)).catch(()=>{});
  if(typeof d.last==='number')since=d.last;  // polling cursor; SEEN (on this device) moves when a line has played
  if(queue.length&&!playing)next();
  const env=getEnv?.();if(!env)return;
  const me=d.me||null;
  let moved=false;
  for(const [action,key,n] of [['marriage','marriageAlerts',Number(me?.alerts)||0],['friends','friendAlerts',Number(me?.friends)||0],['svcMarket','svcAlerts',Number(me?.svc)||0],['wedWork','wedsvcAlerts',Number(me?.wedsvc)||0]]){  // 🛎️ Phố dịch vụ: what waits for my answer; 💒 wedding orders waiting for my work
    if((env.api[key]||0)===n)continue;
    env.api[key]=n;moved=true;
    document.querySelectorAll(`[data-action="${action}"]`).forEach(b=>{if(b.closest('.mr-sheet'))return;b.querySelector('em.badge')?.remove();if(n){const em=document.createElement('em');em.className='badge';em.textContent=String(n);b.append(em);}});
  }
  if(moved)document.dispatchEvent(new Event('mnl:badges'));   // the menu hub that holds them (app.js) shows the sum
  if(me?.xfer)import('./bank-xfer.js').then(m=>m.receiveNow(env)).catch(()=>{});   // 💸 a friend's transfer waits: credit it, toast it
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
// A new neighbour's first day (html[data-fresh], v4/shell.js) waits too: the lines play from day 2.
const covered=()=>{if(document.documentElement.hasAttribute('data-fresh'))return true;try{return Boolean(document.querySelector('dialog:modal'));}catch{return Boolean(document.querySelector('dialog[open]'));}};
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
    x.addEventListener('click',()=>{queue=[];playing=false;clearInterval(hold);bar?.remove();bar=null;});
    bar.append(ic,track,x);document.body.append(bar);
  }
  const text=bar.querySelector('.mr-ticker-text');
  const en=item.radio?songEn(item.text):null;
  text.toggleAttribute('data-no-translate',Boolean(en));
  text.textContent=en||item.text;
  bar.classList.toggle('still',still());
  text.getAnimations?.().forEach(a=>a.cancel());
  if(still()||!text.animate){setTimeout(next,STILL_MS);return;}
  const track=bar.querySelector('.mr-ticker-track'),w=track.clientWidth,tw=text.scrollWidth,ms=Math.max(7000,(w+tw)*16);
  const anim=text.animate([{transform:`translateX(${w}px)`},{transform:`translateX(${-tw}px)`}],{duration:ms,iterations:item.passes||PASSES,easing:'linear'});
  anim.onfinish=()=>{clearInterval(hold);next();};
  // 🐢 Perf 19/10 (iPad "phản hồi rất lag"): a sheet opened while the line plays. Under a modal (its blurred ::backdrop
  // on a tablet, the masked track) every frame of the scroll redrew the sheet: in WebKit (iPad profile) the main thread
  // was busy ~20 ms of every 50 with the 📊 leaderboard open, 3 ms once paused. The line waits, paused, until the
  // street is in sight again (one cheap check a second, only while a line plays).
  clearInterval(hold);
  hold=setInterval(()=>{if(!bar||!text.isConnected){clearInterval(hold);return;}const stop=covered()||document.hidden;
    if(stop&&anim.playState==='running')anim.pause();else if(!stop&&anim.playState==='paused')anim.play();},1000);
}
