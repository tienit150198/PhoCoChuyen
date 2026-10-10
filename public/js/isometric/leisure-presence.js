/** Public outdoor poses only. This local channel owns no socket or gameplay state. */
const DIRECTIONS=new Set(['se','sw','ne','nw']);
const PHASES={fishing:new Set(['walk','waiting','bite']),boat:new Set(['walk','boat','return']),pool:new Set(['walk','pool','return'])};
const ACTIONS={fishing:new Set(['cast','reel','caught']),boat:new Set(['board','exit']),pool:new Set(['board','exit'])};
const DISTRICTS=new Set(['homes-rent','homes-apartment','homes-townhouse','homes-villa']);
for(const kind of DISTRICTS){PHASES[kind]=new Set(['idle','walk']);ACTIONS[kind]=new Set();}

export function publicActivity(value){
  if(!value||typeof value!=='object')return null;
  const {kind,x,y,direction,phase}=value,action=typeof value.action==='object'?value.action?.kind??null:value.action??null;
  if(typeof kind!=='string'||!Object.hasOwn(PHASES,kind)||!PHASES[kind].has(phase)||!DIRECTIONS.has(direction)||
    !Number.isFinite(x)||!Number.isFinite(y)||(DISTRICTS.has(kind)?(x< -20||x>20||y< -20||y>20):(x<0||x>320||y<0||y>200))||
    action!==null&&!ACTIONS[kind].has(action)||value.moving!==undefined&&typeof value.moving!=='boolean')return null;
  return {kind,x:Math.round(x*100)/100,y:Math.round(y*100)/100,direction,phase,action,moving:value.moving===true};
}

/** publish(localState), subscribe(kind, callback), clear() are the scene-facing API.
 * The town bridge alone uses observeLocal/updatePeers, keeping one authenticated socket.
 */
export function createLeisurePresence(){
  let current=null,key='',peers=[];
  const observers=new Set(),subscriptions=new Set();
  const snapshot=kind=>peers.filter(peer=>peer.activity?.kind===kind).map(peer=>({...peer,activity:{...peer.activity}}));
  function publish(value){
    const sample=publicActivity(value);if(!sample)return false;
    const next=JSON.stringify(sample);if(next===key)return true;
    current=Object.freeze(sample);key=next;for(const callback of observers)callback(current);return true;
  }
  function clear(){
    if(!current)return;current=null;key='';for(const callback of observers)callback(null);
  }
  return {publish,clear,get current(){return current;},
    observeLocal(callback){observers.add(callback);return()=>observers.delete(callback);},
    subscribe(kind,callback){
      if(!Object.hasOwn(PHASES,kind)||typeof callback!=='function')return()=>{};
      const subscription={kind,callback};subscriptions.add(subscription);callback(snapshot(kind));
      return()=>subscriptions.delete(subscription);
    },
    updatePeers(values){
      peers=Array.isArray(values)?values:[];
      for(const {kind,callback} of subscriptions)callback(snapshot(kind));
    }};
}

export const leisurePresence=createLeisurePresence();
