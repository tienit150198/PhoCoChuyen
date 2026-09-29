import {UpdateNotice,OUTDATED_CODES} from './update.js';

/** Ordered mutations + idempotent retry. A lost response never doubles a sale. */
export class GameAPI extends EventTarget {
  constructor(){super();this.state=null;this.content=null;this.revision=0;this.csrf='';this.ai={configured:false};this.social=null;this.push={enabled:false};this.clockOffset=0;this.connected=false;this.queue=Promise.resolve();
    // The release this page booted with (<meta name="mnl-version">, read by boot.js) vs X-Game-Version.
    this.updates=new UpdateNotice(globalThis.__mnlBoot?.version||'');}
  /** In-flight request count, announced as a 'net' event (app.js ties it to the tapped button). */
  net(delta){this.inflight=(this.inflight||0)+delta;this.dispatchEvent(new CustomEvent('net',{detail:this.inflight}));}
  async json(url,options={},timeout=12000,early=null){
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeout);
    this.net(1);
    try {
      const sent=early?.sent??Date.now();
      // `early`: a request already on the wire (public/js/boot.js), still bound by the same timeout.
      const response=await (early?Promise.race([early.response,new Promise((_,reject)=>controller.signal.addEventListener('abort',()=>reject(new DOMException('Timeout','AbortError'))))])
        :fetch(url,{credentials:'same-origin',...options,signal:controller.signal}));
      const version=response.headers.get('X-Game-Version');
      const data=await response.json();
      // Server clock for real-time workbenches (boiling, ovens, dye timers).
      if(typeof data?.server_time==='number'){const rtt=Date.now()-sent;if(rtt<1500)this.clockOffset=data.server_time-(sent+rtt/2)/1000;}
      const outdated=response.status===426||OUTDATED_CODES.has(data?.code);
      this.updates.seen(version,outdated);
      if(!response.ok){const error=new Error(data.error||`Lỗi ${response.status}`);error.status=response.status;error.data=data;throw error;}
      this.connected=true;return data;
    } finally {clearTimeout(timer);this.net(-1);}
  }
  async init(){
    // boot.js starts /api/bootstrap?lite=1 and /api/content?v=<hash> while the modules download; use them
    // (a network hiccup asks again). lite=1: the catalogue is not inlined, it comes from /api/content,
    // which the browser keeps for a year (the URL changes with the content).
    const boot=globalThis.__mnlBoot||{},early=boot.response?{sent:boot.sent,response:boot.response}:null;
    const earlyContent=boot.content&&boot.contentUrl?{sent:boot.sent,response:boot.content,url:boot.contentUrl}:null;
    boot.response=boot.content=null;let data=null,content=null;
    if(early)try{data=await this.json('/api/bootstrap?lite=1',{},12000,early);}catch(error){if(error.status)throw error;}
    data??=await this.json('/api/bootstrap?lite=1');
    content=data.content||null;  // a server from before the split still inlines it
    if(!content&&earlyContent)try{content=await this.json(earlyContent.url,{},30000,earlyContent);}catch(error){if(error.status)throw error;}
    content??=await this.json(data.content_url||'/api/content',{},30000);
    // The stylesheets load without blocking the splash (boot.js); the game is shown once they are in.
    await boot.css;
    this.content=content;this.csrf=data.csrf;this.ai=data.ai;this.social=data.social||null;this.push=data.push||{enabled:false};this.account=data.account||null;this.admin=data.admin===true;this.accept(data);
    this.updates.watch(()=>fetch('/api/health',{credentials:'same-origin',cache:'no-store'}).then(r=>{this.updates.seen(r.headers.get('X-Game-Version'));}));
    return data;
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
      const request_id=globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const body=JSON.stringify({request_id,expected_revision:this.revision,career,action,payload});
      this.dispatchEvent(new CustomEvent('busy',{detail:true}));
      try{
        let data;
        for(let attempt=0;attempt<2;attempt++){
          try{data=await this.json('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body});break;}
          catch(error){
            if(error.status===409&&error.data.state){this.accept(error.data);throw error;}
            if(error.status||attempt===1)throw error;
            await new Promise(r=>setTimeout(r,300));
          }
        }
        this.accept(data);
        // v4/sounds.js: detail sounds and the bank speaker (result.bank) follow each confirmed command.
        this.dispatchEvent(new CustomEvent('result',{detail:{action,career,result:data.result}}));
        return data.result;
      }catch(error){
        if(!error.status){this.connected=false;this.dispatchEvent(new Event('offline'));error.message='Mất kết nối máy chủ. Tiến trình đã xác nhận vẫn được lưu. Khởi động lại server rồi thử lại nhé.';}
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
