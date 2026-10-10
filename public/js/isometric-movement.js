/** Shared scene input only. Delivery driving keeps its existing steering and throttle. */
const KEY={arrowleft:[-1,0],a:[-1,0],arrowright:[1,0],d:[1,0],arrowup:[0,-1],w:[0,-1],arrowdown:[0,1],s:[0,1]};
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));

export function normaliseStick(dx,dy,radius=1,deadzone=.12){
  if(!Number.isFinite(dx)||!Number.isFinite(dy)||!Number.isFinite(radius)||radius<=0)return {x:0,y:0,knobX:0,knobY:0};
  const distance=Math.hypot(dx,dy)/radius,magnitude=Math.min(1,distance),dead=clamp(deadzone,0,.95);
  const ux=distance?dx/radius/distance:0,uy=distance?dy/radius/distance:0;
  const speed=magnitude>dead?(magnitude-dead)/(1-dead):0;
  return {x:ux*speed,y:uy*speed,knobX:ux*magnitude,knobY:uy*magnitude};
}

export function movementAllowed({available=false,mode,hidden=false,modal=false,menu=false,driving=false,paused=false,destroyed=false}={}){
  return available&&(mode==='town'||mode==='work')&&!hidden&&!modal&&!menu&&!driving&&!paused&&!destroyed;
}

/** Pure input ownership makes every release/overlay path use the same zero-input reset. */
export function createMovementController({onInput=()=>{},onVisual=()=>{},capturePointer=()=>{},releasePointer=()=>{}}={}){
  let enabled=true,destroyed=false,pointer=null,origin=null,last={x:0,y:0};const keys=new Set();
  function emit(x,y){if(x===last.x&&y===last.y)return;last={x,y};onInput(x,y);}
  function show(value,active=false){onVisual({x:value.knobX||0,y:value.knobY||0,active});}
  function reset(){
    const id=pointer;pointer=null;origin=null;keys.clear();
    if(id!==null)try{releasePointer(id);}catch{}
    emit(0,0);show({});
  }
  function move(e){
    if(!enabled||destroyed||pointer!==e.pointerId||!origin)return false;
    const v=normaliseStick(e.clientX-origin.x,e.clientY-origin.y,origin.radius);
    emit(v.x,v.y);show(v,true);return true;
  }
  function keyboard(){let x=0,y=0;for(const key of keys){x+=KEY[key][0];y+=KEY[key][1];}const v=normaliseStick(x,y,1,0);emit(v.x,v.y);show(v,keys.size>0);}
  return {
    pointerDown(e,bounds){
      if(!enabled||destroyed||pointer!==null||e.isPrimary===false||(e.button!=null&&e.button!==0))return false;
      keys.clear();pointer=e.pointerId;origin={x:bounds.left+bounds.width/2,y:bounds.top+bounds.height/2,radius:Math.min(bounds.width,bounds.height)*.34};
      try{capturePointer(pointer);}catch{}
      move(e);return true;
    },
    pointerMove:move,
    pointerUp(e){if(pointer!==e.pointerId)return false;reset();return true;},
    keyDown(e){const key=String(e.key).toLowerCase();if(!enabled||destroyed||pointer!==null||!KEY[key])return false;keys.add(key);keyboard();return true;},
    keyUp(e){const key=String(e.key).toLowerCase();if(!keys.has(key))return false;keys.delete(key);keyboard();return true;},
    reset,
    enable(value){enabled=!!value;if(!enabled)reset();},
    destroy(){reset();destroyed=true;enabled=false;}
  };
}

let mounted=null;
export function bootIsometricMovement(environment){
  mounted?.destroy();
  const getEnvironment=typeof environment==='function'?environment:()=>environment;
  const stage=document.getElementById('stage')||document.getElementById('app');if(!stage)return null;
  const element=document.createElement('div');element.id='isoMovement';element.className='iso-movement';
  const caption=document.createElement('span');caption.className='iso-stick-caption';caption.textContent='Di chuyển';caption.setAttribute('aria-hidden','true');
  const base=document.createElement('div');base.className='iso-stick-base';base.tabIndex=0;base.setAttribute('role','group');base.setAttribute('aria-label','Di chuyển nhân vật: kéo cần tròn, hoặc dùng phím mũi tên và W A S D.');
  const knob=document.createElement('span');knob.className='iso-stick-knob';knob.setAttribute('aria-hidden','true');
  base.append(knob);element.append(caption,base);stage.append(element);
  const media=window.matchMedia('(max-width: 699px), (pointer: coarse)'),listeners=[];
  let destroyed=false,allowed=false,lastMode=null,lastWorld=null;
  const control=createMovementController({
    onInput:(x,y)=>getEnvironment()?.world?.setMovementInput?.(x,y),
    onVisual:({x,y,active})=>{const travel=Math.min(base.getBoundingClientRect().width,base.getBoundingClientRect().height)*.34;knob.style.transform=`translate(-50%, -50%) translate(${x*travel}px, ${y*travel}px)`;base.classList.toggle('is-active',active);},
    capturePointer:id=>base.setPointerCapture(id),releasePointer:id=>base.releasePointerCapture(id)
  });
  control.enable(false);
  function sync(force=false){
    if(destroyed)return;
    const env=getEnvironment(),world=env?.world,root=document.documentElement,mode=world?.mode||root.dataset.sceneMode;
    const next=!!world&&movementAllowed({available:media.matches,mode,hidden:document.hidden,modal:!!document.querySelector('dialog[open], [aria-modal="true"]:not(dialog):not([hidden])'),menu:root.classList.contains('menu-open')||!!document.body?.classList.contains('menu-open'),driving:!!document.querySelector('.dd-stage.dd-expanded')||!!document.fullscreenElement?.closest?.('.dd-stage'),paused:world?.paused,destroyed});
    if(force||mode!==lastMode||world!==lastWorld){control.reset();if(lastWorld&&lastWorld!==world)lastWorld.setMovementInput?.(0,0);}
    if(next!==allowed){control.enable(next);allowed=next;}
    if(element.hidden===next)element.hidden=!next;
    element.dataset.mode=mode||'';lastMode=mode;lastWorld=world;
  }
  function listen(target,type,fn,options){target.addEventListener(type,fn,options);listeners.push(()=>target.removeEventListener(type,fn,options));}
  const handled=fn=>e=>{sync();if(fn(e)){e.preventDefault();e.stopPropagation();}};
  listen(base,'pointerdown',handled(e=>control.pointerDown(e,base.getBoundingClientRect())));
  listen(base,'pointermove',handled(control.pointerMove));
  for(const event of ['pointerup','pointercancel','lostpointercapture'])listen(base,event,handled(control.pointerUp));
  listen(base,'keydown',handled(e=>{if(e.key==='Escape'){control.reset();return true;}return control.keyDown(e);}));
  listen(base,'keyup',handled(control.keyUp));listen(base,'blur',()=>control.reset());
  listen(window,'blur',()=>control.reset());
  for(const event of ['mnl:iso-mode','layoutchange','resize','orientationchange'])listen(window,event,()=>sync(true));
  for(const event of ['visibilitychange','fullscreenchange'])listen(document,event,()=>sync());
  if(media.addEventListener)listen(media,'change',()=>sync());else{const change=()=>sync();media.addListener(change);listeners.push(()=>media.removeListener(change));}
  const observer=new MutationObserver(()=>sync());observer.observe(document.documentElement,{subtree:true,attributes:true,attributeFilter:['open','hidden','class','data-scene-mode']});
  const api={element,update:()=>sync(),reset:()=>control.reset(),destroy(){if(destroyed)return;control.destroy();destroyed=true;observer.disconnect();listeners.forEach(fn=>fn());element.remove();if(mounted===api)mounted=null;}};
  mounted=api;sync();return api;
}
