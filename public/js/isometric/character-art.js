/** Reference-matched chibi atlas: four views × idle/two walking poses, cached by saved wardrobe. */
import {defaultLook,art,figureOf,paintPlayer,paintTop,paintAcc,paintPairs,cleanPairs,cleanWing,CANVAS,topColour,hairColour} from '../v4/look.js';
import {drawWings,wingSparkles,wingBitmap,wingScale,drawRays,LIGHT_Y,cleanWing as wingOf} from '../v4/wings-art.js';

const WIDTH=120,HEIGHT=160,FOOT=156;
const atlases=new Map(),stamps=new Map(),MAX_STAMPS=160;
const cells={sw:0,se:1,nw:2,ne:3};
export const atlasCell=(direction,walkFrame=0)=>({x:cells[direction]??cells.se,y:Math.max(0,Math.min(2,Math.trunc(Number(walkFrame)||0)))});
// This painted sheet is not a regular 256px grid: the idle shoes cross y=256.
// Keep its authored gutters, otherwise the next step inherits detached shoe pixels.
export function atlasFrameRect(width,height,direction,walkFrame=0){const cell=atlasCell(direction,walkFrame),rows=[0,268,513,768];return {x:cell.x*width/4,y:Math.round(rows[cell.y]*height/768),w:width/4,h:Math.round(rows[cell.y+1]*height/768)-Math.round(rows[cell.y]*height/768)};}
// Source-pixel landmarks measured on the two 1024×768 sheets, not foot offsets.
// head x/y, eye left x/y + right x/y, torso centre x / neckline y / hem y.
const POSES={
  male:[
    [[132,88,98,122,144,121,135,161,205],[409,88,406,124,452,123,420,161,207],[654,88,0,0,0,0,650,161,208],[911,88,0,0,0,0,916,161,208]],
    [[128,343,89,379,134,379,127,417,459],[413,343,414,380,459,380,419,417,459],[654,343,0,0,0,0,649,417,459],[911,343,0,0,0,0,916,417,459]],
    [[131,587,98,626,143,624,131,659,703],[413,587,410,627,455,625,419,659,703],[654,587,0,0,0,0,650,659,703],[911,587,0,0,0,0,916,659,703]],
  ],
  female:[
    [[131,75,101,111,144,110,132,147,217],[400,75,391,111,436,109,400,147,217],[651,74,0,0,0,0,650,147,217],[907,74,0,0,0,0,907,147,217]],
    [[129,327,95,363,142,362,131,399,465],[410,327,404,364,448,365,411,399,465],[652,327,0,0,0,0,650,399,465],[908,327,0,0,0,0,907,399,465]],
    [[132,574,103,610,145,608,136,642,705],[406,574,399,610,443,609,406,642,705],[652,574,0,0,0,0,650,642,705],[907,574,0,0,0,0,907,642,705]],
  ],
};
export function characterPose(gender,direction,walkFrame=0){const cell=atlasCell(direction,walkFrame),p=POSES[gender==='female'?'female':'male'][cell.y][cell.x];return {head:p.slice(0,2),eyes:p[2]?[[p[2],p[3]],[p[4],p[5]]]:[],torso:{x:p[6],top:p[7],bottom:p[8]}};}
const normalise=options=>{
  const gender=options.gender==='female'?'female':'male';
  const look={...defaultLook(gender),...options.look};
  const pr=cleanPairs(look.pr);if(pr)look.pr=pr;else delete look.pr;   // 🤝 phụ kiện đôi: known kinds only (part of the stamp's key)
  const wg=cleanWing(look.wg);if(wg)look.wg=wg;else delete look.wg;   // 🪽 the wing worn, likewise
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
export function recolourPixel(pixel,y,palette,material=''){
  const [r,g,b,a]=pixel;
  if(a<12||Math.max(r,g,b)<65)return [...pixel];
  let colour=null,reference=1;
  if(material==='top'){colour=palette.top;reference=(g>r*1.1&&b>r*1.05)?100:209;}
  else if(y<.58&&r>g*1.09&&g>b*1.08&&r<180){colour=palette.hair;reference=92;}
  else if(y<.79&&r>g*1.08&&g>b*1.08&&r>145&&b<225){colour=palette.skin;reference=211;}
  else if(y>.43&&y<.83&&r>115&&g>110&&b>85&&r-g<38&&g-b<46&&r>=b){colour=palette.top;reference=209;}
  else if(y>.56&&y<.91&&g>r*1.1&&b>r*1.05&&b<g*1.15){colour=palette.top;reference=100;}
  else if(y>.68&&y<.94&&b>r*1.08&&b>g*1.06){colour=palette.bottom;reference=98;}
  else if(y>.89&&r>g*1.08&&g>b*1.05){colour=palette.shoes;reference=98;}
  if(!colour||!/^#[0-9a-f]{6}$/i.test(colour))return [...pixel];
  return [...tint([r,g,b],colour,reference),a];
}
/** Recolor a stamp in place. Decode each saved color once, never per pixel.
 * Keep recolourPixel as a small independent oracle for byte-level regression tests.
 * Body anchors use canvas coordinates so the material boundary matches painting.
 */
export function recolourPixels(data,width,height,palette,body){
  const decode=value=>value&&/^#[0-9a-f]{6}$/i.test(value)?rgb(value):null;
  const hair=decode(palette.hair),skin=decode(palette.skin),top=decode(palette.top),bottom=decode(palette.bottom),shoes=decode(palette.shoes);
  for(let row=0,i=0;row<height;row++){
    const y=row/height,torsoRow=body&&row+body.y>=body.topY+2&&row+body.y<=body.hemY;
    for(let col=0;col<width;col++,i+=4){
      const r=data[i],g=data[i+1],b=data[i+2];
      if(data[i+3]<12||Math.max(r,g,b)<65)continue;
      let colour=null,reference=1;
      if(torsoRow&&Math.abs(col+body.x-body.topX)<=body.halfWidth){colour=top;reference=(g>r*1.1&&b>r*1.05)?100:209;}
      else if(y<.58&&r>g*1.09&&g>b*1.08&&r<180){colour=hair;reference=92;}
      else if(y<.79&&r>g*1.08&&g>b*1.08&&r>145&&b<225){colour=skin;reference=211;}
      else if(y>.43&&y<.83&&r>115&&g>110&&b>85&&r-g<38&&g-b<46&&r>=b){colour=top;reference=209;}
      else if(y>.56&&y<.91&&g>r*1.1&&b>r*1.05&&b<g*1.15){colour=top;reference=100;}
      else if(y>.68&&y<.94&&b>r*1.08&&b>g*1.06){colour=bottom;reference=98;}
      else if(y>.89&&r>g*1.08&&g>b*1.05){colour=shoes;reference=98;}
      if(!colour)continue;
      const light=(r*.28+g*.56+b*.16)/reference;
      data[i]=Math.round(Math.min(255,Math.max(0,colour[0]*light)));
      data[i+1]=Math.round(Math.min(255,Math.max(0,colour[1]*light)));
      data[i+2]=Math.round(Math.min(255,Math.max(0,colour[2]*light)));
    }
  }
  return data;
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
/** Clean only disconnected atlas debris once, when the source sheet loads. */
export function cleanAtlasPixels(data,w,h){
  const visited=new Uint8Array(w*h),components=[];let largest=0;
  for(let i=0;i<w*h;i++)if(!visited[i]&&data[i*4+3]>20){
    const points=[i];visited[i]=1;
    for(let n=0;n<points.length;n++){const at=points[n],x=at%w,y=Math.floor(at/w);for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
      const nx=x+dx,ny=y+dy,next=ny*w+nx;if(nx<0||nx>=w||ny<0||ny>=h||visited[next]||data[next*4+3]<=20)continue;visited[next]=1;points.push(next);
    }}
    largest=Math.max(largest,points.length);components.push(points);
  }
  const keep=new Uint8Array(w*h);
  // Tiny separated antialias specks are not characters; allow disconnected feet
  // or a strand if they are substantial parts of the same pose.
  for(const points of components)if(points.length>=largest*.02)for(const at of points){const x=at%w,y=Math.floor(at/w);for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const nx=x+dx,ny=y+dy;if(nx>=0&&nx<w&&ny>=0&&ny<h)keep[ny*w+nx]=1;}}
  for(let i=0;i<w*h;i++)if(!keep[i])data[i*4+3]=0;
  return data;
}
function extractView(entry,direction,walkFrame=0){
  const key=direction+walkFrame;if(entry.views.has(key))return entry.views.get(key);
  const rect=atlasFrameRect(entry.img.naturalWidth,entry.img.naturalHeight,direction,walkFrame),{w,h}=rect;
  const cv=document.createElement('canvas');cv.width=w;cv.height=h;
  const c=cv.getContext('2d',{willReadFrequently:true});c.drawImage(entry.img,rect.x,rect.y,w,h,0,0,w,h);
  const pixels=c.getImageData(0,0,w,h);let x0=w,y0=h,x1=0,y1=0;
  cleanAtlasPixels(pixels.data,w,h);c.putImageData(pixels,0,0);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(pixels.data[(y*w+x)*4+3]>24){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
  const view={cv,x:x0,y:y0,w:Math.max(1,x1-x0+1),h:Math.max(1,y1-y0+1),rect};entry.views.set(key,view);return view;
}
function fallback(canvas,o){const c=canvas.getContext('2d');c.translate(WIDTH/2,FOOT-3);c.scale(.9,.9);paintPlayer(c,figureOf(o.look,o.gender),CANVAS);}
const GLASSES=new Set(['kinh_tron','kinh_ram','kinh_mat_meo','kinh_can','kinh_phi_cong']);
const BODY_ITEMS=new Set(['tui_cheo','tui_xach','khan_lua','vong_co','dong_ho','balo_mini','khan_choang','dong_ho_da','ca_vat','no_co','that_lung']);
const NECKWEAR=new Set(['ca_vat','no_co']);   // 👔 a tie or a bow tie: seen from the front only
const COVERING_HATS=new Set(['non_la','mu_len','mu_bucket','mu_luoi_trai','mu_beret','mu_cao_boi','mu_fedora']);
const REAR_ITEMS=new Set(['non_la','mu_len','no_toc','no_lua','kep_toc','mu_bucket','mu_luoi_trai','khan_bandana',...[...BODY_ITEMS].filter(x=>!NECKWEAR.has(x))]);
const HALO='rgba(43,29,26,.88)',HALO_R=1.6;
/** Owner 22/10 ("mặc vào thì thấy tốt hơn, nhìn rõ"): what is worn over the illustrated chibi gets a thin dark outline, so
 * a cap, a bag or a pair's charm stays readable over any shirt at a phone's normal zoom (≈0.42 of the stamp). Drawn on a
 * scratch layer of the stamp's size, its silhouette stamped around it, then the layer on top. No DOM: drawn as it is. */
function haloed(c,draw){
  const doc=globalThis.document,cv=c.canvas;
  if(!doc?.createElement||!cv?.width||typeof c.getTransform!=='function'){draw(c);return;}
  const layer=doc.createElement('canvas');layer.width=cv.width;layer.height=cv.height;
  const q=layer.getContext('2d');if(!q){draw(c);return;}
  q.setTransform(c.getTransform());draw(q);
  const sil=doc.createElement('canvas');sil.width=cv.width;sil.height=cv.height;
  const k=sil.getContext('2d');if(!k){c.save();c.setTransform(1,0,0,1,0,0);c.drawImage(layer,0,0);c.restore();return;}
  k.drawImage(layer,0,0);k.globalCompositeOperation='source-in';k.fillStyle=HALO;k.fillRect(0,0,sil.width,sil.height);
  c.save();c.setTransform(1,0,0,1,0,0);
  for(let i=0;i<8;i++){const a=i*Math.PI/4;c.drawImage(sil,Math.round(Math.cos(a)*HALO_R*10)/10,Math.round(Math.sin(a)*HALO_R*10)/10);}
  c.drawImage(layer,0,0);c.restore();
}
function clothingDetails(c,o,box){
  const F=figureOf(o.look,o.gender),front=o.direction==='sw'||o.direction==='se';
  // Match the existing wardrobe item shapes while the illustrated base keeps its fabric shading.
  const cx=box.bodyX??box.x+box.w*.5,bodyY=box.bodyY??box.y+box.h*.8,foot=box.footY??FOOT,s=box.h/145;
  if(F.bottom.skirt||F.top.long){
    const x=box.w*.24,y=bodyY-box.h*.06,end=foot-(F.bottom.skirt==='long'?7:box.h*.13);
    const fill=c.createLinearGradient(cx-x,y,cx+x,end);fill.addColorStop(0,F.bottom.c);fill.addColorStop(1,'#'+rgb(F.bottom.c).map(v=>Math.round(v*.76).toString(16).padStart(2,'0')).join(''));
    c.fillStyle=fill;c.strokeStyle='#684536';c.lineWidth=1;c.beginPath();c.moveTo(cx-x,y);c.lineTo(cx+x,y);c.lineTo(cx+x*1.4,end);c.quadraticCurveTo(cx,end+5,cx-x*1.4,end);c.closePath();c.fill();c.stroke();
  }
  if(front&&F.top.d){
    c.save();if(Number.isFinite(box.topY)){const sy=(box.hemY-box.topY)/34;c.translate(cx,box.topY+52*sy);c.scale(s*.74,sy);}else{c.translate(cx,bodyY+box.h*.07);c.scale(s*.64,s*.67);}paintTop(c,F,CANVAS);c.restore();
  }
  const accessory=art(o.look,'acc');
  if(o.look.acc!=='pk_khong'&&(front||accessory.back||REAR_ITEMS.has(o.look.acc)))haloed(c,c=>{
    c.save();
    if(GLASSES.has(o.look.acc)&&box.eyes?.length===2){
      const [left,right]=box.eyes,sy=s*.88,centreY=(left[1]+right[1])/2;
      c.transform((right[0]-left[0])/22,(right[1]-left[1])/22,0,sy,(left[0]+right[0])/2,centreY+78*sy);
    }else if(Number.isFinite(box.headX)){
      // owner 22/10: a bag, scarf or watch a little larger than before (.8/.85), still on the chibi's torso
      const body=accessory.anchor==='body'||BODY_ITEMS.has(o.look.acc),sx=body?s*.92:Math.min(s*1.22,1.18),sy=body?s*.95:s*(COVERING_HATS.has(o.look.acc)?1.35:1.04);
      c.translate(body?cx:box.headX,body?(box.topY??bodyY)+52*sy:box.headY+103*sy);c.scale(sx,sy);
    }else{
      const body=accessory.anchor==='body'||BODY_ITEMS.has(o.look.acc),accessoryX=body?cx:box.faceX??cx,accessoryY=!body&&box.eyesY!==undefined?box.eyesY+78*s:foot;
      c.translate(accessoryX+(o.direction==='sw'||o.direction==='nw'?-3:3),accessoryY);c.scale(s*.82,s);
    }
    paintAcc(c,F,CANVAS,o.direction);c.restore();
  });
  // 🤝 Phụ kiện đôi (game/friend_charms.py): the bag at the hand, the car at the hip, the rose on the chest, every kind at once.
  if(o.look.pr)haloed(c,c=>{
    const side=o.direction==='sw'||o.direction==='nw'?-1:1,back=o.direction==='nw'||o.direction==='ne';
    const top=Number.isFinite(box.topY)?box.topY:bodyY-box.h*.25,hem=Number.isFinite(box.hemY)?box.hemY:bodyY,half=Math.max(12,box.w*.27);
    const ps=Math.max(.7,s*1.22);   // a little larger than the classic pieces: the chibi is seen at ≈0.42 on a phone
    paintPairs(c,F,CANVAS,{s:ps,side,back,at:{bag:[cx-side*half*1.08,hem-4*ps],car:[cx+side*half*.5,hem-2*ps],rose:[cx-side*half*.4,top+(hem-top)*.3],
      wrist:[cx+side*half*1.02,hem-9*ps],badge:[cx+side*half*.42,top+(hem-top)*.34],shoulder:[cx-side*half*.95,top+3*ps],balloon:[cx+side*half*1.45,top-46*ps],
      fan:[cx-side*half*1.1,hem-12*ps],neck:[cx,top+(hem-top)*.16],jade:[cx-side*half*.2,hem+1*ps]}});
  });
}
/** Shared saved-wardrobe silhouettes. Optional pose anchors move head items separately from the torso. */
export function paintWardrobeOverlay(c,options={},box,alignment={}){
  if(!c||typeof c.save!=='function'||!box||!['x','y','w','h'].every(key=>Number.isFinite(box[key]))||box.w<=0||box.h<=0)return false;
  const geometry={x:box.x,y:box.y,w:box.w,h:box.h};
  for(const key of ['bodyX','bodyY','faceX','eyesY','footY','headX','headY','topY','hemY'])if(Number.isFinite(alignment?.[key]))geometry[key]=alignment[key];
  if(Array.isArray(alignment?.eyes)&&alignment.eyes.length===2&&alignment.eyes.every(point=>Array.isArray(point)&&point.length===2&&point.every(Number.isFinite)))geometry.eyes=alignment.eyes;
  clothingDetails(c,normalise(options||{}),geometry);return true;
}
/** 🪽 Cánh (game/wings.py, owner 22/10 "có cả mode cũ và mode mới đều hiển thị được nhé", 23/10 "cho đẹp hơn, to hơn"):
 * rooted at the top of the chibi's back. In the 120×160 stamp (the other islands: every consumer keeps its size and feet)
 * a smaller pair (STAMP_WING.baked) fits, its tips softly faded at the edges; the 2.5D map draws the full-size pair apart
 * (stampWingFrame, client/isometric/wing-rigs.ts). Facing us (se, sw) they go behind the chibi (destination-over, the
 * sparkles then over it); seen from the back (nw, ne) they lie over its back. */
const WING_OPTS=Object.freeze({s:.8,gap:5,tall:1,spread:0});
export const STAMP_WING=Object.freeze({front:Object.freeze({dy:2,...WING_OPTS}),back:Object.freeze({dy:4,...WING_OPTS}),baked:Object.freeze({dy:4,s:.48,gap:4,tall:1.15,spread:-.1})});
function paintStampWings(c,o,[tx,ty]){
  const back=o.direction==='nw'||o.direction==='ne',v=STAMP_WING.baked,[x,y]=[tx,ty+v.dy],opts={s:v.s,gap:v.gap,tall:v.tall,spread:v.spread,sparkle:false,anim:false};
  const doc=globalThis.document,layer=doc?.createElement?.('canvas'),q=layer?.getContext?.('2d');
  const paint=(k,o2)=>drawWings(k,CANVAS,o.look.wg,x,y,{...opts,...o2});
  if(!q){c.save();c.globalCompositeOperation='destination-over';paint(c,{body:!back});c.restore();if(back)paint(c,{aura:false});wingSparkles(c,CANVAS,o.look.wg,x,y,{s:opts.s});return;}
  // On a layer of the stamp's size, its sides faded out: a wing reaching past the stamp ends softly, never cut straight.
  layer.width=WIDTH;layer.height=HEIGHT;q.lineJoin='round';paint(q,{body:!back});
  const fade=()=>{q.save();q.globalCompositeOperation='destination-out';for(const [x0,x1] of [[0,10],[WIDTH,WIDTH-10]]){const g=q.createLinearGradient(x0,0,x1,0);g.addColorStop(0,'rgba(0,0,0,1)');g.addColorStop(1,'rgba(0,0,0,0)');q.fillStyle=g;q.fillRect(Math.min(x0,x1),0,10,HEIGHT);}q.restore();};
  fade();c.save();c.globalCompositeOperation='destination-over';c.drawImage(layer,0,0);c.restore();   // facing us: behind the chibi (the glow always behind)
  if(back){q.clearRect(0,0,WIDTH,HEIGHT);paint(q,{aura:false});fade();c.drawImage(layer,0,0);}   // seen from the back: over it
  wingSparkles(c,CANVAS,o.look.wg,x,y,{s:opts.s});
}
/** Feet at (60,160). onReady requests one texture refresh after the atlas finishes loading. */
export function getCharacterStamp(options={}){
  const o=normalise(options),key=characterKey(o),entry=atlasFor(o.gender,options.onReady);
  const hit=stamps.get(key);if(hit&&hit.ready===entry.ready){stamps.delete(key);stamps.set(key,hit);return hit;}   // 23/10 lag: a hit counts as recent (LRU), so a busy square keeps its walkers' stamps instead of cycling them out
  const canvas=document.createElement('canvas');canvas.width=WIDTH;canvas.height=HEIGHT;
  if(!entry.ready){fallback(canvas,o);return remember(key,{canvas,width:WIDTH,height:HEIGHT,ready:false});}
  const view=extractView(entry,o.direction,o.walkFrame),scale=entry.scale,w=Math.round(view.w*scale),h=Math.round(view.h*scale),x=Math.round((WIDTH-w)/2),y=FOOT-h;
  const c=canvas.getContext('2d',{willReadFrequently:true});c.drawImage(view.cv,view.x,view.y,view.w,view.h,x,y,w,h);
  const pose=characterPose(o.gender,o.direction,o.walkFrame),point=([px,py])=>[x+(px-view.rect.x-view.x)*w/view.w,y+(py-view.rect.y-view.y)*h/view.h];
  const head=point(pose.head),top=point([pose.torso.x,pose.torso.top]),hem=point([pose.torso.x,pose.torso.bottom]);
  const alignment={headX:head[0],headY:head[1],eyes:pose.eyes.map(point),bodyX:top[0],bodyY:hem[1],topY:top[1],hemY:hem[1]};
  // Water poses receive the canvas itself, so carry the measured chin/neck crop
  // on that object rather than cutting a constant percentage through a shirt.
  canvas.headBottomY=Math.max(1,Math.min(HEIGHT,top[1]-2));
  const pixels=c.getImageData(x,y,w,h),palette={hair:hairColour(o.look),skin:art(o.look,'skin').c,top:o.look.uniform&&o.uniformColor?o.uniformColor:topColour(o.look,o.gender),bottom:art(o.look,'bottom').c,shoes:art(o.look,'shoes').c};
  recolourPixels(pixels.data,w,h,palette,{x,y,topX:top[0],topY:top[1],hemY:hem[1],halfWidth:32*w/view.w});
  c.putImageData(pixels,x,y);
  if(o.look.wg)paintStampWings(c,o,top);
  paintWardrobeOverlay(c,o,{x,y,w,h},alignment);
  return remember(key,{canvas,width:WIDTH,height:HEIGHT,ready:true,top:[top[0],top[1]]});   // top: where wings drawn apart take root (stampWingFrame)
}
/** 🪽 The chibi with its whole pair spread on a wider canvas (WINGED_W×160, centred, the feet as in the stamp): the
 * wardrobe's and the wing shop's mirror in the cozy look (isometric/portraits.js). Still: the light, the pair, sparkles. */
export const WINGED_W=190;
const winged=new Map();
export function wingedStamp(options={}){
  const wg=wingOf(options.look?.wg),{wg:_,...bare}=options.look||{},base=getCharacterStamp({...options,look:bare});
  if(!wg||!base.ready||!base.top||!globalThis.document?.createElement)return base;
  const key=characterKey({...options,look:bare})+JSON.stringify(wg);let hit=winged.get(key);if(hit){winged.delete(key);winged.set(key,hit);return hit;}
  const canvas=document.createElement('canvas');canvas.width=WINGED_W;canvas.height=HEIGHT;const c=canvas.getContext('2d');if(!c)return base;
  const dx=(WINGED_W-WIDTH)/2,back=options.direction==='nw'||options.direction==='ne',v=back?STAMP_WING.back:STAMP_WING.front;
  const x=base.top[0]+dx,y=base.top[1]+v.dy,o={s:.62,gap:4,tall:1,spread:0,anim:false};
  c.lineJoin='round';drawWings(c,CANVAS,wg,x,y,{...o,body:!back,sparkle:false});c.drawImage(base.canvas,dx,0);
  if(back)drawWings(c,CANVAS,wg,x,y,{...o,aura:false,sparkle:false});
  wingSparkles(c,CANVAS,wg,x,y,{s:o.s});
  hit={canvas,width:WINGED_W,height:HEIGHT,ready:true};winged.set(key,hit);if(winged.size>24)winged.delete(winged.keys().next().value);return hit;
}
/* 🪽 The wings apart from the chibi, so the 2.5D map can move them (owner 22/10 "cánh có hoạt họa, có tia sáng này kia nhé";
 * client/isometric/wing-rigs.ts). The stamp is then drawn without them (its look without `wg`); its `top` plus
 * STAMP_WING[view].dy is the roots. Every canvas here is shared by everyone wearing that wing, and by both views (the same
 * pair, only placed and layered apart): a few flaps (FLAP_STEPS), the glow, the rays, the ring, one mote. */
export const RIG_BOX=Object.freeze([296,224,148,142]);   // the wing canvases: w, h, the roots at (148, 142)
const RAYS_BOX=264;
/** The pair at flap step f (no glow, no motes); `back` kept for the callers, the frames are the same. */
export function stampWingFrame(wg,back,f){return wingBitmap(CANVAS,wg,f,WING_OPTS,RIG_BOX,1,'iso');}
const LIGHTS=new Map();
function lightCanvas(key,w,h,draw){let cv=LIGHTS.get(key);if(cv)return cv;const doc=globalThis.document;cv=doc?.createElement?.('canvas');const q=cv?.getContext?.('2d');if(!q)return null;cv.width=w;cv.height=h;draw(q);LIGHTS.set(key,cv);if(LIGHTS.size>48)LIGHTS.delete(LIGHTS.keys().next().value);return cv;}
/** A light of the tier on its own canvas: 'glow' (RIG_BOX, around the roots), 'rays' (RAYS_BOX square, centred: turn
 * it), 'ring' (100×100, radius 44: scale it); `cy` how far above the roots their centre is. Null below S. */
export function stampWingLight(kind,wg,back=false){
  const w=wingOf(wg);if(!w||w.r<4||kind==='ring'&&w.r<6)return null;const ss=wingScale(w,WING_OPTS.s),h=RAYS_BOX/2;
  if(kind==='glow')return {canvas:lightCanvas(`glow|${w.k}|${w.r}`,RIG_BOX[0],RIG_BOX[1],q=>drawWings(q,CANVAS,w,RIG_BOX[2],RIG_BOX[3],{...WING_OPTS,body:false,sparkle:false,anim:false})),ox:RIG_BOX[2],oy:RIG_BOX[3]};
  if(kind==='rays')return {canvas:lightCanvas(`rays|${w.r}`,RAYS_BOX,RAYS_BOX,q=>drawRays(q,CANVAS,w.r,h,h+LIGHT_Y*ss,ss)),cy:LIGHT_Y*ss};
  return {canvas:lightCanvas(`ring|${w.r}`,100,100,q=>{q.strokeStyle=w.r===7?'#ffe58a':'#ffffff';q.lineWidth=3;q.beginPath();q.arc(50,50,44,0,Math.PI*2);q.stroke();q.strokeStyle=w.r===7?'#ffd24a99':'#ff8fd099';q.lineWidth=1.4;q.beginPath();q.arc(50,50,38,0,Math.PI*2);q.stroke();}),cy:LIGHT_Y*ss};
}
/** One mote (16×16, centred): a four-point star or a soft dot of `col`. */
export function stampMote(col,starLike){return lightCanvas(`mote|${col}|${starLike}`,16,16,q=>{if(starLike){q.fillStyle=col;q.beginPath();const r=7;for(const [x,y] of [[0,-r],[r*.3,-r*.3],[r,0],[r*.3,r*.3],[0,r],[-r*.3,r*.3],[-r,0],[-r*.3,-r*.3]])q.lineTo(8+x,8+y);q.closePath();q.fill();}else{const g=q.createRadialGradient(8,8,0,8,8,8);g.addColorStop(0,col);g.addColorStop(.35,col);g.addColorStop(1,col+'00');q.fillStyle=g;q.fillRect(0,0,16,16);}});}
