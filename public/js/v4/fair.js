/** 🏮 Hội chợ dân gian: bầu cua tôm cá, lô tô, the back corner's xóc đĩa (and Công an phường), the Bảng vàng.
 * Every rule, result and number is the server's (game/fair.py, game/fair_board.py): this file renders
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
const TITLE_NAMES={f_loto:'🎱 Thần lô tô hội chợ',f_bao:'🌪️ Trúng bão bầu cua',f_raid:'🚨 Bị công an hỏi thăm'};
const CHIPS=[1,2,5,10];
const XD_STAKES=[10,20,30,50];
const CALL_MS=2300,FAST_MS=1100,NPC_GRACE=2000,ROLL_MS=1400;
const LS='mnl.fair.lt';

/* ---- the people of the fair ---- */
const DEALER={name:'Chú Tám bầu cua',emoji:'🧔🏻',idle:['Bầu cua cá cọp đây, đặt đi bà con ơi!','Đặt lẹ đặt lẹ, chú lắc liền nè!','Ai chơi thì đặt, ai coi thì vỗ tay cho vui nha!','Con gì cũng có, ván nào cũng vui!']};
const CALLER={name:'Cô Út lô tô',emoji:'💃🏻'};
const HOST={name:'Anh Ba chiếu trong',emoji:'🕶️',idle:['Chơi lớn không? Chẵn lẻ, ăn một trả một.','Nói nhỏ thôi… ngó chừng phía ngoài giùm anh.','Xóc nè, xóc nè! Chẵn hay lẻ, đặt đi!']};

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
const S={dlg:null,env:null,tab:'bc',busy:false,flash:null,skew:0,listening:false,tick:null,
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
  d.addEventListener('close',()=>{pauseLoto();clearInterval(S.tick);S.tick=null;S.flash=null;});
  S.dlg=d;return d;
}
export async function openFair(env,data={}){
  S.env=env;
  if(!S.listening){
    S.listening=true;
    let seen='';
    env.api.addEventListener('state',()=>{const f=F();if(typeof f.now==='number')S.skew=f.now*1000-Date.now();
      const key=JSON.stringify([f.wallet,f.today,f.raid_left>0,f.loto?.id,f.loto?.stage,f.points?.total,f.open]);if(key===seen)return;seen=key;
      if(S.dlg?.open&&!animating())render();});
  }
  const f=F();if(typeof f.now==='number')S.skew=f.now*1000-Date.now();
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(data?.tab)S.tab=data.tab;
  if(!f.open&&!data?.tab)S.tab='bc';
  if(!S.bc.say)S.bc.say=pick(DEALER.idle);
  if(!S.xd.say)S.xd.say=pick(HOST.idle);
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  clearInterval(S.tick);S.tick=setInterval(tickLabels,1000);
  if(S.tab==='board')loadBoard();
  if(S.tab==='lt')resumeLoto();
}
export async function fairAction(action,data,el,env){
  if(action!=='fair')return false;
  await openFair(env,data);return true;
}
const animating=()=>S.bc.phase!=='idle'||S.xd.phase!=='idle'||S.busy;

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
  const f=F(),t=f.today||{},p=f.points||{};
  return `<div class="fh-strip" role="status"><span>👛 <b>${xu(f.wallet)}</b></span><span>🎟️ Hôm nay còn chơi <b>${xu(t.left)}</b></span><button type="button" class="fh-pts" data-fh="tab" data-tab="board">🏆 <b>${fmt(p.total)}</b> điểm</button></div>`;
}
function tabs(){
  const f=F(),list=[['bc','🦀','Bầu cua'],['lt','🎱','Lô tô'],['xd','🕯️','Chiếu trong'],['board','🏆','Bảng vàng']];
  return `<nav class="fh-tabs" role="tablist" aria-label="Các gian hàng">${list.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'on':''}${id==='lt'&&f.loto?.stage==='play'?' live':''}" data-fh="tab" data-tab="${id}" data-fh-key="tab-${id}"><span aria-hidden="true">${e}</span>${l}</button>`).join('')}</nav>`;
}
const flash=()=>`<p class="fh-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
const note=()=>`<p class="fh-note">🎪 Trò chơi dân gian ở hội chợ, chơi bằng xu trong game. Không có tiền thật.</p>`;
function page(){
  const f=F();
  if(!f.show&&!f.over&&!f.soon)return head()+`<div class="sheet-body fh-body">${closedCard(true)}</div>`;
  if(!f.open&&S.tab!=='board')return head()+`<div class="sheet-body fh-body">${closedCard()}${S.env?.api?.state?.journey?.story?btn('🏆 Xem Bảng vàng hội chợ','tab',{tab:'board'},'cream full'):''}${note()}</div>`;
  const body=S.tab==='lt'?lotoView():S.tab==='xd'?xdView():S.tab==='board'?boardView():bcView();
  return head()+`<div class="sheet-body fh-body">${f.open?strip():''}${f.open?tabs():''}${flash()}${f.open&&S.tab!=='board'&&f.today?.done?enoughCard():''}${body}${note()}</div>`;
}
function closedCard(gone){
  const f=F();
  if(f.soon)return `<section class="fh-card fh-closed"><div class="fh-big" aria-hidden="true">🏮</div><h3>Hội chợ sắp mở</h3><p>Khai hội ngày ${esc(dateOf(f.opens))}, mở ${Math.round((f.closes-f.opens)/86400)} ngày. Hẹn bà con ghé chơi bầu cua, lô tô nha!</p></section>`;
  return `<section class="fh-card fh-closed"><div class="fh-big" aria-hidden="true">🎐</div><h3>Hội chợ đã tàn, hẹn lần sau</h3><p>${gone?'Lều bạt đã dọn, đèn lồng đã cất.':'Cảm ơn bà con đã ghé hội. Bảng vàng vẫn còn đó để xem lại.'}</p></section>`;
}
const enoughCard=()=>`<section class="fh-card fh-enough"><span aria-hidden="true">🍵</span><div><b>Hôm nay chơi vậy đủ rồi, mai ghé tiếp nha.</b><small>Mỗi ngày thua tối đa ${xu(R().cap)}. Ghé xem Bảng vàng hoặc dạo phố một vòng nhé.</small></div></section>`;
const say=(who,text,cls='')=>`<div class="fh-npcline ${cls}"><span class="fh-npc" aria-hidden="true">${who.emoji}</span><div class="fh-bubble"><small>${esc(who.name)}</small><p>${esc(text)}</p></div></div>`;

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
  const rules=p.rules||{day:1,bc:1,xd:1,loto:3};
  const won=fair?.winners?.length?`<div class="fh-card fh-crowned"><h3>Hội đã tàn · Bảng vàng chung cuộc</h3><ol>${fair.winners.map(w=>`<li class="${w.me?'me':''}"><span aria-hidden="true">${esc(w.emoji)}</span><b>${esc(w.name)}</b><small>${esc(w.title)} · ${fmt(w.score)} điểm</small></li>`).join('')}</ol></div>`:'';
  const rows=B?.rows?.length?`<ol class="fh-board">${B.rows.map(r=>`<li class="${r.me?'me':''}${r.rank===1?' first':''}"><span class="fh-rank">${r.rank===1?'👑':r.rank<=10?'🎪':r.rank}</span><span class="grow"><b>${esc(r.name||'')}</b>${r.guest?'<em class="fh-guest">khách</em>':''}<small>${fmt(r.days)} ngày chơi</small></span><b class="fh-score">${fmt(r.points??r.score)}</b></li>`).join('')}</ol>`
    :S.board.loading||!B?'<p class="muted fh-wait">Đang mở Bảng vàng…</p>':'<p class="muted fh-wait">Chưa ai có điểm. Chơi một ván là có tên trên bảng!</p>';
  const mine=me?`<div class="fh-me"><span>Bạn: <b>${fmt(p.total)}</b> điểm${me.rank&&me.visible!==false?` · hạng <b>${fmt(me.rank)}</b>`:''}</span>${f.open?`<small>Hôm nay ${fmt(p.today)}/${fmt(p.cap)} điểm</small>`:''}${me.visible===false?`<small class="fh-hidden">Tên bạn đang ẩn nên chưa lên bảng và chưa nhận được danh hiệu. Bật “Hiện tên tôi” ở Xếp hạng nhé.</small>`:''}</div>`:'';
  return `<section class="fh-stall fh-gold" aria-label="Bảng vàng hội chợ">
    <div class="fh-card fh-crown"><h3>🏆 Bảng vàng hội chợ</h3><ul class="fh-tiers">${tiers}</ul><p class="small">${f.over?'Danh hiệu đã trao khi hội tàn.':`Trao khi hội tàn (${esc(dateOf(f.closes))} 00:00), giữ mãi trong bộ sưu tập.`}</p></div>
    ${won}${mine}${S.board.error?`<p class="fh-flash bad">${esc(S.board.error)}</p>`:''}${rows}
    <details class="fh-how"><summary>Cách tính điểm</summary><ul><li>Mỗi ngày ghé hội chơi: +${rules.day}</li><li>Ván bầu cua có con trùng mặt đặt: +${rules.bc}</li><li>Thắng một ván chiếu trong: +${rules.xd} (bị công an kiểm tra: 0)</li><li>Kinh thắng một ván lô tô: +${rules.loto}</li><li>Tối đa ${fmt(p.cap||30)} điểm mỗi ngày. Bằng điểm thì ai đạt trước đứng trên.</li></ul><p class="small muted">Điểm tính theo lượt chơi, không theo số xu thắng, nên cược nhỏ cũng lên bảng được.</p></details>
  </section>`;
}

/* ---- clicks ---- */
async function onClick(op,data){
  const b=S.bc,x=S.xd;
  switch(op){
    case'close':S.dlg.close();return;
    case'tab':S.tab=data.tab;S.flash=null;if(S.tab!=='lt')pauseLoto();render();S.dlg.querySelector('.fh-body')?.scrollTo?.(0,0);if(S.tab==='board')loadBoard();if(S.tab==='lt')resumeLoto();return;
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
