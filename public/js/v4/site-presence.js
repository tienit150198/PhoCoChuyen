/** An interior owns the single town membership until it closes. */
const observers=new Set();
export const sitePresence={active:false,set(value){this.active=value;for(const fn of observers)fn(value);},subscribe(fn){observers.add(fn);return()=>observers.delete(fn);}};
let sequence=0;
export function createSitePresence(key,{transport,onJoin,onPeers,onMessage,onClose,onStatus,onCorrect,appearance=()=>({})}={}){
  let room=null,me=null,joining=null,dead=false,started=false,timer=null,resolve,reject,ready=false,lastSent=0,lastPoint='';
  const peers=new Map(),off=[];
  const draw=()=>onPeers?.([...peers.values()].map(p=>({...p,x:p.x*20,y:p.y*20})));
  function join(){
    if(dead||transport.state!=='open'||!transport.flags?.town)return;
    joining=`site-${++sequence}`;transport.send({t:'site_in',...key,...appearance(),cid:joining});
    clearTimeout(timer);timer=setTimeout(()=>{onStatus?.('Kết nối cơ sở quá lâu. Hãy vào lại.');close('timeout');},12000);
  }
  function close(why='out'){
    if(dead)return;dead=true;clearTimeout(timer);off.splice(0).forEach(fn=>fn());
    if(room||joining)transport.send({t:'town_out',cid:`site-out-${++sequence}`});
    room=null;joining=null;peers.clear();draw();sitePresence.set(false);
    if(!ready)reject?.(new Error(why==='private'?'Cơ sở chưa mở đón khách.':'Chưa vào được cơ sở trực tuyến.'));
    onClose?.(why);
  }
  function start(){
    if(started)throw new Error('Site session already started');started=true;
    const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});
    off.push(transport.on('town_room',f=>{
      if(f.map!=='scale-site-v1'||f.cid!==joining)return;
      clearTimeout(timer);joining=null;room=f.room;me=f.me;lastPoint='';lastSent=0;peers.clear();
      for(const p of f.people||[])if(p.pid!==me)peers.set(p.pid,p);
      onCorrect?.({x:f.x*20,y:f.y*20});onJoin?.(f);draw();ready=true;resolve(f);onStatus?.('Đã vào cơ sở · Trò chuyện với người ở gần');
    }),transport.on('town_site',f=>{if(room&&f.room===room){onJoin?.(f);if(Number.isFinite(f.x)&&Number.isFinite(f.y))onCorrect?.({x:f.x*20,y:f.y*20});}}),transport.on('town',f=>{
      if(!room||f.room!==room)return;
      for(const e of f.ev||[]){if(e.pid===me)continue;if(e.k==='out')peers.delete(e.pid);else if(e.k==='in')peers.set(e.pid,e);else if(e.k==='mv'&&peers.has(e.pid))Object.assign(peers.get(e.pid),e);}draw();
    }),...['town_said','town_emoted','town_card'].map(t=>transport.on(t,f=>{if(room&&f.room===room)onMessage?.(f);})),
    transport.on('town_left',f=>{if(f.why==='other'||f.why==='private'&&(!f.room||f.room===room))close(f.why);}),
    transport.on('error',f=>{if(f.ref===joining){onStatus?.(f.msg);close(f.code);}else if(String(f.ref).startsWith('site-'))onStatus?.(f.msg);else if(f.ref==='town_mv'&&room&&Number.isFinite(f.x))onCorrect?.({x:f.x*20,y:f.y*20});}),
    transport.on('down',()=>{room=null;joining=null;clearTimeout(timer);peers.clear();draw();onStatus?.('Mất kết nối · Đang kết nối lại…');}),
    transport.on('welcome',()=>{room=null;joining=null;peers.clear();draw();join();}));
    sitePresence.set(true);
    if(transport.state==='open'&&transport.flags?.town)join();else close('off');
    return promise;
  }
  return {start,close,get room(){return room;},get destroyed(){return dead;},get peers(){return [...peers.values()];},
    move(point){if(!room||dead||Date.now()-lastSent<270)return;const p={x:point.x/20,y:point.y/20,direction:point.direction},value=JSON.stringify(p);if(value===lastPoint)return;if(transport.send({t:'town_mv',...p})){lastPoint=value;lastSent=Date.now();}},
    say(text){if(room)transport.send({t:'town_say',text,cid:`site-say-${++sequence}`});},
    emote(e,target){if(room)transport.send({t:'town_emote',e,...(target?{target}:{}),cid:`site-emote-${++sequence}`});},
    card(pid){if(room)transport.send({t:'town_card',pid,cid:`site-card-${++sequence}`});}};
}
