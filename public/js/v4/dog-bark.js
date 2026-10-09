/** 🐕 Kéo co chó sủa (game/dog_bark.py, live/dog_bark.py; only while the live service's welcome says `bark`).
 * A tug-of-war won by barking into the microphone. Its own dialog, opened from Khu phố ("liveBark"), never part of the
 * Chợ đen. Phone first, few words: one main button in the bottom bar, the rules behind "?".
 *
 * The microphone: getUserMedia({audio}) → Web Audio AnalyserNode, the RMS of each frame as a loudness 0..100 (×
 * the player's own "độ nhạy" slider), about 14 times a second; four numbers a frame go to the live service
 * (`bark_v`, 4 frames a second, under the socket's 8 frames/s). Never audio: no recorder, no upload. Automatic gain
 * control off (it would flatten a shout), echo cancellation on (the barks the page plays stay out of the mic).
 * The stake: `jr_bark_join {stake}` (escrow, game command), then `bark_find {ticket}` on the socket. The pot or a
 * stake back comes through POST /api/live/effects (collect()). The house dog ("🐕 Chó nhà Mây · Mực") is always
 * shown as the house's own dog: its tag, its breed, no avatar and no profile.
 * Barks: CC0 recordings in /audio/bark/ (public/audio/bark/CREDITS.md), each one played at a pitch, length and loudness
 * of its own per breed; only the opponent's dog makes a sound (your own dog only shows it), quiet enough not to feed
 * your mic. 🔇 turns them off. */
import {escapeHTML as esc} from '../icons.js';
import {actBar} from '../ui-kit.js';
import {stylesheet} from '../lazy.js';

const STAKES=[100,200,500,1000,5000],SEND_MS=250,SAMPLE_MS=70,CHEERS=['👏','🔥'];
const BARKS=['a','b','c','d','e','f','g'];
const B={dlg:null,env:null,live:null,bound:false,view:'lobby',info:null,lobby:null,stake:200,busy:false,flash:null,
  ticket:null,waitAt:0,match:null,st:null,end:null,watch:null,mic:null,sens:sens(),mute:muted(),timer:0,poll:0,
  ac:null,buf:{},lastBark:0,oppHigh:false,fx:[],panel:null,year:''};
function sens(){try{const v=Number(localStorage.getItem('mnl.bark.sens'));return v>=0.5&&v<=2.5?v:1;}catch{return 1;}}
function muted(){try{return localStorage.getItem('mnl.bark.mute')==='1';}catch{return false;}}
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const wallet=()=>B.env?.api?.state?.journey?.wallet??0;
const toast=(t,bad)=>B.env?.toast?.(t,bad);

/* ---------------------------------------------------------------- the socket */
async function socket(){
  if(B.live)return B.live;
  try{const m=await import('./live.js');B.live=m.live;}catch{return null;}
  return B.live;
}
function bind(){
  if(B.bound||!B.live)return;B.bound=true;
  const on=(t,fn)=>B.live.on(t,f=>{try{fn(f);}catch(e){console.warn('bark:',t,e);}});
  on('bark_lobby',f=>{B.lobby=f;if(B.view==='lobby')paint();});
  on('bark_wait',f=>{if(f.ticket!==B.ticket&&B.ticket)return;B.ticket=f.ticket;B.view='wait';B.waitAt=Date.now()-(f.waited||0)*1000;B.busy=false;paint();});
  on('bark_info',f=>{if(f.ticket===B.ticket){B.flash={text:f.msg,kind:'bad'};paint();}});
  on('bark_back',f=>{if(f.ticket!==B.ticket)return;B.ticket=null;B.view='lobby';B.flash={text:f.why==='wait'?'Chưa có ai, cược đã trả lại ví.':'Đã hủy, cược trả lại ví.',kind:'good'};collect();paint();lobby();});
  on('bark_go',f=>{B.ticket=null;B.match=f;B.st={x:f.x||0,a:0,b:0,left:f.left??f.limit};B.end=null;B.view='match';B.cdAt=Date.now()+(f.cd||0)*1000;startSend();paint();});
  on('bark_st',f=>onSt(f));
  on('bark_end',f=>{if(B.match?.m!==f.m)return;stopSend();B.end=f;B.view='end';collect();paint();});
  on('bark_over',f=>{if(B.watch?.m===f.m){B.watch={...B.watch,over:f.winner};paint();}});
  on('bark_room',f=>{B.watch={...f,st:{x:f.x,a:0,b:0,left:f.left}};B.view='watch';paint();});
  on('bark_none',()=>{if(B.view==='match'||B.view==='wait'){B.view='lobby';paint();}});
  on('error',f=>{if(!String(f.ref||'').startsWith('bark_')||f.ref==='bark_v'||f.ref==='bark_cheer')return;B.busy=false;B.flash={text:f.msg||'Chưa được, thử lại nha.',kind:'bad'};paint();});
  on('welcome',()=>{if(B.dlg?.open){B.live.send({t:'bark_rejoin'});lobby();}});
}
function lobby(){B.live?.send({t:'bark_lobby'});}

/** The pot / a stake back into the wallet now (the same as on load: game/live_effects.py). */
async function collect(){
  const api=B.env?.api;if(!api)return;
  try{const d=await api.post('/api/live/effects',{});if(d?.paid&&d.state&&typeof d.revision==='number'){api.accept({state:d.state,revision:d.revision});B.env.renderMain?.();}}
  catch(e){console.warn('bark: collect',e);}
}
async function loadInfo(){
  try{B.info=await B.env.api.json('/api/dogbark');}catch{B.info=B.info||{on:false};}
  const o=B.info?.me?.open;
  if(o&&o.status==='wait'&&!B.ticket){B.ticket=o.ticket;B.live?.send({t:'bark_find',ticket:o.ticket});}
}

/* ---------------------------------------------------------------- the microphone */
export function levelOf(rms,s=1){   // RMS of a frame (0..1) → 0..100: −60 dBFS is silence, −10 dBFS a shout
  if(!(rms>0))return 0;const db=20*Math.log10(rms);
  return Math.max(0,Math.min(100,Math.round((db+60)*2*s)));
}
async function micOn(){
  if(B.mic)return true;
  if(!navigator.mediaDevices?.getUserMedia||!(window.AudioContext||window.webkitAudioContext)){B.panel='nomic';return false;}
  let stream;
  try{stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:false,autoGainControl:false,channelCount:1}});}
  catch(e){B.panel=e?.name==='NotAllowedError'||e?.name==='SecurityError'?'denied':'nomic';return false;}
  const ac=audio();const src=ac.createMediaStreamSource(stream),an=ac.createAnalyser();an.fftSize=1024;src.connect(an);
  B.mic={stream,an,data:new Float32Array(an.fftSize),q:[],level:0,peak:0};
  B.mic.t=setInterval(()=>{const m=B.mic;if(!m)return;m.an.getFloatTimeDomainData(m.data);let s=0;for(const v of m.data)s+=v*v;
    m.level=levelOf(Math.sqrt(s/m.data.length),B.sens);m.q.push(m.level);if(m.q.length>8)m.q.shift();meter();},SAMPLE_MS);
  return true;
}
function micOff(){const m=B.mic;if(!m)return;clearInterval(m.t);for(const t of m.stream.getTracks())t.stop();B.mic=null;}
function startSend(){
  stopSend();
  B.send=setInterval(()=>{const m=B.mic;if(!m||!B.match||Date.now()<B.cdAt)return;const v=m.q.splice(0,4);if(v.length)B.live?.send({t:'bark_v',m:B.match.m,v});},SEND_MS);
}
function stopSend(){clearInterval(B.send);B.send=0;}

/* ---------------------------------------------------------------- the barks (CC0 recordings) */
function audio(){if(!B.ac){const C=window.AudioContext||window.webkitAudioContext;B.ac=new C();}if(B.ac.state==='suspended')B.ac.resume().catch(()=>{});return B.ac;}
async function sample(k){
  if(B.buf[k])return B.buf[k];
  const url=globalThis.__mnlBoot?.asset?.(`/audio/bark/bark-${k}.mp3`)||`/audio/bark/bark-${k}.mp3`;
  B.buf[k]=fetch(url).then(r=>r.arrayBuffer()).then(b=>audio().decodeAudioData(b)).catch(()=>null);
  return B.buf[k];
}
/** One bark of this dog: a sample of its breed, its own pitch, length and loudness each time (never the same twice). */
async function bark(dog,power=1){
  if(B.mute)return;
  const list=dog?.barks?.length?dog.barks:['a','c','d'],[lo,hi]=dog?.rate||[0.9,1.1];
  const buf=await sample(list[Math.floor(Math.random()*list.length)]);if(!buf)return;
  const ac=audio(),s=ac.createBufferSource(),g=ac.createGain();
  s.buffer=buf;s.playbackRate.value=lo+Math.random()*(hi-lo);
  g.gain.value=.18+.22*Math.min(1,power)*(.7+Math.random()*.3);
  s.connect(g).connect(ac.destination);
  const cut=Math.random()<.35?buf.duration*(.55+Math.random()*.3):buf.duration;   // a short "gâu" now and then
  s.start(0,0,cut);
}
function oppBarks(level){
  const now=Date.now(),dog=B.match?.opp,gap=280+Math.random()*420;
  if(level>=35&&(!B.oppHigh||now-B.lastBark>gap*(level>70?.8:1.3))){B.lastBark=now;bark(dog,level/100);if(level>78&&Math.random()<.4)setTimeout(()=>bark(dog,level/100),140+Math.random()*120);}
  B.oppHigh=level>=35;
}

/* ---------------------------------------------------------------- live state */
function onSt(f){
  if(B.match?.m===f.m){B.st=f;const mine=B.match.side==='a';oppBarks(mine?f.b:f.a);if(f.fx)floatFx(f.fx);paintRope();return;}
  if(B.watch?.m===f.m){B.watch.st=f;if(f.fx)floatFx(f.fx);paintRope();}
}
function floatFx(fx){
  const box=B.dlg?.querySelector('.db-fx');if(!box)return;
  for(const [e,n] of Object.entries(fx))for(let i=0;i<Math.min(n,5);i++){const s=document.createElement('span');s.textContent=e;s.style.left=`${10+Math.random()*80}%`;s.style.animationDelay=`${i*90}ms`;box.append(s);setTimeout(()=>s.remove(),1800);}
}

/* ---------------------------------------------------------------- the dialog */
function dialog(){
  if(B.dlg)return B.dlg;
  const d=document.createElement('dialog');d.className='sheet v4-sheet narrow db-sheet';d.setAttribute('aria-labelledby','db-title');
  d.innerHTML='<div class="db-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{audio();if(e.target===d){close();return;}
    const el=e.target.closest('[data-db]');if(!el||!d.contains(el)||el.disabled)return;e.preventDefault();act(el.dataset.db,el.dataset);});
  d.addEventListener('input',e=>{
    if(e.target.matches('[data-db-sens]')){B.sens=Number(e.target.value);try{localStorage.setItem('mnl.bark.sens',String(B.sens));}catch{}}
    if(e.target.matches('[data-db-stake]')){B.stake=Math.max(0,Math.floor(Number(e.target.value)||0));const b=d.querySelector('[data-db="find"]');if(b)b.textContent=findLabel();}
    if(e.target.matches('[data-db-year]'))B.year=e.target.value;
  });
  d.addEventListener('cancel',e=>{e.preventDefault();close();});
  d.addEventListener('close',()=>{clearInterval(B.timer);clearInterval(B.poll);stopSend();if(B.view!=='match')micOff();B.live?.send({t:'bark_unwatch'});});
  B.dlg=d;return d;
}
async function close(){
  if(B.view==='match'&&!B.end){
    if(!(await B.env.confirmAction?.('Bỏ trận?','Bỏ giữa chừng là thua kèo này.','Bỏ trận')))return;
    B.live?.send({t:'bark_quit',m:B.match.m});
  }
  if(B.view==='wait'&&B.ticket)cancelTicket();
  B.dlg?.close();
}
function cancelTicket(){
  const t=B.ticket;if(!t)return;
  if(!B.live?.send({t:'bark_cancel',ticket:t}))B.env.api.post('/api/dogbark/cancel',{ticket:t}).then(()=>collect()).catch(()=>{});
}

/** The menu entry, the town map's door. */
export async function openDogBark(env){
  B.env=env;await stylesheet('/css/dog-bark.css');
  const d=dialog();if(!d.open)d.showModal();
  const lv=await socket();bind();
  B.flash=null;if(!['match','wait'].includes(B.view))B.view='lobby';
  paint();
  await loadInfo();
  lv?.send({t:'bark_rejoin'});lobby();paint();
  clearInterval(B.timer);B.timer=setInterval(tickUI,250);
  clearInterval(B.poll);B.poll=setInterval(()=>{if(d.open&&B.view==='lobby')lobby();},4000);
}
export async function dogBarkAction(action,data,el,env){if(action!=='liveBark')return false;await openDogBark(env);return true;}

async function act(a,ds){
  switch(a){
    case'close':await close();break;
    case'stake':B.stake=Number(ds.v)||B.stake;paint();break;
    case'find':await find();break;
    case'cancel':cancelTicket();break;
    case'again':B.view='lobby';B.end=null;B.match=null;await loadInfo();lobby();paint();break;
    case'quit':if(await B.env.confirmAction?.('Bỏ trận?','Bỏ giữa chừng là thua kèo này.','Bỏ trận'))B.live?.send({t:'bark_quit',m:B.match?.m});break;
    case'watch':B.live?.send({t:'bark_watch',m:ds.m});break;
    case'unwatch':B.live?.send({t:'bark_unwatch'});B.watch=null;B.view='lobby';lobby();paint();break;
    case'cheer':if(B.watch)B.live?.send({t:'bark_cheer',m:B.watch.m,e:ds.e});break;
    case'mute':B.mute=!B.mute;try{localStorage.setItem('mnl.bark.mute',B.mute?'1':'0');}catch{}paint();break;
    case'test':if(await micOn())paint();else paint();break;
    case'panel':B.panel=null;paint();break;
    case'birth':await saveYear();break;
  }
}
async function saveYear(){
  const y=Number(B.year);if(!Number.isInteger(y)||y<1920){B.flash={text:'Chọn năm sinh của bạn nha.',kind:'bad'};paint();return;}
  B.busy=true;paint();
  try{const r=await B.env.api.post('/api/karaoke/birth',{year:y});B.panel=null;await loadInfo();if(!r.mic)B.panel='young';}
  catch(e){B.flash={text:e.message||'Chưa lưu được.',kind:'bad'};}
  B.busy=false;paint();
}
async function find(){
  const me=B.info?.me,stake=B.stake;
  if(me?.code==='bark_birth'){B.panel='birth';paint();return;}
  if(me?.code==='bark_young'){B.panel='young';paint();return;}
  if(me?.code){B.flash={text:me.why,kind:'bad'};paint();return;}
  if(!(stake>=(B.info?.min||100))){B.flash={text:`Cược ít nhất ${fmt(B.info?.min||100)} xu nha.`,kind:'bad'};paint();return;}
  if(stake>wallet()){B.flash={text:'Ví không đủ cho kèo này.',kind:'bad'};paint();return;}
  B.busy=true;paint();
  if(!(await micOn())){B.busy=false;paint();return;}   // no microphone: a short reason, no stake taken
  try{
    const r=await B.env.api.command('jr_bark_join',{stake});
    B.ticket=r?.bark?.ticket||r?.result?.bark?.ticket||null;
    if(!B.ticket){await loadInfo();B.ticket=B.info?.me?.open?.ticket||null;}
    B.view='wait';B.waitAt=Date.now();B.flash=null;
    if(!B.live?.send({t:'bark_find',ticket:B.ticket}))B.flash={text:'Mất kết nối, đang nối lại…',kind:'bad'};
  }catch(e){
    const code=e.data?.code||e.code;
    if(code==='bark_birth')B.panel='birth';else if(code==='bark_young')B.panel='young';
    else B.flash=e.quiet?null:{text:e.message||'Chưa đặt được kèo.',kind:'bad'};
  }
  B.busy=false;paint();
}

/* ---------------------------------------------------------------- painting */
const findLabel=()=>`🐕 Tìm đối thủ · ${fmt(B.stake)} xu`;
function head(){
  return `<header class="db-head"><span class="db-logo" aria-hidden="true">🐕</span><h2 id="db-title">Kéo co chó sủa</h2>
    <span class="db-wallet">👛 ${fmt(wallet())}</span>
    <details class="db-help"><summary aria-label="Luật chơi">?</summary><ul>
      <li>Sủa to vào mic, ai to hơn kéo dây về phía mình.</li>
      <li>Kéo tới vạch là thắng. Hết ${Math.round(B.info?.match_s||45)} giây: dây lệch bên nào bên đó thắng, giữa là hòa.</li>
      <li>Thắng ăn cả hai phần cược. Hòa trả cược. Thoát hoặc mất mạng quá 10 giây là thua.</li>
      <li>Sau ${Math.round(B.info?.dog_after||20)} giây không có ai, bạn đấu với chó nhà Mây (chó của game, không phải người chơi).</li>
      <li>Chỉ gửi độ to (con số), không gửi giọng nói. Độ nhạy chỉnh ở dưới.</li></ul></details>
    <button type="button" class="icon-btn db-x" data-db="close" aria-label="Đóng">✕</button></header>`;
}
function flash(){return B.flash?`<p class="db-flash ${B.flash.kind||''}">${esc(B.flash.text)}</p>`:'';}
function sensRow(){
  return `<label class="db-sens"><span>🎚️ Độ nhạy</span><input type="range" min="0.5" max="2.5" step="0.1" value="${B.sens}" data-db-sens aria-label="Độ nhạy mic">
    <i class="db-meter" aria-hidden="true"><b style="width:${B.mic?.level||0}%"></b></i></label>`;
}
function panel(){
  if(B.panel==='denied'||B.panel==='nomic')return `<div class="db-panel"><p>🎙️ ${B.panel==='denied'?'Chưa cho dùng mic nên chưa chơi được. Cho phép mic trong trình duyệt rồi thử lại nha.':'Máy này chưa có mic dùng được.'}</p><button type="button" class="btn" data-db="panel">OK</button></div>`;
  if(B.panel==='young')return `<div class="db-panel"><p>Kéo co bằng mic dành cho bạn từ 16 tuổi nha. Bạn vẫn xem và cổ vũ được 👏</p><button type="button" class="btn" data-db="panel">OK</button></div>`;
  if(B.panel==='birth')return `<div class="db-panel"><p>Năm sinh của bạn? (hỏi một lần)</p>
    <input type="number" inputmode="numeric" min="1920" max="2026" placeholder="2000" value="${esc(B.year)}" data-db-year class="db-year">
    <button type="button" class="btn primary" data-db="birth"${B.busy?' disabled':''}>Lưu</button></div>`;
  return '';
}
function lobbyView(){
  const i=B.info,me=i?.me,lob=B.lobby,k=i?.king;
  const waits=(lob?.wait||[]).map(([s,n])=>`<button type="button" class="db-chip db-wait-chip${s===B.stake?' on':''}" data-db="stake" data-v="${s}">👤 ${fmt(s)}${n>1?` ×${n}`:''}</button>`).join('');
  const chips=STAKES.map(s=>`<button type="button" class="db-chip${s===B.stake?' on':''}" data-db="stake" data-v="${s}">${fmt(s)}</button>`).join('');
  const ms=(lob?.matches||[]).slice(0,6).map(m=>`<li><button type="button" class="db-live" data-db="watch" data-m="${esc(m.m)}">
    <span>${esc(m.a.name)}</span><b>vs</b><span>${m.b.house?'🐕 ':''}${esc(m.b.name)}</span><small>${fmt(m.stake)} xu</small></button></li>`).join('');
  const cool=me?.cool>0?`<p class="db-flash bad">⏳ Nghỉ cổ họng ${Math.ceil(me.cool/60)} phút nữa nha.</p>`:'';
  return `${k?.name?`<p class="db-king">👑 ${esc(k.title)} tuần: <b>${esc(k.name)}</b> · +${fmt(k.xu)} xu</p>`:''}
    <p class="db-lead">Không có ai thì đấu với chó nhà Mây.</p>
    ${flash()}${cool}${panel()}
    <div class="db-card"><h3>Cược</h3><div class="db-chips">${chips}</div>
      <label class="db-num"><input type="number" inputmode="numeric" min="${i?.min||100}" step="50" value="${B.stake}" data-db-stake aria-label="Số xu cược khác"><span aria-hidden="true">xu</span></label>
      ${waits?`<p class="db-sub">Đang chờ kèo:</p><div class="db-chips">${waits}</div>`:''}</div>
    <div class="db-card db-mic">${sensRow()}<div class="db-row"><button type="button" class="btn small" data-db="test" aria-label="Thử mic" title="Thử mic">🎙️</button>
      <button type="button" class="btn small" data-db="mute" aria-label="Tiếng chó sủa" title="Tiếng chó sủa">${B.mute?'🔇':'🔊'}</button></div></div>
    ${ms?`<div class="db-card"><h3>Đang kéo · xem</h3><ul class="db-lives">${ms}</ul></div>`:''}
    ${actBar({next:me&&me.dog_room<B.stake?`<span class="ui-note">${me.dog_room>=(i?.min||100)?`🐕 nhận ≤ ${fmt(me.dog_room)} xu`:'🐕 nghỉ hôm nay'}</span>`:'',
      main:`<button type="button" class="btn primary big" data-db="find"${B.busy||me?.cool>0||i?.on===false?' disabled':''}>${findLabel()}</button>`,cls:'db-bar'})}`;
}
function waitView(){
  const s=Math.floor((Date.now()-B.waitAt)/1000),dogIn=Math.max(0,Math.round((B.info?.dog_after||20)-s));
  return `<div class="db-waiting"><div class="db-dog-run" aria-hidden="true">🐕</div>
    <p class="db-big">Đang tìm đối thủ… <b data-db-clock>${s}s</b></p>
    <p class="db-sub" data-db-dogin>${dogIn>0?`Không có ai sau ${dogIn}s thì đấu với chó nhà Mây.`:'Đang gọi chó nhà Mây…'}</p>
    ${flash()}${sensRow()}</div>
    ${actBar({main:`<button type="button" class="btn big" data-db="cancel">Hủy · trả cược</button>`,cls:'db-bar'})}`;
}
function sideCard(name,dog,me){
  const tag=dog?.house?`<small class="db-tag">🐕 ${esc(dog.tag||'Chó nhà Mây')}</small>`:'';
  return `<div class="db-side${me?' me':''}"><span class="db-pup ${dog?.size||''}" aria-hidden="true">${dog?.house?esc(dog.emoji||'🐕'):'🐶'}<i class="db-woof">GÂU!</i></span>
    <b>${esc(dog?.house?dog.name:name)}</b>${tag}${dog?.house?`<small>${esc(dog.kind||'')}</small>`:me?'<small>Bạn</small>':''}</div>`;
}
function ropeHTML(){
  return `<div class="db-rope-wrap"><div class="db-fx" aria-hidden="true"></div><div class="db-rope"><i class="db-line"></i><i class="db-mid"></i><i class="db-flag"></i></div>
    <div class="db-bars"><i class="db-lv me"><b></b></i><i class="db-lv opp"><b></b></i></div></div>`;
}
function matchView(){
  const m=B.match;
  return `<div class="db-match"><div class="db-sides">${sideCard(m.me.name,null,true)}<span class="db-vs">vs</span>${sideCard(m.opp.name,m.opp,false)}</div>
    <p class="db-pot">🏆 ${fmt(m.pot)} xu · <b data-db-left>${Math.ceil(B.st?.left??m.limit)}s</b></p>
    ${ropeHTML()}<p class="db-cd" data-db-cd></p>${sensRow()}</div>
    ${actBar({next:`<button type="button" class="btn small" data-db="mute">${B.mute?'🔇':'🔊'}</button>`,main:`<button type="button" class="btn big" data-db="quit">Bỏ trận</button>`,cls:'db-bar'})}`;
}
function endView(){
  const e=B.end,txt=e.result==='win'?`Thắng! +${fmt(e.pay)} xu`:e.result==='draw'?`Hòa · trả ${fmt(e.pay)} xu`:'Thua kèo này';
  const why=e.why==='gone'?(e.result==='win'?'Đối thủ mất kết nối.':'Mất kết nối quá lâu.'):e.why==='quit'?(e.result==='win'?'Đối thủ bỏ trận.':'Bạn đã bỏ trận.'):'';
  const m=B.match,opp=m?.opp?.house?`🐕 ${m.opp.tag} · ${m.opp.name}`:m?.opp?.name||'';
  return `<div class="db-result ${e.result}"><div class="db-result-dog" aria-hidden="true">${e.result==='win'?'🏆':e.result==='draw'?'🤝':'🐕'}</div><p class="db-big">${txt}</p>
    <p class="db-sub">${esc(opp)} · ${e.result==='lose'?`−${fmt(m?.stake)} xu`:`cược ${fmt(m?.stake)} xu`}</p>${why?`<p class="db-sub">${why}</p>`:''}${e.saved===false?'<p class="db-sub">Đang chốt kèo, tiền về sau ít phút.</p>':''}</div>
    ${actBar({main:`<button type="button" class="btn primary big" data-db="again">🐕 Kèo nữa</button>`,cls:'db-bar'})}`;
}
function watchView(){
  const w=B.watch;
  return `<div class="db-match watch"><div class="db-sides">${sideCard(w.a.name,null,false)}<span class="db-vs">vs</span>${sideCard(w.b.name,w.b.house?{house:true,tag:'Chó nhà Mây',name:w.b.name.split(' · ').pop(),emoji:w.b.emoji}:null,false)}</div>
    <p class="db-pot">${fmt(w.stake)} xu · <b data-db-left>${Math.ceil(w.st?.left??0)}s</b>${w.over?` · ${w.over==='draw'?'Hòa':'Xong'}`:''}</p>${ropeHTML()}
    <div class="db-cheers">${CHEERS.map(e=>`<button type="button" class="db-chip" data-db="cheer" data-e="${e}">${e}</button>`).join('')}</div></div>
    ${actBar({main:`<button type="button" class="btn big" data-db="unwatch">Về sảnh</button>`,cls:'db-bar'})}`;
}
function paint(){
  const root=B.dlg?.querySelector('.db-root');if(!root)return;
  const off=B.live&&!B.live.flags?.bark&&B.live.welcomed;
  const body=off?'<p class="db-lead">Kéo co chó sủa đang nghỉ, quay lại sau nha.</p>':
    B.view==='wait'?waitView():B.view==='match'&&B.match?matchView():B.view==='end'&&B.end?endView():B.view==='watch'&&B.watch?watchView():lobbyView();
  root.innerHTML=head()+`<div class="db-body">${body}</div>`;
  paintRope();
}
function meter(){const b=B.dlg?.querySelector('.db-meter b');if(b)b.style.width=`${B.mic?.level||0}%`;}
/** The marker and the shake: my end is on the left (x > 0 is side a's end). */
function paintRope(){
  const d=B.dlg;if(!d)return;
  const st=B.view==='watch'?B.watch?.st:B.st;if(!st)return;
  const mine=B.view==='watch'||B.match?.side!=='b',x=mine?st.x:-st.x,my=mine?st.a:st.b,op=mine?st.b:st.a;
  const r=d.querySelector('.db-rope');if(r){r.style.setProperty('--x',`${50-x/2}%`);r.style.setProperty('--shake',`${Math.min(6,(my+op)/30)}px`);r.classList.toggle('hot',my+op>90);}
  const a=d.querySelector('.db-lv.me b'),b=d.querySelector('.db-lv.opp b');if(a)a.style.width=`${my}%`;if(b)b.style.width=`${Math.min(100,op)}%`;
  const sides=d.querySelectorAll('.db-side');sides[0]?.classList.toggle('barking',my>=35);sides[1]?.classList.toggle('barking',op>=35);
  const l=d.querySelector('[data-db-left]');if(l)l.textContent=`${Math.ceil(st.left||0)}s`;
}
function tickUI(){
  if(!B.dlg?.open)return;
  if(B.view==='wait'){const s=Math.floor((Date.now()-B.waitAt)/1000),c=B.dlg.querySelector('[data-db-clock]'),n=B.dlg.querySelector('[data-db-dogin]'),left=Math.max(0,Math.round((B.info?.dog_after||20)-s));
    if(c)c.textContent=`${s}s`;if(n)n.textContent=left>0?`Không có ai sau ${left}s thì đấu với chó nhà Mây.`:'Đang gọi chó nhà Mây…';}
  if(B.view==='match'){const c=B.dlg.querySelector('[data-db-cd]'),left=Math.ceil((B.cdAt-Date.now())/1000);if(c)c.textContent=left>0?`${left}… chuẩn bị sủa!`:'';}
}
