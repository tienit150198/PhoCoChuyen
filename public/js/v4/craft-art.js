import {RECIPES} from './craft-gestures.js';
const beadSlots=Array.from({length:8},(_,i)=>{const a=i*Math.PI/4;return [280+104*Math.cos(a),256+88*Math.sin(a)];});
/** Shared teddy silhouette and finished keepsake: normalized stamps match the workshop. */
export const TEDDY_PATH='M240 110Q255 110 260 132Q280 124 300 132Q305 110 320 110Q344 112 340 134Q339 148 328 156Q344 186 320 210Q348 217 366 232Q389 253 368 258Q354 264 332 246Q341 279 334 306Q350 337 336 344Q313 364 304 344L296 318Q280 325 264 318L256 344Q248 360 224 344Q210 335 226 306Q219 277 228 246Q205 265 192 258Q174 248 194 232Q212 216 240 210Q216 187 232 156Q211 142 224 118Q230 110 240 110Z';
const mark=p=>({plain:'♡',flower:'✿',stars:'✦',waves:'≈'}[p]||'✿');
export function teddyArt({color='#de829d',pattern='flower',marks=[],stuffed=4,face=[0,1,2,3],sewn=true}={}){
 const fill=/^#[\da-f]{3,8}$/i.test(color)?color:'#de829d',fat=1+stuffed*.02;
 return `<g transform="translate(280 235) scale(${fat}) translate(-280 -235)"><path d="${TEDDY_PATH}" fill="${fill}" stroke="#896650" stroke-width="2.5"/>${stuffed?'<ellipse cx="280" cy="271" rx="39" ry="44" fill="#fff3df" opacity=".26"/><ellipse cx="268" cy="165" rx="29" ry="24" fill="#fff3df" opacity=".13"/>':''}<path d="M231 131Q241 115 249 133M311 133Q320 115 330 131" fill="none" stroke="#f5d1bd" stroke-width="9" stroke-linecap="round"/>${sewn?`<path d="${TEDDY_PATH}" transform="translate(280 230) scale(.94) translate(-280 -230)" fill="none" stroke="#a95670" stroke-width="1.8" stroke-dasharray="3 4"/>`:''}${face.includes(0)?'<circle cx="261" cy="176" r="5" fill="#4f3931"/><circle cx="260" cy="175" r="1.4" fill="#fff5e4"/>':''}${face.includes(1)?'<circle cx="299" cy="176" r="5" fill="#4f3931"/><circle cx="298" cy="175" r="1.4" fill="#fff5e4"/>':''}${face.includes(2)?'<ellipse cx="280" cy="192" rx="20" ry="15" fill="#f1d9b9"/><path d="M273 186Q280 182 287 186L280 194Z" fill="#634537"/><path d="M280 193V198M280 198Q273 202 270 197M280 198Q287 202 290 197" fill="none" stroke="#634537" stroke-width="1.6" stroke-linecap="round"/>':''}${face.includes(3)?'<path d="M278 222Q250 207 253 226Q253 239 278 226Q310 240 307 223Q306 210 282 222" fill="#8b4e61"/><circle cx="280" cy="224" r="5" fill="#bd7e8f"/><path d="M277 229L266 248L279 242L286 248L284 229" fill="#8b4e61"/>':''}${marks.map(([x,y])=>`<text x="${252+x*56}" y="${253+y*43}" dominant-baseline="central" text-anchor="middle" fill="#654838" font-size="17">${mark(pattern)}</text>`).join('')}</g>`;
}
export function workpieceArt(d,color,id){
 const step=RECIPES[d.kind][d.step],past=s=>d.done.includes(s),marks=d.marks.map(([x,y])=>`<text x="${152+x*256}" y="${130+y*248}" text-anchor="middle" dominant-baseline="central" fill="#69463b" font-size="32">${mark(d.pattern)}</text>`).join('');
 let shape='';
 if(d.kind==='teddy'){
  const cut=past('cut');
  shape=`${!cut?`<rect x="168" y="94" width="224" height="272" rx="3" fill="${color}" opacity=".4"/><rect x="176" y="102" width="208" height="256" rx="3" fill="${color}" opacity=".5"/>`:''}${cut?`<path d="${TEDDY_PATH}" transform="translate(9 5)" fill="#e3c7ab" stroke="#87664e" stroke-width="2"/>`:''}${teddyArt({color,pattern:d.pattern,marks:d.marks,stuffed:d.stuffed.length,face:d.face,sewn:past('sew')})}${!past('stuff')&&past('sew')?'<path d="M264 133Q280 127 296 133" fill="none" stroke="#644733" stroke-width="8"/><text x="280" y="84" text-anchor="middle" fill="#fff4dd" font-size="12">Chừa khe nhỏ để nhồi bông</text>':''}${step==='cut'?'<text x="280" y="399" text-anchor="middle" fill="#fff4dd" font-size="12">Hai lớp vải đặt chồng · cắt cùng một mẫu</text>':''}`;
 }else if(d.kind==='tote'){
  const cut=past('cut'),sewn=past('sew');
  shape=`${!cut?`<path d="M117 80L438 86L447 419L124 410Z" fill="${color}" opacity=".4"/>`:''}<rect x="152" y="110" width="256" height="288" rx="${sewn?17:2}" fill="${color}" stroke="#836854" stroke-width="2"/><rect x="152" y="110" width="256" height="288" rx="${sewn?17:2}" fill="url(#${id}-linen)"/><path d="M155 132H405" stroke="#fff8ec" stroke-width="6" opacity=".55"/>${sewn?'<path d="M168 142V382H392V142" fill="none" stroke="#b66a78" stroke-width="3" stroke-dasharray="5 5"/>':''}${[0,1].map((i)=>d.placed.includes(i)||past('straps')?`<path d="M${i?312:200} 126V70Q${i?336:224} 23 ${i?360:248} 70V126" fill="none" stroke="#795b40" stroke-width="14"/><path d="M${i?312:200} 126V70Q${i?336:224} 23 ${i?360:248} 70V126" fill="none" stroke="${color}" stroke-width="9"/>`:'').join('')}${marks}`;
 }else if(d.kind==='pot'){
  const shaped=past('shape');shape=`<path d="${shaped?'M177 143H383L350 350Q280 372 210 350Z':'M178 330Q148 274 210 228Q208 171 280 166Q350 165 354 228Q417 280 382 330Z'}" fill="${past('glaze')||step==='glaze'?color:'#bc8e70'}" stroke="#795b48" stroke-width="3"/>${shaped?'<ellipse cx="280" cy="145" rx="104" ry="22" fill="#dab592" stroke="#795b48" stroke-width="3"/><ellipse cx="280" cy="145" rx="87" ry="12" fill="#795b48"/>':''}${marks}`;
 }else if(d.kind==='bracelet'){
  shape=`<ellipse cx="280" cy="256" rx="104" ry="88" fill="none" stroke="#9a7957" stroke-width="${past('thread')?5:2}" stroke-dasharray="${past('thread')?'0':'5 6'}"/>${beadSlots.map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="19" fill="${d.placed.includes(i)?color:'#e5dbc9'}" stroke="#967a60" stroke-width="2"/>${d.placed.includes(i)?`<circle cx="${x-5}" cy="${y-5}" r="5" fill="#fff8ef" opacity=".6"/>`:''}`).join('')}${marks}`;
 }else{
  shape=`<rect x="148" y="118" width="264" height="240" rx="5" fill="${color}" stroke="#876c58" stroke-width="2"/>${past('fold')?'<path d="M280 118L162 138V343L280 358Z" fill="#fff8ec" opacity=".4"/><path d="M280 118V358" stroke="#876c58" stroke-width="3"/>':'<path d="M280 118V358" stroke="#fff8ec" stroke-width="3" stroke-dasharray="6 6"/>'}${marks}`;
 }
 return shape;
}

export function craftedArt(value,colors=[]){
 const color=colors.find(x=>x.id===value.color)?.hex||(/^#[\da-f]{3,8}$/i.test(value.color||'')?value.color:'#de829d');
 if(!RECIPES[value.kind])return '';
 const d={...value,step:RECIPES[value.kind].length-1,done:[...RECIPES[value.kind]],placed:[0,1,2,3,4,5,6,7],stuffed:[0,1,2,3],face:[0,1,2,3],marks:value.work?.marks||[]};
 return `<svg viewBox="${value.kind==='teddy'?'140 88 280 292':'100 0 360 430'}" width="190" height="198" role="img" aria-label="Món thủ công tự tay làm">${workpieceArt(d,color,'craft-keepsake')}</svg>`;
}
