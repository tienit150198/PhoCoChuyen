import {stylesheet} from '../lazy.js';
import {figure} from './look.js';
import {t} from './i18n.js';
import {getCharacterStamp} from '../isometric/character-art.js';
import {createMovementController} from '../isometric-movement.js';
import {createPlaceLifecycle} from '../pixel/places.js';
import {venueLayout,createVenueWalk,renderVenue,unprojectVenue,projectVenue} from '../scenes/venue-place.js';

let active=null,sequence=0;
/** Free local entry. onInteract's Promise settles when the existing service panel closes. */
export async function openVenue(env,{id,title,layout,eyebrow,badge}={}){
  const room=layout||venueLayout(id),request=++sequence;active?.close();
  await stylesheet('/css/venue-visit.css');if(request!==sequence)return null;
  env.closeSheet?.();
  const previousFocus=document.activeElement,dialog=document.createElement('dialog');
  dialog.className='venue-visit';dialog.setAttribute('aria-label',title||room.title);
  dialog.innerHTML='<header class="venue-header"><div><small>GHÉ CHƠI TỰ DO</small><h2></h2></div><button type="button" class="venue-close" aria-label="Ra phố">✕</button></header><div class="venue-scene"><canvas width="640" height="470" tabindex="0" aria-label="Không gian đi bộ. Chạm sàn để đi, dùng phím mũi tên hoặc W A S D."></canvas><span class="venue-free">Vào cửa tự do</span></div><div class="venue-stations" aria-label="Đi đến các góc trong phòng"></div><footer class="venue-footer"><div class="venue-stick" role="group" aria-label="Cần di chuyển: kéo để đi bộ" tabindex="0"><span></span></div><div class="venue-help"><p class="venue-status" role="status"></p><p class="venue-instructions">Chạm sàn để đi · Kéo cần tròn<br>Mũi tên / WASD · E để tương tác</p></div><button type="button" class="venue-action">Ra phố</button></footer>';
  dialog.querySelector('h2').textContent=title||room.title;
  if(eyebrow)dialog.querySelector('.venue-header small').textContent=eyebrow;
  if(badge)dialog.querySelector('.venue-free').textContent=badge;
  const canvas=dialog.querySelector('canvas'),stick=dialog.querySelector('.venue-stick'),knob=stick.firstElementChild,status=dialog.querySelector('.venue-status'),action=dialog.querySelector('.venue-action'),stations=dialog.querySelector('.venue-stations');
  let dead=false,suspended=false,requestedStation=null,requestedExit=false,control,lifecycle,lastStatus='',lastAction='',api;
  const listeners=[],listen=(target,type,fn,options)=>{target.addEventListener(type,fn,options);listeners.push(()=>target.removeEventListener(type,fn,options));};
  const stop=()=>{requestedStation=null;requestedExit=false;control?.reset();scene.reset();};
  const scene=createVenueWalk(room,{onExit:()=>close(),onInteract:station=>{
    suspend();
    try{Promise.resolve(env.onInteract?.({...station,venueId:id},{resume,close})).then(()=>resume(),error=>{if(!dead){resume();status.textContent=error?.message||'Chưa mở được hoạt động. Hãy thử lại.';}});}
    catch(error){resume();status.textContent=error?.message||'Chưa mở được hoạt động. Hãy thử lại.';}
  }});
  function close(){if(dead)return;dead=true;stop();control?.destroy();lifecycle?.destroy();scene.destroy();listeners.splice(0).forEach(off=>off());dialog.close();dialog.remove();if(active===api)active=null;env.onClose?.();if(previousFocus?.isConnected)previousFocus.focus({preventScroll:true});}
  function suspend(){if(dead||suspended)return;stop();suspended=true;scene.suspend();control?.enable(false);lifecycle?.suspend();dialog.close();env.onSuspend?.();}
  function resume(){if(dead)return;stop();suspended=false;scene.resume();control?.enable(!document.hidden);if(!dialog.open)dialog.showModal();env.onResume?.();if(!document.hidden)lifecycle?.resume();canvas.focus({preventScroll:true});}
  function paint(){
    const state=env.getState?.()||env.api?.state||{},me=figure(state);
    renderVenue(canvas,room,scene.state,{translate:t,time:performance.now(),peers:env.getPeers?.()||[],avatar:(direction,walkFrame)=>getCharacterStamp({look:me.L,gender:me.g,direction,walkFrame,onReady:()=>lifecycle?.wake()})});
    const near=scene.nearby(),exit=Math.hypot(scene.state.x-room.entry.x,scene.state.y-room.entry.y)<38;
    const message=near?near.detail:'Đi dạo trong phòng, hoặc chạm tên một góc để đi tới.';
    if(message!==lastStatus){status.textContent=message;lastStatus=message;}
    const label=near?near.label:exit?'Ra phố':'Đi tới một góc';if(label!==lastAction){action.textContent=label;lastAction=label;}action.disabled=!near&&!exit;
    for(const button of stations.children)button.classList.toggle('is-near',button.dataset.station===near?.id);
  }
  const go=station=>{stop();if(scene.goTo(station)){requestedStation=station.id;lifecycle.wake();status.textContent=`Đang đi tới ${station.label.toLowerCase()}…`;}};
  function refreshLayout(){stop();stations.replaceChildren();for(const station of room.stations){const button=document.createElement('button');button.type='button';button.dataset.station=station.id;button.textContent=station.label;button.onclick=()=>go(station);stations.append(button);}lifecycle?.wake();}
  refreshLayout();
  control=createMovementController({onInput:(x,y)=>{
    requestedStation=null;requestedExit=false;
    // Screen-space stick directions are inverse-projected into the isometric floor.
    const wx=x/.67+y/.38,wy=y/.38-x/.67,n=Math.hypot(wx,wy),m=Math.min(1,Math.hypot(x,y));scene.setInput(n?wx/n*m:0,n?wy/n*m:0);lifecycle?.wake();
  },onVisual:({x,y})=>{knob.style.transform=`translate(-50%,-50%) translate(${x*27}px,${y*27}px)`;},capturePointer:pointer=>stick.setPointerCapture(pointer),releasePointer:pointer=>stick.releasePointerCapture(pointer)});
  lifecycle=createPlaceLifecycle({reset:()=>{control.reset();scene.reset();},needsFrame:scene.needsFrame,render:paint,step:dt=>{
    scene.step(dt);env.onMove?.(scene.state);
    if(requestedStation){const station=room.stations.find(s=>s.id===requestedStation);if(Math.hypot(station.x-scene.state.x,station.y-scene.state.y)<12){requestedStation=null;scene.interact(station.id);}}
    if(requestedExit&&Math.hypot(scene.state.x-room.entry.x,scene.state.y-room.entry.y)<12){requestedExit=false;scene.exit();}
  }});
  const handled=fn=>event=>{if(dead||suspended||event.target?.closest?.('input,textarea,select'))return;if(fn(event)){event.preventDefault();event.stopImmediatePropagation();}};
  listen(stick,'pointerdown',handled(e=>control.pointerDown(e,stick.getBoundingClientRect())));
  listen(stick,'pointermove',handled(control.pointerMove));for(const event of ['pointerup','pointercancel','lostpointercapture'])listen(stick,event,handled(control.pointerUp));
  listen(window,'keydown',handled(e=>{if(e.key==='Escape'){close();return true;}if(e.key.toLowerCase()==='e'||e.key===' '&&e.target===canvas){if(!scene.interact())scene.exit();return true;}return control.keyDown(e);}),true);
  listen(window,'keyup',handled(control.keyUp),true);
  listen(window,'blur',()=>{stop();lifecycle.suspend();});listen(window,'focus',()=>{if(!dead&&!suspended&&!document.hidden)lifecycle.resume();});
  listen(document,'visibilitychange',()=>{stop();control.enable(!document.hidden&&!suspended);if(document.hidden)lifecycle.suspend();else if(!suspended)lifecycle.resume();});
  listen(dialog,'cancel',e=>{e.preventDefault();close();});listen(dialog.querySelector('.venue-close'),'click',close);
  listen(action,'click',()=>{if(!scene.interact())scene.exit();});
  listen(canvas,'pointerdown',e=>{if(dead||suspended||e.button!==0)return;e.preventDefault();e.stopPropagation();canvas.focus({preventScroll:true});const bounds=canvas.getBoundingClientRect(),screen={x:(e.clientX-bounds.left)/bounds.width*640,y:(e.clientY-bounds.top)/bounds.height*470};
    const station=room.stations.find(s=>{const p=projectVenue(s);return Math.abs(screen.x-p.x)<52&&Math.abs(screen.y-p.y-12)<25;});if(station){go(station);return;}
    stop();const point=unprojectVenue(screen);requestedExit=Math.hypot(point.x-room.entry.x,point.y-room.entry.y)<25;scene.goTo(requestedExit?room.entry:point);lifecycle.wake();
  });
  const dpr=Math.min(2,window.devicePixelRatio||1);canvas.width=Math.round(640*dpr);canvas.height=Math.round(470*dpr);canvas.getContext('2d').scale(dpr,dpr);
  api={element:dialog,scene,refreshLayout,wake:()=>lifecycle?.wake(),resume,suspend,close,get suspended(){return suspended;},get destroyed(){return dead;}};dialog.venueVisit=api;active=api;
  document.body.append(dialog);resume();return api;
}
