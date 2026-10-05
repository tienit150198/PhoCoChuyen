/** Giữ chân: small anonymous beacons to POST /api/beacon (game/retention.py), so the operator can see where and
 * how players drop off. Loaded by app.js right after the first frame; boot.js keeps the errors (and a leave)
 * that happen before (globalThis.__mnlBoot.tele).
 * - leave (the page is hidden or closed): the sheet or screen, an open popup, the workplace, the life day, the
 *   tutorial / first-day step, seconds since load and the last 3 buttons pressed (their action names);
 * - client errors: script errors, unhandled promise rejections, files that failed to load, failed API calls
 *   (status and path) and the text of a rejected command's toast; each kind+text once per page load (repeats
 *   are counted), at most MAX_PAGE per page load and MAX_SESSION per tab. A script error or rejection carries
 *   where it was thrown (stack(): file:line:col of the top 3 frames, no query strings). Errors that are not the
 *   game's are never sent (foreign(): a script of another origin or none, an in-app browser's injected bridge);
 * - once per page load: load timings (first byte, DOMContentLoaded, first game frame), the network type, coarse
 *   device memory / cores, cold or warm cache; and where a new player came from (referrer site, utm_*).
 * - on 10% of page loads: bounded parse/apply/render, long-task and slow-interaction durations, attached to
 *   those same load/leave beacons. No extra requests or polling; only numeric count/total/max summaries.
 * Only identifiers and numbers; no text typed by the player, no query strings, no ids. Nothing is stored. */
import {observabilityBoot,analyticsError} from './observability.js';
const URL_PATH='/api/beacon',MAX_PAGE=30,MAX_SESSION=60,ERR_DELAY=5000,MAX_TEXT=200;
const ID=/^[A-Za-z0-9_:.-]{1,48}$/;
let env=null,taps=[],seen=new Map(),queue=[],timer=0,lastLeave=0,sentPage=0,clientPerformance=null;

const store={get(k){try{return sessionStorage.getItem(k);}catch{return null;}},set(k,v){try{sessionStorage.setItem(k,v);}catch{/* blocked */}}};
const local={get(k){try{return localStorage.getItem(k);}catch{return null;}},set(k,v){try{localStorage.setItem(k,v);}catch{/* blocked */}}};
const id=v=>typeof v==='string'&&ID.test(v)?v:undefined;
/** A URL as its path only (no origin, query or hash). */
function path(u){try{const x=new URL(String(u),location.href);return x.origin===location.origin?x.pathname:x.host+x.pathname;}catch{return String(u||'').split(/[?#]/)[0];}}
const text=v=>String(v??'').replace(/https?:\/\/[^\s?#]*[?#]\S*/g,m=>m.split(/[?#]/)[0]).slice(0,MAX_TEXT);

const PERF_PHASES=['parse','apply','render'],PERF_LIMIT=200,PERF_MS=60000;
/** Sample after the first frame, without touching event targets, names, response bodies or player input.
 * GameAPI emits `clientperf` only while perfEnabled is true. Native event durations are the longest slow
 * event per interaction (>=40 ms), not INP. Caps apply to this entire page, even when a beacon drains data.
 * Unsupported browsers still report API phases; no PerformanceObserver or timer fallback is installed. */
export function createClientPerformance(api,{random=Math.random,Observer=globalThis.PerformanceObserver}={}){
  if(api)api.perfEnabled=false;
  if(random()>=.1)return {take:()=>null,stop(){}};
  let stopped=false,phaseCount=0,eventCount=0,totals={};
  const counts={},watchers=[],interactions=new Map(),reported=new Set();
  const ms=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0?Math.min(PERF_MS,Math.round(value)):null;
  function add(key,value){
    if((counts[key]||0)>=PERF_LIMIT)return;
    const duration=ms(value);if(duration===null)return;
    counts[key]=(counts[key]||0)+1;
    const row=totals[key]||(totals[key]={n:0,total:0,max:0});
    row.n++;row.total+=duration;row.max=Math.max(row.max,duration);
  }
  function phases(ev){
    if(stopped||phaseCount>=PERF_LIMIT)return;
    const d=ev.detail;if(!d||!PERF_PHASES.some(k=>ms(d[k])!==null))return;
    for(const key of PERF_PHASES)add(key,d[key]);
    if(++phaseCount>=PERF_LIMIT){if(api)api.perfEnabled=false;api?.removeEventListener?.('clientperf',phases);}
  }
  api?.addEventListener?.('clientperf',phases);if(api)api.perfEnabled=true;
  function watch(type,consume,options={}){
    if(!Observer?.supportedEntryTypes?.includes(type))return;
    let observer;
    try{
      const read=entries=>{for(const entry of entries){if(stopped||consume(entry)===false){observer.disconnect();break;}}};
      observer=new Observer(list=>read(list.getEntries()));
      observer.observe({type,buffered:true,...options});watchers.push({observer,read});
    }catch{try{observer?.disconnect();}catch{/* unsupported browser */}}
  }
  watch('longtask',entry=>{
    if((counts.longtask||0)>=PERF_LIMIT)return false;
    if(entry.duration>=50)add('longtask',entry.duration);
    return (counts.longtask||0)<PERF_LIMIT;
  });
  watch('event',entry=>{
    if(eventCount>=PERF_LIMIT)return false;
    eventCount++;
    const duration=ms(entry.duration),key=entry.interactionId;
    if(duration!==null&&duration>=40&&typeof key==='number'&&Number.isFinite(key)&&key>0&&!reported.has(key))
      interactions.set(key,Math.max(interactions.get(key)||0,duration));
    return eventCount<PERF_LIMIT;
  },{durationThreshold:40});
  return {
    take(){
      // Delivery can race pagehide. Consume already queued entries before the last beacon.
      if(!stopped)for(const {observer,read} of watchers)try{read(observer.takeRecords());}catch{/* unsupported browser */}
      for(const [key,duration] of interactions){add('interaction',duration);reported.add(key);}
      interactions.clear();
      const out=totals;totals={};return Object.keys(out).length?out:null;
    },
    stop(){
      stopped=true;if(api)api.perfEnabled=false;api?.removeEventListener?.('clientperf',phases);
      for(const {observer} of watchers)try{observer.disconnect();}catch{/* unsupported browser */}
    }
  };
}

function post(body){
  const data=JSON.stringify(body);if(data.length>8000)return;
  try{if(navigator.sendBeacon?.(URL_PATH,data))return;}catch{/* fall back */}
  try{fetch(URL_PATH,{method:'POST',body:data,keepalive:true,credentials:'same-origin',headers:{'Content-Type':'text/plain;charset=UTF-8'}}).catch(()=>{});}catch{/* offline */}
}

/** Where the player is right now (identifiers and numbers only). */
export function where(){
  const s=env?.api?.state,ui=env?.ui||{},out={};
  const loading=document.getElementById('loading');
  const intro=s?.journey?.story&&!s.journey.intro;   // the one intro screen of a new story player (look, name, workplace)
  out.v=id(loading&&!loading.hidden?'loading':intro&&(!ui.view||ui.view==='home')?'intro':ui.view||(s?.current?'work':'home'));
  const dlg=[...document.querySelectorAll('dialog[open]')].map(d=>d.id).find(x=>x&&x!=='sheet');
  const layer=document.querySelector('.tut-layer:not([hidden])')?'tour':document.querySelector('.tut-note:not([hidden])')?'note':undefined;
  out.p=id(dlg||layer);
  out.c=id(s?.current);
  const day=Number(s?.journey?.life_day);if(Number.isFinite(day)&&day>0)out.d=Math.round(day);
  const tour=local.get('mnl.tut.run');
  if(id(tour))out.t=`tour:${tour}`;
  else if(s?.journey?.story&&(Number(s.journey.life_day)||1)<=1){
    const served=Object.values(s.careers||{}).reduce((n,c)=>n+(Number(c?.metrics?.served)||0),0);
    out.t=`d1:s${Math.min(served,10)}`;
  }
  out.s=Math.round(performance.now()/1000);
  if(taps.length)out.a=[...taps];
  for(const k of Object.keys(out))if(out[k]===undefined)delete out[k];
  return out;
}

/* Where an error was thrown: the top frames of its stack (V8 "at f (url:1:2)", Safari/Firefox "f@url:1:2") as
 * `<path under this origin>:<line>:<col>` (js/app.js:1:59652: the minified release is one line, the column finds
 * it), `~` for a frame of another origin (an extension, a script an in-app browser injected), joined by ` < `. */
const FRAME=/([a-z][a-z0-9+.-]*:\/\/[^\s/]+)(\/[^\s?#)]*)[^\s)]*?:(\d+):(\d+)/i;
export function stack(raw,origin=globalThis.location?.origin){
  const out=[];
  for(const line of String(raw||'').split('\n')){
    const f=FRAME.exec(line);if(!f)continue;
    out.push(f[1]===origin?`${f[2].slice(1).slice(-80)||'-'}:${f[3]}:${f[4]}`:'~');if(out.length>=3)break;
  }
  return out.join(' < ');
}
// Injected by in-app browsers or extensions, never the game's (Zalo's zaloJSV2 bridge, Facebook's autofill, Chrome's
// read mode…). game/retention.py FOREIGN_NAMES drops the same names at the server.
const INJECTED=/zalojsv|zalojavascriptinterface|__gcrweb|getreadmode|_autofillcallbackhandler|java object is gone|instantsearchsdkjsbridge|webkit\.messagehandlers/i;
/** Not the game's error: a known injected name; a script error from a file of another origin or from no file at all
 * (code an app evaluated into the page); a stack whose frames are all from elsewhere; a file of another site. */
export function foreign(kind,message,st='',file){
  if(INJECTED.test(String(message||'')))return true;
  if(kind==='js'&&file!==undefined&&!st.split(' < ').some(f=>f&&f!=='~'))return true;
  if((kind==='js'||kind==='promise')&&st&&st.split(' < ').every(f=>f==='~'))return true;
  if(kind==='asset'&&!String(message||'').startsWith('/'))return true;
  return false;
}

/** One client error (kind: js | promise | asset | api | toast): once per page load, repeats counted. `st`: where it
 * was thrown (stack()). */
export function error(kind,message,screen,st=''){
  const m=text(message).trim();if(!m||foreign(kind,m,st))return;
  const key=kind+'|'+m,have=seen.get(key);
  if(have){have.n++;have.dirty=true;return;}
  if(seen.size>=MAX_PAGE)return;
  analyticsError(kind);   // type only; the detailed error stays on our own server
  const item={k:kind,m,s:id(screen)||where().v||'-',n:1,dirty:true};if(st)item.st=st;seen.set(key,item);queue.push(item);
  clearTimeout(timer);timer=setTimeout(()=>flush(),ERR_DELAY);
}
function takeErrors(){
  const used=Number(store.get('mnl.tele.n')||0),room=Math.max(0,MAX_SESSION-used);
  const out=[];
  for(const item of seen.values()){
    if(!item.dirty||out.length>=Math.min(10,room))continue;
    out.push({k:item.k,m:item.m,s:item.s,n:item.n,...(item.st?{st:item.st}:{})});item.dirty=false;item.n=0;
  }
  queue=[];if(out.length)store.set('mnl.tele.n',String(used+out.length));
  return out;
}
function flush(extra={}){
  clearTimeout(timer);timer=0;
  const errors=takeErrors();
  if(!errors.length&&!Object.keys(extra).length)return;
  if(sentPage++>200)return;   // a page left open for days: stays bounded
  post({...extra,...(errors.length?{errors}:{})});
}
function leave(){
  const now=Date.now();if(now-lastLeave<2000)return;lastLeave=now;   // visibilitychange then pagehide: one beacon
  const leave=where(),perf=clientPerformance?.take();if(perf)leave.perf=perf;
  flush({leave});
}

function loadTimes(){
  const out={};
  try{
    const nav=performance.getEntriesByType('navigation')[0];
    if(nav){if(nav.responseStart>0)out.ttfb=Math.round(nav.responseStart);if(nav.domContentLoadedEventEnd>0)out.dcl=Math.round(nav.domContentLoadedEventEnd);}
    const frame=performance.getEntriesByName('mnl-first-frame')[0];if(frame)out.frame=Math.round(frame.startTime);
    const app=performance.getEntriesByType('resource').find(r=>/\/js\/app\.js(\?|$)/.test(r.name));
    if(app&&typeof app.transferSize==='number')out.cache=app.transferSize>0?'cold':app.decodedBodySize>0?'warm':undefined;
  }catch{/* no Navigation Timing */}
  const c=navigator.connection;if(c?.effectiveType)out.net=String(c.effectiveType);
  if(typeof navigator.deviceMemory==='number')out.mem=navigator.deviceMemory;
  if(typeof navigator.hardwareConcurrency==='number')out.cpu=navigator.hardwareConcurrency;
  for(const k of Object.keys(out))if(out[k]===undefined)delete out[k];
  return out;
}
/** Where a new player came from: the referrer's host and the landing URL's utm_* (sent until the server has it). */
function acquisition(){
  if(local.get('mnl.acq')==='1')return null;
  const q=new URLSearchParams(location.search),out={};
  try{if(document.referrer)out.ref=new URL(document.referrer).hostname;}catch{/* opaque referrer */}
  for(const [k,v] of [['src','utm_source'],['med','utm_medium'],['cmp','utm_campaign']]){const x=q.get(v);if(x)out[k]=x.slice(0,40);}
  return out;
}

/** API answers that are the game saying no, already shown to the player where it happened: not client errors.
 * A rejected command toasts its reason (the 'rejected' event below); these routes show theirs in place. */
const EXPECTED={'/api/social/profile':['name_taken'],'/api/social/shop':['not_found','blocked'],'/api/marriage/plan':['bad_plan']};
export function expectedFail({route,status,code}={}){
  if(route==='/api/beacon')return true;
  if(route==='/api/command')return status===400||status===409;
  if(route==='/api/ai/board')return (status===400||status===409)&&code!=='invalid_data';   // bd_post / bd_reply refused: toasted
  return Boolean(code)&&(EXPECTED[route]||[]).includes(code);
}
export function telemetryBoot(e){
  if(env)return;env=e;
  try{clientPerformance=createClientPerformance(e.api);}catch{/* measurement must never affect the game */}
  try{observabilityBoot(e);}catch{/* Google must never affect game beacons */}
  const B=globalThis.__mnlBoot||(globalThis.__mnlBoot={}),T=B.tele||(B.tele={errs:[]});T.on=true;
  // boot.js kept these (with the screen: 'loading' while the splash shows, 'start' between the first frame and now).
  for(const x of (T.errs||[]).splice(0))error(x.k,x.k==='asset'?path(x.m):x.m,x.s||'loading',x.st?stack(x.st):'');
  addEventListener('error',ev=>{
    const t=ev.target;
    if(t&&t!==window&&(t.src||t.href))error('asset',path(t.src||t.href));
    else if(ev.message){
      const st=stack(ev.error?.stack)||(ev.filename?stack(`${ev.filename}:${ev.lineno||0}:${ev.colno||0}`):'');
      if(foreign('js',ev.message,st,ev.filename||''))return;
      error('js',`${ev.message}${ev.filename?` @${path(ev.filename).split('/').pop()}:${ev.lineno||0}`:''}`,undefined,st);
    }
  },true);
  addEventListener('unhandledrejection',ev=>{const r=ev.reason;error('promise',r?.message||r,undefined,stack(r?.stack));});
  document.addEventListener('click',ev=>{
    const el=ev.target?.closest?.('[data-command],[data-action],[data-act],[data-op]');if(!el)return;
    const a=id(el.dataset.command||el.dataset.action||el.dataset.act||el.dataset.op);
    if(a){taps.push(a);if(taps.length>3)taps.shift();}
  },true);
  const api=e.api;
  api?.addEventListener?.('apifail',ev=>{
    const d=ev.detail||{};
    if(expectedFail(d))return;
    error('api',`${d.status||0} ${d.route||'?'}`);
  });
  api?.addEventListener?.('rejected',ev=>{const d=ev.detail||{};error('toast',d.code&&d.code!=='invalid_action'?`${d.code}: ${d.message}`:d.message);});
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')leave();});
  addEventListener('pagehide',ev=>{leave();if(!ev.persisted)clientPerformance?.stop();});
  const hello=()=>setTimeout(()=>{
    const acq=acquisition(),body={load:loadTimes()};
    const perf=clientPerformance?.take();if(perf)body.load.perf=perf;
    if(acq){body.acq=acq;local.set('mnl.acq','1');}
    post(body);
  },1500);
  if(document.readyState==='complete')hello();else addEventListener('load',hello,{once:true});
}
