import {isWalkable,project} from './model';
import type {Navigation,Point,Rect} from './model';
import {sampleTrailCurve,streetProfile} from './trail-geometry';

type Trail={width:number;points:Point[];sampled?:boolean};
type RoadEdge={a:Point;b:Point;radius:number};
type SignOccluder={bounds:Rect;depth:number};
const roadCache=new WeakMap<Trail[],RoadEdge[]>();
function edges(trails:Trail[]){
  let rows=roadCache.get(trails);
  if(!rows){rows=[];trails.forEach((trail,index)=>{
    const points=streetProfile(sampleTrailCurve(trail.points,trail.sampled),trail.width,index);
    for(let i=1;i<points.length;i++)rows!.push({a:points[i-1],b:points[i],radius:Math.max(points[i-1].radius,points[i].radius)+.13});
  });roadCache.set(trails,rows);}return rows;
}
function roadClearance(p:Point,roads:RoadEdge[]){
  let distance=Infinity;
  for(const {a,b,radius} of roads){
    const dx=b.x-a.x,dy=b.y-a.y,length=dx*dx+dy*dy,t=length?Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/length)):0;
    distance=Math.min(distance,Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)-radius);
  }return distance;
}

/** Nameboards stand on nearby open verges, leaving the destination and doors clear.
 * The original approach remains the walking target; only the visual support moves.
 */
export function wayfindingMount(at:Point,nav:Navigation,trails:Trail[],reserved:Point[]=[],doors:Point[]=[],occluders:SignOccluder[]=[],shape:Rect={x0:-107,y0:-128,x1:107,y1:8}):Point{
  const roads=edges(trails);let fallback:Point|undefined,best=-Infinity;
  for(let radius=1.5;radius<=6;radius+=.5)for(let step=0;step<24;step++){
    // Start on the near verge. A walkable point behind a house can still hide
    // the board a hundred screen pixels above it, so test the full stand too.
    const angle=Math.PI*.25+step*Math.PI/12,p={x:at.x+Math.cos(angle)*radius,y:at.y+Math.sin(angle)*radius},screen=project(p);
    const feet=[p,{x:p.x-.5,y:p.y+.5},{x:p.x+.5,y:p.y-.5}];
    if(feet.some(q=>!isWalkable(nav,q))||reserved.some(q=>Math.hypot(p.x-q.x,p.y-q.y)<1.8)||doors.some(q=>Math.hypot(p.x-q.x,p.y-q.y)<1.3))continue;
    if(occluders.some(({bounds:b,depth})=>depth>screen.y+.4&&screen.x+shape.x0<b.x1&&screen.x+shape.x1>b.x0&&screen.y+shape.y0<b.y1&&screen.y+shape.y1>b.y0))continue;
    const clearance=Math.min(...feet.map(q=>roadClearance(q,roads)));
    if(clearance>=.15)return p;
    if(clearance>best){best=clearance;fallback=p;}
  }
  // In a broad paved forecourt, use the clearest reachable edge rather than the arrival point.
  return fallback||at;
}
