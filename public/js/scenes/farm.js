/** Farm scene (kind `farm`): Nông Trại Đồi Gió, vegetables and hens on a
 * windy hill. Outdoors, no walls: sky, rolling hills with a windmill and the
 * farmhouse, a back fence with the shed (`warehouse`), seed rack (`shelf`),
 * hen house, farm diary (`evidence`), hay bale for Mướp, well and notice
 * board; on the dirt path in front, vegetable beds (`workbench`), the packing
 * table (`counter`), a stump with the farm ledger (`finance`) and the gate
 * (`door`) in the front fence. PLAN schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,heart,bloom,mascot,streetBoard} from './kit.js';
import {t as tr} from '../v4/i18n.js';

/** Cream name plate centred at cx, top y, sized to its text (shrinks past maxW). */
function plate(c,cx,y,text,fs,dark,maxW,fill=CREAM){const size=fit(c,text,maxW-18,fs,800);c.font=`800 ${size}px "Trebuchet MS", "Segoe UI", sans-serif`;
  const w=Math.min(maxW,c.measureText(tr(String(text))).width+20),h=fs+10;R(c,cx-w/2,y,w,h,fill,7,'#c9a27f',1.5);T(c,text,cx,y+h/2+1,size,dark,800);return h;}
const WOOD='#d8ab80',WOOD_D='#a97b55',CREAM='#fff6e4',ROOF='#d9786a',ROOF_D='#b95d52',TRIM='#fff3e2',SHADOW='#6d553a22';

// Staff stand in the back row; their slots sit on the hen house and hay so
// the seed rack, diary and Mướp stay visible with one or two hands hired.
const PLAN={
 land:{badge:{board:[34,-30]},floor:[115,452,1085,690],lane:505,line:560,home:[600,505],kx:82,ky:45,sway:30,
   blocks:[[96,440,240,466],[230,560,420,596],[480,560,670,596],[440,574,460,594],[760,552,920,588],[990,548,1075,570]],
   bench:[125,662,235,684],garden:[[300,712],[560,712],[860,712]],
   customers:[[300,648],[445,655],[590,648],[735,655]],event:[880,655],officer:[190,610],
   staff:{x:470,step:125,y:462},cat:[782,410],counterSpan:[230,920],
   decor:{corner:[1060,648],front:[955,686],center:[680,684]},sill:{plant:[140,338],lamp:[168,338],seat:[196,338],rug:[330,528]},
   spots:{shelf:[[350,392],60,[[350,505]]],evidence:[[657,382],50,[[657,505]]],workbench:[[325,548],62,[[325,512],[560,512]]],counter:[[840,515],60,[[840,510]]],
     warehouse:[[168,400],55,[[168,508],[272,505]]],board:[[1052,370],48,[[1045,505]]],finance:[[1032,522],42,[[950,558],[1032,606]]],
     property:[[712,292],35,[[712,505]]],security:[[268,345],30,[[285,505]]],door:[[1035,712],45,[[1035,672],[960,665]]],pet:[[782,392],38,[[782,505]]]}},
 port:{badge:{board:[36,-34]},floor:[55,512,645,800],lane:572,line:630,home:[330,572],kx:51,ky:57,sway:24,
   blocks:[[40,498,162,516],[75,625,285,660],[75,705,285,740],[400,628,590,662],[560,742,645,762]],
   bench:[60,782,160,800],garden:[[140,818],[262,818],[560,818]],
   customers:[[380,712],[505,712],[330,775],[205,775]],event:[530,775],officer:[335,648],
   staff:{x:300,step:85,y:526},cat:[540,474],counterSpan:[75,590],
   decor:{corner:[630,605],front:[640,700],center:[180,684]},sill:{plant:[78,402],lamp:[100,402],seat:[122,402],rug:[330,745]},
   spots:{shelf:[[240,440],45,[[240,572]]],evidence:[[462,432],40,[[462,572]]],workbench:[[180,640],56,[[180,600],[312,682]]],counter:[[495,612],56,[[495,594]]],
     warehouse:[[100,450],50,[[100,572]]],board:[[625,418],45,[[620,572]]],finance:[[602,705],42,[[598,712],[530,728]]],
     property:[[400,318],35,[[400,572]]],security:[[185,410],30,[[190,572]]],door:[[410,826],45,[[410,785],[410,752]]],pet:[[540,455],38,[[540,572]]]}},
};

/* ------------------------------------------------------------ Landscape bits */
/** Smooth hill line through pts, filled down to `bottom`. */
function hill(c,pts,bottom,fill){c.beginPath();c.moveTo(pts[0][0],bottom);c.lineTo(pts[0][0],pts[0][1]);
  for(let i=1;i<pts.length-1;i++){const [x,y]=pts[i],[nx,ny]=pts[i+1];c.quadraticCurveTo(x,y,(x+nx)/2,(y+ny)/2);}
  const last=pts[pts.length-1];c.lineTo(last[0],last[1]);c.lineTo(last[0],bottom);c.closePath();c.fillStyle=fill;c.fill();}
function sky(c,x,y,w,h){const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#b9e0ee');g.addColorStop(.7,'#dff1ef');g.addColorStop(1,'#f3f8e6');c.fillStyle=g;c.fillRect(x,y,w,h);}
function sun(c,x,y,r,t){E(c,x,y,r*1.9,r*1.9,'#fff6cf66');c.save();c.translate(x,y);c.rotate(t*.06);
  for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,Math.cos(a)*r*1.25,Math.sin(a)*r*1.25,Math.cos(a)*r*1.55,Math.sin(a)*r*1.55,'#ffe29a',r*.12);}c.restore();
  E(c,x,y,r,r,'#ffe49a');E(c,x-r*.12,y-r*.12,r*.78,r*.78,'#fff0bd');E(c,x-r*.3,y-r*.05,r*.08,r*.1,'#a77a55');E(c,x+r*.3,y-r*.05,r*.08,r*.1,'#a77a55');
  E(c,x-r*.48,y+r*.2,r*.14,r*.08,'#f4b39a');E(c,x+r*.48,y+r*.2,r*.14,r*.08,'#f4b39a');c.beginPath();c.arc(x,y+r*.12,r*.16,0,Math.PI);c.strokeStyle='#a77a55';c.lineWidth=Math.max(1.5,r*.06);c.stroke();}
function cloud(c,x,y,s){E(c,x+4*s,y+14*s,48*s,8*s,'#cfe6ec66');E(c,x,y,32*s,17*s,'#ffffff');E(c,x-26*s,y+5*s,21*s,13*s,'#ffffff');E(c,x+27*s,y+4*s,23*s,14*s,'#ffffff');E(c,x+4*s,y-10*s,20*s,15*s,'#ffffff');}
/** Windmill on the far hill; hub at (x,y), tower down to y+85s. */
function windmill(c,x,y,s,t){P(c,[[x-9*s,y],[x+9*s,y],[x+17*s,y+86*s],[x-17*s,y+86*s]],'#fff8ec');L(c,x-9*s,y,x-17*s,y+86*s,'#d9c3a7',1.5);L(c,x+9*s,y,x+17*s,y+86*s,'#d9c3a7',1.5);
  R(c,x-6*s,y+62*s,12*s,24*s,'#c9a27f',6*s);c.save();c.translate(x,y);c.rotate(t*.9);
  for(let i=0;i<4;i++){c.rotate(Math.PI/2);R(c,-6*s,-48*s,12*s,40*s,'#fffdf6',5*s,'#d7c2a8',1.5);L(c,0,-46*s,0,-10*s,'#e6d5bd',1.2);}
  c.restore();E(c,x,y,7*s,7*s,ROOF);E(c,x,y,3*s,3*s,TRIM);}
/** The farmhouse far up the hill (the `property` hotspot). */
function farmhouse(c,x,y,s){E(c,x+36*s,y-14*s,16*s,20*s,'#8fbf86');E(c,x+44*s,y-24*s,12*s,14*s,'#a3cd92');L(c,x+38*s,y-4*s,x+38*s,y+2*s,WOOD_D,3*s);
  R(c,x-24*s,y-26*s,48*s,27*s,'#fff3dd',4*s,'#c9a27f',1.5);P(c,[[x-31*s,y-24*s],[x,y-46*s],[x+31*s,y-24*s]],ROOF);L(c,x-31*s,y-24*s,x,y-46*s,ROOF_D,2);L(c,x+31*s,y-24*s,x,y-46*s,ROOF_D,2);
  R(c,x-6*s,y-15*s,12*s,16*s,'#c9855f',3*s);R(c,x+10*s,y-20*s,9*s,8*s,'#bfe1ea',2*s);R(c,x-19*s,y-20*s,9*s,8*s,'#bfe1ea',2*s);R(c,x+12*s,y-50*s,7*s,12*s,'#c98f76',2*s);}
function tree(c,x,y,s){L(c,x,y,x,y-14*s,WOOD_D,4*s);E(c,x,y-24*s,17*s,15*s,'#94c486');E(c,x-7*s,y-29*s,9*s,8*s,'#a9d497');}
/** Row of fence posts and two rails from x0 to x1, standing on y. */
function fence(c,x0,x1,y,h){R(c,x0,y-h*.78,x1-x0,6,'#ecd0a8',3,'#c29a73',1.2);R(c,x0,y-h*.38,x1-x0,6,'#ecd0a8',3,'#c29a73',1.2);
  for(let x=x0+14;x<x1-4;x+=44){R(c,x-5,y-h,10,h+3,'#efd4ad',4,'#b88f68',1.5);P(c,[[x-5,y-h+1],[x,y-h-6],[x+5,y-h+1]],'#efd4ad');}}
function sunflower(c,x,y,h,s,t){const sw=Math.sin(t*1.3+x)*3*s;L(c,x,y,x+sw,y-h,'#7fae63',4*s);
  c.save();c.translate(x+sw*.4,y-h*.45);c.rotate(-.6);E(c,-9*s,0,11*s,5*s,'#8fbd72');c.restore();c.save();c.translate(x+sw*.5,y-h*.6);c.rotate(.6);E(c,9*s,0,11*s,5*s,'#8fbd72');c.restore();
  for(let i=0;i<10;i++){const a=i*Math.PI/5;E(c,x+sw+Math.cos(a)*12*s,y-h+Math.sin(a)*12*s,7*s,7*s,'#f6c847');}E(c,x+sw,y-h,9*s,9*s,'#9a6a45');E(c,x+sw-2*s,y-h-2*s,4*s,4*s,'#b98357');}
function tufts(c,x0,y0,x1,y1,n,seed=1){for(let i=0;i<n;i++){const x=x0+((i*97+seed*31)%1000)/1000*(x1-x0),y=y0+((i*53+seed*17)%1000)/1000*(y1-y0);
  L(c,x-4,y,x-6,y-7,'#a9cf85',2);L(c,x,y,x,y-9,'#a9cf85',2);L(c,x+4,y,x+6,y-7,'#a9cf85',2);}}

/* ------------------------------------------------------------ Back row */
/** Red-roofed shed with barn doors: the `warehouse`. (x, y) = left, ground. */
function shed(c,x,y,w,h,label,fs,dark,locked){const top=y-h,cx=x+w/2,peak=top-h*.5;
  E(c,cx,y+2,w*.58,9,SHADOW);R(c,x,top,w,h,'#f1d2a6',6,'#b98a66',2);
  for(let i=1;i<6;i++)L(c,x+i*w/6,top+6,x+i*w/6,y-4,'#e3c092',1.5);
  P(c,[[x-14,top+10],[cx,peak-4],[x+w+14,top+10]],ROOF_D);P(c,[[x-7,top+5],[cx,peak+5],[x+w+7,top+5]],ROOF);
  L(c,x-12,top+10,cx,peak-2,TRIM,4);L(c,x+w+12,top+10,cx,peak-2,TRIM,4);
  // Loft window above a little ledge (the "window" sill for decor).
  E(c,cx,top-h*.2,h*.12,h*.12,'#fff3e2');E(c,cx,top-h*.2,h*.095,h*.095,'#bfe1ea');L(c,cx-h*.095,top-h*.2,cx+h*.095,top-h*.2,TRIM,2);L(c,cx,top-h*.295,cx,top-h*.105,TRIM,2);
  R(c,x+w*.18,top-4,w*.64,8,'#e8c39a',3,'#b98a66',1.2);
  // Label plate and barn doors with white braces.
  plate(c,cx,top+8,label,fs,dark,w-14);
  const dh=h*.58,dw=w*.3;for(const dx of [-dw,0]){R(c,cx+dx,y-dh,dw,dh,'#d9786a',3,'#b95d52',1.5);R(c,cx+dx+3,y-dh+3,dw-6,dh-6,'#00000000',2,TRIM,2.5);L(c,cx+dx+4,y-dh+4,cx+dx+dw-4,y-4,TRIM,2.5);L(c,cx+dx+dw-4,y-dh+4,cx+dx+4,y-4,TRIM,2.5);}
  E(c,cx-5,y-dh/2,2.5,2.5,'#8a5a45');E(c,cx+5,y-dh/2,2.5,2.5,'#8a5a45');
  if(locked){R(c,cx-9,y-dh/2+2,18,16,'#e3cf8e',4,'#a59470',1.5);c.beginPath();c.arc(cx,y-dh/2+2,6,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=3;c.stroke();E(c,cx,y-dh/2+9,2,2.5,'#7b6d55');}
  // A sack and a pitchfork leaning by the door.
  E(c,x+w-12,y-12,13,14,'#e9d7b0');E(c,x+w-12,y-26,7,4,'#d6c192');L(c,x+10,y,x+18,y-h*.62,WOOD_D,3);for(const d of [-4,0,4])L(c,x+18+d,y-h*.62,x+19+d*1.4,y-h*.62-14,'#9aa3a6',2);}
/** Wooden post with a birdhouse or lantern; camera and bell when installed. */
function securityPost(c,x,y,h,s,items,t){L(c,x,y,x,y-h,WOOD_D,7*s);E(c,x,y+1,10*s,3*s,SHADOW);const top=y-h;
  if(items.includes('light')){const g=c.createRadialGradient(x,top-10*s,0,x,top-10*s,70*s);g.addColorStop(0,'#ffe1a466');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(x-70*s,top-80*s,140*s,140*s);
    R(c,x-10*s,top-24*s,20*s,24*s,'#fff0b8',6*s,'#b69b79',2);P(c,[[x-13*s,top-22*s],[x,top-33*s],[x+13*s,top-22*s]],'#b69b79');}
  else{R(c,x-13*s,top-22*s,26*s,23*s,'#f4c9a8',4*s,'#c79b85',1.5);P(c,[[x-17*s,top-20*s],[x,top-36*s],[x+17*s,top-20*s]],ROOF);E(c,x,top-12*s,4*s,4*s,'#7a5a48');L(c,x,top-4*s,x,top-2*s,WOOD_D,2);}
  if(items.includes('camera')){L(c,x,top+26*s,x-14*s,top+20*s,'#b79b85',4*s);R(c,x-44*s,top+10*s,34*s,19*s,'#f5f2eb',6*s,'#a7aaa2',2);E(c,x-42*s,top+19*s,6*s,7*s,'#7a8992');E(c,x-42*s,top+19*s,3*s,3.5*s,'#b4d9df');E(c,x-16*s,top+15*s,2,2,'#90bd8b');}
  if(items.includes('bell')){L(c,x,top+14*s,x+22*s,top+14*s,WOOD_D,4*s);L(c,x+20*s,top+14*s,x+20*s,top+22*s,'#ac8f73',2);const sw=Math.sin(t*2)*1.5*s;P(c,[[x+11*s+sw,top+37*s],[x+29*s+sw,top+37*s],[x+26*s+sw,top+23*s],[x+14*s+sw,top+23*s]],'#f0ce85');E(c,x+20*s+sw,top+39*s,3.5*s,3*s,'#d4ad64');}}
/** Seed rack: the `shelf`. (cx, y) = centre, ground. */
function seedRack(c,cx,y,w,h,fs,dark){const x=cx-w/2,top=y-h,ph=fs+12;E(c,cx,y+2,w*.6,7,SHADOW);
  L(c,x+6,y,x+6,top+ph,WOOD_D,5);L(c,x+w-6,y,x+w-6,top+ph,WOOD_D,5);R(c,x,top+ph-4,w,h-ph-6,WOOD,7,WOOD_D,2);R(c,x+6,top+ph+2,w-12,h-ph-18,'#fff1dc',5);
  const cols=['#f2b8a0','#b8d89a','#f4d27a','#c5b4e0','#9fcfe0','#f5c6d4'],rows=3,rh=(h-ph-18)/rows,n=Math.max(3,Math.floor((w-16)/19));
  for(let r=0;r<rows;r++){const yy=top+ph+2+(r+1)*rh;for(let i=0;i<n;i++){const px=x+10+i*(w-20)/n,col=cols[(r*2+i)%6],pw=(w-20)/n-4;R(c,px,yy-rh+5,pw,rh-9,col,3,'#c0a288',1);E(c,px+pw/2,yy-rh/2-1,pw*.22,pw*.22,'#fffaf0');}R(c,x+4,yy-4,w-8,5,'#c99a6c',2);}
  plate(c,cx,top-4,'HẠT GIỐNG',fs,dark,w+22);}
function chicken(c,x,y,s,face,t,i,chick=false){const peck=Math.max(0,Math.sin(t*2.2+i*1.7))**8,bob=Math.sin(t*3+i)*.8;c.save();c.translate(x,y);c.scale(face*s,s);
  E(c,0,1,15,4,SHADOW);L(c,-4,-6,-4,0,'#e3a24a',2);L(c,4,-6,4,0,'#e3a24a',2);
  if(chick){E(c,0,-10+bob,11,9,'#ffe07a');E(c,7,-17+bob+peck*4,7,7,'#ffe58c');P(c,[[13,-18+peck*4],[18,-16+peck*4],[13,-14+peck*4]],'#f2a94b');E(c,9,-19+peck*4,1.4,1.6,'#5a4337');c.restore();return;}
  P(c,[[-12,-16+bob],[-22,-30+bob],[-17,-14+bob]],'#f1e6d4');P(c,[[-10,-15+bob],[-18,-27+bob],[-6,-20+bob]],'#fffaf0');
  E(c,0,-14+bob,16,12,'#fffaf0');E(c,-3,-14+bob,9,6,'#efe3cf');
  const hy=-27+bob+peck*10,hx=10+peck*4;E(c,hx,hy,8,8,'#fffaf0');E(c,hx,hy-8,4,3.5,'#e5806e');E(c,hx-4,hy-7,3,3,'#e5806e');
  P(c,[[hx+7,hy-1],[hx+13,hy+1],[hx+7,hy+3]],'#f2b84b');E(c,hx+6,hy+6,2,3,'#e5806e');E(c,hx+3,hy-1,1.5,1.8,'#5a4337');E(c,hx+1,hy+3,2.4,1.4,'#f6b5a8');c.restore();}
/** Hen house with a wire run and hens; (x, y) = left of the house, ground. */
function coop(c,x,y,s,t,label,fs,dark){const hw=80*s,hh=60*s,top=y-hh,rx=x+hw-4*s,rw=100*s,rh=44*s;
  E(c,x+(hw+rw)/2,y+2,(hw+rw)*.55,8,SHADOW);R(c,rx,y-rh,rw,rh,'#f7eed866',4,'#c8ab88',2);
  chicken(c,rx+28*s,y-3,.85*s,1,t,0);chicken(c,rx+70*s,y-2,.8*s,-1,t,1);
  c.save();c.globalAlpha=.55;for(let i=1;i<7;i++)L(c,rx+i*rw/7,y-rh+2,rx+i*rw/7,y-2,'#b89c7c',1);for(let j=1;j<3;j++)L(c,rx+2,y-rh+j*rh/3,rx+rw-2,y-rh+j*rh/3,'#b89c7c',1);c.restore();
  L(c,rx,y-rh,rx+rw,y-rh,WOOD_D,3);L(c,rx+rw,y-rh,rx+rw,y,WOOD_D,3);
  R(c,x,top,hw,hh,'#fff1dc',6,'#c79b85',2);for(let i=1;i<4;i++)L(c,x+4,top+i*hh/4,x+hw-4,top+i*hh/4,'#f0dcc0',1.5);
  P(c,[[x-9*s,top+6*s],[x+hw/2,top-30*s],[x+hw+9*s,top+6*s]],ROOF_D);P(c,[[x-4*s,top+3*s],[x+hw/2,top-24*s],[x+hw+4*s,top+3*s]],ROOF);
  E(c,x+hw/2,top-6*s,6*s,7.5*s,'#fffaf0');
  R(c,x+hw/2-13*s,y-34*s,26*s,34*s,'#8a6a55',13*s);E(c,x+hw/2,y-24*s,8*s,7*s,'#fffaf0');E(c,x+hw/2+6*s,y-30*s,3.5*s,2.8*s,'#e5806e');
  P(c,[[x+hw/2-11*s,y],[x+hw/2+11*s,y],[x+hw/2+18*s,y+6*s],[x+hw/2-18*s,y+6*s]],WOOD);
  if(label)plate(c,x+hw/2,top+6*s,label,fs,dark,hw-8*s);}
/** Farm diary pinned under a little roof on a post: `evidence`. */
function diaryPost(c,x,y,s,fs,dark,prim){E(c,x,y+1,14*s,4*s,SHADOW);L(c,x,y,x,y-66*s,WOOD_D,8*s);
  R(c,x-38*s,y-122*s,76*s,58*s,WOOD,8*s,WOOD_D,2);P(c,[[x-46*s,y-118*s],[x,y-142*s],[x+46*s,y-118*s]],ROOF);L(c,x-46*s,y-118*s,x+46*s,y-118*s,ROOF_D,3);
  R(c,x-31*s,y-112*s,30*s,40*s,'#fffaf0',3,'#cfb48f',1);R(c,x+1*s,y-112*s,30*s,40*s,'#fffaf0',3,'#cfb48f',1);
  for(let i=0;i<4;i++){L(c,x-26*s,y-102*s+i*8*s,x-6*s,y-102*s+i*8*s,i?'#c9bba8':prim,1.5);L(c,x+6*s,y-102*s+i*8*s,x+26*s,y-102*s+i*8*s,i===2?prim:'#c9bba8',1.5);}
  L(c,x+14*s,y-112*s,x+14*s,y-96*s,ROOF,3);bloom(c,x+22*s,y-78*s,5*s,'#f6c847');
  plate(c,x,y-62*s,'NHẬT KÝ',fs,dark,100*s);}
/** Hay bales: Mướp naps on top. */
function hayBale(c,x,y,s){E(c,x,y+2,50*s,7*s,SHADOW);R(c,x-46*s,y-40*s,92*s,40*s,'#efd27f',12*s,'#c9a458',2);
  for(let i=0;i<7;i++)L(c,x-38*s+i*12*s,y-34*s,x-34*s+i*12*s,y-6*s,'#dcb862',1.5);L(c,x-22*s,y-40*s,x-22*s,y,'#b98d4a',3*s);L(c,x+22*s,y-40*s,x+22*s,y,'#b98d4a',3*s);
  R(c,x+34*s,y-22*s,34*s,22*s,'#f2d98e',8*s,'#c9a458',1.5);L(c,x+51*s,y-22*s,x+51*s,y,'#b98d4a',2.5*s);}
/** Stone well with a little red roof. */
function well(c,x,y,s,t){E(c,x,y+2,46*s,7*s,SHADOW);R(c,x-36*s,y-116*s,7*s,80*s,WOOD_D,3);R(c,x+29*s,y-116*s,7*s,80*s,WOOD_D,3);
  P(c,[[x-50*s,y-108*s],[x,y-140*s],[x+50*s,y-108*s]],ROOF_D);P(c,[[x-44*s,y-111*s],[x,y-134*s],[x+44*s,y-111*s]],ROOF);
  L(c,x-30*s,y-94*s,x+30*s,y-94*s,WOOD_D,4*s);L(c,x+30*s,y-94*s,x+40*s,y-84*s,WOOD_D,3*s);const sw=Math.sin(t*1.4)*2*s;L(c,x,y-94*s,x+sw,y-66*s,'#c9a27f',2);
  P(c,[[x-9*s+sw,y-66*s],[x+9*s+sw,y-66*s],[x+7*s+sw,y-52*s],[x-7*s+sw,y-52*s]],'#8fb8d1');L(c,x-9*s+sw,y-66*s,x+9*s+sw,y-66*s,'#6f98b1',2);
  E(c,x,y-42*s,38*s,9*s,'#e8e2d6');E(c,x,y-42*s,30*s,6*s,'#8fbfd6');R(c,x-38*s,y-42*s,76*s,42*s,'#dcd5c8',12*s,'#aaa192',2);
  for(const [dx,dy] of [[-24,-30],[0,-32],[24,-30],[-12,-14],[12,-14],[-30,-12],[30,-12]])E(c,x+dx*s,y+dy*s,9*s,6*s,'#cbc3b4');}
function boardPost(c,p,x,y,s){L(c,x-18*s,y,x-18*s,y-40*s,WOOD_D,6*s);L(c,x+18*s,y,x+18*s,y-40*s,WOOD_D,6*s);streetBoard(c,p,x-32.5*s,y-40*s-77*s,s);}
/** Wooden farm sign with the mascot, hung from two posts. */
function woodSign(c,p,x,y,w,h,titleSize,subSize,postTo){R(c,x+40,y+h-20,14,postTo-(y+h-20),'#b5875f',6,'#946443',1.5);R(c,x+w-54,y+h-20,14,postTo-(y+h-20),'#b5875f',6,'#946443',1.5);
  R(c,x-5,y+7,w+10,h,'#946443',30);R(c,x,y,w,h,'#c98f5f',28,'#946443',3);R(c,x+11,y+11,w-22,h-22,'#fff6e2',22,'#e3c49c',2);
  for(const dx of [-6,6])E(c,x+w-40+dx,y+8,9,5,'#8fbf72');L(c,x+w-40,y+12,x+w-40,y+2,'#6f9e58',2);
  mascot(c,x+54,y+h/2+3,.6);const cx=x+w/2+22;T(c,p.title,cx,y+h*.42,fit(c,p.title,w-150,titleSize,800),p.dark,800);T(c,p.sub,cx,y+h*.76,fit(c,p.sub,w-130,subSize),p.dark);heart(c,x+w-34,y+h/2+6,.36,p.primary);}

/* ------------------------------------------------------------ Front */
function crop(c,kind,x,y,s,t){const sw=Math.sin(t*1.7+x*.07)*2*s;
  if(kind==='carrot'){for(const d of [-6,0,6])L(c,x,y-2*s,x+d*s+sw,y-22*s+Math.abs(d)*s,'#7fb46a',3*s);for(const d of [-6,0,6])E(c,x+d*s+sw,y-22*s+Math.abs(d)*s,3.5*s,3*s,'#96c47c');E(c,x,y,6*s,4*s,'#ee9a4f');}
  else if(kind==='cabbage'){E(c,x-10*s,y-4*s,10*s,6*s,'#86bb88');E(c,x+10*s,y-4*s,10*s,6*s,'#86bb88');E(c,x,y-9*s,12*s,11*s,'#b9dcae');E(c,x,y-11*s,7*s,6*s,'#d3ebc4');L(c,x,y-18*s,x,y-3*s,'#9dcb98',1.5);}
  else{E(c,x+sw*.3,y-6*s,14*s,9*s,'#8cc47a');E(c,x-7*s+sw*.4,y-10*s,8*s,7*s,'#a8d38a');E(c,x+7*s+sw*.4,y-10*s,8*s,7*s,'#a8d38a');E(c,x+sw*.5,y-13*s,7*s,6*s,'#c5e3a2');}}
/** Raised vegetable bed on the block [x0,y0,x1,y1], two rows of crops. */
function bed(c,[x0,y0,x1,y1],rows,s,t){const w=x1-x0,d=y1-y0;E(c,(x0+x1)/2,y1+3,w/2+10,6,SHADOW);
  R(c,x0-4,y0-10,w+8,d+13,'#a9784f',14);R(c,x0,y0-14,w,d,'#c4915f',12);L(c,x0+12,y0-14+d*.36,x1-12,y0-14+d*.36,'#b3804f',2);L(c,x0+12,y0-14+d*.72,x1-12,y0-14+d*.72,'#b3804f',2);
  rows.forEach((kind,r)=>{const yy=y0-10+r*d*.46,n=Math.floor((w-20)/(30*s));for(let i=0;i<n;i++)crop(c,kind,x0+14*s+(i+.5+(r%2)*.3)*(w-28*s)/n-((r%2)*6*s),yy,s,t);});}
function scarecrow(c,x,y,s,p,t){const sw=Math.sin(t*1.1)*1.5*s;E(c,x,y+1,12*s,3*s,SHADOW);L(c,x,y,x,y-92*s,WOOD_D,6*s);L(c,x-34*s,y-62*s+sw,x+34*s,y-62*s-sw,WOOD_D,5*s);
  P(c,[[x-31*s,y-70*s+sw],[x+31*s,y-70*s-sw],[x+19*s,y-30*s],[x-19*s,y-30*s]],'#9cc3d8');R(c,x+4*s,y-52*s,11*s,11*s,'#f3d27a',2);L(c,x+4*s,y-47*s,x+15*s,y-47*s,'#d9a94a',1);
  for(const d of [-1,1])for(const k of [-3,0,3])L(c,x+d*33*s,y-62*s+k*s-sw*d,x+d*41*s,y-58*s+k*1.6*s-sw*d,'#e3c05f',2);
  E(c,x,y-82*s,14*s,14*s,'#f2dfb2');E(c,x-5*s,y-84*s,1.8*s,2.2*s,'#6a5944');E(c,x+5*s,y-84*s,1.8*s,2.2*s,'#6a5944');E(c,x-8*s,y-78*s,3*s,2*s,'#efa7a0');E(c,x+8*s,y-78*s,3*s,2*s,'#efa7a0');
  c.beginPath();c.arc(x,y-79*s,4*s,0,Math.PI);c.strokeStyle='#a77a55';c.lineWidth=1.5;c.stroke();
  E(c,x,y-93*s,24*s,5*s,'#e3b95e');R(c,x-12*s,y-110*s,24*s,18*s,'#e8c36a',7*s);R(c,x-12*s,y-98*s,24*s,4*s,ROOF,2);}
function crate(c,x,y,w,h,kind,s){R(c,x,y-h,w,h,'#dcb27f',4,'#a97b55',1.5);L(c,x+3,y-h/2,x+w-3,y-h/2,'#c49763',1.5);
  const n=Math.max(2,Math.floor(w/(12*s)));for(let i=0;i<n;i++){const cx=x+(i+.5)*w/n;
    if(kind==='carrot'){E(c,cx,y-h-2*s,4.5*s,8*s,'#ee9a4f');L(c,cx,y-h-9*s,cx-3*s,y-h-17*s,'#7fb46a',2);L(c,cx,y-h-9*s,cx+3*s,y-h-17*s,'#7fb46a',2);}
    else if(kind==='tomato'){E(c,cx,y-h-4*s,6*s,5.5*s,'#e87a6a');E(c,cx-2*s,y-h-6*s,2*s,1.5*s,'#f6a898');L(c,cx-2*s,y-h-9*s,cx+2*s,y-h-9*s,'#7fb46a',2);}
    else{E(c,cx,y-h-4*s,7*s,7*s,'#8cc47a');E(c,cx,y-h-7*s,4*s,4*s,'#c5e3a2');}}}
function eggTray(c,x,y,w,s){R(c,x,y-10*s,w,10*s,'#f3e3c4',4,'#cfb48f',1);const n=Math.floor(w/(13*s));for(let i=0;i<n;i++){const ex=x+(i+.5)*w/n;E(c,ex,y-13*s,5.5*s,7*s,i%3===1?'#f4dcc0':'#fffaf0');E(c,ex-1.5*s,y-15*s,1.5*s,2*s,'#ffffff');}}
/** Packing table with crates and eggs: the `counter`. */
function packTable(c,[x0,y0,x1,y1],s,fs,p,broken){const w=x1-x0,top=y0-16*s;E(c,(x0+x1)/2,y1+3,w/2+12,7,SHADOW);
  R(c,x0+4*s,top+6,9*s,y1-top-6,'#b98a66',3);R(c,x1-13*s,top+6,9*s,y1-top-6,'#b98a66',3);R(c,x0+6*s,y1-16*s,w-12*s,6*s,WOOD,3);
  eggTray(c,x0+22*s,y1-10*s,46*s,s*.85);crate(c,x1-66*s,y1-10*s,44*s,16*s,'lettuce',s*.8);
  R(c,x0-8*s,top-4*s,w+16*s,14*s,'#e6bd99',6,'#b99476',2);R(c,x0-4*s,top-2*s,w+8*s,4*s,'#f5d7b6',2);
  plate(c,(x0+x1)/2,top+12*s,'ĐÓNG HÀNG',fs,p.dark,w-24*s);
  const ct=top-4*s;crate(c,x0+2*s,ct,44*s,24*s,'carrot',s);crate(c,x0+50*s,ct,44*s,24*s,'lettuce',s);eggTray(c,x0+100*s,ct,w-104*s,s);
  // A kraft label tag: "nhãn nói thật".
  L(c,x1-2*s,ct,x1+8*s,ct+14*s,'#c9a27f',1.5);R(c,x1+2*s,ct+12*s,18*s,13*s,'#fff3dc',3,'#c9a27f',1);heart(c,x1+11*s,ct+20*s,.22*s,p.primary);
  if(broken){L(c,x0+8*s,top+10,x0+8*s,top+20*s,'#c9a27f',1.5);plate(c,x0+8*s,top+20*s,'CẦN KIỂM',fs,'#94643d',150,'#f7d995');}}
/** Tree stump desk with the ledger and a coin jar: `finance`. */
function stump(c,cx,y,s,fs,label,p){E(c,cx,y+3,48*s,7*s,SHADOW);E(c,cx-38*s,y-3*s,10*s,5*s,'#b07c4d');E(c,cx+38*s,y-3*s,10*s,5*s,'#b07c4d');
  R(c,cx-38*s,y-38*s,76*s,38*s,'#c28c5c',12*s,'#9c6d45',2);for(const d of [-24,-8,10,26])L(c,cx+d*s,y-30*s,cx+d*s+2,y-6*s,'#a8764a',1.5);
  E(c,cx,y-38*s,38*s,10*s,'#f0d2a4');E(c,cx,y-38*s,26*s,6.5*s,'#e5c08e');E(c,cx,y-38*s,13*s,3.5*s,'#f0d2a4');
  P(c,[[cx-32*s,y-44*s],[cx,y-40*s],[cx,y-60*s],[cx-30*s,y-64*s]],'#fffaf0');P(c,[[cx+22*s,y-44*s],[cx,y-40*s],[cx,y-60*s],[cx+22*s,y-64*s]],'#fffaf0');L(c,cx,y-40*s,cx,y-60*s,'#cfb48f',1.5);
  for(let i=0;i<3;i++){L(c,cx-26*s,y-57*s+i*5*s,cx-5*s,y-54*s+i*5*s,i?'#c9bba8':p.primary,1.5);L(c,cx+4*s,y-54*s+i*5*s,cx+18*s,y-57*s+i*5*s,'#c9bba8',1.5);}
  R(c,cx+22*s,y-68*s,17*s,24*s,'#e6f3f1',6,'#a9c7c3',1.5);for(let i=0;i<3;i++)E(c,cx+30*s,y-50*s-i*5*s,6*s,2.5*s,'#f2cf6a');R(c,cx+24*s,y-72*s,13*s,5*s,'#c9a27f',2);
  plate(c,cx,y-31*s,label,fs,p.dark,84*s);}
/** Front fence with the gate (`door`) and its hanging open/closed sign. */
function frontFence(c,x0,x1,gx0,gx1,y,h,gh,open,text,fs,dark){fence(c,x0,gx0-8,y,h);fence(c,gx1+8,x1,y,h);
  const gy=y-gh;R(c,gx0-12,gy-4,14,gh+6,'#c99a6c',4,'#9c6d45',2);R(c,gx1-2,gy-4,14,gh+6,'#c99a6c',4,'#9c6d45',2);E(c,gx0-5,gy-5,9,5,'#e8c39a');E(c,gx1+5,gy-5,9,5,'#e8c39a');
  const pw=open?(gx1-gx0)*.28:gx1-gx0,px=gx0+2;
  R(c,px,y-h*.8,pw-2,5,'#ecd0a8',2,'#b88f68',1);R(c,px,y-h*.35,pw-2,5,'#ecd0a8',2,'#b88f68',1);for(let i=0;i<=(open?1:4);i++){const xx=px+4+i*(pw-12)/(open?1:4);R(c,xx-3,y-h,6,h,'#efd4ad',3,'#b88f68',1);}
  if(!open)L(c,px+4,y-3,px+pw-8,y-h+3,'#d9b58a',3);
  L(c,gx0-6,gy+2,gx1+6,gy+2,'#b88f68',5);c.font=`800 ${fs}px "Trebuchet MS", "Segoe UI", sans-serif`;const sw=Math.max(gx1-gx0-10,c.measureText(text).width+26),sh=fs+12,cx=(gx0+gx1)/2;
  L(c,cx-sw/2+12,gy+2,cx-sw/2+12,gy+8,'#9c6d45',1.5);L(c,cx+sw/2-12,gy+2,cx+sw/2-12,gy+8,'#9c6d45',1.5);
  R(c,cx-sw/2,gy+6,sw,sh,open?'#fff8e8':'#f3e6d6',9,'#c6a182',2);T(c,text,cx,gy+6+sh/2+1,fs,dark,800);if(open){bloom(c,cx-sw/2+2,gy+8,6,'#f6c847');}}
function bench(c,[x0,y0,x1,y1],mint,label,fs,dark,garden,prim){const w=x1-x0;E(c,(x0+x1)/2,y1+2,w/2+6,5,SHADOW);
  L(c,x0+10,y0,x0+10,y1,'#af8b6c',6);L(c,x1-10,y0,x1-10,y1,'#af8b6c',6);R(c,x0,y0-8,w,12,mint,6,'#9aa98a',1.5);R(c,x0+2,y0-44,w-4,30,mint,10,'#9aa98a',1.5);
  L(c,x0+14,y0-14,x0+14,y0-8,'#af8b6c',4);L(c,x1-14,y0-14,x1-14,y0-8,'#af8b6c',4);if(label)T(c,label,(x0+x1)/2,y0-29,fit(c,label,w-16,fs),dark);else heart(c,(x0+x1)/2,y0-27,.4,prim);
  if(garden)bloom(c,x1-6,y0-46,12,prim);}
function flowerBush(c,x,y,s){E(c,x,y+1,20*s,5*s,SHADOW);E(c,x,y-9*s,20*s,12*s,'#8cc47a');E(c,x-9*s,y-14*s,10*s,8*s,'#a8d38a');bloom(c,x-8*s,y-15*s,6*s,'#f4a9b8');bloom(c,x+8*s,y-12*s,6*s,'#f7d36b');bloom(c,x+1*s,y-21*s,5*s,'#c5b4e0');}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,wd=w.words(),items=w.c?.ops?.security?.items||[];
  E(c,600,774,540,14,'#a8876622');R(c,44,66,1112,706,'#d9b690',40);
  c.save();c.beginPath();c.roundRect(52,74,1096,690,34);c.clip();
  sky(c,52,74,1096,320);sun(c,138,152,32,t);[[300,156,1],[930,128,.9],[1080,205,.7],[560,215,.55]].forEach(([x,y,s],i)=>cloud(c,x+Math.sin(t*.07+i*2)*22,y,s));
  hill(c,[[40,292],[200,248],[400,282],[590,242],[800,276],[980,236],[1160,270]],800,'#c9e4b8');
  windmill(c,955,244,1,t);tree(c,215,260,.9);tree(c,560,254,.8);
  hill(c,[[40,352],[230,318],[470,346],[700,312],[930,342],[1160,318]],800,'#b1d59a');
  for(const [x,y] of [[140,340],[520,332],[830,326],[1060,332]])for(let i=0;i<4;i++)L(c,x+i*9,y+i*5,x+70+i*9,y-4+i*5,'#9fc987',4);
  farmhouse(c,712,318,1);
  hill(c,[[40,398],[300,382],[620,392],[900,380],[1160,390]],800,'#cfe7a6');
  tufts(c,60,395,1140,440,26,1);
  fence(c,52,1148,436,38);
  sunflower(c,72,448,92,1,t);sunflower(c,1122,446,96,1,t);sunflower(c,1098,452,70,.85,t);sunflower(c,985,440,84,.9,t);
  // Dirt path along the working line, a branch down to the gate, a patch at the shed.
  R(c,108,478,984,56,'#ecd6b0',28,'#e0c49a',2);R(c,992,500,86,270,'#ecd6b0',30,'#e0c49a',2);R(c,122,460,96,40,'#ecd6b0',18);R(c,995,504,80,60,'#ecd6b0',0);
  tufts(c,70,545,1130,700,34,2);
  // Back row, left to right.
  shed(c,88,466,160,130,wd.store,17,p.dark,items.includes('lock'));
  securityPost(c,268,446,100,1,items,t);
  seedRack(c,350,448,100,106,13,p.dark);
  coop(c,425,446,1,t,'TRỨNG',11,p.dark);chicken(c,616,452,.8,-1,t,2,true);
  diaryPost(c,657,448,1,12,p.dark,p.primary);
  hayBale(c,782,448,1);
  well(c,925,448,1,t);
  boardPost(c,p,1052,448,1);
  c.restore();
  woodSign(c,p,340,38,520,112,34,14,330);
  if(w.c?.upgrades?.includes('shelf')){crate(c,62,470,34,20,'tomato',.8);crate(c,62,448,34,20,'carrot',.8);}}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,wd=w.words(),items=w.c?.ops?.security?.items||[];
  E(c,350,884,320,10,'#a8876622');R(c,14,108,672,774,'#d9b690',34);
  c.save();c.beginPath();c.roundRect(22,116,656,758,28);c.clip();
  sky(c,22,116,656,300);sun(c,622,196,26,t);[[250,196,.8],[470,236,.62],[110,270,.5]].forEach(([x,y,s],i)=>cloud(c,x+Math.sin(t*.07+i*2)*16,y,s));
  hill(c,[[10,300],[150,262],[330,292],[500,256],[690,288]],900,'#c9e4b8');
  windmill(c,100,262,.9,t);tree(c,470,262,.8);
  hill(c,[[10,362],[180,334],[380,360],[560,328],[690,350]],900,'#b1d59a');
  for(const [x,y] of [[230,352],[520,344]])for(let i=0;i<4;i++)L(c,x+i*8,y+i*5,x+60+i*8,y-4+i*5,'#9fc987',4);
  farmhouse(c,400,340,.9);
  hill(c,[[10,420],[220,404],[470,414],[690,402]],900,'#cfe7a6');
  tufts(c,30,420,670,470,16,3);
  fence(c,22,678,482,36);
  sunflower(c,40,500,84,.9,t);sunflower(c,660,498,80,.85,t);
  R(c,40,540,620,62,'#ecd6b0',30,'#e0c49a',2);R(c,365,560,92,290,'#ecd6b0',34,'#e0c49a',2);R(c,55,516,90,40,'#ecd6b0',18);
  tufts(c,40,610,660,830,24,4);
  shed(c,30,516,140,112,wd.store,17,p.dark,items.includes('lock'));
  securityPost(c,185,505,96,.9,items,t);
  seedRack(c,240,502,86,98,16,p.dark);
  coop(c,296,500,.78,t,null,16,p.dark);
  diaryPost(c,462,504,.85,16,p.dark,p.primary);
  hayBale(c,540,504,.75);
  boardPost(c,p,625,504,1.1);
  c.restore();
  woodSign(c,p,50,24,600,120,34,16,300);}

function landProps(w,p){const c=w.ctx,t=w.reduced?0:w.time,wd=w.words(),pl=PLAN.land,tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,broken=(w.c?.ops?.equipment?.condition??100)<100,out=[];
  out.push([596,()=>bed(c,pl.blocks[1],['cabbage','lettuce'],1,t)],[596,()=>bed(c,pl.blocks[2],['carrot','lettuce'],1,t)]);
  out.push([594,()=>scarecrow(c,450,592,.85,p,t)]);
  out.push([588,()=>packTable(c,pl.blocks[4],1,11,p,broken)]);
  out.push([570,()=>stump(c,1032,570,1,12,wd.ledger,p)]);
  out.push([760,()=>frontFence(c,52,1148,975,1095,756,30,64,open,open?wd.open_sign:wd.closed_sign,13,p.dark)]);
  if(tier!=='cozy')out.push([684,()=>bench(c,pl.bench,p.mint,'ngồi nghỉ nhé ♡',12,p.dark,tier==='garden',p.primary)]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y,()=>flowerBush(c,x,y,1)]);
  return out;}
function portProps(w,p){const c=w.ctx,t=w.reduced?0:w.time,wd=w.words(),pl=PLAN.port,tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,broken=(w.c?.ops?.equipment?.condition??100)<100,out=[];
  out.push([660,()=>bed(c,pl.blocks[1],['cabbage','lettuce'],1,t)],[740,()=>bed(c,pl.blocks[2],['carrot','lettuce'],1,t)]);
  out.push([741,()=>scarecrow(c,262,738,.8,p,t)]);
  out.push([662,()=>packTable(c,pl.blocks[3],1,16,p,broken)]);
  out.push([762,()=>stump(c,602,762,1.05,16,wd.ledger,p)]);
  out.push([852,()=>frontFence(c,22,678,350,470,850,28,44,open,open?wd.open_sign:wd.closed_sign,16,p.dark)]);
  if(tier!=='cozy')out.push([826,()=>bench(c,pl.bench,p.mint,null,16,p.dark,tier==='garden',p.primary)]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y,()=>flowerBush(c,x,y,.9)]);
  return out;}

export default {
  id:'farm',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
