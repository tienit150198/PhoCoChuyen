/** 🐕 Kéo co chó sủa (game/dog_bark.py, live/dog_bark.py; only while the live service's welcome says `bark`).
 * A tug-of-war won by barking into the microphone. Its own dialog, opened from Khu phố ("liveBark"), never part of the
 * Chợ đen. Phone first, few words: one main button in the bottom bar, the rules behind "?".
 *
 * The microphone: getUserMedia({audio}) → Web Audio AnalyserNode, the RMS of each frame in dBFS, a noise floor
 * calibrated in the first second, the loudness ABOVE it as 0..100 (× the player's own "độ nhạy" slider), about 14
 * times a second; four numbers a frame go to the live service (`bark_v`, 4 frames a second). Never audio: no recorder,
 * no upload. See "the microphone" below for why echo cancellation is off and when nothing is sent.
 * The stake: `jr_bark_join {stake}` (escrow, game command), then `bark_find {ticket}` on the socket. The pot or a
 * stake back comes through POST /api/live/effects (collect()). The house dog ("🐕 Chó nhà Mây · Mực") is always
 * shown as the house's own dog: its tag, its breed, no avatar and no profile.
 * Barks: CC0 recordings in /audio/bark/ (public/audio/bark/CREDITS.md), each one played at a pitch, length and loudness
 * of its own per breed. The house dog's barks come from the server (`bark_dog`): the page plays each one exactly while
 * the dog pulls, and shows a "GÂU!" bubble (big when 🔇 is on). */
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
  on('bark_go',f=>{B.ticket=null;B.match=f;B.st={x:f.x||0,a:0,b:0,left:f.left??f.limit};B.end=null;B.view='match';B.dogBarks=0;
    B.cdAt=f.cd==null?null:Date.now()+f.cd*1000;startSend();paint();
    if(B.mic?.status==='live')B.live?.send({t:'bark_ready',m:f.m,floor:Math.round(B.mic.floor)});});   // the rope waits for it
  on('bark_start',f=>{if(B.match?.m!==f.m)return;B.cdAt=Date.now()+(f.cd||0)*1000;paint();});
  on('bark_dog',f=>onDogBark(f));
  on('bark_st',f=>onSt(f));
  on('bark_end',f=>{if(B.match?.m!==f.m)return;stopSend();B.end=f;B.view='end';collect();paint();});
  on('bark_over',f=>{if(B.watch?.m===f.m){B.watch={...B.watch,over:f.winner};paint();}});
  on('bark_room',f=>{B.watch={...f,st:{x:f.x,a:0,b:0,left:f.left}};B.view='watch';paint();});
  on('bark_none',()=>{if(B.view==='match'||B.view==='wait'){B.view='lobby';paint();}});
  on('error',f=>{if(!String(f.ref||'').startsWith('bark_')||f.ref==='bark_v'||f.ref==='bark_cheer'||f.ref==='bark_ready')return;B.busy=false;B.flash={text:f.msg||'Chưa được, thử lại nha.',kind:'bad'};paint();});
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
// Owner 10/10 ("phải sủa mới tính"): only a real bark moves the rope. The page measures its own mic (RMS of each frame in
// dBFS), calibrates the room's noise floor in its first CAL_MS (the 20th percentile, so a shout then does not raise it)
// and sends the loudness ABOVE that floor (levelOf): talking ≈ 30–50, a shout ≈ 70–90; the server counts only what is
// over BARK_MIN. Echo cancellation, noise suppression and auto gain are OFF: echo cancellation ducked the mic exactly
// while the dog's bark played from the speaker (the player was muted at every dog bark), the others flatten a shout.
// The dog's bark may leak back into the mic a little; that can only help the player.
// Nothing is sent while the mic does not deliver: the AudioContext not running (iOS before a tap: "Chạm để bật mic"), or
// digital silence (all-zero frames: a muted or dead input). The server waits for `bark_ready` before the rope starts.
export const BARK_MIN=30,CAL_MS=1000,DEAD_MS=800;
export const dbOf=rms=>rms>1e-9?20*Math.log10(rms):-120;
/** The level the server gets: dB above the floor (never under −52 dBFS: a very quiet room does not turn talk into a shout),
 * one decimal, with a soft knee over 85 so a scream never sits on one number (the server takes a flat level for a hum). */
export function levelOf(db,floor,s=1){
  const base=Math.max(floor+4,-52);let x=(db-base)*2.3*s;
  if(x>85)x=85+15*(1-Math.exp(-(x-85)/15));
  return Math.max(0,Math.min(100,Math.round(x*10)/10));
}
export function floorOf(dbs){const v=[...dbs].filter(Number.isFinite).sort((a,b)=>a-b);return v.length?Math.max(-75,Math.min(-30,v[Math.floor(v.length*.2)])):-60;}
async function micOn(){
  if(B.mic)return true;
  if(!navigator.mediaDevices?.getUserMedia||!(window.AudioContext||window.webkitAudioContext)){B.panel='nomic';return false;}
  const ac=audio();   // created / resumed inside the tap (iOS)
  let stream;
  try{stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false,channelCount:1}});}
  catch(e){B.panel=e?.name==='NotAllowedError'||e?.name==='SecurityError'?'denied':'nomic';return false;}
  if(ac.state!=='running')ac.resume().catch(()=>{});
  const src=ac.createMediaStreamSource(stream),an=ac.createAnalyser();an.fftSize=1024;src.connect(an);
  const m=B.mic={stream,an,data:new Float32Array(an.fftSize),q:[],level:0,db:-120,floor:-60,cal:[],calUntil:0,zeroMs:0,status:'cal'};
  for(const tr of stream.getAudioTracks())tr.addEventListener('ended',()=>{if(B.mic===m)setStatus('dead');});
  calibrate();
  m.t=setInterval(()=>sampleMic(m),SAMPLE_MS);
  return true;
}
function calibrate(){const m=B.mic;if(!m)return;m.cal=[];m.calUntil=Date.now()+CAL_MS;setStatus('cal');}
function setStatus(st){
  const m=B.mic;if(!m||m.status===st)return;m.status=st;
  if(st==='live'&&B.match&&B.view==='match')B.live?.send({t:'bark_ready',m:B.match.m,floor:Math.round(m.floor)});
  paintMic();
}
function sampleMic(m){
  if(B.mic!==m)return;
  if(B.ac?.state!=='running'){m.level=0;setStatus('tap');meter();return;}
  if(m.an.getFloatTimeDomainData)m.an.getFloatTimeDomainData(m.data);
  else{const b=new Uint8Array(m.an.fftSize);m.an.getByteTimeDomainData(b);for(let i=0;i<b.length;i++)m.data[i]=(b[i]-128)/128;}
  let s=0;for(const v of m.data)s+=v*v;
  const rms=Math.sqrt(s/m.data.length);
  if(!(rms>1e-9)){m.zeroMs+=SAMPLE_MS;if(m.zeroMs>=DEAD_MS){m.level=0;setStatus('dead');meter();}return;}
  m.zeroMs=0;m.db=dbOf(rms);
  if(m.status==='dead'||m.status==='tap')calibrate();
  if(Date.now()<m.calUntil){m.cal.push(m.db);m.level=0;meter();return;}
  if(m.status==='cal'){m.floor=floorOf(m.cal);setStatus('live');}
  m.level=levelOf(m.db,m.floor,B.sens);
  m.q.push(m.level);if(m.q.length>8)m.q.shift();
  meter();
}
/** Wait until the mic delivers (or say why not): 'live' | 'cal' | 'tap' | 'dead'. */
async function micReady(ms=2500){
  const end=Date.now()+ms;
  while(B.mic&&B.mic.status!=='live'&&Date.now()<end)await new Promise(r=>setTimeout(r,100));
  return B.mic?.status||'off';
}
function micOff(){const m=B.mic;if(!m)return;clearInterval(m.t);for(const t of m.stream.getTracks())t.stop();B.mic=null;}
function startSend(){
  stopSend();
  B.send=setInterval(()=>{const m=B.mic;if(!m||!B.match||m.status!=='live')return;const v=m.q.splice(0,4);if(v.length)B.live?.send({t:'bark_v',m:B.match.m,v});},SEND_MS);
}
function stopSend(){clearInterval(B.send);B.send=0;}

/* ---------------------------------------------------------------- the barks (CC0 recordings) */
function audio(){if(!B.ac){const C=window.AudioContext||window.webkitAudioContext;B.ac=new C();}if(B.ac.state!=='running')B.ac.resume().catch(()=>{});return B.ac;}
async function sample(k){
  if(B.buf[k])return B.buf[k];
  const url=globalThis.__mnlBoot?.asset?.(`/audio/bark/bark-${k}.mp3`)||`/audio/bark/bark-${k}.mp3`;
  B.buf[k]=fetch(url).then(r=>r.arrayBuffer()).then(b=>audio().decodeAudioData(b)).catch(()=>null);
  return B.buf[k];
}
/** One bark of this dog lasting about `d` seconds: a sample of its breed at its own pitch and loudness each time (a
 * long bark plays a second "gâu" right after). */
async function bark(dog,power=1,d=0.3){
  if(B.mute)return;
  const list=dog?.barks?.length?dog.barks:['a','c','d'],[lo,hi]=dog?.rate||[0.9,1.1];
  const play=async at=>{
    const buf=await sample(list[Math.floor(Math.random()*list.length)]);if(!buf)return 0;
    const ac=audio(),s=ac.createBufferSource(),g=ac.createGain();
    s.buffer=buf;s.playbackRate.value=lo+Math.random()*(hi-lo);
    g.gain.value=.25+.3*Math.min(1,power)*(.75+Math.random()*.25);
    s.connect(g).connect(ac.destination);s.start(ac.currentTime+at);
    return buf.duration/s.playbackRate.value;
  };
  const len=await play(0);
  if(len&&d>len+0.12)play(len+0.04);
}
/** The bubble over a dog for one bark (always; big when the sound is off, so a muted player still sees every bark). */
function woof(which,d){
  const el=B.dlg?.querySelectorAll('.db-side')[which==='opp'?1:0];if(!el)return;
  el.classList.add('barking');el.classList.toggle('loud',B.mute);
  clearTimeout(el._woof);el._woof=setTimeout(()=>el.classList.remove('barking','loud'),Math.max(250,d*1000));
}
/** 🐕 The house dog barks (bark_dog): heard (or seen) exactly while it pulls. */
function onDogBark(f){
  B.dogBarks=(B.dogBarks||0)+1;
  if(B.match?.m===f.m){bark(B.match.opp,(f.p||60)/100,f.d||.3);woof('opp',f.d||.3);}
  else if(B.watch?.m===f.m)woof('opp',f.d||.3);
}
/** A human opponent's dog: barks when their counted level is a bark (the server's `a` / `b`). */
function oppBarks(level){
  const now=Date.now(),dog=B.match?.opp,gap=280+Math.random()*420;
  if(level>=BARK_MIN&&(!B.oppHigh||now-B.lastBark>gap*(level>70?.8:1.3))){B.lastBark=now;bark(dog,level/100,.3);}
  B.oppHigh=level>=BARK_MIN;
}

/* ---------------------------------------------------------------- live state */
function onSt(f){
  if(B.match?.m===f.m){B.st=f;const mine=B.match.side==='a',me=mine?f.a:f.b,op=mine?f.b:f.a;
    if(!B.match.opp?.house){oppBarks(op);if(op>=BARK_MIN)woof('opp',.25);}
    if(me>=BARK_MIN)woof('me',.25);
    if(f.fx)floatFx(f.fx);paintRope();paintMic();return;}
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
    case'test':if(B.mic)calibrate();else await micOn();paint();break;   // 🎙️ also measures the room again
    case'tapmic':audio();if(B.mic?.status==='dead'){micOff();await micOn();}else if(!B.mic)await micOn();paint();break;   // iOS: inside a tap
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
  const st=await micReady();   // owner 10/10: no stake before the mic really delivers
  if(st!=='live'){B.busy=false;B.flash={text:micWhy(st),kind:'bad'};paint();return;}
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
      <li>Chỉ tiếng sủa to (qua vạch trên thanh đo) mới kéo dây. Im lặng hay nói chuyện: dây đứng yên.</li>
      <li>Kéo tới vạch là thắng. Hết ${Math.round(B.info?.match_s||45)} giây: dây lệch bên nào bên đó thắng, giữa là hòa.</li>
      <li>Thắng ăn cả hai phần cược. Hòa trả cược. Thoát hoặc mất mạng quá 10 giây là thua.</li>
      <li>Sau ${Math.round(B.info?.dog_after||20)} giây không có ai, bạn đấu với chó nhà Mây (chó của game, không phải người chơi).</li>
      <li>Chỉ gửi độ to (con số), không gửi giọng nói. Độ nhạy chỉnh ở dưới.</li></ul></details>
    <button type="button" class="icon-btn db-x" data-db="close" aria-label="Đóng">✕</button></header>`;
}
function flash(){return B.flash?`<p class="db-flash ${B.flash.kind||''}">${esc(B.flash.text)}</p>`:'';}
/** Why the mic does not count yet, in a few words. */
function micWhy(st){
  return st==='tap'?'👆 Chạm để bật mic':st==='dead'?'🎙️ Mic không có tiếng. Kiểm tra quyền mic rồi chạm thử lại.':st==='cal'?'Đang đo tiếng ồn, giữ yên 1 giây…':'🎙️ Chưa bật mic';
}
function micLine(){
  const st=B.mic?.status||'off';
  if(st==='tap'||st==='dead')return `<button type="button" class="btn db-tapmic" data-db="tapmic">${esc(micWhy(st))}</button>`;
  return `<span class="db-micst">${st==='live'?'🎙️ Sủa qua vạch là kéo':esc(micWhy(st))}</span>`;
}
function sensRow(){
  return `<div class="db-sens"><label><span>🎚️ Độ nhạy</span><input type="range" min="0.5" max="2.5" step="0.1" value="${B.sens}" data-db-sens aria-label="Độ nhạy mic"></label>
    <i class="db-meter" aria-hidden="true" style="--bark:${BARK_MIN}%"><b style="width:${B.mic?.level||0}%"></b></i><div class="db-micline" data-db-mic>${micLine()}</div></div>`;
}
function paintMic(){const el=B.dlg?.querySelector('[data-db-mic]');if(el){const h=micLine();if(el.innerHTML!==h)el.innerHTML=h;}}
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
  const why=e.why==='gone'?(e.result==='win'?'Đối thủ mất kết nối.':'Mất kết nối quá lâu.'):e.why==='quit'?(e.result==='win'?'Đối thủ bỏ trận.':'Bạn đã bỏ trận.')
    :e.why==='nomic'?(e.result==='draw'&&!B.st?.x?'Mic chưa có tiếng, đã trả cược.':'Mic tắt quá lâu, chốt theo dây.'):'';
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
function meter(){const b=B.dlg?.querySelector('.db-meter b');if(b){const v=B.mic?.level||0;b.style.width=`${v}%`;b.classList.toggle('on',v>=BARK_MIN);}}
/** The marker and the shake: my end is on the left (x > 0 is side a's end). */
function paintRope(){
  const d=B.dlg;if(!d)return;
  const st=B.view==='watch'?B.watch?.st:B.st;if(!st)return;
  const mine=B.view==='watch'||B.match?.side!=='b',x=mine?st.x:-st.x,my=mine?st.a:st.b,op=mine?st.b:st.a;
  const r=d.querySelector('.db-rope');if(r){r.style.setProperty('--x',`${50-x/2}%`);r.style.setProperty('--shake',`${Math.min(6,(my+op)/30)}px`);r.classList.toggle('hot',my+op>90);}
  const a=d.querySelector('.db-lv.me b'),b=d.querySelector('.db-lv.opp b');if(a)a.style.width=`${my}%`;if(b)b.style.width=`${Math.min(100,op)}%`;
  if(B.view==='watch'){const sides=d.querySelectorAll('.db-side');sides[0]?.classList.toggle('barking',my>=BARK_MIN);if(!B.watch?.b?.house)sides[1]?.classList.toggle('barking',op>=BARK_MIN);}
  const l=d.querySelector('[data-db-left]');if(l)l.textContent=`${Math.ceil(st.left||0)}s`;
}
function tickUI(){
  if(!B.dlg?.open)return;
  if(B.view==='wait'){const s=Math.floor((Date.now()-B.waitAt)/1000),c=B.dlg.querySelector('[data-db-clock]'),n=B.dlg.querySelector('[data-db-dogin]'),left=Math.max(0,Math.round((B.info?.dog_after||20)-s));
    if(c)c.textContent=`${s}s`;if(n)n.textContent=left>0?`Không có ai sau ${left}s thì đấu với chó nhà Mây.`:'Đang gọi chó nhà Mây…';}
  if(B.view==='match'){const c=B.dlg.querySelector('[data-db-cd]'),left=B.cdAt?Math.ceil((B.cdAt-Date.now())/1000):0;
    if(c)c.textContent=!B.cdAt?(B.mic?.status==='live'?'⏳ Chờ đối thủ bật mic…':'⏳ Chờ mic của bạn…'):left>0?`${left}… chuẩn bị sủa!`:B.st?.w?.length?'⏸ Chờ mic…':'';}
}
