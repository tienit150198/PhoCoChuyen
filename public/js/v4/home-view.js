/** Canonical display rules for the two views of one shared home. */
export function sharedRooms(rooms,mate){
  if(!mate?.skins)return rooms;
  return rooms.map(r=>({...r,skin:mate.skins[r.id]||{}}));
}

/** Local ids/p: ids reverse for the spouse; ownership rank must not. */
export function ownershipOrder(a,b,owner){
  const rank=o=>(o.mate?!owner:owner)?0:1;
  return rank(a)-rank(b)||String(a.id).replace(/^p:/,'').localeCompare(String(b.id).replace(/^p:/,''));
}

/** Guest projections stay outside api.state; the editor draft survives a visit and late network reads. */
export function guestSession(S){
  const keys=['tab','room','edit','held','sel','drawer','cat','undo','undoKey','try','tryTint','mate','mateState','mateKey','lastLv'];
  let saved=null,version=0,code='';
  function close(){version++;code='';S.remote=null;if(saved){Object.assign(S,saved);saved=null;}}
  async function refresh(read){
    const seq=++version,host=code;if(!host)return false;
    try{const data=await read(host);if(seq!==version||host!==code)return false;S.remote=data;S.mate=data.mate||null;return true;}
    catch(error){if(seq!==version||host!==code)return false;throw error;}
  }
  return {close,refresh,get code(){return code;},async open(host,read){
    if(!saved)saved=Object.fromEntries(keys.map(k=>[k,S[k]]));
    code=host;S.remote={owner:{code:host}};S.edit=false;S.held=null;S.sel='';S.try=null;S.tryTint=null;S.mate=null;
    try{return await refresh(read);}catch(error){close();throw error;}
  }};
}
