/** Pure geometry and navigation for the courier street grid. Metres; y grows south. */
export const B=40;
const GX=6,GY=4,HW=5,FRONT=8;
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
/** A readable map can zoom around the rider and pan without losing the town. */
export function mapTransform(width,height,zoom=1,center={x:120,y:80}){
 const scale=Math.min(width/280,height/200)*clamp(zoom,1,3);
 const axis=(value,span,pixels)=>{const half=pixels/scale/2;
  return half>=span/2+12?span/2:clamp(value,half-12,span+12-half);};
 const at={x:axis(center.x,240,width),y:axis(center.y,160,height)};
 return {scale,ox:width/2-at.x*scale,oy:height/2-at.y*scale,center:at};
}
/** Is (x,y) on a street (with room for the scooter)? */
export function onRoad(x,y,m=.6){
  const i=Math.round(x/B),j=Math.round(y/B);
  if(i>=0&&i<=GX&&Math.abs(x-i*B)<=HW-m&&y>=-HW+m&&y<=GY*B+HW-m)return true;
  return j>=0&&j<=GY&&Math.abs(y-j*B)<=HW-m&&x>=-HW+m&&x<=GX*B+HW-m;
}
/** Where a stop's door is: its landmark stands on the corner north-east of its junction (north-west on the last
 * street), facing the street; `x` is the door, `y` the street it faces. */
export function gateOf(n){
  const gx=Number(n.x)||0,gy=Number(n.y)||0,east=gx<GX;
  return {x:gx*B+(east?FRONT+6:-FRONT-6),y:gy*B,gx,gy,east};
}
/** The next point to ride to on the way to `T` (a gateOf): along this street to the target's street (turning in the
 * middle of a junction), then to the door. The ▲ of the HUD points at it. */
export function waypoint(px,py,T){
  const i=Math.round(px/B),j=Math.round(py/B),onH=Math.abs(py-j*B)<=HW+.5,onV=Math.abs(px-i*B)<=HW+.5;
  const ti=clamp(Math.round(T.x/B),0,GX);
  let w;
  if(onH&&j===T.gy)w={x:T.x,y:T.y-2,last:true};                 // on the target's street: to the door
  else if(onV&&(i===ti||!onH))w={x:i*B,y:T.gy*B};                // on the right avenue (or between junctions on one)
  else w={x:ti*B,y:j*B};                                         // along this street to the target's avenue
  // In a junction, line up with the street about to be taken (its middle) before turning, so the arrow never cuts a corner.
  if(onH&&onV){
    const across=w.y===j*B||w.last?Math.abs(py-j*B)>1.5:Math.abs(px-i*B)>1.5;
    if(across)return {x:i*B,y:j*B};
  }
  return w;
}


/** Trace the same guidance as the ride. Sub-metre steps retain its junction alignment, then remove collinear points. */
export function roadRoute(x,y,target){
 const points=[{x,y}];
 for(let step=0;step<1200;step++){
  const w=waypoint(x,y,target),dx=w.x-x,dy=w.y-y,d=Math.hypot(dx,dy);
  if(d<.00001){if(w.last)break;return points;}
  const k=Math.min(.75,d)/d;x+=dx*k;y+=dy*k;
  const p={x,y},a=points.at(-2),b=points.at(-1);
  if(a&&Math.abs((b.x-a.x)*(p.y-b.y)-(b.y-a.y)*(p.x-b.x))<1e-8&&(b.x-a.x)*(p.x-b.x)+(b.y-a.y)*(p.y-b.y)>=0)points[points.length-1]=p;
  else points.push(p);
  if(w.last&&d<=.75)break;
 }
 return points;
}
const angle=a=>Math.atan2(Math.sin(a),Math.cos(a));
const cueFor=a=>Math.abs(a)>2.35?'uturn':Math.abs(a)>.5?(a>0?'right':'left'):'straight';
export function navigation(points,heading,target){
 const p=points[0],distance=points.slice(1).reduce((sum,q,i)=>sum+Math.hypot(q.x-points[i].x,q.y-points[i].y),0);
 const inBay=Math.abs(p.x-target.x)<6.5&&p.y>=target.y-6&&p.y<=target.y+6;
 if(inBay)return {distance,cue:'arrive',turnDistance:0};
 const segments=[];
 let travelled=0;
 for(let i=1;i<points.length;i++){
  const a=points[i-1],b=points[i],len=Math.hypot(b.x-a.x,b.y-a.y);
  if(len<.01)continue;
  segments.push({dir:Math.atan2(b.y-a.y,b.x-a.x),len,at:travelled});travelled+=len;
 }
 let previous=null;
 for(let i=0;i<segments.length;i++){
  const segment=segments[i],next=segments.slice(i+1).find(s=>s.len>=HW);
  // Short interior segments are lane-centering wiggles. Keep a short approach when it
  // follows the rider's heading: its next sustained segment may turn in just 1-4 m.
  if(i>0&&i<segments.length-1&&segment.len<HW)continue;
  if(i===0&&segment.len<HW&&next&&cueFor(angle(segment.dir-heading))!=='straight'&&cueFor(angle(next.dir-heading))==='straight')continue;
  const cue=cueFor(angle(segment.dir-(previous??heading)));
  if(cue!=='straight')return {distance,cue,turnDistance:previous===null?0:segment.at};
  previous=segment.dir;
 }
 return {distance,cue:'straight',turnDistance:distance};
}
