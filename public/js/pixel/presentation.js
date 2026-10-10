/** Compatibility for decorative legacy SVGs. Native pixel marks stay native; interactive diagrams keep their DOM. */
const cache=new Map(),MAX=96;
let observer=null,queued=false;
const eligible=svg=>!svg.classList.contains('pixel-art')&&!svg.matches('[tabindex],[role="application"],[data-action],[data-command]')&&!svg.querySelector('[data-action],[data-command],a,input,[tabindex]')&&!svg.closest('[data-pixel-skip]')&&(svg.getAttribute('role')==='img'||svg.getAttribute('aria-hidden')==='true')&&svg.querySelector('path,circle,ellipse');
function pixelDecorative(svg){
  if(!eligible(svg)||svg.dataset.pixelSource)return;
  const box=svg.viewBox.baseVal;if(!box.width||!box.height)return;
  const colour=getComputedStyle(svg).color,source=svg.outerHTML,key=source+'|'+colour;
  svg.dataset.pixelSource='pending';
  const apply=url=>{if(!svg.isConnected)return;const image=document.createElementNS('http://www.w3.org/2000/svg','image');image.setAttribute('href',url);image.setAttribute('x',String(box.x));image.setAttribute('y',String(box.y));image.setAttribute('width',String(box.width));image.setAttribute('height',String(box.height));image.style.imageRendering='pixelated';svg.replaceChildren(image);svg.dataset.pixelSource='ready';};
  if(cache.has(key)){apply(cache.get(key));return;}
  const copy=svg.cloneNode(true);copy.removeAttribute('data-pixel-source');copy.setAttribute('xmlns','http://www.w3.org/2000/svg');copy.style.color=colour;
  const width=Math.min(96,Math.max(16,Math.round(box.width/4))),height=Math.min(96,Math.max(16,Math.round(width*box.height/box.width)));
  const image=new Image(),url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml'}));
  image.onload=()=>{URL.revokeObjectURL(url);const cv=document.createElement('canvas');cv.width=width;cv.height=height;const c=cv.getContext('2d');c.imageSmoothingEnabled=false;c.drawImage(image,0,0,width,height);try{const value=cv.toDataURL();cache.set(key,value);while(cache.size>MAX)cache.delete(cache.keys().next().value);apply(value);}catch{delete svg.dataset.pixelSource;}};
  image.onerror=()=>{URL.revokeObjectURL(url);delete svg.dataset.pixelSource;};image.src=url;
}
export function bootPixelPresentation(){
  document.documentElement.dataset.art='pixel';
  const sweep=()=>{queued=false;for(const svg of document.querySelectorAll('svg:not(.pixel-art):not([data-pixel-source])'))pixelDecorative(svg);};
  if(!observer){observer=new MutationObserver(()=>{if(!queued){queued=true;requestAnimationFrame(sweep);}});observer.observe(document.body,{subtree:true,childList:true});}
  sweep();return ()=>{observer?.disconnect();observer=null;};
}
