import {findRoute,isWalkable,lineClear} from './model';
import type {Navigation,Point} from './model';

export type StreetTrail={district:string;width:number;points:Point[];sampled?:boolean};
export type StreetDoor={id:string;district:string;at:Point};
export type DoorPath={id:string;district:string;points:Point[]};
export type StreetSample=Point&{radius:number};

/** The renderer and collision regression use the same bounded Catmull-Rom
 * centerline. Authored control points must leave enough space for its overshoot.
 */
export function sampleTrailCurve(points:readonly Point[],sampled=false):Point[]{
  if(sampled||points.length<2)return points.map(p=>({...p}));
  const out:Point[]=[];
  for(let i=0;i<points.length-1;i++)for(let s=0;s<12;s++){
    const a=points[Math.max(0,i-1)],b=points[i],c=points[i+1],d=points[Math.min(points.length-1,i+2)],t=s/12;
    const value=(key:'x'|'y')=>.5*(2*b[key]+(-a[key]+c[key])*t+(2*a[key]-5*b[key]+4*c[key]-d[key])*t*t+(-a[key]+3*b[key]-3*c[key]+d[key])*t*t*t);
    out.push({x:value('x'),y:value('y')});
  }
  out.push({...points[points.length-1]});
  return out;
}

/** A distance-based profile avoids bumps caused by uneven curve sampling. */
export function streetProfile(points:readonly Point[],width:number,seed:number):StreetSample[]{
  let distance=0;
  return points.map((p,i)=>{
    if(i)distance+=Math.hypot(p.x-points[i-1].x,p.y-points[i-1].y);
    const variation=1+.11*Math.sin(distance*.67+seed*1.7)+.035*Math.sin(distance*1.61+seed*.9);
    return {...p,radius:width*.5*variation};
  });
}

const mix=(a:Point,b:Point,t:number):Point=>({x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t});
const quadratic=(a:Point,b:Point,c:Point):Point[]=>Array.from({length:13},(_,i)=>mix(mix(a,b,i/12),mix(b,c,i/12),i/12));
const safe=(nav:Navigation,points:Point[])=>points.every((p,i)=>isWalkable(nav,p)&&(!i||lineClear(nav,points[i-1],p)));

/** Round only corners that retain clearance. A narrow alley keeps its safe route. */
function softenDoorRoute(nav:Navigation,route:Point[],seed:number,tangent?:Point):Point[]{
  if(route.length===2){
    const [a,b]=route,dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy);
    const bend=Math.min(.65,len*.16)*(seed%2?1:-1),mid=mix(a,b,.5);
    if(len>.2){
      // Arrive along the main road's tangent instead of meeting it at a rigid T.
      if(tangent&&len>1.2){
        const sign=(dx*tangent.x+dy*tangent.y)>=0?1:-1,reach=Math.min(1.15,len*.4);
        const control={x:b.x-tangent.x*reach*sign,y:b.y-tangent.y*reach*sign};
        const curve=quadratic(a,control,b);
        if(safe(nav,curve))return curve;
      }
      const curve=quadratic(a,{x:mid.x-dy/len*bend,y:mid.y+dx/len*bend},b);
      if(safe(nav,curve))return curve;
    }
    return route;
  }
  const out=[route[0]];
  for(let i=1;i<route.length-1;i++){
    const a=route[i-1],b=route[i],c=route[i+1];
    const enter=mix(b,a,Math.min(.25,.7/(Math.hypot(b.x-a.x,b.y-a.y)||1)));
    const leave=mix(b,c,Math.min(.25,.7/(Math.hypot(c.x-b.x,c.y-b.y)||1)));
    const curve=quadratic(enter,b,leave);
    if(safe(nav,[out[out.length-1],...curve,c]))out.push(...curve);
    else out.push(b);
  }
  out.push(route[route.length-1]);return out;
}

/** Generated once with the static ground. The same collision map as movement
 * chooses visible connections, so a winding entrance never cuts through a shop.
 */
export function connectStreetDoors(trails:StreetTrail[],doors:StreetDoor[],nav:Navigation):DoorPath[]{
  const segments=trails.flatMap(trail=>{
    const points=sampleTrailCurve(trail.points,trail.sampled);
    return points.slice(1).map((b,i)=>({a:points[i],b}));
  });
  if(!segments.length)return [];
  const paths:DoorPath[]=[];
  for(const [index,door] of doors.entries()){
    if(!isWalkable(nav,door.at))continue;
    const candidates=segments.map(({a,b})=>{
      const dx=b.x-a.x,dy=b.y-a.y;
      const t=Math.max(0,Math.min(1,((door.at.x-a.x)*dx+(door.at.y-a.y)*dy)/(dx*dx+dy*dy||1)));
      const length=Math.hypot(dx,dy)||1,at=mix(a,b,t);return {at,tangent:{x:dx/length,y:dy/length},distance:Math.hypot(at.x-door.at.x,at.y-door.at.y)};
    }).sort((a,b)=>a.distance-b.distance);
    // Prefer a short visible branch, with a routed connection when an obstacle
    // stands between the doorstep and its closest street.
    const direct=candidates.find(c=>c.distance<=candidates[0].distance+3&&lineClear(nav,door.at,c.at));
    let route:Point[]=[];
    if(direct)route=[{...door.at},direct.at];
    else for(const candidate of candidates.filter((_,i)=>i%12===0).slice(0,6)){
      const found=findRoute(nav,door.at,candidate.at);
      if(found.length&&Math.hypot(found[found.length-1].x-candidate.at.x,found[found.length-1].y-candidate.at.y)<.001){route=[{...door.at},...found];break;}
    }
    if(!route.length)continue;
    paths.push({id:door.id,district:door.district,points:softenDoorRoute(nav,route,index,direct?.tangent)});
  }
  return paths;
}
