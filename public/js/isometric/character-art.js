/** Reference-matched chibi atlas: four views × idle/two walking poses, cached by saved wardrobe. */
import {defaultLook,art,figureOf,paintPlayer,paintTop,paintAcc,CANVAS,topColour,hairColour} from '../v4/look.js';

const WIDTH=120,HEIGHT=160,FOOT=156;
const atlases=new Map(),stamps=new Map(),MAX_STAMPS=160;
const cells={sw:0,se:1,nw:2,ne:3};
export const atlasCell=(direction,walkFrame=0)=>({x:cells[direction]??cells.se,y:Math.max(0,Math.min(2,Math.trunc(Number(walkFrame)||0)))});
const normalise=options=>{
  const gender=options.gender==='female'?'female':'male';
  const look={...defaultLook(gender),...options.look};
  const walkFrame=options.walkFrame??(options.step===1?1:options.step===3?2:0);
  return {gender,look,direction:Object.hasOwn(cells,options.direction)?options.direction:'se',walkFrame:atlasCell('se',walkFrame).y,uniformColor:options.uniformColor||''};
};
export function characterKey(options={}){const o=normalise(options);return JSON.stringify([o.gender,o.direction,o.walkFrame,o.look,o.uniformColor]);}
const rgb=hex=>{const s=hex.slice(1);return [0,2,4].map(i=>parseInt(s.slice(i,i+2),16));};
function tint(source,target,reference){
  const colour=rgb(target),light=(source[0]*.28+source[1]*.56+source[2]*.16)/reference;
  return colour.map(v=>Math.round(Math.min(255,Math.max(0,v*light))));
}
/** Palette masks distinguish fabric from warm skin. Preserve alpha, eyes, outlines and painted shading. */
export function recolourPixel(pixel,y,palette){
  const [r,g,b,a]=pixel;
  if(a<12||Math.max(r,g,b)<65)return [...pixel];
  let colour=null,reference=1;
  if(y<.58&&r>g*1.09&&g>b*1.08&&r<180){colour=palette.hair;reference=92;}
  else if(y<.79&&r>g*1.08&&g>b*1.08&&r>145&&b<225){colour=palette.skin;reference=211;}
  else if(y>.43&&y<.83&&r>115&&g>110&&b>85&&r-g<38&&g-b<46&&r>=b){colour=palette.top;reference=209;}
  else if(y>.56&&y<.91&&g>r*1.1&&b>r*1.05&&b<g*1.15){colour=palette.top;reference=100;}
  else if(y>.68&&y<.94&&b>r*1.08&&b>g*1.06){colour=palette.bottom;reference=98;}
  else if(y>.89&&r>g*1.08&&g>b*1.05){colour=palette.shoes;reference=98;}
  if(!colour||!/^#[0-9a-f]{6}$/i.test(colour))return [...pixel];
  return [...tint([r,g,b],colour,reference),a];
}
function remember(key,value){stamps.set(key,value);while(stamps.size>MAX_STAMPS)stamps.delete(stamps.keys().next().value);return value;}
function atlasFor(gender,onReady){
  let entry=atlases.get(gender);
  if(!entry){
    const img=new Image();entry={img,ready:false,failed:false,listeners:new Set(),views:new Map()};atlases.set(gender,entry);
    img.onload=()=>{for(const direction of Object.keys(cells))for(let frame=0;frame<3;frame++)extractView(entry,direction,frame);entry.scale=Math.min(108/Math.max(...[...entry.views.values()].map(v=>v.w)),148/Math.max(...[...entry.views.values()].map(v=>v.h)));entry.ready=true;stamps.clear();const callbacks=[...entry.listeners];entry.listeners.clear();callbacks.forEach(fn=>fn());};
    img.onerror=()=>{entry.failed=true;entry.listeners.clear();};
    const path=`/icons/cozy-v2/character-${gender}.webp`;
    img.src=globalThis.__mnlBoot?.asset?.(path)||path;
  }
  if(!entry.ready&&!entry.failed&&typeof onReady==='function')entry.listeners.add(onReady);
  return entry;
}
export function preloadIllustratedCharacters(onReady){if(typeof Image==='undefined')return;for(const gender of ['male','female'])atlasFor(gender,onReady);}
function extractView(entry,direction,walkFrame=0){
  const key=direction+walkFrame;if(entry.views.has(key))return entry.views.get(key);
  const cell=atlasCell(direction,walkFrame),w=Math.floor(entry.img.naturalWidth/4),h=Math.floor(entry.img.naturalHeight/3);
  const cv=document.createElement('canvas');cv.width=w;cv.height=h;
  const c=cv.getContext('2d',{willReadFrequently:true});c.drawImage(entry.img,cell.x*w,cell.y*h,w,h,0,0,w,h);
  const pixels=c.getImageData(0,0,w,h);let x0=w,y0=h,x1=0,y1=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(pixels.data[(y*w+x)*4+3]>24){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
  const view={cv,x:x0,y:y0,w:Math.max(1,x1-x0+1),h:Math.max(1,y1-y0+1)};entry.views.set(key,view);return view;
}
function fallback(canvas,o){const c=canvas.getContext('2d');c.translate(WIDTH/2,FOOT-3);c.scale(.9,.9);paintPlayer(c,figureOf(o.look,o.gender),CANVAS);}
function clothingDetails(c,o,box){
  const F=figureOf(o.look,o.gender),front=o.direction==='sw'||o.direction==='se';
  // Match the existing wardrobe item shapes while the illustrated base keeps its fabric shading.
  const cx=box.bodyX??box.x+box.w*.5,bodyY=box.bodyY??box.y+box.h*.8,foot=box.footY??FOOT,s=box.h/145;
  if(F.bottom.skirt||F.top.long){
    const x=box.w*.24,y=bodyY-box.h*.06,end=foot-(F.bottom.skirt==='long'?7:box.h*.13);
    const fill=c.createLinearGradient(cx-x,y,cx+x,end);fill.addColorStop(0,F.bottom.c);fill.addColorStop(1,'#6b493b');
    c.fillStyle=fill;c.strokeStyle='#684536';c.lineWidth=1;c.beginPath();c.moveTo(cx-x,y);c.lineTo(cx+x,y);c.lineTo(cx+x*1.4,end);c.quadraticCurveTo(cx,end+5,cx-x*1.4,end);c.closePath();c.fill();c.stroke();
  }
  if(front&&F.top.d&&F.top.d!=='collar'){
    c.save();c.translate(cx,bodyY+box.h*.07);c.scale(s*.64,s*.67);paintTop(c,F,CANVAS);c.restore();
  }
  if(o.look.acc!=='pk_khong'&&(front||['non_la','mu_len','no_toc','tui_cheo'].includes(o.look.acc))){
    const bag=o.look.acc==='tui_cheo',accessoryX=bag?cx:box.faceX??cx,accessoryY=!bag&&box.eyesY!==undefined?box.eyesY+78*s:foot;
    c.save();c.translate(accessoryX+(o.direction==='sw'?-3:3),accessoryY);c.scale(s*.82,s);paintAcc(c,F,CANVAS);c.restore();
  }
}
/** Shared saved-wardrobe silhouettes. Optional pose anchors move head items separately from the torso. */
export function paintWardrobeOverlay(c,options={},box,alignment={}){
  if(!c||typeof c.save!=='function'||!box||!['x','y','w','h'].every(key=>Number.isFinite(box[key]))||box.w<=0||box.h<=0)return false;
  const geometry={x:box.x,y:box.y,w:box.w,h:box.h};
  for(const key of ['bodyX','bodyY','faceX','eyesY','footY'])if(Number.isFinite(alignment?.[key]))geometry[key]=alignment[key];
  clothingDetails(c,normalise(options||{}),geometry);return true;
}
/** Feet at (60,160). onReady requests one texture refresh after the atlas finishes loading. */
export function getCharacterStamp(options={}){
  const o=normalise(options),key=characterKey(o),entry=atlasFor(o.gender,options.onReady);
  const hit=stamps.get(key);if(hit&&hit.ready===entry.ready)return hit;
  const canvas=document.createElement('canvas');canvas.width=WIDTH;canvas.height=HEIGHT;
  if(!entry.ready){fallback(canvas,o);return remember(key,{canvas,width:WIDTH,height:HEIGHT,ready:false});}
  const view=extractView(entry,o.direction,o.walkFrame),scale=entry.scale,w=Math.round(view.w*scale),h=Math.round(view.h*scale),x=Math.round((WIDTH-w)/2),y=FOOT-h;
  const c=canvas.getContext('2d',{willReadFrequently:true});c.drawImage(view.cv,view.x,view.y,view.w,view.h,x,y,w,h);
  const pixels=c.getImageData(x,y,w,h),palette={hair:hairColour(o.look),skin:art(o.look,'skin').c,top:o.look.uniform&&o.uniformColor?o.uniformColor:topColour(o.look,o.gender),bottom:art(o.look,'bottom').c,shoes:art(o.look,'shoes').c};
  for(let row=0;row<h;row++)for(let col=0;col<w;col++){const i=(row*w+col)*4,output=recolourPixel(Array.from(pixels.data.subarray(i,i+4)),row/h,palette);pixels.data.set(output,i);}
  c.putImageData(pixels,x,y);paintWardrobeOverlay(c,o,{x,y,w,h});
  return remember(key,{canvas,width:WIDTH,height:HEIGHT,ready:true});
}
