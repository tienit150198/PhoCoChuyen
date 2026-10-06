/** 🎤 Phòng hát Mây (live/karaoke.py, game/karaoke.py; only while the live service's welcome says `kara`).
 * Three public rooms (Nhạc trẻ, Bolero, Quốc tế), everyone watching the same YouTube video at the same second: the
 * official IFrame player (youtube-nocookie.com, ads and logo as YouTube shows them, never covered or hidden for a
 * game), a queue, the singer on stage, reactions, a cheer meter, bubbles, xu tips, a 10 s applause moment, and 🧩 Đoán
 * bài (a lyric line with blanks or emoji clues; guesses are typed in the same box). No voice in v1.
 *
 * The clock: `kara_time` five times on entering, the reply with the smallest round trip gives the server offset; a song
 * plays from (server now − at). Every second a playing video more than DRIFT seconds off is sought back; nothing is
 * corrected while YouTube is not playing (an ad, buffering). Phone first, few words: one bottom bar, one main button
 * (🎤 Thêm bài, or Gửi once something is typed); the rest sits behind ⋯. */
import {icon,escapeHTML as esc} from '../icons.js';
import {live} from './live.js';
import {stylesheet} from '../lazy.js';
import {duck} from '../audio.js';

const DRIFT=.35,REACT=['👏','❤️','🔥','🌹'],YT_HOST='https://www.youtube-nocookie.com';
const K={dlg:null,env:null,bound:false,view:'list',rooms:null,room:null,stage:null,queue:[],round:null,n:0,people:[],said:[],fx:{},cheer:0,
  off:0,best:9,c:0,sent:{},yt:null,player:null,ready:false,vid:null,e:null,durSent:null,timer:0,tick:0,panel:null,song:null,busy:false,
  err:'',ticket:null,clap:null,startAt:0,blanks:new Set(),mode:'lyric',want:false,near:0,won:null,reveal:null};
const snow=()=>Date.now()/1000+K.off;
const rid=()=>(crypto.randomUUID?.()||Math.random().toString(36).slice(2)+Date.now().toString(36)).replace(/[^A-Za-z0-9-]/g,'').slice(0,40);
const fmt=s=>{s=Math.max(0,Math.round(s));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;};
const toast=(t,bad)=>K.env?.toast?.(t,bad);

/* ---------------------------------------------------------------- the socket */
function bind(){
  if(K.bound)return;K.bound=true;
  const on=(t,fn)=>live.on(t,f=>{try{fn(f);}catch(e){console.warn('kara:',t,e);}});
  on('kara_time',f=>{const t0=K.sent[f.c];delete K.sent[f.c];if(!t0)return;const t1=Date.now()/1000,rtt=t1-t0;if(rtt<K.best){K.best=rtt;K.off=f.at-(t0+t1)/2;}});
  on('kara_list',f=>{K.rooms=f.rooms||[];if(K.view==='list')render();});
  on('kara_room',f=>{enterRoom(f);});
  on('kara_left',f=>{if(f.why==='out')return;leaveLocal();toast(f.why==='kick'?'Bạn đã được mời ra khỏi phòng.':f.why==='closed'?'Phòng tạm đóng.':'Bạn đã vào phòng ở tab khác.',f.why!=='other');});
  on('kara_ppl',f=>{if(!here(f))return;K.n=f.n;if(f.on){if(!K.people.some(p=>p.pid===f.pid))K.people.push({pid:f.pid,name:f.name});}else K.people=K.people.filter(p=>p.pid!==f.pid);paint();});
  on('kara_q',f=>{if(!here(f))return;K.queue=f.queue||[];paint();});
  on('kara_play',f=>{if(!here(f))return;K.stage={...f,phase:'deck',votes:0,need:1,hearts:0,cheers:0,tips:0};K.clap=null;K.cheer=0;play();paint();});
  on('kara_stage',f=>{if(!here(f))return;const was=K.stage?.e;K.stage=f.stage;if(!f.stage){K.clap=null;stopVideo();}else if(f.stage.e!==was)play();paint();});
  on('kara_votes',f=>{if(!here(f)||K.stage?.e!==f.e)return;K.stage.votes=f.n;K.stage.need=f.need;paint();});
  on('kara_end',f=>{if(!here(f))return;if(K.stage?.e===f.e)K.stage.phase='clap';K.clap={...f};if(f.why!=='done'&&f.why!=='cut')stopVideo();paint();});
  on('kara_fx',f=>{if(!here(f))return;K.cheer=f.cheer||0;for(const [k,n] of Object.entries(f.r||{}))floatFx(k,Math.min(n,6));if(K.stage)K.stage.hearts=(K.stage.hearts||0)+Object.values(f.r||{}).reduce((a,b)=>a+b,0);paintMeter();});
  on('kara_tipped',f=>{if(!here(f))return;if(K.stage?.e===f.e)K.stage.tips=f.tips;floatFx('💰',2);said({pid:f.frm?.pid,name:f.frm?.name,text:`💰 +${f.xu} xu`,sys:1});});
  on('kara_said',f=>{if(f.ch!==K.room?.id)return;said(f);});
  on('kara_round',f=>{if(!here(f))return;K.round=f.round;K.reveal=null;paint();});
  on('kara_reveal',f=>{if(!here(f))return;K.round=null;K.reveal=f;paint();setTimeout(()=>{if(K.reveal===f){K.reveal=null;paint();}},9000);});
  on('kara_near',f=>{if(!here(f))return;K.near=Date.now();toast('Gần đúng rồi! 🤏');});
  on('kara_won',f=>{toast(`🎉 Bạn đoán đúng! +${f.xu} xu`);});
  on('deleted',f=>{if(f.ch&&f.ch===K.room?.id){K.said=K.said.filter(m=>m.id!==f.id);paintSaid();}});
  on('error',f=>{if(!String(f.ref||'').startsWith('kara_')||['kara_dur','kara_time','kara_react','kara_cheer','kara_can'].includes(f.ref))return;K.busy=false;K.err=f.msg||'Chưa được, thử lại nhé.';toast(K.err,true);render();});
  on('welcome',()=>{if(K.dlg?.open){if(K.room)live.send({t:'kara_in',id:K.room.id});else live.send({t:'kara_list'});clock();}});
}
const here=f=>K.room&&f.id===K.room.id;
function clock(){K.best=9;for(let i=0;i<5;i++)setTimeout(()=>{const c=++K.c%1e6;K.sent[c]=Date.now()/1000;live.send({t:'kara_time',c});},i*250);}

/* ---------------------------------------------------------------- the dialog */
function dialog(){
  if(K.dlg)return K.dlg;
  const d=document.createElement('dialog');d.className='sheet v4-sheet kr-sheet';d.setAttribute('aria-label','Phòng hát');
  d.innerHTML=`<div class="kr-root"><header class="kr-head"></header>
    <div class="kr-video" hidden><div class="kr-yt"></div></div>
    <div class="kr-body"></div>
    <form class="kr-bar" hidden><div class="kr-reacts"></div><div class="kr-line">
      <button type="button" class="icon-btn kr-more" data-kr="more" aria-label="Thêm">⋯</button>
      <input class="kr-input" maxlength="120" autocomplete="off" enterkeyhint="send">
      <button type="submit" class="btn primary kr-main"></button></div></form></div>`;
  d.addEventListener('click',e=>{const el=e.target.closest('[data-kr]');if(!el||el.disabled)return;e.preventDefault();act(el.dataset.kr,el.dataset,el);});
  d.addEventListener('close',()=>{if(K.room)live.send({t:'kara_out'});leaveLocal(true);clearInterval(K.timer);});
  const f=d.querySelector('.kr-bar');
  f.addEventListener('submit',e=>{e.preventDefault();main();});
  f.querySelector('.kr-input').addEventListener('input',paintBar);
  d.addEventListener('input',e=>{if(e.target.matches?.('[data-kr-clue]'))paintWords();});
  const cheer=()=>live.send({t:'kara_cheer'});
  f.querySelector('.kr-reacts').addEventListener('pointerdown',e=>{const b=e.target.closest('[data-cheer]');if(!b)return;cheer();clearInterval(K.hold);K.hold=setInterval(cheer,260);});
  for(const ev of ['pointerup','pointercancel','pointerleave'])f.addEventListener(ev,()=>clearInterval(K.hold));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&K.room)sync(true);});
  document.body.append(d);K.dlg=d;return d;
}

/** The menu entry, the town map's door, the outing's link: the room list (or straight into a room: data.room). */
export async function openKaraoke(env,data={}){
  K.env=env;bind();await stylesheet('/css/karaoke.css');
  const d=dialog();if(!d.open)d.showModal();
  K.err='';clock();
  if(data.room){live.send({t:'kara_in',id:data.room});}
  else if(!K.room){K.view='list';live.send({t:'kara_list'});}
  render();
  clearInterval(K.timer);K.timer=setInterval(()=>{if(!d.open)return clearInterval(K.timer);if(K.view==='list'&&++K.tick%10===0)live.send({t:'kara_list'});if(K.room){sync();paintClock();}},1000);
}

function enterRoom(f){
  const first=!K.room||K.room.id!==f.id;
  K.room=f;K.view='room';K.n=f.n;K.people=f.people||[];K.queue=f.queue||[];K.stage=f.stage;K.round=f.round;K.busy=false;K.panel=null;
  if(first){K.said=[];K.clap=null;K.reveal=null;}
  if(f.moved)toast('Phòng đông, bạn vào phòng bên cạnh 🎤');
  duck('kara',true);
  if(K.stage&&K.stage.phase!=='clap')play();else stopVideo();
  render();
}
function leaveLocal(closing=false){
  K.room=null;K.stage=null;K.queue=[];K.round=null;K.view='list';K.panel=null;duck('kara',false);
  try{K.player?.stopVideo?.();}catch{/* gone */}
  if(!closing&&K.dlg?.open){live.send({t:'kara_list'});render();}
}

/* ---------------------------------------------------------------- the YouTube player */
function loadYT(){
  if(window.YT?.Player)return Promise.resolve(window.YT);
  if(!K.yt)K.yt=new Promise((ok,bad)=>{
    const prev=window.onYouTubeIframeAPIReady;window.onYouTubeIframeAPIReady=()=>{try{prev?.();}catch{/* theirs */}ok(window.YT);};
    const s=document.createElement('script');s.src='https://www.youtube.com/iframe_api';s.async=true;s.onerror=()=>{K.yt=null;bad(new Error('yt'));};
    document.head.append(s);setTimeout(()=>{if(!window.YT?.Player){K.yt=null;bad(new Error('yt timeout'));}},20000);
  });
  return K.yt;
}
const pos=()=>K.stage?snow()-K.stage.at:0;
async function play(){
  const st=K.stage;if(!st||!K.dlg)return;
  const box=K.dlg.querySelector('.kr-video');box.hidden=false;
  let YT;try{YT=await loadYT();}catch{K.err='Chưa tải được trình phát YouTube.';paint();return;}
  if(K.stage!==st)return;
  K.e=st.e;K.durSent=null;K.forced=0;
  if(!K.player){
    K.ready=false;K.vid=st.vid;
    // Our own iframe, so it can send the page's origin as Referer: the site's Referrer-Policy is no-referrer, and
    // YouTube refuses an embed that does not say where it is (error 153). Nothing else of the page changes.
    const f=document.createElement('iframe'),q=new URLSearchParams({enablejsapi:'1',playsinline:'1',rel:'0',origin:location.origin,start:String(Math.max(0,Math.floor(pos())))});
    f.src=`${YT_HOST}/embed/${encodeURIComponent(st.vid)}?${q}`;f.className='kr-yt';f.title='YouTube';
    f.referrerPolicy='strict-origin-when-cross-origin';f.allow='autoplay; encrypted-media; picture-in-picture';f.allowFullscreen=true;
    box.querySelector('.kr-yt').replaceWith(f);
    K.player=new YT.Player(f,{
      events:{onReady:()=>{K.ready=true;start();},onStateChange:onState,onError:e=>{K.err=[101,150].includes(e.data)?'Video không cho phát ngoài YouTube.':'Video lỗi, chờ bài sau nhé.';paint();}}});
    return;
  }
  if(!K.ready)return;   // onReady starts it
  start();
}
function start(){
  const st=K.stage,p=K.player;if(!st||!p||!K.ready)return;
  const at=pos();
  if(K.vid!==st.vid){K.vid=st.vid;at<0?p.cueVideoById({videoId:st.vid}):p.loadVideoById({videoId:st.vid,startSeconds:at});}
  clearTimeout(K.startAt);
  if(at<0){K.startAt=setTimeout(()=>{if(K.stage===st){try{p.seekTo(Math.max(0,pos()),true);p.playVideo();}catch{/* player gone */}want();}},-at*1000);}
  else{try{p.seekTo(at,true);p.playVideo();}catch{/* player gone */}want();}
}
/** Phones block sound without a tap: if it is not playing 2 s later, one button under the video says so. */
function want(){setTimeout(()=>{const s=K.player?.getPlayerState?.();K.want=K.stage&&K.stage.phase!=='clap'&&s!==1&&s!==3&&pos()>0;paintBar();},2000);}
function onState(e){
  if(e.data===1){K.want=false;paintBar();const d=K.player.getDuration?.();if(d>0&&K.durSent!==K.e&&K.stage){K.durSent=K.e;live.send({t:'kara_dur',e:K.stage.e,dur:Math.round(d*10)/10});}sync((K.forced=(K.forced||0)+1)<=3);}   // a tight fit when it starts playing, at most 3 times a song (each seek buffers again)
}
function stopVideo(){clearTimeout(K.startAt);try{K.player?.stopVideo?.();}catch{/* gone */}K.vid=null;const box=K.dlg?.querySelector('.kr-video');if(box&&!K.stage)box.hidden=true;}
/** Drift control: only while YouTube says it is playing (never during an ad or a buffer). */
function sync(force=false){
  const p=K.player,st=K.stage;if(!p||!K.ready||!st||st.phase==='clap'||K.clap)return;
  const target=pos();if(target<0)return;
  let s,cur;try{s=p.getPlayerState();cur=p.getCurrentTime();}catch{return;}
  if(s!==1)return;
  if(Math.abs(cur-target)>DRIFT||(force&&Math.abs(cur-target)>.15))try{p.seekTo(target,true);}catch{/* gone */}
}

/* ---------------------------------------------------------------- what the room sees */
function said(m){
  K.said.push({...m,t:Date.now()});if(K.said.length>30)K.said.splice(0,K.said.length-30);paintSaid();
}
function floatFx(k,n){
  const box=K.dlg?.querySelector('.kr-fx');if(!box)return;
  for(let i=0;i<n;i++){const s=document.createElement('span');s.textContent=k;s.style.left=`${10+Math.random()*80}%`;s.style.animationDelay=`${i*90}ms`;box.append(s);setTimeout(()=>s.remove(),2200);}
}
function render(){
  const d=K.dlg;if(!d)return;
  const head=d.querySelector('.kr-head'),body=d.querySelector('.kr-body'),bar=d.querySelector('.kr-bar');
  if(K.view!=='room'||!K.room){
    d.querySelector('.kr-video').hidden=true;bar.hidden=true;
    head.innerHTML=`<b class="kr-title">🎤 Phòng hát Mây</b><span class="grow"></span><button type="button" class="icon-btn" data-kr="close" aria-label="Đóng">${icon('x',20)}</button>`;
    if(live.state!=='open'&&!K.rooms){body.innerHTML=`<p class="kr-empty">Đang kết nối…</p>`;return;}
    if(!K.rooms){body.innerHTML='<div class="mnl-skel" role="status" aria-busy="true"><i></i><i></i><i></i></div>';return;}
    const seen=new Set();
    body.innerHTML=`<ul class="kr-rooms">${K.rooms.filter(r=>{if(r.n===0&&seen.has(r.theme))return false;seen.add(r.theme);return true;}).map(r=>`<li><button type="button" class="kr-room" data-kr="in" data-id="${esc(r.id)}"${r.closed?' disabled':''}>
      <span class="kr-emo" aria-hidden="true">${esc(r.emoji)}</span><span class="grow"><b>${esc(r.name)}</b>${r.song?`<small>▶ ${esc(r.song.title)}</small>`:''}</span>
      <span class="kr-n">👥 ${r.n}</span></button></li>`).join('')}</ul><p class="kr-host">🎤 Chị Ngân giữ mic</p>`;
    return;
  }
  const r=K.room;
  head.innerHTML=`<button type="button" class="icon-btn" data-kr="back" aria-label="Danh sách phòng">${icon('arrow',18)}</button>
    <b class="kr-title">${esc(r.emoji)} ${esc(r.name)}</b><button type="button" class="kr-n" data-kr="people">👥 <span data-kr-n>${K.n}</span></button>
    <span class="grow"></span><button type="button" class="icon-btn" data-kr="close" aria-label="Đóng">${icon('x',20)}</button>`;
  body.innerHTML=`<div class="kr-fx" aria-hidden="true"></div><div class="kr-dyn"></div><ul class="kr-said" aria-live="polite"></ul>`;
  bar.hidden=false;
  bar.querySelector('.kr-reacts').innerHTML=REACT.map(k=>`<button type="button" class="kr-r" data-kr="react" data-k="${k}">${k}</button>`).join('')+
    `<button type="button" class="kr-r kr-cheer" data-cheer aria-label="Giữ để cổ vũ">🙌</button><span class="kr-meter" aria-hidden="true"><i></i></span>`;
  paint();
}
function paint(){
  const dyn=K.dlg?.querySelector('.kr-dyn');if(!dyn||K.view!=='room')return;
  if(K.panel==='add'){const l=dyn.querySelector('[data-kr-link]');if(l)K.link=l.value;}else if(K.panel==='round')readRound();   // keep what is typed
  const n=K.dlg.querySelector('[data-kr-n]');if(n)n.textContent=K.n;
  K.dlg.querySelector('.kr-video').hidden=!K.stage;
  dyn.innerHTML=K.panel?panelHTML():stageHTML()+roundHTML()+queueHTML();
  paintBar();paintSaid();paintMeter();
  if(K.focus){K.focus=false;dyn.querySelector('[data-kr-focus]')?.focus({preventScroll:true});}
}
function stageHTML(){
  const st=K.stage,me=K.room.me;
  if(K.err&&!st)return `<p class="kr-note bad">${esc(K.err)}</p>`;
  if(!st)return `<p class="kr-empty">🎤 Sân khấu trống</p>`;
  const mine=st.by?.pid===me;
  if(K.clap)return `<div class="kr-clap" role="status"><b>🎉 ${esc(K.clap.by?.name||'')}</b><span>❤️ ${K.clap.hearts} · 🙌 ${K.clap.cheers}${K.clap.tips?` · 💰 ${K.clap.tips}`:''}</span></div>`;
  const left=st.at-snow();
  return `<div class="kr-on"><span class="kr-av" aria-hidden="true">🎤</span><span class="grow"><b data-no-translate>${esc(st.by?.name||'')}</b>
    <small data-kr-clock>${left>0?`Bắt đầu sau ${Math.ceil(left)}s`:esc(st.title)}</small></span>
    ${mine?`<button type="button" class="kr-pill" data-kr="skip">⏹</button>`:K.room.account&&!st.reward?`<button type="button" class="kr-pill" data-kr="tip" aria-label="Tặng xu">💰</button>`:''}</div>`;
}
function roundHTML(){
  if(K.reveal){const v=K.reveal;return `<div class="kr-round done" role="status"><b>🧩 ${esc(v.answer)}</b><small>${v.by?`🎉 ${esc(v.by.name)}${v.xu?` +${v.xu} xu`:''}`:'Hết giờ'}</small></div>`;}
  const rd=K.round;if(!rd)return '';
  return `<div class="kr-round"><small>🧩 ${esc(rd.host?.name||'')} · <span data-kr-left>${fmt(rd.until-snow())}</span> · ${rd.words} chữ</small><b class="kr-clue${rd.mode==='emoji'?' emoji':''}">${esc(rd.clue)}</b></div>`;
}
function queueHTML(){
  if(!K.queue.length)return '';
  return `<ol class="kr-q">${K.queue.slice(0,5).map(q=>`<li><b data-no-translate>${esc(q.by?.name||'')}</b> <span>${q.reward?'🎁 ':''}${esc(q.title)}</span></li>`).join('')}</ol>`;
}
function paintBar(){
  const bar=K.dlg?.querySelector('.kr-bar');if(!bar||bar.hidden)return;
  const inp=bar.querySelector('.kr-input'),btn=bar.querySelector('.kr-main'),typed=inp.value.trim().length>0;
  inp.placeholder=K.round&&K.round.host?.pid!==K.room?.me?'Đoán tên bài…':'Nhắn…';
  inp.disabled=!K.room?.account;
  if(K.want){btn.textContent='▶ Nghe';btn.dataset.mode='play';}
  else if(typed){btn.textContent='Gửi';btn.dataset.mode='send';}
  else{btn.textContent='🎤 Thêm bài';btn.dataset.mode='add';}
  btn.disabled=K.busy||(!K.room?.account&&btn.dataset.mode!=='play');
}
function paintSaid(){
  const ul=K.dlg?.querySelector('.kr-said');if(!ul)return;
  ul.innerHTML=K.said.slice(-6).map(m=>`<li${m.sys?' class="sys"':''}><b data-no-translate>${esc(m.name||'')}</b> ${esc(m.text)}</li>`).join('');
}
function paintMeter(){const i=K.dlg?.querySelector('.kr-meter i');if(i)i.style.width=`${Math.max(0,Math.min(100,K.cheer))}%`;}
function paintClock(){
  const c=K.dlg?.querySelector('[data-kr-clock]');if(c&&K.stage){const left=K.stage.at-snow();c.textContent=left>0?`Bắt đầu sau ${Math.ceil(left)}s`:K.stage.title;}
  const l=K.dlg?.querySelector('[data-kr-left]');if(l&&K.round)l.textContent=fmt(K.round.until-snow());
}

/* ---------------------------------------------------------------- panels: add a song, a round, a tip, more */
function panelHTML(){
  const p=K.panel,close=`<button type="button" class="icon-btn kr-x" data-kr="panel" data-p="" aria-label="Đóng">${icon('x',16)}</button>`;
  if(p==='add'){
    const s=K.song;
    return `<div class="kr-panel">${close}<label class="kr-field"><input data-kr-link data-kr-focus inputmode="url" placeholder="Dán link YouTube" value="${esc(K.link||'')}"></label>
      ${s?`<div class="kr-song${s.ok?'':' bad'}"><img src="https://i.ytimg.com/vi/${esc(s.vid)}/mqdefault.jpg" alt="" width="96" height="54" loading="lazy"><span><b>${esc(s.title||s.vid)}</b><small>${s.ok?`✓ Phát được`:esc(s.text||'Không phát được')}</small></span></div>`:''}
      ${K.err?`<p class="kr-note bad">${esc(K.err)}</p>`:''}
      <button type="button" class="btn primary wide" data-kr="${s?.ok?'queue':'check'}"${K.busy?' disabled':''}>${s?.ok?`Xếp hàng · ${K.room.price} xu`:'Kiểm tra'}</button></div>`;
  }
  if(p==='round'){
    const words=(K.clue||'').split(/\s+/).filter(Boolean);
    return `<div class="kr-panel">${close}<div class="kr-seg" role="group"><button type="button" data-kr="mode" data-m="lyric" aria-pressed="${K.mode==='lyric'}">📝 Lời</button><button type="button" data-kr="mode" data-m="emoji" aria-pressed="${K.mode==='emoji'}">😀 Emoji</button></div>
      <input class="kr-field" data-kr-clue data-kr-focus maxlength="90" placeholder="${K.mode==='lyric'?'Một câu hát ngắn':'🌧️💔🏠'}" value="${esc(K.clue||'')}">
      <div class="kr-words" data-kr-words>${wordsHTML(words)}</div>
      <input class="kr-field" data-kr-ans maxlength="60" placeholder="Đáp án" value="${esc(K.ans||'')}">
      <input class="kr-field" data-kr-reward inputmode="url" placeholder="Link thưởng (tùy)" value="${esc(K.reward||'')}">
      ${K.err?`<p class="kr-note bad">${esc(K.err)}</p>`:''}<button type="button" class="btn primary wide" data-kr="start"${K.busy?' disabled':''}>Bắt đầu</button></div>`;
  }
  if(p==='tip'){
    const st=K.stage;
    return `<div class="kr-panel">${close}<b>💰 ${esc(st?.by?.name||'')}</b><div class="kr-chips">${(K.room.tips||[]).map(x=>`<button type="button" class="kr-pill" data-kr="tipgo" data-xu="${x}"${K.busy?' disabled':''}>${x} xu</button>`).join('')}</div>${K.err?`<p class="kr-note bad">${esc(K.err)}</p>`:''}</div>`;
  }
  if(p==='people'){
    const me=K.room.me;
    return `<div class="kr-panel">${close}<ul class="kr-people">${K.people.map(x=>`<li><span>${esc(x.name)}</span>${x.pid!==me?`<button type="button" class="kr-pill" data-kr="report" data-pid="${esc(x.pid)}" aria-label="Báo cáo">🚩</button>${K.room.adm?`<button type="button" class="kr-pill" data-kr="kick" data-pid="${esc(x.pid)}" aria-label="Mời ra">🚪</button>`:''}`:''}</li>`).join('')}</ul></div>`;
  }
  const st=K.stage,mine=st?.by?.pid===K.room.me,adm=K.room.adm;
  const items=[['round','🧩 Đố bài'],...(st&&!mine?[['vote',`👎 Bỏ bài ${st.votes||0}/${st.need||1}`],['report-song','🚩 Báo cáo bài']]:[]),...(K.round&&(K.round.host?.pid===K.room.me||adm)?[['endround','⏹ Kết thúc đố']]:[]),
    ...(adm?[['adm-skip','⏭ Bỏ bài (QL)'],['adm-ban','🚫 Cấm bài'],['adm-close','🔒 Đóng phòng']]:[]),['out','🚪 Ra']];
  return `<div class="kr-panel">${close}<div class="kr-menu">${items.map(([a,l])=>`<button type="button" data-kr="${a}">${esc(l)}</button>`).join('')}</div></div>`;
}

async function main(){
  const bar=K.dlg.querySelector('.kr-bar'),btn=bar.querySelector('.kr-main'),inp=bar.querySelector('.kr-input');
  if(btn.dataset.mode==='play'){K.want=false;try{K.player?.playVideo();}catch{/* gone */}sync(true);paintBar();return;}
  if(btn.dataset.mode==='send'){const text=inp.value.trim();if(!text)return;live.send({t:'kara_say',text});inp.value='';paintBar();return;}
  K.panel='add';K.song=null;K.err='';K.focus=true;paint();
}

async function act(a,d){
  const api=K.env?.api;
  switch(a){
    case'close':K.dlg.close();return;
    case'back':live.send({t:'kara_out'});leaveLocal();return;
    case'in':K.err='';live.send({t:'kara_in',id:d.id});return;
    case'people':K.panel=K.panel==='people'?null:'people';paint();return;
    case'more':K.panel=K.panel==='more'?null:'more';K.err='';paint();return;
    case'panel':K.panel=d.p||null;K.err='';paint();return;
    case'react':live.send({t:'kara_react',k:d.k});floatFx(d.k,1);return;
    case'skip':if(K.stage)live.send({t:'kara_skip',e:K.stage.e});return;
    case'vote':if(K.stage)live.send({t:'kara_vote',e:K.stage.e});K.panel=null;paint();return;
    case'out':live.send({t:'kara_out'});leaveLocal();return;
    case'tip':K.panel='tip';K.err='';paint();return;
    case'round':K.panel='round';K.err='';K.clue='';K.ans='';K.reward='';K.blanks=new Set();K.focus=true;paint();return;
    case'endround':live.send({t:'kara_round_end'});K.panel=null;paint();return;
    case'report':live.send({t:'kara_report',pid:d.pid,reason:'rude'});toast('Đã báo cáo. Cảm ơn bạn!');K.panel=null;paint();return;
    case'report-song':if(K.stage)live.send({t:'kara_report',vid:K.stage.vid,reason:'other'});toast('Đã báo cáo. Cảm ơn bạn!');K.panel=null;paint();return;
    case'kick':live.send({t:'kara_kick',pid:d.pid});K.panel=null;paint();return;
    case'adm-skip':if(K.stage)live.send({t:'kara_skip',e:K.stage.e});K.panel=null;paint();return;
    case'adm-ban':if(K.stage)live.send({t:'kara_ban',vid:K.stage.vid});K.panel=null;paint();return;
    case'adm-close':live.send({t:'kara_close'});return;
    case'mode':K.mode=d.m;K.blanks=new Set();readRound();paint();return;
    case'blank':{readRound();const i=Number(d.i);K.blanks.has(i)?K.blanks.delete(i):K.blanks.add(i);paintWords();return;}
    case'check':{
      K.link=K.dlg.querySelector('[data-kr-link]')?.value.trim()||'';if(!K.link)return;
      K.busy=true;K.err='';paint();
      try{K.song=await api.post('/api/karaoke/song',{url:K.link});}catch(e){K.err=e.message||'Chưa kiểm tra được.';K.song=null;}
      K.busy=false;paint();return;
    }
    case'queue':{
      if(!K.song?.ok)return;K.busy=true;K.err='';paint();
      const can=await ask('kara_can',{}, 'kara_can');
      if(!can?.ok){K.busy=false;K.err=can?.msg||'Chưa xếp được, thử lại nhé.';paint();return;}
      try{
        K.ticket=K.ticket||rid();
        const r=await api.post('/api/karaoke/queue',{rid:K.ticket});
        if(r.state&&typeof r.revision==='number')api.accept({state:r.state,revision:r.revision});
        live.send({t:'kara_add',vid:K.song.vid,e:r.e});K.ticket=null;
        toast(r.price?`Đã xếp hàng · −${r.price} xu`:'Đã xếp hàng 🎁');K.panel=null;K.song=null;K.link='';
      }catch(e){K.err=e.message||'Chưa xếp được.';if(e.status&&e.status<500)K.ticket=null;}
      K.busy=false;paint();return;
    }
    case'start':{
      readRound();
      let clue=K.clue.trim();
      if(K.mode==='lyric')clue=clue.split(/\s+/).map((w,i)=>K.blanks.has(i)?'___':w).join(' ');
      const f={t:'kara_round',mode:K.mode,clue,answer:K.ans.trim()};if(K.reward.trim())f.vid=K.reward.trim();
      if(f.vid){try{const s=await api.post('/api/karaoke/song',{url:f.vid});if(!s.ok){K.err=s.text||'Link thưởng không phát được.';paint();return;}f.vid=s.vid;}catch(e){K.err=e.message;paint();return;}}
      live.send(f);K.panel=null;paint();return;
    }
    case'tipgo':{
      const st=K.stage;if(!st)return;K.busy=true;K.err='';paint();
      try{
        const r=await api.post('/api/karaoke/tip',{e:st.e,xu:Number(d.xu),rid:rid()});
        if(r.state&&typeof r.revision==='number')api.accept({state:r.state,revision:r.revision});
        toast(`💰 Đã tặng ${r.xu} xu`);K.panel=null;
      }catch(e){K.err=e.message||'Chưa tặng được.';}
      K.busy=false;paint();return;
    }
  }
}
function wordsHTML(words){
  return K.mode==='lyric'?words.slice(0,12).map((w,i)=>`<button type="button" data-kr="blank" data-i="${i}" aria-pressed="${K.blanks.has(i)}">${K.blanks.has(i)?'___':esc(w)}</button>`).join(''):'';
}
function paintWords(){const box=K.dlg?.querySelector('[data-kr-words]');if(box){readRound();box.innerHTML=wordsHTML((K.clue||'').split(/\s+/).filter(Boolean));}}
function readRound(){
  const q=s=>K.dlg.querySelector(s);
  if(q('[data-kr-clue]')){const c=q('[data-kr-clue]').value;if(c!==K.clue)K.blanks=new Set();K.clue=c;}
  if(q('[data-kr-ans]'))K.ans=q('[data-kr-ans]').value;if(q('[data-kr-reward]'))K.reward=q('[data-kr-reward]').value;
}
/** One request/answer over the socket (an error frame for it ends it too). */
function ask(t,frame,reply,ms=4000){
  return new Promise(ok=>{
    let done=false;const fin=v=>{if(done)return;done=true;off1();off2();ok(v);};
    const off1=live.on(reply,fin),off2=live.on('error',f=>{if(f.ref===t)fin({ok:false,msg:f.msg});});
    if(!live.send({t,...frame}))fin({ok:false,msg:'Đang kết nối lại…'});
    setTimeout(()=>fin(null),ms);
  });
}

/** For tests and the browser check: what this page holds now. */
export const karaoke={state:()=>({view:K.view,room:K.room?.id||null,stage:K.stage?{e:K.stage.e,vid:K.stage.vid,at:K.stage.at,phase:K.stage.phase}:null,
  queue:K.queue.length,round:K.round,reveal:K.reveal,off:K.off,best:K.best,pos:K.stage?pos():null,
  cur:(()=>{try{return K.player?.getCurrentTime?.()??null;}catch{return null;}})(),ps:(()=>{try{return K.player?.getPlayerState?.()??null;}catch{return null;}})(),said:K.said.length})};
