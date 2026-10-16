/** 🎨 Pictures of /sticker (public/js/sticker/main.js, game/sticker_event.py), all on the device: a chosen file read
 * into a canvas (EXIF orientation kept, the long side capped), a picture fitted whole into the 512 square of a chat
 * sticker, the @username badge, a collage of a whole set for the Facebook post, and the encoder (PNG first, WebP when
 * the PNG is over the limit). Nothing leaves the device until the page sends the pack. */

export const SIZE=512;
const FONT='800 {s}px "Be Vietnam Pro", system-ui, sans-serif';
const canvasOf=(w,h)=>{const c=document.createElement('canvas');c.width=Math.max(1,Math.round(w));c.height=Math.max(1,Math.round(h));return c;};

/** A chosen image file → a canvas whose long side is at most `maxSide`. */
export async function loadPicture(file,maxSide=2048){
  if(!file||!/^image\//.test(file.type||'image/'))throw new Error(`“${file?.name||'Tệp'}” không phải ảnh.`);
  if(file.size>30*1024*1024)throw new Error(`“${file.name}” lớn quá (tối đa 30 MB).`);
  let bmp;
  try{bmp=await createImageBitmap(file,{imageOrientation:'from-image'});}
  catch{bmp=await new Promise((ok,no)=>{const u=URL.createObjectURL(file),im=new Image();im.onload=()=>{URL.revokeObjectURL(u);ok(im);};im.onerror=()=>{URL.revokeObjectURL(u);no(new Error(`Không mở được “${file.name}”. Thử lưu lại thành PNG hoặc JPG nhé.`));};im.src=u;});}
  const w=bmp.width||bmp.naturalWidth,h=bmp.height||bmp.naturalHeight,k=Math.min(1,maxSide/Math.max(w,h));
  const c=canvasOf(w*k,h*k),g=c.getContext('2d');g.imageSmoothingQuality='high';g.drawImage(bmp,0,0,c.width,c.height);bmp.close?.();
  return c;
}

/** The whole picture fitted into the SIZE square, transparent around it (one sticker of a set). */
export function fitSquare(src){
  const out=canvasOf(SIZE,SIZE),g=out.getContext('2d'),k=Math.min(SIZE/src.width,SIZE/src.height),w=src.width*k,h=src.height*k;
  g.imageSmoothingQuality='high';g.drawImage(src,(SIZE-w)/2,(SIZE-h)/2,w,h);
  return out;
}

/** A copy of `src` with the @username badge (a white pill, dark text) in its bottom-right corner. */
export function stamped(src,text){
  const out=canvasOf(src.width,src.height),g=out.getContext('2d');g.drawImage(src,0,0);
  const s=Math.max(.7,Math.min(src.width,src.height)/512),fs=22*s;
  g.font=FONT.replace('{s}',String(Math.round(fs)));
  const w=g.measureText(text).width+28*s,h=40*s,x=out.width-w-12*s,y=out.height-h-12*s,r=h/2;
  g.beginPath();g.moveTo(x+r,y);g.arcTo(x+w,y,x+w,y+h,r);g.arcTo(x+w,y+h,x,y+h,r);g.arcTo(x,y+h,x,y,r);g.arcTo(x,y,x+w,y,r);g.closePath();
  g.fillStyle='rgba(255,255,255,.94)';g.fill();g.lineWidth=2*s;g.strokeStyle='rgba(43,30,24,.35)';g.stroke();
  g.textAlign='center';g.textBaseline='middle';g.fillStyle='#2b1e18';g.fillText(text,x+w/2,y+h/2+s);
  return out;
}

/** The stickers of a set on one white sheet, 4 to a row, the badge in the corner: the picture to post in the group. */
export function collage(items,text){
  const cols=items.length<=9?3:4,rows=Math.ceil(items.length/cols),cell=300,gap=20,pad=28,foot=70;
  const out=canvasOf(pad*2+cols*cell+(cols-1)*gap,pad*2+rows*cell+(rows-1)*gap+foot),g=out.getContext('2d');
  g.fillStyle='#fffaf3';g.fillRect(0,0,out.width,out.height);g.imageSmoothingQuality='high';
  items.forEach((c,i)=>{const x=pad+(i%cols)*(cell+gap),y=pad+Math.floor(i/cols)*(cell+gap);g.drawImage(c,x,y,cell,cell);});
  return stamped(out,text);
}

/** A canvas as {blob, type}: PNG first; WebP when the PNG is over `max`; tooBig when nothing fits. */
export async function encode(c,max=Infinity){
  const blob=(type,q)=>new Promise(ok=>c.toBlob(b=>ok(b),type,q));
  const png=await blob('image/png');
  if(png&&png.size<=max)return {blob:png,type:'image/png'};
  for(const q of [.92,.85,.75,.6]){const w=await blob('image/webp',q);if(w&&w.type==='image/webp'&&w.size<=max)return {blob:w,type:'image/webp'};if(!w||w.type!=='image/webp')break;}
  return {blob:png,type:'image/png',tooBig:true};
}

/** `c` scaled so its long side is `side` (never up). */
export function shrink(c,side){
  const k=Math.min(1,side/Math.max(c.width,c.height));if(k>=1)return c;
  const out=canvasOf(c.width*k,c.height*k),g=out.getContext('2d');g.imageSmoothingQuality='high';g.drawImage(c,0,0,out.width,out.height);
  return out;
}
