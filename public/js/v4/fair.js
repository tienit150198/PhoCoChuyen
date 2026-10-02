/** 🏮 Hội chợ dân gian: the gate (Cổng hội) puts the earn-xu stalls first (ô ăn quan against a neighbour, ném vòng
 * cổ chai), then the small-stake ones (bầu cua tôm cá, lô tô, the back corner's xóc đĩa and Công an phường), the Bảng vàng.
 * Every rule, result and number is the server's (game/fair*.py): this file renders
 * api.state.fair, sends `fair_*` commands and plays the show around their results (the bowl shaking, the gánh lô tô,
 * the raid). The lô tô calls of a round come with the state; cô Bảy Lô Tô reads them out at the player's pace (paused
 * while the stall is not on screen), the player marks the tờ dò by hand and "Kinh!" is checked by the server against
 * those calls and marks. Her verses and the troupe's acts: ./fair-loto.js.
 * Its own dialog (like the bank), opened with data-action="fair" (Khu phố hub, the journey banner).
 * Styles: /css/fair.css. Sounds: tiny Web Audio effects, off when the game's sound is off. Music: only the gánh lô tô
 * plays one recorded CC0 track (public/music/CREDITS.md), and only while the game's music is on. */
import {icon,escapeHTML as esc} from '../icons.js';
import {audioContext,wantAudio,duck} from '../audio.js';
import {language} from './i18n.js';
import {words,callLine,MC,ACTS,CROWD,STICKERS,MODE_STICKER} from './fair-loto.js';
import {setup as dartsSetup} from './fair-darts.js';

const FACES=['bau','cua','tom','ca','ga','nai'];
const FACE_NAME={bau:'Bầu',cua:'Cua',tom:'Tôm',ca:'Cá',ga:'Gà',nai:'Nai'};
const GOURD='<svg class="fh-gourd" viewBox="0 0 40 48" aria-hidden="true"><path d="M20 4c1.2 0 2 .9 2 2v3.4c2.9 1 4.8 3.6 4.8 6.6 0 1.8-.6 3.4-1.7 4.7C31 22.8 35 27.6 35 33.5 35 41.2 28.3 46 20 46S5 41.2 5 33.5c0-5.9 4-10.7 9.9-12.8-1.1-1.3-1.7-2.9-1.7-4.7 0-3 1.9-5.6 4.8-6.6V6c0-1.1.8-2 2-2z" fill="#86b84a" stroke="#3f6b1d" stroke-width="2"/><path d="M21 6.5c2.6-2.4 6.6-2.6 9.2-.6" fill="none" stroke="#3f6b1d" stroke-width="2" stroke-linecap="round"/><path d="M13 31c1.5-3 4-4.6 7-5" fill="none" stroke="#e9f5d3" stroke-width="2.4" stroke-linecap="round" opacity=".8"/></svg>';
const FACE_ART={bau:GOURD,cua:'🦀',tom:'🦐',ca:'🐟',ga:'🐓',nai:'🦌'};
const art=f=>`<span class="fh-art" aria-hidden="true">${FACE_ART[f]||'❔'}</span>`;
const TITLE_NAMES={f_kinh2:'🎎 Kinh đôi rộn ràng',f_nguoc:'🙃 Đọc ngược như xuôi',f_hu:'🏺 Ôm hũ đêm hội',f_loto:'🎱 Thần lô tô hội chợ',f_bao:'🌪️ Trúng bão bầu cua',f_raid:'🚨 Bị công an hỏi thăm',f_oaq:'🪨 Cao tay ô ăn quan',f_ring:'💍 Tay ném vòng thần sầu',f_dart:'🎯 Mắt thần phi tiêu'};
const GAMES={home:['🏮','Cổng hội'],oaq:['🪨','Ô ăn quan'],ring:['💍','Ném vòng cổ chai'],bc:['🦀','Bầu cua'],lt:['🎱','Lô tô'],dt:['🎯','Phóng phi tiêu'],xd:['🕯️','Chiếu trong'],board:['🏆','Bảng vàng'],loan:['💸','Vay nóng']};
const MINI_BOARD='<svg viewBox="0 0 64 40" aria-hidden="true"><rect x="2" y="6" width="60" height="28" rx="14" fill="#e9c98f" stroke="#8a5a26" stroke-width="2"/><path d="M14 6v28M50 6v28M14 20h36M23 6v28M32 6v28M41 6v28" stroke="#8a5a26" stroke-width="1.6"/><circle cx="8" cy="20" r="4" fill="#5b4636"/><circle cx="56" cy="20" r="4" fill="#5b4636"/><g fill="#7a8b99"><circle cx="18" cy="13" r="1.8"/><circle cx="27" cy="27" r="1.8"/><circle cx="36" cy="13" r="1.8"/><circle cx="45" cy="27" r="1.8"/><circle cx="20" cy="28" r="1.8"/><circle cx="38" cy="25" r="1.8"/></g></svg>';
const MINI_BOTTLES='<svg viewBox="0 0 64 40" aria-hidden="true"><g stroke="#2d5a3d" stroke-width="1.4"><path d="M12 38V22c0-4 4-5 4-9V5h4v8c0 4 4 5 4 9v16z" fill="#7cc79a"/><path d="M28 38V22c0-4 4-5 4-9V5h4v8c0 4 4 5 4 9v16z" fill="#8fb6e8"/><path d="M44 38V22c0-4 4-5 4-9V5h4v8c0 4 4 5 4 9v16z" fill="#f0b46a"/></g><ellipse cx="34" cy="10" rx="7" ry="2.6" fill="none" stroke="#e2462d" stroke-width="2.4"/></svg>';
const CHIPS=[1,2,5,10];
const XD_STAKES=[10,20,30,50];
const NPC_GRACE=2000,ROLL_MS=450,ROUND_GAP=450;   // the bowl shakes this long; the server wants rounds ≥0.4 s apart (GAP_MS)
const LS='mnl.fair.lt';

/* ---- the people of the fair ---- */
const DEALER={name:'Chú Tám bầu cua',emoji:'🧔🏻',idle:['Bầu cua cá cọp đây, đặt đi bà con ơi!','Đặt lẹ đặt lẹ, chú lắc liền nè!','Ai chơi thì đặt, ai coi thì vỗ tay cho vui nha!','Con gì cũng có, ván nào cũng vui!']};
const HOST={name:'Anh Ba chiếu trong',emoji:'🕶️',idle:['Chơi lớn không? Chẵn lẻ, ăn một trả một.','Nói nhỏ thôi… ngó chừng phía ngoài giùm anh.','Xóc nè, xóc nè! Chẵn hay lẻ, đặt đi!']};
const RINGER={name:'Cô Tư ném vòng',emoji:'👩🏻',idle:['Ném vòng cổ chai đây! Không mất xu, trúng là có quà!','Canh cho kỹ, vòng ngay miệng chai thì ném!','Mỗi lượt năm cái vòng, ném trúng chai nào ăn chai đó!'],
  hit:['Trúng rồi! Tay ném chắc ghê!','Vô cổ chai luôn!','Đẹp! Thêm chai nữa nè!'],miss:['Hụt chút xíu!','Trật rồi, canh lại nha!','Ui, vòng nảy ra mất!']};
const OPP={de:{start:['Chơi với em nha! Anh chị đi trước đi.','Em mới tập chơi, nương tay giùm em nha!'],think:['Để em đếm coi…','Ô này nè… hông, ô kia!','Em rải bên này nha!'],
    cap:['Hihi, em ăn được rồi!','Ăn rồi nha!'],lose:['Ui da, mất quân rồi.','Ăn của em nhiều quá trời!'],won:['Em thắng rồi! Chơi ván nữa hông?'],lost:['Anh chị giỏi quá! Chơi lại ván nữa nha!'],draw:['Huề rồi! Ván sau phân thắng thua nha!']},
  kho:{start:['Ông chơi ô ăn quan từ hồi còn để chỏm. Mời cháu đi trước.','Bàn bày rồi, cháu đi trước đi.'],think:['Hừm… để ông tính.','Đi nước này coi sao.','Cháu coi kỹ nè.'],
    cap:['Quân này ông xin nha.','Ăn liên tiếp mới vui!'],lose:['Nước này cháu tính hay đó.','Khá lắm, khá lắm.'],won:['Ván này ông thắng, cháu tập thêm rồi ghé nha.'],lost:['Cháu cao tay thiệt! Ông chịu thua ván này.'],draw:['Huề! Ông cháu mình ngang tay.']}};

/* ---- state ---- */
const S={dlg:null,env:null,tab:'home',busy:false,lastRound:0,gift:null,loan:{amt:100,sure:false},flash:null,skew:0,listening:false,tick:null,
  oaq:{sel:null,anim:null,say:'',fast:false,quit:false,end:null,showEnd:false},
  ring:{round:null,t0:0,taps:[],hits:[],raf:0,result:null,say:''},
  bc:{chip:1,bets:{},phase:'idle',dice:null,last:null,say:''},
  xd:{side:'chan',stake:10,phase:'idle',coins:null,last:null,raid:null,say:'',hist:[],tally:{w:0,l:0,raid:0}},
  lt:{id:null,shown:0,marks:[],timer:null,speed:1,over:null,won:null,hut:null,claiming:false,check:false,hot:false,say:'',
    act:0,actAt:0,actSay:'',tier:'vua',n:1,cl:null,cls:2,cot:null,cots:2},
  board:{data:null,at:0,loading:false,error:''}};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const F=()=>S.env?.api?.state?.fair||{};
const R=()=>F().rules||{};
const serverNow=()=>Date.now()+S.skew;
const pick=a=>a[Math.floor(Math.random()*a.length)];
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-fh="${op}"${attrs(data)}${extra}>${label}</button>`;
const reduce=()=>document.documentElement.classList.contains('reduce-motion')||matchMedia('(prefers-reduced-motion: reduce)').matches;

function left(ms){
  const m=Math.max(0,Math.floor(ms/60000)),d=Math.floor(m/1440),h=Math.floor(m%1440/60),mm=m%60;
  return d?`${d} ngày ${h} giờ`:h?`${h} giờ ${mm} phút`:`${Math.max(1,mm)} phút`;
}
const clock=s=>{s=Math.max(0,Math.ceil(s));return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;};
const dateOf=t=>new Date(t*1000).toLocaleDateString('vi-VN',{day:'2-digit',month:'2-digit',timeZone:'Asia/Ho_Chi_Minh'});

/* ---- sounds (Web Audio, synthesised; silent when the game's sound is off) ---- */
function sfx(kind){
  const st=S.env?.api?.state?.settings||{};if(st.sound===false)return;
  const c=audioContext();if(!c||c.state!=='running')return;
  const vol=Math.max(0,Math.min(1.5,(st.sfxVolume??70)/70)),t0=c.currentTime;
  const tone=(f,d,v,at=0,type='sine',to=null)=>{const o=c.createOscillator(),g=c.createGain();o.type=type;o.frequency.setValueAtTime(f,t0+at);if(to)o.frequency.exponentialRampToValueAtTime(to,t0+at+d);
    g.gain.setValueAtTime(.0001,t0+at);g.gain.exponentialRampToValueAtTime(v*vol+.0001,t0+at+.012);g.gain.exponentialRampToValueAtTime(.0001,t0+at+d);o.connect(g);g.connect(c.destination);o.start(t0+at);o.stop(t0+at+d+.05);};
  const rattle=(at,len)=>{const n=Math.floor(c.sampleRate*.03),b=c.createBuffer(1,n,c.sampleRate),d=b.getChannelData(0);for(let i=0;i<n;i++)d[i]=(Math.random()*2-1)*(1-i/n);
    for(let k=0;k<len;k++){const s=c.createBufferSource(),f=c.createBiquadFilter(),g=c.createGain();s.buffer=b;f.type='bandpass';f.frequency.value=2200+Math.random()*1800;g.gain.value=.05*vol;s.connect(f);f.connect(g);g.connect(c.destination);s.start(t0+at+k*.07+Math.random()*.03);}};
  switch(kind){
    case'shake':rattle(0,16);break;
    case'open':tone(880,.18,.03);tone(1320,.25,.025,.06);break;
    case'win':[784,988,1175,1568].forEach((f,i)=>tone(f,.28,.035,i*.09,'triangle'));break;
    case'lose':tone(220,.3,.04,0,'sine',150);break;
    case'call':tone(660,.12,.025);tone(990,.16,.02,.08);break;
    case'mark':tone(520,.06,.03,0,'square',300);break;
    case'kinh':[523,659,784,1047,1319].forEach((f,i)=>tone(f,.35,.04,i*.08,'triangle'));break;
    case'siren':for(let i=0;i<4;i++){tone(740,.28,.04,i*.5,'sawtooth',740);tone(988,.28,.04,i*.5+.25,'sawtooth',988);}break;
    case'stone':tone(1100+Math.random()*300,.05,.018,0,'triangle');break;
    case'cap':[660,880,1175].forEach((f,i)=>tone(f,.18,.03,i*.06,'triangle'));break;
    case'throw':tone(320,.2,.02,0,'sine',900);break;
    case'clink':tone(2350,.3,.03);tone(3150,.22,.02,.035);break;
    case'miss':tone(190,.14,.04,0,'sine',120);break;
  }
}

/* ---- styles on first use ---- */
let cssReady=null;
const ensureCss=()=>cssReady??=new Promise(done=>{
  if(document.querySelector('link[data-fh-css]')){done();return;}
  const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.('/css/fair.css')||'/css/fair.css';l.setAttribute('data-fh-css','');
  l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
});

/* ---- the dialog ---- */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium fh-sheet';d.setAttribute('aria-labelledby','fh-title');
  d.innerHTML='<div class="fh-root"></div><div class="fh-reactlayer" aria-hidden="true"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-fh]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();S.anchor=el.dataset.fhKey||'';S.anchorAt=performance.now();onClick(el.dataset.fh,el.dataset,el);
  });
  d.addEventListener('close',()=>{pauseLoto();ltMusic();stopRing();clearInterval(S.tick);S.tick=null;S.flash=null;});
  S.dlg=d;return d;
}
export async function openFair(env,data={}){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';
    env.api.addEventListener('state',()=>{const f=F();if(typeof f.now==='number')S.skew=f.now*1000-Date.now();
      const key=JSON.stringify([f.wallet,f.today,f.earn,f.raid_left>0,f.loto?.id,f.loto?.stage,f.oaq?.stage,f.oaq?.ply,f.ring?.id,f.points?.total,f.open]);if(key===seen)return;seen=key;
      if(S.dlg?.open&&!animating())render();});
  }
  const f=F();if(typeof f.now==='number')S.skew=f.now*1000-Date.now();
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(data?.tab)S.tab=data.tab;
  else if(!f.open)S.tab='home';
  else if(!(S.tab==='lt'&&f.loto?.stage==='play')&&!(S.tab==='oaq'&&f.oaq?.stage==='play'))S.tab='home';   // back at the gate unless a game is going on
  if(!S.bc.say)S.bc.say=pick(DEALER.idle);
  if(!S.xd.say)S.xd.say=pick(HOST.idle);
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  claimGift();
  clearInterval(S.tick);S.tick=setInterval(tickLabels,1000);
  if(S.tab==='board')loadBoard();
  if(S.tab==='lt')resumeLoto();
  if(S.tab==='ring')startRingLoop();
  if(S.tab==='dt')dt().start();
}
export async function fairAction(action,data,el,env){
  if(action!=='fair')return false;
  await openFair(env,data);return true;
}
const animating=()=>!!S.dt?.flying||S.bc.phase!=='idle'||S.xd.phase!=='idle'||S.busy||!!S.oaq.anim||S.ring.taps.length>0&&!S.ring.result;

async function send(action,payload={}){
  const {api}=S.env;
  try{return await api.command(action,payload);}
  catch(e){S.err=e.code||e.data?.code||'';S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
}

/* ---- rendering ----
 * Every render patches the page in place (morph): only the nodes that changed are touched, so the dialog never
 * loses its height, the tapped button and the focus stay, open <details> stay open and running CSS animations
 * do not restart. The control the player just tapped is then held at the same spot on screen (content above it
 * may grow or shrink: a result line, a flash); the dialog's scroll is written only when it really has to move,
 * so a call tick of the lô tô never fights a finger that is scrolling. */
const keyOf=n=>n.nodeType!==1?'':(n.getAttribute('data-fh-key')||'')+'|'+(n.getAttribute('data-fh')||'')+(n.nodeName==='SECTION'||n.nodeName==='DETAILS'?'|'+n.className:'');
const same=(a,b)=>a.nodeType===b.nodeType&&a.nodeName===b.nodeName&&keyOf(a)===keyOf(b);
function morph(from,to){
  if(from.nodeType!==1){if(from.nodeValue!==to.nodeValue)from.nodeValue=to.nodeValue;return;}
  const det=from.nodeName==='DETAILS';   // a <details> the player opened or closed keeps that
  for(const {name} of [...from.attributes])if(!to.hasAttribute(name)&&!(det&&name==='open'))from.removeAttribute(name);
  for(const {name,value} of [...to.attributes])if(from.getAttribute(name)!==value&&!(det&&name==='open'))from.setAttribute(name,value);
  if(from.hasAttribute('data-fh-live'))return;   // drawn by script (the flying rings, the swinging aim): left alone
  const a=[...from.childNodes],b=[...to.childNodes];
  let i=0,j=0;
  for(;j<b.length;j++){
    const n=b[j],o=a[i];
    if(!o){from.append(n);continue;}
    if(same(o,n)){morph(o,n);i++;continue;}
    if(a[i+1]&&same(a[i+1],n)){o.remove();morph(a[i+1],n);i+=2;continue;}   // a node went away
    if(b[j+1]&&same(o,b[j+1])){from.insertBefore(n,o);continue;}   // a node came in
    from.replaceChild(n,o);i++;
  }
  for(;i<a.length;i++)a[i].remove();
}
const tplEl=document.createElement('template');
const byKey=k=>k?S.dlg.querySelector(`[data-fh-key="${CSS.escape(k)}"]`):null;
/** What to hold still: the control just tapped (for a moment after the tap), else the first keyed control on screen. */
function anchorEl(d){
  if(S.anchor&&performance.now()-S.anchorAt<700){const el=byKey(S.anchor);if(el)return el;}
  if(d.scrollTop<1)return null;
  const top=d.getBoundingClientRect().top;
  for(const el of d.querySelectorAll('[data-fh-key]'))if(el.getBoundingClientRect().top>=top)return el;
  return null;
}
function keep(fn){
  const d=S.dlg,an=anchorEl(d),ak=an?.dataset.fhKey,y0=an?an.getBoundingClientRect().top:0;
  const top=d.scrollTop,a=document.activeElement,key=a&&d.contains(a)?a.dataset.fhKey:'';
  fn();
  const an2=byKey(ak);
  if(an2){const dy=an2.getBoundingClientRect().top-y0;if(Math.abs(dy)>1)d.scrollTop+=dy;}   // held at the same spot on screen
  else if(Math.abs(d.scrollTop-top)>1)d.scrollTop=top;
  if(key&&!a.isConnected)byKey(key)?.focus({preventScroll:true});
}
function render(){
  if(!S.dlg)return;
  keep(()=>{const root=S.dlg.querySelector('.fh-root');tplEl.innerHTML=page();
    const box=document.createElement('div');box.append(tplEl.content);morph(root,Object.assign(box,{className:root.className}));});
  if(S.dlg.getAttribute('aria-busy')!==String(S.busy))S.dlg.setAttribute('aria-busy',String(S.busy));
}
function tickLabels(){
  if(!S.dlg?.open)return;
  const f=F();
  if(!f.open&&f.soon&&f.opens*1000<=serverNow()&&!S.opening){S.opening=1;S.env.api.refresh().catch(()=>{/* next tick */}).finally(()=>{setTimeout(()=>{S.opening=0;},5000);render();});}   // the countdown hit 0: fetch the open fair
  if(S.tab==='lt')nextAct();
  S.dlg.querySelectorAll('[data-fh-count]').forEach(el=>{
    const k=el.dataset.fhCount;
    if(k==='close')el.textContent=f.open?`còn ${left(f.closes*1000-serverNow())}`:f.soon?`mở sau ${left(f.opens*1000-serverNow())}`:'đã tàn';
    if(k==='raid'){const s=raidLeft();el.textContent=clock(s);if(s<=0&&S.xd.phase==='idle')render();}
  });
}
const raidLeft=()=>{const f=F();return f.raid_left>0?f.raid_left-(serverNow()/1000-f.now):0;};

function head(){
  const f=F();
  const when=f.open?`còn ${left(f.closes*1000-serverNow())}`:f.soon?`mở sau ${left(f.opens*1000-serverNow())}`:'đã tàn';
  return `<header class="fh-head">
    <div class="fh-bunting" aria-hidden="true"></div>
    <div class="fh-lanterns" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
    <div class="fh-headrow"><span class="fh-logo" aria-hidden="true">🏮</span>
      <div class="grow"><span class="eyebrow">KHU PHỐ MỞ HỘI · <span data-fh-count="close">${esc(when)}</span></span><h2 id="fh-title">Hội chợ dân gian</h2></div>
      <button class="icon-btn fh-x" type="button" data-fh="close" aria-label="Đóng">${icon('x',21)}</button></div>
  </header>`;
}
function strip(){
  const f=F(),p=f.points||{},e=f.earn||{},got=(e.oaq?.today||0)+(e.ring?.today||0);
  return `<div class="fh-strip" role="status"><span>👛 <b>${xu((f.wallet||0)-ltHold())}</b></span><span>💰 Hôm nay kiếm <b>${xu(got)}</b></span><button type="button" class="fh-pts" data-fh="tab" data-tab="board" data-fh-key="pts">🏆 <b>${fmt(p.total)}</b> điểm</button></div>`;
}
/** Inside a stall: the way back to the gate. */
function nav(){
  if(S.tab==='home')return '';
  const [e,l]=GAMES[S.tab]||GAMES.home;
  return `<nav class="fh-nav" aria-label="Hội chợ">${btn('<span aria-hidden="true">‹</span> Cổng hội','tab',{tab:'home'},'ghost small fh-back',' data-fh-key="home"')}<b><span aria-hidden="true">${e}</span> ${esc(l)}</b></nav>`;
}
/** The small-stake stalls: what is left of today's loss cap. */
const luckLine=()=>{const t=F().today||{};if(R().nocap)return '';return `<p class="fh-luck-left">🎟️ Thử vận hôm nay còn chơi được <b>${xu(t.left)}</b> <small>(thua tối đa ${xu(R().cap)} mỗi ngày)</small></p>`;};
const flash=()=>`<p class="fh-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
const note=()=>`<p class="fh-note">🎪 Trò chơi dân gian ở hội chợ, chơi bằng xu trong game. Không có tiền thật.</p>`;
function page(){
  const f=F();
  if(!f.show&&!f.over&&!f.soon)return head()+`<div class="sheet-body fh-body">${closedCard(true)}</div>`;
  if(!f.open&&S.tab!=='board')return head()+`<div class="sheet-body fh-body">${closedCard()}${S.env?.api?.state?.journey?.story?btn('🏆 Xem Bảng vàng hội chợ','tab',{tab:'board'},'cream full'):''}${note()}</div>`;
  const views={home:homeView,oaq:oaqView,ring:ringView,bc:bcView,lt:lotoView,xd:xdView,board:boardView,loan:loanView,dt:()=>F().darts?dt().view():homeView()};
  const body=(views[S.tab]||homeView)(),luck=['bc','xd'].includes(S.tab)||S.tab==='lt'&&!G();   // the newer lô tô: only the wallet limits it
  return head()+giftPop()+`<div class="sheet-body fh-body">${f.open?strip():''}${f.open?nav():''}${flash()}${f.open&&luck&&f.today?.done?enoughCard():''}${f.open&&luck&&!f.today?.done?luckLine():''}${body}${note()}</div>`;
}
function closedCard(gone){
  const f=F();
  if(f.soon)return `<section class="fh-card fh-closed"><div class="fh-big" aria-hidden="true">🏮</div><h3>Hội chợ sắp mở</h3><p>Khai hội ngày ${esc(dateOf(f.opens))}, mở ${Math.round((f.closes-f.opens)/86400)} ngày. Hẹn bà con ghé chơi ô ăn quan, ném vòng, bầu cua, lô tô nha!</p></section>`;
  return `<section class="fh-card fh-closed"><div class="fh-big" aria-hidden="true">🎐</div><h3>Hội chợ đã tàn, hẹn lần sau</h3><p>${gone?'Lều bạt đã dọn, đèn lồng đã cất.':'Cảm ơn bà con đã ghé hội. Bảng vàng vẫn còn đó để xem lại.'}</p></section>`;
}
const enoughCard=()=>`<section class="fh-card fh-enough"><span aria-hidden="true">🍵</span><div><b>Hôm nay chơi vậy đủ rồi, mai ghé tiếp nha.</b><small>Mỗi ngày thua tối đa ${xu(R().cap)}. Qua chơi ô ăn quan, ném vòng kiếm xu, hoặc ghé xem Bảng vàng nhé.</small></div></section>`;
const say=(who,text,cls='')=>`<div class="fh-npcline ${cls}"><span class="fh-npc" aria-hidden="true">${who.emoji}</span><div class="fh-bubble"><small>${esc(who.name)}</small><p>${esc(text)}</p></div></div>`;

/* ---- 🏮 Cổng hội: the earn-xu stalls first, then the small-stake ones ---- */
const meter=(e,label='Hôm nay đã kiếm')=>{if(e?.nocap)return '';e=e||{today:0,cap:1};const pct=Math.min(100,Math.round(e.today/Math.max(1,e.cap)*100));
  return `<span class="fh-meter${e.today>=e.cap?' full':''}" aria-hidden="true"><i style="width:${pct}%"></i></span><small class="fh-meterlabel">${e.today>=e.cap?'Hôm nay đã kiếm đủ':label} <b>${fmt(e.today)}</b>/${xu(e.cap)}</small>`;};
function homeView(){
  const f=F(),r=R(),e=f.earn||{},o=f.oaq,p=f.points||{},pr=r.oaq_prize||{de:15,kho:30};
  const oaqLine=o?.stage==='play'?`<em class="fh-live">Đang chơi dở với ${esc(o.name)} · chơi tiếp</em>`:`Đấu với Bé Bi (thắng +${pr.de} xu) hoặc Ông Hai (thắng +${pr.kho} xu)`;
  const luck=(id,ico,name,sub,warn='')=>`<button type="button" class="fh-luckgame" data-fh="tab" data-tab="${id}" data-fh-key="g-${id}"><span class="fh-lico" aria-hidden="true">${ico}</span><span class="grow"><b>${name}</b><small>${sub}</small></span>${warn}${f.loto?.stage==='play'&&id==='lt'?'<i class="fh-dot" aria-label="đang chơi"></i>':''}</button>`;
  return `<section class="fh-gate" aria-label="Cổng hội">
    <div class="fh-sec"><h3>💰 Chơi kiếm xu</h3><span class="fh-tag good">Không cần đặt cược</span></div>
    <div class="fh-earn">
      <button type="button" class="fh-game" data-fh="tab" data-tab="oaq" data-fh-key="g-oaq"><span class="fh-gico">${MINI_BOARD}</span><span class="grow"><b>Ô ăn quan</b><small>${oaqLine}</small>${meter(e.oaq)}</span></button>
      <button type="button" class="fh-game" data-fh="tab" data-tab="ring" data-fh-key="g-ring"><span class="fh-gico">${MINI_BOTTLES}</span><span class="grow"><b>Ném vòng cổ chai</b><small>${r.nocap?`Mỗi vòng trúng +${r.ring_hit} xu, trúng cả ${r.rings||5} vòng thêm ${r.ring_all} xu`:`Trúng mỗi chai +${r.ring_hit||2} xu, đủ ${r.rings||5} chai thêm ${r.ring_all||5} xu`}</small>${meter(e.ring)}</span></button>
    </div>
    <div class="fh-sec"><h3>🎲 Thử vận may</h3><span class="fh-tag">Cược nhỏ bằng xu</span></div>
    <div class="fh-luck">
      ${luck('bc',FACE_ART.cua,'Bầu cua',`Đặt 1–${r.bc_max||20} xu một ván`)}
      ${f.darts?luck('dt','🎯','Phóng phi tiêu',`Đặt ${Math.min(...f.darts.stakes)}–${Math.max(...f.darts.stakes)} xu, cắm vòng màu ăn 1 trả 1`):''}
      ${luck('lt','🎱','Gánh lô tô',f.ganh?`Cô Bảy hô số, vé từ ${xu(Math.min(...Object.values(f.ganh.tiers)))} · ${esc(f.ganh.names?.[f.ganh.modes?.[0]?.[1]]||'')}`:`Tờ dò ${xu(r.loto_price)}, kinh ăn ${xu(r.loto_prize)}`)}
      ${luck('xd','🕯️','Chiếu trong',`Cược ${r.xd_min}–${r.xd_max} xu`,'<span class="fh-warnchip">🚨 công an</span>')}
    </div>
    ${loanRow()}
    <button type="button" class="fh-goldlink" data-fh="tab" data-tab="board" data-fh-key="g-board"><span aria-hidden="true">🏆</span><span class="grow"><b>Bảng vàng hội chợ</b><small>Bạn ${fmt(p.total)} điểm · Top 1 khi hội tàn thành 👑 Vua trò chơi</small></span><span aria-hidden="true">›</span></button>
  </section>`;
}

/* ---- 🪨 Ô ăn quan ---- */
const ROW_ME=[1,2,3,4,5],ROW_OPP=[11,10,9,8,7];
function oaqBoard(){
  const o=F().oaq,a=S.oaq.anim,v=a||o,mine=!a&&o?.stage==='play';
  const pebbles=(n,quan)=>{const k=Math.min(n,12);let h=quan?'<i class="fh-quan" aria-hidden="true"></i>':'';for(let i=0;i<k;i++)h+=`<i class="fh-peb" style="--r:${(i*47)%360}deg" aria-hidden="true"></i>`;return h;};
  const cell=(c)=>{const n=v.b[c],quan=c===0||c===6,hasQ=quan&&v.q[c===0?0:1],cls=['fh-o',quan?'quan '+(c===0?'left':'right'):'',a?.at===c?'at':'',a?.flash===c?'flash':'',S.oaq.sel===c?'sel':'',a?.hl===c?'hl':''].join(' ');
    const label=`${quan?'Ô quan':'Ô'}${hasQ?' còn quan':''}, ${n} dân`;
    const inner=`<span class="fh-pebs">${pebbles(n,hasQ)}</span>${n?`<em class="fh-n">${n}</em>`:''}`;
    if(mine&&ROW_ME.includes(c)&&n>0)return `<button type="button" class="${cls} pick" data-fh="oaqsel" data-c="${c}" data-fh-key="o-${c}" aria-pressed="${S.oaq.sel===c}" aria-label="${label}">${inner}</button>`;
    return `<div class="${cls}" role="img" aria-label="${label}">${inner}</div>`;};
  return `<div class="fh-oaq" aria-label="Bàn ô ăn quan">${cell(0)}<div class="fh-orow opp">${ROW_OPP.map(cell).join('')}</div><div class="fh-orow me">${ROW_ME.map(cell).join('')}</div>${cell(6)}</div>`;
}
function oaqView(){
  const f=F(),r=R(),o=f.oaq,e=(f.earn||{}).oaq,pr=r.oaq_prize||{de:15,kho:30},people=r.oaq_people||{de:['Bé Bi','👦'],kho:['Ông Hai','👴']};
  const how=`<details class="fh-how"${o?'':' open'}><summary>Cách chơi</summary><ul>
      <li>Mỗi bên 5 ô dân, mỗi ô 5 quân. Hai đầu là ô quan: mỗi quan ${r.quan||10} điểm, mỗi dân 1 điểm.</li>
      <li>Tới lượt: chọn một ô bên mình còn quân, chọn hướng, bốc hết rải mỗi ô một quân (rải qua cả ô quan).</li>
      <li>Rải xong mà ô kế tiếp còn quân thì bốc ô đó rải tiếp. Kế tiếp là ô quan thì hết lượt.</li>
      <li>Kế tiếp là một ô trống rồi tới ô có quân: ăn hết ô đó. Lại một ô trống rồi ô có quân thì ăn tiếp. Hai ô trống liền nhau: hết lượt.</li>
      <li>Quan non: ô quan còn quan mà chưa đủ ${r.quan_non||5} dân thì chưa ăn được.</li>
      <li>Hàng mình hết quân thì lấy 5 dân đã ăn rải lại mỗi ô một quân; không đủ thì ván kết thúc.</li>
      <li>Hết cả hai ô quan: mỗi bên thu dân còn trên hàng mình. Nhiều điểm hơn thì thắng.</li></ul></details>`;
  if(!o||(o.stage!=='play'&&!S.oaq.showEnd)){
    const opp=lv=>`<button type="button" class="fh-opp fh-opp-${lv}" data-fh="oaqstart" data-lv="${lv}" data-fh-key="opp-${lv}"${S.busy?' disabled':''}><span class="fh-npc" aria-hidden="true">${people[lv][1]}</span><b>${esc(people[lv][0])}</b><small>${S.busy&&S.oaq.starting===lv?'Đang bày bàn…':`${lv==='de'?'Dễ':'Khó'} · thắng <b>+${xu(pr[lv])}</b>`}</small></button>`;
    return `<section class="fh-stall fh-oaqstall" aria-label="Ô ăn quan">
      <div class="fh-card fh-oaqintro"><h3>🪨 Ô ăn quan</h3><p>Chọn người chơi cùng. Thắng thì được xu, thua không mất gì.</p><div class="fh-opps">${opp('de')}${opp('kho')}</div>${meter(e)}</div>
      ${how}<p class="fh-rule">Thắng một ván: +${(F().points?.rules||{}).oaq||3} điểm Bảng vàng.${e?.nocap?' Thắng bao nhiêu ván cũng được xu, không giới hạn.':` Mỗi ngày kiếm từ ô ăn quan tối đa ${xu(e?.cap||90)}.`}</p></section>`;
  }
  const a=S.oaq.anim,v=a||o,lines=OPP[o.lv]||OPP.de,who={name:o.name,emoji:o.emoji};
  if(!S.oaq.say)S.oaq.say=pick(lines.start);
  const me=a?a.cap[0]+10*a.cap[1]:o.me,opp=a?a.cap[2]+10*a.cap[3]:o.opp,cap=v.cap;
  const turn=a?(a.side===1?`${esc(o.name)} đang rải…`:'Bạn đang rải…'):o.stage==='play'?(S.oaq.sel!=null?'Chọn hướng rải (bấm ô khác để đổi, bấm lại để bỏ chọn)':'Lượt của bạn: chạm một ô hàng dưới'):'';
  const hand=a&&a.hand>0?`<span class="fh-hand">✋ ${a.hand}</span>`:'';
  const dirs=S.oaq.sel!=null&&!a&&o.stage==='play'?`<div class="fh-dirs">${btn('◀ Rải sang trái','oaqmove',{d:-1},'primary',' data-fh-key="d-l"')}${btn('Rải sang phải ▶','oaqmove',{d:1},'primary',' data-fh-key="d-r"')}</div>`:'';
  const end=S.oaq.end&&o.stage!=='play'&&!a?oaqEnd(o):'';
  return `<section class="fh-stall fh-oaqstall" aria-label="Ô ăn quan">
    ${say(who,S.oaq.say)}
    <div class="fh-oscore"><span class="opp"><em>${esc(o.emoji)} ${esc(o.name)}</em><b>${opp}</b><small>${cap[2]} dân${cap[3]?` · ${cap[3]} quan`:''}</small></span><span class="me"><em>🙂 Bạn</em><b>${me}</b><small>${cap[0]} dân${cap[1]?` · ${cap[1]} quan`:''}</small></span></div>
    ${oaqBoard()}
    ${dirs}<div class="fh-oturn" aria-live="polite"><span>${turn}</span>${hand}</div>
    ${end}
    <div class="fh-go">${btn(S.oaq.fast?'⏯️ Rải chậm':'⏩ Rải nhanh','oaqfast',{},'ghost small',' data-fh-key="oaqfast"')}${o.stage==='play'?btn(S.oaq.quit?'Chắc chưa? Bỏ ván':'Bỏ ván','oaqquit',{},'ghost small'+(S.oaq.quit?' danger':''),a?' disabled':' data-fh-key="oaqquit"'):''}</div>
    ${how}</section>`;
}
function oaqEnd(o){
  const x=S.oaq.end,people=R().oaq_people||{};
  const head=x.stage==='won'?`🎉 Bạn thắng ${x.me}–${x.opp}!`:x.stage==='draw'?`🤝 Huề ${x.me}–${x.opp}`:`Thua ${x.me}–${x.opp}, ván sau gỡ nha`;
  const pay=x.stage==='won'?(x.prize?`<p class="fh-prize">+${xu(x.prize)}${x.points?` · +${x.points} điểm hội chợ`:''}</p>`:`<p class="muted small">Hôm nay đã kiếm đủ xu từ ô ăn quan${x.points?`, vẫn được +${x.points} điểm hội chợ`:''}. Mai ghé tiếp nha!</p>`):'<p class="muted small">Thua không mất xu nào.</p>';
  const other=o.lv==='de'?'kho':'de';
  return `<div class="fh-card fh-oend ${x.stage}"><h3>${head}</h3>${pay}${x.titles?.includes('f_oaq')?'<p class="fh-award">🪨 Danh hiệu mới: <b>Cao tay ô ăn quan</b></p>':''}
    <div class="row wrap fh-oend-go">${btn(`Ván mới với ${esc(o.name)}`,'oaqstart',{lv:o.lv},'primary',S.busy?' disabled data-fh-key="again"':' data-fh-key="again"')}${btn(`Chơi với ${esc((people[other]||[''])[0])}`,'oaqstart',{lv:other},'ghost',S.busy?' disabled data-fh-key="other"':' data-fh-key="other"')}</div></div>`;
}
const wait=ms=>new Promise(ok=>setTimeout(ok,reduce()?Math.min(ms,60):ms));
async function oaqStart(lv){
  if(S.busy)return;S.busy=true;S.oaq.starting=lv;S.flash=null;render();
  const r=await send('fair_oaq_start',{lv});S.busy=false;S.oaq.starting=null;
  if(r?.fair){S.oaq={...S.oaq,sel:null,anim:null,end:null,showEnd:true,quit:false,say:pick((OPP[lv]||OPP.de).start)};}
  render();
}
async function oaqMove(dir){
  const o=F().oaq,cell=S.oaq.sel;if(!o||o.stage!=='play'||cell==null||S.busy||S.oaq.anim)return;
  S.oaq.sel=null;S.oaq.quit=false;S.busy=true;S.flash=null;
  S.oaq.anim={b:[...o.b],q:[...o.q],cap:[...o.cap],hand:0,at:null,hl:cell,flash:null,side:0};render();
  const r=await send('fair_oaq_move',{cell,dir,...(R().oaq_turn&&Number.isInteger(o.ply)?{ply:o.ply}:{})});   // the newer server refuses a move for a board that moved on
  if(!r?.fair){S.oaq.anim=null;S.busy=false;if(S.err==='fair_oaq_turn')await S.env.api.refresh().catch(()=>{/* the next state */});render();return;}
  await playTrace(r.fair.trace||[],o.lv);
  S.oaq.anim=null;S.busy=false;
  const x=r.fair.end;
  if(x){S.oaq.end={...x,titles:r.fair.titles||[]};S.oaq.showEnd=true;S.oaq.say=pick((OPP[o.lv]||OPP.de)[x.stage==='won'?'lost':x.stage==='lost'?'won':'draw']);
    sfx(x.stage==='won'?'kinh':x.stage==='lost'?'lose':'open');}
  render();
}
async function playTrace(trace,lv){
  const a=S.oaq.anim,lines=OPP[lv]||OPP.de,step=()=>S.oaq.fast?50:115;
  for(const ev of trace){
    if(!S.oaq.anim)return;
    const [k]=ev;
    if(k==='turn'){a.side=ev[1];a.hl=ev[2];a.at=null;a.flash=null;if(ev[1]===1){S.oaq.say=pick(lines.think);render();await wait(S.oaq.fast?250:480);}continue;}
    if(k==='pick'){a.b[ev[1]]=0;a.hand=ev[2];a.at=ev[1];a.hl=null;sfx('stone');render();await wait(step()+40);continue;}
    if(k==='drop'){a.b[ev[1]]++;a.hand=Math.max(0,a.hand-1);a.at=ev[1];sfx('stone');render();await wait(step());continue;}
    if(k==='cap'){const [,c,dan,quan]=ev;a.b[c]=0;if(quan)a.q[c===0?0:1]=0;a.cap[2*a.side]+=dan;a.cap[2*a.side+1]+=quan;a.flash=c;a.at=null;
      S.oaq.say=pick(a.side===1?lines.cap:lines.lose);sfx('cap');render();await wait(S.oaq.fast?220:420);continue;}
    if(k==='non'){a.flash=ev[1];S.flash={text:'Quan non: ô quan chưa đủ dân, chưa ăn được.',kind:'warn'};render();await wait(S.oaq.fast?260:520);S.flash=null;continue;}
    if(k==='seed'){const row=ev[1]===0?ROW_ME:ROW_OPP;row.forEach(c=>{a.b[c]=1;});a.cap[2*ev[1]]-=5;S.flash={text:ev[1]===0?'Hàng bạn hết quân: rải lại 5 dân đã ăn.':'Hàng bên kia hết quân: rải lại 5 dân.',kind:'warn'};render();await wait(S.oaq.fast?260:600);S.flash=null;continue;}
    if(k==='collect'){S.flash={text:'Hết quan, tàn dân: thu quân về đếm điểm!',kind:'good'};render();await wait(S.oaq.fast?260:520);S.flash=null;continue;}
  }
  a.at=null;a.hl=null;
}

/* ---- 💍 Ném vòng cổ chai ---- */
/** Where the ring is at `t` ms (0..100): the same arithmetic as x_at in game/fair_ring.py. */
const ringX=(p,t)=>{const u=((t/p.period)+p.phase)%1;return 100*(1-Math.abs(2*u-1));};
const trackPos=x=>`calc(6% + ${x*0.88}%)`;
/** Same as judge in game/fair_ring.py: the newer server lets one bottle take several rings (rules.nocap). */
function ringJudge(p,taps){const rung=new Set(),many=!!R().nocap;return taps.map(t=>{const x=ringX(p,t);const i=p.xs.findIndex((bx,k)=>(many||!rung.has(k))&&Math.abs(x-bx)<=R().ring_tol);if(i>=0)rung.add(i);return i;});}
function ringView(){
  const f=F(),r=R(),e=(f.earn||{}).ring,R0=S.ring,rd=R0.round,res=R0.result;
  if(!R0.say)R0.say=pick(RINGER.idle);
  const hits=res?res.hits:R0.hits,rings=r.rings||5,used=res?rings:R0.taps.length;
  const xs=rd?.xs||[10,30,50,70,90],colors=['#6cc08b','#7fb0ea','#f0b064','#d98ad6','#e7d36a'];
  const bottles=xs.map((x,i)=>`<span class="fh-bottle${hits.includes(i)?' ringed':''}" data-x="${x}" style="left:${trackPos(x)};--c:${colors[i]}" aria-label="Chai ${i+1}${hits.includes(i)?', đã trúng':''}" role="img"><i></i></span>`).join('');
  const left=Array.from({length:rings},(_,i)=>`<i class="${i<used?'used':''}"></i>`).join('');
  let go;
  if(res){const n=res.n;go=`<div class="fh-card fh-ringres ${n>=3?'good':''}"><h3>${n===rings?'🎉 Trúng cả '+n+' chai!':`Trúng ${n}/${rings} chai`}</h3>${res.prize?`<p class="fh-prize">+${xu(res.prize)}${res.points?` · +${res.points} điểm hội chợ`:''}</p>`:n&&res.capped?'<p class="muted small">Hôm nay đã kiếm đủ xu từ ném vòng, mai ghé tiếp nha!</p>':'<p class="muted small">Lượt sau canh kỹ hơn nha!</p>'}${res.titles?.includes('f_ring')?'<p class="fh-award">💍 Danh hiệu mới: <b>Tay ném vòng thần sầu</b></p>':''}</div>`+
    btn('🎯 Ném lượt nữa (miễn phí)','ringstart',{},'primary big full',S.busy||!r.ring_left?' disabled':' data-fh-key="ringstart"');}
  else if(rd)go=btn(R0.taps.length>=rings?'Đang đếm…':'🫳 Ném!','throw',{},'primary big full fh-throw',R0.taps.length>=rings?' disabled':' data-fh-key="throw"');
  else go=btn(S.busy?'Cô Tư đang phát vòng…':`🎯 Phát ${rings} vòng (miễn phí)`,'ringstart',{},'primary big full',S.busy||!r.ring_left?' disabled':' data-fh-key="ringstart"');
  return `<section class="fh-stall fh-ringstall" aria-label="Ném vòng cổ chai">
    ${say(RINGER,R0.say)}
    <div class="fh-ringstage${rd&&!res?' live':''}"><div class="fh-track" aria-hidden="true" data-fh-live><span class="fh-aim" style="left:${trackPos(rd?ringX(rd,0):50)}"><i></i></span></div><div class="fh-fly-layer" aria-hidden="true" data-fh-live></div><div class="fh-shelf">${bottles}</div></div>
    <div class="fh-ringsleft" aria-label="Còn ${rings-used} vòng">${left}</div>
    ${go}
    <div class="fh-ringmeter">${meter(e)}</div>
    <p class="fh-rule">${r.nocap?`Bấm “Ném!” khi vòng ở ngay trên miệng chai. Một chai ăn được nhiều vòng. Mỗi vòng trúng ${r.ring_hit} xu, trúng cả ${rings} vòng thêm ${r.ring_all} xu. Trúng từ 3 vòng: +${(F().points?.rules||{}).ring3||1} điểm, cả ${rings} vòng: +${(F().points?.rules||{}).ring5||2} điểm.`:`Bấm “Ném!” khi vòng ở ngay trên miệng chai. Mỗi chai chỉ tính một lần. Trúng ${r.ring_hit||2} xu một chai, đủ ${rings} chai thêm ${r.ring_all||5} xu. Từ 3 chai: +${(F().points?.rules||{}).ring3||1} điểm, đủ ${rings} chai: +${(F().points?.rules||{}).ring5||2} điểm.`}</p>
  </section>`;
}
function stopRing(){cancelAnimationFrame(S.ring.raf);S.ring.raf=0;}
function startRingLoop(){
  const v=F().ring;
  if(!S.ring.round&&v&&!S.ring.result){S.ring={...S.ring,round:v,t0:performance.now(),taps:[],hits:[]};render();}   // a round from another visit: the swing starts again now
  if(S.ring.raf||!S.ring.round||S.ring.result)return;
  const loop=()=>{
    if(!S.ring.round||S.ring.result||S.tab!=='ring'||!S.dlg?.open){S.ring.raf=0;return;}
    const el=S.dlg.querySelector('.fh-aim'),x=ringX(S.ring.round,performance.now()-S.ring.t0);if(el){el.style.left=trackPos(x);el.dataset.x=x.toFixed(2);}
    S.ring.raf=requestAnimationFrame(loop);
  };
  S.ring.raf=requestAnimationFrame(loop);
}
async function ringStart(){
  if(S.busy)return;S.busy=true;S.flash=null;render();
  const r=await send('fair_ring_start',{});S.busy=false;
  if(r?.fair?.round){stopRing();S.ring={...S.ring,round:r.fair.round,t0:performance.now(),taps:[],hits:[],result:null,say:pick(RINGER.idle)};}
  render();startRingLoop();
}
function ringThrow(){
  const R0=S.ring,rd=R0.round,rings=R().rings||5;if(!rd||R0.result||R0.taps.length>=rings)return;
  const t=Math.round(performance.now()-R0.t0);
  if(R0.taps.length&&t-R0.taps[R0.taps.length-1]<260)return;   // the server wants throws a little apart
  R0.taps.push(t);
  const judged=ringJudge(rd,R0.taps),hit=judged[judged.length-1],x=ringX(rd,t);
  sfx('throw');
  const layer=S.dlg?.querySelector('.fh-fly-layer');
  if(layer){const fly=document.createElement('i');fly.className='fh-fly '+(hit>=0?'hit':'miss');fly.style.left=trackPos(hit>=0?rd.xs[hit]:x);layer.append(fly);setTimeout(()=>fly.remove(),700);}
  setTimeout(()=>{
    if(S.ring.round!==rd)return;
    if(hit>=0){R0.hits=[...R0.hits,hit];R0.say=pick(RINGER.hit);sfx('clink');}else{R0.say=pick(RINGER.miss);sfx('miss');}
    if(R0.taps.length>=rings)finishRing(rd);else{render();startRingLoop();}
  },reduce()?60:430);
}
async function finishRing(rd){
  render();
  const r=await send('fair_ring_throw',{id:rd.id,taps:S.ring.taps});
  if(S.ring.round!==rd)return;
  stopRing();
  if(r?.fair){const x=r.fair;S.ring.result={...x,titles:x.titles||[]};S.ring.hits=(x.hits||[]).filter(h=>h>=0);
    S.ring.say=x.n>=(R().rings||5)?'Trời ơi, trúng hết luôn! Tay ném thần sầu!':x.n>=3?'Ném hay quá! Nhận quà nè!':'Lượt sau chắc chắn trúng nhiều hơn!';
    if(x.n>=3)sfx('win');}
  else{S.ring.round=null;S.ring.taps=[];S.ring.hits=[];}
  render();
}

/* ---- 🦀 Bầu cua ---- */
const bcTotal=()=>Object.values(S.bc.bets).reduce((a,b)=>a+b,0);
/** Most a bầu cua round may stake now: the table's max, today's room, the wallet (the server checks the same). */
function bcCap(){const f=F(),max=R().bc_max||20,left=R().nocap?Infinity:f.today?.left??max;return {max,cap:Math.max(0,Math.min(max,left,f.wallet??max)),left,wallet:f.wallet??max};}
function bcWhy(total){const c=bcCap();return total>c.left?`Hôm nay chỉ còn chơi được ${xu(c.left)}`:total>c.wallet?'Ví không đủ xu':'';}
function bcView(){
  const f=F(),b=S.bc,r=R(),total=bcTotal(),max=bcCap().cap,stop=f.today?.done,rolling=b.phase!=='idle',why=bcWhy(total);
  const hits=b.last&&b.phase==='idle'?new Set(b.last.dice):new Set();
  const dice=(b.dice||['bau','cua','ca']).map((d,i)=>`<span class="fh-die" style="--i:${i}">${art(d)}<span class="sr-only">${FACE_NAME[d]}</span></span>`).join('');
  const mat=FACES.map(face=>{const n=b.bets[face]||0,hit=hits.has(face);
    return `<button type="button" class="fh-face fh-f-${face}${hit?' hit':''}${n?' bet':''}" data-fh="bet" data-face="${face}" data-fh-key="face-${face}" aria-label="${FACE_NAME[face]}${n?`, đang đặt ${n} xu`:''}"${rolling||stop?' disabled':''}>${art(face)}<b>${FACE_NAME[face]}</b>${n?`<em class="fh-stake">${n}</em>`:''}</button>`;}).join('');
  const again=b.last&&b.phase==='idle'&&!stop?`<div class="row wrap fh-again">${btn('🔁 Lắc tiếp','roll',{},'primary small',total&&!why?' data-fh-key="again"':' disabled data-fh-key="again"')}${btn('Đặt lại','clear',{},'ghost small',' data-fh-key="reset"')}</div>`:'';
  const res=b.last&&b.phase==='idle'?bcResult(b.last)+again:'';
  return `<section class="fh-stall fh-bc" aria-label="Bầu cua tôm cá">
    ${say(DEALER,b.say)}
    <div class="fh-table"><div class="fh-plate ${b.phase==='shake'?'shake':''} ${b.phase==='idle'&&b.dice?'open':''}" aria-live="polite"><div class="fh-dice">${dice}</div><div class="fh-bowl" aria-hidden="true"></div></div>${res}</div>
    <div class="fh-mat" role="group" aria-label="Chiếu bầu cua: chạm một con để đặt">${mat}</div>
    <div class="fh-chips" role="group" aria-label="Mỗi lần chạm đặt"><span>Mỗi chạm</span>${CHIPS.map(c=>`<button type="button" class="fh-chip${b.chip===c?' on':''}" data-fh="chip" data-v="${c}" aria-pressed="${b.chip===c}" data-fh-key="chip-${c}">${c}</button>`).join('')}${btn('Gom lại','clear',{},'ghost small',total&&!rolling?' data-fh-key="gom"':' disabled data-fh-key="gom"')}</div>
    ${stop?'<p class="fh-rule"><b>Hôm nay chơi đủ rồi, mai ghé lắc tiếp nha.</b></p>':''}<div class="fh-go"><span>Đặt <b>${total}</b>/${max} xu</span>${btn(rolling?'Đang lắc…':'🥣 Lắc!','roll',{},'primary big',total&&!rolling&&!stop&&!why?' data-fh-key="roll"':' disabled data-fh-key="roll"')}</div>
    ${why&&!stop&&!rolling?`<p class="fh-why">${esc(why)}: bớt tiền đặt nha (Gom lại rồi đặt ít hơn).</p>`:''}
    <p class="fh-rule">Ra mấy con trùng mặt đặt thì ăn bấy nhiêu lần tiền cược, kèm tiền vốn. Ba con giống nhau (bão) ăn ${r.bao||10} lần.</p>
  </section>`;
}
function bcResult(l){
  const cls=l.net>0?'good':l.net<0?'bad':'';
  return `<div class="fh-result ${cls}"><b>${l.bao?'🌪️ Bão! ':''}${l.net>0?`+${xu(l.net)}`:l.net<0?`−${xu(-l.net)}`:'Hòa vốn'}</b>${l.points?`<small>+${l.points} điểm hội chợ</small>`:''}</div>`;
}
async function roll(){
  const b=S.bc,total=bcTotal();if(!total||b.phase!=='idle'||bcWhy(total))return;
  b.phase='shake';b.say='Lắc nè, lắc nè… xóc xóc xóc!';S.flash=null;render();sfx('shake');
  const r=await shaken(()=>send('fair_bc',{bets:{...b.bets}}));
  if(!r?.fair){b.phase='idle';b.say=pick(DEALER.idle);render();return;}
  const x=r.fair;b.dice=x.dice;b.last={...x};b.phase='idle';
  b.say=x.bao?`Bão! Bão! Ba con ${FACE_NAME[x.bao].toLowerCase()} luôn bà con ơi!`:x.net>0?'Trúng rồi! Chú chung tiền liền nè!':x.net===0?'Huề vốn, vui là chính!':'Ván sau gỡ lại nha, đừng buồn!';
  sfx('open');setTimeout(()=>sfx(x.net>0?'win':x.net<0?'lose':'open'),260);
  titles(x);render();
}
/** The round goes to the server while the bowl shakes (at least ROLL_MS; a quick "Lắc tiếp" waits out the server's gap). */
async function shaken(go){
  const hold=Math.max(0,S.lastRound+ROUND_GAP-Date.now());
  const [r]=await Promise.all([new Promise(ok=>setTimeout(ok,hold)).then(()=>{S.lastRound=Date.now();return go();}),new Promise(ok=>setTimeout(ok,reduce()?250:ROLL_MS))]);
  return r;
}
function titles(x){if(x.titles?.length)S.flash={text:`🎉 Danh hiệu mới: ${x.titles.map(t=>TITLE_NAMES[t]||t).join(', ')}`,kind:'good'};}

/* ---- 🕯️ Chiếu trong (xóc đĩa) ---- */
/** What a chiếu trong round may cost at worst (the stake, or the stake and the fine when the police come): the
 * server checks that against today's room (game/fair.py fair_xd, _guard_round). */
const xdWorst=st=>st+Math.max(R().fine_min||5,Math.floor(st/(R().xd_fine_div||2)));
/** Why a stake cannot be played right now ('' when it can). */
function xdWhy(st){
  const f=F(),left=R().nocap?Infinity:f.today?.left??Infinity;
  if(f.today?.done)return 'Hôm nay chơi vậy đủ rồi';
  if(xdWorst(st)>left)return `Hôm nay chỉ còn chơi được ${xu(left)}`;
  if(st>(f.wallet||0))return 'Ví không đủ xu';
  return '';
}
const SIDE_NAME={chan:'CHẴN',le:'LẺ'};
function xdView(){
  const f=F(),x=S.xd,r=R(),wait=raidLeft(),busy=x.phase!=='idle',left=R().nocap?Infinity:f.today?.left??0;
  if(x.raid)return raidCard(x.raid);
  const minSt=Math.min(...XD_STAKES),can=XD_STAKES.filter(v=>!xdWhy(v)),why=xdWhy(x.stake);
  const coins=(x.coins||[1,0,1,0]).map((c,i)=>`<span class="fh-coin ${c?'red':'white'}" style="--i:${i}"></span>`).join('');
  const L0=x.last&&x.phase==='idle'?x.last:null;
  const res=L0?`<div class="fh-result ${L0.net>0?'good':'bad'}"><b>Ra ${L0.even?'CHẴN':'LẺ'} (${L0.coins.filter(Boolean).length} đỏ)</b><small>Bạn chọn ${SIDE_NAME[L0.side]||''} · ${L0.net>0?`thắng ${xu(L0.net)}`:`thua ${xu(-L0.net)}`}${L0.points?` · +${L0.points} điểm hội chợ`:''}</small></div>`:'';
  const closed=wait>0?`<section class="fh-card fh-swept"><span aria-hidden="true">🧹</span><div><b>Chiếu dẹp rồi, bày lại sau <span data-fh-count="raid">${clock(wait)}</span></b><small>Ra trước chơi bầu cua, lô tô cho lành nha.</small></div></section>`:'';
  const broke=!wait&&!can.length?`<section class="fh-card fh-enough"><span aria-hidden="true">🍵</span><div><b>${f.today?.done?'Hôm nay chơi vậy đủ rồi, mai ghé tiếp nha.':left<xdWorst(minSt)?`Hôm nay chỉ còn chơi được ${xu(left)}, chiếu trong cần ít nhất ${xu(xdWorst(minSt))}`:'Ví không đủ xu cho chiếu trong'}</b><small>Chiếu trong tính cả tiền phạt nếu công an ghé (cược ${minSt} + phạt ${xdWorst(minSt)-minSt}). Ra trước chơi bầu cua hay ô ăn quan nha.</small>${btn('🦀 Ra chơi bầu cua','tab',{tab:'bc'},'ghost small',' data-fh-key="xd-bc"')}</div></section>`:'';
  const hist=x.hist.length?`<div class="fh-xdhist" aria-label="Mấy ván gần đây"><small>Mấy ván gần đây</small><span class="fh-xdchips">${x.hist.map(h=>`<i class="${h.even?'chan':'le'}${h.win?' win':''}" title="${h.even?'Chẵn':'Lẻ'} · ${h.win?'thắng':'thua'}">${h.even?'C':'L'}</i>`).join('')}</span><small>Bạn: thắng <b>${x.tally.w}</b> · thua <b>${x.tally.l}</b>${x.tally.raid?` · bị kiểm tra ${x.tally.raid}`:''}</small></div>`:'';
  const dis=busy||wait>0;
  return `<section class="fh-stall fh-xd" aria-label="Chiếu trong: xóc đĩa chẵn lẻ">
    ${say(HOST,x.say,'dark')}
    <p class="fh-warn">⚠️ Chiếu trong cược lớn hơn (${r.xd_min}–${r.xd_max} xu). Thỉnh thoảng công an phường ghé kiểm tra: mất tiền cược và bị phạt.</p>
    ${closed}${broke}
    <div class="fh-table dark"><div class="fh-plate xd ${x.phase==='shake'?'shake':''} ${x.phase==='idle'&&x.coins?'open':''}"><div class="fh-coins">${coins}</div><div class="fh-bowl" aria-hidden="true"></div></div>${res}</div>
    ${hist}
    <div class="fh-xsides" role="group" aria-label="Chọn chẵn hay lẻ">${[['chan','Chẵn','0, 2 hoặc 4 mặt đỏ'],['le','Lẻ','1 hoặc 3 mặt đỏ']].map(([id,l,s])=>`<button type="button" class="fh-xside${x.side===id?' on':''}" data-fh="side" data-v="${id}" aria-pressed="${x.side===id}" data-fh-key="side-${id}"${dis?' disabled':''}>${x.side===id?'<em class="fh-tick" aria-hidden="true">✓</em>':''}<b>${l}</b><small>${s}</small></button>`).join('')}</div>
    <div class="fh-chips" role="group" aria-label="Tiền cược"><span>Cược</span>${XD_STAKES.map(v=>{const no=xdWhy(v);return `<button type="button" class="fh-chip${x.stake===v?' on':''}" data-fh="stake" data-v="${v}" aria-pressed="${x.stake===v}" data-fh-key="stake-${v}"${dis||no?' disabled':''}${no?` title="${esc(no)}"`:''}>${v}</button>`;}).join('')}</div>
    <div class="fh-go"><span>Chọn <b>${x.side==='chan'?'Chẵn':'Lẻ'}</b> · <b>${xu(x.stake)}</b></span>${btn(busy?'Đang xóc…':'🫙 Xóc!','shakexd',{},'primary big',dis||why?' disabled data-fh-key="xd"':' data-fh-key="xd"')}</div>
    ${why&&!wait&&can.length?`<p class="fh-why">${esc(why)}: chọn mức cược nhỏ hơn nha (tính cả tiền phạt ${xu(xdWorst(x.stake)-x.stake)} nếu công an ghé).</p>`:''}
    <p class="fh-rule">Bốn đồng xu, mặt đỏ chẵn (0, 2, 4) là Chẵn, lẻ (1, 3) là Lẻ. Đoán trúng ăn 1:1.</p>
  </section>`;
}
function raidCard(r){
  return `<section class="fh-card fh-raid" role="alert"><div class="fh-siren" aria-hidden="true"><i></i><i></i></div>
    <h3>🚨 Công an phường kiểm tra!</h3>
    <p class="fh-cop">“Hội chợ vui thì vui, chiếu trong là dẹp nha bà con! Ai ngồi đây thì ghi tên, nộp phạt rồi ra trước chơi cho đàng hoàng.”</p>
    <div class="fh-raid-bill"><span>Tiền cược bị tịch thu</span><b>−${xu(r.stake)}</b><span>Nộp phạt</span><b>−${xu(r.fine)}</b></div>
    <p class="muted small">Anh Ba chiếu trong đã cuốn chiếu chạy mất. Chiếu dẹp ${Math.round((r.cooldown||120)/60)} phút.</p>
    ${r.titles?.includes('f_raid')?'<p class="fh-award">🚨 Danh hiệu mới: <b>Bị công an hỏi thăm</b></p>':''}
    <div class="row wrap fh-raid-go">${btn('Dạ, em ra chơi bầu cua','raidok',{tab:'bc'},'primary')}${btn('Đi dò lô tô','raidok',{tab:'lt'},'ghost')}</div></section>`;
}
async function shakeXd(){
  const x=S.xd;if(x.phase!=='idle'||xdWhy(x.stake)||raidLeft()>0)return;
  const side=x.side,stake=x.stake;
  x.phase='shake';x.say='Xóc nè! Nghe kêu lắc cắc chưa…';S.flash=null;render();sfx('shake');
  const r=await shaken(()=>send('fair_xd',{side,stake}));
  x.phase='idle';
  if(!r?.fair){x.say=pick(HOST.idle);render();return;}
  const d=r.fair;
  if(d.raid){x.raid={...d};x.coins=null;x.last=null;x.tally.raid++;x.say=pick(HOST.idle);sfx('siren');render();return;}
  x.coins=d.coins;x.last={...d,side:d.side||side};x.say=d.net>0?'Hên quá ta! Anh chung liền.':'Ván sau chắc chắn tới lượt em!';
  x.hist=[{even:d.even,win:d.net>0},...x.hist].slice(0,10);x.tally[d.net>0?'w':'l']++;
  sfx('open');setTimeout(()=>sfx(d.net>0?'win':'lose'),260);titles(d);render();
}

/* ---- 🎱 Gánh lô tô: cô Bảy hô số, the troupe between rounds, tờ dò marked by hand, Kinh checked by the server ---- */
const colOf=n=>n<10?0:n>=90?8:Math.floor(n/10);
const COLS=['1–9','10–19','20–29','30–39','40–49','50–59','60–69','70–79','80–90'];
const SPEEDS=[['🐢','Chậm',3300],['🙂','Vừa',2300],['🐇','Nhanh',1200]];
const TIER_NAME={nho:'Vé nhỏ',vua:'Vé vừa',lon:'Vé lớn'};
const MODE_INFO={thuong:['🎱','Vòng thường','Đủ một hàng ngang trên một tờ là kinh.'],
  nguoc:['🙃','Vòng lật ngược','Cô Bảy đọc số lộn ngược: nghe 21 là số 12, nghe 07 là số 70. Dò cho tỉnh nha!'],
  doi:['🎎','Vòng Kinh đôi','Phải đủ hai hàng ngang trên cùng một tờ mới kinh.'],
  dem:['🏺','Hũ đêm hội','Kinh cả tờ: đủ hết 15 số. Sáu người cùng chơi nên hũ to!']};
const LT_TRACK={f:'wedding-funk',name:'Funk nhún nhảy'};   // CC0, public/music/CREDITS.md
const LT_MUSIC='mnl.fair.ltmusic';
/** The newer server's gánh lô tô (rules, the vòng of this minute and the next two, today's tally); null: older server. */
const G=()=>F().ganh||null;
function L(){const v=F().loto;return v&&!v.expired?v:null;}
const need=v=>v?.need||1;
const flip=n=>String(n).split('').reverse().join('');
/** The number as the board and the caller show it: reversed in a lật ngược vòng. */
const shownNum=(v,n)=>v?.mode==='nguoc'?flip(n):String(n);
const nowSlot=()=>Math.floor(serverNow()/60000);
/** This minute's vòng from the server's list (null once the list is behind the clock: the server then decides). */
function curMode(){const g=G();if(!g)return 'thuong';const m=g.modes.find(x=>x[0]===nowSlot());return m?m[1]:null;}
const modeLabel=m=>G()?.names?.[m]||MODE_INFO[m]?.[1]||m;

function syncLoto(){
  const v=L();
  if(!v){if(S.lt.id){pauseLoto();S.lt.id=null;}return null;}
  if(v.id!==S.lt.id){
    pauseLoto();
    let saved=null;try{saved=JSON.parse(localStorage.getItem(LS)||'null');}catch{/* storage blocked */}
    const ok=saved&&saved.id===v.id,cards=(v.cards||[v.card]).length;
    let marks=ok&&Array.isArray(saved.marks)?saved.marks:[];
    if(marks.length&&!Array.isArray(marks[0]))marks=[marks];   // the older save: one card
    marks=Array.from({length:cards},(_,i)=>(Array.isArray(marks[i])?marks[i]:[]).filter(n=>Number.isInteger(n)));
    S.lt={...S.lt,id:v.id,shown:ok?Math.min(saved.shown|0,v.npc_done):0,marks,over:null,won:null,hut:null,claiming:false,check:false,
      say:ok?S.lt.say:MC.ready};
  }
  if(v.stage==='won'&&!S.lt.won)S.lt.won={prize:v.prize??R().loto_prize,mode:v.mode,quiet:true};
  if(v.stage==='lost'&&!S.lt.over&&!S.lt.won)S.lt.over={by:v.npc_name,quiet:true};
  return v;
}
function saveLoto(){try{localStorage.setItem(LS,JSON.stringify({id:S.lt.id,shown:S.lt.shown,marks:S.lt.marks}));}catch{/* storage blocked */}}
function pauseLoto(){clearTimeout(S.lt.timer);S.lt.timer=null;}
const playing=v=>v&&v.stage==='play'&&!S.lt.over&&!S.lt.won;
function resumeLoto(){
  const v=syncLoto();pauseLoto();ltMusic();
  if(!playing(v)||!S.dlg?.open||S.tab!=='lt')return;
  S.lt.timer=setTimeout(stepLoto,S.lt.shown?SPEEDS[S.lt.speed][2]:900);
}
function stepLoto(){
  const v=L();if(!playing(v))return;
  if(S.lt.shown>=v.npc_done){   // a neighbour's pattern is full: they shout, unless the player beats them to it
    if(!S.lt.claiming){S.lt.over={by:v.npc_name};S.lt.say=pick(MC.lose).replace('{who}',v.npc_name);sfx('lose');react('😮',3);saveLoto();render();send('fair_loto_fold',{});}
    return;
  }
  S.lt.shown++;
  const i=S.lt.shown-1,n=v.seq[i];
  S.lt.say=lineFor(v,i,n);
  const hot=rivalMiss(v,calledSet(v)).some(x=>x.miss<=1);
  if(hot&&!S.lt.hot){S.lt.hot=true;react('😱',2);}
  saveLoto();sfx('call');render();
  if(hot&&Math.random()<.18)setTimeout(()=>{if(S.lt.id===v.id&&playing(L())){S.lt.say=pick(MC.near);render();}},Math.min(900,SPEEDS[S.lt.speed][2]/2));
  S.lt.timer=setTimeout(stepLoto,S.lt.shown>=v.npc_done?NPC_GRACE:SPEEDS[S.lt.speed][2]);
}
function lineFor(v,i,n){
  if(v.mode!=='nguoc')return callLine(v.seq,i,v.slot,language()==='en');
  const r=flip(n);
  if(language()==='en')return `Flipped: ${r}!`;
  return r.startsWith('0')?`Lật ngược nè bà con: không ${words(Number(r[1]))}! Ngược lại là số mấy?`:`${callLine(v.seq,i,v.slot,false,Number(r))} (lật ngược!)`;
}
const calledSet=v=>new Set(v.seq.slice(0,S.lt.shown));
const cardsOf=v=>v.cards||[v.card];
/** Full rows on a card by the player's own marks (marks only ever hold called numbers). */
const fullRows=(v,ci)=>{const m=new Set(S.lt.marks[ci]||[]);return cardsOf(v)[ci].filter(row=>row.every(n=>m.has(n))).length;};
function bestCard(v){
  let best=0,score=-1;
  cardsOf(v).forEach((_,ci)=>{const s=fullRows(v,ci)*100+(S.lt.marks[ci]||[]).length;if(s>score){score=s;best=ci;}});
  return best;
}
function rivalMiss(v,called){
  const k=need(v);
  return v.npcs.map(n=>({...n,miss:n.rows.map(r=>r.filter(x=>!called.has(x)).length).sort((a,b)=>a-b).slice(0,k).reduce((a,b)=>a+b,0)}));
}
/** Side-bet winnings already in the wallet but not yet shown (the server settles them at the purchase). */
function ltHold(){const v=L();if(!v||!playing(v)||!v.side)return 0;return Object.values(v.side).reduce((a,s)=>a+(s.back||0),0);}

/* ---- the stage: cô Bảy, the troupe, the crowd ---- */
const MC_ART=`<svg class="fh-mcart" viewBox="0 0 90 120" aria-hidden="true">
  <g class="fh-mc-fan"><path d="M70 62 L52 34 A32 32 0 0 1 88 44 Z" fill="#f6a5c8" stroke="#c2477e" stroke-width="1.5"/><path d="M70 62 L58 36 M70 62 L66 33 M70 62 L75 34 M70 62 L82 38" stroke="#c2477e" stroke-width="1.2"/><circle cx="70" cy="62" r="2.4" fill="#8a5a26"/></g>
  <path d="M28 66 Q45 58 62 66 L72 116 Q45 122 18 116 Z" fill="#d9387a"/>
  <g class="fh-sequin" fill="#ffe27a"><circle cx="34" cy="80" r="1.6"/><circle cx="46" cy="74" r="1.6"/><circle cx="56" cy="86" r="1.6"/><circle cx="40" cy="96" r="1.6"/><circle cx="52" cy="104" r="1.6"/><circle cx="28" cy="108" r="1.6"/><circle cx="62" cy="108" r="1.6"/></g>
  <g class="fh-sequin b" fill="#fff"><circle cx="40" cy="70" r="1.2"/><circle cx="50" cy="94" r="1.2"/><circle cx="33" cy="99" r="1.2"/><circle cx="60" cy="98" r="1.2"/><circle cx="45" cy="112" r="1.2"/></g>
  <path d="M60 68 L70 62" stroke="#f3c9a4" stroke-width="5" stroke-linecap="round"/>
  <path d="M30 68 L20 80 L24 86" stroke="#f3c9a4" stroke-width="5" stroke-linecap="round" fill="none"/><rect x="19" y="80" width="6" height="12" rx="3" fill="#333" transform="rotate(-20 22 86)"/><circle cx="19" cy="78" r="4.5" fill="#666"/>
  <circle cx="45" cy="22" r="13" fill="#2b1d16"/><circle cx="45" cy="40" r="17" fill="#f3c9a4"/><path d="M28 36 Q30 20 45 20 Q60 20 62 36 Q55 28 45 28 Q35 28 28 36Z" fill="#2b1d16"/>
  <circle cx="57" cy="20" r="5" fill="#ff7aa8"/><circle cx="57" cy="20" r="2" fill="#ffe27a"/>
  <circle cx="39" cy="40" r="2" fill="#2b1d16"/><circle cx="51" cy="40" r="2" fill="#2b1d16"/><circle cx="35" cy="46" r="3" fill="#ff9bb8" opacity=".7"/><circle cx="55" cy="46" r="3" fill="#ff9bb8" opacity=".7"/>
  <path d="M40 48 Q45 53 50 48" stroke="#b83a3a" stroke-width="2" fill="none" stroke-linecap="round"/></svg>`;
function stageHtml(v){
  const live=playing(v),cur=live&&S.lt.shown?v.seq[S.lt.shown-1]:null;
  const ball=`<span data-fh-key="ball-${S.lt.shown}" class="fh-ball${cur?' pop':''}${v?.mode==='nguoc'&&cur?' flip':''}" aria-live="polite" aria-label="${cur?`Số vừa gọi: ${shownNum(v,cur)}`:'Chưa gọi số'}">${cur!=null?esc(shownNum(v,cur)):'🎱'}</span>`;
  return `<div class="fh-stage${live?' live':''}" aria-label="Sân khấu lô tô">
    <div class="fh-curtain" aria-hidden="true"></div><div class="fh-spot" aria-hidden="true"></div>
    <div class="fh-mc">${MC_ART}<b>${esc(MC.name)}</b></div>
    <div class="fh-mcsay"><div class="fh-bubble"><small>${esc(MC.name)}</small><p>${esc(S.lt.say||pick(MC.hello))}</p></div>${live?ball:''}</div>
  </div>`;
}
function actsHtml(){
  const a=ACTS[S.lt.act%ACTS.length],line=S.lt.actSay||a.say[0];
  return `<div class="fh-acts fh-act-${a.k}" aria-live="polite"><span class="fh-performer" aria-hidden="true">${a.k==='juggle'?'🤹<i class="fh-ballz"><b></b><b></b><b></b></i>':a.k==='sing'?'🎤<i class="fh-notes">♪ ♫ ♪</i>':a.who}</span><div><b>🎪 ${esc(a.name)}</b><small>${esc(line)}</small></div></div>`;
}
function crowdHtml(){
  const people=(G()?.neighbours||[['Bác Tư','👴'],['Bà Năm','👵'],['Chú Sáu','🧔'],['Cô Ba','👩'],['Anh Tèo','🧑'],['Chị Mận','👧']]);
  return `<div class="fh-crowd" aria-hidden="true">${people.map(([,e],i)=>`<span style="--i:${i}">${e}</span>`).join('')}</div>`;
}
/** Emoji floating up from the crowd (decoration only). */
function react(e,count=1){
  if(reduce())return;
  const box=S.dlg?.querySelector('.fh-reactlayer'),st=S.dlg?.querySelector('.fh-stage');if(!box||!st)return;
  box.style.top=`${Math.round(st.getBoundingClientRect().bottom-S.dlg.getBoundingClientRect().top)}px`;   // just above the crowd
  for(let k=0;k<count;k++){const el=document.createElement('i');el.textContent=e==='*'?pick(CROWD):e;el.style.left=`${10+Math.random()*80}%`;el.style.animationDelay=`${k*.15}s`;box.append(el);setTimeout(()=>el.remove(),2200);}
}
/** The troupe's next act, every few seconds while no round is being called (only that box is redrawn). */
function nextAct(){
  if(S.tab!=='lt'||!S.dlg?.open||playing(L()))return;
  const g=G(),slot=nowSlot();
  if(g&&S.lt.slot!==slot&&!S.busy){
    S.lt.slot=slot;
    if(g.modes.filter(x=>x[0]>=slot).length<4&&Date.now()-(S.lt.asked||0)>30000){S.lt.asked=Date.now();S.env.api.refresh().catch(()=>{/* later */});}
    render();return;
  }
  if(Date.now()-S.lt.actAt<7000)return;
  S.lt.actAt=Date.now();S.lt.act=(S.lt.act+1)%ACTS.length;S.lt.actSay=pick(ACTS[S.lt.act].say);
  const el=S.dlg.querySelector('.fh-acts');if(el)el.outerHTML=actsHtml();
  react('*',2);
}

/* ---- the music: one CC0 recording looped while the stall is on screen, only when the game's music is on ---- */
const LM={on:false,src:null,g:null,buf:null,loading:null};
const musicPref=()=>{try{return localStorage.getItem(LT_MUSIC)!=='0';}catch{return true;}};
const gameMusic=()=>{const st=S.env?.api?.state?.settings||{};return st.music!==false&&st.musicTrack!=='off';};
function ltMusic(){
  const st=S.env?.api?.state?.settings||{};
  const want=gameMusic()&&musicPref()&&!!S.dlg?.open&&S.tab==='lt'&&F().open;
  if(want&&!LM.on){
    const c=audioContext();if(!c)return;
    LM.on=true;wantAudio('fair',true);duck('fair',true);
    LM.g=c.createGain();LM.g.gain.value=0;LM.g.connect(c.destination);
    const url=globalThis.__mnlBoot?.asset?.(`/music/${LT_TRACK.f}.mp3`)||`/music/${LT_TRACK.f}.mp3`;
    LM.loading??=fetch(url).then(r=>{if(!r.ok)throw new Error(r.status);return r.arrayBuffer();}).then(b=>new Promise((ok,no)=>{const p=c.decodeAudioData(b,ok,no);p?.catch?.(()=>{});}));
    LM.loading.then(buf=>{
      if(!LM.on||LM.src)return;
      LM.buf=buf;const src=c.createBufferSource();src.buffer=buf;src.loop=true;src.connect(LM.g);src.start();LM.src=src;
      const vol=Math.max(0,Math.min(1,(st.musicVolume??45)/100))*.5,t=c.currentTime;LM.g.gain.setValueAtTime(0,t);LM.g.gain.linearRampToValueAtTime(vol,t+1.2);
    }).catch(()=>{LM.loading=null;/* the show goes on without music */});
  }else if(!want&&LM.on){
    LM.on=false;duck('fair',false);wantAudio('fair',false);
    const {src,g}=LM;LM.src=null;LM.g=null;
    const c=audioContext();
    if(g&&c){const t=c.currentTime;g.gain.cancelScheduledValues(t);g.gain.setValueAtTime(g.gain.value,t);g.gain.linearRampToValueAtTime(0,t+.4);}
    setTimeout(()=>{try{src?.stop();}catch{/* not started */}try{g?.disconnect();}catch{/* gone */}},450);
    if(!S.dlg?.open){LM.loading=null;LM.buf=null;}   // a decoded song is MBs: kept only while the fair is open
  }
}
function musicBtn(){
  if(!gameMusic())return `<button type="button" class="btn ghost small" disabled title="Nhạc nền đang tắt trong Cài đặt">🔇 Nhạc (đang tắt trong Cài đặt)</button>`;
  const on=musicPref();
  return btn(on?'🔊 Nhạc gánh':'🔇 Nhạc gánh','ltmusic',{},'ghost small',` aria-pressed="${on}" data-fh-key="ltmusic"`);
}

/* ---- views ---- */
function lotoView(){
  const v=syncLoto();
  if(!S.lt.say)S.lt.say=pick(MC.hello);
  if(playing(v))return roundView(v);
  return `<section class="fh-stall fh-lt" aria-label="Lô tô">
    ${stageHtml(v)}${crowdHtml()}${actsHtml()}
    ${v?endCard(v):''}
    ${G()?buyPanel():oldBuy()}
    ${G()?todayBoard():''}
    <div class="fh-go">${musicBtn()}</div>
    ${howLoto()}</section>`;
}
function endCard(v){
  const W=S.lt.won,O=S.lt.over;if(!W&&!O)return '';
  let h='';
  if(W){const [se,sn]=MODE_STICKER[W.mode]||STICKERS[(Number(String(v.id).split('-')[1])||0)%STICKERS.length];
    h=`<div class="fh-card fh-kinhcard"><div class="fh-sticker" aria-hidden="true">${se}</div><h3>Kinh! +${xu(W.prize)}</h3><p class="fh-award">Nhãn dán: <b>${esc(sn)}</b></p>${(W.titles||[]).map(t=>`<p class="fh-award">🎉 Danh hiệu mới: <b>${esc(TITLE_NAMES[t]||t)}</b></p>`).join('')}${W.points?`<p class="muted small">+${W.points} điểm hội chợ</p>`:''}</div>`;}
  else if(O.out)h=`<div class="fh-card fh-lostcard"><b>🙈 Kinh hụt ba lần, cô Bảy mời nghỉ ván này</b><small>Ván sau dò kỹ rồi hãy hô nha!</small></div>`;
  else if(!O.quiet)h=`<div class="fh-card fh-lostcard"><b>📣 ${esc(O.by)}: “Kinh!”</b><small>${O.mine?'Tờ của bạn cũng vừa đủ mà chưa kịp hô. Lần sau hô lẹ nha!':'Ván này người khác đủ trước rồi.'}</small></div>`;
  const side=v.side?`<div class="fh-card fh-sideres"><b>🎯 Số chốt ván: ${esc(shownNum(v,v.chot_n))}${v.mode==='nguoc'?` <small>(tức số ${v.chot_n})</small>`:''}</b>${Object.entries(v.side).map(([k,s])=>`<span class="${s.back?'good':'bad'}">${k==='cl'?`Chẵn/lẻ: ${s.pick==='chan'?'Chẵn':'Lẻ'}`:`Cột ${COLS[s.pick]}`} · ${s.back?`ăn ${xu(s.back)}`:`thua ${xu(s.stake)}`}</span>`).join('')}</div>`:'';
  const check=`<button type="button" class="btn ghost small" data-fh="ltcheck" aria-pressed="${S.lt.check}" data-fh-key="ltcheck">${S.lt.check?'Ẩn bản dò':'🔍 Tự dò lại tờ vừa chơi'}</button>`;
  return h+side+`<div class="fh-go">${check}</div>${S.lt.check?cardsHtml(v,false):''}`;
}
function buyPanel(){
  const g=G(),f=F(),m=curMode()||'thuong',[me,,md]=MODE_INFO[m]||MODE_INFO.thuong,lt=S.lt,price=g.tiers[lt.tier]||5;
  const prize=(g.prizes?.[m]?.[lt.tier]||[])[lt.n-1]||0,rule=g.modes_rule?.[m]||{npcs:4};
  const side=(lt.cl?lt.cls:0)+(lt.cot!=null?lt.cots:0),total=lt.n*price+side;
  const why=total>(f.wallet||0)?'Ví không đủ xu':S.busy?'Đang mua…':'';   // no daily limit: only the wallet
  const next=g.modes.filter(x=>x[0]>nowSlot()).slice(0,2).map(([s,k])=>`<span class="fh-nextmode">${esc(new Date(s*60000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Ho_Chi_Minh'}))} · ${MODE_INFO[k]?.[0]||''} ${esc(modeLabel(k))}</span>`).join('');
  const tiers=Object.entries(g.tiers).map(([k,p])=>`<button type="button" class="fh-tier${lt.tier===k?' on':''}" data-fh="lttier" data-v="${k}" aria-pressed="${lt.tier===k}" data-fh-key="tier-${k}"><b>${esc(TIER_NAME[k]||k)}</b><small>${xu(p)}/tờ</small></button>`).join('');
  const ns=Array.from({length:g.cards},(_,i)=>i+1).map(n=>`<button type="button" class="fh-chip${lt.n===n?' on':''}" data-fh="ltn" data-v="${n}" aria-pressed="${lt.n===n}" data-fh-key="ltn-${n}">${n}</button>`).join('');
  const chip=(op,v,on)=>`<button type="button" class="fh-chip small${on?' on':''}" data-fh="${op}" data-v="${v}" aria-pressed="${on}" data-fh-key="${op}-${v}">${v}</button>`;
  const cl=[['chan','Chẵn'],['le','Lẻ']].map(([k,l])=>`<button type="button" class="fh-pickb${lt.cl===k?' on':''}" data-fh="ltcl" data-v="${k}" aria-pressed="${lt.cl===k}" data-fh-key="cl-${k}">${l}</button>`).join('');
  const cot=COLS.map((l,i)=>`<button type="button" class="fh-pickb${lt.cot===i?' on':''}" data-fh="ltcot" data-v="${i}" aria-pressed="${lt.cot===i}" data-fh-key="cot-${i}">${l}</button>`).join('');
  return `<div class="fh-card fh-ltbuy">
    <div class="fh-modebar mode-${m}"><span class="fh-modeico" aria-hidden="true">${me}</span><div class="grow"><b>${esc(modeLabel(m))}</b><small>${esc(md)}</small></div></div>
    <div class="fh-nextmodes"><small>Phút sau:</small>${next}</div>
    <h4>🎟️ Chọn vé</h4><div class="fh-lttiers" role="group" aria-label="Loại vé">${tiers}</div>
    <div class="fh-chips" role="group" aria-label="Số tờ"><span>Số tờ</span>${ns}</div>
    <p class="fh-pot">🏺 Hũ ván này: <b>${xu(prize)}</b> <small>· ${lt.n} tờ của bạn + ${rule.npcs} tờ hàng xóm, cô Bảy giữ ${rule.cut}% tiền gánh</small></p>
    <details class="fh-side"${lt.cl||lt.cot!=null?' open':''}><summary>🎲 Cược phụ (tùy chọn)</summary>
      <p class="small muted">Đoán về <b>số chốt ván</b>: con số làm đủ tờ đầu tiên trên chiếu (của bạn hay hàng xóm). Kết quả mở khi ván xong.</p>
      <div class="fh-sidebet"><b>Chẵn hay lẻ?</b> <small>ăn 1 trả 1 · số 7 và 70 là số ruột cô Bảy: ra hai số đó thì cô Bảy ăn cả hai cửa</small>
        <div class="fh-picks">${cl}${lt.cl?btn('Bỏ','ltcl',{v:''},'ghost small'):''}</div>
        ${lt.cl?`<div class="fh-chips"><span>Đặt</span>${g.side_stakes.map(s=>chip('ltcls',s,lt.cls===s)).join('')}</div>`:''}</div>
      <div class="fh-sidebet"><b>🍀 Cột may mắn</b> <small>số chốt nằm ở cột nào trên tờ dò · trúng ăn ${String(g.cot_pay).replace('.',',')} lần tiền đặt</small>
        <div class="fh-picks cols">${cot}${lt.cot!=null?btn('Bỏ','ltcot',{v:''},'ghost small'):''}</div>
        ${lt.cot!=null?`<div class="fh-chips"><span>Đặt</span>${g.side_stakes.map(s=>chip('ltcots',s,lt.cots===s)).join('')}</div>`:''}</div>
    </details>
    ${btn(S.busy?'Cô Bảy đang xé tờ…':`🎟️ Mua ${lt.n} tờ · ${xu(total)}`,'buy',{},'primary big full',why?` disabled data-fh-key="buy" title="${esc(why)}"`:' data-fh-key="buy"')}
    ${why&&!S.busy?`<p class="fh-why">${esc(why)}</p>`:''}
  </div>`;
}
function oldBuy(){
  const r=R(),f=F();
  return `<div class="fh-card fh-buy"><div class="fh-ticket" aria-hidden="true"><i></i><i></i><i></i></div><div class="grow"><b>Tờ dò ${xu(r.loto_price)}</b><small>Đủ 5 số một hàng ngang trước ${r.loto_npcs} người chơi khác: hô “Kinh!” ăn ${xu(r.loto_prize)}.</small></div></div>
    ${btn(`🎟️ Mua tờ dò · ${xu(r.loto_price)}`,'buy',{},'primary big full',f.today?.done||S.busy?' disabled data-fh-key="buy"':' data-fh-key="buy"')}`;
}
function todayBoard(){
  const g=G(),t=g.today||{},people=g.neighbours||[];
  const rows=[['Bạn','🙂',t.w||0,true],...people.map(([n,e],i)=>[n,e,(t.npc||[])[i]||0,false])].sort((a,b)=>b[2]-a[2]||(b[3]-a[3]));
  if(!t.r)return '';
  const top=rows[0][2]>0?rows[0]:null;
  return `<details class="fh-how fh-ltday"><summary>🏅 Bảng kinh hôm nay</summary>
    <ol>${rows.map((r,i)=>`<li class="${r[3]?'me':''}"><span aria-hidden="true">${r[1]}</span><b>${esc(r[0])}</b><em>${r[2]} lần kinh</em>${i===0&&top?' <span class="fh-crownmini">👑 Vua kinh hôm nay</span>':''}</li>`).join('')}</ol>
    <p class="small muted">Hôm nay bạn chơi ${t.r} ván${t.fk?`, kinh hụt ${t.fk} lần 🙈`:''}. Bảng này tính lại mỗi ngày.</p></details>`;
}
function howLoto(){
  const g=G();
  if(!g)return `<p class="fh-rule">Cô Bảy hô số nào, bạn chạm số đó trên tờ dò. Ai mua tờ trong cùng một phút sẽ nghe chung một lượt số.</p>`;
  const pz=g.prizes||{};
  return `<details class="fh-how"><summary>Cách chơi gánh lô tô</summary><ul>
    <li>Mua 1 đến ${g.cards} tờ dò. Cô Bảy hô số nào thì số đó sáng lên trên tờ của bạn, bạn tự chạm để đánh dấu, không ai đánh dấu giùm.</li>
    <li>Đủ hình của vòng thì bấm “Kinh!”. Cô Bảy dò lại: đúng thì ôm hũ; kinh hụt (hàng chưa đủ) thì bỏ ${xu(g.fine)} vô hũ phạt${g.hut_max?`, hụt ${g.hut_max} lần là nghỉ ván`:' rồi dò tiếp, hụt mấy lần cũng được'}.</li>
    <li>Hũ = tiền tờ của cả chiếu (của bạn và hàng xóm), cô Bảy giữ một chút tiền gánh. Ai đủ trước người đó ăn, hai người cùng lúc thì bạn được.</li>
    <li>Mỗi phút một vòng: thường, Kinh đôi (hai hàng), lật ngược (đọc số ngược). Từ ${g.dem_hours[0]} giờ tới ${g.dem_hours[g.dem_hours.length-1]+1} giờ tối là Hũ đêm hội: kinh cả tờ, sáu người chơi.</li>
    <li>Ví dụ vé vừa 1 tờ: vòng thường ăn ${xu(pz.thuong?.vua?.[0])}, Kinh đôi ${xu(pz.doi?.vua?.[0])}, Hũ đêm hội ${xu(pz.dem?.vua?.[0])}.</li>
    <li>Ai mua tờ trong cùng một phút sẽ nghe chung một lượt số.</li></ul></details>`;
}
/** The calls light up on the player's own tờ while a round is called: the latest one glows (cur), the earlier ones
 * not marked yet keep a soft tint (hint). Hints only: the player still taps to mark. Not in a lật ngược vòng, whose
 * whole game is flipping the number back by ear. */
function cardsHtml(v,live=true){
  const all=new Set(v.seq.slice(0,live?S.lt.shown:S.lt.shown||v.chot||0)),check=!live,lit=live&&v.mode!=='nguoc',cur=lit&&S.lt.shown?v.seq[S.lt.shown-1]:null;
  return cardsOf(v).map((card,ci)=>{
    const marks=new Set(S.lt.marks[ci]||[]);
    const grid=card.map(row=>{const cells=Array(9).fill(null);row.forEach(n=>{cells[colOf(n)]=n;});
      return `<div class="fh-row" role="row">${cells.map(n=>{
        if(n==null)return '<span class="fh-cell empty" role="gridcell"></span>';
        const cls=`fh-cell${marks.has(n)?' marked':''}${check&&all.has(n)&&!marks.has(n)?' called':''}${n===cur?' cur':lit&&all.has(n)&&!marks.has(n)?' hint':''}`;
        return live?`<button type="button" role="gridcell" class="${cls}" data-fh="mark" data-c="${ci}" data-n="${n}" data-fh-key="n-${ci}-${n}" aria-pressed="${marks.has(n)}" aria-label="Số ${n}${n===cur?', vừa gọi':''}">${n}</button>`
          :`<span role="gridcell" class="${cls}">${n}</span>`;}).join('')}</div>`;}).join('');
    return `<div class="fh-ticketcard" role="grid" aria-label="Tờ dò ${ci+1}">${cardsOf(v).length>1?`<span class="fh-cardno">Tờ ${ci+1}</span>`:''}${grid}</div>`;
  }).join('')+(check?`<p class="small muted">Viền đứt: số đã gọi (tới số chốt) mà bạn chưa chạm.</p>`:'');
}
function boardHtml(v){
  if(v.mode==='nguoc')return `<div class="fh-bigboard covered" aria-label="Bảng số úp lại trong vòng lật ngược"><span>🙃 Vòng lật ngược: bảng số úp lại, nghe cô Bảy đọc rồi tự lật nha!</span></div>`;
  const called=calledSet(v),cur=S.lt.shown?v.seq[S.lt.shown-1]:null;
  let h='';for(let n=1;n<=90;n++)h+=`<i class="${called.has(n)?'on':''}${n===cur?' cur':''}">${n}</i>`;
  return `<div class="fh-bigboard" aria-label="Bảng số đã gọi">${h}</div>`;
}
function roundView(v){
  const called=calledSet(v);
  const rivals=rivalMiss(v,called).map(n=>`<span class="fh-rival${n.miss<=1?' hot':''}"><span aria-hidden="true">${n.emoji}</span>${esc(n.name)}<em>${n.miss<=1?'chờ 1!':`còn ${n.miss}`}</em></span>`).join('');
  const recent=v.seq.slice(Math.max(0,S.lt.shown-7),Math.max(0,S.lt.shown-1)).reverse().map(n=>`<i>${esc(shownNum(v,n))}</i>`).join('');
  const [me]=MODE_INFO[v.mode||'thuong']||MODE_INFO.thuong;
  const hut=v.fk||S.lt.hut?.fk||0;
  const speed=SPEEDS.map(([e,l],i)=>`<button type="button" class="fh-chip small${S.lt.speed===i?' on':''}" data-fh="ltspeed" data-v="${i}" aria-pressed="${S.lt.speed===i}" aria-label="Gọi ${l.toLowerCase()}" data-fh-key="sp-${i}">${e}</button>`).join('');
  return `<section class="fh-stall fh-lt" aria-label="Lô tô">
    ${stageHtml(v)}
    <div class="fh-callrow"><div class="grow"><div class="fh-recent" aria-label="Các số vừa gọi">${recent}</div><small>${me} ${esc(modeLabel(v.mode||'thuong'))} · đã gọi ${S.lt.shown}/90 · ván phút ${esc(v.minute)}${v.prize?` · hũ ${xu(v.prize)}`:''}</small></div></div>
    ${boardHtml(v)}
    <div class="fh-rivals" aria-label="Người chơi khác">${rivals}</div>
    ${cardsHtml(v)}
    <div class="fh-go"><span class="fh-speed" role="group" aria-label="Tốc độ gọi số">${speed}</span>${btn('📣 Kinh!','kinh',{},'primary big fh-kinh',S.lt.claiming?' disabled data-fh-key="kinh"':' data-fh-key="kinh"')}</div>
    ${hut?`<p class="fh-hutline">🙈 Kinh hụt ${hut}${v.hut_max?`/${v.hut_max}`:' lần'}${S.lt.hut?.fine?` · đã bỏ ${xu(S.lt.hut.fine)} vô hũ phạt`:''}</p>`:''}
    <div class="fh-go">${musicBtn()}</div>
    <p class="fh-rule">Tự chạm số cô Bảy vừa hô trên tờ của bạn. Đủ ${need(v)===1?'một hàng ngang':need(v)===2?'hai hàng ngang trên một tờ':'cả tờ'} thì bấm “Kinh!” trước người khác. Kinh hụt chỉ bị phạt nhẹ, dò lại rồi hô tiếp nha!</p></section>`;
}

/* ---- actions ---- */
async function buy(){
  if(S.busy)return;
  const g=G(),lt=S.lt;
  const mode=curMode();
  const p=g?{tier:lt.tier,n:lt.n,...(mode?{mode}:{}),...(lt.cl?{cl:[lt.cl,lt.cls]}:{}),...(lt.cot!=null?{cot:[lt.cot,lt.cots]}:{})}:{};
  S.busy=true;S.flash=null;render();
  const r=await send('fair_loto_buy',p);S.busy=false;
  if(r?.fair){S.lt.id=null;S.lt.hot=false;syncLoto();S.lt.say=MC.ready;react('👏',3);}
  else if(S.err==='fair_loto_mode')await S.env.api.refresh().catch(()=>{/* the next state */});   // the vòng changed meanwhile
  render();resumeLoto();
}
async function kinh(){
  const v=L();if(!playing(v)||S.lt.claiming)return;
  let p;
  if(!G()){   // the older server: a full row of the first card, by the player's own marks
    const m=new Set(S.lt.marks[0]||[]),row=v.card.findIndex(r=>r.every(n=>m.has(n)));
    if(row<0){S.flash={text:'Hàng nào đủ 5 số mới kinh được nha!',kind:'warn'};render();return;}
    p={row,at:S.lt.shown};
  }else{const ci=bestCard(v);p={card:ci,at:S.lt.shown,marks:[...(S.lt.marks[ci]||[])]};}
  S.lt.claiming=true;pauseLoto();render();
  const r=await send('fair_loto_kinh',p);
  S.lt.claiming=false;
  const x=r?.fair;
  if(x?.won){S.lt.won={prize:x.prize,mode:x.mode||v.mode,titles:x.titles||[],points:x.points||0};S.lt.say=pick(MC.win);sfx('kinh');react('🎉',4);react('👏',3);titles(x);}
  else if(x?.hut){S.lt.hut={...x};S.lt.say=pick(MC.hut);sfx('lose');react('😂',4);
    if(x.out){S.lt.over={by:v.npc_name,out:true};}}
  else if(x){S.lt.over={by:x.by||v.npc_name,mine:!x.late};S.lt.say=pick(MC.lose).replace('{who}',x.by||v.npc_name);sfx('lose');}
  saveLoto();render();
  if(!S.lt.over&&!S.lt.won)resumeLoto();
}
function mark(ci,n){
  const v=L();if(!playing(v))return;
  if(!calledSet(v).has(n)){S.flash={text:v.mode==='nguoc'?`Số ${n} chưa gọi đâu. Vòng lật ngược nhớ lật số lại nha!`:`Số ${n} chưa gọi đâu, đợi cô Bảy hô nha!`,kind:'warn'};render();return;}
  const list=S.lt.marks[ci]||(S.lt.marks[ci]=[]);
  const i=list.indexOf(n);if(i>=0)list.splice(i,1);else list.push(n);
  S.flash=null;sfx('mark');saveLoto();render();
}

/* ---- 🎯 Phóng phi tiêu: ./fair-darts.js (set up on first use, with this file's helpers) ---- */
let DT=null;
const dt=()=>DT??=dartsSetup({S,F,btn,say,xu,esc,send,render,sfx,pick,reduce,titles});

/* ---- 🏆 Bảng vàng ---- */
async function loadBoard(force=false){
  const ed=F().board;if(!ed||S.board.loading)return;
  if(!force&&S.board.data?.board===ed&&Date.now()-S.board.at<15000)return;
  S.board.loading=true;
  try{S.board.data=await S.env.api.json(`/api/leaderboard?board=${encodeURIComponent(ed)}&limit=20`);S.board.at=Date.now();S.board.error='';}
  catch(e){S.board.error=e.message||'Chưa tải được bảng vàng.';}
  finally{S.board.loading=false;if(S.dlg?.open&&S.tab==='board'&&!animating())render();}
}
function boardView(){
  const f=F(),p=f.points||{},B=S.board.data,fair=B?.fair,me=B?.me;
  const tiers=(fair?.tiers||[{label:'Top 1',emoji:'👑',name:'Vua trò chơi'},{label:'Top 2–10',emoji:'🎪',name:'Cao thủ hội chợ'}]).map(t=>`<li><span aria-hidden="true">${esc(t.emoji)}</span><b>${esc(t.name)}</b><small>${esc(t.label)}</small></li>`).join('');
  const rules=p.rules||{day:1,bc:1,xd:1,loto:3,oaq:3,ring3:1,ring5:2};
  const won=fair?.winners?.length?`<div class="fh-card fh-crowned"><h3>Hội đã tàn · Bảng vàng chung cuộc</h3><ol>${fair.winners.map(w=>`<li class="${w.me?'me':''}"><span aria-hidden="true">${esc(w.emoji)}</span><b>${esc(w.name)}</b><small>${esc(w.title)} · ${fmt(w.score)} điểm</small></li>`).join('')}</ol></div>`:'';
  const rows=B?.rows?.length?`<ol class="fh-board">${B.rows.map(r=>`<li class="${r.me?'me':''}${r.rank===1?' first':''}"><span class="fh-rank">${r.rank===1?'👑':r.rank<=10?'🎪':r.rank}</span><span class="grow"><b>${esc(r.name||'')}</b>${r.guest?'<em class="fh-guest">khách</em>':''}<small>${fmt(r.days)} ngày chơi</small></span><b class="fh-score">${fmt(r.points??r.score)}</b></li>`).join('')}</ol>`
    :S.board.loading||!B?'<p class="muted fh-wait">Đang mở Bảng vàng…</p>':'<p class="muted fh-wait">Chưa ai có điểm. Chơi một ván là có tên trên bảng!</p>';
  const mine=me?`<div class="fh-me"><span>Bạn: <b>${fmt(p.total)}</b> điểm${me.rank&&me.visible!==false?` · hạng <b>${fmt(me.rank)}</b>`:''}</span>${f.open&&p.cap?`<small>Hôm nay ${fmt(p.today)}/${fmt(p.cap)} điểm</small>`:''}${me.visible===false?`<small class="fh-hidden">Tên bạn đang ẩn nên chưa lên bảng và chưa nhận được danh hiệu. Bật “Hiện tên tôi” ở Xếp hạng nhé.</small>`:''}</div>`:'';
  return `<section class="fh-stall fh-gold" aria-label="Bảng vàng hội chợ">
    <div class="fh-card fh-crown"><h3>🏆 Bảng vàng hội chợ</h3><ul class="fh-tiers">${tiers}</ul><p class="small">${f.over?'Danh hiệu đã trao khi hội tàn.':`Trao khi hội tàn (${esc(dateOf(f.closes))} 00:00), giữ mãi trong bộ sưu tập.`}</p></div>
    ${won}${mine}${S.board.error?`<p class="fh-flash bad">${esc(S.board.error)}</p>`:''}${rows}
    <details class="fh-how"><summary>Cách tính điểm</summary><ul><li>Mỗi ngày ghé hội chơi: +${rules.day}</li><li>Thắng một ván ô ăn quan: +${rules.oaq}</li><li>Ném vòng trúng từ 3 chai: +${rules.ring3}, đủ 5 chai: +${rules.ring5}</li><li>Ván bầu cua có con trùng mặt đặt: +${rules.bc}</li><li>Thắng một ván chiếu trong: +${rules.xd} (bị công an kiểm tra: 0)</li><li>Kinh thắng một ván lô tô: +${rules.loto}</li>${rules.dt?`<li>Phóng phi tiêu trúng vòng màu: +${rules.dt} mỗi phát</li>`:''}${p.cap?`<li>Tối đa ${fmt(p.cap)} điểm mỗi ngày.</li>`:''}<li>Bằng điểm thì ai đạt trước đứng trên.</li></ul><p class="small muted">Điểm tính theo lượt chơi, không theo số xu thắng, nên cược nhỏ cũng lên bảng được.</p></details>
  </section>`;
}


/* ---- 🎁 Tiền vốn hội chợ and 💸 Vay nóng (game/fair_cash.py; an older server sends no `cash`: nothing shows) ---- */
const C=()=>F().cash||null;
async function claimGift(){
  const c=C();if(!c?.gift_ready||!F().open||S.gifting)return;
  S.gifting=true;
  const r=await send('fair_gift',{});S.gifting=false;
  if(r?.fair?.gift){S.gift=r.fair.gift;S.flash=null;sfx('win');render();S.dlg?.querySelector('[data-fh="giftok"]')?.focus({preventScroll:true});}
  else{S.flash=null;render();}   // already claimed (another tab): nothing to say
}
function giftPop(){
  if(!S.gift)return '';
  return `<div class="fh-giftpop" role="dialog" aria-modal="true" aria-labelledby="fh-gift-h"><div class="fh-giftcard">
    <div class="fh-giftbox" aria-hidden="true">🎁</div><h3 id="fh-gift-h">Ban tổ chức tặng ${xu(S.gift)} làm vốn chơi hội!</h3>
    <p>Đã bỏ vô ví của bạn. Chúc bà con chơi hội vui vẻ, ăn nhiều nha!</p>${btn('🏮 Vào hội','giftok',{},'primary big full',' data-fh-key="giftok"')}</div></div>`;
}
function loanRow(){
  const c=C();if(!c)return '';
  const owe=(c.loan?.due||0)+(c.debt||0);
  return `<button type="button" class="fh-goldlink fh-loanlink" data-fh="tab" data-tab="loan" data-fh-key="g-loan"><span aria-hidden="true">💸</span><span class="grow"><b>${esc(c.lender)}</b><small>${owe?`Đang nợ <b>${xu(owe)}</b> · trả lúc nào cũng được`:`Vay nhanh ${xu(c.steps[0])}–${xu(c.steps[c.steps.length-1])}, lãi ${c.rate}%`}</small></span><span aria-hidden="true">›</span></button>`;
}
function loanView(){
  const c=C(),f=F();
  if(!c)return homeView();
  const who={name:c.lender,emoji:'👵'},owe=(c.loan?.due||0)+(c.debt||0),L0=S.loan;
  if(owe){
    const short=(f.wallet||0)<owe;
    return `<section class="fh-stall fh-loan" aria-label="Vay nóng">
      ${say(who,short?'Chưa đủ thì cứ chơi tiếp, có đủ rồi ghé trả bà nha.':'Có tiền rồi hả? Trả bà là xong, vay tiếp lúc nào cũng được.')}
      <div class="fh-card fh-loancard"><h3>Đang nợ ${xu(owe)}</h3>${c.loan?`<p>Vay ${xu(c.loan.p)}, lãi ${c.rate}%: trả ${xu(c.loan.due)}.</p>`:''}${c.debt?`<p>Nợ còn lại từ lần hội trước: ${xu(c.debt)} (tự trừ dần khi có tiền vào ví).</p>`:''}
      ${btn(S.busy?'Đang trả…':`💸 Trả hết ${xu(owe)}`,'repay',{},'primary big full',short||S.busy?' disabled data-fh-key="repay"':' data-fh-key="repay"')}
      ${short?`<p class="fh-why">Ví đang có ${xu(f.wallet||0)}, cần đủ ${xu(owe)} để trả hết.</p>`:''}</div>
      <p class="fh-rule">Hội tàn mà chưa trả thì bà tự thu: lấy tiền trong ví trước, thiếu thì lấy từ tài khoản ngân hàng, vẫn thiếu thì trừ dần khi bạn có tiền vào ví. Ví không bao giờ bị âm.</p>
    </section>`;
  }
  const amt=c.steps.includes(L0.amt)?L0.amt:c.steps[1]||c.steps[0],due=Math.ceil(amt*(100+c.rate)/100);
  return `<section class="fh-stall fh-loan" aria-label="Vay nóng">
    ${say(who,'Thiếu vốn chơi hội hả con? Bà cho vay liền, lãi hai chục phần trăm thôi, trả lúc nào cũng được.')}
    <div class="fh-card fh-loancard"><h3>💸 Vay nóng hội chợ</h3>
      <div class="fh-chips" role="group" aria-label="Số tiền vay"><span>Vay</span>${c.steps.map(v=>`<button type="button" class="fh-chip${amt===v?' on':''}" data-fh="loanamt" data-v="${v}" aria-pressed="${amt===v}" data-fh-key="loan-${v}">${v}</button>`).join('')}</div>
      <p class="fh-loansum">Nhận <b>${xu(amt)}</b> · trả lại <b>${xu(due)}</b> <small>(lãi ${c.rate}%)</small></p>
      ${btn(S.busy?'Đang đếm tiền…':L0.sure?`Chắc chưa? Vay ${xu(amt)}, trả ${xu(due)}`:`Vay ${xu(amt)}`,'borrow',{},'primary big full'+(L0.sure?' danger':''),!f.open||S.busy?' disabled data-fh-key="borrow"':' data-fh-key="borrow"')}
    </div>
    <p class="fh-rule">Mỗi lần một khoản. Trả hết lúc nào cũng được ngay tại đây. Hội tàn mà chưa trả thì bà tự thu từ ví, rồi tài khoản ngân hàng; còn thiếu thì trừ dần khi có tiền vào ví.</p>
  </section>`;
}
async function borrow(){
  const c=C();if(!c||S.busy)return;
  const amt=c.steps.includes(S.loan.amt)?S.loan.amt:c.steps[1]||c.steps[0];
  if(!S.loan.sure){S.loan.sure=true;render();return;}
  S.busy=true;S.loan.sure=false;S.flash=null;render();
  const r=await send('fair_borrow',{amount:amt});S.busy=false;
  if(r?.fair?.borrowed){S.flash={text:`Đã vay ${xu(r.fair.borrowed)}, nhớ trả ${xu(r.fair.due)} nha.`,kind:'good'};sfx('open');}
  render();
}
async function repay(){
  if(S.busy)return;
  S.busy=true;S.flash=null;render();
  const r=await send('fair_repay',{});S.busy=false;
  if(r?.fair?.repaid){S.flash={text:`Đã trả ${xu(r.fair.repaid)}, hết nợ rồi!`,kind:'good'};sfx('win');}
  render();
}

/* ---- clicks ---- */
async function onClick(op,data){
  const b=S.bc,x=S.xd;
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;S.anchor='';if(S.tab!=='lt'){pauseLoto();ltMusic();}render();S.dlg.scrollTop=0;if(S.tab==='board')loadBoard();if(S.tab==='lt')resumeLoto();if(S.tab==='ring')startRingLoop();if(S.tab==='dt')dt().start();return;
    case'oaqstart':oaqStart(data.lv==='kho'?'kho':'de');return;
    case'oaqsel':{if(S.oaq.anim||S.busy)return;const c=Number(data.c);S.oaq.sel=S.oaq.sel===c?null:c;S.oaq.quit=false;sfx('mark');render();return;}   // owner 03/10: change or unpick the ô freely until a direction is chosen
    case'oaqmove':oaqMove(Number(data.d)===-1?-1:1);return;
    case'oaqfast':S.oaq.fast=!S.oaq.fast;render();return;
    case'oaqquit':{if(!S.oaq.quit){S.oaq.quit=true;render();return;}
      S.oaq.quit=false;S.busy=true;render();const r=await send('fair_oaq_quit',{});S.busy=false;
      if(r){S.oaq.end=null;S.oaq.showEnd=false;S.oaq.sel=null;S.oaq.say='';}render();return;}
    case'ringstart':ringStart();return;
    case'throw':ringThrow();return;
    case'chip':b.chip=Number(data.v)||1;render();return;
    case'bet':{if(b.phase!=='idle')return;const c=bcCap(),room=c.cap-bcTotal();
      if(room<=0){S.flash={text:c.cap<c.max?(c.left<=c.wallet?`Hôm nay chỉ còn chơi được ${xu(c.left)} thôi nha.`:`Ví chỉ còn ${xu(c.wallet)} thôi nha.`):`Mỗi ván đặt tối đa ${c.max} xu thôi nha.`,kind:'warn'};render();return;}
      const add=Math.min(b.chip,room);b.bets={...b.bets,[data.face]:(b.bets[data.face]||0)+add};b.last=null;S.flash=null;sfx('mark');render();return;}
    case'clear':b.bets={};b.last=null;render();return;
    case'roll':roll();return;
    case'side':x.side=data.v==='le'?'le':'chan';render();return;
    case'stake':x.stake=Number(data.v)||10;render();return;
    case'shakexd':shakeXd();return;
    case'raidok':x.raid=null;S.tab=data.tab||'bc';render();S.dlg.scrollTop=0;if(S.tab==='lt')resumeLoto();return;
    case'buy':buy();return;
    case'mark':mark(Number(data.c)||0,Number(data.n));return;
    case'kinh':kinh();return;
    case'ltspeed':S.lt.speed=Math.max(0,Math.min(2,Number(data.v)||0));render();if(S.lt.timer){pauseLoto();resumeLoto();}return;
    case'lttier':if(G()?.tiers?.[data.v])S.lt.tier=data.v;render();return;
    case'ltn':S.lt.n=Math.max(1,Math.min(G()?.cards||1,Number(data.v)||1));render();return;
    case'ltcl':S.lt.cl=data.v==='chan'||data.v==='le'?data.v:null;render();return;
    case'ltcot':{const c=data.v===''?null:Number(data.v);S.lt.cot=Number.isInteger(c)&&c>=0&&c<=8?c:null;render();return;}
    case'ltcls':S.lt.cls=Number(data.v)||2;render();return;
    case'ltcots':S.lt.cots=Number(data.v)||2;render();return;
    case'ltcheck':S.lt.check=!S.lt.check;render();return;
    case'giftok':S.gift=null;render();return;
    case'loanamt':S.loan.amt=Number(data.v)||0;S.loan.sure=false;render();return;
    case'borrow':borrow();return;
    case'repay':repay();return;
    case'ltmusic':{const on=!musicPref();try{localStorage.setItem(LT_MUSIC,on?'1':'0');}catch{/* storage blocked */}ltMusic();render();return;}
    default:if(op.startsWith('dt'))dt().click(op,data);
  }
}
