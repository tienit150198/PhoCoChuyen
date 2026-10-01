/** 🏮 Hội chợ dân gian: the gate (Cổng hội) puts the earn-xu stalls first (ô ăn quan against a neighbour, ném vòng
 * cổ chai), then the small-stake ones (bầu cua tôm cá, lô tô, the back corner's xóc đĩa and Công an phường), the Bảng vàng.
 * Every rule, result and number is the server's (game/fair*.py): this file renders
 * api.state.fair, sends `fair_*` commands and plays the show around their results (the bowl shaking, the lô tô
 * caller's rhymes, the raid). The lô tô calls of a round come with the state; the caller reads them out at the
 * player's pace (paused while the stall is not on screen) and "Kinh!" is checked by the server against those calls.
 * Its own dialog (like the bank), opened with data-action="fair" (Khu phố hub, the journey banner).
 * Styles: /css/fair.css. Sounds: tiny Web Audio synths (no recordings), off when the game's sound is off. */
import {icon,escapeHTML as esc} from '../icons.js';
import {audioContext} from '../audio.js';
import {language} from './i18n.js';

const FACES=['bau','cua','tom','ca','ga','nai'];
const FACE_NAME={bau:'Bầu',cua:'Cua',tom:'Tôm',ca:'Cá',ga:'Gà',nai:'Nai'};
const GOURD='<svg class="fh-gourd" viewBox="0 0 40 48" aria-hidden="true"><path d="M20 4c1.2 0 2 .9 2 2v3.4c2.9 1 4.8 3.6 4.8 6.6 0 1.8-.6 3.4-1.7 4.7C31 22.8 35 27.6 35 33.5 35 41.2 28.3 46 20 46S5 41.2 5 33.5c0-5.9 4-10.7 9.9-12.8-1.1-1.3-1.7-2.9-1.7-4.7 0-3 1.9-5.6 4.8-6.6V6c0-1.1.8-2 2-2z" fill="#86b84a" stroke="#3f6b1d" stroke-width="2"/><path d="M21 6.5c2.6-2.4 6.6-2.6 9.2-.6" fill="none" stroke="#3f6b1d" stroke-width="2" stroke-linecap="round"/><path d="M13 31c1.5-3 4-4.6 7-5" fill="none" stroke="#e9f5d3" stroke-width="2.4" stroke-linecap="round" opacity=".8"/></svg>';
const FACE_ART={bau:GOURD,cua:'🦀',tom:'🦐',ca:'🐟',ga:'🐓',nai:'🦌'};
const art=f=>`<span class="fh-art" aria-hidden="true">${FACE_ART[f]||'❔'}</span>`;
const TITLE_NAMES={f_loto:'🎱 Thần lô tô hội chợ',f_bao:'🌪️ Trúng bão bầu cua',f_raid:'🚨 Bị công an hỏi thăm',f_oaq:'🪨 Cao tay ô ăn quan',f_ring:'💍 Tay ném vòng thần sầu'};
const GAMES={home:['🏮','Cổng hội'],oaq:['🪨','Ô ăn quan'],ring:['💍','Ném vòng cổ chai'],bc:['🦀','Bầu cua'],lt:['🎱','Lô tô'],xd:['🕯️','Chiếu trong'],board:['🏆','Bảng vàng']};
const MINI_BOARD='<svg viewBox="0 0 64 40" aria-hidden="true"><rect x="2" y="6" width="60" height="28" rx="14" fill="#e9c98f" stroke="#8a5a26" stroke-width="2"/><path d="M14 6v28M50 6v28M14 20h36M23 6v28M32 6v28M41 6v28" stroke="#8a5a26" stroke-width="1.6"/><circle cx="8" cy="20" r="4" fill="#5b4636"/><circle cx="56" cy="20" r="4" fill="#5b4636"/><g fill="#7a8b99"><circle cx="18" cy="13" r="1.8"/><circle cx="27" cy="27" r="1.8"/><circle cx="36" cy="13" r="1.8"/><circle cx="45" cy="27" r="1.8"/><circle cx="20" cy="28" r="1.8"/><circle cx="38" cy="25" r="1.8"/></g></svg>';
const MINI_BOTTLES='<svg viewBox="0 0 64 40" aria-hidden="true"><g stroke="#2d5a3d" stroke-width="1.4"><path d="M12 38V22c0-4 4-5 4-9V5h4v8c0 4 4 5 4 9v16z" fill="#7cc79a"/><path d="M28 38V22c0-4 4-5 4-9V5h4v8c0 4 4 5 4 9v16z" fill="#8fb6e8"/><path d="M44 38V22c0-4 4-5 4-9V5h4v8c0 4 4 5 4 9v16z" fill="#f0b46a"/></g><ellipse cx="34" cy="10" rx="7" ry="2.6" fill="none" stroke="#e2462d" stroke-width="2.4"/></svg>';
const CHIPS=[1,2,5,10];
const XD_STAKES=[10,20,30,50];
const CALL_MS=2300,FAST_MS=1100,NPC_GRACE=2000,ROLL_MS=1400;
const LS='mnl.fair.lt';

/* ---- the people of the fair ---- */
const DEALER={name:'Chú Tám bầu cua',emoji:'🧔🏻',idle:['Bầu cua cá cọp đây, đặt đi bà con ơi!','Đặt lẹ đặt lẹ, chú lắc liền nè!','Ai chơi thì đặt, ai coi thì vỗ tay cho vui nha!','Con gì cũng có, ván nào cũng vui!']};
const CALLER={name:'Cô Út lô tô',emoji:'💃🏻'};
const HOST={name:'Anh Ba chiếu trong',emoji:'🕶️',idle:['Chơi lớn không? Chẵn lẻ, ăn một trả một.','Nói nhỏ thôi… ngó chừng phía ngoài giùm anh.','Xóc nè, xóc nè! Chẵn hay lẻ, đặt đi!']};
const RINGER={name:'Cô Tư ném vòng',emoji:'👩🏻',idle:['Ném vòng cổ chai đây! Không mất xu, trúng là có quà!','Canh cho kỹ, vòng ngay miệng chai thì ném!','Mỗi lượt năm cái vòng, ném trúng chai nào ăn chai đó!'],
  hit:['Trúng rồi! Tay ném chắc ghê!','Vô cổ chai luôn!','Đẹp! Thêm chai nữa nè!'],miss:['Hụt chút xíu!','Trật rồi, canh lại nha!','Ui, vòng nảy ra mất!']};
const OPP={de:{start:['Chơi với em nha! Anh chị đi trước đi.','Em mới tập chơi, nương tay giùm em nha!'],think:['Để em đếm coi…','Ô này nè… hông, ô kia!','Em rải bên này nha!'],
    cap:['Hihi, em ăn được rồi!','Ăn rồi nha!'],lose:['Ui da, mất quân rồi.','Ăn của em nhiều quá trời!'],won:['Em thắng rồi! Chơi ván nữa hông?'],lost:['Anh chị giỏi quá! Chơi lại ván nữa nha!'],draw:['Huề rồi! Ván sau phân thắng thua nha!']},
  kho:{start:['Ông chơi ô ăn quan từ hồi còn để chỏm. Mời cháu đi trước.','Bàn bày rồi, cháu đi trước đi.'],think:['Hừm… để ông tính.','Đi nước này coi sao.','Cháu coi kỹ nè.'],
    cap:['Quân này ông xin nha.','Ăn liên tiếp mới vui!'],lose:['Nước này cháu tính hay đó.','Khá lắm, khá lắm.'],won:['Ván này ông thắng, cháu tập thêm rồi ghé nha.'],lost:['Cháu cao tay thiệt! Ông chịu thua ván này.'],draw:['Huề! Ông cháu mình ngang tay.']}};

/* ---- lô tô calls: folk-style rhymes written for the game, the number at the rhyme ---- */
const UNITS=['','một','hai','ba','bốn','năm','sáu','bảy','tám','chín'];
function words(n){
  if(n<10)return UNITS[n];
  const t=Math.floor(n/10),u=n%10,head=t===1?'mười':UNITS[t]+' mươi';
  if(!u)return head;
  const tail=u===1&&t>1?'mốt':u===4&&t>1?'tư':u===5?'lăm':UNITS[u];
  return head+' '+tail;
}
const RHYME={
  mot:['Nắng lên ruộng lúa xanh tươi tốt, ra con số {w}!','Bánh xèo đổ chảo thơm lừng mùi bột, ra con số {w}!'],
  hai:['Cây cau trước ngõ thẳng hàng dài, ra con số {w}!','Gánh hàng rong đi khắp phố dài, chờ hoài mới thấy {w}!'],
  ba:['Hội chợ đông vui khắp xóm gần xa, mời bà con dò số {w}!','Bánh tráng phơi nắng trước hiên nhà, ra con số {w}!'],
  bon:['Trẻ con chạy giỡn lòng bồn chồn, ra con số {w}!','Thuyền ai xuôi nước chảy bon bon, ra con số {w}!'],
  tu:['Nhớ ai mà viết lá thư, ra con số {w}!','Ngồi dò cho kỹ chớ có chần chừ, ra con số {w}!'],
  nam:['Ai đi xa nhớ ghé về thăm, ra con số {w}!','Đêm nay trăng sáng như rằm, ra con số {w}!'],
  sau:['Hai đứa mình đi hội cùng nhau, ra con số {w}!','Miếng trầu têm với quả cau, ra con số {w}!'],
  bay:['Hội chợ vui quá, vỗ tay vỗ tay, ra con số {w}!','Cánh diều no gió tung bay, ra con số {w}!'],
  tam:['Ai ăn quýt ngọt, ai ăn cam, ra con số {w}!','Áo ai phơi nắng màu lam, ra con số {w}!'],
  chin:['Đứng đây mà ngó mà nhìn, ra con số {w}!','Lời thương nhắn gửi ai tin, ra con số {w}!'],
  muoi:['Cô hàng nước miệng cười tươi, ra con số {w}!','Cả phố đi hội vui tươi, ra con số {w}!'],
};
const END={một:'mot',mốt:'mot',hai:'hai',ba:'ba',bốn:'bon',tư:'tu',năm:'nam',lăm:'nam',sáu:'sau',bảy:'bay',tám:'tam',chín:'chin',mười:'muoi',mươi:'muoi'};
const SPECIAL={1:'Mở hàng con số đầu dàn: số một!',90:'Lớn nhất cả dàn: chín mươi!',45:'Bốn mươi lăm, ai chờ thì dò cho kỹ, bốn mươi lăm!'};
/** The line for a number: the same for everyone in the same minute (slot). */
function callLine(n,slot){
  if(language()==='en')return `Number ${n}!`;
  if(SPECIAL[n]&&(slot+n)%2===0)return SPECIAL[n];
  const w=words(n),lines=RHYME[END[w.split(' ').pop()]]||RHYME.muoi;
  return lines[(slot*7+n)%lines.length].replace('{w}',w);
}

/* ---- state ---- */
const S={dlg:null,env:null,tab:'home',busy:false,flash:null,skew:0,listening:false,tick:null,
  oaq:{sel:null,anim:null,say:'',fast:false,quit:false,end:null,showEnd:false},
  ring:{round:null,t0:0,taps:[],hits:[],raf:0,result:null,say:''},
  bc:{chip:1,bets:{},phase:'idle',dice:null,last:null,say:''},
  xd:{side:'chan',stake:10,phase:'idle',coins:null,last:null,raid:null,say:''},
  lt:{id:null,shown:0,marks:[],timer:null,fast:false,over:null,won:null,claiming:false,npcAt:0},
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
  d.innerHTML='<div class="fh-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-fh]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.fh,el.dataset,el);
  });
  d.addEventListener('close',()=>{pauseLoto();stopRing();clearInterval(S.tick);S.tick=null;S.flash=null;});
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
  clearInterval(S.tick);S.tick=setInterval(tickLabels,1000);
  if(S.tab==='board')loadBoard();
  if(S.tab==='lt')resumeLoto();
  if(S.tab==='ring')startRingLoop();
}
export async function fairAction(action,data,el,env){
  if(action!=='fair')return false;
  await openFair(env,data);return true;
}
const animating=()=>S.bc.phase!=='idle'||S.xd.phase!=='idle'||S.busy||!!S.oaq.anim||S.ring.taps.length>0&&!S.ring.result;

async function send(action,payload={}){
  const {api}=S.env;
  try{return await api.command(action,payload);}
  catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
}

/* ---- rendering ---- */
function keep(fn){
  const body=S.dlg?.querySelector('.fh-body'),top=body?.scrollTop,a=document.activeElement,key=a&&S.dlg?.contains(a)?a.dataset.fhKey:'';
  fn();
  const nb=S.dlg?.querySelector('.fh-body');if(nb&&top!=null)nb.scrollTop=top;
  if(key){const el=S.dlg.querySelector(`[data-fh-key="${CSS.escape(key)}"]`);el?.focus({preventScroll:true});}
}
function render(){
  if(!S.dlg)return;
  keep(()=>{S.dlg.querySelector('.fh-root').innerHTML=page();});
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function tickLabels(){
  if(!S.dlg?.open)return;
  const f=F();
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
  return `<div class="fh-strip" role="status"><span>👛 <b>${xu(f.wallet)}</b></span><span>💰 Hôm nay kiếm <b>${xu(got)}</b></span><button type="button" class="fh-pts" data-fh="tab" data-tab="board" data-fh-key="pts">🏆 <b>${fmt(p.total)}</b> điểm</button></div>`;
}
/** Inside a stall: the way back to the gate. */
function nav(){
  if(S.tab==='home')return '';
  const [e,l]=GAMES[S.tab]||GAMES.home;
  return `<nav class="fh-nav" aria-label="Hội chợ">${btn('<span aria-hidden="true">‹</span> Cổng hội','tab',{tab:'home'},'ghost small fh-back',' data-fh-key="home"')}<b><span aria-hidden="true">${e}</span> ${esc(l)}</b></nav>`;
}
/** The small-stake stalls: what is left of today's loss cap. */
const luckLine=()=>{const t=F().today||{};return `<p class="fh-luck-left">🎟️ Thử vận hôm nay còn chơi được <b>${xu(t.left)}</b> <small>(thua tối đa ${xu(R().cap)} mỗi ngày)</small></p>`;};
const flash=()=>`<p class="fh-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
const note=()=>`<p class="fh-note">🎪 Trò chơi dân gian ở hội chợ, chơi bằng xu trong game. Không có tiền thật.</p>`;
function page(){
  const f=F();
  if(!f.show&&!f.over&&!f.soon)return head()+`<div class="sheet-body fh-body">${closedCard(true)}</div>`;
  if(!f.open&&S.tab!=='board')return head()+`<div class="sheet-body fh-body">${closedCard()}${S.env?.api?.state?.journey?.story?btn('🏆 Xem Bảng vàng hội chợ','tab',{tab:'board'},'cream full'):''}${note()}</div>`;
  const views={home:homeView,oaq:oaqView,ring:ringView,bc:bcView,lt:lotoView,xd:xdView,board:boardView};
  const body=(views[S.tab]||homeView)(),luck=['bc','lt','xd'].includes(S.tab);
  return head()+`<div class="sheet-body fh-body">${f.open?strip():''}${f.open?nav():''}${flash()}${f.open&&luck&&f.today?.done?enoughCard():''}${f.open&&luck&&!f.today?.done?luckLine():''}${body}${note()}</div>`;
}
function closedCard(gone){
  const f=F();
  if(f.soon)return `<section class="fh-card fh-closed"><div class="fh-big" aria-hidden="true">🏮</div><h3>Hội chợ sắp mở</h3><p>Khai hội ngày ${esc(dateOf(f.opens))}, mở ${Math.round((f.closes-f.opens)/86400)} ngày. Hẹn bà con ghé chơi ô ăn quan, ném vòng, bầu cua, lô tô nha!</p></section>`;
  return `<section class="fh-card fh-closed"><div class="fh-big" aria-hidden="true">🎐</div><h3>Hội chợ đã tàn, hẹn lần sau</h3><p>${gone?'Lều bạt đã dọn, đèn lồng đã cất.':'Cảm ơn bà con đã ghé hội. Bảng vàng vẫn còn đó để xem lại.'}</p></section>`;
}
const enoughCard=()=>`<section class="fh-card fh-enough"><span aria-hidden="true">🍵</span><div><b>Hôm nay chơi vậy đủ rồi, mai ghé tiếp nha.</b><small>Mỗi ngày thua tối đa ${xu(R().cap)}. Qua chơi ô ăn quan, ném vòng kiếm xu, hoặc ghé xem Bảng vàng nhé.</small></div></section>`;
const say=(who,text,cls='')=>`<div class="fh-npcline ${cls}"><span class="fh-npc" aria-hidden="true">${who.emoji}</span><div class="fh-bubble"><small>${esc(who.name)}</small><p>${esc(text)}</p></div></div>`;

/* ---- 🏮 Cổng hội: the earn-xu stalls first, then the small-stake ones ---- */
const meter=(e,label='Hôm nay đã kiếm')=>{e=e||{today:0,cap:1};const pct=Math.min(100,Math.round(e.today/Math.max(1,e.cap)*100));
  return `<span class="fh-meter${e.today>=e.cap?' full':''}" aria-hidden="true"><i style="width:${pct}%"></i></span><small class="fh-meterlabel">${e.today>=e.cap?'Hôm nay đã kiếm đủ':label} <b>${fmt(e.today)}</b>/${xu(e.cap)}</small>`;};
function homeView(){
  const f=F(),r=R(),e=f.earn||{},o=f.oaq,p=f.points||{},pr=r.oaq_prize||{de:15,kho:30};
  const oaqLine=o?.stage==='play'?`<em class="fh-live">Đang chơi dở với ${esc(o.name)} · chơi tiếp</em>`:`Đấu với Bé Bi (thắng +${pr.de} xu) hoặc Ông Hai (thắng +${pr.kho} xu)`;
  const luck=(id,ico,name,sub,warn='')=>`<button type="button" class="fh-luckgame" data-fh="tab" data-tab="${id}" data-fh-key="g-${id}"><span class="fh-lico" aria-hidden="true">${ico}</span><span class="grow"><b>${name}</b><small>${sub}</small></span>${warn}${f.loto?.stage==='play'&&id==='lt'?'<i class="fh-dot" aria-label="đang chơi"></i>':''}</button>`;
  return `<section class="fh-gate" aria-label="Cổng hội">
    <div class="fh-sec"><h3>💰 Chơi kiếm xu</h3><span class="fh-tag good">Không cần đặt cược</span></div>
    <div class="fh-earn">
      <button type="button" class="fh-game" data-fh="tab" data-tab="oaq" data-fh-key="g-oaq"><span class="fh-gico">${MINI_BOARD}</span><span class="grow"><b>Ô ăn quan</b><small>${oaqLine}</small>${meter(e.oaq)}</span></button>
      <button type="button" class="fh-game" data-fh="tab" data-tab="ring" data-fh-key="g-ring"><span class="fh-gico">${MINI_BOTTLES}</span><span class="grow"><b>Ném vòng cổ chai</b><small>Trúng mỗi chai +${r.ring_hit||2} xu, đủ ${r.rings||5} chai thêm ${r.ring_all||5} xu</small>${meter(e.ring)}</span></button>
    </div>
    <div class="fh-sec"><h3>🎲 Thử vận may</h3><span class="fh-tag">Cược nhỏ bằng xu</span></div>
    <div class="fh-luck">
      ${luck('bc',FACE_ART.cua,'Bầu cua',`Đặt 1–${r.bc_max||20} xu một ván`)}
      ${luck('lt','🎱','Lô tô',`Tờ dò ${xu(r.loto_price)}, kinh ăn ${xu(r.loto_prize)}`)}
      ${luck('xd','🕯️','Chiếu trong',`Cược ${r.xd_min}–${r.xd_max} xu`,'<span class="fh-warnchip">🚨 công an</span>')}
    </div>
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
    const opp=lv=>`<button type="button" class="fh-opp fh-opp-${lv}" data-fh="oaqstart" data-lv="${lv}" data-fh-key="opp-${lv}"${S.busy?' disabled':''}><span class="fh-npc" aria-hidden="true">${people[lv][1]}</span><b>${esc(people[lv][0])}</b><small>${lv==='de'?'Dễ':'Khó'} · thắng <b>+${xu(pr[lv])}</b></small></button>`;
    return `<section class="fh-stall fh-oaqstall" aria-label="Ô ăn quan">
      <div class="fh-card fh-oaqintro"><h3>🪨 Ô ăn quan</h3><p>Chọn người chơi cùng. Thắng thì được xu, thua không mất gì.</p><div class="fh-opps">${opp('de')}${opp('kho')}</div>${meter(e)}</div>
      ${how}<p class="fh-rule">Thắng một ván: +${(F().points?.rules||{}).oaq||3} điểm Bảng vàng. Mỗi ngày kiếm từ ô ăn quan tối đa ${xu(e?.cap||90)}.</p></section>`;
  }
  const a=S.oaq.anim,v=a||o,lines=OPP[o.lv]||OPP.de,who={name:o.name,emoji:o.emoji};
  if(!S.oaq.say)S.oaq.say=pick(lines.start);
  const me=a?a.cap[0]+10*a.cap[1]:o.me,opp=a?a.cap[2]+10*a.cap[3]:o.opp,cap=v.cap;
  const turn=a?(a.side===1?`${esc(o.name)} đang rải…`:'Bạn đang rải…'):o.stage==='play'?(S.oaq.sel!=null?'Chọn hướng rải':'Lượt của bạn: chạm một ô hàng dưới'):'';
  const hand=a&&a.hand>0?`<span class="fh-hand">✋ ${a.hand}</span>`:'';
  const dirs=S.oaq.sel!=null&&!a&&o.stage==='play'?`<div class="fh-dirs">${btn('◀ Rải sang trái','oaqmove',{d:-1},'primary',' data-fh-key="d-l"')}${btn('Rải sang phải ▶','oaqmove',{d:1},'primary',' data-fh-key="d-r"')}</div>`:'';
  const end=S.oaq.end&&o.stage!=='play'&&!a?oaqEnd(o):'';
  return `<section class="fh-stall fh-oaqstall" aria-label="Ô ăn quan">
    ${say(who,S.oaq.say)}
    <div class="fh-oscore"><span class="opp"><em>${esc(o.emoji)} ${esc(o.name)}</em><b>${opp}</b><small>${cap[2]} dân${cap[3]?` · ${cap[3]} quan`:''}</small></span><span class="me"><em>🙂 Bạn</em><b>${me}</b><small>${cap[0]} dân${cap[1]?` · ${cap[1]} quan`:''}</small></span></div>
    ${oaqBoard()}
    <div class="fh-oturn" aria-live="polite"><span>${turn}</span>${hand}</div>
    ${dirs}${end}
    <div class="fh-go">${btn(S.oaq.fast?'⏯️ Rải chậm':'⏩ Rải nhanh','oaqfast',{},'ghost small',' data-fh-key="oaqfast"')}${o.stage==='play'?btn(S.oaq.quit?'Chắc chưa? Bỏ ván':'Bỏ ván','oaqquit',{},'ghost small'+(S.oaq.quit?' danger':''),a?' disabled':' data-fh-key="oaqquit"'):''}</div>
    ${how}</section>`;
}
function oaqEnd(o){
  const x=S.oaq.end,people=R().oaq_people||{};
  const head=x.stage==='won'?`🎉 Bạn thắng ${x.me}–${x.opp}!`:x.stage==='draw'?`🤝 Huề ${x.me}–${x.opp}`:`Thua ${x.me}–${x.opp}, ván sau gỡ nha`;
  const pay=x.stage==='won'?(x.prize?`<p class="fh-prize">+${xu(x.prize)}${x.points?` · +${x.points} điểm hội chợ`:''}</p>`:`<p class="muted small">Hôm nay đã kiếm đủ xu từ ô ăn quan${x.points?`, vẫn được +${x.points} điểm hội chợ`:''}. Mai ghé tiếp nha!</p>`):'<p class="muted small">Thua không mất xu nào.</p>';
  const other=o.lv==='de'?'kho':'de';
  return `<div class="fh-card fh-oend ${x.stage}"><h3>${head}</h3>${pay}${x.titles?.includes('f_oaq')?'<p class="fh-award">🪨 Danh hiệu mới: <b>Cao tay ô ăn quan</b></p>':''}
    <div class="row wrap fh-oend-go">${btn(`Ván mới với ${esc(o.name)}`,'oaqstart',{lv:o.lv},'primary',' data-fh-key="again"')}${btn(`Chơi với ${esc((people[other]||[''])[0])}`,'oaqstart',{lv:other},'ghost')}</div></div>`;
}
const wait=ms=>new Promise(ok=>setTimeout(ok,reduce()?Math.min(ms,60):ms));
async function oaqStart(lv){
  if(S.busy)return;S.busy=true;S.flash=null;render();
  const r=await send('fair_oaq_start',{lv});S.busy=false;
  if(r?.fair){S.oaq={...S.oaq,sel:null,anim:null,end:null,showEnd:true,quit:false,say:pick((OPP[lv]||OPP.de).start)};}
  render();
}
async function oaqMove(dir){
  const o=F().oaq,cell=S.oaq.sel;if(!o||o.stage!=='play'||cell==null||S.busy||S.oaq.anim)return;
  S.oaq.sel=null;S.oaq.quit=false;S.busy=true;S.flash=null;
  S.oaq.anim={b:[...o.b],q:[...o.q],cap:[...o.cap],hand:0,at:null,hl:cell,flash:null,side:0};render();
  const r=await send('fair_oaq_move',{cell,dir});
  if(!r?.fair){S.oaq.anim=null;S.busy=false;render();return;}
  await playTrace(r.fair.trace||[],o.lv);
  S.oaq.anim=null;S.busy=false;
  const x=r.fair.end;
  if(x){S.oaq.end={...x,titles:r.fair.titles||[]};S.oaq.showEnd=true;S.oaq.say=pick((OPP[o.lv]||OPP.de)[x.stage==='won'?'lost':x.stage==='lost'?'won':'draw']);
    sfx(x.stage==='won'?'kinh':x.stage==='lost'?'lose':'open');}
  render();
}
async function playTrace(trace,lv){
  const a=S.oaq.anim,lines=OPP[lv]||OPP.de,step=()=>S.oaq.fast?55:150;
  for(const ev of trace){
    if(!S.oaq.anim)return;
    const [k]=ev;
    if(k==='turn'){a.side=ev[1];a.hl=ev[2];a.at=null;a.flash=null;if(ev[1]===1){S.oaq.say=pick(lines.think);render();await wait(S.oaq.fast?300:750);}continue;}
    if(k==='pick'){a.b[ev[1]]=0;a.hand=ev[2];a.at=ev[1];a.hl=null;sfx('stone');render();await wait(step()+60);continue;}
    if(k==='drop'){a.b[ev[1]]++;a.hand=Math.max(0,a.hand-1);a.at=ev[1];sfx('stone');render();await wait(step());continue;}
    if(k==='cap'){const [,c,dan,quan]=ev;a.b[c]=0;if(quan)a.q[c===0?0:1]=0;a.cap[2*a.side]+=dan;a.cap[2*a.side+1]+=quan;a.flash=c;a.at=null;
      S.oaq.say=pick(a.side===1?lines.cap:lines.lose);sfx('cap');render();await wait(S.oaq.fast?250:600);continue;}
    if(k==='non'){a.flash=ev[1];S.flash={text:'Quan non: ô quan chưa đủ dân, chưa ăn được.',kind:'warn'};render();await wait(S.oaq.fast?300:700);S.flash=null;continue;}
    if(k==='seed'){const row=ev[1]===0?ROW_ME:ROW_OPP;row.forEach(c=>{a.b[c]=1;});a.cap[2*ev[1]]-=5;S.flash={text:ev[1]===0?'Hàng bạn hết quân: rải lại 5 dân đã ăn.':'Hàng bên kia hết quân: rải lại 5 dân.',kind:'warn'};render();await wait(S.oaq.fast?300:800);S.flash=null;continue;}
    if(k==='collect'){S.flash={text:'Hết quan, tàn dân: thu quân về đếm điểm!',kind:'good'};render();await wait(S.oaq.fast?300:700);S.flash=null;continue;}
  }
  a.at=null;a.hl=null;
}

/* ---- 💍 Ném vòng cổ chai ---- */
/** Where the ring is at `t` ms (0..100): the same arithmetic as x_at in game/fair_ring.py. */
const ringX=(p,t)=>{const u=((t/p.period)+p.phase)%1;return 100*(1-Math.abs(2*u-1));};
const trackPos=x=>`calc(6% + ${x*0.88}%)`;
function ringJudge(p,taps){const rung=new Set();return taps.map(t=>{const x=ringX(p,t);const i=p.xs.findIndex((bx,k)=>!rung.has(k)&&Math.abs(x-bx)<=R().ring_tol);if(i>=0)rung.add(i);return i;});}
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
  else go=btn(`🎯 Phát ${rings} vòng (miễn phí)`,'ringstart',{},'primary big full',S.busy||!r.ring_left?' disabled':' data-fh-key="ringstart"');
  return `<section class="fh-stall fh-ringstall" aria-label="Ném vòng cổ chai">
    ${say(RINGER,R0.say)}
    <div class="fh-ringstage${rd&&!res?' live':''}"><div class="fh-track" aria-hidden="true"><span class="fh-aim" style="left:${trackPos(rd?ringX(rd,0):50)}"><i></i></span></div><div class="fh-fly-layer" aria-hidden="true"></div><div class="fh-shelf">${bottles}</div></div>
    <div class="fh-ringsleft" aria-label="Còn ${rings-used} vòng">${left}</div>
    ${go}
    <div class="fh-ringmeter">${meter(e)}</div>
    <p class="fh-rule">Bấm “Ném!” khi vòng ở ngay trên miệng chai. Mỗi chai chỉ tính một lần. Trúng ${r.ring_hit||2} xu một chai, đủ ${rings} chai thêm ${r.ring_all||5} xu. Từ 3 chai: +${(F().points?.rules||{}).ring3||1} điểm, đủ ${rings} chai: +${(F().points?.rules||{}).ring5||2} điểm.</p>
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
function bcView(){
  const f=F(),b=S.bc,r=R(),total=bcTotal(),max=r.bc_max||20,stop=f.today?.done,rolling=b.phase!=='idle';
  const hits=b.last&&b.phase==='idle'?new Set(b.last.dice):new Set();
  const dice=(b.dice||['bau','cua','ca']).map((d,i)=>`<span class="fh-die" style="--i:${i}">${art(d)}<span class="sr-only">${FACE_NAME[d]}</span></span>`).join('');
  const mat=FACES.map(face=>{const n=b.bets[face]||0,hit=hits.has(face);
    return `<button type="button" class="fh-face fh-f-${face}${hit?' hit':''}${n?' bet':''}" data-fh="bet" data-face="${face}" data-fh-key="face-${face}" aria-label="${FACE_NAME[face]}${n?`, đang đặt ${n} xu`:''}"${rolling||stop?' disabled':''}>${art(face)}<b>${FACE_NAME[face]}</b>${n?`<em class="fh-stake">${n}</em>`:''}</button>`;}).join('');
  const res=b.last&&b.phase==='idle'?bcResult(b.last):'';
  return `<section class="fh-stall fh-bc" aria-label="Bầu cua tôm cá">
    ${say(DEALER,b.say)}
    <div class="fh-table"><div class="fh-plate ${b.phase==='shake'?'shake':''} ${b.phase==='idle'&&b.dice?'open':''}" aria-live="polite"><div class="fh-dice">${dice}</div><div class="fh-bowl" aria-hidden="true"></div></div>${res}</div>
    <div class="fh-mat" role="group" aria-label="Chiếu bầu cua: chạm một con để đặt">${mat}</div>
    <div class="fh-chips" role="group" aria-label="Mỗi lần chạm đặt"><span>Mỗi chạm</span>${CHIPS.map(c=>`<button type="button" class="fh-chip${b.chip===c?' on':''}" data-fh="chip" data-v="${c}" aria-pressed="${b.chip===c}" data-fh-key="chip-${c}">${c}</button>`).join('')}${btn('Gom lại','clear',{},'ghost small',total&&!rolling?'':' disabled')}</div>
    <div class="fh-go"><span>Đặt <b>${total}</b>/${max} xu</span>${btn(rolling?'Đang lắc…':'🥣 Lắc!','roll',{},'primary big',total&&!rolling&&!stop?' data-fh-key="roll"':' disabled data-fh-key="roll"')}</div>
    <p class="fh-rule">Ra mấy con trùng mặt đặt thì ăn bấy nhiêu lần tiền cược, kèm tiền vốn. Ba con giống nhau (bão) ăn ${r.bao||10} lần.</p>
  </section>`;
}
function bcResult(l){
  const cls=l.net>0?'good':l.net<0?'bad':'';
  return `<div class="fh-result ${cls}"><b>${l.bao?'🌪️ Bão! ':''}${l.net>0?`+${xu(l.net)}`:l.net<0?`−${xu(-l.net)}`:'Hòa vốn'}</b>${l.points?`<small>+${l.points} điểm hội chợ</small>`:''}</div>`;
}
async function roll(){
  const b=S.bc,total=bcTotal();if(!total||b.phase!=='idle')return;
  b.phase='shake';b.say='Lắc nè, lắc nè… xóc xóc xóc!';S.flash=null;render();sfx('shake');
  const [r]=await Promise.all([send('fair_bc',{bets:{...b.bets}}),new Promise(ok=>setTimeout(ok,reduce()?300:ROLL_MS))]);
  if(!r?.fair){b.phase='idle';b.say=pick(DEALER.idle);render();return;}
  const x=r.fair;b.dice=x.dice;b.last={...x};b.phase='idle';
  b.say=x.bao?`Bão! Bão! Ba con ${FACE_NAME[x.bao].toLowerCase()} luôn bà con ơi!`:x.net>0?'Trúng rồi! Chú chung tiền liền nè!':x.net===0?'Huề vốn, vui là chính!':'Ván sau gỡ lại nha, đừng buồn!';
  sfx('open');setTimeout(()=>sfx(x.net>0?'win':x.net<0?'lose':'open'),260);
  titles(x);render();
}
function titles(x){if(x.titles?.length)S.flash={text:`🎉 Danh hiệu mới: ${x.titles.map(t=>TITLE_NAMES[t]||t).join(', ')}`,kind:'good'};}

/* ---- 🕯️ Chiếu trong (xóc đĩa) ---- */
function xdView(){
  const f=F(),x=S.xd,r=R(),wait=raidLeft(),busy=x.phase!=='idle',stop=f.today?.done;
  if(x.raid)return raidCard(x.raid);
  const coins=(x.coins||[1,0,1,0]).map((c,i)=>`<span class="fh-coin ${c?'red':'white'}" style="--i:${i}"></span>`).join('');
  const res=x.last&&x.phase==='idle'?`<div class="fh-result ${x.last.net>0?'good':'bad'}"><b>${x.last.even?'Chẵn':'Lẻ'}! ${x.last.net>0?`+${xu(x.last.net)}`:`−${xu(-x.last.net)}`}</b>${x.last.points?`<small>+${x.last.points} điểm hội chợ</small>`:''}</div>`:'';
  const closed=wait>0?`<section class="fh-card fh-swept"><span aria-hidden="true">🧹</span><div><b>Chiếu dẹp rồi, bày lại sau <span data-fh-count="raid">${clock(wait)}</span></b><small>Ra trước chơi bầu cua, lô tô cho lành nha.</small></div></section>`:'';
  return `<section class="fh-stall fh-xd" aria-label="Chiếu trong: xóc đĩa chẵn lẻ">
    ${say(HOST,x.say,'dark')}
    <p class="fh-warn">⚠️ Chiếu trong cược lớn hơn (${r.xd_min}–${r.xd_max} xu). Thỉnh thoảng công an phường ghé kiểm tra: mất tiền cược và bị phạt.</p>
    ${closed}
    <div class="fh-table dark"><div class="fh-plate xd ${x.phase==='shake'?'shake':''} ${x.phase==='idle'&&x.coins?'open':''}"><div class="fh-coins">${coins}</div><div class="fh-bowl" aria-hidden="true"></div></div>${res}</div>
    <div class="fh-sides" role="group" aria-label="Chọn chẵn hay lẻ">${[['chan','Chẵn','0, 2 hoặc 4 mặt đỏ'],['le','Lẻ','1 hoặc 3 mặt đỏ']].map(([id,l,s])=>`<button type="button" class="fh-side${x.side===id?' on':''}" data-fh="side" data-v="${id}" aria-pressed="${x.side===id}" data-fh-key="side-${id}"${busy||wait>0?' disabled':''}><b>${l}</b><small>${s}</small></button>`).join('')}</div>
    <div class="fh-chips" role="group" aria-label="Tiền cược"><span>Cược</span>${XD_STAKES.map(v=>`<button type="button" class="fh-chip${x.stake===v?' on':''}" data-fh="stake" data-v="${v}" aria-pressed="${x.stake===v}" data-fh-key="stake-${v}"${busy||wait>0?' disabled':''}>${v}</button>`).join('')}</div>
    <div class="fh-go"><span>${x.side==='chan'?'Chẵn':'Lẻ'} · <b>${xu(x.stake)}</b></span>${btn(busy?'Đang xóc…':'🫙 Xóc!','shakexd',{},'primary big',busy||wait>0||stop?' disabled data-fh-key="xd"':' data-fh-key="xd"')}</div>
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
  const x=S.xd;if(x.phase!=='idle')return;
  x.phase='shake';x.say='Xóc nè! Nghe kêu lắc cắc chưa…';S.flash=null;render();sfx('shake');
  const [r]=await Promise.all([send('fair_xd',{side:x.side,stake:x.stake}),new Promise(ok=>setTimeout(ok,reduce()?300:ROLL_MS))]);
  x.phase='idle';
  if(!r?.fair){x.say=pick(HOST.idle);render();return;}
  const d=r.fair;
  if(d.raid){x.raid={...d};x.coins=null;x.last=null;x.say=pick(HOST.idle);sfx('siren');render();return;}
  x.coins=d.coins;x.last={...d};x.say=d.net>0?'Hên quá ta! Anh chung liền.':'Ván sau chắc chắn tới lượt em!';
  sfx('open');setTimeout(()=>sfx(d.net>0?'win':'lose'),260);titles(d);render();
}

/* ---- 🎱 Lô tô ---- */
const colOf=n=>n<10?0:n>=90?8:Math.floor(n/10);
function L(){const v=F().loto;return v&&!v.expired?v:null;}
function syncLoto(){
  const v=L();
  if(!v){if(S.lt.id){pauseLoto();S.lt.id=null;}return null;}
  if(v.id!==S.lt.id){
    pauseLoto();
    let saved=null;try{saved=JSON.parse(localStorage.getItem(LS)||'null');}catch{/* storage blocked */}
    const ok=saved&&saved.id===v.id;
    S.lt={...S.lt,id:v.id,shown:ok?Math.min(saved.shown|0,v.npc_done):0,marks:ok&&Array.isArray(saved.marks)?saved.marks.filter(n=>Number.isInteger(n)):[],over:null,won:null,claiming:false,npcAt:0};
  }
  if(v.stage==='won'&&!S.lt.won)S.lt.won={prize:R().loto_prize};
  if(v.stage==='lost'&&!S.lt.over&&!S.lt.won)S.lt.over={by:v.npc_name,quiet:true};
  return v;
}
function saveLoto(){try{localStorage.setItem(LS,JSON.stringify({id:S.lt.id,shown:S.lt.shown,marks:S.lt.marks}));}catch{/* storage blocked */}}
function pauseLoto(){clearTimeout(S.lt.timer);S.lt.timer=null;}
function resumeLoto(){
  const v=syncLoto();pauseLoto();
  if(!v||v.stage!=='play'||S.lt.over||S.lt.won||!S.dlg?.open||S.tab!=='lt')return;
  S.lt.timer=setTimeout(stepLoto,S.lt.shown?(S.lt.fast?FAST_MS:CALL_MS):900);
}
function stepLoto(){
  const v=L();if(!v||v.stage!=='play'||S.lt.over||S.lt.won)return;
  if(S.lt.shown>=v.npc_done){   // a neighbour's row is full: they shout, unless the player beats them to it
    if(!S.lt.claiming){S.lt.over={by:v.npc_name};sfx('lose');saveLoto();render();send('fair_loto_fold',{});}
    return;
  }
  S.lt.shown++;saveLoto();sfx('call');render();
  S.lt.timer=setTimeout(stepLoto,S.lt.shown>=v.npc_done?NPC_GRACE:(S.lt.fast?FAST_MS:CALL_MS));
}
const calledSet=v=>new Set(v.seq.slice(0,S.lt.shown));
function readyRow(v){
  const marks=new Set(S.lt.marks),called=calledSet(v);
  return v.card.findIndex(row=>row.every(n=>marks.has(n)&&called.has(n)));
}
function rivalMiss(v,called){
  return v.npcs.map(n=>({...n,miss:Math.min(...n.rows.map(r=>r.filter(x=>!called.has(x)).length))}));
}
function lotoView(){
  const v=syncLoto(),r=R(),f=F();
  if(!v||S.lt.won||S.lt.over)return `<section class="fh-stall fh-lt" aria-label="Lô tô">${say(CALLER,S.lt.won?'Kinh rồi! Chúc mừng người thắng, ván sau chơi tiếp nha bà con!':S.lt.over?`${S.lt.over.by} kinh rồi! Ván sau tới lượt mình nha.`:'Lô tô hội chợ đây! Ai mua tờ dò thì ngồi xuống, ai chưa mua thì nghe cho vui!')}
    ${S.lt.won?`<div class="fh-card fh-kinhcard"><div class="fh-big" aria-hidden="true">🎉</div><h3>Kinh! +${xu(S.lt.won.prize)}</h3>${S.lt.won.titles?.includes('f_loto')?'<p class="fh-award">🎱 Danh hiệu mới: <b>Thần lô tô hội chợ</b></p>':''}${S.lt.won.points?`<p class="muted small">+${S.lt.won.points} điểm hội chợ</p>`:''}</div>`:''}
    ${S.lt.over&&!S.lt.over.quiet?`<div class="fh-card fh-lostcard"><b>📣 ${esc(S.lt.over.by)}: “Kinh!”</b><small>${S.lt.over.mine?'Tờ của bạn cũng vừa đủ hàng mà chưa kịp hô. Lần sau hô lẹ nha!':'Ván này người khác đủ hàng trước rồi.'}</small></div>`:''}
    <div class="fh-card fh-buy"><div class="fh-ticket" aria-hidden="true"><i></i><i></i><i></i></div><div class="grow"><b>Tờ dò ${xu(r.loto_price)}</b><small>Đủ 5 số một hàng ngang trước ${r.loto_npcs} người chơi khác: hô “Kinh!” ăn ${xu(r.loto_prize)}.</small></div></div>
    ${btn(`🎟️ Mua tờ dò · ${xu(r.loto_price)}`,'buy',{},'primary big full',f.today?.done||S.busy?' disabled data-fh-key="buy"':' data-fh-key="buy"')}
    <p class="fh-rule">Cô Út hô số nào, bạn chạm số đó trên tờ dò. Ai mua tờ trong cùng một phút sẽ nghe chung một lượt số.</p></section>`;
  const called=calledSet(v),marks=new Set(S.lt.marks),cur=S.lt.shown?v.seq[S.lt.shown-1]:null,ready=readyRow(v);
  const grid=v.card.map((row,ri)=>{const cells=Array(9).fill(null);row.forEach(n=>{cells[colOf(n)]=n;});
    return `<div class="fh-row${ready===ri?' full':''}" role="row">${cells.map(n=>n==null?'<span class="fh-cell empty" role="gridcell"></span>':
      `<button type="button" role="gridcell" class="fh-cell${marks.has(n)?' marked':called.has(n)?' called':''}" data-fh="mark" data-n="${n}" data-fh-key="n-${n}" aria-pressed="${marks.has(n)}" aria-label="Số ${n}${called.has(n)?', đã gọi':''}">${n}</button>`).join('')}</div>`;}).join('');
  const rivals=rivalMiss(v,called).map(n=>`<span class="fh-rival${n.miss<=1?' hot':''}"><span aria-hidden="true">${n.emoji}</span>${esc(n.name)}<em>${n.miss<=1?'chờ 1!':`còn ${n.miss}`}</em></span>`).join('');
  const recent=v.seq.slice(Math.max(0,S.lt.shown-7),Math.max(0,S.lt.shown-1)).reverse().map(n=>`<i>${n}</i>`).join('');
  return `<section class="fh-stall fh-lt" aria-label="Lô tô">
    ${say(CALLER,cur?callLine(cur,v.slot):'Chuẩn bị nha bà con… số đầu tiên ra liền!','caller')}
    <div class="fh-callrow"><span class="fh-ball${cur?' pop':''}" aria-live="polite" aria-label="${cur?`Số vừa gọi: ${cur}`:'Chưa gọi số'}">${cur??'–'}</span><div class="grow"><div class="fh-recent" aria-label="Các số vừa gọi">${recent}</div><small>Đã gọi ${S.lt.shown}/90 · ván phút ${esc(v.minute)}</small></div></div>
    <div class="fh-rivals" aria-label="Người chơi khác">${rivals}</div>
    <div class="fh-ticketcard" role="grid" aria-label="Tờ dò của bạn">${grid}</div>
    <div class="fh-go">${btn(S.lt.fast?'⏯️ Gọi chậm':'⏩ Gọi nhanh','fast',{},'ghost small')}${btn('📣 Kinh!','kinh',{},`primary big fh-kinh${ready>=0?' ready':''}`,ready>=0&&!S.lt.claiming?' data-fh-key="kinh"':' disabled data-fh-key="kinh"')}</div>
    <p class="fh-rule">Chạm số đã gọi để đánh dấu. Đủ một hàng ngang thì bấm “Kinh!” trước người khác.</p></section>`;
}
async function buy(){
  if(S.busy)return;S.busy=true;S.flash=null;render();
  const r=await send('fair_loto_buy',{});S.busy=false;
  if(r?.fair){S.lt.id=null;syncLoto();}
  render();resumeLoto();
}
async function kinh(){
  const v=L();if(!v||S.lt.claiming)return;
  const row=readyRow(v);if(row<0)return;
  S.lt.claiming=true;pauseLoto();render();
  const r=await send('fair_loto_kinh',{row,at:S.lt.shown});
  S.lt.claiming=false;
  if(r?.fair?.won){S.lt.won={prize:r.fair.prize,titles:r.fair.titles||[],points:r.fair.points||0};sfx('kinh');titles(r.fair);}
  else if(r?.fair){S.lt.over={by:r.fair.by||v.npc_name,mine:true};sfx('lose');}
  else{resumeLoto();}
  saveLoto();render();
}
function mark(n){
  const v=L();if(!v)return;
  if(!calledSet(v).has(n)){S.flash={text:`Số ${n} chưa gọi đâu, đợi Cô Út hô nha!`,kind:'warn'};render();return;}
  const i=S.lt.marks.indexOf(n);if(i>=0)S.lt.marks.splice(i,1);else S.lt.marks.push(n);
  S.flash=null;sfx('mark');saveLoto();render();
}

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
  const mine=me?`<div class="fh-me"><span>Bạn: <b>${fmt(p.total)}</b> điểm${me.rank&&me.visible!==false?` · hạng <b>${fmt(me.rank)}</b>`:''}</span>${f.open?`<small>Hôm nay ${fmt(p.today)}/${fmt(p.cap)} điểm</small>`:''}${me.visible===false?`<small class="fh-hidden">Tên bạn đang ẩn nên chưa lên bảng và chưa nhận được danh hiệu. Bật “Hiện tên tôi” ở Xếp hạng nhé.</small>`:''}</div>`:'';
  return `<section class="fh-stall fh-gold" aria-label="Bảng vàng hội chợ">
    <div class="fh-card fh-crown"><h3>🏆 Bảng vàng hội chợ</h3><ul class="fh-tiers">${tiers}</ul><p class="small">${f.over?'Danh hiệu đã trao khi hội tàn.':`Trao khi hội tàn (${esc(dateOf(f.closes))} 00:00), giữ mãi trong bộ sưu tập.`}</p></div>
    ${won}${mine}${S.board.error?`<p class="fh-flash bad">${esc(S.board.error)}</p>`:''}${rows}
    <details class="fh-how"><summary>Cách tính điểm</summary><ul><li>Mỗi ngày ghé hội chơi: +${rules.day}</li><li>Thắng một ván ô ăn quan: +${rules.oaq}</li><li>Ném vòng trúng từ 3 chai: +${rules.ring3}, đủ 5 chai: +${rules.ring5}</li><li>Ván bầu cua có con trùng mặt đặt: +${rules.bc}</li><li>Thắng một ván chiếu trong: +${rules.xd} (bị công an kiểm tra: 0)</li><li>Kinh thắng một ván lô tô: +${rules.loto}</li><li>Tối đa ${fmt(p.cap||30)} điểm mỗi ngày. Bằng điểm thì ai đạt trước đứng trên.</li></ul><p class="small muted">Điểm tính theo lượt chơi, không theo số xu thắng, nên cược nhỏ cũng lên bảng được.</p></details>
  </section>`;
}

/* ---- clicks ---- */
async function onClick(op,data){
  const b=S.bc,x=S.xd;
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;if(S.tab!=='lt')pauseLoto();render();S.dlg.querySelector('.fh-body')?.scrollTo?.(0,0);if(S.tab==='board')loadBoard();if(S.tab==='lt')resumeLoto();if(S.tab==='ring')startRingLoop();return;
    case'oaqstart':oaqStart(data.lv==='kho'?'kho':'de');return;
    case'oaqsel':{if(S.oaq.anim||S.busy)return;const c=Number(data.c);S.oaq.sel=S.oaq.sel===c?null:c;S.oaq.quit=false;sfx('mark');render();return;}
    case'oaqmove':oaqMove(Number(data.d)===-1?-1:1);return;
    case'oaqfast':S.oaq.fast=!S.oaq.fast;render();return;
    case'oaqquit':{if(!S.oaq.quit){S.oaq.quit=true;render();return;}
      S.oaq.quit=false;S.busy=true;render();const r=await send('fair_oaq_quit',{});S.busy=false;
      if(r){S.oaq.end=null;S.oaq.showEnd=false;S.oaq.sel=null;S.oaq.say='';}render();return;}
    case'ringstart':ringStart();return;
    case'throw':ringThrow();return;
    case'chip':b.chip=Number(data.v)||1;render();return;
    case'bet':{if(b.phase!=='idle')return;const max=R().bc_max||20,room=max-bcTotal();
      if(room<=0){S.flash={text:`Mỗi ván đặt tối đa ${max} xu thôi nha.`,kind:'warn'};render();return;}
      const add=Math.min(b.chip,room);b.bets={...b.bets,[data.face]:(b.bets[data.face]||0)+add};b.last=null;S.flash=null;sfx('mark');render();return;}
    case'clear':b.bets={};b.last=null;render();return;
    case'roll':roll();return;
    case'side':x.side=data.v==='le'?'le':'chan';render();return;
    case'stake':x.stake=Number(data.v)||10;render();return;
    case'shakexd':shakeXd();return;
    case'raidok':x.raid=null;S.tab=data.tab||'bc';render();if(S.tab==='lt')resumeLoto();return;
    case'buy':buy();return;
    case'mark':mark(Number(data.n));return;
    case'kinh':kinh();return;
    case'fast':S.lt.fast=!S.lt.fast;render();if(S.lt.timer){pauseLoto();resumeLoto();}return;
  }
}
