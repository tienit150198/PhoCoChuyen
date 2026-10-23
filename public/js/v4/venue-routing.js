/** Physical entry is free; existing panels remain responsible for purchases. */
export const venueForSpend=tab=>({quan:'cafe',spa:'spa',rap:'cinema',chua:'temple'}[tab]||null);

export async function waitForPanels(open,scope=globalThis){
  const doc=scope.document,before=new Set(doc.querySelectorAll('dialog[open]'));
  await open();
  const active=()=>[...doc.querySelectorAll('dialog[open]')].some(d=>!before.has(d));
  if(!active())return;
  await new Promise(resolve=>{
    const observer=new scope.MutationObserver(()=>{if(!active()){observer.disconnect();resolve();}});
    observer.observe(doc.body,{subtree:true,attributes:true,attributeFilter:['open'],childList:true});
    if(!active()){observer.disconnect();resolve();}
  });
}

export async function visitVenue(env,id,openPanel){
  const {openVenue}=await import('./venue-visit.js');
  return openVenue({...env,onInteract:station=>waitForPanels(()=>openPanel(station))},{id});
}

export async function visitTemple(env){
  const {openChua}=await import('./chua-visit.js');
  return openChua({...env,onDonate:()=>waitForPanels(async()=>{
    const {openSpend}=await import('./spend.js');
    await openSpend({...env,venueId:'temple'},'chua');
  })});
}

export async function visitLeisure(env,kind){
  if(!['fishing','boat','pool'].includes(kind))return;
  if(kind==='fishing'&&env.api?.state?.journey?.story&&env.api?.content?.journey?.fish){   // 🎣 the lake with rods, stalls and Sổ cá (v4/fishing.js)
    env.closeSheet?.();return (await import('./fishing.js')).openFishing(env,{});
  }
  const [{openPixelPlace},{loadLeisureArt}]=await Promise.all([import('../pixel/places.js'),import('../isometric/leisure-art.js')]);
  const leisureArt=await loadLeisureArt(kind);
  if(env.api?.state?.jail){await env.act('jail');return;}
  env.closeSheet();return openPixelPlace(kind,{...env,leisureArt});
}
