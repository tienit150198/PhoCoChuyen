import {UpdateNotice,OUTDATED_CODES,prewarmRelease} from './update.js';

/* A restart (deploy) answers 502/503/504 through the proxy, or drops the connection, for a few seconds.
 * Reads (GET) and commands are then sent again, byte for byte (a command keeps its request_id: the server's
 * receipt replays one that already landed, so nothing is applied twice), after RETRY_DELAYS, for at most
 * RETRY_WINDOW ms; meanwhile a small "Đang cập nhật máy chủ…" note shows instead of an error. The command
 * queue waits meanwhile, so commands keep their order. 4xx answers and other writes are never re-sent. */
export const TRANSIENT=new Set([502,503,504]);
export const RETRY_DELAYS=[300,600,1000,1500,2000,2000,2000,2000,2000];
export const RETRY_WINDOW=14000;
export const UPDATING_TEXT='Đang cập nhật máy chủ…';
const BUSY_TEXT='Máy chủ đang bận, thử lại sau giây lát.';
/** Worth sending again: no answer at all (network, timeout, unreadable body) or a restart's 502/503/504. */
export const transient=error=>!error?.status||TRANSIENT.has(error.status);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
/** A step this tab sent within this long counts as the same tap when it comes again from an older screen. */
export const DOUBLE_TAP_MS=5000;

/* The server's clock as this page reads it (live bars and stop taps, v4/careers.js: the bar drawn, the moment a
 * stop sends as tap_at). Each JSON answer carries server_time (when it left) and server_recv (when the request
 * came in): the NTP estimate offset = ((recv - sent) + (time - got)) / 2 leaves out the time the request spent on
 * the server (a lock, other players' commands), `got` is taken when the answer's headers are in (a slow phone's
 * JSON parse is not network time), and of the answers of the last CLOCK_AGE ms the one with the shortest network
 * trip wins. Before, the last answer simply won, leaned by half of any server wait or slow leg: on a busy server the
 * bars were drawn a few tenths of a second off the server's own clock and jumped with every answer. */
export const CLOCK_AGE=120000,CLOCK_KEEP=16;
/** Adds one reading to `samples` (kept in place) and returns the offset to use (seconds, server - page). */
export function clockSample(samples,sent,got,time,recv){
  const t1=sent/1000,t4=got/1000,trip=Math.max(0,t4-t1);
  const stay=Number.isFinite(recv)?Math.min(trip,Math.max(0,time-recv)):0;   // on the server (an older one: unknown)
  samples.push({offset:((time-stay-t1)+(time-t4))/2,trip:trip-stay,at:got});
  while(samples.length>CLOCK_KEEP||(samples.length>1&&got-samples[0].at>CLOCK_AGE))samples.shift();
  let best=samples[0];for(const x of samples)if(x.trip<=best.trip)best=x;   // a tie: the newer
  return best.offset;
}

/* An AI write (a reviewer's answer to the owner's reply, /api/ai/feedback; a review reworded, /api/ai/review; the
 * teacher's voice, v4/teach-tour.js) saves after the model has written, seconds later, and bumps the revision. Off the
 * command queue it landed under a tap already on its way: 409 revision_conflict on fb_reply and the taps after it
 * (about 29 sessions on 06/10: trà sữa, quần áo, cà phê, thư ký, homestay), and a tap dropped when it moved again
 * under the one retry. So it takes its place in the queue (after the taps already queued) and the taps after it wait
 * until it lands, AI_WAIT at most from when it was sent: a usual answer lands first, a slow model never freezes the
 * screen (a later landing is what the one 409 retry in command() is for). Returns the write's own promise. */
export const AI_WAIT=4000;
export function aiQueued(api,fn,wait=AI_WAIT){
  let sent;const started=new Promise(resolve=>{sent=resolve;});
  const run=()=>{sent();return fn();};
  const job=api.queue.then(run,run);
  api.queue=Promise.race([job.then(()=>{},()=>{}),started.then(()=>sleep(wait))]);
  return job;
}

/** The "Đang cập nhật máy chủ…" note: shown once a retry has lasted `after` ms, gone with the last one.
 * Top layer (popover) so an open sheet does not hide it; inline styles, never takes a tap. */
export class UpdatingNote{
  constructor(lang=()=>'vi',doc=globalThis.document,after=400){this.lang=lang;this.doc=doc;this.after=after;this.count=0;this.el=null;this.timer=null;}
  hold(){if(this.count++===0)this.timer=setTimeout(()=>this.show(),this.after);}
  release(){if(--this.count>0)return;this.count=0;clearTimeout(this.timer);this.timer=null;this.el?.remove?.();this.el=null;}
  show(){
    const doc=this.doc;if(!doc?.body||this.el)return;
    const el=this.el=doc.createElement('div');el.className='net-hold';el.setAttribute('role','status');el.setAttribute('aria-live','polite');
    el.textContent=this.lang()==='en'?'Updating the server…':UPDATING_TEXT;
    if(el.style)el.style.cssText='position:fixed;inset:auto;top:calc(env(safe-area-inset-top,0px) + 10px);left:50%;transform:translateX(-50%);z-index:2147483000;margin:0;padding:7px 14px;border:0;border-radius:99px;'
      +'background:rgba(58,42,33,.92);color:#fff;font:600 13px/1.3 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.2);pointer-events:none;white-space:nowrap;max-width:calc(100vw - 24px);overflow:hidden';
    doc.body.append(el);
    if(typeof el.showPopover==='function'){try{el.popover='manual';el.showPopover();}catch{/* fixed + z-index is enough */}}
  }
}

/** Merge a part of the catalogue into it: a key both have as an object (journey, experiences) gets the part's
 * members added, anything else is set. */
export function mergeContent(content,part){
  for(const [key,value] of Object.entries(part||{})){
    const have=content[key];
    if(have&&value&&typeof have==='object'&&typeof value==='object'&&!Array.isArray(have)&&!Array.isArray(value))Object.assign(have,value);
    else content[key]=value;
  }
  return content;
}

/* Smaller state answers (game/state_delta.py). Every request says X-Game-Delta: 1; an answer whose `state` is the
 * public state then also has `delta` = {refs:[[path,hash]…], keys:[[path,hash]…]}: `keys` name the parts of the state
 * sent in it (by a hash of their JSON), `refs` the places where the state holds a 0 instead of a part this page
 * already has. A command sends the hashes it holds (`known`), so what did not change does not come again. A server
 * that knows nothing of this answers in full without `delta`: taken as before, and the held parts are dropped.
 * The parts are shared between the states this page keeps: nothing may change a state in place (it never did:
 * every answer replaced it whole). */
/** The parts a page holds: hash → part, and the named parts inside each split one (lent on when it is reused whole). */
export class Held{
  constructor(parts=new Map(),kids=new Map()){this.parts=parts;this.kids=kids;}
  /** For a command's `known`: the hashes, 8 characters each, one after the other. */
  known(){return [...this.parts.keys()].join('');}
}
const NONE=new Held();
const at=(root,path,n=path.length)=>{
  let node=root;
  for(let i=0;i<n;i++){if(node===null||typeof node!=='object')throw new Error('state delta: no such path');node=node[path[i]];}
  return node;
};
/** Fill the 0 placeholders of an answer's state from `held` (the parts the page held when it sent the request) and
 * return the parts it holds after it, or null for an answer without `delta` (a whole state). Throws when a
 * reference cannot be filled: the caller reads the whole state instead. Taking the same answer twice is harmless. */
export function inflate(data,held=NONE){
  const d=data?.delta;if(!d||typeof d!=='object')return null;
  if(d.held)return d.held;
  const refs=Array.isArray(d.refs)?d.refs:[],keys=Array.isArray(d.keys)?d.keys:[];
  const parts=new Map(),kids=new Map(),state=data.state;
  const carry=h=>{if(parts.has(h))return;parts.set(h,held.parts.get(h));const k=held.kids.get(h);if(k){kids.set(h,k);for(const x of k)carry(x);}};
  for(const [path,h] of refs){
    if(!held.parts.has(h))throw new Error('state delta: a part this page does not hold');
    const parent=at(state,path,path.length-1),key=path[path.length-1];
    if(parent===null||typeof parent!=='object'||parent[key]!==0)throw new Error('state delta: no placeholder');
    parent[key]=held.parts.get(h);carry(h);
  }
  const named=new Map();
  for(const [path,h] of keys){parts.set(h,at(state,path));named.set(JSON.stringify(path),h);}
  for(const list of [refs,keys])for(const [path,h] of list){
    for(let n=path.length-1;n>0;n--){const p=named.get(JSON.stringify(path.slice(0,n)));if(p!==undefined){const k=kids.get(p);if(k)k.push(h);else kids.set(p,[h]);break;}}
  }
  Object.defineProperty(d,'held',{value:new Held(parts,kids)});
  return d.held;
}
/** Dev only (localhost with ?deltacheck=1, or localStorage mnl.deltacheck=1): every adopted state is frozen (a change in
 * place throws where it is made) and each command's state is compared with a fresh GET /api/state. */
const DELTA_CHECK=(()=>{try{return /^(localhost|127\.0\.0\.1)$/.test(globalThis.location?.hostname||'')&&(/[?&]deltacheck=1\b/.test(globalThis.location.search)||globalThis.localStorage?.getItem('mnl.deltacheck')==='1');}catch{return false;}})();
const freeze=x=>{if(x&&typeof x==='object'&&!Object.isFrozen(x)){Object.freeze(x);for(const v of Object.values(x))freeze(v);}return x;};
const canon=x=>Array.isArray(x)?`[${x.map(canon).join(',')}]`:x&&typeof x==='object'?`{${Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')}}`:JSON.stringify(x);

/** Ordered mutations + idempotent retry. A lost response never doubles a sale. */
export class GameAPI extends EventTarget {
  constructor(){super();this.state=null;this.content=null;this.revision=0;this.accepted=0;this.done=[];this.csrf='';this.ai={configured:false};this.auth={tiktok:{enabled:false,mode:'sandbox'}};this.social=null;this.push={enabled:false};this.clockOffset=0;this.clock=[];this.connected=false;this.queue=Promise.resolve();
    // The release this page booted with (<meta name="mnl-version">, read by boot.js) vs X-Game-Version.
    this.updates=new UpdateNotice(globalThis.__mnlBoot?.version||'',{prewarm:globalThis.document?()=>prewarmRelease():null});
    this.delays=RETRY_DELAYS;this.retryWindow=RETRY_WINDOW;this.holding=new UpdatingNote(()=>this.lang);this.held=NONE;
    if(DELTA_CHECK)globalThis.__mnlApi=this;}  // dev only: scripts/browser_state_delta.py reads the page's state
  /** In-flight request count, announced as a 'net' event (app.js ties it to the tapped button). */
  net(delta){this.inflight=(this.inflight||0)+delta;this.dispatchEvent(new CustomEvent('net',{detail:this.inflight}));}
  /** One API call. `options.retry`: send again through a restart (default: GET yes, other methods no;
   * command() turns it on). `early`: a request boot.js already sent, never re-sent here. */
  async json(url,options={},timeout=12000,early=null){
    const {retry,...init}=options;init.headers={...init.headers,'X-Game-Delta':'1'};  // see Held
    // Writes on the wire (commands, posts): the update pill never reloads the page under one (update.js).
    const write=Boolean(init.method&&init.method!=='GET');if(write)this.writing=(this.writing||0)+1;
    this.net(1);
    try{
      if(early||!(retry??!write))return await this.fetchJSON(url,init,timeout,early);
      return await this.retrying(()=>this.fetchJSON(url,init,timeout));
    }catch(error){this.failed(url,error);throw error;}
    finally{if(write)this.writing--;this.net(-1);}
  }
  /** A call that failed for good (after its retries): an 'apifail' event with the status, the path and the server's
   * error code only (public/js/telemetry.js counts it; no query string, no body). */
  failed(url,error){
    let route=String(url||'');try{route=new URL(route,globalThis.location?.href||'http://x/').pathname;}catch{route=route.split('?')[0];}
    this.dispatchEvent(new CustomEvent('apifail',{detail:{route,status:error?.status||0,code:String(error?.data?.code||'')}}));
  }
  async retrying(send){
    const t0=Date.now();let held=false;
    try{
      for(let i=0;;i++){
        try{return await send();}
        catch(error){
          if(!transient(error)||i>=this.delays.length||Date.now()-t0>=this.retryWindow)throw error;
          if(!held){held=true;this.holding.hold();this.dispatchEvent(new CustomEvent('updating',{detail:true}));}
          await sleep(this.delays[i]);
        }
      }
    }finally{if(held){this.holding.release();this.dispatchEvent(new CustomEvent('updating',{detail:false}));}}
  }
  async fetchJSON(url,options,timeout,early=null){
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeout);
    try {
      const sent=early?.sent??Date.now();
      // `early`: a request already on the wire (public/js/boot.js), still bound by the same timeout.
      const response=await (early?Promise.race([early.response,new Promise((_,reject)=>controller.signal.addEventListener('abort',()=>reject(new DOMException('Timeout','AbortError'))))])
        :fetch(url,{credentials:'same-origin',...options,signal:controller.signal}));
      const got=early?early.got?.()??Date.now():Date.now();   // the headers are in (boot.js stamps its own)
      const version=response.headers.get('X-Game-Version');
      let data=null;
      try{
        if(this.perfEnabled){
          const raw=await response.text();   // body/network wait is not JSON parse CPU time
          if(this.perfEnabled){
            const started=performance.now();
            try{data=JSON.parse(raw);}
            finally{this.dispatchEvent(new CustomEvent('clientperf',{detail:{parse:performance.now()-started}}));}
          }else data=JSON.parse(raw);   // the page reached its sample cap while the body was arriving
        }else data=await response.json();
      }catch{/* not JSON: the proxy's own 502/504 page, or a body cut off */}
      // Server clock for real-time workbenches (boiling, ovens, dye timers, stop taps): see clockSample.
      if(typeof data?.server_time==='number')this.clockOffset=clockSample(this.clock,sent,got,data.server_time,data.server_recv);
      const outdated=response.status===426||OUTDATED_CODES.has(data?.code);
      this.updates.seen(version,outdated);
      if(!response.ok){const error=new Error(data?.error||(TRANSIENT.has(response.status)?BUSY_TEXT:`Lỗi ${response.status}`));error.status=response.status;error.data=data||{};throw error;}
      if(data===null)throw new TypeError('Phản hồi không đọc được.');  // treated like a lost connection
      this.connected=true;return data;
    } finally {clearTimeout(timer);}
  }
  async init(){
    // boot.js starts /api/bootstrap?lite=1 and /api/content?v=<hash>&part=core while the modules download; use
    // them (a network hiccup asks again). lite=1: the catalogue is not inlined, it comes from /api/content,
    // which the browser keeps for a year (the URL changes with the content). Its other parts: more() and
    // careerContent() below.
    const boot=globalThis.__mnlBoot||{},early=boot.response?{sent:boot.sent,response:boot.response,got:()=>boot.got}:null;
    const earlyContent=boot.content&&boot.contentUrl?{sent:boot.sent,response:boot.content,url:boot.contentUrl}:null;
    this.early=boot.place||null;this.contentBase=boot.contentBase||'';
    boot.response=boot.content=boot.place=null;let data=null,content=null;
    if(early)try{data=await this.json('/api/bootstrap?lite=1',{},12000,early);}catch(error){if(!transient(error))throw error;}
    data??=await this.json('/api/bootstrap?lite=1');
    content=data.content||null;  // a server from before the split still inlines it
    if(!content&&earlyContent)try{content=await this.json(earlyContent.url,{},30000,earlyContent);}catch(error){if(!transient(error))throw error;}
    content??=await this.json(data.content_url||'/api/content',{},30000);  // the whole catalogue
    this.contentBase||=data.content_url||'';
    // The stylesheets load without blocking the splash (boot.js); the game is shown once they are in.
    await boot.css;
    this.content=content;this.csrf=data.csrf;this.ai=data.ai;this.auth=data.auth||{tiktok:{enabled:false,mode:'sandbox'}};this.social=data.social||null;this.push=data.push||{enabled:false};this.account=data.account||null;this.admin=data.admin===true;this.gifts=Array.isArray(data.gifts)?data.gifts:[];this.xfers=Array.isArray(data.xfers)?data.xfers:[];this.lbTitles=Array.isArray(data.lb_titles)?data.lb_titles:[];this.quayInvites=Number.isSafeInteger(data.quay_invites)?data.quay_invites:0;this.live=data.live||null;this.uiConfig=data.ui||null;this.accept(data);
    this.updates.watch(()=>fetch('/api/health',{credentials:'same-origin',cache:'no-store'}).then(r=>{this.updates.seen(r.headers.get('X-Game-Version'));}));
    return data;
  }
  /** True once the whole catalogue is in: a `core` part (game/content.py content_parts) lacks CONTENT_LATER. */
  hasMore(){return this.content?.part!=='core';}
  /** The catalogue's `more` part (job postings, the shop book, situations, certificate and story texts): fetched
   * once (app.js asks right after the first frame; a view that needs it asks too and shows a skeleton meanwhile),
   * merged into this.content, then a 'mnl:lazy' event re-renders the screen. */
  more(){
    if(this.hasMore())return Promise.resolve(this.content);
    return this._more??=this.json(`${this.contentBase}&part=more`,{},30000).then(part=>{
      mergeContent(this.content,part);this.content.part='whole';
      globalThis.document?.dispatchEvent(new CustomEvent('mnl:lazy',{detail:{wanted:true}}));
      return this.content;
    },error=>{this._more=null;throw error;});
  }
  /** False while a plugin workplace's part of the catalogue (content.careers[id]) is still to come. */
  hasCareerContent(id){const all=this.content?.careers;return !all||!Object.hasOwn(all,id)||Boolean(all[id]);}
  /** A workplace's own part of the catalogue (content.careers[id], a plugin career's data): loaded with its
   * workbench (app.js careerAssets), before its first frame. boot.js has usually started it already. */
  careerContent(id){
    const all=this.content?.careers;
    if(!id||this.hasCareerContent(id)||!this.contentBase)return Promise.resolve();
    this._places??={};
    const url=`${this.contentBase}&career=${encodeURIComponent(id)}`,early=this.early?.url===url?this.early:null;
    if(early)this.early=null;
    return this._places[id]??=(early?this.json(url,{},30000,early).catch(error=>{if(!transient(error))throw error;return this.json(url,{},30000);})
      :this.json(url,{},30000)).then(part=>{all[id]=part||{};},error=>{delete this._places[id];console.warn('careerContent',id,error);});
  }
  /** Adopt a state from the server. `since` (a read: this.accepted when it was sent): an answer older than a state
   * adopted meanwhile (a command's, while /api/state was on the wire) is left out, so the screen never shows a done
   * step undone and the next tap is not sent against that older revision. Returns whether it was adopted.
   * `inflatedMs`: sampled delta reconstruction already done by command(), before entering this method. */
  accept(data,since,inflatedMs=0){
    if(since!==undefined&&since!==this.accepted&&typeof data?.revision==='number'&&data.revision<this.revision)return false;
    const started=this.perfEnabled?performance.now():null;
    // A command's answer was filled in command(); any other `delta` only names parts (it has no references).
    const held=inflate(data,this.held);
    if(this.account&&this.state?.name!==undefined&&this.state.name!==data.state?.name&&typeof data.state?.name==='string'&&data.state.name.trim())this.account.display=data.state.name;
    this.accepted++;
    this.state=DELTA_CHECK?freeze(data.state):data.state;this.revision=data.revision;this.connected=true;this.syncedAt=Date.now();this.held=held||NONE;
    // boot.js starts the English pack early for English players.
    const lang=data.state?.settings?.lang;if(lang&&lang!==this.lang){this.lang=lang;try{localStorage.setItem('mnl.lang',lang);}catch{/* storage blocked */}}
    const applied=started===null?null:performance.now();
    this.dispatchEvent(new CustomEvent('state',{detail:data}));
    // Includes synchronous state listeners (the app's renderMain/renderSheet), not later paint or async work.
    if(started!==null&&this.perfEnabled)this.dispatchEvent(new CustomEvent('clientperf',{detail:{apply:applied-started+inflatedMs,render:performance.now()-applied}}));
    return true;
  }
  /** Dev only (DELTA_CHECK): the state built from references equals the server's whole state. */
  async deltaCheck(){
    const mine=this.state,revision=this.revision;
    try{
      const r=await fetch('/api/state',{credentials:'same-origin',cache:'no-store'}),whole=await r.json();
      if(whole.revision!==revision||this.state!==mine)return;  // moved on meanwhile: nothing to compare
      const D=globalThis.__mnlDelta??={checked:0,bad:0};D.checked++;
      const plain=s=>s?.fair?{...s,fair:{...s.fair,now:0,ganh:s.fair.ganh&&{...s.fair.ganh,modes:0}}}:s;  // these move with the clock
      const a=canon(plain(mine)),b=canon(plain(whole.state));
      if(a!==b){let i=0;while(a[i]===b[i])i++;D.bad++;console.error('state delta: the merged state differs from /api/state at revision',revision,a.slice(Math.max(0,i-160),i+60),b.slice(Math.max(0,i-160),i+60));}
    }catch(error){console.warn('deltaCheck',error);}
  }
  async refresh(){
    if(this.refreshing)return this.refreshing;
    const since=this.accepted;
    const work=(async()=>{const data=await this.json('/api/state');this.accept(data,since);return data;})();
    this.refreshing=work;
    try{return await work;}finally{if(this.refreshing===work)this.refreshing=null;}
  }
  // No career given: the workplace on screen. A new account has no `current` yet; the screen is drawn from `focus`
  // (app.js career(), v4/careers.js careerContext), so the command goes there too ("Chọn một nghề trước nhé" on the
  // first milk-tea tap). `jr_*`, `fair_*`, `settings` ignore it.
  /* Double taps while the queue is held (1.9.3 regression, 07/10). An AI write (aiQueued) holds the queue up to
   * AI_WAIT, and a command waiting behind it showed nothing: 'busy' fired only when a command started, so ui.busy
   * stayed false, the click hold and the submit guard let a second tap through, and the pending mark (a request
   * started within 400 ms of the tap) never came. Players tapped again; the copies queued up, the first landed and
   * the rest were refused ("Khách đang đọc phản hồi trước của bạn.", "Còn một chuyện trong lớp cần xử lý trước.").
   * Now:
   * - an IDENTICAL command (same career, action and payload) already queued or on the wire is not queued again:
   *   the caller gets the same promise;
   * - 'busy' (true) fires when a command is QUEUED and (false) once no command is queued or on the wire, and a
   *   'queued' event names each new one (app.js marks the tapped control pending with it). */
  /** The promise of an identical command queued or on the wire, or null (v4 florist's timers ask before sending). */
  sending(action,payload={},career=this.state?.current||this.state?.focus){return this.flying?.get(JSON.stringify([career,action,payload]))||null;}
  /** Commands queued or on the wire; 'busy' follows it (0 ↔ more). */
  hold(delta){
    const was=this.waiting|0;this.waiting=Math.max(0,was+delta);
    if(!was&&this.waiting)this.dispatchEvent(new CustomEvent('busy',{detail:true}));
    else if(was&&!this.waiting)this.dispatchEvent(new CustomEvent('busy',{detail:false}));
  }
  command(action,payload={},career=this.state?.current||this.state?.focus){
    const tap=JSON.stringify([career,action,payload]);
    const same=this.flying?.get(tap);if(same)return same;
    // A stop tap on a running meter (v4/careers.js): the moment the finger came down rides along as tap_at.
    const stamp=this.tapStamp?.(action);if(stamp)payload={...payload,tap_at:stamp.at};
    const execute=async()=>{
      let expected=this.revision,held=this.held;
      const send=()=>{
        const request_id=globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
        expected=this.revision;held=this.held;
        // `known`: the parts held now; the answer refers to them (filled from `held`, whatever is adopted meanwhile).
        // `cv`: this page's release (server.py MIN_CLIENT: an older page is answered 426 client_outdated and reloads).
        const known=held.known(),body=JSON.stringify({request_id,expected_revision:expected,career,action,payload,cv:this.updates?.own||'',...known?{known}:{}});
        // The same body (request_id, expected_revision) on every try: see RETRY_DELAYS.
        return this.json('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body,retry:true});
      };
      try{
        let data;
        // 409 revision_conflict: the save moved under this tap (a spouse's gift or fund move landing through the
        // marriage inbox, a ticker, another tab). Adopt the server's state (or read it), then:
        // - this very step already landed from this tab after the screen the tap was made on (a double tap let
        //   through by an older screen): it is not sent again, and the tap ends quietly (result.duplicate);
        // - else the tap is sent once more against it (a new request_id; the server checks everything again);
        // - moved again under that retry: the tap is dropped quietly (error.quiet, no toast), the screen shows the
        //   server's state and the player taps again if they still want it. Never applied twice: a lost answer is
        //   replayed by its request_id (RETRY_DELAYS), a conflict was not applied at all.
        for(let tries=0;;tries++){
          try{data=await send();break;}
          catch(error){
            if(error.status===409&&error.data?.code==='revision_conflict'){
              if(error.data.state)this.accept(error.data);else await this.refresh().catch(()=>{});
              if(this.done.some(d=>d.tap===tap&&d.revision>expected&&Date.now()-d.at<DOUBLE_TAP_MS))return {message:'',duplicate:true};
              if(tries===0)continue;
              error.quiet=true;error.message='';
            }else if(error.status===409&&error.data?.state)this.accept(error.data);
            throw error;
          }
        }
        let inflatedMs=0;
        try{
          const started=this.perfEnabled?performance.now():null;
          try{inflate(data,held);}finally{if(started!==null)inflatedMs=performance.now()-started;}
        }
        catch(error){  // never seen: a reference to a part not held. The whole state instead (the command did land).
          console.warn(error);const whole=await this.json('/api/state');data={...data,state:whole.state,revision:whole.revision,delta:whole.delta};
        }
        this.accept(data,undefined,inflatedMs);
        if(DELTA_CHECK&&data.delta?.refs?.length)this.deltaCheck();
        this.done.push({tap,revision:data.revision,at:Date.now()});if(this.done.length>8)this.done.shift();   // landed (or replayed: landed before)
        // v4/sounds.js: detail sounds and the bank speaker (result.bank) follow each confirmed command.
        this.dispatchEvent(new CustomEvent('result',{detail:{action,career,result:data.result}}));
        return data.result;
      }catch(error){
        if(transient(error)){this.connected=false;this.dispatchEvent(new Event('offline'));error.message='Mất kết nối máy chủ. Tiến trình đã xác nhận vẫn được lưu. Khởi động lại server rồi thử lại nhé.';}
        else if(!error.quiet)this.dispatchEvent(new CustomEvent('rejected',{detail:{action,career,status:error.status,code:error.data?.code||'',message:error.message}}));  // its toast text (telemetry.js)
        throw error;
      }finally{stamp?.done();}
    };
    const job=this.queue.then(execute,execute);this.queue=job.catch(()=>{});
    (this.flying??=new Map()).set(tap,job);
    const done=()=>{if(this.flying.get(tap)===job)this.flying.delete(tap);this.hold(-1);};
    job.then(done,done);
    this.hold(1);this.dispatchEvent(new CustomEvent('queued',{detail:{action,career}}));
    return job;
  }
  async aiReply(npc){
    try{return await this.json('/api/ai/rephrase',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body:JSON.stringify({career:this.state.current||this.state.focus,npc})},11500);}
    catch{return {mode:'scripted',reason:'unavailable'};}
  }
  post(url,body,timeout=12000){return this.json(url,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body:JSON.stringify(body)},timeout);}
  /** An AI save write in the command queue (see aiQueued). `since` is taken when it is sent: an answer older than a
   * state a later tap adopted meanwhile (the model was slower than AI_WAIT) is left out, the screen never steps back. */
  async aiWrite(url,body){
    let since;
    try{const data=await aiQueued(this,()=>{since=this.accepted;return this.post(url,body,25000);},this.aiWait??AI_WAIT);if(data?.state)this.accept(data,since);return data;}
    catch{return {mode:'none'};}
  }
  /** Reviewer answers the owner's reply (AI persona when allowed, scripted otherwise). */
  aiFeedback(post,career=this.state.current||this.state.focus){return this.aiWrite('/api/ai/feedback',{career,post});}
  /** Rewrite a fresh scripted review in the reviewer's own voice (optional). */
  aiReview(post,career=this.state.current||this.state.focus){return this.aiWrite('/api/ai/review',{career,post});}
  async socialGet(route,query={}){
    const q=new URLSearchParams(Object.entries(query).filter(([,v])=>v!==undefined&&v!==null&&v!=='')).toString();
    return this.json(`/api/social/${route}${q?'?'+q:''}`);
  }
  async socialPost(route,body={}){
    const data=await this.post(`/api/social/${route}`,body);
    // Trades and gifts change coins/stock: refresh the authoritative state.
    if(['gift','buy','list','unlist'].includes(route))await this.refresh().catch(()=>{});
    return data;
  }
  /** Optional account: register / login / logout / password. The cookie is rotated by the server. */
  async accountPost(route,body={}){const data=await this.post(`/api/account/${route}`,body,20000);if(data.csrf)this.csrf=data.csrf;if('account' in data)this.account=data.account;return data;}
  async deleteAccount(){return this.post('/api/account/delete',{confirm:'XOA'});}
  async exportSave(){const data=await this.json('/api/save/export');return data;}
}
