/** A presentation-only view of delivery_drive's metre-based street world.
 * Projection, gate bays and heading use the existing scooter state. No game commands live here.
 * Ground is cached in visible chunks; buildings/trees are cached stamps and drawn in ground-depth order.
 */
import {B,roadRoute} from './delivery_navigation.js';
import {signalState} from '../v4/traffic.js';
import {t as tr} from '../v4/i18n.js';
import {art,topColour,hairColour,defaultLook} from '../v4/look.js';
import {getCharacterStamp,preloadIllustratedCharacters} from '../isometric/character-art.js';

const HW=5,FRONT=8,GX=6,GY=4;
const INK='#70523e',CREAM='#fff7e5';
const SOURCES={home:'/icons/isometric/home.webp',grocery:'/icons/isometric/grocery.webp',cafe:'/icons/isometric/cafe.webp',tree:'/icons/isometric/tree.webp',pharmacy:'/icons/cozy-v2/pharmacy.webp','mother-baby':'/icons/cozy-v2/mother-baby.webp'};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));

/** Fixed orthographic 2:1 projection: one world metre is scale pixels horizontally. */
export function isoProject(x,y,z=0,camera){
  const dx=x-camera.x,dy=y-camera.y,k=camera.scale;
  return {x:camera.cx+(dx-dy)*k,y:camera.cy+(dx+dy)*k*.5-z*k};
}
export function isoCamera(state,w,h){
  const scale=clamp(w/95*1.8,6.5,10.5),ahead=5;
  return {x:state.x+Math.cos(state.a)*ahead,y:state.y+Math.sin(state.a)*ahead,scale,cx:w*.5,cy:h*.59};
}
export const depthOf=point=>point.x+point.y;
export function riderDirection(angle=0){return ['se','sw','nw','ne'][((Math.round(angle/(Math.PI/2))%4)+4)%4];}
export function neighbourhoodKind(building){
  if(SOURCES[building.assetKind])return building.assetKind;
  const variant=Math.abs(Math.round(building.x0*3+building.y0*5))%9;
  return variant===0?'pharmacy':variant===1?'mother-baby':'home';
}
export function destinationPoints(gate,camera){
  const g=gate;
  return {anchor:isoProject(g.x,g.y,0,camera),bay:[[g.x-5.5,g.y-HW+.3],[g.x+5.5,g.y-HW+.3],[g.x+5.5,g.y-.4],[g.x-5.5,g.y-.4]].map(([x,y])=>isoProject(x,y,0,camera))};
}
/** RAF is needed for input, coasting, parking, or the existing bounded signal wait. */
export function needsDrivingFrames(state){
  const k=state.keys||{},b=state.btn||{},j=state.joy||{};
  return Math.abs(state.v||0)>.025||Math.abs(state.steer||0)>.025||Object.values(k).some(Boolean)||Object.values(b).some(Boolean)||
    Math.abs(j.drive||0)>.01||Math.abs(j.steer||0)>.01||(!state.stopDone&&!state.sending)||
    !!(state.lightPending&&!state.lightDenied?.has(state.lightKey));
}
export function riderPalette(look={},gender='none'){
  const L={...defaultLook(gender),...look};
  return {top:topColour(L,gender),skin:art(L,'skin').c,hair:hairColour(L),bottom:art(L,'bottom').c,long:!!art(L,'hair').long,glasses:L.acc==='kinh_tron'||L.acc==='kinh_ram',helmet:look.helmet||'#6a9b8b'};
}

function surface(width,height){
  if(typeof OffscreenCanvas!=='undefined')return new OffscreenCanvas(width,height);
  const cv=document.createElement('canvas');cv.width=width;cv.height=height;return cv;
}
function polygon(c,points,fill,stroke=null,width=1){
  c.beginPath();points.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.closePath();
  if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=width;c.stroke();}
}
function softPolygon(c,points,fill,stroke=INK,width=1.2){
  c.beginPath();const first=points[0],last=points[points.length-1];c.moveTo(first.x*.75+last.x*.25,first.y*.75+last.y*.25);
  for(let i=0;i<points.length;i++){const p=points[i],next=points[(i+1)%points.length];c.quadraticCurveTo(p.x,p.y,p.x*.75+next.x*.25,p.y*.75+next.y*.25);c.lineTo(p.x*.25+next.x*.75,p.y*.25+next.y*.75);}
  c.closePath();c.fillStyle=fill;c.fill();c.strokeStyle=stroke;c.lineWidth=width;c.stroke();
}
function material(c,x0,y0,x1,y1,light,dark){
  const gradient=c.createLinearGradient?.(x0,y0,x1,y1);if(!gradient?.addColorStop)return light;
  gradient.addColorStop(0,light);gradient.addColorStop(1,dark);return gradient;
}
function groundRect(c,camera,x0,y0,x1,y1,fill,stroke=null,width=1){
  polygon(c,[[x0,y0],[x1,y0],[x1,y1],[x0,y1]].map(([x,y])=>isoProject(x,y,0,camera)),fill,stroke,width);
}
function line(c,a,b,color,width=1){
  c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.stroke();
}
function ellipse(c,x,y,rx,ry,fill,stroke=null){
  c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=1.2;c.stroke();}
}
function softRect(c,x,y,w,h,fill,stroke=null){
  c.beginPath();c.roundRect(x,y,w,h,Math.min(w,h)*.18);c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=1;c.stroke();}
}
function paper(c,x,y,w,h,fill=CREAM){
  c.fillStyle=fill;c.strokeStyle=INK;c.lineWidth=1.2;c.beginPath();c.roundRect(x,y,w,h,8);c.fill();c.stroke();
}

export function createIsometricRenderer({createCanvas=surface,ImageClass=globalThis.Image,spriteSources=SOURCES,characterStamp=getCharacterStamp,preloadCharacters=preloadIllustratedCharacters,onAsset=()=>{}}={}){
  const stamps=new Map(),groundCache=new Map(),images=new Map();
  const visibleStamps=new Set(),visibleGround=new Set();
  let worldRef=null,groundBuilds=0,stampBuilds=0,disposed=false;
  // Evict only after the whole viewport is known. A fixed FIFO smaller than a
  // fullscreen view otherwise rebuilds every visible sprite/chunk every frame.
  function trimCache(cache,visible,spareLimit){
    const limit=Math.max(spareLimit,visible.size);
    for(const key of cache.keys()){
      if(cache.size<=limit)break;
      if(!visible.has(key))cache.delete(key);
    }
  }
  function cachedStamp(key){const stamp=stamps.get(key);if(stamp)visibleStamps.add(key);return stamp;}
  function cacheStamp(key,stamp){
    visibleStamps.add(key);stamps.set(key,stamp);stampBuilds++;return stamp;
  }
  function illustrationsReady(){if(disposed)return;for(const key of stamps.keys())if(key.startsWith('character:'))stamps.delete(key);onAsset();}
  preloadCharacters(illustrationsReady);
  function imageFor(kind){
    const src=spriteSources[kind];if(!src||!ImageClass)return null;if(images.has(src))return images.get(src);
    const image=new ImageClass(),record={image,ready:false,failed:false};images.set(src,record);
    image.onload=()=>{if(disposed)return;record.ready=!!image.naturalWidth;stamps.clear();onAsset();};image.onerror=()=>{record.failed=true;};image.src=globalThis.__mnlBoot?.asset?.(src)||src;return record;
  }
  function groundFor(W,k,chunkX,chunkY){
    if(worldRef!==W){groundCache.clear();worldRef=W;}
    const key=[k.toFixed(3),chunkX,chunkY].join(':');
    visibleGround.add(key);
    if(groundCache.has(key)){const value=groundCache.get(key);groundCache.delete(key);groundCache.set(key,value);return value;}
    const chunk=B*2,x0=chunkX*chunk,y0=chunkY*chunk,x1=x0+chunk,y1=y0+chunk,pad=3;
    const width=Math.ceil((x1-x0+y1-y0)*k)+pad*2,height=Math.ceil((x1-x0+y1-y0)*k*.5)+pad*2;
    const cv=createCanvas(width,height),c=cv.getContext('2d'),camera={x:0,y:0,scale:k,cx:-(x0-y1)*k+pad,cy:-(x0+y0)*k*.5+pad};
    c.clearRect(0,0,width,height);
    c.save();groundRect(c,camera,x0,y0,x1,y1,null);c.clip();
    groundRect(c,camera,-B,-B,GX*B+B,GY*B+B,'#e2e9c7');
    // The block parcels keep the same bounds as the collision world.
    for(let x=0;x<GX;x++)for(let y=0;y<GY;y++){
      groundRect(c,camera,x*B+HW,y*B+HW,(x+1)*B-HW,(y+1)*B-HW,(x+y)%3?'#c9d7b0':'#b9cca2');
      groundRect(c,camera,x*B+FRONT,y*B+FRONT,(x+1)*B-FRONT,(y+1)*B-FRONT,'#dce3bf');
    }
    for(let i=0;i<=GX;i++)groundRect(c,camera,i*B-FRONT,-FRONT,i*B+FRONT,GY*B+FRONT,'#e8d9b9', '#baaa8d',.8);
    for(let j=0;j<=GY;j++)groundRect(c,camera,-FRONT,j*B-FRONT,GX*B+FRONT,j*B+FRONT,'#e8d9b9', '#baaa8d',.8);
    const road=material(c,0,0,width,height,'#cac5b6','#bbb7a9');
    for(let i=0;i<=GX;i++)groundRect(c,camera,i*B-HW,-HW,i*B+HW,GY*B+HW,road);
    for(let j=0;j<=GY;j++)groundRect(c,camera,-HW,j*B-HW,GX*B+HW,j*B+HW,road);
    // Fixed seams and quiet lane dashes are painted once.
    for(let i=0;i<=GX;i++)for(let y=HW+1;y<GY*B-HW;y+=6){
      if(Math.abs(y-Math.round(y/B)*B)<HW+2)continue;
      groundRect(c,camera,i*B-.12,y,i*B+.12,y+2.6,'#fff6de');
      line(c,isoProject(i*B-HW-1,y,0,camera),isoProject(i*B-FRONT,y,0,camera),'#cdbb9d',.6);
      line(c,isoProject(i*B+HW+1,y,0,camera),isoProject(i*B+FRONT,y,0,camera),'#cdbb9d',.6);
    }
    for(let j=0;j<=GY;j++)for(let x=HW+1;x<GX*B-HW;x+=6){
      if(Math.abs(x-Math.round(x/B)*B)<HW+2)continue;
      groundRect(c,camera,x,j*B-.12,x+2.6,j*B+.12,'#fff6de');
      line(c,isoProject(x,j*B-HW-1,0,camera),isoProject(x,j*B-FRONT,0,camera),'#cdbb9d',.6);
      line(c,isoProject(x,j*B+HW+1,0,camera),isoProject(x,j*B+FRONT,0,camera),'#cdbb9d',.6);
    }
    for(const L of W.lights||[])for(let n=-3;n<=3;n++){
      const x=L.i*B,y=L.j*B,u=n*1.3;
      groundRect(c,camera,x+u-.4,y-HW-2.6,x+u+.4,y-HW-.6,CREAM);
      groundRect(c,camera,x+u-.4,y+HW+.6,x+u+.4,y+HW+2.6,CREAM);
      groundRect(c,camera,x-HW-2.6,y+u-.4,x-HW-.6,y+u+.4,CREAM);
      groundRect(c,camera,x+HW+.6,y+u-.4,x+HW+2.6,y+u+.4,CREAM);
    }
    for(const g of W.gardens||[])groundRect(c,camera,g.x0,g.y0,g.x1,g.y1,'#b7cc96');
    c.restore();
    const ground={cv,ox:camera.cx,oy:camera.cy};groundCache.set(key,ground);groundBuilds++;
    return ground;
  }
  function drawGround(c,state,W,camera){
    const k=camera.scale,corner=[[0,0],[state.w,0],[state.w,state.h],[0,state.h]].map(([x,y])=>{
      const dx=(x-camera.cx)/k,dy=(y-camera.cy)*2/k;return {x:camera.x+(dx+dy)*.5,y:camera.y+(dy-dx)*.5};
    });
    const minX=Math.floor(Math.min(...corner.map(p=>p.x))/(B*2)),maxX=Math.floor(Math.max(...corner.map(p=>p.x))/(B*2));
    const minY=Math.floor(Math.min(...corner.map(p=>p.y))/(B*2)),maxY=Math.floor(Math.max(...corner.map(p=>p.y))/(B*2)),origin=isoProject(0,0,0,camera);
    for(let x=minX;x<=maxX;x++)for(let y=minY;y<=maxY;y++){const floor=groundFor(W,k,x,y);c.drawImage(floor.cv,origin.x-floor.ox,origin.y-floor.oy);}
  }
  function fallbackHouse(c,w,d,h,k,col,awn,kind){
    const camera={x:0,y:0,scale:k,cx:(w+d)*k*.5+4,cy:(h+(w+d)*.25+1)*k+4};
    const p=(x,y,z)=>isoProject(x-w/2,y-d/2,z,camera),roof=h+.8;
    polygon(c,[p(0,0,0),p(w,0,0),p(w,d,0),p(0,d,0)],'#654e3920');
    polygon(c,[p(0,d,0),p(w,d,0),p(w,d,h),p(0,d,h)],col,INK);
    polygon(c,[p(w,0,0),p(w,d,0),p(w,d,h),p(w,0,h)],'#d6c6a9',INK);
    polygon(c,[p(0,0,h),p(w,0,h),p(w,d,h),p(0,d,h)],'#bb7960',INK);
    polygon(c,[p(-.3,-.3,roof),p(w+.3,-.3,roof),p(w+.3,d+.3,roof),p(-.3,d+.3,roof)],'#cf9473',INK);
    for(let x=1.1;x<w-.5;x+=Math.max(2,w/3)){
      polygon(c,[p(x,d,1.4),p(Math.min(w-.5,x+1.1),d,1.4),p(Math.min(w-.5,x+1.1),d,3.1),p(x,d,3.1)],'#9cbbbc',INK,.7);
      if(h>7)polygon(c,[p(x,d,4.6),p(Math.min(w-.5,x+1.1),d,4.6),p(Math.min(w-.5,x+1.1),d,6.3),p(x,d,6.3)],'#a9c6c0',INK,.7);
    }
    polygon(c,[p(w*.4,d,0),p(w*.63,d,0),p(w*.63,d,2.6),p(w*.4,d,2.6)],'#9f7451',INK,.8);
    if(awn||kind!=='home'){
      const awning=awn||(kind==='cafe'?'#91a774':'#d8ac63');
      polygon(c,[p(0,d,3.8),p(w,d,3.8),p(w,d+1,3.3),p(0,d+1,3.3)],awning,INK,.8);
      for(let x=.8;x<w;x+=2)line(c,p(x,d,3.75),p(x,d+1,3.3),CREAM,1);
    }
    // Roof tiles and pots are fixed details; no animated scenery or external textures.
    for(let x=1;x<w;x+=2.5)line(c,p(x,0,roof),p(x,d,roof),'#b87d61',1);
    const pot=p(w*.17,d,0);softRect(c,pot.x-2,pot.y-3,4,3,'#bb815f',INK);softRect(c,pot.x-2,pot.y-6,4,3,'#78935b');
  }
  function buildingStamp(b,k,kind){
    const w=b.x1-b.x0,d=b.y1-b.y0,h=clamp(b.h||7,4,13),record=imageFor(kind);
    const key=[kind,w.toFixed(1),d.toFixed(1),h,b.col,b.awn,k.toFixed(3),record?.ready?'illustrated':'fallback'].join(':');
    const hit=cachedStamp(key);if(hit)return hit;
    const width=Math.ceil((w+d)*k+8),height=Math.ceil((h+(w+d)*.5+1)*k+8),cv=createCanvas(width,height),c=cv.getContext('2d');
    if(record?.ready){const ratio=record.image.naturalHeight/record.image.naturalWidth,ih=Math.min(height,width*ratio),iw=ih/ratio;c.imageSmoothingEnabled=true;c.drawImage(record.image,(width-iw)*.5,height-ih,iw,ih);}
    else fallbackHouse(c,w,d,h,k,b.col||'#f4deb3',b.awn,kind);
    return cacheStamp(key,{cv,width,height});
  }
  function drawBuilding(c,b,camera,kind,player){
    const midX=(b.x0+b.x1)/2,midY=(b.y0+b.y1)/2,p=isoProject(midX,midY,0,camera),stamp=buildingStamp(b,camera.scale,kind);
    const left=Math.round(p.x-stamp.width*.5),top=Math.round(p.y-stamp.height+(b.x1-b.x0+b.y1-b.y0)*camera.scale*.25+4),r=isoProject(player.x,player.y,0,camera);
    // A nearby roof fades when it covers the controlled scooter, preserving ground depth and visibility.
    const covers=midX+midY>depthOf(player)&&r.x+12>left&&r.x-12<left+stamp.width&&r.y>top&&r.y-35<top+stamp.height;
    c.save();if(covers)c.globalAlpha=.22;c.drawImage(stamp.cv,left,top);c.restore();
  }
  function treeStamp(k,r){
    const record=imageFor('tree'),key='tree:'+k.toFixed(3)+':'+r.toFixed(1)+':'+(record?.ready?'illustrated':'fallback');
    const hit=cachedStamp(key);if(hit)return hit;
    const width=Math.ceil(r*k*4+6),height=Math.ceil(k*(5+r*2)+6),cv=createCanvas(width,height),c=cv.getContext('2d'),x=width*.5,y=height-3;
    if(record?.ready){const ratio=record.image.naturalHeight/record.image.naturalWidth,iw=Math.min(width,height/ratio),ih=iw*ratio;c.imageSmoothingEnabled=true;c.drawImage(record.image,x-iw*.5,y-ih,iw,ih);}
    else {ellipse(c,x,y,r*k*1.5,r*k*.65,'#6b7d4530');softRect(c,x-k*.2,y-k*3.8,k*.4,k*3.8,'#a37f57',INK);ellipse(c,x-r*k*.55,y-k*4.1,r*k,r*k*1.05,'#6e965b',INK);ellipse(c,x+r*k*.5,y-k*4.3,r*k,r*k,'#8caf71',INK);ellipse(c,x,y-k*5,r*k,r*k,'#9bbd7c',INK);}
    return cacheStamp(key,{cv,width,height});
  }
  function drawTree(c,t,camera){const p=isoProject(t.x,t.y,0,camera),s=treeStamp(camera.scale,t.r||1.3);c.drawImage(s.cv,Math.round(p.x-s.width*.5),Math.round(p.y-s.height+3));}
  function drawLamp(c,l,camera){
    const k=camera.scale,p=isoProject(l.x,l.y,0,camera);
    line(c,p,{x:p.x,y:p.y-4.8*k},'#9b8061',1.6);line(c,{x:p.x,y:p.y-4.8*k},{x:p.x+1.1*k,y:p.y-4.8*k},'#9b8061',1.6);
    ellipse(c,p.x+1.1*k,p.y-4.7*k,.45*k,.2*k,'#fbdf8a',INK);
  }
  function drawSignal(c,L,which,camera,axis,now){
    const k=camera.scale,p=isoProject(which===1?L.x:L.x2,which===1?L.y:L.y2,0,camera),color=signalState(now,L.off,axis).color;
    line(c,p,{x:p.x,y:p.y-5.2*k},INK,1.6);
    softRect(c,p.x-.58*k,p.y-6*k,1.16*k,2.75*k,'#655b4c',INK);
    ['red','yellow','green'].forEach((v,i)=>ellipse(c,p.x,p.y-(5.55-i*.82)*k,.3*k,.3*k,v===color?{red:'#da624c',yellow:'#ebc15c',green:'#75ad69'}[v]:'#8b8070'));
  }
  function drawPerson(c,person,camera,wave=false){
    const k=camera.scale,p=isoProject(person.x,person.y,0,camera),gender=(person.variant||0)%2?'female':'male';
    const look={...defaultLook(gender),acc:person.hat?'non_la':'pk_khong'},angle=person.axis==='y'?(person.dir>0?Math.PI/2:-Math.PI/2):(person.dir>0?0:Math.PI);
    const stamp=playerStamp(look,gender,wave?'se':riderDirection(angle),34,person.col||'#a8856b');
    ellipse(c,p.x,p.y,.8*k,.33*k,'#65503923');c.drawImage(stamp.cv,p.x-stamp.width*.5,p.y-stamp.height,stamp.width,stamp.height);
    if(wave){c.font='18px system-ui';c.textAlign='center';c.fillText('👋',p.x+18,p.y-stamp.height+12);}
  }
  function playerStamp(look,gender,direction,width=48,uniformColor=''){
    const key='character:'+JSON.stringify([look,gender,direction,width,uniformColor]);
    const hit=cachedStamp(key);if(hit)return hit;
    const art=characterStamp({look,gender,direction,walkFrame:0,uniformColor,onReady:illustrationsReady});
    return cacheStamp(key,{cv:art.canvas,width,height:width*art.height/art.width});
  }
  function drawScooter(c,rider,camera,player=false,look={},gender='none'){
    const k=camera.scale*(player?1.85:1.15),p=isoProject(rider.x,rider.y,0,camera),a=rider.a??(rider.axis==='x'?(rider.dir>0?0:Math.PI):(rider.dir>0?Math.PI/2:-Math.PI/2));
    const fx=Math.cos(a)-Math.sin(a),fy=(Math.cos(a)+Math.sin(a))*.5,sx=-Math.sin(a)-Math.cos(a),sy=(Math.cos(a)-Math.sin(a))*.5;
    const point=(long,side,z)=>({x:p.x+(fx*long+sx*side)*k,y:p.y+(fy*long+sy*side)*k-z*k});
    const body=player?'#679591':rider.col||'#a2b58c',top=player?'#aac6b0':'#d4d7ae';
    if(player)ellipse(c,p.x,p.y,2.25*k,k*.85,'#fff7e5c9','#a0a475');
    ellipse(c,p.x,p.y,2.1*k,k*.65,'#70523e26');
    // Wheels, a step-through floor, raised rear fairing and seat share the actual heading.
    for(const long of [-1.15,1.15]){
      const wheel=point(long,0,.3);ellipse(c,wheel.x,wheel.y,.42*k,.56*k,'#5c594b',INK);
      ellipse(c,wheel.x,wheel.y,.2*k,.28*k,'#d4c9ac',INK);
    }
    const enamel=material(c,p.x-k,p.y-2*k,p.x+k,p.y,top,body);
    softPolygon(c,[point(-.5,-.5,.55),point(.85,-.5,.55),point(.85,.5,.55),point(-.5,.5,.55)],'#ddd7bb');
    softPolygon(c,[point(-1.3,-.52,.6),point(-.25,-.52,.6),point(-.2,-.46,1.25),point(-1.2,-.46,1.2)],body);
    softPolygon(c,[point(-1.3,.52,.6),point(-.25,.52,.6),point(-.2,.46,1.25),point(-1.2,.46,1.2)],enamel);
    softPolygon(c,[point(-1.2,-.46,1.2),point(-.2,-.46,1.25),point(-.2,.46,1.25),point(-1.2,.46,1.2)],top);
    softPolygon(c,[point(-.95,-.4,1.48),point(.2,-.4,1.48),point(.2,.4,1.48),point(-.95,.4,1.48)],'#81644a');
    const tail=point(-1.32,0,.85);ellipse(c,tail.x,tail.y,.17*k,.19*k,'#c58366',INK);
    if(player){
      polygon(c,[point(-1.3,-.45,1.5),point(-.45,-.45,1.5),point(-.45,-.45,2.4),point(-1.3,-.45,2.4)],'#c99c68',INK,1.1);
      polygon(c,[point(-1.3,.45,1.5),point(-.45,.45,1.5),point(-.45,.45,2.4),point(-1.3,.45,2.4)],'#d9b885',INK,1.1);
      polygon(c,[point(-1.3,-.45,2.4),point(-.45,-.45,2.4),point(-.45,.45,2.4),point(-1.3,.45,2.4)],'#edcca0',INK,1.1);
      const stamp=playerStamp(look,gender,riderDirection(a));c.drawImage(stamp.cv,p.x-stamp.width*.5,p.y-k*.65-stamp.height,stamp.width,stamp.height);
    }else{
      const stamp=playerStamp(defaultLook('male'),'male',riderDirection(a),36,rider.col||'#b79b73');c.drawImage(stamp.cv,p.x-stamp.width*.5,p.y-k*.65-stamp.height,stamp.width,stamp.height);
    }
    // The tall leg shield, steering bar, headlamp and mirrors make the silhouette a scooter.
    softPolygon(c,[point(.75,-.6,.65),point(.75,.6,.65),point(1,.45,2.05),point(1,-.45,2.05)],enamel,INK,1.4);
    softPolygon(c,[point(.76,-.26,.9),point(.76,.26,.9),point(1,.22,1.9),point(1,-.22,1.9)],CREAM,INK,.8);
    line(c,point(.9,0,1.65),point(.9,0,2.55),INK,1.8);
    line(c,point(.9,-.68,2.55),point(.9,.68,2.55),INK,2.3);
    const lamp=point(1.1,0,2.05);ellipse(c,lamp.x,lamp.y,.28*k,.23*k,'#f9e1a3',INK);
    for(const side of [-1,1]){
      line(c,point(.9,side*.54,2.55),point(.9,side*.74,3.05),INK,1.2);
      const mirror=point(.9,side*.74,3.05);ellipse(c,mirror.x,mirror.y,.22*k,.15*k,'#c4d5c5',INK);
    }
  }
  function label(c,text,x,y,highlight=false){
    c.font='700 11px "Be Vietnam Pro",system-ui,sans-serif';c.textAlign='center';c.textBaseline='middle';
    const width=Math.min(155,c.measureText(text).width+18);
    paper(c,x-width*.5,y-12,width,24,highlight?'#fce5a5':CREAM);c.fillStyle=INK;c.fillText(text,x,y,width-10);
  }
  function route(c,state,T,camera){
    if(!T||T.id===state.at)return;
    const points=roadRoute(state.x,state.y,T.gate).map(p=>isoProject(p.x,p.y,0,camera));
    if(points.length<2)return;
    c.lineJoin='round';c.lineCap='round';c.beginPath();points.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));
    c.strokeStyle='#fff8e4';c.lineWidth=5;c.stroke();c.strokeStyle='#af956047';c.lineWidth=2;c.stroke();
    const bay=destinationPoints(T.gate,camera);polygon(c,bay.bay,'#f7d36c80','#b48a3f',1.5);
  }
  function destinationBadge(c,state,T,camera,w,h){
    if(!T||T.id===state.at)return;
    const p=destinationPoints(T.gate,camera).anchor,visible=p.x>38&&p.x<w-38&&p.y>105&&p.y<h-105;
    if(visible){
      const x=p.x,y=p.y-38;
      line(c,p,{x,y:y+8},'#af813d',1.5);
      label(c,`${T.emoji||'📍'} ${tr(T.name)}`,x,y,true);
    }else{
      // A small edge badge still indicates the genuine projected destination when it is off-screen.
      const center=isoProject(state.x,state.y,0,camera),dx=p.x-center.x,dy=p.y-center.y;
      const k=Math.min((w*.5-55)/(Math.abs(dx)||1),(h*.5-135)/(Math.abs(dy)||1));
      const x=clamp(center.x+dx*Math.max(.05,k),46,w-46),y=clamp(center.y+dy*Math.max(.05,k),190,h-135);
      ellipse(c,x,y,18,18,'#fce5a5',INK);c.fillStyle=INK;c.font='700 16px system-ui';c.textAlign='center';c.textBaseline='middle';c.fillText('📍',x,y);
      const length=Math.hypot(dx,dy)||1;line(c,{x:x+dx/length*22,y:y+dy/length*22},{x:x+dx/length*30,y:y+dy/length*30},INK,2);
    }
  }
  function dash(c,state,o,w,h){
    const speed=Math.round(Math.abs(state.v||0)*3.6),fuel=clamp(Number(o.fuel)||0,0,100),width=110,x=w*.5-width*.5,y=h-48;
    paper(c,x,y,width,34);c.fillStyle=INK;c.font='700 11px "Be Vietnam Pro",system-ui';c.textAlign='center';c.textBaseline='middle';c.fillText(`${speed} km/h  ·  ${tr('Xăng')} ${Math.round(fuel)}%`,w*.5,y+16);
  }
  function drawScene(c,state,W,o,now,camera){
    const w=state.w,h=state.h,k=camera.scale,T=W.marks?.[o.target];
    c.fillStyle='#f2ecd7';c.fillRect(0,0,w,h);
    drawGround(c,state,W,camera);
    route(c,state,T,camera);
    for(const sign of o.signs||[]){const L=W.marks?.[sign.node];if(L&&sign.kind==='flood')groundRect(c,camera,L.gate.x-14,L.gate.y-HW,L.gate.x+10,L.gate.y+HW,'#86b4c775');}
    const items=[],seen=(x,y,r=35)=>{const p=isoProject(x,y,0,camera);return p.x>-r&&p.x<w+r&&p.y>-r&&p.y<h+r+70;};
    const add=(x,y,kind,value,extra)=>{if(seen(x,y,kind==='building'?85:35))items.push({x,y,depth:depthOf({x,y}),kind,value,extra});};
    for(const list of W.cells?.values?.()||[])for(const b of list){if(b.L)continue;add((b.x0+b.x1)/2,(b.y0+b.y1)/2,'building',b,neighbourhoodKind(b));}
    for(const L of Object.values(W.marks||{})){
      const kind=['hub','market','gas'].includes(L.id)?'grocery':['com','bun','tra'].includes(L.id)?'cafe':'home';
      const b={x0:L.x0,x1:L.x1,y0:L.y1-8,y1:L.y1,h:L.look?.h||7,col:L.look?.col,awn:L.look?.awn};
      add((b.x0+b.x1)/2,(b.y0+b.y1)/2,'building',b,kind);
    }
    for(const t of W.trees||[])add(t.x,t.y,'tree',t);
    for(const l of W.lamps||[])add(l.x,l.y,'lamp',l);
    for(const L of W.lights||[]){add(L.x,L.y,'signal',L,1);add(L.x2,L.y2,'signal',L,2);}
    for(const p of W.props||[])add((p.x0+p.x1)/2,(p.y0+p.y1)/2,'planter',p);
    for(const p of state.npcs||[])add(p.x,p.y,'scooter',p);
    for(const p of state.peds||[])add(p.x,p.y,'person',p);
    for(const sign of o.signs||[]){
      const L=W.marks?.[sign.node];if(!L||sign.kind!=='works')continue;
      const point={x:L.gate.x+(L.gate.east?-10:10),y:L.gate.y+HW-1.2};add(point.x,point.y,'works',point);
    }
    if(T&&T.id!==state.at)add(T.gate.x,T.gate.y-HW-1.6,'customer',{x:T.gate.x,y:T.gate.y-HW-1.6,col:'#d69a72'});
    add(state.x,state.y,'rider',state);
    const axis=Math.abs(Math.cos(state.a))>Math.abs(Math.sin(state.a))?'x':'y';
    items.sort((a,b)=>a.depth-b.depth);
    for(const item of items){
      const p=item.value;
      switch(item.kind){
        case 'building':drawBuilding(c,p,camera,item.extra,state);break;
        case 'tree':drawTree(c,p,camera);break;
        case 'lamp':drawLamp(c,p,camera);break;
        case 'signal':drawSignal(c,p,item.extra,camera,axis,now);break;
        case 'scooter':drawScooter(c,p,camera);break;
        case 'rider':drawScooter(c,p,camera,true,o.look,o.player?.gender);break;
        case 'person':drawPerson(c,p,camera);break;
        case 'customer':drawPerson(c,p,camera,true);break;
        case 'works':{const q=isoProject(p.x,p.y,0,camera);paper(c,q.x-2.3*k,q.y-1.9*k,4.6*k,.75*k,'#dca176');line(c,{x:q.x-1.6*k,y:q.y-1.2*k},{x:q.x-1.6*k,y:q.y},INK,1.5);line(c,{x:q.x+1.6*k,y:q.y-1.2*k},{x:q.x+1.6*k,y:q.y},INK,1.5);break;}
        case 'planter':groundRect(c,camera,p.x0,p.y0,p.x1,p.y1,'#b98260',INK);{const q=isoProject(item.x,item.y,.6,camera);ellipse(c,q.x,q.y,k,k*.4,'#8aa46b',INK);}break;
      }
    }
    // Weather is a quiet tint; an idle town has no rain loop or pulsing scenery.
    if(o.weather==='rain'){c.fillStyle='#7898ac16';c.fillRect(0,0,w,h);}
  }
  function draw(c,state,W,o={},now=0){
    visibleStamps.clear();visibleGround.clear();
    const w=state.w,h=state.h,camera=isoCamera(state,w,h);c.imageSmoothingEnabled=true;
    drawScene(c,state,W,o,now,camera);
    destinationBadge(c,state,W.marks?.[o.target],camera,w,h);dash(c,state,o,w,h);
    const p=isoProject(state.x,state.y,0,camera);c.font='700 10px "Be Vietnam Pro",system-ui';c.textAlign='center';c.textBaseline='middle';paper(c,p.x-18,p.y+26,36,17);c.fillStyle=INK;c.fillText(tr('Bạn'),p.x,p.y+35);
    trimCache(stamps,visibleStamps,160);trimCache(groundCache,visibleGround,12);
    return camera;
  }
  return {draw,stats:()=>({groundBuilds,groundChunks:groundCache.size,stampBuilds,stamps:stamps.size,images:images.size}),invalidate:()=>{groundCache.clear();},dispose:()=>{disposed=true;groundCache.clear();stamps.clear();visibleStamps.clear();visibleGround.clear();for(const record of images.values()){record.image.onload=null;record.image.onerror=null;}images.clear();}};
}
