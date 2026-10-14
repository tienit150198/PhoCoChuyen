/** Classic players visit the same server-authoritative island without changing
 * their renderer preference or replacing their current workplace. */
export function createSharedIslandSession(env,{view,loadRuntime,onClose=()=>{}}){
  let world=null,presence=null,treasure=null,input=null,closed=false,started=false,startPromise=null,cancelReady=null;
  let previousPause=false,listTimer=null;
  const current=()=>({...env,world,toast:text=>view.notice(text)});
  /** F#381 (a blind player): every chest as a list row, nearest first, with a button that walks there and picks it.
   * Same route and claim as a tap on the chest; results are read out by the notice live region. */
  const chestRows=()=>{
    const at=world?.getPresence?.(),counts=new Map((world?.treasure||[]).map(c=>[c.id,c.count||1]));
    return (world?.hotspots||[]).filter(h=>typeof h?.id==='string'&&h.id.startsWith('treasure:')&&Number.isFinite(h.x)&&Number.isFinite(h.y))
      .map(h=>({id:h.id.slice(9),count:counts.get(h.id.slice(9))||1,steps:at?Math.max(0,Math.round(Math.hypot(h.x-at.x,h.y-at.y))):null}))
      .sort((a,b)=>(a.steps??0)-(b.steps??0)||a.id.localeCompare(b.id));
  };
  const refreshList=()=>{if(world&&!closed)view.chests?.(chestRows());};
  function walkTo(id){
    const hid='treasure:'+id;
    if(!world||closed)return;
    if(!(world.hotspots||[]).some(h=>h.id===hid)){view.notice('Rương này đã được nhặt. Danh sách đã cập nhật.');refreshList();return;}
    const row=chestRows().find(r=>r.id===id);
    view.notice(row?.steps?`Đang đi tới rương, khoảng ${row.steps} bước…`:'Đang nhặt rương…');
    world.go(hid,()=>interact(hid));
  }
  function interact(id){if(id.startsWith('treasure:'))void treasure?.claim(id.slice(9));}
  const update=()=>{if(env.api.state?.jail){close();return;}world?.update(env.api.state,env.api.content);presence?.sync();};
  function close(){
    if(closed)return;closed=true;clearInterval(listTimer);cancelReady?.();input?.destroy();treasure?.stop();presence?.stop();world?.destroy();world=null;
    env.api.removeEventListener?.('state',update);view.destroy();
    if(started){env.world.paused=previousPause;env.world.wake?.();}onClose();
  }
  view.onClose(close);
  view.onCamera(action=>{if(action==='me')world?.recenter();else if(action==='in'||action==='out')world?.zoomBy(action==='in'?1.25:1/1.25);});
  async function start(){
    if(startPromise)return startPromise;
    if(closed||env.api.state?.jail){close();return;}
    started=true;env.closeSheet?.();previousPause=env.world.paused;env.world.paused=true;view.open();env.api.addEventListener?.('state',update);
    startPromise=(async()=>{
      try{
        const runtime=await loadRuntime();if(closed)return;
        world=new runtime.World(view.canvas,interact);
        let timer;const ready=await new Promise((resolve,reject)=>{
          cancelReady=()=>resolve(false);timer=setTimeout(()=>reject(new Error('Tải đảo quá lâu. Thử mở lại nhé.')),20000);
          world.ready.then(()=>resolve(true),reject);
        }).finally(()=>{clearTimeout(timer);cancelReady=null;});
        if(!ready||closed)return;
        world.update(env.api.state,env.api.content);world.resize();
        input=runtime.attachInput(view,world);
        presence=runtime.createPresence(current,{status:text=>view.status(text)}).start();
        treasure=runtime.createTreasure(current).start();view.ready();
        if(typeof world.go==='function'&&view.chests){view.onChest?.(walkTo);refreshList();listTimer=setInterval(refreshList,1000);}
      }catch(error){if(!closed){env.toast?.(error.message||'Chưa tải được đảo. Thử lại nhé.',true);close();}}
    })();
    return startPromise;
  }
  return {start,close};
}

const escapeAttr=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/** Exported for tests only. */
export function createView(){
  const previousFocus=document.activeElement,dialog=document.createElement('dialog');dialog.className='shared-island';dialog.setAttribute('data-shared-island','');
  dialog.setAttribute('aria-labelledby','sharedIslandTitle');
  dialog.innerHTML=`<div class="shared-island-layout"><header><div><h2 id="sharedIslandTitle">Đảo chung</h2><p data-island-status role="status">Đang tải đảo…</p></div><div class="shared-island-actions"><button type="button" data-island-list aria-expanded="false" aria-controls="sharedIslandList">📋 Danh sách rương</button><button type="button" data-island-close aria-label="Trở lại giao diện cũ">← Trở về</button></div></header>
    <section class="shared-island-list" id="sharedIslandList" aria-labelledby="sharedIslandListTitle" hidden><h3 id="sharedIslandListTitle" tabindex="-1">Rương trên đảo</h3><p data-island-list-empty>Đang tìm rương…</p><ul data-island-chests></ul></section>
    <div class="shared-island-stage"><canvas tabindex="0" aria-label="Đảo chung: chạm để đi, kéo để xem bản đồ; dùng mũi tên hoặc W A S D để di chuyển."></canvas>
      <p class="shared-island-loading" role="status">Đang dựng đảo…</p>
      <div class="shared-island-camera" role="group" aria-label="Điều khiển bản đồ"><button type="button" data-island-camera="out" aria-label="Thu nhỏ">−</button><button type="button" data-island-camera="in" aria-label="Phóng to">+</button><button type="button" data-island-camera="me" aria-label="Về nhân vật">◎</button></div>
      <div class="shared-island-stick" tabindex="0" role="group" aria-label="Kéo cần tròn để di chuyển"><span></span></div>
      <p class="shared-island-notice" role="status" aria-live="polite" hidden></p>
    </div><footer>Chạm rương để đi tới và nhặt · Mỗi rương 10.000 xu · Dùng trình đọc màn hình: mở 📋 Danh sách rương</footer></div>`;
  const canvas=dialog.querySelector('canvas'),stick=dialog.querySelector('.shared-island-stick'),knob=stick.firstElementChild,listeners=[];
  const listen=(target,name,fn,options)=>{target.addEventListener(name,fn,options);listeners.push(()=>target.removeEventListener(name,fn,options));};
  let close=()=>{},camera=()=>{},pick=()=>{},shown='';
  const panel=dialog.querySelector('.shared-island-list'),toggle=dialog.querySelector('[data-island-list]'),list=panel.querySelector('ul'),empty=panel.querySelector('[data-island-list-empty]');
  const remember=on=>{try{localStorage.setItem('mnl.islandList',on?'1':'0');}catch{/* private mode */}};
  const setList=(on,focus=true)=>{panel.hidden=!on;toggle.setAttribute('aria-expanded',String(on));toggle.textContent=on?'📋 Ẩn danh sách':'📋 Danh sách rương';if(on&&focus)panel.querySelector('h3').focus({preventScroll:true});};
  try{if(localStorage.getItem('mnl.islandList')==='1')setList(true,false);}catch{/* private mode */}
  listen(dialog,'cancel',event=>{event.preventDefault();close();});listen(dialog,'close',()=>close());
  listen(dialog,'click',event=>{const button=event.target.closest('button');if(!button)return;if(button.hasAttribute('data-island-close'))close();else if(button.hasAttribute('data-island-list')){const on=panel.hidden;setList(on);remember(on);}
    else if(button.dataset.islandChest)pick(button.dataset.islandChest);else if(button.dataset.islandCamera)camera(button.dataset.islandCamera);});
  const where=r=>(r.count>1?`${r.count} rương chồng · `:'')+(r.steps==null?'trên đảo':r.steps<=1?'ngay cạnh bạn':`cách khoảng ${r.steps} bước`);
  listen(window,'pagehide',()=>close());
  return {canvas,stick,knob,dialog,listen,
    onClose:fn=>{close=fn;},onCamera:fn=>{camera=fn;},onChest:fn=>{pick=fn;},
    /** Rows rebuild only when the set of chests changes, so a focused button survives distance updates. */
    chests(rows){
      const ids=rows.map(r=>r.id).join('|');
      empty.textContent=rows.length?`${rows.length} rương · gần nhất ở đầu danh sách.`:'Chưa có rương. Rương ra theo đợt; danh sách tự cập nhật.';
      if(ids!==shown){
        const had=dialog.contains(document.activeElement)&&document.activeElement?.dataset?.islandChest;shown=ids;
        list.innerHTML=rows.map((r,i)=>`<li data-chest-row="${escapeAttr(r.id)}"><span>Rương ${i+1} · <span data-where>${where(r)}</span></span><button type="button" data-island-chest="${escapeAttr(r.id)}" aria-label="Đi tới và nhặt rương ${i+1}">Đi tới và nhặt</button></li>`).join('');
        if(had){const again=[...list.querySelectorAll('[data-island-chest]')].find(b=>b.dataset.islandChest===had);(again||panel.querySelector('h3')).focus({preventScroll:true});}
      }else for(const r of rows){const node=[...list.querySelectorAll('[data-chest-row]')].find(li=>li.dataset.chestRow===r.id)?.querySelector('[data-where]');if(node&&node.textContent!==where(r))node.textContent=where(r);}
    },
    open(){document.body.append(dialog);dialog.showModal();},
    ready(){dialog.querySelector('.shared-island-loading').hidden=true;(panel.hidden?canvas:panel.querySelector('h3')).focus({preventScroll:true});},
    status:text=>{dialog.querySelector('[data-island-status]').textContent=text;},
    notice:text=>{const node=dialog.querySelector('.shared-island-notice');node.textContent=text;node.hidden=false;},
    destroy(){listeners.splice(0).forEach(off=>off());if(dialog.open)dialog.close();dialog.remove();if(previousFocus?.isConnected)previousFocus.focus({preventScroll:true});}
  };
}

function attachInput(view,world,createMovementController){
  const {stick,knob}=view;
  const control=createMovementController({onInput:(x,y)=>world.setMovementInput(x,y),
    onVisual:({x,y})=>{knob.style.transform=`translate(-50%,-50%) translate(${x*34}px,${y*34}px)`;},
    capturePointer:id=>stick.setPointerCapture(id),releasePointer:id=>stick.releasePointerCapture(id)});
  const handle=fn=>event=>{if(fn(event)){event.preventDefault();event.stopPropagation();}};
  view.listen(stick,'pointerdown',handle(event=>control.pointerDown(event,stick.getBoundingClientRect())));
  view.listen(stick,'pointermove',handle(control.pointerMove));
  for(const name of ['pointerup','pointercancel','lostpointercapture'])view.listen(stick,name,handle(control.pointerUp));
  view.listen(stick,'keydown',handle(control.keyDown));view.listen(stick,'keyup',handle(control.keyUp));
  view.listen(stick,'blur',control.reset);view.listen(window,'blur',control.reset);view.listen(document,'visibilitychange',control.reset);
  // Stop a held thumb when another modal covers this one; closing that modal
  // requires a fresh gesture instead of restarting stale movement.
  const observer=new MutationObserver(()=>{if(document.querySelector('dialog[open]:not([data-shared-island])'))control.reset();});
  observer.observe(document.body,{subtree:true,attributes:true,attributeFilter:['open']});
  return {destroy(){observer.disconnect();control.destroy();}};
}

let active=null;
export function openSharedIsland(env){
  if(active)return active;
  if(env.api.state?.jail)return env.act?.('jail');
  // Dynamic imports keep Phaser out of the classic first screen.
  active=(async()=>{
    try{
      const {stylesheet}=await import('./lazy.js');await stylesheet('/css/shared-island.css');
      if(env.api.state?.jail){active=null;return env.act?.('jail');}
      const session=createSharedIslandSession(env,{view:createView(),onClose:()=>{active=null;},loadRuntime:async()=>{
        const [engine,town,treasure,movement,network]=await Promise.all([import('./isometric/phaser-world.js'),import('./isometric-town.js'),import('./isometric/treasure.js'),import('./isometric-movement.js'),import('./v4/live.js')]);
        env.bootLive?.(network);
        return {World:engine.PhaserWorld,createPresence:town.createTownPresence,createTreasure:getEnv=>treasure.createTreasureController(getEnv,{socket:network.live}),attachInput:(view,world)=>attachInput(view,world,movement.createMovementController)};
      }});
      await session.start();return session;
    }catch(error){active=null;env.toast?.(error.message||'Chưa mở được đảo. Thử lại nhé.',true);}
  })();return active;
}
