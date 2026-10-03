/** photo-frames.js — photobooth frames, people in the shot and the printed strip, drawn in code (canvas 2D).
 * Shared by the 📸 photobooth career (public/js/careers/photobooth.js) and the fair's player photo booth.
 * Self-contained: no imports, no DOM lookups, no network; everything is drawn from plain data, the same data
 * always gives the same picture (ornaments are placed by a generator seeded from the frame id).
 *
 * ---------------------------------------------------------------- API
 *   FRAMES      [{id, name, emoji, sub, bg, ink, accent, edge, font}]   14 themed frames (Vietnamese names)
 *   FRAME       {id: frame}
 *   LAYOUTS     {strip, double, big}: {name, emoji, cells, w, h}       4-cut strip · 2 strips (one sheet) · big frame
 *   BACKDROPS   [{id, name, emoji}]                                    the booth's backdrops
 *   PROPS       [{id, name, emoji, slot: 'hat'|'eyes'|'hand'}]         hats, glasses, signs, flowers…
 *   STICKERS    [{id, name, emoji}]                                    stickers for the print
 *   FILTERS     [{id, name}]                                           colour filters
 *   size(layout)                       → {w, h} of the print in canvas units (before `scale`)
 *   draw(target, strip, frame, deco, opts) → {w, h}
 *       target  a <canvas> (resized to the print × scale) or a CanvasRenderingContext2D (drawn at its transform)
 *       strip   {layout: 'strip'|'double'|'big', shots: [shot|null, …]}   (strip/double: 4 cells, big: 1)
 *       frame   a frame id or a FRAMES row (unknown ids fall back to 'kawaii')
 *       deco    {stickers: ['tim', …] | [{id, cell, x, y, s, r}], date: '03.10.26' | '', filter: 'none'|…,
 *                caption: 'text under the title' (optional), cut: true = the dashed cut line of a double sheet}
 *       opts    {scale: 2, t: s => s (translate the words drawn), brand: 'small line at the very bottom',
 *                paintShot: (ctx, shot, w, h, index) => void   draw a cell yourself (e.g. the fair's avatars);
 *                the default paints `shot` with paintShot below}
 *   paintShot(ctx, shot, w, h)         one photo: backdrop, people, props, light, blur (origin = the cell's corner)
 *       shot    {backdrop: id, light: 'soft'|'bright'|'warm'|'dim'|'harsh', blur: 0..1, pose: 0..3, sign: 'BFF',
 *                people: [{age: 'kid'|'teen'|'adult'|'old', skin: 0..3, hair: '#hex', style: 'long'|'bob'|'short'|
 *                          'bun'|'pony'|'pigtails'|'spiky'|'bald', top: '#hex', wear: 'tee'|'uniform'|'aodai'|'suit'|
 *                          'bride'|'gown', eyes: 'open'|'closed'|'half', mouth: 'smile'|'grin'|'o', hat, eyewear, hold}],
 *                props: [prop ids]  (handed out to people whose slot is free, in order)}
 *   thumb(target, frame, opts)         a small preview of a frame with empty cells (pickers); opts.layout, opts.scale
 *   sig(strip, frame, deco)            a short string that changes when the picture would (cache key for callers)
 * Colours follow the game's warm palette; the canvas is never read back except by a filter on its own cells. */

const SANS='"Trebuchet MS", "Segoe UI", sans-serif';
const SERIF='"Noto Serif", "Times New Roman", serif';   // Georgia has no Vietnamese tones on Windows
const MONO='"Courier New", ui-monospace, monospace';
const TAU=Math.PI*2;

/* ---------------------------------------------------------------- seeded randomness */
function hash(s){let h=2166136261;for(const ch of String(s)){h^=ch.codePointAt(0);h=Math.imul(h,16777619);}return h>>>0;}
function rng(seed){let a=hash(seed)||1;return()=>{a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}

/* ---------------------------------------------------------------- shapes */
const rr=(c,x,y,w,h,r,fill,stroke,lw=2)=>{c.beginPath();c.roundRect(x,y,w,h,r);if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=lw;c.stroke();}};
const el=(c,x,y,rx,ry,fill,rot=0)=>{c.beginPath();c.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),rot,0,TAU);c.fillStyle=fill;c.fill();};
const ln=(c,x,y,x2,y2,col,w=2)=>{c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.beginPath();c.moveTo(x,y);c.lineTo(x2,y2);c.stroke();};
const arc=(c,x,y,r,a0,a1,col,w=2)=>{c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.beginPath();c.arc(x,y,r,a0,a1);c.stroke();};
const poly=(c,pts,fill)=>{c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=fill;c.fill();};
function star(c,x,y,R,r,n,fill,rot=-Math.PI/2){c.beginPath();for(let i=0;i<n*2;i++){const a=rot+i*Math.PI/n,d=i%2?r:R;c.lineTo(x+Math.cos(a)*d,y+Math.sin(a)*d);}c.closePath();c.fillStyle=fill;c.fill();}
function heart(c,x,y,s,fill){c.save();c.translate(x,y);c.scale(s/14,s/14);c.beginPath();c.moveTo(0,7);c.bezierCurveTo(-18,-6,-10,-20,0,-9);c.bezierCurveTo(10,-20,18,-6,0,7);c.fillStyle=fill;c.fill();c.restore();}
function sparkle(c,x,y,s,fill){c.beginPath();c.moveTo(x,y-s);c.quadraticCurveTo(x,y,x+s,y);c.quadraticCurveTo(x,y,x,y+s);c.quadraticCurveTo(x,y,x-s,y);c.quadraticCurveTo(x,y,x,y-s);c.fillStyle=fill;c.fill();}
function flower(c,x,y,s,petal,center,n=5,rot=0){for(let i=0;i<n;i++){const a=rot+i*TAU/n;el(c,x+Math.cos(a)*s*.55,y+Math.sin(a)*s*.55,s*.5,s*.34,petal,a);}el(c,x,y,s*.28,s*.28,center);}
function cloud(c,x,y,s,fill){el(c,x,y,s,s*.55,fill);el(c,x-s*.75,y+s*.15,s*.6,s*.4,fill);el(c,x+s*.8,y+s*.12,s*.65,s*.42,fill);}
function balloon(c,x,y,s,fill){c.strokeStyle='#9c7b6a';c.lineWidth=1;c.beginPath();c.moveTo(x,y+s*1.15);c.quadraticCurveTo(x+s*.4,y+s*1.8,x-s*.1,y+s*2.6);c.stroke();el(c,x,y,s*.85,s,fill);poly(c,[[x-s*.15,y+s*1.15],[x+s*.15,y+s*1.15],[x,y+s*.95]],fill);el(c,x-s*.3,y-s*.35,s*.18,s*.3,'#ffffff66',-.5);}
function lantern(c,x,y,s,body,trim='#e9b949'){ln(c,x,y-s*1.2,x,y-s*.8,trim,1.5);rr(c,x-s*.32,y-s*.86,s*.64,s*.16,3,trim);el(c,x,y,s*.7,s*.72,body);
  for(const k of [-.45,0,.45])c.strokeStyle='#00000022',c.lineWidth=1,c.beginPath(),c.ellipse(x,y,Math.abs(k)*s*.7+.5,s*.72,0,0,TAU),c.stroke();
  rr(c,x-s*.32,y+s*.7,s*.64,s*.16,3,trim);ln(c,x,y+s*.86,x,y+s*1.35,trim,2);el(c,x,y+s*1.4,s*.08,s*.1,trim);el(c,x-s*.22,y-s*.2,s*.12,s*.28,'#ffffff40',-.3);}
function starLantern(c,x,y,s,fill='#f2c84b'){star(c,x,y,s,s*.45,5,'#c0392b');star(c,x,y,s*.78,s*.35,5,fill);el(c,x,y,s*.18,s*.18,'#fff3c4');
  c.strokeStyle='#c0392b';c.lineWidth=1.5;c.beginPath();c.moveTo(x+s*.6,y+s*.7);c.quadraticCurveTo(x+s*1.1,y+s*1.4,x+s*.8,y+s*2);c.stroke();ln(c,x-s*.2,y-s*.9,x-s*.7,y-s*1.9,'#8b5e3c',2);}
function wave(c,x,y,w,amp,col,lw=3,step=24){c.strokeStyle=col;c.lineWidth=lw;c.lineCap='round';c.beginPath();for(let i=0;i<=w;i+=2){const yy=y+Math.sin(i/step*Math.PI)*amp;i?c.lineTo(x+i,yy):c.moveTo(x+i,yy);}c.stroke();}
function sun(c,x,y,r){for(let i=0;i<12;i++){const a=i*TAU/12;ln(c,x+Math.cos(a)*r*1.25,y+Math.sin(a)*r*1.25,x+Math.cos(a)*r*1.6,y+Math.sin(a)*r*1.6,'#ffcf5a',3);}el(c,x,y,r,r,'#ffd55e');el(c,x-r*.3,y-r*.3,r*.3,r*.3,'#fff2b3');}
function moon(c,x,y,r){el(c,x,y,r*1.35,r*1.35,'#fff3c430');el(c,x,y,r,r,'#fde9a6');el(c,x-r*.35,y-r*.2,r*.18,r*.15,'#f1d27e');el(c,x+r*.3,y+r*.3,r*.24,r*.2,'#f1d27e');el(c,x+r*.1,y-r*.45,r*.1,r*.08,'#f1d27e');}
function rabbit(c,x,y,s,fill='#fff7ea'){el(c,x,y,s*.75,s*.6,fill);el(c,x+s*.55,y-s*.45,s*.38,s*.34,fill);el(c,x+s*.42,y-s*1.05,s*.11,s*.42,fill,-.2);el(c,x+s*.66,y-s*1.02,s*.11,s*.4,fill,.25);el(c,x+s*.7,y-s*.5,s*.05,s*.05,'#6b4a3a');el(c,x-s*.72,y+s*.05,s*.16,s*.16,fill);}
function firework(c,x,y,r,col,rnd){for(let i=0;i<14;i++){const a=i*TAU/14+rnd()*.2,d=r*(.75+rnd()*.25);ln(c,x+Math.cos(a)*r*.25,y+Math.sin(a)*r*.25,x+Math.cos(a)*d,y+Math.sin(a)*d,col,2);el(c,x+Math.cos(a)*(d+3),y+Math.sin(a)*(d+3),1.6,1.6,col);}el(c,x,y,r*.12,r*.12,'#fff8d6');}
function cap(c,x,y,s,fill='#1f2a44',tassel='#f2c84b'){poly(c,[[x-s,y],[x,y-s*.42],[x+s,y],[x,y+s*.42]],fill);rr(c,x-s*.55,y+s*.05,s*1.1,s*.45,s*.12,fill);el(c,x,y,s*.08,s*.06,tassel);ln(c,x,y,x+s*.7,y+s*.15,tassel,1.5);ln(c,x+s*.7,y+s*.15,x+s*.72,y+s*.6,tassel,2.5);}
function umbrella(c,x,y,s,col){c.beginPath();c.moveTo(x-s,y);c.quadraticCurveTo(x,y-s*1.3,x+s,y);c.closePath();c.fillStyle=col;c.fill();for(const k of [-.5,0,.5]){el(c,x+k*s,y,s*.25,s*.08,col);}ln(c,x,y-s*.65,x,y+s*.95,'#5b4a40',2);arc(c,x-s*.15,y+s*.95,s*.15,0,Math.PI,'#5b4a40',2);}
function drop(c,x,y,s,col){c.beginPath();c.moveTo(x,y-s);c.quadraticCurveTo(x+s*.75,y+s*.1,x,y+s*.6);c.quadraticCurveTo(x-s*.75,y+s*.1,x,y-s);c.fillStyle=col;c.fill();}
function shell(c,x,y,s,col){c.beginPath();c.moveTo(x,y+s*.6);for(let i=0;i<=6;i++){const a=Math.PI+i*Math.PI/6;c.lineTo(x+Math.cos(a)*s,y+Math.sin(a)*s);}c.closePath();c.fillStyle=col;c.fill();for(let i=1;i<6;i++){const a=Math.PI+i*Math.PI/6;ln(c,x,y+s*.55,x+Math.cos(a)*s*.9,y+Math.sin(a)*s*.9,'#00000022',1);}}
function lotus(c,x,y,s,a='#f2a5bd',b='#f7c6d5'){for(const [dx,ry,col] of [[-.55,.9,b],[.55,.9,b],[-.28,1,a],[.28,1,a],[0,1.1,a]]){el(c,x+dx*s,y-s*.35,s*.32,s*ry*.62,col,dx*.9);}el(c,x,y,s*.62,s*.16,'#7fae7a');}
function lotusLeaf(c,x,y,r,col='#77a874'){el(c,x,y,r,r*.62,col);ln(c,x,y,x+r*.9,y-r*.1,'#5d8f5d',1.5);ln(c,x,y,x-r*.7,y-r*.35,'#5d8f5d',1.5);ln(c,x,y,x-r*.2,y+r*.55,'#5d8f5d',1.5);}
function rose(c,x,y,s,col='#d9506c'){el(c,x,y,s,s*.9,col);arc(c,x,y,s*.6,0,4.5,'#00000030',1.5);arc(c,x+s*.1,y,s*.3,1,6,'#00000030',1.5);el(c,x-s*.9,y+s*.6,s*.5,s*.22,'#6f9f6a',-.5);el(c,x+s*.9,y+s*.6,s*.5,s*.22,'#6f9f6a',.5);}
function ring(c,x,y,r){arc(c,x,y,r,0,TAU,'#e5b84c',r*.32);sparkle(c,x,y-r*1.2,r*.5,'#fff6cf');}
function bunting(c,x1,x2,y,cols,size=14){c.strokeStyle='#8a6a58';c.lineWidth=1.2;c.beginPath();c.moveTo(x1,y);c.quadraticCurveTo((x1+x2)/2,y+size*.7,x2,y);c.stroke();const n=Math.max(2,Math.floor((x2-x1)/(size*1.6)));
  for(let i=0;i<n;i++){const t=(i+.5)/n,xx=x1+(x2-x1)*t,yy=y+Math.sin(t*Math.PI)*size*.5;poly(c,[[xx-size*.55,yy],[xx+size*.55,yy],[xx,yy+size*1.1]],cols[i%cols.length]);}}
function snow(c,x,y,s,col='#ffffff'){for(let i=0;i<3;i++){const a=i*Math.PI/3;ln(c,x-Math.cos(a)*s,y-Math.sin(a)*s,x+Math.cos(a)*s,y+Math.sin(a)*s,col,1.6);}}
function pine(c,x,y,s,col='#2f7a55'){for(let i=0;i<3;i++)poly(c,[[x,y-s*(1.2-i*.35)],[x-s*(.45+i*.15),y-s*(.5-i*.35)],[x+s*(.45+i*.15),y-s*(.5-i*.35)]],col);rr(c,x-s*.1,y+s*.5,s*.2,s*.25,2,'#7a5236');star(c,x,y-s*1.25,s*.16,s*.07,5,'#f2c84b');}
function mai(c,x,y,s,rnd,dir=1){c.strokeStyle='#6d4a35';c.lineWidth=s*.14;c.lineCap='round';c.beginPath();c.moveTo(x,y);c.quadraticCurveTo(x+dir*s*1.6,y+s*.2,x+dir*s*3.2,y+s*1.3);c.stroke();
  c.lineWidth=s*.08;c.beginPath();c.moveTo(x+dir*s*1.3,y+s*.25);c.quadraticCurveTo(x+dir*s*1.9,y-s*.5,x+dir*s*2.4,y-s*.6);c.stroke();
  for(const [t,dy] of [[.6,.05],[1.25,.28],[1.95,-.45],[2.45,-.6],[2.4,.75],[3.05,1.2],[1.7,.55]])flower(c,x+dir*s*t,y+s*dy,s*(.42+rnd()*.12),'#f6cf3c','#e3862f',5,rnd()*2);}
function phuong(c,x,y,s,rnd){for(let i=0;i<3;i++){const a=rnd()*TAU;el(c,x+Math.cos(a)*s*.9,y+Math.sin(a)*s*.5,s*.75,s*.22,'#7aa65a',a);}flower(c,x,y,s*.62,'#e2463a','#f6b23e',5,rnd());flower(c,x+s*.8,y+s*.4,s*.42,'#ee5b45','#f6b23e',5,rnd());}
function confetti(c,L,rnd,cols,n,area){for(let i=0;i<n;i++){const x=area.x+rnd()*area.w,y=area.y+rnd()*area.h,col=cols[i%cols.length];if(i%3===0)el(c,x,y,2.4,2.4,col);else{c.save();c.translate(x,y);c.rotate(rnd()*TAU);c.fillStyle=col;c.fillRect(-4,-1.5,8,3);c.restore();}}}
function fairyLights(c,x1,x2,y,sag,rnd){c.strokeStyle='#4a3a55';c.lineWidth=1.2;c.beginPath();c.moveTo(x1,y);c.quadraticCurveTo((x1+x2)/2,y+sag,x2,y);c.stroke();const cols=['#ffd36e','#ff8fab','#8fd3ff','#b6f28c'];
  for(let i=1;i<10;i++){const t=i/10,xx=x1+(x2-x1)*t,yy=y+2*sag*t*(1-t);el(c,xx,yy+4,5,5,cols[i%4]+'55');el(c,xx,yy+4,2.6,3.2,cols[i%4]);}}
function roofTiles(c,x,y,w,h){rr(c,x,y,w,h,0,'#8a4b2f');for(let i=0;i<w;i+=14){el(c,x+i+7,y+h,7.5,5,'#a85b37');arc(c,x+i+7,y+h-1,6,0,Math.PI,'#6f3b25',1);}ln(c,x,y+3,x+w,y+3,'#6f3b25',2);}

/* ---------------------------------------------------------------- the catalogue */
export const LAYOUTS={
  strip:{name:'Dải 4 ô',emoji:'🎞️',cells:4,w:300,h:900},
  double:{name:'2 dải 4 ô',emoji:'🎞️🎞️',cells:4,w:600,h:900},
  big:{name:'Khung lớn',emoji:'🖼️',cells:1,w:640,h:800},
};
export const BACKDROPS=[
  {id:'kem',name:'Phông kem trơn',emoji:'🤍'},{id:'hong',name:'Phông hồng phấn',emoji:'🩷'},{id:'mint',name:'Phông xanh bạc hà',emoji:'🩵'},
  {id:'den',name:'Phông đen sang',emoji:'🖤'},{id:'hoa',name:'Tường hoa giấy',emoji:'🌸'},{id:'kim_tuyen',name:'Rèm kim tuyến',emoji:'✨'},
];
export const PROPS=[
  {id:'mu_tiec',name:'Mũ sinh nhật',emoji:'🥳',slot:'hat'},{id:'non_la',name:'Nón lá',emoji:'👒',slot:'hat'},
  {id:'mu_tn',name:'Mũ tốt nghiệp',emoji:'🎓',slot:'hat'},{id:'tai_tho',name:'Bờm tai thỏ',emoji:'🐰',slot:'hat'},
  {id:'vuong_mien',name:'Vương miện',emoji:'👑',slot:'hat'},{id:'kinh_tim',name:'Kính trái tim',emoji:'😍',slot:'eyes'},
  {id:'kinh_ram',name:'Kính râm',emoji:'🕶️',slot:'eyes'},{id:'bang_chu',name:'Bảng chữ',emoji:'🪧',slot:'hand'},
  {id:'hoa',name:'Bó hoa',emoji:'💐',slot:'hand'},{id:'bong_bay',name:'Bong bóng',emoji:'🎈',slot:'hand'},
  {id:'long_den',name:'Lồng đèn ông sao',emoji:'⭐',slot:'hand'},
];
const PROP=Object.fromEntries(PROPS.map(p=>[p.id,p]));
export const STICKERS=[
  {id:'tim',name:'Trái tim',emoji:'💗'},{id:'sao',name:'Ngôi sao',emoji:'⭐'},{id:'meo',name:'Mặt mèo',emoji:'🐱'},
  {id:'tho',name:'Thỏ con',emoji:'🐰'},{id:'hoa',name:'Bông hoa',emoji:'🌼'},{id:'may',name:'Đám mây',emoji:'☁️'},
  {id:'lap_lanh',name:'Lấp lánh',emoji:'✨'},{id:'vuong_mien',name:'Vương miện',emoji:'👑'},{id:'not_nhac',name:'Nốt nhạc',emoji:'🎵'},
  {id:'cau_vong',name:'Cầu vồng',emoji:'🌈'},
];
export const FILTERS=[
  {id:'none',name:'Màu gốc'},{id:'den_trang',name:'Đen trắng'},{id:'co_dien',name:'Cổ điển (nâu)'},{id:'am',name:'Nắng ấm'},
  {id:'lanh',name:'Xanh mát'},{id:'phim',name:'Phim cũ'},{id:'hong',name:'Hồng mộng mơ'},
];

/* Frames: palette + `paper` (the sheet under everything) + `deco` (ornaments in the margins and the foot). L is one
 * strip or the big frame: {w, h, cells: [{x,y,w,h}], foot: {x,y,w,h}, big}. */
const F=(id,name,emoji,sub,bg,ink,accent,edge,font,paper,deco)=>({id,name,emoji,sub,bg,ink,accent,edge,font,paper,deco});
export const FRAMES=[
  F('tet','Tết sum vầy','🧧','An khang thịnh vượng','#c8323a','#ffe7a0','#f3c55b','#f3c55b',SERIF,
    (c,L,r)=>{for(let i=0;i<40;i++)el(c,r()*L.w,r()*L.h,1.5+r()*2,1.5+r()*2,'#f3c55b22');},
    (c,L,r)=>{const s=L.big?14:9;mai(c,-2,L.cells[0].y-2,s,r,1);mai(c,L.w+2,L.cells[L.cells.length-1].y+L.cells[L.cells.length-1].h-s,s,r,-1);
      const f=L.foot,y=f.y+f.h*.62;for(const k of [-1,1]){const x=L.w/2+k*(L.big?200:104);rr(c,x-13,y-18,26,36,4,'#e0464d','#f3c55b',1.5);el(c,x,y-6,6,6,'#f3c55b');}
      for(let i=0;i<5;i++){const x=L.w*.2+r()*L.w*.6;el(c,x,f.y+f.h-16-r()*10,6,6,'#f3c55b');el(c,x,f.y+f.h-16-r()*10,3,3,'#d8a63c');}}),
  F('trung_thu','Trung thu','🏮','Rước đèn tháng Tám','#26305e','#ffe39a','#f2c84b','#f2c84b',SANS,
    (c,L,r)=>{const g=c.createLinearGradient(0,0,0,L.h);g.addColorStop(0,'#1d2550');g.addColorStop(1,'#3a3d7a');c.fillStyle=g;c.fillRect(0,0,L.w,L.h);for(let i=0;i<50;i++)sparkle(c,r()*L.w,r()*L.h,1+r()*2.5,'#fff6c8aa');},
    (c,L,r)=>{const f=L.foot,m=L.big?40:28;moon(c,L.w-m-6,f.y+m+8,m);starLantern(c,L.big?70:44,f.y+(L.big?78:58),L.big?28:18);rabbit(c,L.w/2+(L.big?150:62),f.y+f.h-26,L.big?20:12);
      for(const cl of L.cells.slice(0,2))lantern(c,cl.x+cl.w-14,cl.y+8,L.big?16:10,'#e5533d');}),
  F('hoa_sen','Hoa sen','🪷','Thơm ngát đầm sen','#f6efe2','#7a4a5a','#e8a9bd','#e8a9bd',SERIF,
    (c,L,r)=>{const g=c.createLinearGradient(0,L.h*.6,0,L.h);g.addColorStop(0,'#f6efe2');g.addColorStop(1,'#cfe3c4');c.fillStyle=g;c.fillRect(0,0,L.w,L.h);},
    (c,L,r)=>{const f=L.foot,s=L.big?30:20;lotusLeaf(c,s*1.2,f.y+f.h-s*1.1,s*1.5);lotusLeaf(c,L.w-s*1.4,f.y+f.h-s*.9,s*1.3,'#86b47f');lotus(c,s*1.5,f.y+f.h-s*1.7,s);lotus(c,L.w-s*1.6,f.y+f.h-s*1.5,s*.85,'#f4b3c7','#f9d2de');
      for(const cl of L.cells){el(c,cl.x+4,cl.y+4,5,5,'#e8a9bd');}const cl=L.cells[0];lotusLeaf(c,cl.x+cl.w-6,cl.y-2,L.big?20:13,'#8dbb85');}),
  F('pho_co','Phố cổ','🏯','Đèn lồng phố Hội','#f2c75c','#6b3a24','#c0392b','#8a4b2f',SERIF,
    (c,L,r)=>{c.fillStyle='#f2c75c';c.fillRect(0,0,L.w,L.h);for(let i=0;i<70;i++)el(c,r()*L.w,r()*L.h,4+r()*14,2+r()*6,'#e3b44a55');},
    (c,L,r)=>{roofTiles(c,0,0,L.w,L.big?30:18);const cols=['#d9433a','#e98a2f','#c73a6c','#4d8f5a','#d9433a'];const n=L.big?5:3;
      for(let i=0;i<n;i++){const x=L.w*(i+.5)/n;ln(c,x,L.big?30:18,x,(L.big?30:18)+8,'#6b3a24',1.5);lantern(c,x,(L.big?30:18)+(L.big?28:18),L.big?16:10,cols[i%cols.length]);}
      const f=L.foot;rr(c,L.w/2-(L.big?150:100),f.y+f.h-(L.big?26:20),L.big?300:200,L.big?10:7,4,'#8a4b2f');}),
  F('retro','Phim cũ','🎞️','PHIM 135 · ISO 200','#1d1b1a','#f1b25a','#f1b25a','#2c2927',MONO,
    (c,L,r)=>{c.fillStyle='#1d1b1a';c.fillRect(0,0,L.w,L.h);const hx=L.big?20:10,hw=L.big?14:8;for(let y=8;y<L.h-8;y+=L.big?26:20){rr(c,hx-hw/2,y,hw,L.big?14:10,2,'#f3ead7');rr(c,L.w-hx-hw/2,y,hw,L.big?14:10,2,'#f3ead7');}},
    (c,L,r)=>{c.font=`700 ${L.big?13:9}px ${MONO}`;c.fillStyle='#f1b25a';c.textBaseline='middle';
      L.cells.forEach((cl,i)=>{c.textAlign='left';c.fillText(`${12+i*2} ▸`,cl.x+2,cl.y-(L.big?12:8));c.textAlign='right';c.fillText(`${12+i*2}A`,cl.x+cl.w-2,cl.y-(L.big?12:8));});}),
  F('kawaii','Dễ thương','🎀','Cute hết nấc','#ffd6e5','#d0567f','#ff9ec0','#ffffff',SANS,
    (c,L,r)=>{c.fillStyle='#ffd6e5';c.fillRect(0,0,L.w,L.h);for(let y=8;y<L.h;y+=22)for(let x=(y/22)%2?8:19;x<L.w;x+=22)el(c,x,y,2.4,2.4,'#ffffffaa');},
    (c,L,r)=>{const s=L.big?1.6:1;L.cells.forEach((cl,i)=>{heart(c,cl.x+(i%2?cl.w-6:6),cl.y+4,12*s,i%2?'#ff7aa8':'#ffb3cf');sparkle(c,cl.x+(i%2?10:cl.w-10),cl.y+cl.h-4,6*s,'#fff');});
      const f=L.foot;bow(c,L.w/2,f.y+(L.big?26:18),L.big?22:15);rabbit(c,(L.big?70:40),f.y+f.h-(L.big?34:24),L.big?18:11,'#ffffff');heart(c,L.w-(L.big?66:38),f.y+f.h-(L.big?40:30),L.big?22:15,'#ff7aa8');
      for(let i=0;i<6;i++)star(c,r()*L.w,f.y+r()*f.h,4,1.8,5,'#ffe27a');}),
  F('cuoi','Ngày cưới','💍','Trăm năm hạnh phúc','#fffaf2','#b0893e','#d9506c','#e5c88a',SERIF,
    (c,L,r)=>{c.fillStyle='#fffaf2';c.fillRect(0,0,L.w,L.h);rr(c,5,5,L.w-10,L.h-10,L.big?14:10,null,'#e5c88a',2);rr(c,10,10,L.w-20,L.h-20,L.big?10:7,null,'#efdcb0',1);},
    (c,L,r)=>{const f=L.foot,cx=L.w/2;c.font=`700 ${L.big?44:30}px ${SERIF}`;c.fillStyle='#d03a3a';c.textAlign='center';c.textBaseline='middle';c.fillText('囍',cx,f.y+(L.big?36:26));
      rose(c,L.big?60:34,f.y+f.h-(L.big?40:28),L.big?16:10);rose(c,L.w-(L.big?60:34),f.y+f.h-(L.big?40:28),L.big?16:10,'#e98aa0');ring(c,cx-(L.big?120:70),f.y+(L.big?36:26),L.big?10:6);ring(c,cx+(L.big?120:70),f.y+(L.big?36:26),L.big?10:6);
      for(const cl of [L.cells[0],L.cells[L.cells.length-1]])sparkle(c,cl.x+cl.w-8,cl.y+8,L.big?9:6,'#e5c88a');}),
  F('tot_nghiep','Tốt nghiệp','🎓','Chúc mừng tân cử nhân','#203a6b','#f5d77e','#f5d77e','#f5d77e',SANS,
    (c,L,r)=>{c.fillStyle='#203a6b';c.fillRect(0,0,L.w,L.h);confetti(c,L,r,['#f5d77e55','#ffffff33','#8fb4ff44'],60,{x:0,y:0,w:L.w,h:L.h});},
    (c,L,r)=>{const f=L.foot,s=L.big?22:14;cap(c,L.big?70:40,f.y+(L.big?40:30),s);cap(c,L.w-(L.big?70:40),f.y+(L.big?60:44),s*.85,'#2b2b2b');
      rr(c,L.w/2-(L.big?40:26),f.y+f.h-(L.big?44:30),L.big?80:52,L.big?16:11,6,'#fdf1d0','#c49a3a',1.5);el(c,L.w/2,f.y+f.h-(L.big?36:24.5),L.big?5:3.5,L.big?8:5.5,'#c0392b');
      cap(c,L.cells[0].x+L.cells[0].w-12,L.cells[0].y+2,L.big?16:10,'#1f2a44');}),
  F('bien','Biển gọi','🏖️','Nắng, gió và sóng','#8fd3ee','#ffffff','#ffcf5a','#ffffff',SANS,
    (c,L,r)=>{const g=c.createLinearGradient(0,0,0,L.h);g.addColorStop(0,'#bfe8f7');g.addColorStop(.72,'#7cc6e4');g.addColorStop(.86,'#4fa7cf');g.addColorStop(1,'#f3dca4');c.fillStyle=g;c.fillRect(0,0,L.w,L.h);},
    (c,L,r)=>{const f=L.foot;sun(c,L.w-(L.big?60:38),f.y+(L.big?44:32),L.big?20:13);for(let i=0;i<3;i++)wave(c,6,f.y+f.h*.5+i*(L.big?14:10),L.w-12,L.big?4:3,'#ffffffcc',2,L.big?28:18);
      shell(c,L.big?60:34,f.y+f.h-(L.big?18:12),L.big?14:9,'#f7b39a');star(c,L.w/2+(L.big?120:70),f.y+f.h-(L.big?16:11),L.big?11:7,L.big?5:3,5,'#f29b5d');
      cloud(c,L.big?80:46,f.y+(L.big?36:26),L.big?18:11,'#ffffffdd');}),
  F('mua_sg','Mưa Sài Gòn','🌧️','Chiều mưa phố mình','#5f7488','#e8f1f7','#f2c84b','#cfdbe6',SANS,
    (c,L,r)=>{const g=c.createLinearGradient(0,0,0,L.h);g.addColorStop(0,'#536779');g.addColorStop(1,'#7890a6');c.fillStyle=g;c.fillRect(0,0,L.w,L.h);c.strokeStyle='#ffffff2e';c.lineWidth=1.2;for(let i=0;i<110;i++){const x=r()*L.w,y=r()*L.h;c.beginPath();c.moveTo(x,y);c.lineTo(x-3,y+12);c.stroke();}},
    (c,L,r)=>{const f=L.foot,base=f.y+f.h-(L.big?18:12);c.fillStyle='#3e4f60';let x=0;while(x<L.w){const w=(L.big?26:16)+r()*(L.big?30:18),h=(L.big?22:16)+r()*(L.big?40:36);c.fillRect(x,base-h,w-3,h);for(let wy=base-h+6;wy<base-6;wy+=9)for(let wx=x+4;wx<x+w-8;wx+=8)if(r()<.45)c.fillStyle='#f6d77f99',c.fillRect(wx,wy,3,4),c.fillStyle='#3e4f60';x+=w;}
      c.fillStyle='#2f3d4b';c.fillRect(0,base,L.w,L.big?18:12);umbrella(c,L.big?70:40,f.y+(L.big?44:30),L.big?22:14,'#e5533d');umbrella(c,L.w-(L.big?70:40),f.y+(L.big?50:34),L.big?20:13,'#f2c84b');
      for(const cl of L.cells)drop(c,cl.x+cl.w-8,cl.y+cl.h-4,L.big?7:5,'#cfe6f5');}),
  F('sinh_nhat','Sinh nhật','🎂','Tuổi mới thật vui','#fff4d6','#e2574c','#5bb6d9','#ffffff',SANS,
    (c,L,r)=>{c.fillStyle='#fff4d6';c.fillRect(0,0,L.w,L.h);confetti(c,L,r,['#e2574c66','#5bb6d966','#f2c84b88','#8fd18b66'],70,{x:0,y:0,w:L.w,h:L.h});},
    (c,L,r)=>{bunting(c,4,L.w-4,6,['#e2574c','#f2c84b','#5bb6d9','#8fd18b'],L.big?18:11);const f=L.foot,s=L.big?1.5:1;balloon(c,L.big?60:32,f.y+(L.big?36:26),14*s,'#e2574c');balloon(c,L.big?96:54,f.y+(L.big?50:36),12*s,'#5bb6d9');
      const cx=L.w-(L.big?80:46),cy=f.y+f.h-(L.big?30:22);rr(c,cx-22*s,cy-14*s,44*s,22*s,5,'#f7c4d4','#e2574c',1.5);rr(c,cx-16*s,cy-28*s,32*s,15*s,4,'#ffffff','#e2574c',1.5);for(const k of [-8,0,8]){ln(c,cx+k*s,cy-28*s,cx+k*s,cy-36*s,'#5bb6d9',2);el(c,cx+k*s,cy-39*s,1.8*s,3*s,'#f2a33a');}}),
  F('dem_hoi','Đêm hội','🎆','Pháo hoa rực trời','#2b1840','#ffd36e','#ff8fab','#5a3a78',SANS,
    (c,L,r)=>{const g=c.createLinearGradient(0,0,0,L.h);g.addColorStop(0,'#1d1030');g.addColorStop(1,'#3b2157');c.fillStyle=g;c.fillRect(0,0,L.w,L.h);for(let i=0;i<40;i++)el(c,r()*L.w,r()*L.h,1,1,'#ffffff99');},
    (c,L,r)=>{fairyLights(c,0,L.w,4,L.big?26:16,r);const f=L.foot;firework(c,L.big?80:46,f.y+(L.big?50:36),L.big?34:22,'#ff8fab',r);firework(c,L.w-(L.big?80:46),f.y+(L.big?60:44),L.big?30:20,'#ffd36e',r);firework(c,L.w/2,f.y+f.h-(L.big?24:16),L.big?14:9,'#8fd3ff',r);}),
  F('phuong','Mùa phượng','🌺','Tuổi học trò','#fff1e4','#c23b2e','#e2463a','#f4c7b8',SERIF,
    (c,L,r)=>{c.fillStyle='#fff1e4';c.fillRect(0,0,L.w,L.h);c.strokeStyle='#f0d5c3';c.lineWidth=1;for(let y=16;y<L.h;y+=16){c.beginPath();c.moveTo(0,y);c.lineTo(L.w,y);c.stroke();}ln(c,L.big?34:16,0,L.big?34:16,L.h,'#f2a3a0',1.2);},
    (c,L,r)=>{const s=L.big?18:12;phuong(c,L.w-s*1.2,s*1.1,s,r);phuong(c,s*1.4,L.foot.y+L.foot.h-s*1.4,s,r);phuong(c,L.w-s*1.6,L.foot.y+s*1.6,s*.8,r);
      for(let i=0;i<5;i++)el(c,r()*L.w,L.foot.y+r()*L.foot.h,s*.22,s*.12,'#e2463a',r()*TAU);}),
  F('giang_sinh','Giáng sinh','🎄','Mùa an lành','#1f5a43','#ffffff','#e5533d','#f3e6c8',SANS,
    (c,L,r)=>{c.fillStyle='#1f5a43';c.fillRect(0,0,L.w,L.h);for(let i=0;i<45;i++)snow(c,r()*L.w,r()*L.h,2+r()*3,'#ffffff66');},
    (c,L,r)=>{const f=L.foot,s=L.big?26:16;pine(c,L.big?66:36,f.y+f.h-s*.9,s);pine(c,L.w-(L.big?66:36),f.y+f.h-s*.8,s*.85,'#3d8f66');
      c.fillStyle='#ffffff';c.beginPath();c.moveTo(0,f.y+f.h);c.quadraticCurveTo(L.w/2,f.y+f.h-(L.big?24:16),L.w,f.y+f.h);c.fill();
      for(const cl of L.cells.slice(0,2)){el(c,cl.x+cl.w-10,cl.y+2,L.big?7:5,L.big?7:5,'#e5533d');el(c,cl.x+cl.w-20,cl.y+4,L.big?6:4,L.big?6:4,'#f2c84b');}}),
];
function bow(c,x,y,s){el(c,x-s*.6,y,s*.6,s*.38,'#ff7aa8',-.3);el(c,x+s*.6,y,s*.6,s*.38,'#ff7aa8',.3);el(c,x,y,s*.22,s*.22,'#e2557f');}
export const FRAME=Object.fromEntries(FRAMES.map(f=>[f.id,f]));

/* ---------------------------------------------------------------- the geometry of a print */
export function size(layout){const l=LAYOUTS[layout]||LAYOUTS.strip;return {w:l.w,h:l.h};}
function stripBox(){
  const cells=[];for(let i=0;i<4;i++)cells.push({x:20,y:44+i*174,w:260,h:162});
  return {w:300,h:900,cells,foot:{x:0,y:728,w:300,h:172},big:false};
}
function bigBox(){return {w:640,h:800,cells:[{x:52,y:56,w:536,h:540}],foot:{x:0,y:596,w:640,h:204},big:true};}

/* ---------------------------------------------------------------- people in the shot */
const SKIN=['#f6d3b8','#eec09c','#d9a27a','#b07a55'];
const SKIN_SHADE=['#e9b998','#dba783','#c48862','#956445'];
function person(c,p,cx,hy,r,pose,lean,sign){
  const skin=SKIN[(p.skin|0)%4]||SKIN[0],shade=SKIN_SHADE[(p.skin|0)%4]||SKIN_SHADE[0],old=p.age==='old',kid=p.age==='kid';
  const hair=p.hair||(old?'#d9d4cc':'#3a2a22'),style=p.style||'short',top=p.top||'#7fb3d5',wear=p.wear||'tee';
  c.save();c.translate(cx,hy);c.rotate(lean);
  // back hair and veil
  if(wear==='bride'){c.fillStyle='#ffffffcc';c.beginPath();c.moveTo(-r*.9,-r*.6);c.quadraticCurveTo(-r*2,r*1.5,-r*1.6,r*3.4);c.lineTo(r*1.6,r*3.4);c.quadraticCurveTo(r*2,r*1.5,r*.9,-r*.6);c.fill();}
  if(style==='long'||style==='pony')rr(c,-r*1.02,-r*.4,r*2.04,r*(style==='long'?2.2:1.2),r*.8,hair);
  if(style==='bun')el(c,0,-r*1.08,r*.42,r*.38,hair);
  if(style==='pigtails'){el(c,-r*1.05,r*.1,r*.32,r*.5,hair);el(c,r*1.05,r*.1,r*.32,r*.5,hair);}
  // body
  const by=r*.92,bw=r*(kid?1.25:1.42);
  c.beginPath();c.moveTo(-bw,r*3.6);c.lineTo(-bw,by+r*.6);c.quadraticCurveTo(-bw,by,-bw+r*.5,by);c.lineTo(bw-r*.5,by);c.quadraticCurveTo(bw,by,bw,by+r*.6);c.lineTo(bw,r*3.6);c.closePath();
  c.fillStyle=wear==='uniform'?'#fbfbf7':wear==='suit'?'#2d3340':wear==='gown'?'#1f2430':wear==='bride'?'#fffdf8':top;c.fill();
  if(wear==='uniform'){poly(c,[[-r*.42,by],[0,by+r*.5],[r*.42,by]],'#e9ece9');ln(c,-r*.42,by,0,by+r*.5,'#c9cdc9',1.2);ln(c,r*.42,by,0,by+r*.5,'#c9cdc9',1.2);if(kid)poly(c,[[-r*.36,by+r*.1],[r*.36,by+r*.1],[r*.1,by+r*.9],[-r*.1,by+r*.9]],'#d8382e');else rr(c,r*.5,by+r*.7,r*.36,r*.22,2,'#3b6fb6');}
  if(wear==='suit'){poly(c,[[-r*.38,by],[0,by+r*1.1],[r*.38,by]],'#ffffff');poly(c,[[-r*.09,by+r*.12],[r*.09,by+r*.12],[r*.12,by+r*.85],[0,by+r*.98],[-r*.12,by+r*.85]],'#c0392b');}
  if(wear==='gown'){poly(c,[[-r*.55,by],[-r*.2,by+r*1.6],[-r*.05,by+r*1.6],[-r*.2,by]],p.top||'#c0392b');poly(c,[[r*.55,by],[r*.2,by+r*1.6],[r*.05,by+r*1.6],[r*.2,by]],p.top||'#c0392b');}
  if(wear==='aodai'){rr(c,-r*.3,by-r*.12,r*.6,r*.3,r*.12,top);ln(c,0,by+r*.18,r*.5,by+r*.5,'#00000022',2);}
  if(wear==='bride'){for(let i=-2;i<=2;i++)el(c,i*r*.25,by+r*.1,r*.08,r*.08,'#f3e3c8');}
  // neck and head
  rr(c,-r*.24,r*.6,r*.48,r*.42,r*.1,shade);
  el(c,-r*.98,r*.08,r*.17,r*.22,skin);el(c,r*.98,r*.08,r*.17,r*.22,skin);
  el(c,0,0,r,r*(kid?1:1.05),skin);
  // front hair
  c.fillStyle=hair;
  if(style==='bald'){el(c,-r*.82,-r*.1,r*.22,r*.35,hair);el(c,r*.82,-r*.1,r*.22,r*.35,hair);}
  else if(style==='spiky'){c.beginPath();c.moveTo(-r*1.02,-r*.1);for(let i=0;i<=6;i++){const a=Math.PI+i*Math.PI/6;c.lineTo(Math.cos(a)*r*1.18*(i%2?1.15:1),Math.sin(a)*r*1.18*(i%2?1.15:1)-r*.05);}c.lineTo(r*1.02,-r*.1);c.quadraticCurveTo(0,-r*.55,-r*1.02,-r*.1);c.fill();}
  else{c.beginPath();c.arc(0,-r*.05,r*1.04,Math.PI*1.02,Math.PI*1.98);c.quadraticCurveTo(r*.45,-r*.62,r*.05,-r*.42);c.quadraticCurveTo(-r*.5,-r*.25,-r*1.02,-r*.02);c.fill();
    if(style==='bob'){rr(c,-r*1.06,-r*.3,r*.34,r*1.05,r*.17,hair);rr(c,r*.72,-r*.3,r*.34,r*1.05,r*.17,hair);}
    if(style==='long'){rr(c,-r*1.06,-r*.3,r*.3,r*1.3,r*.15,hair);rr(c,r*.76,-r*.3,r*.3,r*1.3,r*.15,hair);}}
  if(style==='pony'){el(c,r*.98,-r*.55,r*.22,r*.18,'#e2574c');}
  // face
  const ey=-r*.02,ex=r*.38;
  el(c,-r*.58,r*.32,r*.17,r*.1,'#f19c9c66');el(c,r*.58,r*.32,r*.17,r*.1,'#f19c9c66');
  if(p.eyes==='closed'){arc(c,-ex,ey-r*.06,r*.13,Math.PI*.15,Math.PI*.85,'#3a2a22',r*.07);arc(c,ex,ey-r*.06,r*.13,Math.PI*.15,Math.PI*.85,'#3a2a22',r*.07);}
  else if(p.eyes==='half'){ln(c,-ex-r*.12,ey,-ex+r*.12,ey,'#3a2a22',r*.08);ln(c,ex-r*.12,ey,ex+r*.12,ey,'#3a2a22',r*.08);}
  else{for(const s of [-1,1]){el(c,s*ex,ey,r*.12,r*.15,'#3a2a22');el(c,s*ex+r*.04,ey-r*.05,r*.045,r*.045,'#ffffff');}}
  if(old){arc(c,-ex,ey+r*.2,r*.12,Math.PI*.2,Math.PI*.8,'#00000022',1);arc(c,ex,ey+r*.2,r*.12,Math.PI*.2,Math.PI*.8,'#00000022',1);}
  const my=r*.42,mouth=p.mouth||'smile';
  if(mouth==='grin'){c.beginPath();c.moveTo(-r*.28,my-r*.05);c.quadraticCurveTo(0,my+r*.4,r*.28,my-r*.05);c.closePath();c.fillStyle='#a8434b';c.fill();rr(c,-r*.2,my-r*.05,r*.4,r*.09,2,'#ffffff');}
  else if(mouth==='o')el(c,0,my+r*.05,r*.09,r*.12,'#a8434b');
  else arc(c,0,my-r*.12,r*.2,Math.PI*.2,Math.PI*.8,'#a8434b',r*.07);
  // eyewear and hat
  const eye=p.eyewear||(old&&p.glasses!==false?'kinh_gia':null);   // grandparents wear their own glasses (glasses: false: none)
  if(eye==='kinh_tim'){heart(c,-ex,ey+r*.06,r*.42,'#e8335a');heart(c,ex,ey+r*.06,r*.42,'#e8335a');ln(c,-ex+r*.2,ey-r*.04,ex-r*.2,ey-r*.04,'#e8335a',r*.06);}
  else if(eye==='kinh_ram'){rr(c,-ex-r*.25,ey-r*.17,r*.5,r*.32,r*.12,'#1d1d24');rr(c,ex-r*.25,ey-r*.17,r*.5,r*.32,r*.12,'#1d1d24');ln(c,-ex+r*.25,ey-r*.08,ex-r*.25,ey-r*.08,'#1d1d24',r*.06);el(c,-ex-r*.08,ey-r*.08,r*.08,r*.04,'#ffffff55');}
  else if(eye==='kinh_gia'){arc(c,-ex,ey,r*.22,0,TAU,'#7b6250',r*.05);arc(c,ex,ey,r*.22,0,TAU,'#7b6250',r*.05);ln(c,-ex+r*.22,ey,ex-r*.22,ey,'#7b6250',r*.05);}
  const hat=p.hat;
  if(hat==='mu_tiec'){c.save();c.translate(r*.25,-r*.85);c.rotate(.25);poly(c,[[-r*.45,0],[r*.45,0],[0,-r*1.25]],'#5bb6d9');for(let i=1;i<4;i++){const y=-r*1.25*i/4,w=r*.45*(1-i/4);ln(c,-w,y,w,y,'#f2c84b',r*.1);}el(c,0,-r*1.28,r*.16,r*.16,'#e2574c');c.restore();}
  else if(hat==='non_la'){poly(c,[[-r*1.65,-r*.55],[r*1.65,-r*.55],[0,-r*1.75]],'#efd79a');ln(c,-r*1.65,-r*.55,r*1.65,-r*.55,'#c9a75a',r*.08);for(const k of [.35,.65])ln(c,-r*1.65*(1-k),-r*.55-r*1.2*k,r*1.65*(1-k),-r*.55-r*1.2*k,'#d8bc72',1.2);}
  else if(hat==='mu_tn'){c.save();c.translate(0,-r*.95);cap(c,0,0,r*1.15);c.restore();}
  else if(hat==='tai_tho'){arc(c,0,-r*.1,r*1.02,Math.PI*1.1,Math.PI*1.9,'#ffffff',r*.14);for(const s of [-1,1]){el(c,s*r*.45,-r*1.55,r*.24,r*.7,'#ffffff',s*.2);el(c,s*r*.45,-r*1.5,r*.12,r*.5,'#ffb3cf',s*.2);}}
  else if(hat==='vuong_mien'){poly(c,[[-r*.6,-r*.75],[-r*.62,-r*1.35],[-r*.3,-r*1.0],[0,-r*1.45],[r*.3,-r*1.0],[r*.62,-r*1.35],[r*.6,-r*.75]],'#f2c84b');el(c,0,-r*.95,r*.1,r*.1,'#e2574c');el(c,-r*.38,-r*.88,r*.07,r*.07,'#5bb6d9');el(c,r*.38,-r*.88,r*.07,r*.07,'#5bb6d9');}
  else if(wear==='bride'){for(let i=-2;i<=2;i++)el(c,i*r*.28,-r*.9+Math.abs(i)*r*.08,r*.1,r*.1,'#fff6e6');}
  // hands: pose and what the hand holds
  const hold=p.hold,hx=r*.95,hyy=r*1.6;
  if(pose===1&&!hold){el(c,hx,r*.75,r*.2,r*.22,skin);ln(c,hx-r*.06,r*.6,hx-r*.16,r*.25,skin,r*.11);ln(c,hx+r*.06,r*.6,hx+r*.12,r*.25,skin,r*.11);}
  else if(pose===2&&!hold){el(c,0,r*1.25,r*.18,r*.18,skin);heart(c,0,r*.98,r*.32,'#e8335a');}
  if(hold==='bang_chu'){c.save();c.translate(0,hyy+r*.35);c.rotate(-.06);rr(c,-r*1.1,-r*.42,r*2.2,r*.84,r*.12,'#fffaf0','#c79879',r*.06);c.font=`800 ${Math.round(r*.48)}px ${SANS}`;c.fillStyle='#d0567f';c.textAlign='center';c.textBaseline='middle';c.fillText(String(sign||'BFF').slice(0,10),0,r*.02,r*2);c.restore();el(c,-r*1.0,hyy+r*.35,r*.17,r*.17,skin);el(c,r*1.0,hyy+r*.35,r*.17,r*.17,skin);}
  else if(hold==='hoa'){for(let i=0;i<5;i++)flower(c,-r*.5+(i%3)*r*.35,hyy-r*.1+Math.floor(i/3)*r*.32,r*.28,['#ff8fab','#f2c84b','#ffffff','#d9506c','#ffb3cf'][i],'#f6b23e');poly(c,[[-r*.6,hyy+r*.35],[r*.25,hyy+r*.35],[-r*.15,hyy+r*1.2]],'#b9d7a8');el(c,-r*.15,hyy+r*.6,r*.17,r*.17,skin);}
  else if(hold==='bong_bay'){ln(c,hx,hyy,hx+r*.25,-r*.2,'#9c7b6a',1);balloon(c,hx+r*.3,-r*.95,r*.5,'#e2574c');el(c,hx,hyy,r*.17,r*.17,skin);}
  else if(hold==='long_den'){ln(c,hx,hyy,hx+r*.2,r*.3,'#8b5e3c',r*.08);starLantern(c,hx+r*.55,r*.05,r*.45);el(c,hx,hyy,r*.17,r*.17,skin);}
  c.restore();
}
function backdrop(c,id,w,h){
  const solid={kem:['#f7ecd9','#efdcc0'],hong:['#ffd9e6','#f6b8cd'],mint:['#d6f1e6','#b2e0cd'],den:['#2c2a33','#17161c']}[id];
  if(solid){const g=c.createRadialGradient(w/2,h*.4,h*.1,w/2,h*.45,Math.max(w,h)*.75);g.addColorStop(0,solid[0]);g.addColorStop(1,solid[1]);c.fillStyle=g;c.fillRect(0,0,w,h);return;}
  if(id==='hoa'){c.fillStyle='#fde6ee';c.fillRect(0,0,w,h);const r=rng('hoa-wall');for(let i=0;i<Math.round(w*h/900);i++)flower(c,r()*w,r()*h,6+r()*8,['#ffb3cf','#ffd3a3','#ffffff','#f7a1b9','#c9e7c1'][i%5],'#f6b23e',5,r()*3);return;}
  if(id==='kim_tuyen'){const g=c.createLinearGradient(0,0,w,0);for(let i=0;i<=10;i++)g.addColorStop(i/10,i%2?'#e9c46a':'#d4a64a');c.fillStyle=g;c.fillRect(0,0,w,h);const r=rng('sequin');for(let i=0;i<Math.round(w*h/260);i++)el(c,r()*w,r()*h,1.3,1.3,r()<.5?'#fff6cf':'#b8892f');return;}
  c.fillStyle='#efe6d8';c.fillRect(0,0,w,h);
}
/** One photo in a cell of w × h (origin at its top-left corner). */
export function paintShot(c,shot,w,h){
  shot=shot||{};c.save();c.beginPath();c.rect(0,0,w,h);c.clip();
  backdrop(c,shot.backdrop||'kem',w,h);
  const ppl=(shot.people||[]).slice(0,6),n=Math.max(1,ppl.length);
  // hand the props out: hats to heads, glasses to faces, hand items to hands, in order
  const given=ppl.map(p=>({...p}));
  for(const id of shot.props||[]){const pr=PROP[id];if(!pr)continue;const k=pr.slot==='hat'?'hat':pr.slot==='eyes'?'eyewear':'hold';const who=given.find(p=>!p[k]&&!(k==='hat'&&p.wear==='bride'));if(who)who[k]=id;}
  const r0=Math.min(h*.2,w/(n*2.9)),pose=shot.pose|0;
  const draw=(dx,alpha)=>{c.globalAlpha=alpha;given.forEach((p,i)=>{const kid=p.age==='kid',r=r0*(kid?.82:p.age==='old'?.98:1);
    const cx=w*(i+.5)/n+dx+(n>1?(i-(n-1)/2)*-r0*.12:0),hy=h*(kid?.6:.5)+(i%2?r0*.12:0),lean=pose===3?((i-(n-1)/2)*-.12):(i%2?.04:-.04);
    person(c,p,cx,hy,r,pose===3?0:(pose+i)%3===0?0:pose,lean,shot.sign);});c.globalAlpha=1;};
  const blur=Math.max(0,Math.min(1,Number(shot.blur)||0));
  if(blur){draw(-w*.035*blur,.45);draw(w*.03*blur,.45);draw(0,.55);}else draw(0,1);
  const light=shot.light||'soft';
  if(light==='soft'){const g=c.createRadialGradient(w/2,h*.4,0,w/2,h*.4,w*.75);g.addColorStop(0,'#ffffff22');g.addColorStop(1,'#00000014');c.fillStyle=g;c.fillRect(0,0,w,h);}
  else if(light==='bright'){c.fillStyle='#ffffff1c';c.fillRect(0,0,w,h);}
  else if(light==='warm'){c.fillStyle='#ffb35a26';c.fillRect(0,0,w,h);}
  else if(light==='dim'){c.fillStyle='#14102266';c.fillRect(0,0,w,h);}
  else if(light==='harsh'){c.fillStyle='#ffffff70';c.fillRect(0,0,w,h);const g=c.createRadialGradient(w/2,h*.45,0,w/2,h*.45,w*.4);g.addColorStop(0,'#ffffff66');g.addColorStop(1,'#ffffff00');c.fillStyle=g;c.fillRect(0,0,w,h);}
  c.restore();
}
function emptyCell(c,w,h,frame){
  c.save();c.fillStyle='#ffffff2e';c.fillRect(0,0,w,h);c.setLineDash([6,5]);c.strokeStyle=(frame&&frame.ink)||'#b89a86';c.globalAlpha=.55;c.lineWidth=1.5;c.strokeRect(3,3,w-6,h-6);c.setLineDash([]);
  const s=Math.min(w,h)*.16;rr(c,w/2-s,h/2-s*.6,s*2,s*1.3,s*.25,null,(frame&&frame.ink)||'#b89a86',2);arc(c,w/2,h/2+s*.05,s*.42,0,TAU,(frame&&frame.ink)||'#b89a86',2);c.restore();
}

/* ---------------------------------------------------------------- filters (read back the cell's own pixels) */
const MATRIX={
  den_trang:[.3,.59,.11,.3,.59,.11,.3,.59,.11],co_dien:[.393,.769,.189,.349,.686,.168,.272,.534,.131],
  am:[1.08,.04,0,.02,1,0,0,0,.86],lanh:[.9,0,.04,0,1,.04,.02,.04,1.12],phim:[.9,.12,.05,.06,.86,.06,.05,.1,.78],hong:[1.06,.06,.04,0,.94,.04,.04,.04,1],
};
function filterCell(c,x,y,w,h,id){
  const m=MATRIX[id];if(!m)return;
  const t=c.getTransform(),X=Math.round(t.a*x+t.e),Y=Math.round(t.d*y+t.f),W=Math.round(t.a*w),H=Math.round(t.d*h);
  let img;try{img=c.getImageData(X,Y,W,H);}catch{return;}
  const d=img.data,lift=id==='phim'?14:id==='hong'?8:0;
  for(let i=0;i<d.length;i+=4){const r=d[i],g=d[i+1],b=d[i+2];d[i]=m[0]*r+m[1]*g+m[2]*b+lift;d[i+1]=m[3]*r+m[4]*g+m[5]*b+lift;d[i+2]=m[6]*r+m[7]*g+m[8]*b+lift;}
  if(id==='phim'){const r=rng(`grain${W}x${H}`);for(let i=0;i<d.length;i+=4*3){const k=(r()-.5)*22;d[i]+=k;d[i+1]+=k;d[i+2]+=k;}}
  c.putImageData(img,X,Y);
}

/* ---------------------------------------------------------------- stickers and the date stamp */
function sticker(c,id,x,y,s,rot=0){
  c.save();c.translate(x,y);c.rotate(rot);c.shadowColor='#00000033';c.shadowBlur=3;c.shadowOffsetY=1;
  const o='#ffffff';
  switch(id){
    case 'tim':heart(c,0,0,s*1.15,o);c.shadowColor='transparent';heart(c,0,0,s*.9,'#ff5c8a');el(c,-s*.3,-s*.25,s*.14,s*.1,'#ffffff99',-.6);break;
    case 'sao':star(c,0,0,s*1.05,s*.5,5,o);c.shadowColor='transparent';star(c,0,0,s*.82,s*.38,5,'#ffc93c');break;
    case 'meo':el(c,0,0,s*.95,s*.82,o);poly(c,[[-s*.85,-s*.25],[-s*.65,-s*1.05],[-s*.2,-s*.7]],o);poly(c,[[s*.85,-s*.25],[s*.65,-s*1.05],[s*.2,-s*.7]],o);c.shadowColor='transparent';
      el(c,0,0,s*.8,s*.68,'#f7b267');poly(c,[[-s*.72,-s*.25],[-s*.6,-s*.88],[-s*.25,-s*.6]],'#f7b267');poly(c,[[s*.72,-s*.25],[s*.6,-s*.88],[s*.25,-s*.6]],'#f7b267');
      el(c,-s*.3,-s*.05,s*.08,s*.12,'#3a2a22');el(c,s*.3,-s*.05,s*.08,s*.12,'#3a2a22');el(c,0,s*.18,s*.08,s*.06,'#e2557f');ln(c,-s*.8,s*.15,-s*.42,s*.2,'#3a2a2288',1);ln(c,s*.8,s*.15,s*.42,s*.2,'#3a2a2288',1);break;
    case 'tho':el(c,0,s*.15,s*.9,s*.75,o);el(c,-s*.35,-s*.75,s*.28,s*.65,o);el(c,s*.35,-s*.75,s*.28,s*.65,o);c.shadowColor='transparent';el(c,0,s*.15,s*.75,s*.62,'#fff4f8');
      el(c,-s*.35,-s*.75,s*.18,s*.52,'#fff4f8');el(c,s*.35,-s*.75,s*.18,s*.52,'#fff4f8');el(c,-s*.35,-s*.72,s*.08,s*.38,'#ffb3cf');el(c,s*.35,-s*.72,s*.08,s*.38,'#ffb3cf');
      el(c,-s*.26,s*.08,s*.07,s*.09,'#3a2a22');el(c,s*.26,s*.08,s*.07,s*.09,'#3a2a22');el(c,-s*.45,s*.3,s*.12,s*.07,'#ffb3cf');el(c,s*.45,s*.3,s*.12,s*.07,'#ffb3cf');break;
    case 'hoa':flower(c,0,0,s*1.15,o,o,5);c.shadowColor='transparent';flower(c,0,0,s*.95,'#ffd6e5','#f6b23e',5);break;
    case 'may':cloud(c,0,0,s*.8,o);c.shadowColor='transparent';cloud(c,0,s*.02,s*.66,'#e8f6ff');el(c,-s*.2,0,s*.06,s*.08,'#3a2a22');el(c,s*.2,0,s*.06,s*.08,'#3a2a22');arc(c,0,s*.08,s*.12,.3,2.8,'#3a2a22',1.2);break;
    case 'lap_lanh':sparkle(c,0,0,s*1.05,o);c.shadowColor='transparent';sparkle(c,0,0,s*.85,'#ffe27a');sparkle(c,s*.8,-s*.6,s*.35,'#ffe27a');sparkle(c,-s*.7,s*.6,s*.28,'#ffffff');break;
    case 'vuong_mien':poly(c,[[-s,s*.5],[-s*1.05,-s*.6],[-s*.5,-s*.05],[0,-s*.8],[s*.5,-s*.05],[s*1.05,-s*.6],[s,s*.5]],o);c.shadowColor='transparent';
      poly(c,[[-s*.85,s*.4],[-s*.88,-s*.42],[-s*.45,s*.02],[0,-s*.62],[s*.45,s*.02],[s*.88,-s*.42],[s*.85,s*.4]],'#f2c84b');el(c,0,s*.15,s*.12,s*.12,'#e2574c');break;
    case 'not_nhac':el(c,-s*.3,s*.55,s*.42,s*.32,o,-.3);c.shadowColor='transparent';el(c,-s*.3,s*.55,s*.3,s*.22,'#6c63ff',-.3);ln(c,-s*.02,s*.5,-s*.02,-s*.8,'#6c63ff',s*.14);c.beginPath();c.moveTo(-s*.02,-s*.8);c.quadraticCurveTo(s*.6,-s*.6,s*.5,-s*.1);c.strokeStyle='#6c63ff';c.lineWidth=s*.14;c.stroke();break;
    case 'cau_vong':for(const [k,col] of [[1.12,o],[1,'#ff6b6b'],[.84,'#ffc93c'],[.68,'#6bcB77'],[.52,'#4d96ff']]){c.beginPath();c.arc(0,s*.4,s*k,Math.PI,0);c.lineTo(s*(k-.16),s*.4);c.arc(0,s*.4,s*(k-.16),0,Math.PI,true);c.closePath();c.fillStyle=col;c.fill();if(col===o)c.shadowColor='transparent';}cloud(c,-s*.8,s*.42,s*.26,o);cloud(c,s*.8,s*.42,s*.26,o);break;
    default:star(c,0,0,s,s*.45,5,'#ffc93c');
  }
  c.restore();
}
/** Stickers as ids are laid out by the print: cell corners in turn, tilted a little (always the same for the same list). */
function stickerSpots(list,L){
  const out=[],r=rng(`st|${list.map(s=>typeof s==='string'?s:s.id).join(',')}|${L.cells.length}`);
  list.slice(0,12).forEach((s,i)=>{
    if(s&&typeof s==='object'&&typeof s.x==='number'){const cl=L.cells[Math.max(0,Math.min(L.cells.length-1,s.cell|0))];out.push({id:s.id,x:cl.x+s.x*cl.w,y:cl.y+s.y*cl.h,s:(s.s||1)*(L.big?26:15),r:s.r||0});return;}
    const id=typeof s==='string'?s:s?.id,cl=L.cells[i%L.cells.length],corner=Math.floor(i/L.cells.length+i)%4;
    const px=corner%2?cl.x+cl.w-(L.big?34:18):cl.x+(L.big?34:18),py=corner<2?cl.y+(L.big?32:17):cl.y+cl.h-(L.big?32:17);
    out.push({id,x:px+(r()-.5)*6,y:py+(r()-.5)*6,s:(L.big?26:15)*(.9+r()*.25),r:(r()-.5)*.6});
  });
  return out;
}
function dateStamp(c,L,text){
  const cl=L.cells[L.cells.length-1],size=L.big?22:13;
  c.save();c.font=`700 ${size}px ${MONO}`;c.textAlign='right';c.textBaseline='alphabetic';c.shadowColor='#ff7a1a';c.shadowBlur=size*.5;c.fillStyle='#ff9a3d';
  c.fillText(String(text).slice(0,14),cl.x+cl.w-(L.big?16:8),cl.y+cl.h-(L.big?14:8));c.restore();
}
function fitFont(c,s,max,size,family,weight=800){c.font=`${weight} ${size}px ${family}`;const w=c.measureText(s).width;const k=w>max?Math.max(9,Math.floor(size*max/w)):size;c.font=`${weight} ${k}px ${family}`;return k;}

/* ---------------------------------------------------------------- one strip (or the big frame) */
function drawOne(c,L,shots,frame,deco,opts){
  const r=rng(`frame|${frame.id}|${L.big?'big':'strip'}`),t=opts.t||(s=>s);
  c.fillStyle=frame.bg;c.fillRect(0,0,L.w,L.h);
  if(frame.paper)frame.paper(c,L,r);
  const rad=frame.id==='retro'?2:L.big?14:8;
  L.cells.forEach((cl,i)=>{
    c.save();c.translate(cl.x,cl.y);c.beginPath();c.roundRect(0,0,cl.w,cl.h,rad);c.clip();
    const shot=shots[i];
    if(shot){if(opts.paintShot)opts.paintShot(c,shot,cl.w,cl.h,i);else paintShot(c,shot,cl.w,cl.h);}else emptyCell(c,cl.w,cl.h,frame);
    c.restore();
    if(shot&&deco.filter&&deco.filter!=='none')filterCell(c,cl.x,cl.y,cl.w,cl.h,deco.filter);
    if(frame.edge){c.beginPath();c.roundRect(cl.x,cl.y,cl.w,cl.h,rad);c.strokeStyle=frame.edge;c.lineWidth=L.big?5:3;c.stroke();}
  });
  const r2=rng(`deco|${frame.id}|${L.big?'big':'strip'}`);
  if(frame.deco)frame.deco(c,L,r2);
  for(const s of stickerSpots(deco.stickers||[],L))sticker(c,s.id,s.x,s.y,s.s,s.r);
  if(deco.date)dateStamp(c,L,deco.date);
  // the foot: title, the line under it, the shop's small print
  const f=L.foot,cx=L.w/2,title=t(frame.name),sub=deco.caption?String(deco.caption):t(frame.sub||'');
  c.save();c.textAlign='center';c.textBaseline='middle';c.fillStyle=frame.ink;
  const ts=fitFont(c,title,L.w-(L.big?220:120),L.big?44:28,frame.font||SANS);c.shadowColor='#00000026';c.shadowBlur=2;c.shadowOffsetY=1;
  c.fillText(title,cx,f.y+f.h*(L.big?.42:.4));c.shadowColor='transparent';
  if(sub){fitFont(c,sub,L.w-(L.big?220:100),L.big?17:12,frame.font||SANS,600);c.globalAlpha=.9;c.fillText(sub,cx,f.y+f.h*(L.big?.42:.4)+ts*.85);}
  if(opts.brand){c.globalAlpha=.75;fitFont(c,String(opts.brand),L.w-40,L.big?13:9,SANS,700);c.fillText(String(opts.brand),cx,L.h-(L.big?14:9));}
  c.restore();
}

/** Draw a print. Returns {w, h} (canvas units before scale). */
export function draw(target,strip,frame,deco={},opts={}){
  const layout=LAYOUTS[strip?.layout]?strip.layout:'strip',{w,h}=size(layout);
  const fr=typeof frame==='object'&&frame?frame:FRAME[frame]||FRAME.kawaii;
  const scale=opts.scale||1;let c=target;
  if(target&&typeof target.getContext==='function'){target.width=Math.round(w*scale);target.height=Math.round(h*scale);c=target.getContext('2d');c.setTransform(scale,0,0,scale,0,0);}
  if(!c)return {w,h};
  const shots=(strip?.shots||[]).slice(0,4);
  c.save();
  if(layout==='big')drawOne(c,bigBox(),shots.slice(0,1),fr,deco||{},opts);
  else{
    drawOne(c,stripBox(),shots,fr,deco||{},opts);
    if(layout==='double'){c.translate(300,0);drawOne(c,stripBox(),shots,fr,deco||{},opts);c.translate(-300,0);
      if(deco?.cut){c.save();c.setLineDash([7,6]);c.strokeStyle='#ffffffcc';c.lineWidth=2;c.beginPath();c.moveTo(300,0);c.lineTo(300,h);c.stroke();c.setLineDash([7,6]);c.strokeStyle='#00000055';c.lineWidth=1;c.lineDashOffset=6;c.beginPath();c.moveTo(300,0);c.lineTo(300,h);c.stroke();c.restore();
        c.save();c.font=`20px ${SANS}`;c.textAlign='center';c.textBaseline='middle';c.fillText('✂️',300,16);c.restore();}}
  }
  c.restore();
  return {w,h};
}

/** A small preview of a frame: its paper, ornaments and empty cells. */
export function thumb(target,frame,opts={}){return draw(target,{layout:opts.layout||'strip',shots:[]},frame,{},{scale:opts.scale||.3,t:opts.t});}

/** A key for caching a drawn print. */
export function sig(strip,frame,deco){
  const fr=typeof frame==='object'&&frame?frame.id:frame;
  return JSON.stringify([strip?.layout,strip?.shots||[],fr,deco?.stickers||[],deco?.date||'',deco?.filter||'none',deco?.caption||'',!!deco?.cut]);
}
