/** Art-space navigation. Public poses and round proofs retain the server's 320×200 coordinates. */
const LAKE={width:320,height:200,
  water:[[46,31],[81,17],[218,17],[273,42],[291,69],[292,128],[278,149],[218,154],[117,152],[52,151],[28,132],[27,69]],
  pier:{left:80,right:106,top:100,bottom:165},footprint:{x:24,top:18,bottom:18},
  start:[93,180],dock:[96,142],entry:[104,150]};
const POOL={width:640,height:400,
  water:[[100,109.34],[541.33,109.34],[580,283.33],[60,283.33]],
  footprint:{x:16,top:24,bottom:12},start:[91.5,176],dock:[91.5,151],entry:[86,142]};
const FISHING={...LAKE,dock:[93,112]};
export const placeGeometry=kind=>kind==='pool'?POOL:kind==='fishing'?FISHING:LAKE;

export function placeWorldPoint(kind,{x,y},water=false){
  if(kind==='pool')return {x:2*(x+(water?5.5:0)),y:2*(water?.8*y+16.4:y)};
  return water?{x:132+.75*(x-104),y:130+.8*(y-150)}:{x,y};
}
export function placeNetworkPoint(kind,{x,y},water=false){
  if(kind==='pool')return {x:x/2-(water?5.5:0),y:water?(y/2-16.4)/.8:y/2};
  return water?{x:104+(x-132)/.75,y:150+(y-130)/.8}:{x,y};
}

function inside(polygon,x,y){
  let hit=false;
  for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
    const a=polygon[i],b=polygon[j];
    if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])hit=!hit;
  }
  return hit;
}

/** The footprint covers the hull in every heading, so turning beside a post is safe too. */
export function navigablePlaceWorld(kind,x,y,water=false){
  const g=placeGeometry(kind);
  if(!Number.isFinite(x)||!Number.isFinite(y))return false;
  if(!water){
    if(kind==='pool')return x>=52&&x<=588&&y>=299&&y<=380;
    return x>=12&&x<=308&&y>=166&&y<=190||x>=85&&x<=101&&y>=108&&y<=166;
  }
  const f=g.footprint;
  for(const dx of [-f.x,f.x])for(const dy of [-f.top,f.bottom])if(!inside(g.water,x+dx,y+dy))return false;
  const p=g.pier;
  return !p||x+f.x<=p.left||x-f.x>=p.right||y+f.bottom<=p.top||y-f.top>=p.bottom;
}

export function walkablePlace(kind,x,y,inWater=false){
  if(!Number.isFinite(x)||!Number.isFinite(y)||x<0||x>320||y<0||y>200)return false;
  const p=placeWorldPoint(kind,{x,y},inWater);return navigablePlaceWorld(kind,p.x,p.y,inWater);
}

/** Sweep in ≤1-art-unit increments; diagonal moves and delayed frames cannot jump a pier. */
export function moveInPlace(kind,point,dx,dy,water=false){
  const p=placeWorldPoint(kind,point,water),steps=Math.max(1,Math.ceil(Math.hypot(dx,dy))),sx=dx/steps,sy=dy/steps;
  const valid=(x,y)=>{const n=placeNetworkPoint(kind,{x,y},water);return walkablePlace(kind,n.x,n.y,water);};
  for(let i=0;i<steps;i++){
    if(valid(p.x+sx,p.y+sy)){p.x+=sx;p.y+=sy;}
    else{if(valid(p.x+sx,p.y))p.x+=sx;if(valid(p.x,p.y+sy))p.y+=sy;}
  }
  return placeNetworkPoint(kind,p,water);
}
