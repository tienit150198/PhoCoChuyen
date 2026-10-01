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

/** Ordered mutations + idempotent retry. A lost response never doubles a sale. */
export class GameAPI extends EventTarget {
  constructor(){super();this.state=null;this.content=null;this.revision=0;this.csrf='';this.ai={configured:false};this.social=null;this.push={enabled:false};this.clockOffset=0;this.connected=false;this.queue=Promise.resolve();
    // The release this page booted with (<meta name="mnl-version">, read by boot.js) vs X-Game-Version.
    this.updates=new UpdateNotice(globalThis.__mnlBoot?.version||'',{prewarm:globalThis.document?()=>prewarmRelease():null});
    this.delays=RETRY_DELAYS;this.retryWindow=RETRY_WINDOW;this.holding=new UpdatingNote(()=>this.lang);}
  /** In-flight request count, announced as a 'net' event (app.js ties it to the tapped button). */
  net(delta){this.inflight=(this.inflight||0)+delta;this.dispatchEvent(new CustomEvent('net',{detail:this.inflight}));}
  /** One API call. `options.retry`: send again through a restart (default: GET yes, other methods no;
   * command() turns it on). `early`: a request boot.js already sent, never re-sent here. */
  async json(url,options={},timeout=12000,early=null){
    const {retry,...init}=options;
    // Writes on the wire (commands, posts): the update pill never reloads the page under one (update.js).
    const write=Boolean(init.method&&init.method!=='GET');if(write)this.writing=(this.writing||0)+1;
    this.net(1);
    try{
      if(early||!(retry??!write))return await this.fetchJSON(url,init,timeout,early);
      return await this.retrying(()=>this.fetchJSON(url,init,timeout));
    }catch(error){this.failed(url,error);throw error;}
    finally{if(write)this.writing--;this.net(-1);}
  }
  /** A call that failed for good (after its retries): an 'apifail' event with the status and the path only
   * (public/js/telemetry.js counts it; no query string, no body). */
  failed(url,error){
    let route=String(url||'');try{route=new URL(route,globalThis.location?.href||'http://x/').pathname;}catch{route=route.split('?')[0];}
    this.dispatchEvent(new CustomEvent('apifail',{detail:{route,status:error?.status||0}}));
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
      const version=response.headers.get('X-Game-Version');
      let data=null;
      try{data=await response.json();}catch{/* not JSON: the proxy's own 502/504 page, or a body cut off */}
      // Server clock for real-time workbenches (boiling, ovens, dye timers).
      if(typeof data?.server_time==='number'){const rtt=Date.now()-sent;if(rtt<1500)this.clockOffset=data.server_time-(sent+rtt/2)/1000;}
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
    const boot=globalThis.__mnlBoot||{},early=boot.response?{sent:boot.sent,response:boot.response}:null;
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
    this.content=content;this.csrf=data.csrf;this.ai=data.ai;this.social=data.social||null;this.push=data.push||{enabled:false};this.account=data.account||null;this.admin=data.admin===true;this.gifts=Array.isArray(data.gifts)?data.gifts:[];this.accept(data);
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
  accept(data){
    this.state=data.state;this.revision=data.revision;this.connected=true;this.syncedAt=Date.now();
    // boot.js starts the English pack early for English players.
    const lang=data.state?.settings?.lang;if(lang&&lang!==this.lang){this.lang=lang;try{localStorage.setItem('mnl.lang',lang);}catch{/* storage blocked */}}
    this.dispatchEvent(new CustomEvent('state',{detail:data}));
  }
  async refresh(){const data=await this.json('/api/state');this.accept(data);return data;}
  command(action,payload={},career=this.state?.current){
    const execute=async()=>{
      const send=()=>{
        const request_id=globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const body=JSON.stringify({request_id,expected_revision:this.revision,career,action,payload});
        // The same body (request_id, expected_revision) on every try: see RETRY_DELAYS.
        return this.json('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body,retry:true});
      };
      this.dispatchEvent(new CustomEvent('busy',{detail:true}));
      try{
        let data;
        // 409 revision_conflict: the save moved under this tap (a spouse's gift or fund move landing through the
        // marriage inbox, a ticker, another tab). Adopt the server's state and send the tap once more against it
        // (a new request_id; the server checks everything again); a second conflict is reported.
        for(let tries=0;;tries++){
          try{data=await send();break;}
          catch(error){
            if(error.status===409&&error.data?.state){this.accept(error.data);if(tries===0&&error.data.code==='revision_conflict')continue;}
            throw error;
          }
        }
        this.accept(data);
        // v4/sounds.js: detail sounds and the bank speaker (result.bank) follow each confirmed command.
        this.dispatchEvent(new CustomEvent('result',{detail:{action,career,result:data.result}}));
        return data.result;
      }catch(error){
        if(transient(error)){this.connected=false;this.dispatchEvent(new Event('offline'));error.message='Mất kết nối máy chủ. Tiến trình đã xác nhận vẫn được lưu. Khởi động lại server rồi thử lại nhé.';}
        else this.dispatchEvent(new CustomEvent('rejected',{detail:{action,career,status:error.status,code:error.data?.code||'',message:error.message}}));  // its toast text (telemetry.js)
        throw error;
      }finally{this.dispatchEvent(new CustomEvent('busy',{detail:false}));}
    };
    const job=this.queue.then(execute,execute);this.queue=job.catch(()=>{});return job;
  }
  async aiReply(npc){
    try{return await this.json('/api/ai/rephrase',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body:JSON.stringify({career:this.state.current,npc})},11500);}
    catch{return {mode:'scripted',reason:'unavailable'};}
  }
  post(url,body,timeout=12000){return this.json(url,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body:JSON.stringify(body)},timeout);}
  /** Reviewer answers the owner's reply (AI persona when allowed, scripted otherwise). */
  async aiFeedback(post,career=this.state.current){
    try{const data=await this.post('/api/ai/feedback',{career,post},25000);if(data.state)this.accept(data);return data;}
    catch{return {mode:'none'};}
  }
  /** Rewrite a fresh scripted review in the reviewer's own voice (optional). */
  async aiReview(post,career=this.state.current){
    try{const data=await this.post('/api/ai/review',{career,post},25000);if(data.state)this.accept(data);return data;}
    catch{return {mode:'none'};}
  }
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
