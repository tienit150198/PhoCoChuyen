/** Decorate explicitly tagged SVG portraits with the same saved-wardrobe chibi used in the world.
 * Keep the semantic SVG root and all wardrobe handlers on their existing parent buttons. */
import {getCharacterStamp} from './character-art.js';
import {ART,SLOTS,TINT_SLOTS,ACC_COLORS,defaultLook} from '../v4/look.js';

const SELECTOR='svg[data-cozy-portrait]',NS='http://www.w3.org/2000/svg',MAX_THUMBNAILS=64;
const active=new WeakMap();

/** Malformed DOM metadata never replaces the original vector fallback. */
export function decodeCozyPortrait(value){
  if(typeof value!=='string'||value.length>8192)return null;
  try{
    const data=JSON.parse(decodeURIComponent(value));
    if(data?.v!==1||!['face','figure'].includes(data.mode)||!['male','female','none'].includes(data.gender)||!data.look||typeof data.look!=='object'||Array.isArray(data.look))return null;
    const look=defaultLook(data.gender);
    for(const slot of SLOTS)if(typeof data.look[slot]==='string'&&Object.hasOwn(ART[slot],data.look[slot]))look[slot]=data.look[slot];
    if(typeof data.look.uniform==='boolean')look.uniform=data.look.uniform;
    const tint={};
    for(const slot of TINT_SLOTS){const id=look[slot],colour=data.look.tint?.[id];if(typeof colour==='string'&&Object.hasOwn(ACC_COLORS,colour))tint[id]=colour;}
    if(Object.keys(tint).length)look.tint=tint;
    return {mode:data.mode,gender:data.gender,look};
  }catch{return null;}
}

function makeThumbnail(stamp,mode,doc){
  const canvas=doc.createElement('canvas');
  canvas.width=mode==='face'?160:120;canvas.height=160;
  const c=canvas.getContext('2d');if(!c)return null;
  c.imageSmoothingEnabled=true;
  if(mode==='face')c.drawImage(stamp.canvas,0,0,120,120,0,0,160,160);
  else c.drawImage(stamp.canvas,0,0,120,160);
  return canvas.toDataURL('image/png');
}
function decorative(svg){
  if(svg.hasAttribute('data-action')||svg.hasAttribute('onclick')||svg.hasAttribute('tabindex')||['button','link','slider','checkbox'].includes(svg.getAttribute('role')))return false;
  return !svg.querySelector('a, foreignObject, [data-action], [tabindex], [onclick], [role="button"]');
}
function replaceArt(svg,spec,thumbnail,doc){
  const values=(svg.getAttribute('viewBox')||'').trim().split(/\s+/).map(Number);
  const [x,y,w,h]=values.length===4&&values.every(Number.isFinite)&&values[2]>0&&values[3]>0?values:[0,0,spec.mode==='face'?80:120,spec.mode==='face'?80:160];
  const preserved=[...svg.children].filter(n=>n.localName==='title'||n.localName==='desc');
  const paper=doc.createElementNS(NS,'rect');
  for(const [key,value] of Object.entries({x,y,width:w,height:h,rx:spec.mode==='face'?w*.325:Math.min(w,h)*.1,fill:'var(--iso-paper-inset, #f4e4cf)','aria-hidden':'true'}))paper.setAttribute(key,value);
  const image=doc.createElementNS(NS,'image');
  for(const [key,value] of Object.entries({x,y,width:w,height:h,href:thumbnail.href,preserveAspectRatio:spec.mode==='face'?'xMidYMid slice':'xMidYMid meet','aria-hidden':'true',class:'cozy-portrait-image'}))image.setAttribute(key,value);
  svg.replaceChildren(...preserved,paper,image);
  svg.setAttribute('data-cozy-ready',String(thumbnail.ready));
}

/** Idempotent per DOM root. One mutation observer queues one frame only when tagged art changes.
 * Optional dependencies allow lifecycle tests without a browser or loading the bitmap atlas. */
export function bootCozyPortraits(options={}){
  const root=options.root??globalThis.document;if(!root)return null;
  const current=active.get(root);if(current)return current;
  const doc=root.nodeType===9?root:root.ownerDocument;
  const Observer=options.Observer??globalThis.MutationObserver;
  const requestFrame=options.requestFrame??globalThis.requestAnimationFrame;
  const cancelFrame=options.cancelFrame??globalThis.cancelAnimationFrame;
  if(!doc||!Observer||!requestFrame)return null;
  const getStamp=options.getStamp??getCharacterStamp,thumbnailOf=options.makeThumbnail??makeThumbnail;
  const thumbnails=new Map(),tracked=new Set(),pending=new Set();let frame=null,disposed=false;
  const connected=svg=>root.contains(svg);
  function schedule(){if(!disposed&&frame===null&&pending.size)frame=requestFrame(sweep);}
  function ready(){
    if(disposed)return;thumbnails.clear();
    for(const svg of tracked)if(connected(svg))pending.add(svg);else tracked.delete(svg);
    schedule();
  }
  function thumbnail(spec){
    const key=JSON.stringify(spec),hit=thumbnails.get(key);
    if(hit){thumbnails.delete(key);thumbnails.set(key,hit);return hit;}
    const stamp=getStamp({look:spec.look,gender:spec.gender,direction:'se',walkFrame:0,onReady:ready});
    const href=thumbnailOf(stamp,spec.mode,doc);if(!href)return null;
    const result={href,ready:stamp.ready};thumbnails.set(key,result);
    while(thumbnails.size>MAX_THUMBNAILS)thumbnails.delete(thumbnails.keys().next().value);
    return result;
  }
  function collect(node){
    if(node.nodeType!==1&&node.nodeType!==9)return;
    if(node.matches?.(SELECTOR))pending.add(node);
    for(const svg of node.querySelectorAll?.(SELECTOR)||[])pending.add(svg);
  }
  function sweep(){
    frame=null;if(disposed)return;
    const batch=[...pending];pending.clear();
    for(const svg of batch){
      if(!connected(svg)||!decorative(svg)){tracked.delete(svg);continue;}
      const spec=decodeCozyPortrait(svg.getAttribute('data-cozy-portrait'));
      if(!spec){tracked.delete(svg);continue;}
      tracked.add(svg);
      try{const art=thumbnail(spec);if(art)replaceArt(svg,spec,art,doc);}catch{/* Keep the native SVG if canvas drawing is unavailable. */}
    }
  }
  const observer=new Observer(records=>{
    if(disposed)return;
    let removed=false;
    for(const record of records){
      if(record.type==='attributes'){
        if(record.target.hasAttribute('data-cozy-portrait'))collect(record.target);
        else {tracked.delete(record.target);pending.delete(record.target);}
      }
      else if(record.type==='childList'){
        for(const node of record.addedNodes)collect(node);
        removed ||= record.removedNodes.length>0;
      }
    }
    if(removed){for(const svg of tracked)if(!connected(svg))tracked.delete(svg);for(const svg of pending)if(!connected(svg))pending.delete(svg);}
    schedule();
  });
  observer.observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['data-cozy-portrait']});
  const controller={disconnect(){if(disposed)return;disposed=true;observer.disconnect();if(frame!==null)cancelFrame?.(frame);frame=null;pending.clear();tracked.clear();thumbnails.clear();active.delete(root);}};
  active.set(root,controller);collect(root);schedule();return controller;
}
