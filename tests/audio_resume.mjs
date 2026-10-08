// Background music that plays for some players and not for others (owner report 08/10/2026: "nhạc lúc nghe được
// lúc không"): public/js/audio.js + public/js/v4/music.js against a fake AudioContext / fetch / document.
// Each scenario runs in its own node process (the modules keep page-wide state). Checks: the first tap starts a
// blocked context and the song; hidden/visible, pageshow, a phone interruption and a stuck clock bring the sound
// back; first seconds that ran out before the whole song came, a failed download and a failed decode are tried
// again; career switches never leave two songs or none; the iPhone silent switch (old iOS: silent <audio> keeper,
// Safari 16.4+: navigator.audioSession) and the karaoke room.
// Run: node tests/audio_resume.mjs   (tests/test_audio_resume.py runs it); exits non-zero on failure.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const SELF=fileURLToPath(import.meta.url);
const SCENARIOS=['gesture','visibility','head','switch','retry','decode','ios_old','ios_new','android','hidden_tap','duck'];

if(!process.argv[2]){
  let failed=0;
  for(const name of SCENARIOS){
    try{execFileSync(process.execPath,[SELF,name],{stdio:'pipe',encoding:'utf-8',timeout:30000});console.log(`ok   ${name}`);}
    catch(e){failed++;console.log(`FAIL ${name}\n${e.stdout||''}${e.stderr||''}`);}
  }
  console.log(failed?`${failed} scenario(s) failed`:`${SCENARIOS.length} audio scenarios OK`);
  process.exit(failed?1:0);
}

/* ---------------------------------------------------------------- the fake browser */
const G={gesture:false};
const win=new EventTarget();
globalThis.window=globalThis;
globalThis.addEventListener=(t,f,o)=>win.addEventListener(t,f,o);
globalThis.removeEventListener=(t,f,o)=>win.removeEventListener(t,f,o);
const fire=(t)=>win.dispatchEvent(new Event(t));
/** A user tap: the handlers run inside the gesture. */
function tap(){G.gesture=true;try{fire('pointerup');fire('touchend');fire('click');}finally{G.gesture=false;}}

const elements=[],blobs=new Map();
{const make=URL.createObjectURL.bind(URL);URL.createObjectURL=b=>{const u=make(b);blobs.set(u,b);return u;};}
class FakeAudioEl{
  constructor(){this.paused=true;this.plays=0;this.attrs={};this.loop=false;this.src='';elements.push(this);}
  setAttribute(k,v){this.attrs[k]=v;}
  play(){this.plays++;if(!this.unlocked&&!G.gesture)return Promise.reject(new Error('NotAllowedError'));this.unlocked=true;this.paused=false;return Promise.resolve();}
  pause(){this.paused=true;}
}
const doc=new EventTarget();doc.hidden=false;doc.createElement=tag=>{assert.equal(tag,'audio');return new FakeAudioEl();};
Object.defineProperty(globalThis,'document',{value:doc,configurable:true,writable:true});
const NAV={iphone:{platform:'iPhone',maxTouchPoints:5},android:{platform:'Linux armv8l',maxTouchPoints:5},desktop:{platform:'Win32',maxTouchPoints:0}};
const nav=process.argv[2].startsWith('ios')?{...NAV.iphone}:process.argv[2]==='android'?{...NAV.android}:{...NAV.desktop};
if(process.argv[2]==='ios_new')nav.audioSession={type:'auto'};
Object.defineProperty(globalThis,'navigator',{value:nav,configurable:true,writable:true});
function setHidden(h){doc.hidden=h;doc.dispatchEvent(new Event('visibilitychange'));}

const param=v=>({value:v,targets:[],setValueAtTime(x){this.value=x;},linearRampToValueAtTime(x){this.value=x;},setTargetAtTime(x){this.targets.push(x);this.value=x;},cancelScheduledValues(){},exponentialRampToValueAtTime(x){this.value=x;}});
const contexts=[];
const BPS=8000;  // the tracks are 64 kbps: 8000 bytes a second
function decodeInto(data,ok,fail,self){
  const n=data.byteLength;
  setTimeout(()=>{if(self.failDecode||FakeCtx.failAllDecodes)fail(new Error('EncodingError'));else ok({duration:n/BPS,length:n,sampleRate:self.sampleRate,tag:new Uint8Array(data)[0]});},0);
}
class FakeCtx extends EventTarget{
  constructor(){super();this.state='suspended';this.currentTime=0;this.sampleRate=48000;this.destination={};this.unlocked=false;this.refuse=false;
    this.resumes=0;this.suspends=0;this.sources=[];contexts.push(this);}
  set(s){if(this.state!==s){this.state=s;this.dispatchEvent(new Event('statechange'));}}
  resume(){this.resumes++;
    if(this.refuse)return Promise.reject(new Error('InvalidStateError: interrupted'));
    if(!this.unlocked&&!G.gesture)return Promise.reject(new Error('NotAllowedError'));
    this.unlocked=true;return Promise.resolve().then(()=>this.set('running'));}
  suspend(){this.suspends++;return Promise.resolve().then(()=>this.set('suspended'));}
  createGain(){return {gain:param(1),connect(){},disconnect(){}};}
  createOscillator(){return {frequency:param(0),connect(){},start(){},stop(){}};}
  createBufferSource(){
    const s={buffer:null,loop:false,playing:false,onended:null,playbackRate:param(1),connect(){},disconnect(){},
      start:(t,off=0)=>{s.playing=true;s.offset=off;},
      // stop(when): later (a crossfade) → at advance(); now → at once; onended after it, like a browser
      stop:(when)=>{if(!s.playing)return;if(when>this.currentTime){s.stopAt=when;return;}s.playing=false;Promise.resolve().then(()=>s.onended?.());}};
    this.sources.push(s);return s;
  }
  decodeAudioData(data,ok,fail){decodeInto(data,ok,fail,this);}
  /** The clock moves dt s (when running); crossfaded songs that were due to stop stop. */
  advance(dt){if(this.state!=='running')return;this.currentTime+=dt;for(const s of this.sources)if(s.playing&&s.stopAt<=this.currentTime){s.stopAt=undefined;s.stop();}}
  playing(){return this.sources.filter(s=>s.playing);}
}
class FakeOAC{constructor(ch,len,rate){this.sampleRate=rate;this.failDecode=FakeOAC.fail;}decodeAudioData(data,ok,fail){decodeInto(data,ok,fail,this);}}
globalThis.AudioContext=FakeCtx;globalThis.OfflineAudioContext=FakeOAC;

/** fetch: each call makes a download the scenario feeds (push/finish/error), or follows `fetchPlan`. */
const downloads=[];
let fetchPlan=null;  // (url) => 'reject' | null
function fakeFetch(url,init={}){
  const plan=fetchPlan?.(url);
  if(plan==='reject'){downloads.push({url,rejected:true});return Promise.reject(new TypeError('Load failed'));}
  const d={url,chunks:[],waiters:[],done:false,err:null,total:init.total,signal:init.signal};
  d.push=bytes=>{d.chunks.push(bytes);d.flush();};
  d.finish=()=>{d.done=true;d.flush();};
  d.error=()=>{d.err=new TypeError('network connection was lost');d.flush();};
  d.flush=()=>{while(d.waiters.length&&(d.chunks.length||d.done||d.err)){const w=d.waiters.shift();if(d.chunks.length)w.ok({done:false,value:d.chunks.shift()});else if(d.err)w.no(d.err);else w.ok({done:true});}};
  init.signal?.addEventListener('abort',()=>{d.err=new Error('AbortError');d.flush();});
  downloads.push(d);
  const len=d.len=fetchLen(url);
  return Promise.resolve({ok:true,status:200,
    headers:{get:k=>k==='Content-Length'?String(len):null},
    body:{getReader:()=>({read:()=>new Promise((ok,no)=>{d.waiters.push({ok,no});d.flush();})})},
    arrayBuffer:async()=>{const parts=[];for(;;){const r=await new Promise((ok,no)=>{d.waiters.push({ok,no});d.flush();});if(r.done)break;parts.push(r.value);}
      const all=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let o=0;for(const p of parts){all.set(p,o);o+=p.length;}return all.buffer;}});
}
globalThis.fetch=fakeFetch;
/** Track sizes: small (whole-file path) unless a scenario says otherwise. Byte 0 tags the track. */
let fetchLen=()=>40000;
const TAG={'apple-cider':1,'good-morning':2,'urban-shop':3,'happy-lullaby':4,'hot-springs-town':5,'cozy-puzzle':6};
const tagOf=url=>TAG[/music\/([\w-]+)\.mp3/.exec(url)[1]];
function bytes(url,n){const b=new Uint8Array(n);b[0]=tagOf(url);return b;}
/** Serve download `d` whole (in two chunks). */
function serve(d){const all=bytes(d.url,d.len);d.push(all.subarray(0,Math.floor(d.len/2)));d.push(all.subarray(Math.floor(d.len/2)));d.finish();}
const settle=async(n=6)=>{for(let i=0;i<n;i++)await new Promise(r=>setTimeout(r,0));};
const wait=ms=>new Promise(r=>setTimeout(r,ms));

const audio=await import('../public/js/audio.js');
const {Music}=await import('../public/js/v4/music.js');
const ctx=()=>audio.audioContext();
const playingTags=()=>ctx().playing().map(s=>s.buffer.tag);
function onlySong(tag,loop=true){const p=ctx().playing();assert.equal(p.length,1,`exactly one song playing, got ${p.length}`);assert.equal(p[0].buffer.tag,tag);assert.equal(p[0].loop,loop);}
const ON={on:true,volume:45,track:'auto',career:'grocery'};

/* ---------------------------------------------------------------- scenarios */
const S={
  /** Autoplay: nothing plays before a tap; the first tap starts the context and the song; a refused resume
   * (iOS 'interrupted') is tried again by the next tap. */
  async gesture(){
    const m=new Music();m.configure(ON);await settle();
    assert.equal(downloads.length,0,'nothing fetched before the first tap');
    const c=ctx();c.refuse=true;          // the phone refuses the first time (a call was ringing)
    tap();await settle();
    assert.equal(c.state,'suspended');
    assert.equal(downloads.length,1);assert.match(downloads[0].url,/apple-cider\.mp3$/);
    serve(downloads[0]);await settle();
    assert.equal(c.playing().length,1,'the song is scheduled on the (still suspended) context');
    c.refuse=false;
    audio.audioHealth();await settle();   // outside a tap, before any tap started the context: still blocked
    assert.equal(c.state,'suspended');
    tap();await settle();                 // the next tap
    assert.equal(c.state,'running');onlySong(1);
    tap();tap();await settle();
    onlySong(1);assert.equal(downloads.length,1,'taps never start the song twice');
  },
  /** Hidden/visible, back/forward cache, a phone interruption, a stuck clock: the song comes back, once. */
  async visibility(){
    const m=new Music();m.configure(ON);tap();await settle();serve(downloads[0]);await settle();
    const c=ctx();assert.equal(c.state,'running');onlySong(1);
    const shown=h=>{setHidden(h);m.setHidden(h);};   // v4/shell.js tells the music too
    shown(true);await settle();
    assert.equal(c.state,'suspended');assert.equal(m.hidden,true);
    audio.audioHealth();await settle();assert.equal(c.state,'suspended','hidden: stays paused');
    shown(false);await settle();
    assert.equal(c.state,'running','visible again: resumed without a tap');onlySong(1);
    // A call: the phone interrupts the context while the page stays on screen.
    c.set('interrupted');await settle();
    assert.equal(c.state,'running','interruption ended: resumed');
    // Still ringing: resume refused, then the health check brings it back once the phone allows it.
    c.refuse=true;c.set('interrupted');await settle();assert.equal(c.state,'interrupted');
    c.refuse=false;audio.audioHealth();await settle();assert.equal(c.state,'running');
    // Back/forward cache: the page comes back with the context stopped.
    c.refuse=true;c.set('suspended');await settle();c.refuse=false;
    fire('pageshow');await settle();assert.equal(c.state,'running');
    // A context 'running' whose clock stands still (iPhone after a lock): suspended and resumed.
    const sus=c.suspends;audio.audioHealth();audio.audioHealth();await settle();
    assert.equal(c.suspends,sus+1,'stuck clock: kicked once');assert.equal(c.state,'running');
    c.advance(2.5);audio.audioHealth();c.advance(2.5);audio.audioHealth();await settle();
    assert.equal(c.suspends,sus+1,'a moving clock is left alone');
    onlySong(1);assert.equal(downloads.length,1);
  },
  /** The first seconds play while the song downloads; the download dies: the song is tried again and plays. */
  async head(){
    fetchLen=()=>400000;
    const m=new Music();m.retry=[30,60,90];m.configure(ON);tap();await settle();
    const d=downloads[0],all=bytes(d.url,d.len);
    d.push(all.subarray(0,170*1024));await settle();
    let p=ctx().playing();assert.equal(p.length,1,'the first seconds play');assert.equal(p[0].loop,false);
    d.error();await settle();             // the phone was locked mid-download
    p[0].stop();await settle();           // …and the first seconds ran out
    assert.equal(ctx().playing().length,0);
    await wait(120);await settle();
    assert.equal(downloads.length,2,'tried again');
    serve(downloads[1]);await settle(10);ctx().advance(.5);await settle();
    // the new head may play first; once the whole song is in it is the only one, looping
    p=ctx().playing();assert.equal(p.length,1);assert.equal(p[0].loop,true);assert.equal(p[0].buffer.tag,1);
    // The handoff from head to whole song does not drop the song (the head's onended must not clear it).
    m.configure({...ON,career:'teacher'});await settle();
    const d3=downloads[2],b3=bytes(d3.url,d3.len);d3.push(b3.subarray(0,170*1024));await settle();
    assert.deepEqual(playingTags().sort(),[1,2].sort(),'crossfade: old song fades out while the new head starts');
    d3.push(b3.subarray(170*1024));d3.finish();await settle(10);ctx().advance(2);await settle();
    onlySong(2);
  },
  /** Career switches while songs load: the last wanted song plays, alone; off while loading plays nothing. */
  async switch(){
    const m=new Music();m.configure(ON);tap();await settle();
    const a=downloads[0];
    m.configure({...ON,career:'teacher'});await settle();
    const b=downloads[1];assert.match(b.url,/good-morning/);
    serve(b);await settle();onlySong(2);
    serve(a);await settle();ctx().advance(2);onlySong(2);   // the stale song arrives late: ignored
    // A→B→A while A loads: A plays.
    m.configure({...ON,career:'delivery'});await settle();
    m.configure({...ON,career:'teacher'});await settle();
    assert.equal(downloads.length,3,'B is already playing: switching back needs no download');
    serve(downloads[2]);await settle();
    onlySong(2);   // the song that came back is still the one playing; the abandoned one never starts
    // Off while a song loads: nothing plays when it arrives; on again: it plays.
    m.configure({...ON,career:'florist'});await settle();
    m.configure({...ON,on:false,career:'florist'});await settle();
    serve(downloads[3]);await settle();ctx().advance(1);await settle();
    assert.equal(ctx().playing().length,0,'off: faded out, and the song that came later never starts');
    m.configure({...ON,career:'florist'});await settle();
    serve(downloads[4]);await settle();onlySong(5);
  },
  /** A failed download is tried again, with growing waits; back online tries at once. */
  async retry(){
    let fails=2;fetchPlan=()=>fails-->0?'reject':null;
    const m=new Music();m.retry=[300,900,5000];m.configure(ON);tap();await settle();
    assert.equal(downloads.length,1);assert.equal(ctx().playing().length,0);
    tap();await settle();assert.equal(downloads.length,1,'a tap inside the wait does not hammer the server');
    await wait(450);await settle();assert.equal(downloads.length,2,'first retry');
    await wait(350);await settle();assert.equal(downloads.length,2,'the second wait is longer');
    await wait(800);await settle();assert.equal(downloads.length,3,'second retry');
    serve(downloads[2]);await settle();onlySong(1);
    // Offline again on another song: 'online' retries at once.
    fails=1;m.configure({...ON,career:'teacher'});await settle();
    assert.equal(downloads.length,4);assert.ok(downloads[3].rejected);
    fire('online');await settle();assert.equal(downloads.length,5);
    serve(downloads[4]);await settle();ctx().advance(2);onlySong(2);
  },
  /** The 32 kHz decoder fails (some Safari builds): the page context decodes it; a decode that fails everywhere
   * is tried again later. */
  async decode(){
    FakeOAC.fail=true;
    const m=new Music();m.retry=[30,30];m.configure(ON);tap();await settle();
    serve(downloads[0]);await settle(10);onlySong(1);
    m.configure({...ON,career:'teacher'});await settle();
    FakeCtx.failAllDecodes=true;serve(downloads[1]);await settle(10);
    FakeCtx.failAllDecodes=false;
    await wait(150);await settle();
    assert.equal(downloads.length,3,'a failed decode is tried again');
    serve(downloads[2]);await settle(10);ctx().advance(2);onlySong(2);
  },
  /** iOS 15–16.3 (no navigator.audioSession): a silent looping <audio> plays while music is on and the page is
   * shown, so the ringer switch does not mute the music; never during karaoke. */
  async ios_old(){
    const m=new Music();tap();await settle();
    assert.equal(elements.length,0,'no keeper while music is off');
    m.configure(ON);await settle();
    assert.equal(elements.length,1);const k=elements[0];
    assert.equal(k.paused,true,'outside a tap the keeper is refused');
    assert.match(k.src,/^blob:/,'blob: (the CSP allows media from self and blob:, not data:)');assert.equal(k.loop,true);assert.ok('playsinline' in k.attrs);
    const blob=blobs.get(k.src);assert.equal(blob.type,'audio/wav');
    const wav=Buffer.from(await blob.arrayBuffer());
    assert.equal(wav.toString('latin1',0,4),'RIFF');assert.equal(wav.toString('latin1',8,12),'WAVE');assert.equal(wav.readUInt16LE(34),16);assert.equal(wav.readUInt32LE(24),44100);assert.equal(wav.readUInt32LE(40),88200);assert.ok(wav.subarray(44).every(x=>x===0),'pure silence');
    tap();await settle();assert.equal(k.paused,false,'the next tap starts it');
    setHidden(true);await settle();assert.equal(k.paused,true,'hidden: paused');
    setHidden(false);await settle();assert.equal(k.paused,false,'visible: playing again (no tap needed now)');
    audio.duck('kara',true);assert.equal(k.paused,true,'karaoke room: its own media');
    audio.duck('kara',false);assert.equal(k.paused,false);
    audio.duck('wedding',true);assert.equal(k.paused,false,'the wedding music is Web Audio: keep it');audio.duck('wedding',false);
    m.configure({...ON,on:false});await settle();assert.equal(k.paused,true,'music off: paused');
    audio.wantAudio('wedding',true);await settle();assert.equal(k.paused,false,'the wedding party music plays like media too');
    audio.wantAudio('wedding',false);assert.equal(k.paused,true);
  },
  /** Safari 16.4+: the Audio Session API, no keeper. */
  async ios_new(){
    const m=new Music();tap();await settle();
    m.configure(ON);await settle();
    assert.equal(navigator.audioSession.type,'playback');assert.equal(elements.length,0);
    m.configure({...ON,on:false});await settle();assert.equal(navigator.audioSession.type,'auto');
  },
  /** Android / desktop: neither. */
  async android(){
    const m=new Music();m.configure(ON);tap();await settle();serve(downloads[0]);await settle();
    assert.equal(elements.length,0);onlySong(1);assert.equal(ctx().state,'running');
  },
  /** An in-app browser that still says document.hidden after coming back: a tap proves the page is shown. */
  async hidden_tap(){
    const m=new Music();m.configure(ON);setHidden(true);m.setHidden(true);
    tap();await settle();
    assert.equal(ctx().state,'running');assert.equal(downloads.length,1);
    serve(downloads[0]);await settle();onlySong(1);
  },
  /** The wedding party / fair / pagoda / karaoke duck the song and give it back. */
  async duck(){
    const m=new Music();m.configure(ON);tap();await settle();serve(downloads[0]);await settle();
    const g=m.master.gain;
    audio.duck('wedding',true);assert.equal(g.targets.at(-1),0);
    audio.duck('kara',true);audio.duck('wedding',false);assert.equal(g.targets.at(-1),0,'still ducked by karaoke');
    audio.duck('kara',false);assert.ok(g.targets.at(-1)>0,'back');
    onlySong(1);
  },
};

try{await S[process.argv[2]]();console.log('ok');process.exit(0);}
catch(e){console.error(e);process.exit(1);}
