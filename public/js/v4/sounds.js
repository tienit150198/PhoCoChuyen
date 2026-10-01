/** Character voices, detail sounds and the bank speaker ("loa báo tiền").
 *
 * - Giọng nhân vật: every speech bubble (world.say) and chat line plays a short syllable babble
 *   (audio.js Sound.babble) in the speaker's own pitch: children high, elders low, one timbre per NPC.
 * - Âm thanh chi tiết: coins / cash register when money comes in, a pop for a finished step, a chime for
 *   the day's close and level ups, the door bell for a new customer, a paper rustle when a sheet opens.
 * - Story and chapter scenes (.jr-line bubbles in an open dialog): each NPC line babbles once as it appears.
 * - Tiền về (feedback #13): money that comes in plays "ting ting" (a recorded CC0 bell,
 *   public/audio/sfx/CREDITS.md; switch moneyTing) and a bank-app voice reads the amount (switch bankVoice):
 *   · a transfer / QR payment into the player's own shop (the server marks it: result.bank, game/bank_speaker.py):
 *     "Đã nhận N xu";
 *   · the journey wallet going up (salary, gifts, lì xì, mừng cưới, a draw from a shop, a withdrawal…), read from
 *     the new rows of its history: "Đã nhận lương N xu" / "Ví vừa nhận thêm N xu";
 *   · the bank account balance going up: "Tài khoản vừa nhận thêm N xu".
 *   Whatever lands within ~1.5 s is one ting and one line. The voice (speechSynthesis, vi-VN; English UI:
 *   en-US) speaks for shop transfers, salary and anything from VOICE_MIN xu; smaller sums only ting.
 *   No Vietnamese voice: a "🔔 +N xu" chip, never another language.
 *
 * Nothing runs before the first tap: listeners only. Nodes are made per sound; the bell (~9 KB) is fetched once,
 * on the first tap with sound on. */
import {loadSample,setTing} from '../audio.js';
const ENDED=new Set(['completed','referred','cancelled']);
const isIOS=()=>/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
const WINDOW=1500,QUIET=600,SAY_DELAY=420,VOICE_MIN=10;
const TING_URL='/audio/sfx/ting.mp3';

/* ---- voices ---- */
function hash(text){let h=2166136261;for(const ch of String(text||''))h=Math.imul(h^ch.codePointAt(0),16777619);return h>>>0;}
const starts=(name,words)=>words.some(w=>name===w||name.startsWith(w+' '));
/** A stable little voice from the NPC's id, name (Vietnamese kinship word) and role. */
export function voiceOf(id,npc={}){
  const name=String(npc.display_name||'').toLowerCase(),role=String(npc.role||'').toLowerCase(),h=hash(id||name);
  const has=words=>words.some(w=>` ${role} `.includes(` ${w}`));
  const child=starts(name,['bé','cháu','nhóc'])||has(['học sinh','trẻ','em bé','thiếu nhi']);
  const elder=starts(name,['bà','ông','cụ'])||has(['hưu','lớn tuổi','cao tuổi']);
  const woman=starts(name,['chị','cô','dì','mợ','thím','bà'])||has(['mẹ']);
  const man=starts(name,['anh','chú','bác','cậu','dượng','ông','thầy'])||has(['bố']);
  let base=woman?350:man?185:220+h%150,step=.08+(h%3)*.006,wave=['triangle','square','sawtooth'][h%3],gain=wave==='triangle'?.9:.45;
  if(child){base=woman||!man?600:540;step=.068;wave='triangle';gain=.8;}
  else if(elder){base=woman?265:140;step=.1;wave=h%2?'sine':'triangle';gain=1;}
  return {base:base*(1+((h>>>4)%13-6)/100),step,wave,gain};
}
export const PLAYER_VOICE={base:320,step:.074,wave:'triangle',gain:.55};

/* ---- bank speaker ---- */
const langOf=v=>String(v?.lang||'').toLowerCase().replace('_','-');
function pickVoice(want){
  const synth=globalThis.speechSynthesis;if(!synth)return null;
  let list=[];try{list=synth.getVoices()||[];}catch{/* no voices */}
  const fit=list.filter(v=>langOf(v).split('-')[0]===want);
  if(!fit.length)return null;
  const score=v=>(langOf(v)===(want==='vi'?'vi-vn':'en-us')?4:0)+(v.localService?2:0)+(/linh|an\b|female|nữ|samantha|google/i.test(v.name||'')?1:0);
  return fit.sort((a,b)=>score(b)-score(a))[0];
}
export function bankText(amounts,en){
  const total=amounts.reduce((a,b)=>a+b,0),n=amounts.length;
  return en?(n>1?`Received ${n} payments, ${total} coins`:`Received ${total} coins`)
    :(n>1?`Đã nhận ${n} khoản, ${total} xu`:`Đã nhận ${total} xu`);
}
/** The spoken line for what came in within one window: [{amount, kind:'shop'|'salary'|'wallet'|'account'}]. */
export function moneyText(items,en){
  if(items.every(x=>x.kind==='shop'))return bankText(items.map(x=>x.amount),en);
  const total=items.reduce((a,x)=>a+x.amount,0),all=k=>items.every(x=>x.kind===k);
  if(all('salary'))return en?`Salary received, ${total} coins`:`Đã nhận lương ${total} xu`;
  if(all('account'))return en?`Your account just received ${total} coins`:`Tài khoản vừa nhận thêm ${total} xu`;
  if(all('wallet'))return en?`Your wallet just received ${total} coins`:`Ví vừa nhận thêm ${total} xu`;
  return en?`You just received ${total} coins`:`Vừa nhận thêm ${total} xu`;
}
/** Worth reading out: shop transfers and pay always, anything else from VOICE_MIN xu (not every 1 xu). */
export const worthSaying=items=>items.some(x=>x.kind==='shop'||x.kind==='salary')||items.reduce((a,x)=>a+x.amount,0)>=VOICE_MIN;

/* ---- money in: the journey wallet (its history rows) and the bank account ---- */
/** What the incoming-money check needs from a state (journey.history is newest first, at most 30 rows). */
export function moneySnap(state){
  const j=state?.journey;if(!j||typeof j.wallet!=='number')return null;
  return {who:String(state.name??''),day:j.life_day||0,wallet:j.wallet,hist:Array.isArray(j.history)?j.history:[],
    bank:typeof j.bank?.balance==='number'?j.bank.balance:null};
}
const rowKey=r=>r?`${r.day}|${r.amount}|${r.kind}|${r.label}|${r.career??''}`:'';
/** Money that came in between two snapshots: the new positive wallet rows (salary told apart), else the wallet's
 * rise; plus the bank account's rise. Another player or an older day (sign-in, reset): nothing. */
export function moneyIn(prev,now){
  if(!prev||!now||prev.who!==now.who||now.day<prev.day)return [];
  const out=[],dw=now.wallet-prev.wallet;
  if(dw){
    let rows=null;
    if(!prev.hist.length)rows=now.hist;
    else{const top=rowKey(prev.hist[0]),next=rowKey(prev.hist[1]);
      for(let k=0;k<now.hist.length&&k<=30;k++)if(rowKey(now.hist[k])===top&&rowKey(now.hist[k+1])===next){rows=now.hist.slice(0,k);break;}}
    if(rows&&rows.reduce((a,r)=>a+(Number(r.amount)||0),0)===dw){
      for(const r of rows)if(r.amount>0)out.push({amount:r.amount,kind:r.kind==='salary'?'salary':'wallet'});
    }else if(dw>0)out.push({amount:dw,kind:'wallet'});
  }
  if(prev.bank!=null&&now.bank!=null&&now.bank>prev.bank)out.push({amount:now.bank-prev.bank,kind:'account'});
  return out;
}

function chip(text){
  const el=document.createElement('div');el.className='bank-chip';el.setAttribute('role','status');el.textContent=text;
  (document.querySelector('dialog[open]')||document.body).append(el);setTimeout(()=>{el.classList.add('leaving');setTimeout(()=>el.remove(),320);},2400);
}

/** Cài đặt → Âm thanh: the four switches (labels follow the language here: new text, no pack entry yet). */
export function soundToggles(s,toggle){
  const en=s.lang==='en',off=s.sound===false;
  const note=(vi,e)=>(en?e:vi)+(off?(en?' Off while action sounds are off.':' Đang tắt vì Âm thanh thao tác tắt.'):'');
  return `<section class="settings-block"><h3>${en?'Voices & details':'Giọng & chi tiết'}</h3>
    ${toggle('moneyTing',en?'“Ting ting” when money comes in':'Tiếng ting ting khi nhận tiền',s.moneyTing!==false,note('Lương, quà, khách chuyển khoản… tiền về là nghe “ting ting” như app ngân hàng.','Pay, gifts, customer transfers… a bank-app chime when money lands.'))}
    ${toggle('bankVoice',en?'Read the amount aloud':'Giọng đọc số tiền',s.bankVoice!==false,note('Đọc số tiền vừa về như loa ngân hàng: “Đã nhận 50 xu”. Khoản dưới 10 xu chỉ ting ting.','Reads what just came in, like a bank speaker: “Received 50 coins”. Under 10 coins: just the chime.'))}
    ${toggle('npcVoices',en?'Character voices':'Giọng nhân vật',s.npcVoices!==false,note('Nhân vật “líu lo” vài tiếng khi nói, mỗi người một giọng.','Characters babble a little when they talk, each in their own voice.'))}
    ${toggle('detailSfx',en?'Detail sounds':'Âm thanh chi tiết',s.detailSfx!==false,note('Tiếng thu ngân, chuông cửa, lật giấy…','Coins, cash register, door bell, paper rustle…'))}
    ${isIOS()?`<p class="small muted">${en?'On iPhone, silent mode (the side switch) mutes action sounds and voices. Switch it off to hear them.':'Trên iPhone, chế độ im lặng (nút gạt bên hông) sẽ tắt âm thanh thao tác và giọng nhân vật. Gạt tắt để nghe.'}</p>`:''}
  </section>`;
}

export function soundsBoot({api,world,sound}){
  const settings=()=>api.state?.settings||{};
  let last=null,delta=null,bell=0,chimeAt=0;
  const queue=[];let first=0,timer=0;

  /* speech needs a gesture on iOS: the first tap speaks an empty line (and asks Chrome to load its voices). */
  let warmed=false;
  const warm=()=>{
    if(warmed)return;warmed=true;
    const synth=globalThis.speechSynthesis,s=settings();if(!synth||s.bankVoice===false||s.sound===false){warmed=false;return;}
    try{synth.getVoices();const u=new SpeechSynthesisUtterance(' ');u.volume=0;synth.speak(u);}catch{/* no speech */}
  };
  addEventListener('pointerdown',warm,{capture:true,passive:true});
  addEventListener('keydown',warm,{capture:true,passive:true});

  /* "ting ting": the recorded bell, fetched on the first tap with sound on (audio.js loadSample) */
  const tingUrl=()=>globalThis.__mnlBoot?.asset?.(TING_URL)||TING_URL;
  const fetchTing=()=>loadSample(tingUrl()).then(buf=>{if(buf)setTing(buf);return buf;});
  let fetched=false;
  const prefetch=()=>{const s=settings();if(fetched||!api.state||s.sound===false||s.moneyTing===false&&s.detailSfx===false)return;fetched=true;fetchTing();};
  addEventListener('pointerdown',prefetch,{capture:true,passive:true});
  addEventListener('keydown',prefetch,{capture:true,passive:true});
  // Not loaded yet (the first payment right after the first tap): play when it is, if that is still "now".
  // It could not be loaded at all (offline): the synthesised dings.
  function ting(){const asked=Date.now();fetchTing().then(()=>{if(Date.now()-asked<1200)sound.ting();});}

  function flush(){
    clearTimeout(timer);timer=0;const list=queue.splice(0);first=0;
    const s=settings();if(!list.length||s.sound===false)return;
    const ding=s.moneyTing!==false,speak=s.bankVoice!==false&&worthSaying(list);
    if(!ding&&!speak)return;
    const en=s.lang==='en',total=list.reduce((a,x)=>a+x.amount,0),note=`🔔 +${total} ${en?'coins':'xu'}`;
    sound.configure(s);if(ding)ting();
    if(!speak)return;
    const voice=pickVoice(en?'en':'vi');
    if(!voice){chip(note);return;}
    setTimeout(()=>{
      try{
        const u=new SpeechSynthesisUtterance(moneyText(list,en));
        u.voice=voice;u.lang=en?(langOf(voice).startsWith('en-')?voice.lang.replace('_','-'):'en-US'):'vi-VN';
        u.rate=en?1.05:1.12;u.pitch=1.05;u.volume=Math.max(.2,Math.min(1,(s.sfxVolume??70)/70));
        sound.hush();globalThis.speechSynthesis.speak(u);
      }catch{chip(note);}
    },ding?SAY_DELAY:0);
  }
  /** items: [{amount, kind}] (moneyText). */
  function money(items){
    const now=Date.now();
    for(const x of items)if(Number.isInteger(x?.amount)&&x.amount>0)queue.push(x);
    if(!queue.length)return;
    first||=now;clearTimeout(timer);
    // quiet for 0.6 s, or 1.5 s after the first payment at most: one announcement for a rush.
    timer=setTimeout(flush,Math.max(0,Math.min(QUIET,first+WINDOW-now)));
  }
  const bank=amounts=>money(amounts.map(amount=>({amount,kind:'shop'})));
  let lastMoney=moneySnap(api.state);
  function onMoney(){const now=moneySnap(api.state),got=moneyIn(lastMoney,now);lastMoney=now;if(got.length)money(got);}

  const snap=state=>{
    const id=state?.current,c=id&&state.careers?.[id];if(!c||!Array.isArray(c.tasks))return null;
    return {id,money:c.money,level:c.level,tasks:new Map(c.tasks.map(t=>[t.id,{status:t.status,stage:t.stage??t.step??null}]))};
  };
  function onState(){
    const now=snap(api.state),prev=last;last=now;delta=null;
    if(!now||!prev||now.id!==prev.id)return;
    const d={money:(now.money||0)-(prev.money||0),arrived:false,completed:false,step:false};
    for(const [id,t] of now.tasks){
      const p=prev.tasks.get(id);
      if(!p){if(!ENDED.has(t.status))d.arrived=true;continue;}
      if(ENDED.has(t.status)&&!ENDED.has(p.status))d.completed=true;
      else if(!ENDED.has(t.status)&&(t.status!==p.status||t.stage!==p.stage))d.step=true;
    }
    delta=d;
    const s=settings();if(s.sound===false||s.detailSfx===false)return;
    sound.configure(s);
    const t=Date.now();
    if(now.level>prev.level&&t-chimeAt>1500){chimeAt=t;sound.chime();}
    if(d.arrived&&t-bell>2000){bell=t;sound.doorbell();}
  }
  function onResult(e){
    const {action,result={}}=e.detail||{},d=delta;delta=null;
    if(Array.isArray(result.bank)&&result.bank.length)bank(result.bank);
    const s=settings();if(s.sound===false||s.detailSfx===false)return;
    sound.configure(s);
    if(action==='end_day'){const t=Date.now();if(t-chimeAt>1500){chimeAt=t;sound.chime();}return;}
    if(!d)return;
    if(d.money>0&&!result.bank?.length){if(d.completed)sound.register();else sound.coins();}
    else if(d.step&&!d.completed&&!result.celebrate&&result.correct!==false&&!result.refused)sound.pop();
  }
  const safe=fn=>(...a)=>{try{fn(...a);}catch(error){console.warn('sounds',error);}};
  api.addEventListener('state',safe(onState));
  api.addEventListener('state',safe(onMoney));
  api.addEventListener('result',safe(onResult));

  /* speech bubbles on the canvas: NPC babble, the player's own lines (no npc) in the player's voice */
  const npc=id=>api.content?.npcs?.find(n=>n.id===id);
  const say=world.say.bind(world);
  world.say=(text,id=null)=>{
    say(text,id);
    try{const s=settings();if(s.sound!==false&&s.npcVoices!==false){sound.configure(s);sound.babble(text,id?voiceOf(id,npc(id)):PLAYER_VOICE);}}catch{/* silent */}
  };
  // The player's chat line (v4/ai-chat.js #chatForm): read before app.js clears the box.
  document.addEventListener('submit',e=>{
    if(e.target?.id!=='chatForm')return;
    const s=settings(),text=e.target.querySelector('#chat-input')?.value;
    if(text&&s.sound!==false&&s.npcVoices!==false){sound.configure(s);sound.babble(text,PLAYER_VOICE);}
  },true);
  // Story and chapter scenes (v4/stories.js, v4/journey.js): the first NPC line not heard yet in an open dialog
  // babbles once (a scene that shows several lines at once: its first one). Closed: heard again next time.
  const heard=new Set();let scanning=false;
  const scan=()=>{
    scanning=false;
    const boxes=document.querySelectorAll('dialog[open] .jr-lines');
    if(!boxes.length){heard.clear();return;}
    let say=null;
    for(const box of boxes)for(const el of box.querySelectorAll('.jr-line:not(.me)')){
      const name=el.querySelector('.jr-bubble b')?.textContent||'',text=el.querySelector('.jr-bubble p')?.textContent||'',key=`${name}|${text}`;
      if(text&&!heard.has(key)){heard.add(key);say??=[name,text];}
    }
    const s=settings();
    if(say&&s.sound!==false&&s.npcVoices!==false){sound.configure(s);sound.babble(say[1],voiceOf(say[0],{display_name:say[0]}));}
  };
  const lineAdded=n=>n.nodeType===1&&(n.classList.contains('jr-line')||n.classList.contains('jr-lines')||Boolean(n.querySelector?.('.jr-line')));
  new MutationObserver(list=>{
    if(scanning)return;
    for(const m of list)if(m.type==='attributes'?m.target.tagName==='DIALOG':[...m.addedNodes].some(lineAdded)){scanning=true;setTimeout(scan,60);return;}
  }).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['open']});
  // A sheet slides open: paper rustle.
  const sheet=document.getElementById('sheet');
  if(sheet)new MutationObserver(()=>{if(sheet.open){const s=settings();if(s.sound!==false&&s.detailSfx!==false){sound.configure(s);sound.paper();}}})
    .observe(sheet,{attributes:true,attributeFilter:['open']});
  return {bank,money,flush};
}
