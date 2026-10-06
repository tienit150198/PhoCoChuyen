/** Background music: looping CC0 tracks from public/music (sources and
 * licences in public/music/CREDITS.md). Each career has its own track;
 * "Êm dịu" and "Tươi vui" use one track everywhere. Tracks are decoded into
 * WebAudio buffers: loops are gap-free, the volume slider works on iPhone, and
 * the server needs no Range requests. Nothing is fetched before the first tap.
 *
 * - One AudioContext for the page (audio.js): every tap starts it, so music switched on after a server
 *   round trip still plays on iPhone (a context of its own, made outside a tap, stayed silent there).
 * - A song streams: the first ~20 s play as soon as they are in (about a second on a slow phone
 *   network), then the whole song takes over at the same sample and loops.
 * - Changing career crossfades; hiding the tab pauses the context so the song resumes in place;
 *   switching music off stops the song and frees its buffer (tens of MB). */
import {audioContext,wantAudio,onGesture,onDuck,ducked} from '../audio.js';

const FILES={cider:'apple-cider',springs:'hot-springs-town',lullaby:'happy-lullaby',morning:'good-morning',urban:'urban-shop',puzzle:'cozy-puzzle'};
const BY_CAREER={
  restaurant:'cider',cafe_bakery:'cider',milk_tea:'cider',grocery:'cider',
  florist:'springs',farm:'springs',homestay:'springs',tour_guide:'springs',
  mother_baby:'lullaby',pet_care:'lullaby',pharmacy:'lullaby',
  teacher:'morning',salon:'morning',customer_care:'morning',
  delivery:'urban',repair:'urban',
  accounting:'puzzle',corp_accounting:'puzzle',tax_payroll:'puzzle',group_accounting:'puzzle',
  hr_admin:'puzzle',secretary:'puzzle',it_helpdesk:'puzzle',
  oil:'urban',
};
const MOOD={calm:'lullaby',bright:'urban'};
const FADE=1.5;
const HEAD=160*1024;  // ~20 s of a 64 kbps track (public/music/CREDITS.md): enough to start while the rest arrives
const url=name=>globalThis.__mnlBoot?.asset?.(`/music/${FILES[name]}.mp3`)||`/music/${FILES[name]}.mp3`;

/** Decode at 32 kHz (the tracks are mono 32 kHz): a song stays near 25 MB instead of ~38 MB at 48 kHz. */
function decode(data,ctx){
  const OAC=window.OfflineAudioContext||window.webkitOfflineAudioContext;
  let dec=ctx;try{if(OAC)dec=new OAC(1,1,32000);}catch{/* rate not supported: the page context */}
  return new Promise((ok,fail)=>{const p=dec.decodeAudioData(data,ok,fail);p?.catch?.(()=>{/* fail() had it */});});  // callback form: older Safari
}

/** The whole file; onHead(bytes) once its first HEAD bytes are in, while the rest is still downloading. */
async function download(name,onHead){
  const r=await fetch(url(name));if(!r.ok)throw new Error(r.status);
  const total=Number(r.headers.get('Content-Length'))||0;
  if(!r.body?.getReader||r.headers.get('Content-Encoding')||total<HEAD*1.5)return r.arrayBuffer();
  const reader=r.body.getReader();let all=new Uint8Array(total),got=0,told=false;
  for(;;){
    const {done,value}=await reader.read();if(done)break;
    if(got+value.length>all.length){const more=new Uint8Array(Math.max(all.length*2,got+value.length));more.set(all.subarray(0,got));all=more;}
    all.set(value,got);got+=value.length;
    if(!told&&got>=HEAD){told=true;try{onHead(all.slice(0,got).buffer);}catch{/* music only */}}
  }
  return all.buffer.slice(0,got);
}

export class Music{
  constructor(){this.ctx=null;this.on=false;this.volume=.45;this.hidden=false;this.armed=false;this.want='cider';this.cur=null;this.pending=null;this.buffers=new Map();
    // Every tap (inside the gesture): arm, and start the song if it is on.
    onGesture(()=>this.unlock());
    // The wedding party plays its own music: this one fades out meanwhile and comes back after.
    onDuck(()=>{if(this.master)this.master.gain.setTargetAtTime(this.level(),this.ctx.currentTime,.4);});}
  // Armed by the first tap/key: a song is 0.3-1.6 MB, never fetched while the game is still loading.
  unlock(){this.armed=true;this.refresh();}
  setHidden(h){this.hidden=h;this.refresh();}
  configure({on,volume,track,career}){
    this.on=!!on&&track!=='off';this.volume=Math.max(0,Math.min(1,(volume??45)/100));
    this.want=MOOD[track]||BY_CAREER[career]||'cider';
    if(this.master)this.master.gain.setTargetAtTime(this.level(),this.ctx.currentTime,.3);
    this.refresh();
  }
  level(){return ducked()?0:this.volume*.7;}
  init(){
    if(this.ctx)return;
    this.ctx=audioContext();if(!this.ctx)return;
    this.master=this.ctx.createGain();this.master.gain.value=this.level();this.master.connect(this.ctx.destination);
  }
  refresh(){
    wantAudio('music',this.on);
    if(!this.on){if(this.cur||this.pending)this.stop();return;}
    if(!this.armed||this.hidden)return;
    this.init();if(!this.ctx)return;
    // Inside a tap this starts the context (iPhone); elsewhere it works once a tap has started it before.
    if(this.ctx.state!=='running'&&this.ctx.state!=='closed')this.ctx.resume().catch(()=>{/* the next tap */});
    if(this.cur?.name!==this.want&&this.pending!==this.want)this.play(this.want);
  }
  /** Music switched off: fade out and free the song. */
  stop(){
    this.pending=null;const cur=this.cur;this.cur=null;this.buffers.clear();
    if(cur&&this.ctx){const t=this.ctx.currentTime;cur.g.gain.cancelScheduledValues(t);cur.g.gain.setValueAtTime(cur.g.gain.value,t);cur.g.gain.linearRampToValueAtTime(0,t+.3);try{cur.src.stop(t+.35);}catch{/* not started */}}
  }
  /** A source for `buf` fading in over the playing song (which fades out). */
  start(name,buf,head){
    const c=this.ctx,t=c.currentTime,old=this.cur,g=c.createGain(),src=c.createBufferSource();
    g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(1,t+FADE);g.connect(this.master);
    src.buffer=buf;src.loop=!head;src.connect(g);src.start(t);
    this.cur={name,src,g,t0:t,head};
    if(old){old.g.gain.cancelScheduledValues(t);old.g.gain.setValueAtTime(old.g.gain.value,t);old.g.gain.linearRampToValueAtTime(0,t+FADE);try{old.src.stop(t+FADE+.05);}catch{/* not started */}}
  }
  async play(name){
    this.pending=name;
    if(!this.buffers.has(name)){
      const onHead=bytes=>decode(bytes,this.ctx).then(buf=>{if(this.pending===name&&this.cur?.name!==name)this.start(name,buf,true);}).catch(()=>{/* wait for the whole song */});
      const p=download(name,onHead).then(data=>decode(data,this.ctx));
      this.buffers.set(name,p);p.catch(()=>this.buffers.delete(name));
    }
    let buf;try{buf=await this.buffers.get(name);}catch{if(this.pending===name)this.pending=null;return;}  // silent: the game plays fine without music
    if(this.pending!==name)return;
    this.pending=null;
    const cur=this.cur,c=this.ctx;
    if(cur?.name===name&&cur.head){
      // The first seconds are playing: the whole song carries on from the same sample, then loops.
      const at=c.currentTime+.08,pos=at-cur.t0;
      if(pos<Math.min(cur.src.buffer.duration,buf.duration)-.05){
        const src=c.createBufferSource();src.buffer=buf;src.loop=true;src.connect(cur.g);src.start(at,pos);
        try{cur.src.stop(at);}catch{/* ended */}
        this.cur={name,src,g:cur.g,t0:cur.t0,head:false};
      }else this.start(name,buf,false);  // the head ran out first: start the song again
    }else this.start(name,buf,false);
    // A decoded song is tens of MB: keep only the one playing.
    for(const k of [...this.buffers.keys()])if(k!==name)this.buffers.delete(k);
  }
}
