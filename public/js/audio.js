/** Tiny original synthesised sounds, and one recorded CC0 bell for "ting ting" (public/audio/sfx/CREDITS.md). */
// One AudioContext for the page: every Sound (app.js, the career desks, v4/sounds.js) and the background music
// (v4/music.js). Phones cap how many can run, and iOS lets a context start only inside a tap.
let shared=null,noise=null,primed=false;
const AC=()=>window.AudioContext||window.webkitAudioContext;
const wants=new Set(),hooks=new Set();  // wants: 'sfx' (action sounds on), 'music' (background music on)
/** The page's AudioContext, created on first use (suspended until a tap starts it); null without Web Audio. */
export function audioContext(){try{shared??=new (AC())();}catch{/* no Web Audio */}return shared;}
const doc=globalThis.document,hidden=()=>Boolean(doc?.hidden);
/** Run the context when someone wants sound. resume() works only inside a tap/key handler on iOS Safari until
 * the context has once been started by one (then anywhere); 'interrupted' (iOS: call, other app) needs it too. */
function wake(){const c=shared;if(c&&wants.size&&!hidden()&&c.state!=='running'&&c.state!=='closed')c.resume().catch(()=>{/* next tap */});}
/** Who needs the context running. Music on: the iPhone plays it like media (through the silent switch);
 * action sounds alone keep the default session and follow the switch. */
export function wantAudio(who,on){
  const had=wants.has(who);if(on)wants.add(who);else wants.delete(who);
  if(had===Boolean(on))return;
  try{const s=navigator.audioSession,type=wants.has('music')?'playback':'auto';if(s&&s.type!==type)s.type=type;}catch{/* no Audio Session API */}
  if(on)wake();
}
/** fn() on every tap/key (inside the gesture): v4/music.js starts a song there. */
export function onGesture(fn){hooks.add(fn);}
/** Who wants the background music to step aside (the wedding party plays its own: v4/wedfeast.js). */
const ducks=new Set(),duckHooks=new Set();
export function duck(who,on){const was=ducks.size>0;if(on)ducks.add(who);else ducks.delete(who);if(was!==ducks.size>0)for(const fn of duckHooks){try{fn(ducks.size>0);}catch{/* music only */}}}
export const ducked=()=>ducks.size>0;
/** fn(ducked) when the background music should step aside or come back (v4/music.js). */
export function onDuck(fn){duckHooks.add(fn);}
/** Inside a tap/key: start the context. The first tap starts it even when nothing is wanted yet (then pauses
 * it again): iOS lifts its tap-only rule for good once a tap started a context, so a sound switched on later
 * (after a server round trip, outside any tap) plays at once. */
function start(){
  if(hidden()||(primed&&!wants.size))return;
  const c=audioContext();if(!c||c.state==='closed')return;
  if(c.state==='running'){primed=true;return;}
  c.resume().then(()=>{primed=true;if(!wants.size&&c.state==='running')c.suspend().catch(()=>{});}).catch(()=>{/* the next tap */});
}
// Every tap, not only the first one and not only on [data-action] buttons (the Nhạc nền switch is a checkbox).
// pointerdown/touchstart are not a user activation; pointerup/touchend/click/keydown are.
function gesture(){start();for(const fn of hooks){try{fn();}catch{/* silent */}}}
if(doc?.addEventListener){
  for(const type of ['pointerup','touchend','click','keydown'])addEventListener(type,gesture,{capture:true,passive:true});
  // Hidden tab: stop the audio thread (the music resumes in place when the tab is back).
  doc.addEventListener('visibilitychange',()=>{if(hidden()){if(shared?.state==='running')shared.suspend().catch(()=>{});}else wake();});
}
/* Recorded sounds (public/audio/sfx/, licences in CREDITS.md there): fetched once, decoded into the shared context. */
const decoded=new Map();  // url -> Promise<AudioBuffer|null>
export function loadSample(url){
  if(!decoded.has(url)){const c=audioContext();decoded.set(url,!c||!globalThis.fetch?Promise.resolve(null)
    :fetch(url,{credentials:'same-origin'}).then(r=>r.ok?r.arrayBuffer():null).then(b=>b&&new Promise((ok,no)=>c.decodeAudioData(b,ok,no))).catch(()=>null));}
  return decoded.get(url);
}
let tingBuf=null;
/** The recorded bell for Sound.ting() (v4/sounds.js loads it). */
export function setTing(buf){tingBuf=buf||null;}
// Vietnamese tone marks (NFD) → pitch glide of a babble syllable: sắc up, huyền down, hỏi dip, ngã up-hop, nặng short low.
const TONES={'\u0301':[1,1.18],'\u0300':[1,.84],'\u0309':[.94,1.04],'\u0303':[1.02,1.2],'\u0323':[.86,.8]};
const VOWEL={a:1500,e:1900,i:2500,o:950,u:750,y:2400};  // brightness of the syllable's filter by its vowel
export class Sound {
  constructor(){this.enabled=true;this.volume=1;this.detail=true;this.voices=true;this.talk=null;}
  get ctx(){return shared;}
  set ctx(value){shared=value;}
  /** Create the (suspended) context ahead of time, in idle time: creating it is slow on phones (~100 ms
   * on a throttled CPU) and used to land on the player's very first tap. unlock() then only resumes it. */
  prepare(){audioContext();}
  unlock(){try{start();}catch{/* Silent play remains fully usable. */}}
  ready(){return !!(shared&&this.enabled&&shared.state!=='closed');}
  tone(freq,time=.08,volume=.045,delay=0,type='sine',out=null){
    if(!this.ready())return;const t=shared.currentTime+delay,o=shared.createOscillator(),g=shared.createGain();o.type=type;o.frequency.value=freq;g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(volume*this.volume,t+.015);g.gain.exponentialRampToValueAtTime(.0001,t+time);o.connect(g);g.connect(out||shared.destination);o.start(t);o.stop(t+time+.03);
  }
  click(){this.tone(660,.07,.024);}
  success(){[523.25,659.25,783.99,1046.5].forEach((f,i)=>this.tone(f,.36,.038,i*.11));}
  error(){this.tone(245,.14,.03);}
  // Background music lives in v4/music.js; this class only plays short UI sounds.
  configure(settings){this.enabled=settings.sound!==false;wantAudio('sfx',this.enabled);this.volume=Math.max(0,Math.min(1.5,(settings.sfxVolume??70)/70));this.detail=settings.detailSfx!==false;this.voices=settings.npcVoices!==false;}
  stopMusic(){}
  /* ---- detail sounds (Cài đặt → Âm thanh chi tiết) ---- */
  bell(freq,delay=0,time=.5,volume=.03){this.tone(freq,time,volume,delay);this.tone(freq*2.76,time*.45,volume*.35,delay);}
  /** "Ting ting": the bank speaker's two bright dings (the caller checks its switch). The recorded bell once
   * v4/sounds.js has loaded it (setTing), else two synthesised dings. */
  ting(){if(tingBuf&&this.sample(tingBuf,0,.32)){this.sample(tingBuf,.17,.27);return;}this.bell(1975.5,0,.32,.026);this.bell(1975.5,.17,.42,.026);}
  /** A decoded recorded sound (loadSample) after `delay` s; false when it cannot play. */
  sample(buf,delay=0,volume=1,rate=1){
    if(!buf||!this.ready())return false;const t=shared.currentTime+delay,src=shared.createBufferSource(),g=shared.createGain();
    src.buffer=buf;src.playbackRate.value=rate;g.gain.value=volume*this.volume;src.connect(g);g.connect(shared.destination);src.start(t);return true;
  }
  coins(){if(this.detail){this.bell(1568,0,.18,.02);this.bell(2093,.07,.26,.02);}}
  /** Cash register "ka-ching": drawer clack, then the bell. */
  register(){if(!this.detail||!this.ready())return;this.hiss(.035,2400,.05,0);[1318.5,1760,2637].forEach((f,i)=>this.bell(f,.06+i*.012,.5,.016));}
  pop(){if(!this.detail||!this.ready())return;const t=shared.currentTime,o=shared.createOscillator(),g=shared.createGain();o.frequency.setValueAtTime(620,t);o.frequency.exponentialRampToValueAtTime(260,t+.07);g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.03*this.volume+.0001,t+.008);g.gain.exponentialRampToValueAtTime(.0001,t+.09);o.connect(g);g.connect(shared.destination);o.start(t);o.stop(t+.12);}
  /** Gentle chime: day closed, level up. */
  chime(){if(this.detail)[783.99,987.77,1174.66,1567.98].forEach((f,i)=>this.bell(f,i*.16,.9,.016));}
  /** Shop door bell: a customer walks in. */
  doorbell(){if(this.detail){this.bell(1318.5,0,.55,.018);this.bell(1046.5,.22,.7,.018);}}
  /** Paper rustle: a sheet slides open. */
  paper(){if(this.detail&&this.ready()){this.hiss(.09,3200,.018,0);this.hiss(.07,4200,.012,.07);}}
  hiss(time,freq,volume,delay){
    if(!this.ready())return;
    if(!noise){const n=Math.floor(shared.sampleRate*.25);noise=shared.createBuffer(1,n,shared.sampleRate);const d=noise.getChannelData(0);for(let i=0;i<n;i++)d[i]=Math.random()*2-1;}
    const t=shared.currentTime+delay,src=shared.createBufferSource(),f=shared.createBiquadFilter(),g=shared.createGain();
    src.buffer=noise;f.type='bandpass';f.frequency.value=freq;f.Q.value=.9;
    g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(volume*this.volume+.0001,t+.012);g.gain.exponentialRampToValueAtTime(.0001,t+time);
    src.connect(f);f.connect(g);g.connect(shared.destination);src.start(t,Math.random()*.1);src.stop(t+time+.02);
  }
  /* ---- character voices (Cài đặt → Giọng nhân vật) ---- */
  /** Cute syllable babble in the Animal Crossing manner: one blip per Vietnamese syllable, tone marks bend
   * the pitch, the vowel colours it. `voice` = {base Hz, wave, step s, gain}. The newest line cuts the old one. */
  babble(text,voice){
    if(!this.voices||!this.ready()||shared.state!=='running')return;
    const words=String(text||'').normalize('NFD').toLowerCase().split(/\s+/).filter(w=>/[a-z]/.test(w));
    if(!words.length)return;
    this.hush();
    const step=voice.step||.085,max=Math.max(1,Math.floor(1.2/step)),t0=shared.currentTime+.02;
    const bus=shared.createGain(),f=shared.createBiquadFilter();
    bus.gain.value=(voice.gain||1)*this.volume;f.type='lowpass';f.Q.value=4;f.connect(bus);bus.connect(shared.destination);
    const o=shared.createOscillator(),env=shared.createGain();o.type=voice.wave||'triangle';env.gain.value=0;o.connect(env);env.connect(f);
    const list=words.length>max?words.filter((_,i)=>i%Math.ceil(words.length/max)===0).slice(0,max):words;
    list.forEach((w,i)=>{
      const t=t0+i*step,[a,b]=TONES[[...w].find(ch=>TONES[ch])]||[1,1],v=VOWEL[w.replace(/[^a-z]/g,'').match(/[aeiouy]/)?.[0]]||1400;
      const jitter=1+((w.charCodeAt(0)*7+i*13)%9-4)/100,p=voice.base*jitter,d=step*(w.includes('\u0323')?0.6:0.78);
      o.frequency.setValueAtTime(p*a,t);o.frequency.linearRampToValueAtTime(p*b,t+d);
      f.frequency.setValueAtTime(v*(voice.base>400?1.25:1),t);
      env.gain.setValueAtTime(0,t);env.gain.linearRampToValueAtTime(.05,t+.012);env.gain.setValueAtTime(.05,t+d*.55);env.gain.linearRampToValueAtTime(0,t+d);
    });
    const end=t0+list.length*step+.05;o.start(t0);o.stop(end);
    const talk={bus,end};this.talk=talk;o.onended=()=>{if(this.talk===talk)this.talk=null;try{bus.disconnect();}catch{/* gone */}};
  }
  hush(){const old=this.talk;if(!old||!shared)return;this.talk=null;const t=shared.currentTime;try{old.bus.gain.cancelScheduledValues(t);old.bus.gain.setTargetAtTime(0,t,.012);}catch{/* already stopped */}setTimeout(()=>{try{old.bus.disconnect();}catch{/* gone */}},120);}
}
