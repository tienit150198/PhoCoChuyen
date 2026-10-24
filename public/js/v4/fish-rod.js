/** 🎣 Each rod of game/fishing_content.py RODS looks like itself (owner 25/10 "cần xịn thì nhìn khác đi nữa chứ nhìn cần
 * giống nhau quá"): drawn in code, no image, the same look on the lake (my rod and every other fisher's, `p.rod` on the
 * wire) and in 🎣 Quầy bán cần (rodSvg). Bamboo with its nodes (tre, trúc), woven carbon on a cork grip, a heavy blue
 * sea rod with a chrome reel and a braided line, gold with gold rings and a ruby, platinum with diamonds and an icy
 * glowing line, and Long Vương: red lacquer with gold scales, a jade grip and a golden dragon's head at the tip, a fiery
 * line. Longer, thicker and with a bigger reel the better it is; the top ones glow and sparkle.
 * Pure but for the canvas it is handed (tests/fishing-rod.mjs). Old-Safari safe. */

/** id → {name of the material, len (× the plain rod), w (butt px at scale 1), tip px, body colours (butt → tip), grip,
 * nodes (bamboo rings), weave (carbon), rings (guide colour, how many), reel (radius, colour, rim), gem, head (a
 * dragon), line (colour), glow, spark}. */
export const ROD_LOOK=Object.freeze({
  tre:{mat:'tre',len:1,w:3.6,tip:1.6,body:['#b88a4a','#e0c58a'],grip:null,nodes:5,nodeC:'#7a5726',rings:null,reel:null,gem:null,head:null,line:'rgba(255,255,255,.8)',glow:null,spark:0},
  truc:{mat:'truc',len:1.05,w:3.2,tip:1.4,body:['#6f9a38','#b9dc7a'],grip:'#8a6a3e',nodes:7,nodeC:'#4f7424',rings:null,reel:{r:3.2,c:'#8a5a2b',rim:'#5a3a1a'},gem:null,head:null,line:'rgba(226,255,206,.85)',glow:null,spark:0},
  carbon:{mat:'carbon',len:1.1,w:3,tip:1.1,body:['#23262e','#4b505c'],grip:'#c8a06a',nodes:0,weave:'#6b7280',rings:{c:'#c9ced6',n:4},reel:{r:4,c:'#b8bec8',rim:'#4a4f58'},gem:null,head:null,line:'rgba(255,255,255,.95)',glow:null,spark:0},
  bien:{mat:'bien',len:1.15,w:4.2,tip:1.6,body:['#1d4f8f','#4f9be0'],grip:'#1b1f27',nodes:0,rings:{c:'#e6ebf2',n:5},reel:{r:5.6,c:'#dfe6ee',rim:'#2a6fb8'},gem:null,head:null,line:'#ffd34d',glow:null,spark:0},
  vang:{mat:'vang',len:1.2,w:3.8,tip:1.4,body:['#b8860b','#ffe27a'],grip:'#6b3a12',nodes:0,rings:{c:'#fff1a8',n:5},reel:{r:5.6,c:'#ffd34d',rim:'#9a6a00'},gem:'#e0115f',head:null,line:'#ffe58a',glow:'#ffd34d',spark:2},
  bach_kim:{mat:'bach_kim',len:1.25,w:3.8,tip:1.3,body:['#9aa6b6','#ffffff'],grip:'#3a4a66',nodes:0,rings:{c:'#7fd4ff',n:6},reel:{r:5.8,c:'#eef4fb',rim:'#7fd4ff'},gem:'#b9f2ff',head:null,line:'#9fe8ff',glow:'#9fe8ff',spark:4},
  long_vuong:{mat:'long_vuong',len:1.32,w:4.6,tip:1.8,body:['#8f1010','#e8402c'],grip:'#1f9a5a',nodes:0,scales:'#ffcf26',rings:{c:'#ffcf26',n:6},reel:{r:6.2,c:'#ffcf26',rim:'#8f1010'},gem:'#2fe0a0',head:'#ffcf26',line:'#ff7a3d',glow:'#ff5a2a',spark:6},
});
export const ROD_IDS=Object.freeze(Object.keys(ROD_LOOK));
/** A rod's look ('tre' for one this build does not know). */
export const rodLook=id=>ROD_LOOK[id]||ROD_LOOK.tre;
/** The line's colour of a rod. */
export const lineColor=id=>rodLook(id).line;

const lerp=(a,b,u)=>a+(b-a)*u;
function hex(c){const m=/^#([0-9a-f]{6})$/i.exec(c||'');if(!m)return [200,200,200];const n=parseInt(m[1],16);return [n>>16&255,n>>8&255,n&255];}
const mixHex=(a,b,u)=>{const p=hex(a),q=hex(b);return `rgb(${p.map((v,i)=>Math.round(lerp(v,q[i],u))).join(',')})`;};
/** A point and the direction along a rod bent as a quadratic: butt (bx, by) → tip (x, y) through control (cx, cy). */
function at(R,u){
  const v=1-u,x=v*v*R.bx+2*v*u*R.cx+u*u*R.x,y=v*v*R.by+2*v*u*R.cy+u*u*R.y;
  let dx=2*v*(R.cx-R.bx)+2*u*(R.x-R.cx),dy=2*v*(R.cy-R.by)+2*u*(R.y-R.cy);const l=Math.hypot(dx,dy)||1;dx/=l;dy/=l;
  return {x,y,dx,dy,nx:-dy,ny:dx};
}
/** Draw rod `id` on a canvas: its butt at (bx, by) in the hands, its tip at (x, y), the control (cx, cy) of its bend;
 * `s` the scale (line widths), `t` seconds (the sparkles; null: still), `calm`: reduced motion. */
export function drawRod(c,id,{bx,by,x,y,cx=(bx+x)/2,cy=(by+y)/2,s=1,t=null,calm=false}){
  const L=rodLook(id),R={bx,by,x,y,cx,cy},N=14,k=Math.max(.6,s);
  c.save();c.lineCap='round';c.lineJoin='round';
  if(L.glow&&!calm){c.shadowColor=L.glow;c.shadowBlur=(L.spark>=4?10:7)*k;}
  // the body: a tapering stroke, butt colour to tip colour
  for(let i=0;i<N;i++){const a=at(R,i/N),b=at(R,(i+1)/N),u=(i+.5)/N;
    c.strokeStyle=mixHex(L.body[0],L.body[1],u);c.lineWidth=lerp(L.w,L.tip,u)*k;c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.stroke();}
  c.shadowBlur=0;
  // the grip (cork, rubber, jade)
  if(L.grip){const a=at(R,0),b=at(R,.16);c.strokeStyle=L.grip;c.lineWidth=(L.w+1.6)*k;c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.stroke();}
  // bamboo nodes, carbon weave, dragon scales
  if(L.nodes){c.strokeStyle=L.nodeC;c.lineWidth=1.1*k;for(let i=1;i<=L.nodes;i++){const p=at(R,i/(L.nodes+1)),h=lerp(L.w,L.tip,i/(L.nodes+1))*.75*k+.6;c.beginPath();c.moveTo(p.x-p.nx*h,p.y-p.ny*h);c.lineTo(p.x+p.nx*h,p.y+p.ny*h);c.stroke();}}
  if(L.weave){c.strokeStyle=L.weave;c.lineWidth=.7*k;for(let i=0;i<10;i++){const p=at(R,.2+i*.065),h=lerp(L.w,L.tip,.2+i*.065)*.45*k;c.beginPath();c.moveTo(p.x-p.nx*h-p.dx*h,p.y-p.ny*h-p.dy*h);c.lineTo(p.x+p.nx*h+p.dx*h,p.y+p.ny*h+p.dy*h);c.stroke();}}
  if(L.scales){c.fillStyle=L.scales;for(let i=0;i<9;i++){const u=.2+i*.075,p=at(R,u),h=lerp(L.w,L.tip,u)*.5*k;c.beginPath();c.moveTo(p.x+p.nx*h,p.y+p.ny*h);c.lineTo(p.x+p.dx*h*1.8,p.y+p.dy*h*1.8);c.lineTo(p.x-p.nx*h,p.y-p.ny*h);c.closePath();c.fill();}}
  // the guides: small rings on the underside
  if(L.rings){c.strokeStyle=L.rings.c;c.lineWidth=.9*k;for(let i=0;i<L.rings.n;i++){const u=.3+i*(.62/L.rings.n),p=at(R,u),o=(lerp(L.w,L.tip,u)*.5+1.4)*k;c.beginPath();c.arc(p.x+p.nx*o,p.y+p.ny*o,1.3*k,0,7);c.stroke();}}
  // the reel under the grip
  if(L.reel){const p=at(R,.2),o=(L.w*.5+L.reel.r*.8)*k,rx=p.x+p.nx*o,ry=p.y+p.ny*o,rr=L.reel.r*k;
    c.fillStyle=L.reel.c;c.strokeStyle=L.reel.rim;c.lineWidth=1.1*k;c.beginPath();c.arc(rx,ry,rr,0,7);c.fill();c.stroke();
    c.fillStyle=L.reel.rim;c.beginPath();c.arc(rx,ry,rr*.35,0,7);c.fill();
    c.strokeStyle=L.reel.rim;c.lineWidth=1*k;c.beginPath();c.moveTo(rx,ry);c.lineTo(rx+rr*1.1,ry-rr*.6);c.stroke();}
  // a gem in the butt cap
  if(L.gem){const p=at(R,0),g=2.4*k;c.fillStyle=L.gem;c.strokeStyle='#fff';c.lineWidth=.8*k;c.beginPath();c.moveTo(p.x,p.y-g);c.lineTo(p.x+g,p.y);c.lineTo(p.x,p.y+g);c.lineTo(p.x-g,p.y);c.closePath();c.fill();c.stroke();}
  // 🐉 the dragon's head at the tip, the line leaving its mouth
  if(L.head){const p=at(R,1),h=4.2*k,fx=p.dx,fy=p.dy,nx=p.nx,ny=p.ny,P=(a,b)=>[p.x+fx*a*h+nx*b*h,p.y+fy*a*h+ny*b*h];
    c.fillStyle=L.head;c.strokeStyle='#7a4a00';c.lineWidth=.8*k;c.beginPath();
    for(const [i,q] of [P(-1.2,-.7),P(.3,-.9),P(1.3,-.3),P(1.5,.2),P(.4,.6),P(-1.2,.7)].entries()){if(i)c.lineTo(q[0],q[1]);else c.moveTo(q[0],q[1]);}
    c.closePath();c.fill();c.stroke();
    c.strokeStyle=L.head;c.lineWidth=1*k;for(const sgn of [-1,1]){const a=P(-.6,sgn*.6),b=P(-1.9,sgn*1.3);c.beginPath();c.moveTo(a[0],a[1]);c.lineTo(b[0],b[1]);c.stroke();}   // horns
    const e=P(.5,-.3);c.fillStyle='#d10f0f';c.beginPath();c.arc(e[0],e[1],.9*k,0,7);c.fill();}
  // sparkles along the top rods
  if(L.spark&&t!=null&&!calm){c.fillStyle='#fff';for(let i=0;i<L.spark;i++){const u=((t*.35+i/L.spark)%1),p=at(R,.15+u*.85),a=.5+.5*Math.sin(t*6+i*2);c.globalAlpha=a;const r=(1+a)*k;
    c.beginPath();c.moveTo(p.x,p.y-r*1.6);c.lineTo(p.x+r*.45,p.y);c.lineTo(p.x,p.y+r*1.6);c.lineTo(p.x-r*.45,p.y);c.closePath();c.fill();}c.globalAlpha=1;}
  c.restore();
}
/** The rod's tip after drawRod: where its line leaves (the dragon's mouth for Long Vương). */
export function rodTipOf(id,{x,y,bx,by,cx=(bx+x)/2,cy=(by+y)/2,s=1}){
  const L=rodLook(id);if(!L.head)return [x,y];
  const p=at({bx,by,x,y,cx,cy},1),h=4.2*Math.max(.6,s);return [x+p.dx*h*1.3,y+p.dy*h*1.3];
}
/** The rod as a small picture (🎣 Quầy bán cần, a fisher's card): an SVG `size` px square, the rod corner to corner. */
export function rodSvg(id,size=44,label=''){
  const L=rodLook(id),n=v=>Math.round(v*10)/10,bx=7,by=42,x=7+27*L.len,y=42-27*L.len,cx=bx+(x-bx)*.55+3,cy=by+(y-by)*.55+3,R={bx,by,x,y,cx,cy},N=10,out=[];
  const gid=`rg${id}${Math.round(Math.random()*1e6)}`;
  if(L.glow)out.push(`<defs><filter id="${gid}" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="0" stdDeviation="1.4" flood-color="${L.glow}" flood-opacity=".9"/></filter></defs>`);
  out.push(`<g${L.glow?` filter="url(#${gid})"`:''} stroke-linecap="round">`);
  for(let i=0;i<N;i++){const a=at(R,i/N),b=at(R,(i+1)/N),u=(i+.5)/N;out.push(`<path d="M${n(a.x)} ${n(a.y)}L${n(b.x)} ${n(b.y)}" stroke="${mixHex(L.body[0],L.body[1],u)}" stroke-width="${n(lerp(L.w,L.tip,u)*.9)}"/>`);}
  out.push('</g>');
  if(L.grip){const a=at(R,0),b=at(R,.16);out.push(`<path d="M${n(a.x)} ${n(a.y)}L${n(b.x)} ${n(b.y)}" stroke="${L.grip}" stroke-width="${n(L.w+1.4)}" stroke-linecap="round"/>`);}
  if(L.nodes)for(let i=1;i<=L.nodes;i++){const p=at(R,i/(L.nodes+1)),h=lerp(L.w,L.tip,i/(L.nodes+1))*.7+.5;out.push(`<path d="M${n(p.x-p.nx*h)} ${n(p.y-p.ny*h)}L${n(p.x+p.nx*h)} ${n(p.y+p.ny*h)}" stroke="${L.nodeC}" stroke-width="1"/>`);}
  if(L.scales)for(let i=0;i<6;i++){const u=.25+i*.1,p=at(R,u),h=lerp(L.w,L.tip,u)*.5;out.push(`<path d="M${n(p.x+p.nx*h)} ${n(p.y+p.ny*h)}L${n(p.x+p.dx*h*1.8)} ${n(p.y+p.dy*h*1.8)}L${n(p.x-p.nx*h)} ${n(p.y-p.ny*h)}Z" fill="${L.scales}"/>`);}
  if(L.rings)for(let i=0;i<L.rings.n;i++){const u=.3+i*(.62/L.rings.n),p=at(R,u),o=lerp(L.w,L.tip,u)*.5+1.3;out.push(`<circle cx="${n(p.x+p.nx*o)}" cy="${n(p.y+p.ny*o)}" r="1.2" fill="none" stroke="${L.rings.c}" stroke-width=".9"/>`);}
  if(L.reel){const p=at(R,.2),o=L.w*.5+L.reel.r*.8,rx=p.x+p.nx*o,ry=p.y+p.ny*o;out.push(`<circle cx="${n(rx)}" cy="${n(ry)}" r="${L.reel.r}" fill="${L.reel.c}" stroke="${L.reel.rim}" stroke-width="1"/><circle cx="${n(rx)}" cy="${n(ry)}" r="${n(L.reel.r*.35)}" fill="${L.reel.rim}"/>`);}
  if(L.gem){const p=at(R,0);out.push(`<path d="M${n(p.x)} ${n(p.y-2.6)}l2.6 2.6l-2.6 2.6l-2.6 -2.6Z" fill="${L.gem}" stroke="#fff" stroke-width=".7"/>`);}
  if(L.head){const p=at(R,1),h=3.6,P=(a,b)=>`${n(p.x+p.dx*a*h+p.nx*b*h)} ${n(p.y+p.dy*a*h+p.ny*b*h)}`;
    out.push(`<path d="M${P(-1.2,-.7)}L${P(.3,-.9)}L${P(1.3,-.3)}L${P(1.5,.2)}L${P(.4,.6)}L${P(-1.2,.7)}Z" fill="${L.head}" stroke="#7a4a00" stroke-width=".7"/><path d="M${P(-.6,-.6)}L${P(-1.9,-1.3)}M${P(-.6,.6)}L${P(-1.9,1.3)}" stroke="${L.head}" stroke-width="1"/>`);}
  const tip=L.head?rodTipOf(id,R):[x,y];
  out.push(`<path d="M${n(tip[0])} ${n(tip[1])}Q${n(tip[0]+4)} ${n(tip[1]+14)} ${n(tip[0]+1)} ${n(Math.min(42,tip[1]+26))}" fill="none" stroke="${L.line.startsWith('rgba(255,255,255')?'#9aa7b0':L.line}" stroke-width="1"/>`);
  if(L.spark)for(const [sx,sy] of [[x-6,y+12],[bx+14,by-16],[x+2,y+22]].slice(0,L.spark>=4?3:2))out.push(`<path d="M${n(sx)} ${n(sy-2.4)}l.8 1.6l1.6 .8l-1.6 .8l-.8 1.6l-.8 -1.6l-1.6 -.8l1.6 -.8Z" fill="#fff8d0"/>`);
  return `<svg class="fs-rod" width="${size}" height="${size}" viewBox="0 0 48 48" ${label?`role="img" aria-label="${String(label).replace(/"/g,'')}"`:'aria-hidden="true"'}>${out.join('')}</svg>`;
}
