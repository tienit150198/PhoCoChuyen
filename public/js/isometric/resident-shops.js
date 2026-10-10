/** Public discovery only. Visits and shop creation remain owned by their existing server flows. */
const text=(value,max)=>typeof value==='string'?value.trim().slice(0,max):'';

export function normalizeResidentShops(data){
  const out=[],seen=new Set();
  for(const place of (Array.isArray(data?.places)?data.places:[]).slice(0,60)){
    if(!place||place.visibility!=='public'||!['career','quay'].includes(place.kind))continue;
    const id=text(place.id,100),name=text(place.name,100),target=text(place.target,100),ownerName=text(place.owner?.name,40);
    if(!id||!name||!target||!ownerName||seen.has(id))continue;
    seen.add(id);out.push({id,name,kind:place.kind,target,ownerName,career:place.kind==='career'?target:text(place.career,80)});
    if(out.length===24)break;
  }
  return out;
}

/** No timer or subscription: callers explicitly load when discovery is opened. */
export function createResidentDirectory({now=Date.now,ttlMs=60000}={}){
  const ttl=Math.max(60000,Number(ttlMs)||60000);
  let account=null,source=null,epoch=0,pending=null,lastAttempt=null,state={status:'idle',shops:[]};
  const read=api=>{
    const name=api?.account?.username||'';
    if(source!==api||name!==account){
      source=api;account=name;epoch++;pending=null;lastAttempt=null;
      state={status:name?'idle':'guest',shops:[]};
    }
    return state;
  };
  const load=api=>{
    read(api);
    if(!account)return Promise.resolve(state);
    if(pending)return pending;
    if(lastAttempt!==null&&now()-lastAttempt<ttl)return Promise.resolve(state);
    lastAttempt=now();const version=epoch;
    state={status:'loading',shops:state.shops};
    pending=(async()=>{
      try{
        const data=await api.json('/api/work-visits/places?scope=public',{retry:false});
        if(version!==epoch)return state;
        read(api);
        if(version!==epoch)return state;
        if(!Array.isArray(data?.places))throw Error('Invalid directory response');
        const shops=normalizeResidentShops(data);
        state={status:shops.length?'ready':'empty',shops};
      }catch{
        if(version===epoch)read(api);
        if(version===epoch)state={status:'error',shops:[]};
      }finally{if(version===epoch)pending=null;}
      return state;
    })();
    return pending;
  };
  return {read,load};
}
