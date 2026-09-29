/** Operator site data layer. Uses only existing endpoints, each re-checked by the server:
 *  GET  /api/bootstrap            session cookie + CSRF + `account` + `admin` flag (+ career catalogue)
 *  GET  /api/feedback/mine        cheap `admin` re-check after signing in
 *  POST /api/account/login|logout the game's own account API (same rate limits, same answers)
 *  GET  /api/admin/stats          dashboard numbers (game/admin_stats.py)
 *  GET/POST /api/admin/feedback   feedback inbox (game/player_feedback.py)
 * The CSRF token lives only in memory; nothing is written to storage. */

export class AdminAPI{
  constructor(){this.csrf='';this.account=null;this.admin=false;this.careers={};}

  async json(url,options={},timeout=20000){
    const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),timeout);
    try{
      const res=await fetch(url,{credentials:'same-origin',cache:'no-store',...options,signal:ctl.signal});
      let data={};try{data=await res.json();}catch{data={};}
      if(!res.ok){const e=new Error(data.error||`Lỗi ${res.status}`);e.status=res.status;e.code=data.code||'';throw e;}
      return data;
    }catch(e){
      if(!e.status){const n=new Error(e.name==='AbortError'?'Máy chủ phản hồi quá lâu. Thử lại nhé.':'Mất kết nối máy chủ. Thử lại sau nhé.');n.status=0;throw n;}
      throw e;
    }finally{clearTimeout(timer);}
  }
  get(url,timeout){return this.json(url,{headers:{'X-Game-CSRF':this.csrf}},timeout);}
  post(url,body,timeout){return this.json(url,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':this.csrf},body:JSON.stringify(body)},timeout);}

  /** Session, CSRF and who is signed in. Only the pieces the site needs are kept. */
  async bootstrap(){
    const d=await this.json('/api/bootstrap',{},30000);
    this.csrf=d.csrf||'';this.account=d.account||null;this.admin=d.admin===true;
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
  stats(range,fresh=false){return this.get(`/api/admin/stats?range=${range}${fresh?'&fresh=1':''}`,30000);}
  inbox(filter,before){
    const q=new URLSearchParams();
    if(filter.status)q.set('status',filter.status);
    if(filter.kind)q.set('kind',filter.kind);
    if(before)q.set('before',before);
    return this.get('/api/admin/feedback?'+q);
  }
  update(body){return this.post('/api/admin/feedback',body);}
}
