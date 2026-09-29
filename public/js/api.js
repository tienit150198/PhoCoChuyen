/** Ordered mutations + idempotent retry. A lost response never doubles a sale. */
export class GameAPI extends EventTarget {
  constructor(){super();this.state=null;this.content=null;this.revision=0;this.csrf='';this.ai={configured:false};this.social=null;this.push={enabled:false};this.clockOffset=0;this.connected=false;this.queue=Promise.resolve();}
  async json(url,options={},timeout=12000){
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeout);
    try {
      const sent=Date.now();
      const response=await fetch(url,{credentials:'same-origin',...options,signal:controller.signal});
      const data=await response.json();
      // Server clock for real-time workbenches (boiling, ovens, dye timers).
      if(typeof data?.server_time==='number'){const rtt=Date.now()-sent;if(rtt<1500)this.clockOffset=data.server_time-(sent+rtt/2)/1000;}
      if(!response.ok){const error=new Error(data.error||`Lỗi ${response.status}`);error.status=response.status;error.data=data;throw error;}
      this.connected=true;return data;
    } finally {clearTimeout(timer);}
  }
  async init(){
    const data=await this.json('/api/bootstrap');this.content=data.content;this.csrf=data.csrf;this.ai=data.ai;this.social=data.social||null;this.push=data.push||{enabled:false};this.account=data.account||null;this.admin=data.admin===true;this.accept(data);return data;
  }
  accept(data){this.state=data.state;this.revision=data.revision;this.connected=true;this.dispatchEvent(new CustomEvent('state',{detail:data}));}
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
        this.accept(data);return data.result;
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
