/** The garden is a view of farm_walk's existing metre coordinates and server data.
 * Fixed 2:1 camera, no commands and no animation loop. Small floor chunks and static
 * prop/bed stamps are bounded caches; movement only translates the finished art. */
import {getCharacterStamp,preloadIllustratedCharacters} from '../isometric/character-art.js';
import {t as tr} from '../v4/i18n.js';

const INK='#76583e',CREAM='#fff5dc',WOOD='#c29963',LEAF='#6d9a48';
const FONT='"Trebuchet MS", "Segoe UI", sans-serif';
const SOURCES={tree:'/icons/isometric/tree.webp',home:'/icons/isometric/home.webp'};
// This finite farm and its surrounding trees occupy twenty 16 m chunks at most.
// Keep the whole working set plus four recently used chunks from a prior scale/weather.
const GROUND_LIMIT=24,GROUND_BOUNDS={x0:-2,x1:1,z0:-2,z1:2};
export const farmObstacleBounds={pen:[-7,15.6,-3.6,19],hay:[11.4,1.3,12.8,2.7]};
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
export function farmProject(x,y,z,camera){const dx=x-camera.x,dz=z-camera.z,k=camera.scale;return {x:camera.cx+(dx+dz)*k,y:camera.cy+(dx-dz)*k*.5-y*k};}
export function farmUnproject(x,y,camera){const dx=(x-camera.cx)/camera.scale,dy=(y-camera.cy)/camera.scale;return {x:camera.x+dx*.5+dy,z:camera.z+dx*.5-dy};}
export function farmCamera(me,w,h){return {x:me.x-2.4,z:me.z+2.4,scale:Math.round(clamp(w/28,15,23)*2)/2,cx:w*.5,cy:h*.56};}
export const farmDepth=point=>point.x-point.z;
/** Invert screen input before normalising: diagonals point to their actual screen corner. */
export function farmMovement(right,down,speed){const strength=Math.min(1,Math.hypot(right,down));if(strength<.01)return {x:0,z:0};const x=right*.5+down,z=right*.5-down,k=speed*strength/(Math.hypot(x,z)||1);return {x:x*k,z:z*k};}
export function farmDirection(yaw=0){return ['ne','se','sw','nw'][((Math.round(yaw/(Math.PI/2))%4)+4)%4];}
export function pickFarmSpot(px,py,camera,spots){
  let best=null,score=Infinity;
  for(const [id,s] of Object.entries(spots)){
    const height=/^P[1-6]$/.test(id)?.32:0,p=farmUnproject(px,py+height*camera.scale,camera);
    const dx=Math.max(s[0]-p.x,0,p.x-s[2]),dz=Math.max(s[1]-p.z,0,p.z-s[3]);
    const center=farmProject((s[0]+s[2])*.5,height,(s[1]+s[3])*.5,camera),distance=Math.hypot(px-center.x,py-center.y);
    const inside=dx===0&&dz===0;
    // A small touch margin remains tied to the actual ground footprint, never a neighbour's billboard.
    if(!inside&&(Math.hypot(dx,dz)>.7||distance>28))continue;
    const rank=(inside?0:1000)+distance;if(rank<score){best=id;score=rank;}
  }
  return best;
}
export function needsFarmFrames(state){return !!(state.joy||state.look||state.keys?.size||state.auto||state.ride||state.fx?.length||state.hint||(state.me?.moving||0)>.01);}
/** Ignore server clock/countdown ticks that do not change anything painted in the garden. */
export function farmVisualKey(x){const d=x.room?.data||{},order=x.room?.tasks?.find(t=>t.id===x.ui?.fvTask);return JSON.stringify([d.plots,d.coop,d.weather?.id,d.nopump,d.bees,d.cold,order&&[order.id,order.known,order.crate,order.label],x.ui?.fvTarget,x.ui?.fvNear,x.state?.wardrobe,x.state?.wardrobe_plus,x.state?.journey?.gender]);}

function surface(w,h){if(typeof OffscreenCanvas!=='undefined')return new OffscreenCanvas(w,h);const cv=document.createElement('canvas');cv.width=w;cv.height=h;return cv;}
function polygon(c,points,fill,stroke=null,width=1){c.beginPath();points.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.closePath();if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=width;c.stroke();}}
function line(c,a,b,col,width=1){c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.strokeStyle=col;c.lineWidth=width;c.lineCap='round';c.stroke();}
function ellipse(c,x,y,rx,ry,col,stroke=null){c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=col;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=.8;c.stroke();}}
function rect(c,x,y,w,h,col,stroke=null,r=3){c.beginPath();c.roundRect(x,y,w,h,r);c.fillStyle=col;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=.8;c.stroke();}}
function ground(c,V,x0,z0,x1,z1,col,stroke=null,y=0){polygon(c,[[x0,z0],[x1,z0],[x1,z1],[x0,z1]].map(([x,z])=>farmProject(x,y,z,V)),col,stroke);}
function cuboid(c,V,x0,z0,x1,z1,h,top,front,side,y=0){
  const p=(x,z,up)=>farmProject(x,up,z,V);
  polygon(c,[p(x0,z0,y),p(x1,z0,y),p(x1,z0,h+y),p(x0,z0,h+y)],front,INK,.7);
  polygon(c,[p(x1,z0,y),p(x1,z1,y),p(x1,z1,h+y),p(x1,z0,h+y)],side,INK,.7);
  ground(c,V,x0,z0,x1,z1,top,INK,h+y);
}
function label(c,x,y,text,color=INK){c.font=`700 11px ${FONT}`;const w=c.measureText(text).width+14;rect(c,x-w/2,y-9,w,19,CREAM,'#b8966e',5);c.textAlign='center';c.textBaseline='middle';c.fillStyle=color;c.fillText(text,x,y+1);}

export function createFarmRenderer({createCanvas=surface,ImageClass=globalThis.Image,characterStamp=getCharacterStamp,preloadCharacters=preloadIllustratedCharacters,onAsset=()=>{}}={}){
  const stamps=new Map(),groundCache=new Map(),images=new Map(),avatars=new Map();let disposed=false,groundBuilds=0,preloaded=false;
  const remember=(cache,key,value,max)=>{cache.set(key,value);while(cache.size>max)cache.delete(cache.keys().next().value);return value;};
  const assetReady=()=>{if(disposed)return;stamps.clear();avatars.clear();onAsset();};
  function imageFor(kind){
    if(!ImageClass||!SOURCES[kind])return null;
    let record=images.get(kind);if(record)return record;
    const img=new ImageClass();record={img,ready:false};images.set(kind,record);
    img.onload=()=>{if(disposed)return;record.ready=true;assetReady();};img.onerror=()=>{};
    img.src=globalThis.__mnlBoot?.asset?.(SOURCES[kind])||SOURCES[kind];return record;
  }
  function stamp(key,w,h,paint){if(stamps.has(key))return stamps.get(key);const cv=createCanvas(Math.ceil(w),Math.ceil(h)),c=cv.getContext('2d');c.imageSmoothingEnabled=true;paint(c,cv.width,cv.height);return remember(stamps,key,{cv,w:cv.width,h:cv.height},96);}
  function chunk(k,ix,iz,weather){
    const key=[k,ix,iz,weather].join(':');if(groundCache.has(key))return groundCache.get(key);
    const size=16,x0=ix*size,z0=iz*size,w=Math.ceil(size*2*k+4),h=Math.ceil(size*k+4),cv=createCanvas(w,h),c=cv.getContext('2d');
    const V={x:x0,z:z0,scale:k,cx:2,cy:size*k*.5+2};
    const grass=weather==='rain'?'#a6bc82':weather==='hot'?'#c6cf8b':'#b8ce8e';
    ground(c,V,x0,z0,x0+size,z0+size,grass);c.save();ground(c,V,x0,z0,x0+size,z0+size,null);c.clip();
    ground(c,V,-13.3,-5.3,13.3,25.3,'#b4c982','#91af69');
    // Fixed tufts, light meadow patches and soil paths are painted once per chunk/weather.
    for(let x=x0;x<x0+size;x+=1.7)for(let z=z0;z<z0+size;z+=1.8){const seed=Math.abs(Math.sin(x*13.7+z*31.3));const p=farmProject(x,0,z,V);ellipse(c,p.x,p.y,k*.23,k*.12,seed>.5?'#d1dfa044':'#8caa6533');if(seed>.7){line(c,p,{x:p.x-2,y:p.y-3},'#8faa62',.8);line(c,p,{x:p.x+2,y:p.y-4},'#98b56b',.8);}}
    ground(c,V,-7.55,6.45,7.55,14.35,'#d8c292','#bba478');
    const paths=[[-1.25,-16,1.25,24],[-13,3.1,13,4.9],[-7.9,9.7,9.3,10.7],[-12.8,-2,-4,2.5],[-12,14.6,12,15.7],[4,-5.2,12.5,-1.8]];
    for(const [a,b,d,e] of paths){ground(c,V,a,b,d,e,'#bda57a');ground(c,V,a+.12,b+.12,d-.12,e-.12,'#e5d2a7');}
    for(let i=0;i<45;i++){const x=x0+((i*47)%157)/10,z=z0+((i*71)%157)/10;const onPath=paths.some(([a,b,d,e])=>x>a&&x<d&&z>b&&z<e);if(!onPath)continue;const p=farmProject(x,.01,z,V);ellipse(c,p.x,p.y,k*.09,k*.04,'#a58d6335');}
    for(let z=0;z<24;z+=2.4){const p=farmProject(-1.4,0,z,V);ellipse(c,p.x,p.y,k*.24,k*.13,'#9fae7333');}
    c.restore();groundBuilds++;return remember(groundCache,key,{cv,x:x0,z:z0,ox:V.cx,oy:V.cy},GROUND_LIMIT);
  }
  function floor(c,state,V,weather){
    c.fillStyle=weather==='rain'?'#a6bc82':'#b8ce8e';c.fillRect(0,0,state.w,state.h);
    const corners=[[0,0],[state.w,0],[state.w,state.h],[0,state.h]].map(([x,y])=>farmUnproject(x,y,V));
    const x0=Math.max(GROUND_BOUNDS.x0,Math.floor(Math.min(...corners.map(p=>p.x))/16)),x1=Math.min(GROUND_BOUNDS.x1,Math.floor(Math.max(...corners.map(p=>p.x))/16)),z0=Math.max(GROUND_BOUNDS.z0,Math.floor(Math.min(...corners.map(p=>p.z))/16)),z1=Math.min(GROUND_BOUNDS.z1,Math.floor(Math.max(...corners.map(p=>p.z))/16));
    for(let x=x0;x<=x1;x++)for(let z=z0;z<=z1;z++){const tile=chunk(V.scale,x,z,weather),p=farmProject(tile.x,0,tile.z,V);c.drawImage(tile.cv,Math.round(p.x-tile.ox),Math.round(p.y-tile.oy));}
  }
  function leaf(c,x,y,size,angle,color){c.save();c.translate(x,y);c.rotate(angle);ellipse(c,0,-size*.5,size*.39,size*.65,color,'#486c384d');line(c,{x:0,y:0},{x:0,y:-size*.92},'#e1e6a977',.65);c.restore();}
  function crop(c,x,y,k,id,stage,thirst,seed){
    const size={sprout:.3,young:.62,almost:.86,ripe:1,over:1.03,rotten:.62}[stage]||.7,scale=k*size;
    const brown=stage==='rotten',mature=['almost','ripe','over'].includes(stage),green=brown?'#947149':thirst?'#929d51':LEAF;
    ellipse(c,x,y,scale*.5,scale*.2,'#3e301d26');
    if(id==='tomato'||id==='cucumber'){
      line(c,{x:x+scale*.15,y:y+2},{x:x+scale*.15,y:y-k*1.6},'#c5aa70',Math.max(1,k*.055));
      line(c,{x,y},{x:x+(thirst?scale*.23:0),y:y-scale*1.45},green,Math.max(1.4,k*.08));
      for(let i=0;i<5;i++){const side=i%2?1:-1,yy=y-scale*(.35+i*.23),xx=x+side*scale*.35;line(c,{x,y:yy+scale*.12},{x:xx,y:yy},green,1.1);leaf(c,xx,yy,scale*.48,side*.9,green);}
      if(mature)for(let i=0;i<3;i++){const xx=x+((i+seed)%2?-.31:.35)*scale,yy=y-scale*(.38+i*.4);if(id==='tomato'){ellipse(c,xx,yy,scale*.19,scale*.19,stage==='almost'?'#e6a64a':'#dc6750','#a34e37');ellipse(c,xx-scale*.055,yy-scale*.06,scale*.055,scale*.04,'#f8c382');}else{c.save();c.translate(xx,yy);c.rotate(.2);rect(c,-scale*.11,-scale*.21,scale*.22,scale*.49,'#589146','#436f36',scale*.1);line(c,{x:scale*.01,y:-scale*.12},{x:scale*.01,y:scale*.2},'#a4c476',.7);c.restore();}}
    }else if(id==='carrot'){
      if(mature){polygon(c,[{x:x-scale*.18,y:y-scale*.18},{x:x+scale*.18,y:y-scale*.18},{x:x+scale*.08,y:y+scale*.15},{x:x-scale*.1,y:y+scale*.23}],'#e99a43','#ba7439');}
      for(let i=0;i<5;i++)leaf(c,x,y-scale*.15,scale*(.65+(i%2)*.18),(i-2)*.48,green);
    }else{
      for(let i=0;i<7;i++)leaf(c,x+Math.sin(i)*scale*.22,y-Math.cos(i)*scale*.06,scale*(.55+(i%3)*.08),i*.87,green);
      ellipse(c,x,y-scale*.4,scale*.27,scale*.3,brown?'#b99865':id==='cabbage'?'#c0d58c':'#a1c574','#6a984d');
      if(!brown)for(let i=0;i<3;i++)leaf(c,x+(i-1)*scale*.1,y-scale*.31,scale*.34,(i-1)*.6,'#c3d98b');
    }
  }
  function bedStamp(plot,k,moisture){
    const stage=plot.stage||(plot.crop?'young':'empty'),m=moisture||{},wet=plot.moisture>(m.high??80),dry=plot.moisture<(m.low??40);
    const key=['bed',k,plot.crop,stage,wet,dry,plot.weeds||0,plot.seen||0,plot.scouted_today,plot.compost,plot.safe_in||0].join(':');
    return stamp(key,k*5.3+8,k*5.2+16,(c,w,h)=>{
      const V={x:0,z:0,scale:k,cx:w/2,cy:h-k*1.4},p=(x,y,z)=>farmProject(x,y,z,V);
      ground(c,V,-1.72,-.92,1.72,.92,'#493e2433');
      cuboid(c,V,-1.6,-.8,1.6,.8,.32,wet?'#79583c':dry?'#b08a58':'#947044','#ad8150','#956b43');
      for(const z of [-.8,.8])cuboid(c,V,-1.67,z-.065,1.67,z+.065,.36,'#d7b279','#c7a16b','#a97f50');
      for(const x of [-1.6,1.6])cuboid(c,V,x-.065,-.85,x+.065,.85,.36,'#d7b279','#c7a16b','#a97f50');
      for(const x of [-1.15,-.4,.4,1.15])line(c,p(x,.325,-.65),p(x,.325,.65),'#66492f66',Math.max(1,k*.07));
      for(let i=0;i<14;i++){const q=p(-1.35+(i*7%27)/10,.335,-.62+(i*3%12)/10);ellipse(c,q.x,q.y,k*.032,k*.018,plot.compost?'#513c29':'#c0a078');}
      for(const x of [-1.5,1.5]){const q=p(x,.22,-.865);ellipse(c,q.x,q.y,1,1,'#6c563e');}
      const plants=[];
      if(plot.crop){const tall=['tomato','cucumber'].includes(plot.crop);for(let i=0;i<3;i++)for(let j=0;j<(tall?1:2);j++)plants.push({x:-1.02+i*1.02,z:tall?0:j*.65-.325,seed:i*3+j});}
      plants.sort((a,b)=>farmDepth(a)-farmDepth(b));
      for(const plant of plants){const q=p(plant.x,.36,plant.z);crop(c,q.x,q.y,k,plot.crop,stage,dry,plant.seed);}
      for(let i=0;i<(plot.weeds||0);i++){const q=p(-1.2+i*.9,.34,-.56);for(let j=0;j<3;j++)line(c,q,{x:q.x+(j-1)*3,y:q.y-6},'#9bab4f',1.2);}
      if(plot.scouted_today&&plot.seen){const q=p(.95,.55,-.35);for(let i=0;i<3;i++)ellipse(c,q.x+i*2,q.y,2.1,1.8,'#b3c55f','#698445');}
      if(wet){const q=p(.5,.34,.5);ellipse(c,q.x,q.y,k*.26,k*.09,'#a0bfbd88');}
    });
  }
  function bed(c,plot,position,V,options){const k=V.scale,s=bedStamp(plot,k,options.moisture),p=farmProject(position[0],0,position[1],V);c.drawImage(s.cv,p.x-s.w/2,p.y-s.h+k*1.4);}
  function tree(c,t,V){
    const k=V.scale,s=t.s||1,asset=imageFor('tree');
    const art=stamp(`tree:${k}:${s.toFixed(2)}:${asset?.ready}`,k*s*5.7,k*s*6.4,(g,w,h)=>{
      if(asset?.ready){g.drawImage(asset.img,0,0,w,h);return;}
      ellipse(g,w*.5,h-4,w*.32,k*.38,'#4c66352a');rect(g,w*.47,h-k*2,k*.25,k*1.8,'#a27c4d');
      for(let i=0;i<16;i++){const a=i*2.4,x=w*.5+Math.sin(a)*w*.25,y=h*.38+Math.cos(a)*h*.21;ellipse(g,x,y,w*.23,h*.19,i%3?'#8aaa5d':'#afc878','#6d8a4c66');}
    });
    const p=farmProject(t.x,0,t.z,V);c.drawImage(art.cv,p.x-art.w*.5,p.y-art.h+3);
  }
  function building(c,kind,x,z,V){
    const k=V.scale,asset=kind==='home'?imageFor('home'):null;
    const art=stamp(`building:${kind}:${k}:${asset?.ready}`,k*10+10,k*8+10,(g,w,h)=>{
      if(asset?.ready){g.drawImage(asset.img,w*.1,0,w*.8,h);return;}
      const C={x:0,z:0,scale:k,cx:w/2,cy:h-k*2.1},p=(x,y,z)=>farmProject(x,y,z,C),cold=kind==='cold';
      ground(g,C,-2.4,-1.65,2.5,1.7,'#6c603432');
      cuboid(g,C,-2,-1.3,2,1.3,cold?2.5:2.3,cold?'#e3e5ca':'#eac993',cold?'#f3efce':'#f2d9aa',cold?'#c2d1c3':'#d9b987');
      for(let y=.25;y<2.2;y+=.24)line(g,p(-2,y,-1.305),p(2,y,-1.305),cold?'#c9d5c7':'#d6b88a',.7);
      polygon(g,[p(-.9,0,-1.32),p(.9,0,-1.32),p(.9,1.8,-1.32),p(-.9,1.8,-1.32)],cold?'#83b3b2':'#a6ae69',INK);
      line(g,p(0,0,-1.34),p(0,1.8,-1.34),cold?'#567e81':'#768149',1);
      line(g,p(-.8,.2,-1.34),p(.8,1.6,-1.34),cold?'#b9d6cf':'#ded7a0',2);
      polygon(g,[p(2.01,1,0),p(2.01,1,1),p(2.01,1.9,1),p(2.01,1.9,0)],'#93b6a9',INK,.8);
      line(g,p(2.02,1.45,0),p(2.02,1.45,1),'#e6e0b7',1.5);
      if(cold)cuboid(g,C,-2.2,-1.5,2.2,1.5,.18,'#bec8b2','#a9b6a5','#8c9f91',2.5);
      else{
        polygon(g,[p(-2.3,2.3,-1.6),p(2.3,2.3,-1.6),p(2.3,3.55,0),p(-2.3,3.55,0)],'#ce7955',INK);
        polygon(g,[p(2.3,2.3,-1.6),p(2.3,2.3,1.6),p(2.3,3.55,0)],'#a65d43',INK);
        polygon(g,[p(-2.3,3.55,0),p(2.3,3.55,0),p(2.3,2.3,1.6),p(-2.3,2.3,1.6)],'#db9063',INK);
        for(let x=-2.1;x<=2.2;x+=.4){line(g,p(x,2.32,-1.6),p(x,3.57,0),'#efbb82',1.1);line(g,p(x,3.57,0),p(x,2.32,1.6),'#b76e4d',.85);}
        for(let j=1;j<=3;j++){const t=j/4;line(g,p(-2.3,2.3+1.25*t,-1.6+1.6*t),p(2.3,2.3+1.25*t,-1.6+1.6*t),'#ad6045',.7);}
      }
      if(kind==='coop'){cuboid(g,C,-1.85,-1.7,-.9,-1.32,.6,'#dfbf75','#c29d5d','#a6814d',.45);const q=p(-1.4,1.1,-1.72);ellipse(g,q.x,q.y,4,2.5,'#fff2c5');}
      for(const x of [-1.6,1.6]){const q=p(x,0,-1.6);rect(g,q.x-3,q.y-5,6,5,'#bb8356');for(let j=0;j<3;j++)leaf(g,q.x,q.y-4,7,(j-1)*.6,'#8da75c');}
    });
    const p=farmProject(x,0,z,V);c.drawImage(art.cv,p.x-art.w/2,p.y-art.h+(kind==='home'?k*.6:k*2.1));
  }
  function fence(c,x,z,V,axis='x',length=2.2){const k=V.scale,C=farmProject(x,0,z,V);const key=`fence:${k}:${axis}:${length}`;const art=stamp(key,k*(length+1.2),k*(length*.5+1.6),(g,w,h)=>{const camera={x:x,z:z,scale:k,cx:k*.5,cy:h-k*.25},p=(a,y,b)=>farmProject(a,y,b,camera),ex=x+(axis==='x'?length:0),ez=z+(axis==='z'?length:0);for(const h of [.38,.74])line(g,p(x,h,z),p(ex,h,ez),'#dbc79a',Math.max(2,k*.095));line(g,p(x,.04,z),p(x,.98,z),'#b49464',Math.max(3,k*.15));line(g,p(x,.93,z),p(x,1.03,z),'#f0dbb0',Math.max(3,k*.17));});c.drawImage(art.cv,C.x-k*.5,C.y-art.h+k*.25);}
  function utility(c,kind,V,data,order){
    const hay=farmObstacleBounds.hay,k=V.scale,pos={tank:[9.5,9],well:[9.5,6.4],pack:[-7.6,0],bike:[-5,-2],truck:[9.1,-3.4],board:[2.8,-4.2],hay:[(hay[0]+hay[2])/2,(hay[1]+hay[3])/2]}[kind],p=farmProject(pos[0],0,pos[1],V);
    const contents=kind==='pack'&&order?.known?order.crate||[]:[];
    const art=stamp(`utility:${kind}:${k}:${kind==='tank'?!!data.nopump:kind==='pack'?JSON.stringify([contents,order?.label]):''}`,k*6.2,k*4.4,(g,w,h)=>{
      const x=w/2,y=h-k*.6,C={x:0,z:0,scale:k,cx:x,cy:y},q=(a,b,d)=>farmProject(a,b,d,C);
      ellipse(g,x,y,k*(kind==='truck'?2.3:1),k*.38,'#5d542d22');
      if(kind==='tank'){for(const a of [-.4,.4])line(g,{x:x+a*k,y},{x:x+a*k,y:y-k*1.8},'#8a9b87',2.3);rect(g,x-k*.58,y-k*2.7,k*1.16,k*1.45,'#9dbdb1',INK,k*.2);ellipse(g,x,y-k*2.7,k*.58,k*.17,'#cfdfc3',INK);for(let i=0;i<4;i++)line(g,{x:x-k*.55,y:y-k*(1.35+i*.29)},{x:x+k*.55,y:y-k*(1.35+i*.29)},'#769b8e',1);line(g,{x:x+k*.4,y:y-k*1.3},{x:x+k*.8,y:y-k*.75},'#73968c',3);ellipse(g,x+k*.8,y-k*.72,3,2,data.nopump?'#b17958':'#83bdbb');}
      else if(kind==='well'){rect(g,x-k*.7,y-k*.5,k*1.4,k*.55,'#b4b5a0',INK,k*.2);ellipse(g,x,y-k*.5,k*.7,k*.23,'#ddd1a8',INK);ellipse(g,x,y-k*.52,k*.53,k*.14,'#7ca3a1');for(const a of [-.8,.8])line(g,{x:x+a*k,y:y-k*.4},{x:x+a*k,y:y-k*1.7},'#aa8755',2.5);line(g,{x:x-k*.85,y:y-k*1.7},{x:x+k*.85,y:y-k*1.7},WOOD,3);line(g,{x,y:y-k*1.7},{x,y:y-k*.6},'#a49164',1);}
      else if(kind==='pack'){for(const a of [-.85,.85])for(const b of [-.4,.4])line(g,q(a,0,b),q(a,.8,b),'#a47d4c',k*.12);cuboid(g,C,-1,-.55,1,.55,.15,'#e4c18a','#bb945d','#ad8657',.8);cuboid(g,C,-.55,-.35,.45,.35,.38,'#937747','#cda86c','#b99359',.95);let n=0;for(const item of contents)for(let j=0;j<Math.min(3,item.qty)&&n<6;j++,n++){const b=q((n%3)*.26-.35,1.35,Math.floor(n/3)*.2-.1);if(item.crop==='egg'||item.crop==='tomato')ellipse(g,b.x,b.y,k*.13,k*.16,item.crop==='egg'?CREAM:'#d77452',INK);else leaf(g,b.x,b.y,k*.36,(n%3-1)*.7,LEAF);}if(order?.label){const b=q(-.12,1.2,-.36);rect(g,b.x-4,b.y-2,8,4,order.label==='organic'?'#b2c984':CREAM);}}
      else if(kind==='bike'){for(const dx of [-.85,.85]){ellipse(g,x+dx*k,y-k*.12,k*.33,k*.35,'#596257',INK);ellipse(g,x+dx*k,y-k*.12,k*.18,k*.2,'#d9d4b5');}line(g,{x:x-k*.8,y:y-k*.4},{x:x+k*.55,y:y-k*.9},'#92ac92',k*.3);line(g,{x:x+k*.85,y:y-k*.22},{x:x+k*.45,y:y-k*1.25},'#73947d',k*.15);rect(g,x-k*.7,y-k*.95,k*.9,k*.18,'#745e43');line(g,{x:x+k*.25,y:y-k*1.3},{x:x+k*.7,y:y-k*1.3},INK,2);cuboid(g,C,-1.05,-.25,-.4,.3,.55,'#e6c97e','#bf9558','#aa824b',.6);}
      else if(kind==='truck'){for(const a of [-1.5,1.3]){const b=q(a,.2,-.9);ellipse(g,b.x,b.y,k*.32,k*.36,'#596154',INK);ellipse(g,b.x,b.y,k*.14,k*.17,'#c8cab0');}cuboid(g,C,-2,-.8,-.6,.8,1.35,'#b2c7bb','#8aa99b','#719487',.35);polygon(g,[q(-2.01,1.02,-.55),q(-2.01,1.02,.55),q(-2.01,1.54,.55),q(-2.01,1.54,-.55)],'#d9e9d6',INK);cuboid(g,C,-.6,-.8,2,.8,.45,'#a6ba9e','#759481','#6a8775',.35);for(const a of [-.3,.65,1.5])cuboid(g,C,a-.35,-.5,a+.35,.5,.45,'#a5bd70','#c4a164','#af8c55',.8);}
      else if(kind==='hay'){const a=(hay[2]-hay[0])/2,b=(hay[3]-hay[1])/2;cuboid(g,C,-a,-b,a,b,.9,'#eed593','#d7b471','#bc974f');for(let y=.12;y<.9;y+=.15){line(g,q(-a,y,-b-.01),q(a,y,-b-.01),'#f3d48c',1);line(g,q(a+.01,y,-b),q(a+.01,y,b),'#d9b56e',1);}for(const x of [-a*.48,a*.48]){line(g,q(x,.02,-b-.015),q(x,.92,-b-.015),'#a48750',1.6);line(g,q(x,.92,-b-.015),q(x,.92,b),'#b9995b',1.6);}for(let i=0;i<8;i++)line(g,q(-a+i*.18,.915,-b),q(-a+i*.18+.07,.915,b),'#dfbc77',.7);}
      else{line(g,{x,y},{x,y:y-k*1.6},WOOD,k*.12);rect(g,x-k*.6,y-k*2,k*1.2,k*.8,'#dfc590',INK);ellipse(g,x-k*.22,y-k*1.7,k*.13,k*.13,'#e8b857');line(g,{x:x-k*.1,y:y-k*1.8},{x:x+k*.35,y:y-k*1.8},'#9d8f64',1);line(g,{x:x-k*.1,y:y-k*1.55},{x:x+k*.35,y:y-k*1.55},'#9d8f64',1);}
    });c.drawImage(art.cv,p.x-art.w/2,p.y-art.h+k*.6);
  }
  function avatar(c,state,V,options){
    const me=state.me,p=farmProject(me.x,0,me.z,V),direction=farmDirection(me.yaw),key=JSON.stringify([options.look,options.gender,direction,options.uniformColor]);
    let art=avatars.get(key);if(!art){art=characterStamp({look:options.look,gender:options.gender,direction,walkFrame:0,uniformColor:options.uniformColor,onReady:assetReady});remember(avatars,key,art,16);}
    const h=V.scale*3.6,w=h*art.width/art.height;
    ellipse(c,p.x,p.y,V.scale*.5,V.scale*.23,'#53633230');c.drawImage(art.canvas,p.x-w/2,p.y-h+2,w,h);
    const tool=options.tool;if(tool){const x=p.x+w*.29,y=p.y-h*.3,k=V.scale;if(tool==='can'){rect(c,x,y,k*.5,k*.42,'#8eaf9a',INK,k*.1);line(c,{x:x+k*.45,y:y+k*.1},{x:x+k*.83,y:y-k*.15},'#84a78e',k*.1);ellipse(c,x+k*.84,y-k*.16,k*.1,k*.06,'#c2d2b2');}else if(tool==='basket'){rect(c,x,y,k*.56,k*.36,'#c9a16a',INK,k*.1);line(c,{x,y:y+k*.1},{x:x+k*.55,y:y+k*.1},'#e7c88c',1);}else if(tool==='hoe'){line(c,{x,y:y+k*.3},{x:x+k*.25,y:y-k*.7},WOOD,k*.07);line(c,{x:x+k*.12,y:y-k*.68},{x:x+k*.48,y:y-k*.52},'#8c9b88',k*.16);}else{rect(c,x,y,k*.4,k*.5,'#e6cf8e',INK);leaf(c,x+k*.2,y+k*.27,k*.16,.3,LEAF);}}
  }
  function chicken(c,hen,V){const p=farmProject(hen.x,0,hen.z,V),k=V.scale;ellipse(c,p.x,p.y,k*.27,k*.12,'#6c603422');ellipse(c,p.x,p.y-k*.28,k*.26,k*.25,CREAM,'#aa8d66');ellipse(c,p.x+k*.2,p.y-k*.5,k*.14,k*.17,'#fff8df','#aa8d66');ellipse(c,p.x+k*.19,p.y-k*.66,k*.07,k*.05,'#cf795c');polygon(c,[{x:p.x+k*.32,y:p.y-k*.53},{x:p.x+k*.45,y:p.y-k*.47},{x:p.x+k*.32,y:p.y-k*.43}],'#e2b466');ellipse(c,p.x+k*.24,p.y-k*.54,1,1,INK);}
  function badges(c,state,world,V,options){
    for(const plot of options.data.plots||[]){const b=world.beds[plot.id];if(!b)continue;const p=farmProject(b[0],.1,b[1]-.95,V);if(p.x<-50||p.x>state.w+50||p.y<75||p.y>state.h)continue;
      const dry=plot.crop&&plot.moisture<(options.moisture?.low??40),ripe=['ripe','over'].includes(plot.stage),text=plot.id+(dry?' · 💧':ripe?' · 🧺':'');label(c,p.x,p.y+12,text,dry?'#658a92':ripe?'#5c813d':INK);
    }
    const target=state.near||options.target,s=world.spots[target];if(s){const x=(s[0]+s[2])*.5,z=(s[1]+s[3])*.5,p=farmProject(x,/^P/.test(target)?2.15:3,z,V);if(p.x>12&&p.x<state.w-12&&p.y>90&&p.y<state.h-25){const title=/^P/.test(target)?tr('Luống')+' '+target:tr({tank:'Bồn nước',coop:'Chuồng gà',shed:'Nhà kho',pack:'Bàn đóng hàng',bike:'Xe máy',truck:'Xe anh Tuấn',board:'Thời tiết'}[target]||target);label(c,p.x,p.y,title,'#537742');polygon(c,[{x:p.x-4,y:p.y+11},{x:p.x+4,y:p.y+11},{x:p.x,y:p.y+17}],CREAM,'#b8966e');}}
  }
  function draw(c,state,world,options){
    if(disposed)return;
    if(!preloaded){preloaded=true;preloadCharacters(assetReady);}
    const V=farmCamera(state.me,state.w,state.h),data=options.data||{},weather=data.weather?.id||'sun',Q=[];c.imageSmoothingEnabled=true;
    floor(c,state,V,weather);
    const add=(x,z,paint,tall=100)=>{const p=farmProject(x,0,z,V);if(p.x<-160||p.x>state.w+160||p.y<-20||p.y>state.h+tall)return;Q.push({depth:x-z,paint});};
    for(const t of world.trees||[])add(t.x,t.z,()=>tree(c,t,V),200);
    add(0,32,()=>building(c,'home',0,32,V),220);
    add(-9,17.3,()=>building(c,'coop',-9,17.3,V));add(9.25,17.75,()=>building(c,'shed',9.25,17.75,V));add(-11.1,.2,()=>building(c,'cold',-11.1,.2,V));
    // Rails are sorted individually so the player can walk behind the front fence.
    for(const [x,z] of world.posts||[]){const edge=Math.abs(z+5.3)<.1||Math.abs(z-25.3)<.1;const len=edge?Math.min(2.2,13.3-x):Math.min(2.2,25.3-z);if(len>.1&&!(z<0&&x<1.8&&x+len>-1.8))add(x,z,()=>fence(c,x,z,V,edge?'x':'z',len));}
    const [px0,pz0,px1,pz1]=farmObstacleBounds.pen;
    for(const [x,z,axis,length] of [[px0,pz0,'x',px1-px0],[px0,pz1,'x',px1-px0],[px0,pz0,'z',pz1-pz0],[px1,pz0,'z',pz1-pz0]]){
      // Individual rails and their end posts sit on the exact solid run boundary.
      const pieces=Math.ceil(length/1.7);for(let i=0;i<pieces;i++){const offset=i*length/pieces,sx=x+(axis==='x'?offset:0),sz=z+(axis==='z'?offset:0);add(sx,sz,()=>fence(c,sx,sz,V,axis,length/pieces));}
    }
    for(const plot of data.plots||[]){const b=world.beds[plot.id];if(b)add(b[0],b[1],()=>bed(c,plot,b,V,options));}
    const hay=farmObstacleBounds.hay;
    for(const [kind,x,z] of [['tank',9.5,9],['well',9.5,6.4],['pack',-7.6,0],['bike',-5,-2],['truck',9.1,-3.4],['board',2.8,-4.2],['hay',(hay[0]+hay[2])/2,(hay[1]+hay[3])/2]])add(x,z,()=>utility(c,kind,V,data,options.order));
    for(const hen of state.hens||[])add(hen.x,hen.z,()=>chicken(c,hen,V));
    if(data.coop?.nest)add(-10,15.65,()=>{for(let i=0;i<Math.min(8,data.coop.nest);i++){const p=farmProject(-10.6+(i%4)*.22,.88,15.65+Math.floor(i/4)*.16,V);ellipse(c,p.x,p.y,V.scale*.075,V.scale*.1,i<(data.coop.stale||0)?'#dfcca0':CREAM,'#bbaa81');}});
    if(data.bees)add(1,10,()=>{for(let i=0;i<3;i++){const p=farmProject(i*1.2-1,1.3,9+i*.7,V);ellipse(c,p.x,p.y,3,2,'#d9b653',INK);ellipse(c,p.x,p.y-3,2.5,1.5,'#fff9df');}});
    add(state.me.x,state.me.z,()=>avatar(c,state,V,options));
    Q.sort((a,b)=>a.depth-b.depth);for(const item of Q)item.paint();
    badges(c,state,world,V,options);
    // Weather changes the garden palette and a quiet static veil, without idle particles.
    if(weather==='rain'){c.fillStyle='#809caa16';c.fillRect(0,0,state.w,state.h);for(let i=0;i<22;i++){const x=i*97%state.w,y=i*73%state.h;line(c,{x,y},{x:x-3,y:y+9},'#f4f7e866',1);}}
    if(weather==='hot'){c.fillStyle='#f4d68a10';c.fillRect(0,0,state.w,state.h);}
    return V;
  }
  return {draw,stats:()=>({stamps:stamps.size,groundChunks:groundCache.size,groundBuilds,images:images.size}),dispose(){disposed=true;stamps.clear();groundCache.clear();avatars.clear();for(const record of images.values())record.img.onload=record.img.onerror=null;images.clear();}};
}
