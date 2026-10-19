// 🎤 Hát cùng, the co-singer's page (feedback #430: "bạn mình bấm đồng ý rồi thì bên mình quay lại nút hát cùng lúc
// đầu… bấm bao nhiêu lần đồng ý vẫn quay về lúc đầu"). v4/karaoke.js against a fake live socket (answering like
// live/karaoke.py), a fake LiveKit (karaoke-mic.js publish/listen) and a tiny fake DOM; Lan sings on stage with her mic
// live, Bé (this page) presses 🎤 Hát cùng. Each scenario runs in its own node process (the module keeps page state):
//   yes        Lan says yes: Bé's mic goes live ("🔴 Bạn đang hát cùng"), never back to the first button;
//   publish    Bé's microphone fails only after the yes (LiveKit's getUserMedia: NotReadableError): her page turns its
//              mic off (kara_join on:0) and the server's echo (kara_co on:0 why 'off') no longer wipes the failure:
//              "Chưa phát được giọng · Thử lại" with the reason stays (before: the first 🎤 Hát cùng button, silently);
//   nomic      no microphone on Bé's desktop: said at once, before Lan is asked (no kara_join at all);
//   retry      Thử lại after a failure asks again (the microphone first, then kara_join);
//   relisten   a co-singer's voice this page gave up on (three failed tries) is tried again once their video time
//              (kara_cvt, sent only while their mic is live) arrives;
//   tag        karaoke-mic.js tag() on a DOMException (read-only `code`): no TypeError, the name and the stage kept.
// Run: node tests/karaoke_duet.mjs (tests/test_karaoke_mic.py runs it); exits non-zero on failure.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {registerHooks} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';

const SELF=fileURLToPath(import.meta.url);
const SCENARIOS=['yes','publish','nomic','retry','relisten','tag'];
if(!process.argv[2]){
  let failed=0;
  for(const name of SCENARIOS){
    try{execFileSync(process.execPath,[SELF,name],{stdio:'pipe',encoding:'utf-8',timeout:30000});console.log(`ok   ${name}`);}
    catch(e){failed++;console.log(`FAIL ${name}\n${e.stdout||''}${e.stderr||''}`);}
  }
  console.log(failed?`${failed} scenario(s) failed`:`${SCENARIOS.length} duet scenarios OK`);
  process.exit(failed?1:0);
}
const SCENARIO=process.argv[2];

const ROOT=path.resolve(path.dirname(SELF),'..');
const KJS=pathToFileURL(path.join(ROOT,'public/js/v4/karaoke.js')).href;
const MICJS=pathToFileURL(path.join(ROOT,'public/js/v4/karaoke-mic.js')).href;

if(SCENARIO==='tag'){
  const {tag}=await import(MICJS);
  const dom=new DOMException('Could not start audio source','NotReadableError');
  const e=tag(dom,'perm');
  assert.equal(e.name,'NotReadableError');
  assert.equal(e.stage,'perm');
  assert.match(e.code,/^NotReadableError/);
  const plain=new Error('boom');
  assert.equal(tag(plain,'signal'),plain,'an ordinary Error is tagged in place');
  assert.equal(plain.stage,'signal');
  assert.equal(tag(e,'ice'),e,'a tagged error keeps its first stage');
  assert.equal(tag('x','sdk').stage,'sdk');
  console.log('tag OK');
  process.exit(0);
}

/* ---------------------------------------------------------------- stub modules */
const STUB={
  'icons.js':`export const icon=()=>'';export const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');`,
  'live.js':`export const live=globalThis.__live;`,
  'lazy.js':`export const stylesheet=async()=>{};`,
  'audio.js':`export const duck=()=>{};`,
  'telemetry.js':`export const error=(...a)=>{globalThis.__beacons.push(a.join(' '));};`,
  'karaoke-mic.js':`export * from '${MICJS}';const F=globalThis.__lk;
    export const loadSDK=async()=>({});export const audioCtx=()=>null;export const resumeAudio=()=>{};export const localLatency=()=>0;
    export const publish=o=>F.publish(o);export const listen=o=>F.listen(o);`,
};
registerHooks({
  resolve(spec,ctx,next){
    if(ctx.parentURL&&ctx.parentURL.startsWith(KJS)){
      const base=spec.split('/').pop();
      if(STUB[base])return {url:`stub:${base}`,shortCircuit:true};
    }
    return next(spec,ctx);
  },
  load(url,ctx,next){
    if(url.startsWith('stub:'))return {format:'module',source:STUB[url.slice(5)],shortCircuit:true};
    return next(url,ctx);
  },
});
const {tag}=await import(MICJS);

/* ---------------------------------------------------------------- the fake browser */
class El{
  constructor(tag='div'){this.tag=tag;this.innerHTML='';this.hidden=false;this.value='';this.dataset={};this.kids=new Map();this.ls={};this.style={};this.open=false;}
  querySelector(sel){
    if(/^\[data-kr-(link|focus|clue|ans|reward|words|year|left|clock|mic|n)\]$/.test(sel))return null;
    if(!this.kids.has(sel))this.kids.set(sel,new El());
    return this.kids.get(sel);
  }
  querySelectorAll(){return [];}
  addEventListener(t,f){(this.ls[t]||=[]).push(f);}
  removeEventListener(){}
  setAttribute(){}append(){}remove(){}replaceWith(){}focus(){}
  showModal(){this.open=true;}close(){this.open=false;for(const f of this.ls.close||[])f({});}
  closest(){return null;}
}
const dialogs=[];
globalThis.window=globalThis;
globalThis.document={createElement:t=>{const e=new El(t);if(t==='dialog')dialogs.push(e);return e;},body:new El(),head:new El(),
  addEventListener(){},hidden:false,visibilityState:'visible'};
const store=new Map([['kr-mic-ask','1']]);   // the headphones note was seen before
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
/* the microphone: G.mic is the getUserMedia error name of this machine (null: it works) */
const G={mic:null,gum:0,open:0};
Object.defineProperty(globalThis,'navigator',{value:{userAgent:'node',mediaDevices:{getUserMedia:async()=>{
  G.gum++;if(G.mic)throw new DOMException('mic',G.mic);G.open++;return {getTracks:()=>[{stop(){G.open--;}}]};}}},configurable:true});
globalThis.isSecureContext=true;
globalThis.RTCPeerConnection=function(){};
globalThis.location={origin:'https://example.test',protocol:'https:',host:'example.test'};
globalThis.confirm=()=>true;
globalThis.__beacons=[];
class Player{constructor(f,o){this.t=0;setTimeout(()=>o.events.onReady?.(),0);}
  getPlayerState(){return 1;}getCurrentTime(){return this.t;}seekTo(){}playVideo(){}stopVideo(){}loadVideoById(){}cueVideoById(){}
  getDuration(){return 200;}setPlaybackRate(){}getPlaybackRate(){return 1;}}
globalThis.YT={Player};

/* the live socket: what the page sends, and frames from "the server" */
const sent=[],listeners=new Map();
globalThis.__live={state:'open',flags:{kara:1,kara_mic:1},
  on(t,fn){if(!listeners.has(t))listeners.set(t,new Set());listeners.get(t).add(fn);return ()=>listeners.get(t)?.delete(fn);},
  send(f){sent.push(f);setTimeout(()=>server(f),1);return true;}};
const push=f=>{for(const fn of [...(listeners.get(f.t)||[])])fn(f);};

/* LiveKit: each publish resolves (or fails) when the test says so */
const pubs=[];
function handle(o){
  let stopped=false;
  return {opts:o,stopped:()=>stopped,stop(){stopped=true;},track:{},stats:async()=>({bytes:100,packets:5}),path:async()=>null,delay:async()=>null,
    setVolume(){},mute(){},tap:async()=>{},canPlay:()=>true,heard:()=>true,setDelay:()=>true,held:()=>0,base:()=>0};
}
globalThis.__lk={
  publish(o){return new Promise((ok,bad)=>{pubs.push({o,ok:()=>ok(handle(o)),bad});});},
  listen(o){G.listens++;if(G.listenFail>0){G.listenFail--;return Promise.reject(Object.assign(new Error('none'),{stage:'track',code:'none'}));}return Promise.resolve(handle(o));},
};
G.listens=0;G.listenFail=0;

/* ---------------------------------------------------------------- the room and "the server" (live/karaoke.py) */
const ROOM='kara:tre',ME='p_be',LAN='p_lan',E='e1';
const now=()=>Date.now()/1000;
const room=()=>({t:'kara_room',id:ROOM,name:'Nhạc trẻ',emoji:'🎧',theme:'tre',cap:20,me:ME,account:true,adm:0,n:2,
  people:[{pid:ME,name:'Bé'},{pid:LAN,name:'Lan'}],queue:[],round:null,now:now(),reacts:[],tips:[],price:0,lead:5,
  stage:{e:E,vid:'abcdefghijk',title:'Bài hát',by:{pid:LAN,name:'Lan'},phase:'play',at:now()-30,dur:200,until:now()+170,votes:0,need:1,hearts:0,cheers:0,tips:0,
    mic:{on:1,until:now()+600}}});
const S={asks:0,live:false};
function server(f){
  switch(f.t){
    case'kara_in':push(room());break;
    case'kara_time':push({t:'kara_time',c:f.c,at:now()});break;
    case'kara_listen':push(f.pid?{t:'kara_listen',id:ROOM,pid:f.pid,on:1,e:E,url:'wss://sfu',room:'r-'+f.pid,token:'t'}:{t:'kara_listen',id:ROOM,on:1,e:E,url:'wss://sfu',room:'r-main',token:'t'});break;
    case'kara_join':
      if(f.on){S.asks++;push({t:'kara_join',id:ROOM,e:E,on:1,ask:1,until:now()+30});}
      else{   // _ask_off + _co_off(…, 'off'): the room (me too) sees kara_co on:0 why 'off'
        const was=S.live;S.live=false;push({t:'kara_join',id:ROOM,e:f.e,on:0});if(was)push({t:'kara_co',id:ROOM,e:E,pid:ME,on:0,why:'off'});
      }
      break;
  }
}
/** Lan says yes (kara_let): the publishing token to me, then kara_co to the room. */
function lanSaysYes(){S.live=true;push({t:'kara_sing',id:ROOM,e:E,on:1,url:'wss://sfu',room:'r-'+ME,token:'pub',until:now()+600});push({t:'kara_co',id:ROOM,e:E,pid:ME,name:'Bé',on:1});}

const tick=(ms=15)=>new Promise(r=>setTimeout(r,ms));
const {openKaraoke,karaoke}=await import(KJS);
const toasts=[];
await openKaraoke({toast:t=>toasts.push(t)},{room:ROOM});
await tick(30);
const dlg=dialogs[0];
const html=()=>dlg.querySelector('.kr-dyn').innerHTML;
const click=kr=>{const t={dataset:{kr},disabled:false,closest:s=>s==='[data-kr]'?t:null};for(const f of dlg.ls.click)f({target:t,preventDefault(){}});};
const joins=on=>sent.filter(f=>f.t==='kara_join'&&!!f.on===on).length;
const FIRST=/data-kr="join"[^>]*>🎤 Hát cùng/;

assert.equal(karaoke.state().live?.by,LAN,'Lan\'s mic is live for this page');
assert.match(html(),FIRST,'the 🎤 Hát cùng button');

if(SCENARIO==='relisten'){
  // Tú sings along; this page cannot hear her three times in a row (her mic came late), then her video time arrives
  // (kara_cvt: her mic is live now): her voice is tried again
  const TU='p_tu';
  await tick(50);   // my own listen() to Lan settles first
  const before=G.listens;
  G.listenFail=3;
  push({t:'kara_co',id:ROOM,e:E,pid:TU,name:'Tú',on:1});
  await tick(6800);   // the first try, then 2 s and 4 s later the two retries
  assert.equal(G.listens-before,3,'three tries');
  assert.deepEqual(karaoke.state().coHeard,[]);
  const cvt=()=>push({t:'kara_cvt',id:ROOM,e:E,pid:TU,vt:31,at:now()});
  cvt();
  await tick(30);
  assert.equal(G.listens-before,4,'tried again once her voice is live');
  assert.deepEqual(karaoke.state().coHeard,[TU]);
  cvt();cvt();
  await tick(30);
  assert.equal(G.listens-before,4,'not again while it plays');
  console.log('relisten OK');process.exit(0);
}

if(SCENARIO==='nomic'){
  G.mic='NotFoundError';
  click('join');
  await tick();
  assert.equal(G.gum,1,'the microphone is tried with the tap');
  assert.equal(joins(true),0,'Lan is not asked');
  assert.equal(karaoke.state().coSt,'fail');
  assert.ok(toasts.includes('Không thấy micro trên máy này.'),JSON.stringify(toasts));
  assert.match(html(),/Chưa phát được giọng/);
  assert.match(html(),/Không thấy micro trên máy này/);
  assert.doesNotMatch(html(),FIRST);
  assert.ok(__beacons.some(b=>/kara_mic cosing perm: NotFoundError/.test(b)),JSON.stringify(__beacons));
  console.log('nomic OK');process.exit(0);
}

// Bé asks: the microphone opens and closes at once, then the ask
click('join');
await tick();
assert.equal(G.gum,1);
assert.equal(G.open,0,'nothing kept open while Lan decides');
assert.equal(S.asks,1);
assert.equal(karaoke.state().coSt,'ask');
assert.match(html(),/Đang chờ người hát đồng ý/);

lanSaysYes();
await tick();
assert.equal(pubs.length,1,'Bé publishes her microphone');
assert.equal(karaoke.state().coSt,'join');

if(SCENARIO==='yes'){
  pubs[0].ok();
  await tick();
  const st=karaoke.state();
  assert.ok(st.cpub,`Bé's mic is live (coSt=${st.coSt}, toasts=${JSON.stringify(toasts)})`);
  assert.equal(st.coSt,'live');
  assert.match(html(),/Bạn đang hát cùng/);
  assert.doesNotMatch(html(),FIRST,'not back to the first button');
  assert.equal(joins(false),0,'the page never turned its own mic off');
  console.log('yes OK');process.exit(0);
}

// publish / retry: the microphone fails only now (another app took it); LiveKit throws getUserMedia's DOMException,
// karaoke-mic.js tags it with its stage
pubs[0].bad(tag(new DOMException('Could not start audio source','NotReadableError'),'perm'));
await tick(40);   // the page's kara_join on:0, then the server's kara_co on:0 why 'off'
assert.equal(joins(false),1,'the page turned its own mic off');
let st=karaoke.state();
assert.equal(st.coSt,'fail',`the failure stays (coSt=${st.coSt})`);
assert.ok(!st.cpub);
assert.match(html(),/Chưa phát được giọng/);
assert.match(html(),/data-kr="join"[^>]*>Thử lại/);
assert.match(html(),/Micro đang bận ở ứng dụng khác/);
assert.doesNotMatch(html(),FIRST,'not back to the first 🎤 Hát cùng button');
assert.ok(toasts.includes('Micro đang bận ở ứng dụng khác. Tắt ứng dụng đó rồi thử lại nhé.'),JSON.stringify(toasts));
assert.ok(__beacons.some(b=>/kara_mic cosing perm: NotReadableError/.test(b)),JSON.stringify(__beacons));
assert.ok(!__beacons.some(b=>/TypeError/.test(b)),JSON.stringify(__beacons));
if(SCENARIO==='publish'){console.log('publish OK');process.exit(0);}

// retry: Thử lại asks again, the microphone first
click('join');
await tick();
assert.equal(G.gum,2);
assert.equal(S.asks,2);
assert.equal(karaoke.state().coSt,'ask');
lanSaysYes();
await tick();
pubs[1].ok();
await tick();
st=karaoke.state();
assert.ok(st.cpub);
assert.equal(st.coSt,'live');
assert.match(html(),/Bạn đang hát cùng/);
console.log('retry OK');
process.exit(0);
