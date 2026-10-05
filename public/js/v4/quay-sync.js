/** A Quay projection never replaces the API's full state or revision. */
export function createQuaySync(api,changed=()=>{}){
  const identity=()=>JSON.stringify([api.account?.username||'',api.csrf||'']);
  let owner=identity(),projection=null,inFlight=null,disposed=false;
  const current=()=>{
    if(owner!==identity()){owner=identity();projection=null;}
    if(projection&&api.revision>=projection.revision)projection=null;
    return projection?.journey||api.state?.journey||{};
  };
  const signature=()=>{const j=current();return JSON.stringify([j.story,j.life_day,j.wallet,j.quay]);};
  let seen=signature();
  const announce=()=>{const key=signature();if(key!==seen){seen=key;if(!disposed)changed();}};
  const onState=()=>announce();
  api.addEventListener('state',onState);
  const refresh=()=>{
    if(inFlight)return inFlight;
    const account=identity();
    const work=(async()=>{
      const data=await api.json('/api/business/quay');
      if(disposed||account!==identity())return;
      if(!Number.isSafeInteger(data?.revision)||!data?.journey)throw new Error('Chưa đọc được cập nhật quầy.');
      current();
      if(data.revision<api.revision||projection&&data.revision<projection.revision)return;
      projection=data;
      announce();
      return data;
    })();
    inFlight=work;
    work.finally(()=>{if(inFlight===work)inFlight=null;}).catch(()=>{});
    return work;
  };
  const ensureCurrent=async()=>{
      const account=identity();
      // A poll may have committed settlement before its response reaches us.
      // Wait for that revision before deciding whether a full read is needed.
      if(inFlight)await inFlight.catch(()=>{});
      current();
      const required=projection?.revision??api.revision;
      if(required>api.revision){
        await api.refresh();
        // refresh() may have coalesced with a read sent before the projection.
        if(required>api.revision&&account===identity())await api.refresh();
      }
      if(account!==identity()||disposed)throw new Error('Phiên chơi đã thay đổi. Mở lại quầy nhé.');
      if(required>api.revision)throw new Error('Quầy đang đồng bộ. Thử lại nhé.');
  };
  return {
    journey:current,refresh,ensureCurrent,
    async command(action,payload={}){await ensureCurrent();return api.command(action,payload);},
    dispose(){disposed=true;projection=null;api.removeEventListener('state',onState);}
  };
}
