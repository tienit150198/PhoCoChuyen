/** Character voices, detail sounds and the bank speaker ("loa báo tiền").
 *
 * - Giọng nhân vật: every speech bubble (world.say) and chat line plays a short syllable babble
 *   (audio.js Sound.babble) in the speaker's own pitch: children high, elders low, one timbre per NPC.
 * - Âm thanh chi tiết: coins / cash register when money comes in, a pop for a finished step, a chime for
 *   the day's close and level ups, the door bell for a new customer, a paper rustle when a sheet opens.
 * - Loa báo tiền: a transfer / QR payment into the player's own shop (the server marks it: result.bank,
 *   game/bank_speaker.py) plays "ting ting" and reads "Đã nhận N xu" with a Vietnamese voice
 *   (speechSynthesis), coalescing payments that land within ~1.5 s. No Vietnamese voice: ting ting and
 *   a "🔔 +N xu" chip, never another language. English UI: "Received N coins" with an English voice.
 *
 * Nothing runs before the first tap: listeners only. Nodes are made per sound; nothing is fetched. */
const ENDED=new Set(['completed','referred','cancelled']);
const isIOS=()=>/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
const WINDOW=1500,QUIET=600,SAY_DELAY=420;

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
function chip(text){
  const el=document.createElement('div');el.className='bank-chip';el.setAttribute('role','status');el.textContent=text;
  (document.querySelector('dialog[open]')||document.body).append(el);setTimeout(()=>{el.classList.add('leaving');setTimeout(()=>el.remove(),320);},2400);
}

/** Cài đặt → Âm thanh: the three switches (labels follow the language here: new text, no pack entry yet). */
export function soundToggles(s,toggle){
  const en=s.lang==='en',off=s.sound===false;
  const note=(vi,e)=>(en?e:vi)+(off?(en?' Off while action sounds are off.':' Đang tắt vì Âm thanh thao tác tắt.'):'');
  return `<section class="settings-block"><h3>${en?'Voices & details':'Giọng & chi tiết'}</h3>
    ${toggle('npcVoices',en?'Character voices':'Giọng nhân vật',s.npcVoices!==false,note('Nhân vật “líu lo” khi nói.','Characters babble when they talk.'))}
    ${toggle('detailSfx',en?'Detail sounds':'Âm thanh chi tiết',s.detailSfx!==false,note('Ting ting tiền về, chuông cửa, lật giấy…','Coins, door bell, paper rustle…'))}
    ${toggle('bankVoice',en?'Payment speaker (reads the amount)':'Loa báo tiền (đọc số tiền)',s.bankVoice!==false,note('Khách chuyển khoản vào tiệm: loa đọc “Đã nhận … xu”.','A customer pays the shop by transfer: the speaker reads “Received … coins”.'))}
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

  function flush(){
    clearTimeout(timer);timer=0;const list=queue.splice(0);first=0;
    const s=settings();if(!list.length||s.bankVoice===false||s.sound===false)return;
    const en=s.lang==='en',total=list.reduce((a,b)=>a+b,0);
    sound.configure(s);sound.ting();
    const voice=pickVoice(en?'en':'vi');
    if(!voice){chip(`🔔 +${total} ${en?'coins':'xu'}`);return;}
    setTimeout(()=>{
      try{
        const u=new SpeechSynthesisUtterance(bankText(list,en));
        u.voice=voice;u.lang=en?(langOf(voice).startsWith('en-')?voice.lang.replace('_','-'):'en-US'):'vi-VN';
        u.rate=en?1.05:1.12;u.pitch=1.05;u.volume=Math.max(.2,Math.min(1,(s.sfxVolume??70)/70));
        sound.hush();globalThis.speechSynthesis.speak(u);
      }catch{chip(`🔔 +${total} ${en?'coins':'xu'}`);}
    },SAY_DELAY);
  }
  function bank(amounts){
    const now=Date.now();
    for(const a of amounts)if(Number.isInteger(a)&&a>0)queue.push(a);
    if(!queue.length)return;
    first||=now;clearTimeout(timer);
    // quiet for 0.6 s, or 1.5 s after the first payment at most: one announcement for a rush.
    timer=setTimeout(flush,Math.max(0,Math.min(QUIET,first+WINDOW-now)));
  }

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
  // A sheet slides open: paper rustle.
  const sheet=document.getElementById('sheet');
  if(sheet)new MutationObserver(()=>{if(sheet.open){const s=settings();if(s.sound!==false&&s.detailSfx!==false){sound.configure(s);sound.paper();}}})
    .observe(sheet,{attributes:true,attributeFilter:['open']});
  return {bank,flush};
}
