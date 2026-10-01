// Unit test of the client-error beacon (public/js/telemetry.js + the early catcher in public/js/boot.js), 01/10:
// a script error or rejection carries where it was thrown (file:line:col of the top 3 frames, no query strings), and
// errors that are not the game's (Zalo's zaloJSV2 bridge, extensions, scripts of other sites) are never sent.
// Run by tests/test_telemetry_js.py (node tests/telemetry.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';

const ORIGIN='https://phocochuyen.io.vn';
const sent=[];
const win=new EventTarget();
for(const k of ['addEventListener','removeEventListener','dispatchEvent'])globalThis[k]=win[k].bind(win);
globalThis.window=globalThis;
const store=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};
Object.defineProperty(globalThis,'localStorage',{value:store(),configurable:true});
Object.defineProperty(globalThis,'sessionStorage',{value:store(),configurable:true});
Object.defineProperty(globalThis,'navigator',{value:{sendBeacon:(url,data)=>{sent.push(JSON.parse(data));return true;}},configurable:true});
globalThis.location={origin:ORIGIN,href:ORIGIN+'/',search:'',protocol:'https:',host:'phocochuyen.io.vn'};
const loading={hidden:false};
const doc=new EventTarget();
Object.assign(doc,{visibilityState:'visible',readyState:'loading',referrer:'',head:{append(){}},documentElement:{dataset:{}},
  getElementById:id=>id==='loading'?loading:null,querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({})});
globalThis.document=doc;
globalThis.fetch=()=>new Promise(()=>{});   // boot.js's early requests: never answered here

const V8=`TypeError: Cannot read properties of undefined (reading 'filter')
    at es (${ORIGIN}/js/app.js?v=b7d4ba3805f4:1:59652)
    at Rn (${ORIGIN}/js/app.js?v=b7d4ba3805f4:1:37283)
    at A (${ORIGIN}/js/app.js?v=b7d4ba3805f4:1:28135)
    at L (${ORIGIN}/js/app.js?v=b7d4ba3805f4:1:8046)`;
const SAFARI=`es@${ORIGIN}/js/careers/milk_tea.js?v=12ab:1:200\nRn@${ORIGIN}/js/app.js?v=9f:3:4\nglobal code@${ORIGIN}/:2:10`;
const EXT=`TypeError: Cannot read properties of undefined (reading 'sendMessage')
    at chrome-extension://abcdefgh/inject.js:4:11
    at https://cdn.example.com/sdk.js?id=42:1:99`;

// boot.js: the early catcher, then its stack shortener (exposed as __mnlBoot.stack)
await import('../public/js/boot.js');
const B=globalThis.__mnlBoot,T=B.tele;
const {stack,foreign,error,telemetryBoot}=await import('../public/js/telemetry.js');

{ // stack(): path:line:col of this origin, ~ for any other, the top 3 only, never a query string
  assert.equal(stack(V8,ORIGIN),'js/app.js:1:59652 < js/app.js:1:37283 < js/app.js:1:28135');
  assert.equal(stack(SAFARI,ORIGIN),'js/careers/milk_tea.js:1:200 < js/app.js:3:4 < -:2:10');
  assert.equal(stack(EXT,ORIGIN),'~ < ~');
  assert.equal(stack('Error: boom',ORIGIN),'');assert.equal(stack(undefined,ORIGIN),'');
  assert.ok(!/[?]|v=/.test(stack(V8,ORIGIN)));
  for(const s of [V8,SAFARI,EXT,'x','',`at f (${ORIGIN}/js/a.js:9:9)`])assert.equal(B.stack(s),stack(s,ORIGIN),'boot.js shortens the same way');
}
{ // foreign(): known injected names, scripts of other origins or of none, other sites' files
  assert.equal(foreign('js','Uncaught ReferenceError: zaloJSV2 is not defined','-:1:20',''),true);
  assert.equal(foreign('promise',"Cannot read properties of undefined (reading 'getReadModeExtract')",''),true);
  assert.equal(foreign('js','Uncaught TypeError: x','',''),true,'no file, no frame of ours: evaluated into the page');
  assert.equal(foreign('js','Uncaught TypeError: x','~','chrome-extension://x/a.js'),true);
  assert.equal(foreign('promise','Cannot read x','~ < ~'),true);
  assert.equal(foreign('promise','Cannot read x','js/app.js:1:2 < ~'),false,'one frame of ours is enough');
  assert.equal(foreign('promise','Failed to fetch',''),false,'no stack at all: kept');
  assert.equal(foreign('js','Uncaught TypeError: x','js/app.js:1:5',ORIGIN+'/js/app.js'),false);
  assert.equal(foreign('asset','connect.facebook.net/en_US/fbevents.js'),true);
  assert.equal(foreign('asset','/js/careers/fruit.js'),false);
  assert.equal(foreign('api','502 /api/command'),false);
}
{ // the early catcher (boot.js): before the first frame 'loading', after it 'start'; no-file script errors are dropped
  const fire=(type,props)=>dispatchEvent(Object.assign(new Event(type),props));
  fire('unhandledrejection',{reason:Object.assign(new TypeError("Cannot read properties of undefined (reading 'filter')"),{stack:V8})});
  fire('error',{message:'Uncaught ReferenceError: zaloJSV2 is not defined',filename:'',lineno:1,colno:1});
  loading.hidden=true;   // the first frame is out; telemetry.js not yet
  fire('error',{message:'Uncaught TypeError: boom',filename:ORIGIN+'/js/app.js?v=1',lineno:1,colno:77,error:{stack:''}});
  fire('unhandledrejection',{reason:Object.assign(new TypeError("Cannot read properties of undefined (reading 'sendMessage')"),{stack:EXT})});
  assert.deepEqual(T.errs.map(x=>[x.k,x.s]),[['promise','loading'],['js','start'],['promise','start']]);
  assert.ok(T.errs[0].st.includes('app.js'));
}
{ // telemetry.js takes them over: ours with their stack, the extension's dropped; the beacon is small and query-free
  const api=new EventTarget();
  telemetryBoot({api,ui:{}});
  dispatchEvent(Object.assign(new Event('unhandledrejection'),{reason:Object.assign(new TypeError('later'),{stack:`TypeError: later\n    at x (${ORIGIN}/js/v4/walk.js?v=aa:1:10)`})}));
  dispatchEvent(Object.assign(new Event('error'),{message:'Uncaught ReferenceError: zaloJSV2 is not defined',filename:ORIGIN+'/',lineno:3,colno:1}));
  dispatchEvent(Object.assign(new Event('error'),{message:'Script error.',filename:'',lineno:0,colno:0}));
  error('asset','cdn.zalo.me/sdk.js');
  dispatchEvent(new Event('pagehide'));
  const body=sent.at(-1),errs=body.errors;
  assert.deepEqual(errs.map(e=>[e.k,e.s,e.st]),[
    ['promise','loading','js/app.js:1:59652 < js/app.js:1:37283 < js/app.js:1:28135'],
    ['js','start','js/app.js:1:77'],
    ['promise','home','js/v4/walk.js:1:10'],   // where() now: the home screen (no state here)
  ]);
  assert.equal(errs[0].m,"Cannot read properties of undefined (reading 'filter')");
  assert.ok(!JSON.stringify(body).includes('?v='),'no query strings');
  assert.ok(JSON.stringify(body).length<8000);
}
console.log('telemetry.mjs: ok');
process.exit(0);
