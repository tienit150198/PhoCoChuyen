/** Inside / outside: the areas of a workplace (BobaWorld calls these; render-only, nothing goes to the server).
 *
 * A scene kind may list `areas` (an array, or `(w)=>array` when its careers differ). One area carries
 * `main:true`: that is the scene's own room, plan and props (the shop floor, the apron…). The others are
 * interiors, each a small scene of its own:
 *   {id, name, icon,
 *    plan:{land,port}      the PLAN schema of scenes/shop.js; every key optional except floor, home, kx, ky,
 *                          blocks and spots. `labels` {spot: words} renames a hotspot here; `cat` [x,y] puts
 *                          Mướp in the room (and the `pet` spot), customers ×n / event the task people,
 *    room(w,p), props(w,p) drawing (props → [[depth, draw]] like a scene's),
 *    people                true: the people of the tasks stand here (customers / event), default: not,
 *    outdoor               true: the time-of-day lamp posts stand here (v4/dayclock.js),
 *    looks {key: w=>line}  `look:key` spots: the player walks there and says the line}
 * Plans (main or not) join areas with `go:<area id>` spots: [hit, range, approach] like any spot, at a door.
 * Optional `areaFor(w)` on the scene: where the work in hand happens, {key, area, spot?}. When the key
 * changes (another task, the next step of a flight, the shift opens or ends) the player is taken there;
 * otherwise they may look around freely. A live happening (v4/scene-events.js) always plays on the main area.
 * The area chips over the stage (#sceneAreas) do the same as walking through a door. */
import {t as tr} from '../v4/i18n.js';

const FADE=.32;
const STAND=['shelf','evidence','workbench','counter','warehouse','board','finance','property','security','door','pet'];

/** The scene's areas for this career ([] when it has none), cached per career and scene kind. */
export function areaList(w){
  const s=w.scene(),key=w.career+'|'+s.id;
  if(w._areas?.key===key)return w._areas.list;
  let list=typeof s.areas==='function'?s.areas(w):s.areas;
  list=Array.isArray(list)&&list.length>1&&list.some(a=>a.main)?list:[];
  w._areas={key,list};return list;
}
const mainOf=list=>list.find(a=>a.main);
/** The area the player is in (null: the scene has none, or a career preview is being drawn). */
export function areaOf(w){
  if(w.previewRendering)return null;
  const list=areaList(w);if(!list.length)return null;
  const id=w.areaAt?.[w.career];
  return list.find(a=>a.id===id)||mainOf(list);
}
/** Is the player on the scene's own (main) floor? */
export const onMain=w=>{const a=areaOf(w);return !a||!!a.main;};
/** The plan in use: the area's, or the scene's own. */
export function planOf(w,scene){const a=areaOf(w),src=a&&!a.main?a.plan:scene.plan;return w.isPortrait()?src.port:src.land;}

/** Hotspots of the plan: the standard spots it has, then its doors and things to look at. */
export function areaSpots(w,pl,add,words){
  const area=areaOf(w),list=areaList(w);
  for(const key of Object.keys(pl.spots||{})){
    const [at,range,go]=pl.spots[key];
    if(key.startsWith('go:')){const to=list.find(a=>a.id===key.slice(3));if(to)add(key,to.icon+' '+to.name,at,range,go);}
    else if(key.startsWith('look:'))add(key,pl.labels?.[key]||'',at,range,go);
    else if(area&&!area.main&&STAND.includes(key)&&!(key==='pet'&&!pl.cat))add(key==='finance'||key==='property'||key==='security'?'ops:'+key:key,pl.labels?.[key]||words[key]||'',at,range,go);
  }
}

/** Walk through a door or look at something; true when the hotspot was an area one. */
export function areaTap(w,h){
  if(h.id.startsWith('go:')){w.ping(h.point.x,h.point.y,'#8fb7d8');w.approach(h,()=>enterArea(w,h.id.slice(3)));return true;}
  if(h.id.startsWith('look:')){const line=areaOf(w)?.looks?.[h.id.slice(5)]?.(w);w.approach(h,()=>{if(line)w.say(line);});return true;}
  return false;
}

/** Step into another area: the player comes in through the door back to where they were (or stands at the
 * area's home), takes a step in, and the stage fades through. `spot`: walk on to that hotspot (auto moves). */
export function enterArea(w,id,{spot=null}={}){
  const list=areaList(w),to=list.find(a=>a.id===id);if(!to)return;
  const from=areaOf(w);w.areaAt??={};
  const p=w.player;p.path=[];p.goal=null;w.pending=null;w.hover=null;
  if(from?.id!==to.id){
    w.areaAt[w.career]=to.id;
    const pl=w.plan(),door=pl.spots?.['go:'+from?.id],at=door?door[2][0]:pl.home,t=w.unproject(at[0],at[1]);
    p.x=t.x;p.y=t.y;
    if(!w.reduced)w.fadeAt=w.time;
    w.speech=null;w.setupObjects();
    if(!spot&&door){const h=w.plan().home,ht=w.unproject(h[0],h[1]);w.walkTo(ht.x,ht.y,null,{marker:false});}
  }
  if(spot)w.go(spot,()=>{});
  w.wake(true);
}

/** Take the player to where the work in hand happens, once per change of the scene's `areaFor` key. */
export function autoArea(w){
  const list=areaList(w);if(!list.length||w.previewRendering||!w.c)return;
  const main=mainOf(list);
  if(w.fx?.ev){if(areaOf(w)!==main)enterArea(w,main.id);return;}
  const want=w.scene().areaFor?.(w)||null,key=want?.key??null;
  w.areaKey??={};
  if(w.areaKey[w.career]===key)return;
  w.areaKey[w.career]=key;
  if(want?.area&&list.some(a=>a.id===want.area)&&want.area!==areaOf(w).id)enterArea(w,want.area,{spot:want.spot||null});
}
/** The area of the work in hand (for the chips' dot and the door marker), or null. */
function taskArea(w){const want=w.c?.open?w.scene().areaFor?.(w):null;return want?.area||null;}

/** The marker spot when the work's station is in another area: the door that leads there. */
export function focusDoor(w,focus){
  if(!focus||w.hotspots.some(h=>h.id===focus))return focus;
  const there=taskArea(w);if(there&&w.hotspots.some(h=>h.id==='go:'+there))return 'go:'+there;
  return null;
}

/** Doors carry a small sign with the place they lead to (always shown: that is how the player finds them). */
export function doorTags(w,p,R,T,fit){
  const c=w.ctx,port=w.isPortrait(),size=port?17:12,hgt=port?30:24,fx=port?[28,672]:[70,1130];
  for(const h of w.hotspots){if(!h.id.startsWith('go:'))continue;
    const to=areaList(w).find(a=>a.id===h.id.slice(3)),pt=w.project(h.x,h.y,h.z),label=to?`${to.icon} ${tr(to.name)} ›`:h.label+' ›',wd=Math.min(port?250:200,Math.max(70,label.length*(port?9.5:7)+24));
    pt.x=Math.max(fx[0]+wd/2,Math.min(fx[1]-wd/2,pt.x));   // inside the frame, never cut by the screen edge
    const hover=w.hover?.id===h.id;
    R(c,pt.x-wd/2,pt.y-hgt/2,wd,hgt,hover?p.dark:'#fffaf0ee',hgt/2,hover?p.dark:'#c9b49a',1.5);
    T(c,label,pt.x,pt.y+1,fit(c,label,wd-14,size),hover?'#fffaf2':p.dark,800);}
}

/** The fade between two areas (scene space already reset by the caller). */
export function areaFade(w){
  if(w.fadeAt==null)return;
  const k=(w.time-w.fadeAt)/FADE;if(k>=1||w.reduced){w.fadeAt=null;return;}
  const c=w.ctx;c.save();c.setTransform(w.dpr,0,0,w.dpr,0,0);c.globalAlpha=Math.max(0,1-k)*.85;c.fillStyle='#fff6ed';c.fillRect(0,0,w.width,w.height);c.restore();
}
export const fading=w=>w.fadeAt!=null&&!w.reduced;

/* ------------------------------------------------------------ the chips over the stage */
const esc=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
/** #sceneAreas: one chip per area (the current one named, the work's one dotted). Placed beside the title
 * card when the row has room, else under it; returns true when its height changed (the phone layout uses it). */
export function areaBar(w){
  const doc=globalThis.document,bar=doc?.getElementById?.('sceneAreas');if(!bar||w.previewRendering)return false;
  const list=areaList(w),cur=areaOf(w),work=taskArea(w);
  const key=list.length?[w.career,cur.id,work,list.map(a=>a.id+a.name).join()].join('|'):'';
  const was=bar.hidden?0:bar.offsetHeight;
  if(bar.dataset.key!==key){
    bar.dataset.key=key;bar.hidden=!list.length;
    bar.innerHTML=list.map(a=>{const on=a.id===cur.id,dot=a.id===work&&!on;
      return `<button type="button" class="sa-chip${on?' on':''}" data-area="${esc(a.id)}" aria-pressed="${on}" title="${esc(a.name)}" aria-label="${esc(a.name)}${dot?' · việc đang ở đây':''}"><span aria-hidden="true">${esc(a.icon)}</span>${on?`<b>${esc(a.name)}</b>`:''}${dot?'<i class="sa-dot" aria-hidden="true"></i>':''}</button>`;}).join('');
    if(!bar.dataset.wired){bar.dataset.wired='1';bar.addEventListener('click',e=>{const b=e.target.closest('[data-area]');if(b)goArea(w,b.dataset.area);});}
  }
  placeBar(w,bar);
  return (bar.hidden?0:bar.offsetHeight)!==was;
}
/** Beside the title card if the row is free up to the right-hand chips, else under it. */
function placeBar(w,bar){
  if(bar.hidden)return;
  const stage=bar.parentElement?.getBoundingClientRect?.(),head=bar.parentElement?.querySelector?.('.scene-heading')?.getBoundingClientRect?.();if(!stage)return;
  const blocks=[...bar.parentElement.querySelectorAll('.jr-hud:not([hidden]),.live-fab:not([hidden])')].map(e=>e.getBoundingClientRect()).filter(r=>r.width);
  const hx=head&&head.width?head.right-stage.left:0,hy=head&&head.width?head.top-stage.top:12,hb=head&&head.width?head.bottom-stage.top:12;
  bar.style.maxWidth='none';const need=bar.scrollWidth;
  const rightAt=(top,bottom)=>Math.min(stage.width-10,...blocks.filter(r=>r.bottom-stage.top>top&&r.top-stage.top<bottom).map(r=>r.left-stage.left-8));
  const room=rightAt(hy,hb)-(hx+10);
  if(hx&&need<=room){Object.assign(bar.style,{left:`${hx+10}px`,top:`${hy}px`,maxWidth:`${room}px`});return;}
  const top=hb+6,left=head&&head.width?head.left-stage.left:10;
  Object.assign(bar.style,{left:`${left}px`,top:`${top}px`,maxWidth:`${Math.max(120,rightAt(top,top+40)-left)}px`});
}
/** A chip: walk out through the door to it when there is one here, else step straight in. */
export function goArea(w,id){
  if(w.paused)return;w.poke?.(true);
  if(areaOf(w)?.id===id)return;
  const door=w.hotspots.find(h=>h.id==='go:'+id);
  if(door&&!w.reduced){w.approach(door,()=>enterArea(w,id));w.wake(true);}else enterArea(w,id);
}
