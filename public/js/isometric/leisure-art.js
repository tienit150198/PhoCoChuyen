/** Lazy illustrated leisure art. Five known images; only two 960x600 backdrops. */
import {getCharacterStamp,recolourPixel,paintWardrobeOverlay} from './character-art.js';
import {defaultLook,art,topColour,hairColour} from '../v4/look.js';

const PATHS={lake:'/icons/cozy-v2/leisure-lake.webp',pool:'/icons/cozy-v2/leisure-pool.webp',
  boat:'/icons/cozy-v2/boat.webp',actions:'/icons/cozy-v2/fishing-actions.webp',fish:'/icons/cozy-v2/fish.webp'};
const images=new Map(),attempts=new Map(),TIMEOUT=12000;
const POSES=['ready','cast','reel','caught'],actionStamps=new Map();let actionImage=null,actionViews=null;
const HAND={ready:[2,-11],cast:[8,-18],reel:[6,-14],caught:[8,-20]};
// The atlas leans its head and torso independently. These anchors are in the shared 120x160 stamp.
const ALIGN={ready:{bodyX:68,bodyY:120,faceX:65,eyesY:65},cast:{bodyX:60,bodyY:118,faceX:54,eyesY:64},
  reel:{bodyX:77,bodyY:121,faceX:48,eyesY:74},caught:{bodyX:57,bodyY:120,faceX:56,eyesY:60}};
const normalise=kind=>({fish:'fishing',pond:'fishing',swim:'pool',boating:'boat'})[kind]||kind;
export const fishingCell=(gender,pose)=>({x:Math.max(0,POSES.indexOf(pose)),y:gender==='female'?1:0});

function imageFor(key){
  const hit=images.get(key);if(hit)return hit.promise;
  const img=new Image(),entry={img,promise:null,ready:false};images.set(key,entry);
  entry.promise=new Promise((resolve,reject)=>{
    let settled=false;
    const finish=error=>{if(settled)return;settled=true;clearTimeout(timer);img.onload=img.onerror=null;
      if(error){if(images.get(key)===entry)images.delete(key);attempts.set(key,(attempts.get(key)||0)+1);reject(error);}
      else{entry.ready=true;resolve(img);}};
    const error=()=>new Error('Chưa tải được cảnh hồ. Thử mở lại hoạt động khi kết nối ổn định.');
    const timer=setTimeout(()=>finish(error()),TIMEOUT);
    img.onload=()=>{if(!img.naturalWidth||!img.naturalHeight||img.naturalWidth>4096||img.naturalHeight>4096)return finish(error());finish();};
    img.onerror=()=>finish(error());
    const path=globalThis.__mnlBoot?.asset?.(PATHS[key])||PATHS[key],retry=attempts.get(key)||0;
    img.src=retry?`${path}${path.includes('?')?'&':'?'}leisure_retry=${retry}`:path;
  });
  return entry.promise;
}

/** Preserve the atlas grid, then trim individual cells and use one scale for all eight poses. */
function extractActions(img){
  if(actionImage===img)return actionViews;
  if(img.naturalWidth%4||img.naturalHeight%2||img.naturalWidth<4||img.naturalHeight<2)return null;
  const width=img.naturalWidth/4,height=img.naturalHeight/2,views=new Map();let maxWidth=1,maxHeight=1;
  for(const gender of ['male','female'])for(const pose of POSES){
    const cell=fishingCell(gender,pose),canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
    const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,cell.x*width,cell.y*height,width,height,0,0,width,height);
    const pixels=ctx.getImageData(0,0,width,height);let x0=width,y0=height,x1=-1,y1=-1;
    for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(pixels.data[(y*width+x)*4+3]>24){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
    if(x1<0)continue;const view={canvas,x:x0,y:y0,width:x1-x0+1,height:y1-y0+1};views.set(`${gender}:${pose}`,view);maxWidth=Math.max(maxWidth,view.width);maxHeight=Math.max(maxHeight,view.height);
  }
  actionImage=img;actionStamps.clear();actionViews={views,scale:Math.min(108/maxWidth,148/maxHeight)};return actionViews;
}

function fishingCharacter(options={}){
  const entry=images.get('actions');if(!entry?.ready)return getCharacterStamp({...options,direction:'ne',walkFrame:0});
  const gender=options.gender==='female'?'female':'male',pose=POSES.includes(options.pose)?options.pose:'ready',set=extractActions(entry.img),view=set?.views.get(`${gender}:${pose}`);
  if(!view)return getCharacterStamp({...options,direction:'ne',walkFrame:0});
  const look={...defaultLook(gender),...options.look},key=JSON.stringify([gender,pose,look]);if(actionStamps.has(key))return actionStamps.get(key);
  const canvas=document.createElement('canvas');canvas.width=120;canvas.height=160;const ctx=canvas.getContext('2d',{willReadFrequently:true});
  const width=Math.round(view.width*set.scale),height=Math.round(view.height*set.scale),x=Math.round((120-width)/2),y=156-height;
  ctx.drawImage(view.canvas,view.x,view.y,view.width,view.height,x,y,width,height);
  const pixels=ctx.getImageData(x,y,width,height),palette={hair:hairColour(look),skin:art(look,'skin').c,top:topColour(look,gender),bottom:art(look,'bottom').c,shoes:art(look,'shoes').c};
  for(let row=0;row<height;row++)for(let col=0;col<width;col++){const i=(row*width+col)*4;pixels.data.set(recolourPixel(Array.from(pixels.data.subarray(i,i+4)),row/height,palette),i);}
  ctx.putImageData(pixels,x,y);paintWardrobeOverlay(ctx,{gender,look,direction:'se'},{x,y,w:width,h:height},ALIGN[pose]);
  const stamp={canvas,width:120,height:160,ready:true,pose,gender,hand:{x:HAND[pose][0],y:HAND[pose][1]}};actionStamps.set(key,stamp);
  while(actionStamps.size>80)actionStamps.delete(actionStamps.keys().next().value);return stamp;
}

function background(kind){
  const key=normalise(kind)==='pool'?'pool':'lake';
  const entry=images.get(key);
  // Both opaque backdrops already use the navigation's 960x600 source geometry.
  // Keep the decoded image: a copied canvas can lose its bitmap after context loss.
  return entry?.ready?entry.img:null;
}

/** Call after choosing an outing, never at startup. Reopening explicitly retries failed images.
 * Fishing uses lake + pose atlas + fish (3); articulated boats only need lake (1), pool uses pool (1).
 * Optional action artwork falls back for this opening; only reopening explicitly retries it.
 * The legacy no-argument call loads both backdrops + boat, also three images.
 */
export async function loadLeisureArt(kind){
  kind=normalise(kind);
  const keys=kind===undefined?['lake','pool','boat']:[kind==='pool'?'pool':'lake'];let optionalFailed=false;
  const required=Promise.all(keys.map(imageFor)),optional=kind==='fishing'?Promise.all(['actions','fish'].map(key=>imageFor(key).catch(()=>{optionalFailed=true;}))):Promise.resolve();
  await Promise.all([required,optional]);
  return {pixelated:false,resolution:3,background,notice:optionalFailed?'Chưa tải đủ hình câu cá. Mở lại cảnh để thử tải lại; hoạt động vẫn chơi được.':'',
    asset:name=>images.get(name)?.ready?images.get(name).img:null,
    fishingCharacter,
    character:options=>getCharacterStamp({...options,walkFrame:options.walkFrame??(options.step===1?1:options.step===3?2:0)})};
}
