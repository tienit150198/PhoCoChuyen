/** Presentation coordinates only. All saves, prices and permissions remain in reno/game.deco. */
export const U=20;
export const clamp=(n,a,b)=>Math.max(a,Math.min(b,Number(n)||0));
export const dimensions=room=>({width:room.cols,depth:room.frows,height:Math.max(1.6,room.wrows*1.1+.35)});
export const surfaceHeight=it=>it.ledge ? .1 : Math.max(.12,(it.surface||22)/32);
export function hostOf(room,id,all){
  if(!id)return null;
  if(id[0]==='#'){
    const f=(room.fix||[]).find(x=>x.t===id.slice(1)&&x.surface);
    return f?{id,it:{...f,spot:f.layer,surface:f.surface,ledge:f.layer==='wall'},q:{r:room.id,x:f.x*U,y:f.y*U,f:0}}:null;
  }
  return all.find(o=>o.id===id)||null;
}
export function placement(room,o,all=[],depth=0){
  const {width,depth:d,height}=dimensions(room),{it,q}=o,w=it.w||1,h=it.h||1;
  const host=depth<3?hostOf(room,q.on,all):null;
  if(host){
    const p=placement(room,host,all,depth+1),hw=host.it.w;
    const offset=q.x/U+w/2-hw/2;
    return {x:p.x+(host.q.f?-offset:offset),y:p.y+surfaceHeight(host.it),z:host.it.spot==='wall'?p.z+.28:p.z-host.it.h/2+q.y/U+h/2};
  }
  return {x:q.x/U+w/2-width/2,y:it.spot==='wall'?height-(q.y/U+h/2)*1.1:it.spot==='rug'?.018:0,z:it.spot==='wall'?-d/2+.1:q.y/U+h/2-d/2};
}
export function hitPlacement(room,it,hit,{host=null,all=[],f=0}={}){
  const {width,depth,height}=dimensions(room),w=it.w||1,h=it.h||1;
  let x,y,on;
  if(host&&it.spot==='top'&&(host.it.surface||host.it.ledge)){
    const p=placement(room,host,all),off=(hit.x-p.x)*(host.q.f?-1:1);
    x=clamp(Math.round((off+host.it.w/2-w/2)*U),0,Math.max(0,(host.it.w-w)*U));
    y=host.it.spot==='wall'?0:clamp(Math.round((hit.z-p.z+host.it.h/2-h/2)*U),0,Math.max(0,(host.it.h-h)*U));on=host.id;
  }else{
    x=clamp(Math.round((hit.x+width/2-w/2)*U),0,Math.max(0,(width-w)*U));
    y=it.spot==='wall'?(height-hit.y)/1.1-h/2:hit.z+depth/2-h/2;
    y=clamp(Math.round(y*U),0,Math.max(0,((it.spot==='wall'?room.wrows:room.frows)-h)*U));
  }
  return {r:room.id,x,y,f,...(on?{on}:{})};
}
export function editIntent(state,item,hit){
  if(state.busy)return null;
  if(!state.edit)return {type:'walk',uid:item?.id||'',point:hit};
  if(state.remote&&!state.coop)return null;
  if(state.held)return {type:'place',point:hit};
  if(item&&!item.mate)return {type:'select',uid:item.id};
  return null;
}
export const boundedActors=(people=[],children=[],pets=[])=>[...people.slice(0,12),...children.slice(0,8),...pets.slice(0,8)];

/** Resource ownership is explicit, including shared geometries/materials and late SVG loads. */
export function disposeTree(root){
  const resources=new Set();
  root.traverse(o=>{if(o.geometry)resources.add(o.geometry);for(const m of Array.isArray(o.material)?o.material:o.material?[o.material]:[]){resources.add(m);for(const v of Object.values(m))if(v?.isTexture)resources.add(v);}});
  for(const resource of resources)resource.dispose();
  root.clear();
}
