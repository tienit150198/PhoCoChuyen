/* A photo sent inside a command (📸 the scene for the album, app.js `photo`; Sửa nhà's room photo, v4/reno.js): B10
 * (07/10) three iPhone commands were refused as too large (> 256 KB, server.py). Safari cannot encode WebP on a canvas
 * and toDataURL('image/webp') then hands back a PNG, which for a 1080 px scene is often 1 MB. Like v4/diploma.js and
 * v4/walk.js: WebP when the browser makes it, else JPEG (never PNG), quality then size stepping down until the data
 * URL is at most PHOTO_MAX characters, so the command body stays well under the 256 KB cap after base64. */
export const PHOTO_MAX=200000;
export const PHOTO_QUALITIES=[.82,.7,.58,.46,.36];
export const PHOTO_SCALES=[1,.8,.64,.5,.4];

/** The data URL of `src` (a canvas or a loaded image, `w`×`h` its own size) drawn `width` px wide on `bg`, or null
 * when even the smallest step is over `max`. `doc`: where canvases come from (tests pass a fake one). */
export function encodePhoto(src,{w,h,width,bg='#ffffff',max=PHOTO_MAX,qualities=PHOTO_QUALITIES,scales=PHOTO_SCALES,doc=globalThis.document}={}){
  const sw=Number(w||src?.naturalWidth||src?.width)||0,sh=Number(h||src?.naturalHeight||src?.height)||0;
  if(!sw||!sh||!doc)return null;
  const base=Math.round(width||sw);
  for(const s of scales){
    const cw=Math.max(1,Math.round(base*s)),ch=Math.max(1,Math.round(cw*sh/sw));
    const c=doc.createElement('canvas');c.width=cw;c.height=ch;
    const x=c.getContext('2d');
    x.fillStyle=bg;x.fillRect(0,0,cw,ch);   // JPEG has no transparency: a see-through corner would turn black
    x.drawImage(src,0,0,cw,ch);
    for(const q of qualities){
      let url=c.toDataURL('image/webp',q);
      if(!url.startsWith('data:image/webp'))url=c.toDataURL('image/jpeg',q);
      if(!url.startsWith('data:image/webp')&&!url.startsWith('data:image/jpeg'))return null;   // never a PNG
      if(url.length<=max)return url;
    }
  }
  return null;
}
