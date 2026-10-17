// 🔊 Giọng đọc số tiền (public/js/v4/sounds.js), feedback #407 (17/10, Android Chrome, 2.4.36): "sao bên mình không
// còn nghe Giọng đọc số tiền nữa, dù đã bật". A speech queue Android leaves stuck (an earlier line that never ended,
// the screen locked mid-line) or paused (back from another app) kept every later line silent until a reload, and a
// voice list that arrives late ('voiceschanged') turned the line into the chip. Run by tests/test_bank_speaker.py.
import assert from 'node:assert/strict';
import test from 'node:test';

const listeners={};
globalThis.addEventListener=(type,fn)=>{(listeners[type]??=[]).push(fn);};
globalThis.MutationObserver=class{observe(){}};
const body={append(){},querySelector:()=>null,querySelectorAll:()=>[]};
globalThis.document={hidden:false,body,addEventListener:(t,fn)=>{(listeners['doc:'+t]??=[]).push(fn);},getElementById:()=>null,
  querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({setAttribute(){},classList:{add(){}},remove(){}})};
globalThis.SpeechSynthesisUtterance=class{constructor(t){this.text=t;this.lang='';this.voice=null;}};

/** A speech engine as Android shows it: lines are heard only while the queue is neither stuck nor paused;
 * cancel() clears a stuck queue, resume() a paused one; voices may come late with 'voiceschanged'. */
function engine({stuck=false,paused=false,voices=[{name:'Linh',lang:'vi-VN',localService:true}],late=0}={}){
  const e={heard:[],queued:[],stuck,paused,cancels:0,resumes:0,ev:{},listed:late?[]:voices,
    get speaking(){return this.stuck;},get pending(){return this.queued.length>0;},
    getVoices(){return this.listed;},
    addEventListener(t,fn){(this.ev[t]??=[]).push(fn);},removeEventListener(t,fn){this.ev[t]=(this.ev[t]||[]).filter(f=>f!==fn);},
    cancel(){this.cancels++;this.stuck=false;this.queued=[];},
    resume(){this.resumes++;this.paused=false;this.flush();},
    speak(u){this.queued.push(u);this.flush();},
    flush(){if(this.stuck||this.paused)return;for(const u of this.queued.splice(0))this.heard.push({text:u.text,lang:u.lang,voice:u.voice?.name});}};
  if(late)setTimeout(()=>{e.listed=voices;for(const fn of e.ev.voiceschanged||[])fn();},late);
  return e;
}

const {soundsBoot,sayLine,voicesReady}=await import('../public/js/v4/sounds.js');
const settings={sound:true,bankVoice:true,moneyTing:false,detailSfx:false,npcVoices:false};
const api=new EventTarget();api.state={settings,name:'An',journey:{wallet:0,life_day:1,history:[]}};
const sound={configure(){},ting(){},hush(){},babble(){}};
const boot=soundsBoot({api,world:{say(){}},sound});
const wait=ms=>new Promise(r=>setTimeout(r,ms));

test('a stuck queue (an earlier line that never ended) is cleared: the payment is heard',async()=>{
  const e=engine({stuck:true});globalThis.speechSynthesis=e;
  boot.bank([50]);
  await wait(900);
  assert.equal(e.cancels,1);
  assert.deepEqual(e.heard,[{text:'Đã nhận 50 xu',lang:'vi-VN',voice:'Linh'}]);
});

test('a queue Android left paused (back from the lock screen) is resumed',async()=>{
  const e=engine({paused:true});globalThis.speechSynthesis=e;
  boot.money([{amount:120,kind:'salary'}]);
  await wait(900);
  assert.ok(e.resumes>=1);
  assert.deepEqual(e.heard.map(x=>x.text),['Đã nhận lương 120 xu']);
  // and coming back to the page resumes it too
  e.paused=true;for(const fn of listeners['doc:visibilitychange']||[])fn();
  assert.equal(e.paused,false);
});

test('voices listed late (Android) are waited for: the line, not the chip',async()=>{
  const e=engine({late:900});globalThis.speechSynthesis=e;   // later than the 0.6 s the payment waits for company
  boot.bank([30]);
  await wait(1800);
  assert.deepEqual(e.heard.map(x=>x.text),['Đã nhận 30 xu']);
});

test('no Vietnamese voice at all: nothing in another language (the chip instead)',async()=>{
  const e=engine({voices:[{name:'Samantha',lang:'en-US',localService:true}]});globalThis.speechSynthesis=e;
  boot.bank([40]);
  await wait(900);
  assert.deepEqual(e.heard,[]);
});

test('the switch off stays off',async()=>{
  const e=engine();globalThis.speechSynthesis=e;
  settings.bankVoice=false;
  boot.bank([60]);
  await wait(900);
  settings.bankVoice=true;
  assert.deepEqual(e.heard,[]);
});

test('helpers: voicesReady gives up after its wait; sayLine on a healthy queue cancels nothing',async()=>{
  const e=engine({late:5000});
  assert.deepEqual(await voicesReady(e,50),[]);
  const ok=engine();
  sayLine(new SpeechSynthesisUtterance('Đã nhận 5 xu'),ok);
  assert.equal(ok.cancels,0);
  assert.deepEqual(ok.heard.map(x=>x.text),['Đã nhận 5 xu']);
});

test('the first tap no longer queues a silent line outside iPhone',()=>{
  const e=engine();globalThis.speechSynthesis=e;
  for(const fn of listeners.pointerdown||[])fn();
  assert.equal(e.queued.length+e.heard.length,0);
});
