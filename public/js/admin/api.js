/** Operator site data layer. Uses only existing endpoints, each re-checked by the server:
 *  GET  /api/bootstrap?lite=1     session cookie + CSRF + `account` + `admin` flag (no catalogue)
 *  GET  /api/feedback/mine        cheap `admin` re-check after signing in
 *  POST /api/account/login|logout the game's own account API (same rate limits, same answers)
 *  GET  /api/admin/stats/summary  first screen in one call, with the career names (game/admin_stats.py)
 *  GET  /api/admin/stats/section  save-derived cards / "Hệ thống", when they are shown
 *  GET/POST /api/admin/feedback   feedback inbox (game/player_feedback.py)
 *  GET /api/admin/gifts, POST /api/admin/gift   🎁 Tặng xu (./gifts.js, game/system_gift.py)
 * The CSRF token lives only in memory; nothing is written to storage. */

export class AdminAPI{
  constructor(){this.csrf='';this.account=null;this.admin=false;this.careers={};}

  /** `options.signal`: the caller's AbortController; an abort it asked for rejects with `e.aborted`. */
  async json(url,options={},timeout=20000){
    const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),timeout),outer=options.signal;
    const stop=()=>ctl.abort();
    if(outer){if(outer.aborted)ctl.abort();else outer.addEventListener('abort',stop,{once:true});}
    try{
      const res=await fetch(url,{credentials:'same-origin',cache:'no-store',...options,signal:ctl.signal});
      let data={};try{data=await res.json();}catch{data={};}
      if(!res.ok){const e=new Error(data.error||`Lỗi ${res.status}`);e.status=res.status;e.code=data.code||'';throw e;}
      return data;
    }catch(e){
      if(outer?.aborted){const n=new Error('aborted');n.status=0;n.aborted=true;throw n;}
      if(!e.status){const n=new Error(e.name==='AbortError'?'Máy chủ phản hồi quá lâu. Thử lại nhé.':'Mất kết nối máy chủ. Thử lại sau nhé.');n.status=0;throw n;}
      throw e;
    }finally{clearTimeout(timer);outer?.removeEventListener('abort',stop);}
  }
  get(url,timeout,signal){return this.json(url,{headers:{'X-Game-CSRF':this.csrf},signal},timeout);}
  post(url,body,timeout){return this.json(url,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body:JSON.stringify(body)},timeout);}

  /** Session, CSRF and who is signed in. Only the pieces the site needs are kept. */
  async bootstrap(){
    // lite: no ~0.4 MB catalogue; career names come with the stats summary (or loadNames()).
    const d=await this.json('/api/bootstrap?lite=1',{},30000);
    this.csrf=d.csrf||'';this.account=d.account||null;this.admin=d.admin===true;this.contentUrl=d.content_url||'';
    const cat=d.content?.catalogue;
    if(Array.isArray(cat))this.careers=Object.fromEntries(cat.map(c=>[c.id,c.short||c.name||c.id]));
    return this;
  }
  async login(username,password,replace=false){
    const d=await this.post('/api/account/login',{username,password,...(replace?{replace:true}:{})},30000);
    if(d.csrf)this.csrf=d.csrf;
    this.account=d.account||null;
    const mine=await this.json('/api/feedback/mine');
    this.admin=mine.admin===true;
    return d;
  }
  async logout(){
    try{await this.post('/api/account/logout',{});}
    finally{await this.bootstrap();}
  }
  career(id){return this.careers[id]||id;}
  setNames(names){if(names&&typeof names==='object')this.careers={...this.careers,...names};}
  /** Career names without the summary (the inbox opened first): the catalogue, cached by the browser. */
  async loadNames(){
    if(Object.keys(this.careers).length||!this.contentUrl)return false;
    this._names??=fetch(this.contentUrl,{credentials:'same-origin'}).then(r=>r.ok?r.json():{}).then(c=>{
      const cat=c?.catalogue;if(Array.isArray(cat))this.setNames(Object.fromEntries(cat.map(x=>[x.id,x.short||x.name||x.id])));return true;
    }).catch(()=>false).finally(()=>{this._names=null;});
    return this._names;
  }
  summary(range,{fresh=false,signal}={}){return this.get(`/api/admin/stats/summary?range=${range}${fresh?'&fresh=1':''}`,30000,signal);}
  section(name,{fresh=false,signal}={}){return this.get(`/api/admin/stats/section?name=${encodeURIComponent(name)}${fresh?'&fresh=1':''}`,90000,signal);}
  inbox(filter,before,signal){
    const q=new URLSearchParams();
    if(filter.status)q.set('status',filter.status);
    if(filter.kind)q.set('kind',filter.kind);
    if(before)q.set('before',before);
    return this.get('/api/admin/feedback?'+q,undefined,signal);
  }
  update(body){return this.post('/api/admin/feedback',body);}
}
