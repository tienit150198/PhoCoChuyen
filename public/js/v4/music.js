/** Background music: looping CC0 tracks from public/music (sources and
 * licences in public/music/CREDITS.md). Each career has its own track;
 * "Êm dịu" and "Tươi vui" use one track everywhere. Tracks are fetched and
 * decoded into WebAudio buffers: loops are gap-free, the volume slider works
 * on iPhone, and the server needs no Range requests. Changing career
 * crossfades; hiding the tab suspends the context so the song resumes in place. */
const FILES={cider:'apple-cider',springs:'hot-springs-town',lullaby:'happy-lullaby',morning:'good-morning',urban:'urban-shop',puzzle:'cozy-puzzle'};
const BY_CAREER={
  restaurant:'cider',cafe_bakery:'cider',milk_tea:'cider',grocery:'cider',
  florist:'springs',farm:'springs',homestay:'springs',tour_guide:'springs',
  mother_baby:'lullaby',pet_care:'lullaby',pharmacy:'lullaby',
  teacher:'morning',salon:'morning',customer_care:'morning',
  delivery:'urban',repair:'urban',
  accounting:'puzzle',corp_accounting:'puzzle',tax_payroll:'puzzle',group_accounting:'puzzle',
};
const MOOD={calm:'lullaby',bright:'urban'};
const FADE=1.5;

export class Music{
  constructor(){this.ctx=null;this.on=false;this.volume=.45;this.hidden=false;this.want='cider';this.cur=null;this.pending=null;this.buffers=new Map();}
  // armed by the first tap/key (shell.js): a song is 0.3-1.6 MB, never fetched while the game is still loading.
  unlock(){this.armed=true;if(this.ctx?.state==='suspended'&&this.on&&!this.hidden)this.ctx.resume().catch(()=>{});this.refresh();}
  setHidden(h){this.hidden=h;this.refresh();}
  configure({on,volume,track,career}){
    this.on=!!on&&track!=='off';this.volume=Math.max(0,Math.min(1,(volume??45)/100));
    this.want=MOOD[track]||BY_CAREER[career]||'cider';
    if(this.master)this.master.gain.setTargetAtTime(this.level(),this.ctx.currentTime,.3);
    this.refresh();
  }
  level(){return this.volume*.7;}
  init(){
    if(this.ctx)return;
    const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;
    // 32 kHz keeps a decoded song near 25 MB (tracks are mono 32 kHz anyway).
    try{this.ctx=new AC({sampleRate:32000});}catch{this.ctx=new AC();}
    this.master=this.ctx.createGain();this.master.gain.value=this.level();this.master.connect(this.ctx.destination);
  }
  refresh(){
    if(!(this.on&&!this.hidden)){if(this.ctx?.state==='running')this.ctx.suspend().catch(()=>{});return;}
    if(!this.armed)return;
    this.init();if(!this.ctx)return;
    if(this.ctx.state==='suspended')this.ctx.resume().catch(()=>{});
    if(this.cur?.name!==this.want&&this.pending!==this.want)this.play(this.want);
  }
  load(name){
    if(!this.buffers.has(name)){
      const p=fetch(globalThis.__mnlBoot?.asset?.(`/music/${FILES[name]}.mp3`)||`/music/${FILES[name]}.mp3`).then(r=>{if(!r.ok)throw new Error(r.status);return r.arrayBuffer();})
        .then(data=>new Promise((ok,fail)=>this.ctx.decodeAudioData(data,ok,fail)));  // callback form: older Safari
      this.buffers.set(name,p);p.catch(()=>this.buffers.delete(name));
    }
    return this.buffers.get(name);
  }
  async play(name){
    this.pending=name;
    let buf;try{buf=await this.load(name);}catch{if(this.pending===name)this.pending=null;return;}  // silent: the game plays fine without music
    if(this.pending!==name)return;
    this.pending=null;
    const c=this.ctx,t=c.currentTime,old=this.cur,g=c.createGain(),src=c.createBufferSource();
    g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(1,t+FADE);g.connect(this.master);
    src.buffer=buf;src.loop=true;src.connect(g);src.start(t);
    this.cur={name,src,g};
    if(old){old.g.gain.cancelScheduledValues(t);old.g.gain.setValueAtTime(old.g.gain.value,t);old.g.gain.linearRampToValueAtTime(0,t+FADE);old.src.stop(t+FADE+.05);}
    // A decoded song is tens of MB: keep only the one playing.
    for(const k of [...this.buffers.keys()])if(k!==name)this.buffers.delete(k);
  }
}
