/** Articulated water poses. The illustrated head keeps the player's saved appearance;
 * limbs, hull and oars share one ground projection. No extra image fetches or frame loop. */
import {art,defaultLook,topColour} from '../v4/look.js';

const TAU=Math.PI*2,INK='#76533f';
const ellipse=(c,x,y,rx,ry,colour,edge='')=>{c.beginPath();c.ellipse(x,y,rx,ry,0,0,TAU);c.fillStyle=colour;c.fill();if(edge){c.strokeStyle=edge;c.lineWidth=.45;c.stroke();}};
function curve(c,a,b,d,colour,width){c.beginPath();c.moveTo(...a);c.quadraticCurveTo(...b,...d);c.strokeStyle=colour;c.lineWidth=width;c.lineCap='round';c.stroke();}
function limb(c,a,b,d,skin){curve(c,a,b,d,INK,3.1);curve(c,a,b,d,skin,2.25);}
function ring(c,x,y,rx,alpha=.4){c.beginPath();c.ellipse(x,y,rx,rx*.32,0,0,TAU);c.strokeStyle=`rgba(235,255,246,${alpha})`;c.lineWidth=.6;c.stroke();}
function palette(appearance){const look={...defaultLook(appearance.gender),...appearance.look};return {skin:art(look,'skin').c,top:topColour(look,appearance.gender),bottom:art(look,'bottom').c};}

/** Screen heading remains aligned with movement even with a foreshortened hull. */
export function waterFrame(heading=0){
  const h=Number.isFinite(heading)?heading:0,a=Math.atan2(Math.sin(h)/.56,Math.cos(h)),co=Math.cos(a),si=Math.sin(a);
  return (forward,side,height=0)=>[co*forward-si*side,(si*forward+co*side)*.56-height];
}
export function waterStroke(time,moving){return moving?Math.sin(time/240):0;}
function face(c,stamp,x,y,size=20){
  // The atlas' hair and face occupy the upper 58%; standing arms and clothes stay out.
  const sh=stamp.height*.58,h=size*sh/stamp.width;
  c.drawImage(stamp,0,0,stamp.width,sh,x-size/2,y-h,size,h);
}

function projection(pose,bobScale){
  const p=waterFrame(pose.heading),bob=(Number.isFinite(pose.bob)?pose.bob:0)*bobScale;
  return {at:(f,s,z=0)=>{const q=p(f,s,z);return [pose.x+q[0],pose.y+q[1]+bob];},depth:(f,s)=>p(f,s)[1]};
}
function polygon(c,points,colour,edge=''){
  c.beginPath();c.moveTo(...points[0]);for(let i=1;i<points.length;i++)c.lineTo(...points[i]);c.closePath();
  c.fillStyle=colour;c.fill();if(edge){c.strokeStyle=edge;c.lineWidth=.55;c.lineJoin='round';c.stroke();}
}
function line(c,a,b,colour,width){c.beginPath();c.moveTo(...a);c.lineTo(...b);c.strokeStyle=colour;c.lineWidth=width;c.lineCap='round';c.stroke();}
function convexHull(points){
  const sorted=[...points].sort((a,b)=>a[0]-b[0]||a[1]-b[1]),turn=(a,b,d)=>(b[0]-a[0])*(d[1]-a[1])-(b[1]-a[1])*(d[0]-a[0]);
  const half=list=>{const out=[];for(const point of list){while(out.length>1&&turn(out[out.length-2],out[out.length-1],point)<=0)out.pop();out.push(point);}return out;};
  return [...half(sorted).slice(0,-1),...half(sorted.reverse()).slice(0,-1)];
}

/** A single prone body supplies every limb root; depth is measured before height. */
export function swimmerGeometry(pose,time,moving){
  const {at,depth}=projection(pose,.2),stroke=waterStroke(time,moving);
  const shoulders=[-1,1].map(side=>({side,point:at(1,side*3.4,.4)})),hips=[-1,1].map(side=>({side,point:at(-5.2,side*2.1,-.7)}));
  const chest=at(2.4,0,1),head=at(2.8,0,2.7),arms=shoulders.map(({side,point})=>{
    const pull=stroke*side;
    return {side,shoulder:point,elbow:at(1+pull*2.5,side*(6.2-Math.abs(pull)*.6),-.2),hand:at(3+pull*4.5,side*(7.1-Math.abs(pull)*1.6),-.35),depth:depth(1,side*4),pull};
  }).sort((a,b)=>a.depth-b.depth);
  const legs=hips.map(({side,point})=>({side,hip:point,knee:at(-9.1,side*(2.5+stroke*.4),-1.1),foot:at(-13.7+stroke*side*.8,side*(2.3-stroke*.5),-.6),depth:depth(-8,side*2)})).sort((a,b)=>a.depth-b.depth);
  return {at,stroke,shoulders,hips,chest,head,neck:[chest,head],arms,legs,headSize:19,bodyAlpha:.68,
    body:[chest,shoulders[0].point,hips[0].point,at(-6,0,-.8),hips[1].point,shoulders[1].point]};
}

export function drawSwimmer(c,stamp,pose,time,moving,appearance={}){
  const g=swimmerGeometry(pose,time,moving),{skin,top,bottom}=palette(appearance),[far,near]=g.arms;
  if(moving)ring(c,...g.at(-15,0),8+g.stroke*.5,.28);
  c.save();c.globalAlpha=g.bodyAlpha;
  for(const leg of g.legs){limb(c,leg.hip,leg.knee,leg.foot,skin);line(c,leg.hip,leg.knee,bottom,2.5);}
  limb(c,far.shoulder,far.elbow,far.hand,skin);
  polygon(c,g.body,top,INK);
  // The neck overlaps the chest and crop baseline, including in a side view.
  line(c,...g.neck,INK,3.6);line(c,...g.neck,skin,2.7);
  limb(c,near.shoulder,near.elbow,near.hand,skin);c.restore();
  face(c,stamp,...g.head,g.headSize);
  // Short local ripples leave the joined chest and limbs visible.
  for(const arm of g.arms)if(moving&&arm.pull<-.2)ring(c,...arm.hand,2.1,.48);
  ring(c,...g.at(-2,0),9,.2);
}

// Sample the two smooth gunwales once in boat space. Both wall edges reuse these vertices.
const HULL=[];
for(const side of [-1,1])for(let i=0;i<16;i++){
  const t=i/16,u=1-t;
  HULL.push(side<0?[23*u*u*u+42*u*u*t-48*u*t*t-22*t*t*t,-30*u*t]:[-22*u*u*u-48*u*u*t+42*u*t*t+23*t*t*t,30*u*t]);
}

/** Fixed oarlocks, connected hull walls and a sitter all use the same boat coordinates. */
export function rowboatGeometry(pose,time,moving){
  const {at,depth}=projection(pose,.45),stroke=waterStroke(time,moving),lean=stroke*.5;
  const rim=HULL.map(([f,s])=>at(f,s,3.4)),keel=HULL.map(([f,s])=>at(f*.86,s*.83,-2.1));
  const walls=rim.map((point,i)=>[point,rim[(i+1)%rim.length],keel[(i+1)%rim.length],keel[i]]);
  // On a clockwise screen contour the edges travelling right form the near wall.
  const visible=rim.map((point,i)=>rim[(i+1)%rim.length][0]>point[0]);
  const start=visible.findIndex((value,i)=>value&&!visible[(i+visible.length-1)%visible.length]);
  const indices=[start];for(let i=start;visible[i];i=(i+1)%rim.length)indices.push((i+1)%rim.length);
  const nearRim=indices.map(i=>rim[i]),near=[...nearRim,...indices.map(i=>keel[i]).reverse()];
  const seat=at(-1.5,0,5),hips=seat,head=at(-1.5+lean,0,12);
  const torso=convexHull([-1,1].flatMap(side=>[-1,1].flatMap(f=>[at(-1.5+lean+f*1.6,side*3.2,11.9),at(-1.5+f*1.3,side*2.6,5.3)])));
  const recovery=moving?Math.max(0,Math.cos(time/240)):0,angle=stroke*.44,dz=-.33+recovery*.16;
  const oars=[-1,1].map(side=>{
    const along=length=>at(2+Math.sin(angle)*length,side*(7+Math.cos(angle)*length),4.8+dz*length);
    return {side,grip:along(-4.5),lock:along(0),tip:along(16),bladeStart:along(12),depth:depth(2,side*7),inWater:4.8+dz*16<=0};
  }).sort((a,b)=>a.depth-b.depth);
  const arms=oars.map(oar=>({side:oar.side,shoulder:at(-1.5+lean,oar.side*3.2,11.6),elbow:at(-1+lean,oar.side*4.1,8.1),hand:oar.grip,depth:oar.depth}));
  return {at,stroke,seat,hips,head,torso,arms,oars,hull:{rim,keel,walls,near,nearRim,outer:convexHull([...rim,...keel]),inside:HULL.map(([f,s])=>at(f*.91,s*.84,3.5))}};
}

/** Outer oars straddle the joined hull; only the near wall covers the seated legs. */
export function drawRowboat(c,stamp,pose,time,moving,appearance={}){
  const g=rowboatGeometry(pose,time,moving),{skin,top,bottom}=palette(appearance),{at,hull}=g,[farOar,nearOar]=g.oars,[farArm,nearArm]=g.arms;
  const outerOar=oar=>{
    line(c,oar.lock,oar.tip,'#76553b',1.25);line(c,oar.bladeStart,oar.tip,'#c58f54',2.9);
    if(moving&&oar.inWater)ring(c,...oar.tip,2.8,.52);
  };
  const innerOar=oar=>line(c,oar.grip,oar.lock,'#76553b',1.25);
  const oarlock=oar=>ellipse(c,...oar.lock,.85,.75,'#d7ae72',INK);
  const arm=a=>{limb(c,a.shoulder,a.elbow,a.hand,skin);ellipse(c,...a.hand,1.2,1.1,skin,INK);};
  ring(c,pose.x,pose.y+6,24,.2);
  if(moving)ring(c,...at(-25,0),12+g.stroke,.28);
  if(stamp)outerOar(farOar);
  polygon(c,hull.outer,'#8d4939',INK);polygon(c,hull.rim,'#bd7850',INK);polygon(c,hull.inside,'#e8bc7e');
  for(let f=-15;f<=15;f+=5)line(c,at(f,-5,3.6),at(f,5,3.6),'#bc8656',.45);
  for(const f of [-11,-1.5,12])line(c,at(f,-6.2,4.5),at(f,6.2,4.5),'#97633e',2.3);
  if(stamp){
    innerOar(farOar);oarlock(farOar);arm(farArm);
    for(const side of [-1,1])curve(c,at(-1.5,side*1.8,5.6),at(4.5,side*2.1,5.5),at(6,side*2,2.5),bottom,2.8);
    polygon(c,g.torso,top,INK);
    // Jacket panels rotate with the chest, rather than standing upright across the neck.
    for(const side of [-1,1])line(c,at(-.3+g.stroke*.5,side*2,11.1),at(-.4,side*1.8,6.1),'#e7b363',1.9);
    line(c,at(-1.5+g.stroke*.5,0,11.9),g.head,skin,2.5);
    innerOar(nearOar);arm(nearArm);face(c,stamp,...g.head,20.5);
  }
  polygon(c,hull.near,'#8d4939');
  for(let i=1;i<hull.nearRim.length;i++)line(c,hull.nearRim[i-1],hull.nearRim[i],'#f0c789',1.15);
  if(stamp){outerOar(nearOar);oarlock(nearOar);}
}
