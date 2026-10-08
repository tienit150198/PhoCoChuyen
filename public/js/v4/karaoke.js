/** 🎤 Phòng hát Mây (live/karaoke.py, game/karaoke.py; only while the live service's welcome says `kara`).
 * Three public rooms (Nhạc trẻ, Bolero, Quốc tế), everyone watching the same YouTube video at the same second: the
 * official IFrame player (youtube-nocookie.com, ads and logo as YouTube shows them, never covered or hidden for a
 * game), a queue, the singer on stage, reactions, a cheer meter, bubbles, xu tips, a 10 s applause moment, and 🧩 Đoán
 * bài (a lyric line with blanks or emoji clues; guesses are typed in the same box). No voice in v1.
 *
 * The clock: `kara_time` five times on entering (then one every 15 s), the reply with the smallest round trip gives the
 * server offset; a song plays from (server now − at). Every second a playing video more than DRIFT seconds off is nudged back (sync()); nothing is
 * corrected while YouTube is not playing (an ad, buffering). Phone first, few words: one bottom bar, one main button
 * (🎤 Thêm bài, or Gửi once something is typed); the rest sits behind ⋯.
 *
 * 🎙️ Mic trực tiếp (welcome flag `kara_mic`, LIVE_KARAOKE_MIC): the singer on stage may turn a live mic on (🎙️ on the
 * stage line; the first time a short note with the headphones advice, then the birth year if the account has none,
 * then the browser's permission prompt); everyone in the room then sees "🎤 Đang phát trực tiếp giọng hát" and hears
 * the voice over their own YouTube player (a 🎤 volume of its own, 🔇, and "Chạm để nghe" when a phone wants a tap).
 * The SDK and the SFU are in v4/karaoke-mic.js, loaded only then. While a listener hears the voice, their video keeps a
 * little behind the singer's own (kara_vt, about once a second) minus the voice's delay, and the voice is held in a
 * Web Audio delay to play exactly with it (mixNow(); 07/10 "bị delay xíu": the singer sings to their video, the voice
 * comes later); without one it is the clock, as without a mic. 🎤 Hát cùng: others in the room ask to sing along, the
 * stage singer says yes or no; every voice is held to the listener's music the same way (coJoin … coListen).
 * Each side shows where it is: a listener "🎧 Đang nối giọng…", then the voice (or "Chạm để nghe giọng"), or "Chưa
 * nghe được giọng · Thử lại"; the singer "Đang nối mic…", then the timer, or "Chưa phát được giọng · Thử lại". A
 * failed step (and a wait given up on) goes to the page's error beacon (micReport) with the stage it stopped at:
 * mod → sdk → token → signal → ice → track → audio (the singer: … token → perm → signal …). */
import {icon,escapeHTML as esc} from '../icons.js';
import {live} from './live.js';
import {stylesheet} from '../lazy.js';
import {duck} from '../audio.js';
import {error as beacon} from '../telemetry.js';

const DRIFT=.35,REACT=['👏','❤️','🔥','🌹'],YT_HOST='https://www.youtube-nocookie.com';
const K={dlg:null,env:null,bound:false,view:'list',rooms:null,room:null,stage:null,queue:[],round:null,n:0,people:[],said:[],fx:{},cheer:0,
  off:0,best:9,c:0,sent:{},yt:null,player:null,ready:false,vid:null,e:null,durSent:null,timer:0,tick:0,panel:null,song:null,busy:false,
  err:'',ticket:null,clap:null,startAt:0,blanks:new Set(),mode:'lyric',want:false,near:0,won:null,reveal:null,
  live:null,M:null,ct:0,vt:null,vtOff:false,vSeeks:0,far:0,rateOk:null,rateAt:0,
  co:new Map(),cvt:new Map(),coList:[],asks:[],coOff:false,birthNext:'',
  mic:{pub:null,pubE:null,sub:null,subE:null,busy:false,joining:false,tap:false,muted:false,tries:0,vol:vol(),
    ls:'',at:'',gen:0,t0:0,hc:0,pubAt:'',pubFail:null,lag:{},sy:null,syE:null,up:null,vtAt:0,pt:0,polling:false,
    cpub:null,cpubE:null,co:{st:''},side:0}};
function vol(){try{const v=Number(localStorage.getItem('kr-voice-vol'));return v>=0&&v<=1&&localStorage.getItem('kr-voice-vol')!==null?v:.9;}catch{return .9;}}
const micFlag=()=>!!live.flags?.kara_mic;
const mic=()=>import('./karaoke-mic.js').then(m=>(K.M=m));
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
  on('kara_play',f=>{if(!here(f))return;liveOff();K.stage={...f,phase:'deck',votes:0,need:1,hearts:0,cheers:0,tips:0};K.clap=null;K.cheer=0;play();paint();});
  on('kara_stage',f=>{if(!here(f))return;const was=K.stage?.e;K.stage=f.stage;if(!f.stage||f.stage.e!==was)liveOff();if(!f.stage){K.clap=null;stopVideo();}else if(f.stage.e!==was)play();paint();});
  on('kara_votes',f=>{if(!here(f)||K.stage?.e!==f.e)return;K.stage.votes=f.n;K.stage.need=f.need;paint();});
  on('kara_end',f=>{if(!here(f))return;liveOff();if(K.stage?.e===f.e)K.stage.phase='clap';K.clap={...f};if(f.why!=='done'&&f.why!=='cut')stopVideo();paint();});
  on('kara_live',f=>{if(!here(f))return;onLive(f);});
  on('kara_listen',f=>{if(!here(f)||f.on)return;   // the server took my listening away (a block); 🎤 `pid`: a co-singer's voice
    if(f.pid&&f.pid!==K.live?.by?.pid){if(K.co.has(f.pid)){coDrop(f.pid);paint();}}else if(K.mic.sub){stopListen();paint();}});
  on('kara_vt',f=>{if(!here(f)||!K.stage||f.e!==K.stage.e||!Number.isFinite(f.vt)||!Number.isFinite(f.at))return;   // 🎙️ the singer's own video time
    K.vt=vtOf(f);if(K.mic.sy)K.mic.sy.up=K.vt.up;});
  on('kara_cvt',f=>{if(!here(f)||!K.stage||f.e!==K.stage.e||typeof f.pid!=='string'||!Number.isFinite(f.vt)||!Number.isFinite(f.at))return;   // 🎤 a co-singer's
    if(K.co.has(f.pid))K.cvt.set(f.pid,vtOf(f));});
  on('kara_ask',f=>{if(!here(f)||!K.live||f.e!==K.live.e)return;   // 🎤 the singer: someone asks to sing along
    K.asks=K.asks.filter(a=>a.pid!==f.pid);if(f.on){K.asks.push({pid:f.pid,name:f.name,until:f.until});toast(`🙋 ${f.name||''} muốn hát cùng`);}paint();});
  on('kara_sing',f=>{if(!here(f))return;if(f.on)coPublish(f);else coRefused(f);});
  on('kara_co',f=>{if(!here(f)||!K.stage||f.e!==K.stage.e)return;onCo(f);paint();});
  on('kara_fx',f=>{if(!here(f))return;K.cheer=f.cheer||0;for(const [k,n] of Object.entries(f.r||{}))floatFx(k,Math.min(n,6));if(K.stage)K.stage.hearts=(K.stage.hearts||0)+Object.values(f.r||{}).reduce((a,b)=>a+b,0);paintMeter();});
  on('kara_tipped',f=>{if(!here(f))return;if(K.stage?.e===f.e)K.stage.tips=f.tips;floatFx('💰',2);said({pid:f.frm?.pid,name:f.frm?.name,text:`💰 +${f.xu} xu`,sys:1});});
  on('kara_said',f=>{if(f.ch!==K.room?.id)return;said(f);});
  on('kara_round',f=>{if(!here(f))return;K.round=f.round;K.reveal=null;paint();});
  on('kara_reveal',f=>{if(!here(f))return;K.round=null;K.reveal=f;paint();setTimeout(()=>{if(K.reveal===f){K.reveal=null;paint();}},9000);});
  on('kara_near',f=>{if(!here(f))return;K.near=Date.now();toast('Gần đúng rồi! 🤏');});
  on('kara_won',f=>{toast(`🎉 Bạn đoán đúng! +${f.xu} xu`);});
  on('deleted',f=>{if(f.ch&&f.ch===K.room?.id){K.said=K.said.filter(m=>m.id!==f.id);paintSaid();}});
  on('error',f=>{if(f.ref==='kara_vt'&&(f.code==='unknown'||f.code==='off'))K.vtOff=true;   // an older live service: stop sending it
    if(f.ref==='kara_join'&&f.code==='unknown'){K.coOff=true;paint();}   // 🎤 an older live service: no "Hát cùng"
    if(f.ref==='kara_let')toast(f.msg||'Chưa được, thử lại nhé.',true);
    if(!String(f.ref||'').startsWith('kara_')||['kara_dur','kara_time','kara_react','kara_cheer','kara_can','kara_mic','kara_listen','kara_vt','kara_join','kara_let'].includes(f.ref))return;K.busy=false;K.err=f.msg||'Chưa được, thử lại nhé.';toast(K.err,true);render();});
  on('welcome',()=>{K.vtOff=false;K.coOff=false;if(K.dlg?.open){if(K.room)live.send({t:'kara_in',id:K.room.id});else live.send({t:'kara_list'});clock();}});
}
/** A singer's video time (kara_vt / kara_cvt) as the page keeps it: `up` their path's round trip, `ol` their own
 * output + capture latency, both in seconds. */
const vtOf=f=>({e:f.e,pid:f.pid,vt:f.vt,at:f.at,r:Number.isFinite(f.r)?f.r:1,up:Number.isFinite(f.rtt)?f.rtt/1000:null,
  ol:Number.isFinite(f.ol)&&f.ol>0?f.ol/1000:0,got:Date.now()});
const here=f=>K.room&&f.id===K.room.id;
function clock(){K.best=9;for(let i=0;i<5;i++)setTimeout(timeAsk,i*250);}
/** One more clock reading (kept only if its round trip beats the best so far): every CLOCK_EVERY s in a room, as the
 * five on entering may come while the page is busy loading, and a late reply skews the offset (a listener following a
 * live voice compares two pages' clocks: kara_vt). */
function timeAsk(){const c=++K.c%1e6;K.sent[c]=Date.now()/1000;if(!live.send({t:'kara_time',c}))delete K.sent[c];}
const CLOCK_EVERY=15;

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
  d.addEventListener('click',e=>{
    K.M?.resumeAudio?.();   // the voices' shared context, inside a tap (iPhone)
    if(tapWanted()&&!e.target.closest('[data-kr=voicetap]'))voiceTap();   // iPhone: any tap in the sheet may start the voice
    const el=e.target.closest('[data-kr]');if(!el||el.disabled)return;e.preventDefault();act(el.dataset.kr,el.dataset,el);});
  d.addEventListener('close',()=>{if(K.room)live.send({t:'kara_out'});leaveLocal(true);clearInterval(K.timer);});
  const f=d.querySelector('.kr-bar');
  f.addEventListener('submit',e=>{e.preventDefault();main();});
  f.querySelector('.kr-input').addEventListener('input',paintBar);
  d.addEventListener('input',e=>{if(e.target.matches?.('[data-kr-clue]'))paintWords();else if(e.target.matches?.('[data-kr-vol]'))setVol(e.target.value/100);});
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
  clearInterval(K.timer);K.timer=setInterval(()=>{if(!d.open)return clearInterval(K.timer);if(K.view==='list'&&++K.tick%10===0)live.send({t:'kara_list'});if(K.room){sync();paintClock();micPoll();if(++K.ct%CLOCK_EVERY===0)timeAsk();}},1000);
}

function enterRoom(f){
  const first=!K.room||K.room.id!==f.id;
  K.room=f;K.view='room';K.n=f.n;K.people=f.people||[];K.queue=f.queue||[];K.stage=f.stage;K.round=f.round;K.busy=false;K.panel=null;
  if(first){K.said=[];K.clap=null;K.reveal=null;}
  if(f.moved)toast('Phòng đông, bạn vào phòng bên cạnh 🎤');
  duck('kara',true);
  if(K.stage&&K.stage.phase!=='clap')play();else stopVideo();
  const m=K.stage?.mic;liveOff();
  if(m?.on&&K.stage.phase!=='clap'){
    onLive({on:1,e:K.stage.e,by:K.stage.by,until:m.until});
    for(const c of m.co||[])onCo({on:1,e:K.stage.e,pid:c.pid,name:c.name});   // 🎤 the co-singers singing now
    K.asks=(f.asks||[]).filter(a=>a&&a.pid);
  }
  render();
}
function leaveLocal(closing=false){
  liveOff();
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
  K.vSeeks=0;K.far=0;
  clearTimeout(K.startAt);if(K.rate&&K.rate!==1)try{p.setPlaybackRate?.(1);}catch{/* gone */}K.rate=1;   // a new song starts at 1×
  if(at<0){K.startAt=setTimeout(()=>{if(K.stage===st){try{p.seekTo(Math.max(0,pos()),true);p.playVideo();}catch{/* player gone */}want();}},-at*1000);}
  else{try{p.seekTo(at,true);p.playVideo();}catch{/* player gone */}want();}
}
/** Phones block sound without a tap: if it is not playing 2 s later, one button under the video says so. */
function want(){setTimeout(()=>{const s=K.player?.getPlayerState?.();K.want=K.stage&&K.stage.phase!=='clap'&&s!==1&&s!==3&&pos()>0;paintBar();},2000);}
function onState(e){
  if(e.data===1){K.want=false;paintBar();const d=K.player.getDuration?.();if(d>0&&K.durSent!==K.e&&K.stage){K.durSent=K.e;live.send({t:'kara_dur',e:K.stage.e,dur:Math.round(d*10)/10});}
    if(K.seekT){const t=(performance.now()-K.seekT)/1000;K.seekT=0;if(t<8)K.lag=Math.min(SEEK_LEAD,t);}   // how long my last seek took to play again
    sync();}
}
function stopVideo(){clearTimeout(K.startAt);try{K.player?.stopVideo?.();}catch{/* gone */}K.vid=null;const box=K.dlg?.querySelector('.kr-video');if(box&&!K.stage)box.hidden=true;}
/** Drift control (B2, "nhạc cứ giật giật"): every seek buffers again, and on a weak phone that buffer is new drift, so
 * a tight seek loop stutters. Under SEEK_AT seconds off nothing is sought: past DRIFT the playback rate is nudged
 * (0.95 / 1.05) until within NUDGE_OK. 08/10: YouTube lists only 0.25 steps, so asking only for a listed rate never
 * nudged at all; now the rate is asked for and kept where the player plays it (rateSeen). Past SEEK_AT one seek, at
 * most every SEEK_GAP ms, aimed ahead by what the last seek took to play again (≤ SEEK_LEAD s). Only while YouTube
 * says it is playing: never during an ad, a buffer or a pause. */
const SEEK_AT=2,SEEK_GAP=10000,SEEK_LEAD=1.5,NUDGE_OK=.12;   // a lead < SEEK_AT: a wrong guess is nudged, never sought again
/** 🎙️ While I hear live voices (mixNow), each voice is held in a delay of its own so it plays with my music; my music
 * only keeps a little behind them (voiceMove): a nudge past DRIFT_V (two readings in a row) until within NUDGE_OK_V,
 * a seek only when a voice would come later than my music (VOICE_SEEKS a song, VSEEK_GAP apart). A singer sends its
 * video time (kara_vt) every VT_EVERY ms while its mic is live and its video plays. */
const DRIFT_V=.12,NUDGE_OK_V=.05,VOICE_SEEKS=3,VSEEK_GAP=6000,VT_EVERY=900;
function sync(){
  const p=K.player,st=K.stage;if(!p||!K.ready||!st||st.phase==='clap'||K.clap)return;
  const clock=pos();if(clock<0)return;
  let s,cur;try{s=p.getPlayerState();cur=p.getCurrentTime();}catch{return;}
  if(s!==1)return;
  rateSeen(p);
  if((K.mic.pub&&K.mic.pubE===st.e)||(K.mic.cpub&&K.mic.cpubE===st.e))sendVt(st.e,cur);
  const {t:target,voice,hearing,margin,late}=mixNow(clock,cur,true);
  const off=cur-target,now=Date.now();
  if(hearing&&K.mic.sy)K.mic.sy.h++;
  if(voice){syncSeen(late);return voiceMove(p,off,target,margin,now);}
  if(Math.abs(off)>SEEK_AT){
    if(now-(K.seekAt||0)<SEEK_GAP)return nudge(p,off);
    K.seekAt=now;K.seekT=performance.now();nudge(p,0);K.far=0;
    try{p.seekTo(target+(K.lag||0),true);}catch{/* gone */}
    return;
  }
  K.far=0;
  nudge(p,Math.abs(off)>DRIFT||(K.rate&&K.rate!==1&&Math.abs(off)>NUDGE_OK)?off:0);
}
/** 🎙️ My music while voices lead it (karaoke-mic.js musicMove): a seek only when a voice would play later than my
 * music, or would need too long a hold (VOICE_SEEKS a song, VSEEK_GAP apart; then only past SEEK_AT, as without);
 * otherwise a gentle rate toward the aim (two readings in a row) while the holds keep every voice in time. */
function voiceMove(p,off,target,margin,now){
  const mv=K.M.musicMove(off,margin),gap=now-(K.seekAt||0);
  if(mv==='seek'&&((K.vSeeks<VOICE_SEEKS&&gap>=VSEEK_GAP)||(Math.abs(off)>SEEK_AT&&gap>=SEEK_GAP))){
    K.seekAt=now;K.seekT=performance.now();nudge(p,0);K.far=0;K.vSeeks++;
    try{p.seekTo(target+(K.lag||0),true);}catch{/* gone */}
    return;
  }
  K.far=mv!=='ok'?K.far+1:0;
  nudge(p,K.far>=2||(K.rate&&K.rate!==1&&Math.abs(off)>NUDGE_OK_V)?off:0);
}
/** 🎙️ Every voice I hear, with my music (karaoke-mic.js mixPlan): each one's target is the singer's own video time
 * minus that voice's delay (followTarget, voiceLag with the singer's `ol` and my Web Audio path); `apply` holds each
 * voice (setDelay) so it plays exactly with my music now. My music follows the voices (a listener: all of them; a
 * co-singer: the stage singer's) a margin behind, or the shared clock: the stage singer, or no fresh video time (an
 * older page or service), exactly as without a mic. */
function mixNow(clock,cur,apply){
  const M=K.M,e=K.stage?.e,none={t:clock,voice:false,hearing:false,margin:0};
  if(!M||!e)return none;
  const role=K.mic.pub&&K.mic.pubE===e?'stage':K.mic.cpub&&K.mic.cpubE===e?'co':'ear';
  const now=snow(),list=[],lead=[],hs={};
  const add=(id,h,vt,lag,main)=>{
    hs[id]=h;
    const ok=vt&&vt.e===e;
    const r=ok?M.followTarget({clock,vt,now,age:(Date.now()-vt.got)/1000,lag:M.voiceLag(lag,vt.up,(vt.ol||0)+(h.base?.()||0)),voice:true}):null;
    list.push({id,t:r?.voice?r.t:null});
    if(role==='ear'||(role==='co'&&main))lead.push(id);
  };
  if(K.mic.sub&&K.mic.subE===e&&!K.mic.tap&&K.mic.sub.heard())add('',K.mic.sub,K.vt,K.mic.lag,true);
  for(const [pid,v] of K.co)if(v.h&&v.e===e&&!v.tap&&v.h.heard())add(pid,v.h,K.cvt.get(pid),v.lag,false);
  if(!list.length)return none;
  const margin=role==='co'?M.MIX.coMargin:M.MIX.margin;
  const plan=M.mixPlan({cur,voices:list,lead,margin});
  if(apply)for(const [id,d] of Object.entries(plan.d))hs[id]?.setDelay?.(d);
  const late=Math.max(0,...list.filter(v=>Number.isFinite(v.t)&&lead.includes(v.id)).map(v=>cur-v.t));   // what no hold can fix
  return {t:plan.aim??clock,voice:plan.aim!==null,hearing:true,margin,late};
}
/** Where YouTube takes 0.95 / 1.05 (desktop Chrome does, though its list says only 0.25 steps): nudge() asks for it and
 * a second later the player says what it plays. A rate it rounded off: no more nudges on this page (seeks, and the
 * voices' holds, still work). */
function rateSeen(p){
  if(!K.rate||K.rate===1||!K.rateAt||Date.now()-K.rateAt<1500||K.rateOk)return;
  let r;try{r=p.getPlaybackRate?.();}catch{return;}
  if(!Number.isFinite(r))return;
  if(Math.abs(r-K.rate)<.01){K.rateOk=true;return;}
  K.rateOk=false;K.rate=r;nudge(p,0);
}
/** 🎙️ A singer (stage or 🎤 co): my video's time now, for the listeners to follow (live/karaoke.py kara_vt relays it,
 * stamped), with my own output + capture latency (`ol`, ms) where the browser says it. */
function sendVt(e,cur){
  const t=Date.now();if(K.vtOff||t-K.mic.vtAt<VT_EVERY||!Number.isFinite(cur))return;
  K.mic.vtAt=t;
  const f={t:'kara_vt',e,vt:Math.round(cur*1000)/1000,st:Math.round(snow()*1000)/1000};
  if(K.rate&&K.rate!==1)f.r=K.rate;if(Number.isFinite(K.mic.up))f.rtt=Math.round(K.mic.up*1000);
  if(K.mic.side>0)f.ol=Math.round(K.mic.side*1000);
  live.send(f);
}
/** 🎙️ Every 2 s while the mic is in play, from getStats: each voice's delay as I hear it (jitter buffer, path;
 * lagStep), and, singing, my path's round trip and my own latency (sent with kara_vt). */
function micPoll(){
  const M=K.M;if(!M||K.mic.polling||++K.mic.pt%2)return;
  const jobs=[],pub=K.mic.pub||K.mic.cpub,sub=K.mic.sub;
  if(pub){K.mic.side=M.localLatency(pub.track);
    jobs.push(Promise.resolve(pub.path?.()).then(r=>{if((K.mic.pub||K.mic.cpub)===pub&&Number.isFinite(r?.rtt))K.mic.up=r.rtt;}));}
  if(sub)jobs.push(Promise.resolve(sub.delay?.()).then(r=>{if(K.mic.sub===sub)K.mic.lag=M.lagStep(K.mic.lag,r);}));
  for(const v of K.co.values())if(v.h){const h=v.h;jobs.push(Promise.resolve(h.delay?.()).then(r=>{if(v.h===h)v.lag=M.lagStep(v.lag,r);}));}
  if(!jobs.length)return;
  K.mic.polling=true;
  Promise.allSettled(jobs).then(()=>{K.mic.polling=false;});
}
/** 🎙️ Once a song a listener tells the error beacon (as micReport does) how the voice and the video lined up. The
 * server masks digits, so each value is a letter (karaoke-mic.js bucket: a 0–99 ms, b 100–199 ms … p ≥ 1.5 s): jb my
 * jitter buffer, rtt my path's round trip, up the singer's, lag the delay followed, off how late the voice still
 * played against my music once held (08/10; before: how far my video stayed from its target; median of the last 10 s), hold the voice's delay held now (08/10), ol the singer's own latency, co how
 * many co-singers I hear (a = 0, b = 1 …); `novt` when no video time of the singer came (an older page or service).
 * Sent after 30 s of following, or when listening stops (if the voice played 10 s or more). */
function syncSeen(off){const y=K.mic.sy;if(!y)return;y.n++;y.offs.push(Math.abs(off));if(y.offs.length>10)y.offs.shift();if(y.n===30)syncReport();}
function syncReport(){
  const y=K.mic.sy,M=K.M;if(!y||!M||K.mic.syE===y.e||y.h<10)return;   // heard 10 s at least
  K.mic.syE=y.e;
  const b=x=>M.bucket(Number.isFinite(x)?x*1000:NaN),l=K.mic.lag||{},o=[...y.offs].sort((a,c)=>a-c)[y.offs.length>>1];
  try{beacon('toast',`kara_mic sync${y.n?'':' novt'} jb=${b(l.jb)} rtt=${b(l.rtt)} up=${b(y.up)} lag=${b(M.voiceLag(l,y.up,(K.vt?.ol||0)+(K.mic.sub?.base?.()||0)))} off=${b(o)} hold=${b(K.mic.sub?.held?.())} ol=${b(K.vt?.ol)} co=${b(K.co.size/10)}`,'kara');}catch{/* never in the way */}
}
/** Play a little faster (behind) or slower (ahead), or at 1. 1.9.19 took only a rate YouTube listed, and it lists
 * none between 0.75 and 1.25: no nudge ever happened. Now 1.05 / 0.95 are asked for unless this page saw the player
 * round them off (rateSeen: K.rateOk false). */
function nudge(p,off){
  const want=off&&K.rateOk!==false?(off<0?1.05:.95):1;
  if(want===(K.rate||1))return;
  try{p.setPlaybackRate?.(want);K.rate=want;K.rateAt=Date.now();}catch{/* gone */}
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
  dyn.innerHTML=K.panel?panelHTML():stageHTML()+(live.flags?.kara_mic?'':'<p class="kr-note kr-nomic">🎤 Mic trực tiếp sắp có; giờ hát theo video, cả phòng xem chung</p>')+roundHTML()+queueHTML();   // B3: no voice yet, say so
  paintBar();paintSaid();paintMeter();
  if(K.focus){K.focus=false;dyn.querySelector('[data-kr-focus]')?.focus({preventScroll:true});}
}
function stageHTML(){
  const st=K.stage,me=K.room.me;
  if(K.err&&!st)return `<p class="kr-note bad">${esc(K.err)}</p>`;
  if(!st)return `<p class="kr-empty">🎤 Sân khấu trống</p>`;
  const mine=st.by?.pid===me;
  if(K.clap)return `<div class="kr-clap" role="status"><b>🎉 ${esc(K.clap.by?.name||'')}</b><span>❤️ ${K.clap.hearts} · 🙌 ${K.clap.cheers}${K.clap.tips?` · 💰 ${K.clap.tips}`:''}</span></div>`;
  const left=st.at-snow(),on=!!K.mic.pub;
  const micBtn=mine&&micFlag()?`<button type="button" class="kr-pill kr-micbtn${on?' on':''}" data-kr="mic" aria-pressed="${on}" aria-label="${on?'Tắt mic':'Bật mic trực tiếp'}"${K.mic.busy?' disabled':''}>${on?'🔴 Tắt mic':'🎙️ Mic'}</button>`:'';
  return `<div class="kr-on"><span class="kr-av" aria-hidden="true">🎤</span><span class="grow"><b data-no-translate>${esc(st.by?.name||'')}</b>
    <small data-kr-clock>${left>0?`Bắt đầu sau ${Math.ceil(left)}s`:esc(st.title)}</small></span>
    ${micBtn}${mine?`<button type="button" class="kr-pill" data-kr="skip">⏹</button>`:K.room.account&&!st.reward?`<button type="button" class="kr-pill" data-kr="tip" aria-label="Tặng xu">💰</button>`:''}</div>`+singHTML(mine)+liveHTML();
}
/** 🎙️ The singer's own mic line while it is not live: connecting, or the failure with a retry. */
function singHTML(mine){
  if(!mine||!micFlag()||K.mic.pub||(K.live&&K.live.e===K.stage?.e))return '';
  if(K.mic.busy)return `<div class="kr-live mine" role="status"><small>🎙️ Đang nối mic…</small></div>`;
  if(K.mic.pubFail?.e!==K.stage?.e)return '';
  return `<div class="kr-live mine fail" role="alert"><div class="kr-live-ctl"><b class="grow">Chưa phát được giọng</b><button type="button" class="btn small" data-kr="mic">Thử lại</button></div></div>`;
}
/** 🎙️ "Đang phát trực tiếp": for everyone while the mic is on; the singer sees their time, a listener the voice's own volume. */
function liveHTML(){
  const lv=K.live;if(!lv||!K.stage||lv.e!==K.stage.e)return '';
  const mine=lv.by?.pid===K.room?.me,coHeard=[...K.co.values()].some(v=>v.h);
  if(mine)return `<div class="kr-live mine" role="status"><b>🎤 Đang phát trực tiếp giọng hát</b><small><span data-kr-mic>${K.mic.pub?`🔴 ${fmt(lv.until-snow())}`:'🎙️ Đang nối mic…'}</span> · 🎧 Đeo tai nghe cho đỡ vọng nhạc</small>${coHTML(true)}${coHeard||tapWanted()?`<div class="kr-live-ctl">${tapHTML()}${volHTML()}</div>`:''}</div>`;
  const ls=K.mic.ls;
  if(!K.mic.sub&&ls==='nortc')return `<div class="kr-live" role="status"><b>🎤 Đang phát trực tiếp giọng hát</b><small>Máy này chưa nghe được giọng trực tiếp. Mở bằng Chrome hoặc Safari nhé.</small></div>`;
  if(!K.mic.sub&&ls==='fail')return `<div class="kr-live fail" role="alert"><b>🎤 Đang phát trực tiếp giọng hát</b><div class="kr-live-ctl"><span class="grow">Chưa nghe được giọng</span><button type="button" class="btn small" data-kr="voiceretry">Thử lại</button></div>${coHTML(false)}</div>`;
  if(!K.mic.sub&&ls==='join')return `<div class="kr-live" role="status"><b>🎤 Đang phát trực tiếp giọng hát</b><small>🎧 Đang nối giọng…</small>${coHTML(false)}</div>`;
  const tap=tapHTML(),ctl=K.mic.sub||coHeard?volHTML():'';
  return `<div class="kr-live" role="status"><b>🎤 Đang phát trực tiếp giọng hát</b>${tap||ctl?`<div class="kr-live-ctl">${tap}${ctl}</div>`:''}${coHTML(false)}</div>`;
}
const tapHTML=()=>tapWanted()?`<button type="button" class="btn primary kr-tap" data-kr="voicetap">🔈 Chạm để nghe giọng</button>`:'';
const volHTML=()=>`<label class="kr-vol"><span aria-hidden="true">🎤</span><input type="range" min="0" max="100" step="5" value="${Math.round(K.mic.vol*100)}" data-kr-vol aria-label="Âm lượng giọng hát"></label>
    <button type="button" class="kr-pill" data-kr="voicemute" aria-pressed="${K.mic.muted}" aria-label="${K.mic.muted?'Bật tiếng giọng hát':'Tắt tiếng giọng hát'}">${K.mic.muted?'🔇':'🔊'}</button>`;
/** 🎤 Hát cùng in the live line: who sings along (the stage singer can turn each one off), the asks waiting for the
 * stage singer, and for anyone else the one button (or where their own ask / mic is). */
function coHTML(mine){
  const me=K.room?.me,list=K.coList;
  let h=list.length?`<div class="kr-co"><small>🎤 Hát cùng:</small>${list.map(c=>`<span class="kr-co-n"><b data-no-translate>${esc(c.name||'')}</b>${mine?`<button type="button" class="kr-x-s" data-kr="cokick" data-pid="${esc(c.pid)}" aria-label="Tắt mic người hát cùng">✕</button>`:''}</span>`).join('')}</div>`:'';
  if(mine){
    const now=snow();
    return h+K.asks.filter(a=>!(a.until<now)).map(a=>`<div class="kr-ask"><span class="grow">🙋 <b data-no-translate>${esc(a.name||'')}</b> <span>muốn hát cùng</span></span>
      <button type="button" class="btn small primary" data-kr="let" data-pid="${esc(a.pid)}" data-ok="1">Cho hát</button><button type="button" class="kr-pill" data-kr="let" data-pid="${esc(a.pid)}" data-ok="0" aria-label="Không cho">✕</button></div>`).join('');
  }
  if(!coCan())return h;
  const c=K.mic.co;
  if(K.mic.cpub)return h+`<div class="kr-live-ctl"><b class="grow">🔴 Bạn đang hát cùng</b><button type="button" class="btn small" data-kr="joinoff">Tắt mic</button></div><small>🎧 Đeo tai nghe cho đỡ vọng nhạc</small>`;
  if(c.st==='ask')return h+`<div class="kr-live-ctl"><small class="grow">🙋 Đang chờ người hát đồng ý…</small><button type="button" class="btn small" data-kr="joinoff">Hủy</button></div>`;
  if(c.st==='join')return h+`<small>🎙️ Đang nối mic…</small>`;
  if(c.st==='fail')return h+`<div class="kr-live-ctl"><span class="grow">Chưa phát được giọng</span><button type="button" class="btn small" data-kr="join">Thử lại</button></div>`;
  return list.length<CO_MAX||list.some(x=>x.pid===me)?h+`<div class="kr-live-ctl"><button type="button" class="btn small kr-join" data-kr="join">🎤 Hát cùng</button></div>`:h;
}
const CO_MAX=3;
const coCan=()=>micFlag()&&!!K.room?.account&&!K.coOff&&!!window.RTCPeerConnection;
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
  const mc=K.dlg?.querySelector('[data-kr-mic]');if(mc&&K.live&&K.mic.pub)mc.textContent=`🔴 ${fmt(K.live.until-snow())}`;
  const l=K.dlg?.querySelector('[data-kr-left]');if(l&&K.round)l.textContent=fmt(K.round.until-snow());
}

/* ---------------------------------------------------------------- panels: add a song, a round, a tip, more */
function panelHTML(){
  const p=K.panel,close=`<button type="button" class="icon-btn kr-x" data-kr="panel" data-p="" aria-label="Đóng">${icon('x',16)}</button>`;
  if(p==='add'){
    const s=K.song;
    return `<div class="kr-panel">${close}<label class="kr-field"><input data-kr-link data-kr-focus inputmode="url" placeholder="Dán link YouTube" value="${esc(K.link||'')}"></label>${s?.ok?'':'<p class="kr-note kr-how">Mở YouTube → Chia sẻ → Sao chép đường liên kết → dán vào đây</p>'}
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
    const me=K.room.me,blk=K.room.account&&live.flags?.chat;
    return `<div class="kr-panel">${close}<ul class="kr-people">${K.people.map(x=>`<li><span>${esc(x.name)}</span>${x.pid!==me?`<button type="button" class="kr-pill" data-kr="report" data-pid="${esc(x.pid)}" aria-label="Báo cáo">🚩</button>${blk?`<button type="button" class="kr-pill" data-kr="block" data-pid="${esc(x.pid)}" aria-label="Chặn">🚫</button>`:''}${K.room.adm?`<button type="button" class="kr-pill" data-kr="kick" data-pid="${esc(x.pid)}" aria-label="Mời ra">🚪</button>`:''}`:''}</li>`).join('')}</ul></div>`;
  }
  if(p==='micask')return `<div class="kr-panel">${close}<b>🎙️ Hát trực tiếp</b><p class="kr-note">Cả phòng nghe giọng bạn ngay lúc hát. Không ghi âm. Mic tự tắt khi hết bài hoặc sau 6 phút.</p>
    <p class="kr-note">🎧 Đeo tai nghe để nhạc không vọng vào mic.</p><button type="button" class="btn primary wide" data-kr="micgo"${K.mic.busy?' disabled':''}>🎙️ Bật mic</button></div>`;
  if(p==='coask')return `<div class="kr-panel">${close}<b>🎤 Hát cùng</b><p class="kr-note">Người hát đồng ý là cả phòng nghe giọng bạn hát chung. Không ghi âm.</p>
    <p class="kr-note">🎧 Đeo tai nghe để nhạc không vọng vào mic.</p><button type="button" class="btn primary wide" data-kr="joingo">🙋 Xin hát cùng</button></div>`;
  if(p==='birth'){
    const y=new Date().getFullYear();let opts='<option value="">Năm sinh</option>';for(let i=y;i>=1930;i--)opts+=`<option value="${i}">${i}</option>`;
    return `<div class="kr-panel">${close}<b>🎂 Bạn sinh năm nào?</b><p class="kr-note">Chỉ để mở mic trực tiếp (từ 16 tuổi). Lưu một lần, không đổi được.</p>
      <select class="kr-field" data-kr-year aria-label="Năm sinh">${opts}</select>${K.err?`<p class="kr-note bad">${esc(K.err)}</p>`:''}
      <button type="button" class="btn primary wide" data-kr="birthgo"${K.busy?' disabled':''}>Lưu</button></div>`;
  }
  if(p==='young')return `<div class="kr-panel">${close}<b>🎧 Bạn nghe cùng mọi người nhé</b><p class="kr-note">Mic trực tiếp dành cho bạn từ 16 tuổi. Bạn vẫn nghe, thả tim và cổ vũ được nha.</p></div>`;
  if(p==='micreport')return `<div class="kr-panel">${close}<b>🚩 Báo cáo giọng hát</b><div class="kr-menu">${[['rude','Nói bậy / quấy rối'],['minor','🛟 Có vẻ là trẻ em'],['other','Khác']].map(([r,l])=>`<button type="button" data-kr="micreportgo" data-r="${r}">${esc(l)}</button>`).join('')}</div></div>`;
  const st=K.stage,mine=st?.by?.pid===K.room.me,adm=K.room.adm,lv=K.live&&st&&K.live.e===st.e;
  const items=[['round','🧩 Đố bài'],...(st&&!mine?[['vote',`👎 Bỏ bài ${st.votes||0}/${st.need||1}`],['report-song','🚩 Báo cáo bài']]:[]),...(lv&&!mine?[['micreport','🚩 Báo cáo giọng hát']]:[]),...(K.round&&(K.round.host?.pid===K.room.me||adm)?[['endround','⏹ Kết thúc đố']]:[]),
    ...(adm?[['adm-skip','⏭ Bỏ bài (QL)'],...(st?[['adm-mic','🔇 Cắt mic (QL)']]:[]),['adm-ban','🚫 Cấm bài'],['adm-close','🔒 Đóng phòng']]:[]),['out','🚪 Ra']];
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
    case'block':if(!confirm('Chặn người này? Hai bạn sẽ không thấy tin, không nghe giọng nhau.'))return;live.send({t:'block',pid:d.pid});toast('Đã chặn.');K.panel=null;paint();return;
    case'mic':if(K.mic.pub){micOff();return;}if(!micCan())return;if(!seenAsk()){K.panel='micask';K.err='';paint();return;}micOn();return;
    case'micgo':seenAsk(true);K.panel=null;micOn();return;
    case'join':if(!micCan())return;if(!seenAsk()){K.panel='coask';K.err='';paint();return;}coJoin();return;
    case'joingo':seenAsk(true);K.panel=null;coJoin();return;
    case'joinoff':coOff();return;
    case'let':if(K.live)live.send({t:'kara_let',e:K.live.e,pid:d.pid,ok:d.ok==='1'?1:0});K.asks=K.asks.filter(a=>a.pid!==d.pid);paint();return;
    case'cokick':if(K.live)live.send({t:'kara_let',e:K.live.e,pid:d.pid,ok:0});return;
    case'birthgo':{
      const y=Number(K.dlg.querySelector('[data-kr-year]')?.value||0);if(!y){K.err='Chọn năm sinh nhé.';paint();return;}
      K.busy=true;K.err='';paint();
      try{const r=await api.post('/api/karaoke/birth',{year:y});K.busy=false;if(!r.mic){K.panel='young';paint();return;}K.panel=null;paint();if(K.birthNext==='join')coJoin();else micOn();}
      catch(e){K.busy=false;K.err=e.message||'Chưa lưu được.';paint();}
      return;
    }
    case'voicetap':voiceTap();return;
    case'voiceretry':K.mic.tries=0;K.mic.ls='';listen();return;
    case'voicemute':K.mic.muted=!K.mic.muted;for(const h of voices())h.mute(K.mic.muted);paint();return;
    case'micreport':K.panel='micreport';paint();return;
    case'micreportgo':if(K.live?.by?.pid)live.send({t:'kara_report',pid:K.live.by.pid,reason:d.r});toast('Đã báo cáo. Cảm ơn bạn!');K.panel=null;paint();return;
    case'adm-mic':live.send({t:'kara_mic_cut'});K.panel=null;paint();return;
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
/** One request/answer over the socket (an error frame for it ends it too). `match`: only a reply it accepts (two asks
 * of the same type at once: 🎤 one voice's kara_listen each). */
function ask(t,frame,reply,ms=4000,match=null){
  return new Promise(ok=>{
    let done=false;const fin=v=>{if(done)return;done=true;off1();off2();ok(v);};
    const off1=live.on(reply,f=>{if(!match||match(f))fin(f);}),off2=live.on('error',f=>{if(f.ref===t)fin({ok:false,msg:f.msg,code:f.code});});
    if(!live.send({t,...frame}))fin({ok:false,msg:'Đang kết nối lại…'});
    setTimeout(()=>fin(null),ms);
  });
}

/* ---------------------------------------------------------------- 🎙️ the live mic (v4/karaoke-mic.js) */
function seenAsk(set){try{if(set)localStorage.setItem('kr-mic-ask','1');return localStorage.getItem('kr-mic-ask')==='1';}catch{return !!set;}}
function micCan(){
  if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia||!window.RTCPeerConnection){toast('Máy này chỉ nghe được. Mở bằng Safari/Chrome để hát trực tiếp nhé.',true);return false;}
  return true;
}
/** 🎙️ A mic step that failed (or a wait given up on) on the page's error beacon (telemetry.js error(): kind 'toast',
 * once per page load per text, repeats counted; digits are masked at the server): "kara_mic listen sdk: self timeout,
 * cdn load". `role` listen | sing, `stage` the step that did not complete. */
function micReport(role,stage,code){try{beacon('toast',`kara_mic ${role} ${stage}: ${String(code||'?').slice(0,80)}`,'kara');}catch{/* never in the way */}}
const errCode=err=>err?.code&&err?.stage?err.code:[err?.name,String(err?.message||err||'').replace(/https?:\/\/\S+/g,'').slice(0,48)].filter(Boolean).join(' ')||'?';
const NEXT={'':'mod',mod:'sdk',sdk:'token',token:'signal',perm:'signal',signal:'ice',ice:'track',track:'audio'};
const SERVER_END=new Set([4,5,10]);   // LiveKit DisconnectReason: PARTICIPANT_REMOVED, ROOM_DELETED, ROOM_CLOSED (the mic went off)
const MIC_NO_PERM='Bạn chưa cho phép micro. Mở cài đặt trang web › Micro để bật nhé.';

async function micOn(){
  if(K.mic.busy||K.mic.pub||!K.stage)return;
  const e0=K.stage.e;
  K.mic.busy=true;K.mic.pubFail=null;K.mic.pubAt='';paint();
  let M;
  try{M=await mic();K.mic.pubAt='mod';ownLatency(M);await M.loadSDK();K.mic.pubAt='sdk';}   // before the server puts the mic live for the room
  catch(err){K.mic.busy=false;singFailed(e0,err?.stage||NEXT[K.mic.pubAt],err);paint();return;}
  if(!K.stage||K.stage.e!==e0){K.mic.busy=false;paint();return;}
  const r=await ask('kara_mic',{on:1},'kara_mic',8000);
  if(!r?.on){
    K.mic.busy=false;
    if(r?.code==='birth'){K.panel='birth';K.err='';K.birthNext='';}else if(r?.code==='young')K.panel='young';else toast(r?.msg||'Chưa bật được mic, thử lại nhé.',true);
    if(!r)micReport('sing','token','timeout');   // a refusal with a reason is the game saying no, not a failure
    paint();return;
  }
  K.mic.pubAt='token';
  const e=r.e;let h=null;
  try{
    h=await M.publish({url:r.url,token:r.token,onStage:s=>{K.mic.pubAt=s;},onEnd:(_,why)=>{
      if(!h||K.mic.pub!==h)return;
      K.mic.pub=null;K.mic.pubE=null;
      if(SERVER_END.has(why)){paint();return;}   // the server turned it off: its kara_live frame says so
      live.send({t:'kara_mic',on:0});micReport('sing','ice',`dropped r${why??'?'}`);
      K.mic.pubFail={e,stage:'ice'};toast('Mic đã ngắt kết nối.',true);paint();}});
    if(!K.stage||K.stage.e!==e||!K.live||K.live.e!==e){h.stop();live.send({t:'kara_mic',on:0});micReport('sing','track','stale');}   // the song or the mic ended meanwhile
    else{K.mic.pub=h;K.mic.pubE=e;sendCheck(h);}
  }catch(err){
    live.send({t:'kara_mic',on:0});
    singFailed(e,err?.stage||NEXT[K.mic.pubAt],err);
  }
  K.mic.busy=false;paint();
}
function singFailed(e,stage,err){
  micReport('sing',stage||'?',errCode(err));
  K.mic.pubFail={e,stage};
  toast(err?.name==='NotAllowedError'?MIC_NO_PERM:err?.name==='NotFoundError'?'Không thấy micro trên máy này.':'Chưa kết nối được mic, thử lại nhé.',true);
}
/** The singer's voice leaves the phone: outbound RTP bytes a few seconds after publishing. */
function sendCheck(h,role='sing'){
  const mine=()=>K.mic.pub===h||K.mic.cpub===h;
  setTimeout(async()=>{
    if(!mine())return;
    const s=await h.stats?.();if(!mine())return;
    if(s&&s.bytes>0){if(role==='sing')K.mic.pubAt='audio';}else micReport(role,'audio','notx');
  },5000);
}
/** A singer's own latency needs a running AudioContext to read (Chrome; where `outputLatency` exists at all). */
function ownLatency(M){try{if('outputLatency' in (window.AudioContext||Object).prototype)M.audioCtx();}catch{/* none */}}
function micOff(){if(!K.mic.pub)return;micStop();live.send({t:'kara_mic',on:0});paint();}
function micStop(){const h=K.mic.pub;K.mic.pub=null;K.mic.pubE=null;K.mic.up=null;K.mic.vtAt=0;try{h?.stop();}catch{/* gone */}}
/** Listening off here. A listener still waiting after 8 s (the song ended, they left) is reported with its stage. */
function stopListen(){
  const h=K.mic.sub;
  if(K.mic.joining&&Date.now()-K.mic.t0>8000)micReport('listen',NEXT[K.mic.at]||'?','left waiting');
  else if(h&&K.mic.tap)micReport('listen','audio','tap not pressed');
  syncReport();K.vt=null;K.mic.sy=null;K.mic.lag={};
  K.mic.gen++;K.mic.joining=false;K.mic.sub=null;K.mic.subE=null;K.mic.tap=false;K.mic.ls='';clearTimeout(K.mic.hc);
  try{h?.stop();}catch{/* gone */}
}
/** Everything of the mic off here (a new song, the end, leaving the room). */
function liveOff(){K.live=null;micStop();stopListen();coReset();}
function onLive(f){
  if(!f.on){if(K.live&&K.live.e!==f.e)return;K.live=null;if(K.mic.pubE===f.e)micStop();stopListen();coReset();paint();return;}
  if(!K.stage||K.stage.e!==f.e)return;
  if(K.live&&K.live.e!==f.e)stopListen();
  K.live={on:1,e:f.e,by:f.by,until:f.until};K.mic.tries=0;K.mic.pubFail=null;
  if(f.by?.pid!==K.room?.me)listen();
  paint();
}
/** A listener: the SDK first (so a slow network never spends the token's minute), then the token, the SFU, the voice.
 * `gen` ties every await to this attempt: stopListen() (or a failure) moves it on and a late answer is dropped. */
async function listen(){
  const lv=K.live;if(!lv||!micFlag()||K.mic.sub||K.mic.joining||lv.by?.pid===K.room?.me)return;
  if(!window.RTCPeerConnection){if(K.mic.ls!=='nortc'){K.mic.ls='nortc';micReport('listen','mod','no RTCPeerConnection');paint();}return;}
  const gen=++K.mic.gen,e=lv.e,mine=()=>K.mic.gen===gen,still=()=>mine()&&K.live?.e===e;
  const reach=s=>{if(mine())K.mic.at=s;};
  K.mic.joining=true;K.mic.ls='join';K.mic.at='';K.mic.t0=Date.now();paint();
  let M=null,h=null;
  try{
    M=await mic();reach('mod');if(!still())return;
    await M.loadSDK();reach('sdk');if(!still())return;
    const r=await ask('kara_listen',{},'kara_listen',6000,f=>!f.pid);if(!still())return;
    if(!r)throw M.fail('token','timeout');
    if(!r.on||r.e!==e){K.mic.ls='';return;}   // off meanwhile, or not for me: nothing to hear and nothing to say (a block stays unseen)
    reach('token');
    h=await M.listen({url:r.url,token:r.token,volume:K.mic.vol,ctx:M.audioCtx(),onStage:reach,
      onTap:need=>{if(!mine())return;const was=K.mic.tap;K.mic.tap=need;if(was&&!need&&K.mic.sub)heardCheck(gen);if(was!==need)paint();},
      onEnd:(_,why)=>{
        if(!mine()||!h||K.mic.sub!==h)return;
        if(SERVER_END.has(why)){K.mic.sub=null;K.mic.subE=null;K.mic.ls='';paint();return;}   // the mic went off: the kara_live frame follows
        listenFailed(gen,'ice',`dropped r${why??'?'}`);}});
    if(!still()){h.stop();return;}
    K.mic.sub=h;K.mic.subE=e;K.mic.ls='live';h.mute(K.mic.muted);
    K.mic.lag={};if(K.mic.sy?.e!==e)K.mic.sy={e,n:0,h:0,offs:[],up:K.vt?.up??null};
    heardCheck(gen);
  }catch(err){
    if(mine())listenFailed(gen,err?.stage||NEXT[K.mic.at]||'?',errCode(err));
  }finally{
    if(mine()){K.mic.joining=false;if(K.mic.ls==='join'&&!K.mic.sub)K.mic.ls='';}
    paint();
  }
}
/** Audio playing: inbound RTP bytes a few seconds in, and the phone allowed to play (else "Chạm để nghe giọng"). */
function heardCheck(gen){
  clearTimeout(K.mic.hc);
  K.mic.hc=setTimeout(async()=>{
    const h=K.mic.sub;if(K.mic.gen!==gen||!h)return;
    const s=await h.stats();if(K.mic.gen!==gen||K.mic.sub!==h)return;
    if(!s||!s.bytes){listenFailed(gen,'audio','norx');return;}
    if(h.canPlay()){K.mic.at='audio';K.mic.tries=0;}
  },4000);
}
/** A listening attempt failed: report it, then try again by itself twice (2 s, 4 s), then "Chưa nghe được giọng · Thử lại". */
function listenFailed(gen,stage,code){
  if(K.mic.gen!==gen)return;
  const h=K.mic.sub;
  K.mic.gen++;K.mic.joining=false;K.mic.sub=null;K.mic.subE=null;K.mic.tap=false;clearTimeout(K.mic.hc);
  try{h?.stop();}catch{/* gone */}
  micReport('listen',stage,code);
  if(K.live&&++K.mic.tries<=2){
    K.mic.ls='join';const g=K.mic.gen;
    setTimeout(()=>{if(K.mic.gen===g&&K.live&&!K.mic.sub&&!K.mic.joining)listen();},2000*K.mic.tries);
  }else K.mic.ls=K.live?'fail':'';
  paint();
}
/** "Chạm để nghe giọng" (or any tap in the sheet while the phone waits for one): inside the click, iPhone resumes audio.
 * 🎤 Every voice waiting for it (they share one AudioContext, but each LiveKit room keeps its own flag). */
function voiceTap(){
  const h=K.mic.sub;
  if(h&&K.mic.tap){
    let p;try{p=h.tap();}catch(err){p=Promise.reject(err);}
    Promise.resolve(p).then(()=>{if(K.mic.sub!==h)return;if(h.canPlay()){K.mic.tap=false;heardCheck(K.mic.gen);}paint();})
      .catch(err=>{micReport('listen','audio',`tap ${errCode(err)}`);});
  }
  for(const v of K.co.values())if(v.h&&v.tap){const c=v.h;Promise.resolve().then(()=>c.tap()).then(()=>{if(v.h===c&&c.canPlay()){v.tap=false;paint();}}).catch(()=>{/* the next tap */});}
}
const tapWanted=()=>!!(K.mic.sub&&K.mic.tap)||[...K.co.values()].some(v=>v.h&&v.tap);
/** Every voice handle I hear now. */
const voices=()=>[K.mic.sub,...[...K.co.values()].map(v=>v.h)].filter(Boolean);
function setVol(v){K.mic.vol=v;for(const h of voices())h.setVolume(v);try{localStorage.setItem('kr-voice-vol',String(v));}catch{/* private mode */}}

/* ---------------------------------------------------------------- 🎤 hát cùng (live/karaoke.py kara_join / kara_let)
 * Anyone else in the room may ask to sing along while the stage singer's mic is live (🎤 Hát cùng; the headphones note
 * the first time, the birth year if the account has none); the stage singer answers on their live line (Cho hát / ✕)
 * and can turn a co-singer off (✕ by the name). A co-singer publishes like the stage singer (their own SFU room), hears
 * the stage singer with their music a little behind it (mixNow: lead), never hears themselves (no local monitor), and
 * the other co-singers as soon as they arrive. Every page hears each co-singer through a listen() of its own. */
async function coJoin(){
  const lv=K.live,st=K.stage;if(!lv||!st||lv.e!==st.e||K.mic.cpub||K.mic.co.st==='ask'||K.mic.co.st==='join')return;
  const e=lv.e;K.mic.co={st:'ask',e};paint();
  mic().then(M=>{ownLatency(M);return M.loadSDK();}).catch(()=>{/* coPublish says so */});   // while the singer decides
  const r=await ask('kara_join',{e,on:1},'kara_join',8000);
  if(K.mic.co.e!==e||K.mic.co.st!=='ask')return;
  if(r?.on)return;   // waiting (kara_sing comes with the answer) or live again (kara_sing came first)
  K.mic.co={st:''};
  if(r?.code==='birth'){K.panel='birth';K.err='';K.birthNext='join';}
  else if(r?.code==='young')K.panel='young';
  else if(r?.code==='unknown')K.coOff=true;
  else toast(r?.msg||'Chưa xin hát cùng được, thử lại nhé.',true);
  paint();
}
function coRefused(f){
  if(K.mic.co.e!==f.e||K.mic.cpub)return;
  const was=K.mic.co.st;K.mic.co={st:''};
  if(was==='ask'||was==='join')toast(f.why==='time'?'Người hát chưa trả lời, lát thử lại nhé.':f.why==='sfu'?'Mic đang bận, thử lại sau ít phút nhé.':'Lần này bạn nghe cùng mọi người nhé 🎧',true);
  paint();
}
/** The stage singer said yes (or I asked again while on): my mic into my own SFU room. */
async function coPublish(f){
  if(!K.stage||K.stage.e!==f.e||!K.live||K.live.e!==f.e)return;
  if(K.mic.cpub){if(K.mic.cpubE===f.e)return;coStop();}
  if(K.mic.co.st==='join')return;
  K.mic.co={st:'join',e:f.e};paint();
  let h=null;
  try{
    const M=await mic();ownLatency(M);
    h=await M.publish({url:f.url,token:f.token,onEnd:(_,why)=>{
      if(!h||K.mic.cpub!==h)return;
      K.mic.cpub=null;K.mic.cpubE=null;K.mic.co={st:''};
      if(SERVER_END.has(why)){paint();return;}   // turned off by the server: its kara_co / kara_live frame says so
      live.send({t:'kara_join',e:f.e,on:0});micReport('cosing','ice',`dropped r${why??'?'}`);
      K.mic.co={st:'fail',e:f.e};toast('Mic đã ngắt kết nối.',true);paint();}});
    if(!K.stage||K.stage.e!==f.e||!K.live||K.live.e!==f.e||K.mic.co.st!=='join'){h.stop();live.send({t:'kara_join',e:f.e,on:0});K.mic.co={st:''};}
    else{K.mic.cpub=h;K.mic.cpubE=f.e;K.mic.co={st:'live',e:f.e};sendCheck(h,'cosing');}
  }catch(err){
    live.send({t:'kara_join',e:f.e,on:0});micReport('cosing',err?.stage||'?',errCode(err));
    K.mic.co={st:'fail',e:f.e};
    toast(err?.name==='NotAllowedError'?MIC_NO_PERM:err?.name==='NotFoundError'?'Không thấy micro trên máy này.':'Chưa kết nối được mic, thử lại nhé.',true);
  }
  paint();
}
/** I stop: an ask withdrawn, or my co-singer mic off. */
function coOff(){
  const c=K.mic.co,e=c.e||K.mic.cpubE||K.live?.e;
  coStop();K.mic.co={st:''};
  if(e)live.send({t:'kara_join',e,on:0});
  paint();
}
function coStop(){const h=K.mic.cpub;K.mic.cpub=null;K.mic.cpubE=null;if(!K.mic.pub)K.mic.up=null;try{h?.stop();}catch{/* gone */}}
/** All of hát cùng off here (the mic went off, a new song, leaving). */
function coReset(){coStop();K.mic.co={st:''};for(const pid of [...K.co.keys()])coDrop(pid);K.cvt.clear();K.coList=[];K.asks=[];}
/** kara_co: a co-singer on (hear them) or off (stop hearing them; mine: my mic off). */
function onCo(f){
  const me=K.room?.me;
  K.coList=K.coList.filter(c=>c.pid!==f.pid);
  if(f.on){
    K.coList.push({pid:f.pid,name:f.name});K.asks=K.asks.filter(a=>a.pid!==f.pid);
    if(f.pid!==me)coListen(f.pid);
    return;
  }
  if(f.pid===me){
    const was=!!K.mic.cpub||K.mic.co.st==='join';coStop();K.mic.co={st:''};
    if(was&&f.why!=='off')toast(f.why==='kick'?'Người hát đã tắt mic hát cùng của bạn.':'Mic hát cùng đã tắt.',f.why==='kick');
  }else coDrop(f.pid);
}
/** One co-singer's voice in my page: like listen() (the SDK, a token for that voice, the SFU), held with my music. */
async function coListen(pid){
  const lv=K.live;if(!lv||!micFlag()||pid===K.room?.me||!window.RTCPeerConnection)return;
  let v=K.co.get(pid);if(v&&(v.h||v.joining))return;
  if(!v){v={pid,h:null,e:lv.e,joining:false,tries:0,gen:0,tap:false,lag:{}};K.co.set(pid,v);}
  const gen=++v.gen,e=lv.e,still=()=>K.co.get(pid)===v&&v.gen===gen&&K.live?.e===e;
  v.joining=true;v.e=e;
  try{
    const M=await mic();await M.loadSDK();if(!still())return;
    const r=await ask('kara_listen',{pid},'kara_listen',6000,f=>f.pid===pid);if(!still())return;
    if(!r)throw M.fail('token','timeout');
    if(!r.on||r.e!==e)return;   // off meanwhile, or not for me (a block stays unseen)
    const h=await M.listen({url:r.url,token:r.token,volume:K.mic.vol,ctx:M.audioCtx(),
      onTap:need=>{if(!still())return;const was=v.tap;v.tap=need;if(was!==need)paint();},
      onEnd:(_,why)=>{if(!still()||v.h!==h)return;v.h=null;if(SERVER_END.has(why)){paint();return;}coListenFailed(v,gen,'ice',`dropped r${why??'?'}`);}});
    if(!still()){h.stop();return;}
    v.h=h;v.lag={};h.mute(K.mic.muted);
  }catch(err){
    if(still())coListenFailed(v,gen,err?.stage||'?',errCode(err));
  }finally{
    if(K.co.get(pid)===v&&v.gen===gen)v.joining=false;
    paint();
  }
}
/** A co-singer's voice failed: reported, then tried again by itself twice (2 s, 4 s); after that it stays quiet. */
function coListenFailed(v,gen,stage,code){
  if(v.gen!==gen)return;
  const h=v.h;v.gen++;v.joining=false;v.h=null;v.tap=false;
  try{h?.stop();}catch{/* gone */}
  micReport('colisten',stage,code);
  if(K.live&&++v.tries<=2){const g=v.gen;setTimeout(()=>{if(K.co.get(v.pid)===v&&v.gen===g&&!v.h&&!v.joining)coListen(v.pid);},2000*v.tries);}
}
function coDrop(pid){const v=K.co.get(pid);if(!v)return;K.co.delete(pid);K.cvt.delete(pid);v.gen++;try{v.h?.stop();}catch{/* gone */}}
/** My music's position now (the state export's target). */
const curNow=()=>{try{return K.player?.getCurrentTime?.()??NaN;}catch{return NaN;}};

/** For tests and the browser check: what this page holds now. */
export const karaoke={state:()=>({view:K.view,room:K.room?.id||null,stage:K.stage?{e:K.stage.e,vid:K.stage.vid,at:K.stage.at,phase:K.stage.phase}:null,
  queue:K.queue.length,round:K.round,reveal:K.reveal,off:K.off,best:K.best,pos:K.stage?pos():null,
  cur:(()=>{try{return K.player?.getCurrentTime?.()??null;}catch{return null;}})(),ps:(()=>{try{return K.player?.getPlayerState?.()??null;}catch{return null;}})(),said:K.said.length,
  live:K.live?{e:K.live.e,by:K.live.by?.pid}:null,pub:!!K.mic.pub,sub:!!K.mic.sub,heard:!!K.mic.sub?.heard(),tap:K.mic.tap,panel:K.panel,
  ls:K.mic.ls,at:K.mic.at,pubAt:K.mic.pubAt,pubFail:K.mic.pubFail?.stage||null,tries:K.mic.tries,
  follow:K.stage?mixNow(pos(),curNow(),false).voice:false,target:K.stage?mixNow(pos(),curNow(),false).t:null,vt:K.vt?{vt:K.vt.vt,at:K.vt.at,up:K.vt.up,ol:K.vt.ol,age:(Date.now()-K.vt.got)/1000}:null,vtOff:K.vtOff,
  lag:K.M&&K.mic.sub?K.M.voiceLag(K.mic.lag,K.vt?.up,(K.vt?.ol||0)+(K.mic.sub.base?.()||0)):null,jb:K.mic.lag?.jb??null,rate:K.rate||1,rateOk:K.rateOk,
  hold:K.mic.sub?.held?.()??null,side:K.mic.side,
  co:K.coList.map(c=>c.pid),coHeard:[...K.co.values()].filter(v=>v.h&&v.h.heard()).map(v=>v.pid),coHold:Object.fromEntries([...K.co.values()].filter(v=>v.h).map(v=>[v.pid,v.h.held()])),
  cpub:!!K.mic.cpub,coSt:K.mic.co.st,asks:K.asks.map(a=>a.pid),coOff:K.coOff}),
  /** 🎙️ the RTP counters of my mic (singer, 🎤 co-singer) or of the voices I hear (listener) */
  micStats:async()=>({pub:await (K.mic.pub||K.mic.cpub)?.stats?.()??null,sub:await K.mic.sub?.stats?.()??null,
    co:Object.fromEntries(await Promise.all([...K.co.values()].filter(v=>v.h).map(async v=>[v.pid,await v.h.stats()])))}),
  micPath:async()=>await K.mic.sub?.path?.()??null};
