/** Mother & baby shop (mother_baby): "Tiệm Mây Nhỏ", a pastel nursery shop.
 * Back wall: bunting, cloud and star decals, a hanging mobile, the curtained
 * doorway to the back store (`warehouse`), cubbies of soft toys (`shelf`), a
 * sunny window where Mướp naps over a line of tiny onesies (`pet`), the
 * nappies-by-size and formula shelf with its checklist (`evidence`), the
 * street notice board with a giraffe height chart, the cloud plaque
 * (`property`) and the pastel door (`door`).
 * Floor: the gift-wrapping table with paper roll and ribbon spools
 * (`workbench`), the checkout counter (`counter`), a changing table, a crib
 * and a pram on display, a puzzle play mat with blocks, the ledger desk
 * (`finance`) and, on better leases, a nursing armchair. PLAN schema: see
 * scenes/shop.js.
 *
 * Floor pieces are drawn in local units with the origin at the middle of
 * their feet line, then placed with `at(x, y, scale)`, so portrait reuses
 * them at a smaller scale.
 */
import {R,E,L,T,P,fit,heart,bloom,plantAt,mascot,signBoard,streetBoard} from './kit.js';

/* ------------------------------------------------------------ Floor plan */
export const PLAN={
 land:{badge:{board:[0,-42]},floor:[130,452,1070,682],lane:515,line:515,home:[600,515],kx:82,ky:45,sway:28,
   blocks:[[315,572,495,602],[660,572,850,602],[140,566,232,598],[905,566,985,598],[150,646,222,668],[990,640,1066,668]],
   bench:[236,652,300,676],garden:[[210,468],[868,470]],
   customers:[[405,640],[575,652],[755,640],[860,660]],event:[505,676],officer:[1030,612],
   staff:{x:300,step:130,y:470},cat:[490,352],counterSpan:[315,850],
   decor:{corner:[1050,545],front:[800,676],center:[500,628]},sill:{plant:[440,352],lamp:[462,352],seat:[538,352],rug:[590,662]},
   wall:{poster:[612,318]},
   spots:{shelf:[[311,320],90,[[311,515]]],evidence:[[748,330],95,[[748,515]]],workbench:[[405,548],62,[[405,515]]],counter:[[755,548],60,[[755,515]]],
     warehouse:[[162,392],48,[[165,500],[230,515]]],board:[[898,290],42,[[898,515]]],finance:[[1028,612],42,[[950,655],[960,622]]],
     property:[[1016,236],32,[[995,515]]],security:[[150,206],30,[[250,515]]],door:[[1016,380],55,[[1016,505]]],pet:[[490,332],38,[[490,515]]]}},
 port:{badge:{board:[0,-40]},floor:[62,512,638,822],lane:575,line:575,home:[330,575],kx:51,ky:57,sway:22,
   blocks:[[98,626,272,656],[378,626,560,656],[62,706,142,736],[548,700,638,736],[152,798,228,818],[562,792,638,818]],
   bench:[64,798,140,818],garden:[[84,770],[618,642]],
   customers:[[200,712],[330,702],[462,712],[340,796]],event:[262,772],officer:[450,792],
   staff:{x:150,step:95,y:532},cat:[350,360],counterSpan:[98,560],
   decor:{corner:[612,752],front:[150,768],center:[400,762]},sill:{plant:[298,360],lamp:[320,360],seat:[398,360],rug:[365,796]},
   wall:{poster:[350,442]},
   spots:{shelf:[[195,380],70,[[195,575]]],evidence:[[503,384],62,[[503,575]]],workbench:[[185,600],58,[[185,575]]],counter:[[469,598],56,[[469,575]]],
     warehouse:[[79,440],45,[[92,562],[130,575]]],board:[[620,238],42,[[612,575]]],finance:[[600,774],40,[[530,804],[540,775]]],
     property:[[620,297],30,[[600,575]]],security:[[70,206],30,[[140,575]]],door:[[618,440],50,[[618,568]]],pet:[[350,344],36,[[350,575]]]}},
};

/* ------------------------------------------------------------ Palette */
const PEACH='#fbd9c6',PEACH_D='#e9b49c',BLUE='#cfe3f3',BLUE_D='#93b7d6',BLUE_L='#e4f0f9',MINT='#c7eadb',MINT_D='#8fc4ae',LILAC='#e1d4f2',BUTTER='#fbe7a6',
  PINK='#f7c8d4',CREAM='#fffaf2',WOOD='#f2d9bf',WOOD_D='#c9a07f',EDGE='#b98f73',WHITE='#fffdf8',LINE='#d9c3ae',SHADOW='#8b73531f',INK='#6f5646';
const TOYS=[PINK,BLUE,MINT,BUTTER,LILAC,PEACH];

/** Draw `fn` with the origin at (x,y) scaled by s. */
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
/** Five-point star. */
function star(c,x,y,r,col){const pts=[];for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.46:r;pts.push([x+Math.cos(a)*rr,y+Math.sin(a)*rr]);}P(c,pts,col);}
/** Puffy cloud centred at (x,y). */
function cloud(c,x,y,k,col){E(c,x-15*k,y+3*k,13*k,9*k,col);E(c,x+15*k,y+3*k,14*k,9*k,col);E(c,x-4*k,y-7*k,14*k,12*k,col);E(c,x+9*k,y-4*k,11*k,10*k,col);E(c,x,y+4*k,22*k,9*k,col);}
/** Crescent moon. */
function moon(c,x,y,r,col,bg){E(c,x,y,r,r,col);E(c,x+r*.45,y-r*.25,r*.8,r*.8,bg);}

/* ------------------------------------------------------------ Soft toys (origin: bottom centre) */
function bunny(c,x,y,k,col){E(c,x-4*k,y-37*k,3.2*k,10*k,col);E(c,x+4*k,y-37*k,3.2*k,10*k,col);E(c,x-4*k,y-36*k,1.4*k,7*k,'#f4a9bc');E(c,x+4*k,y-36*k,1.4*k,7*k,'#f4a9bc');
  E(c,x,y-10*k,11*k,10*k,col);E(c,x,y-24*k,9*k,8*k,col);E(c,x,y-8*k,6*k,5*k,'#ffffff99');E(c,x-3*k,y-25*k,1.3*k,1.6*k,INK);E(c,x+3*k,y-25*k,1.3*k,1.6*k,INK);E(c,x,y-22*k,1.5*k,1*k,'#e48ea4');
  E(c,x-6*k,y-21*k,2.2*k,1.3*k,'#f4a9bc99');E(c,x+6*k,y-21*k,2.2*k,1.3*k,'#f4a9bc99');}
function bear(c,x,y,k,col){E(c,x-7*k,y-31*k,4*k,4*k,col);E(c,x+7*k,y-31*k,4*k,4*k,col);E(c,x,y-9*k,11*k,9*k,col);E(c,x,y-24*k,9.5*k,8.5*k,col);E(c,x,y-21*k,4.5*k,3.2*k,'#fff3e3');
  E(c,x-3.5*k,y-26*k,1.3*k,1.6*k,INK);E(c,x+3.5*k,y-26*k,1.3*k,1.6*k,INK);E(c,x,y-22*k,1.4*k,1*k,INK);E(c,x-8*k,y-3*k,3.5*k,2.6*k,col);E(c,x+8*k,y-3*k,3.5*k,2.6*k,col);heart(c,x,y-9*k,.18*k,'#f19bb0');}
function duck(c,x,y,k){E(c,x,y-8*k,12*k,8*k,'#fbe39a');E(c,x+5*k,y-19*k,6.5*k,6.5*k,'#fbe39a');P(c,[[x+10*k,y-20*k],[x+16*k,y-18*k],[x+10*k,y-16*k]],'#f3b27a');E(c,x+6*k,y-21*k,1.2*k,1.4*k,INK);E(c,x-5*k,y-9*k,5*k,3*k,'#f6d27b');}
function elephant(c,x,y,k){E(c,x,y-12*k,12*k,11*k,'#c9d6ea');E(c,x-10*k,y-16*k,6*k,8*k,'#b8c8e2');E(c,x+10*k,y-16*k,6*k,8*k,'#b8c8e2');L(c,x,y-12*k,x+2*k,y-3*k,'#c9d6ea',4*k);E(c,x-4*k,y-16*k,1.2*k,1.5*k,INK);E(c,x+4*k,y-16*k,1.2*k,1.5*k,INK);E(c,x+6*k,y-10*k,2*k,1.2*k,'#f4a9bc99');}
function blocks(c,x,y,k){const s=12*k;R(c,x-s-1,y-s,s,s,PINK,2,'#c9a48c',1);R(c,x+1,y-s,s,s,MINT,2,'#9fbfae',1);R(c,x-s/2,y-2*s-1,s,s,BUTTER,2,'#cdb27a',1);
  T(c,'A',x-s/2-1,y-s/2,8*k,'#b0697f',800);T(c,'B',x+s/2+1,y-s/2,8*k,'#5f8f7c',800);T(c,'C',x,y-1.5*s-1,8*k,'#a38444',800);}
function ball(c,x,y,k){E(c,x,y-9*k,9*k,9*k,BLUE);c.save();c.beginPath();c.ellipse(x,y-9*k,9*k,9*k,0,0,Math.PI*2);c.clip();R(c,x-9*k,y-12*k,18*k,6*k,'#fff6e8',0);c.restore();E(c,x-3*k,y-13*k,2.5*k,2*k,'#ffffffaa');}
function rattle(c,x,y,k){L(c,x,y-2*k,x,y-14*k,'#f3c16f',3*k);E(c,x,y-19*k,7*k,7*k,LILAC);E(c,x-2*k,y-21*k,2*k,2*k,'#ffffffaa');E(c,x,y-1*k,3*k,2*k,'#f3c16f');}

/* ------------------------------------------------------------ Wall pieces */
/** Soft wallpaper: pastel dots, clouds and stars. */
function wallpaper(c,p,x,y,w,h,k){c.save();c.beginPath();c.roundRect(x,y,w,h,20);c.clip();
  for(let r=0,yy=y+26;yy<y+h;r++,yy+=34)for(let xx=x+(r%2?34:14);xx<x+w;xx+=40)E(c,xx,yy,2.4,2.4,r%3===0?'#f2bfcd70':r%3===1?'#b9d4ea80':'#bfe2d270');
  c.restore();}
/** String of pastel pennants. */
function bunting(c,x0,x1,y,sag,size){c.strokeStyle='#d7b99a';c.lineWidth=2;c.beginPath();c.moveTo(x0,y);c.quadraticCurveTo((x0+x1)/2,y+sag*2,x1,y);c.stroke();
  const n=Math.max(5,Math.round((x1-x0)/(size*2.3)));
  for(let i=1;i<n;i++){const t=i/n,xx=x0+(x1-x0)*t,yy=y+sag*4*t*(1-t);P(c,[[xx-size*.62,yy],[xx+size*.62,yy],[xx,yy+size]],TOYS[i%6]);E(c,xx,yy+size*.36,size*.12,size*.12,'#ffffffb0');}}
/** Hanging mobile: star, moon, cloud and heart turning slowly. */
function mobile(c,p,x,top,len,k,time,reduced){const sw=reduced?0:Math.sin(time*.9)*.12;
  L(c,x,top,x,top+len,'#c9ab8c',1.5);c.save();c.translate(x,top+len);c.rotate(sw);
  E(c,0,0,4*k,4*k,'#e2c29c');L(c,-36*k,6*k,36*k,6*k,'#d9b58d',3*k);L(c,0,0,-36*k,6*k,'#c9ab8c',1);L(c,0,0,36*k,6*k,'#c9ab8c',1);
  const hang=[[-34,28,'star'],[-12,44,'moon'],[12,36,'cloud'],[34,24,'heart']];
  hang.forEach(([dx,dy,kind],i)=>{const bob=reduced?0:Math.sin(time*1.6+i)*2*k,hx=dx*k,hy=dy*k+bob;L(c,hx,6*k,hx,hy-8*k,'#c9ab8c',1);
    if(kind==='star')star(c,hx,hy,9*k,BUTTER);else if(kind==='moon')moon(c,hx,hy,8*k,LILAC,p.wall);else if(kind==='cloud')cloud(c,hx,hy,.42*k,WHITE);else heart(c,hx,hy+3*k,.34*k,'#f3a7bb');});
  c.restore();}
/** Arched doorway to the back store with a tied curtain: the `warehouse`. */
function storeDoor(c,p,x,y,w,h,label,locked,size){const r=w/2;
  c.beginPath();c.moveTo(x-6,y+h);c.lineTo(x-6,y+r);c.arc(x+r,y+r,r+6,Math.PI,0);c.lineTo(x+w+6,y+h);c.closePath();c.fillStyle='#e7c3a4';c.fill();
  c.beginPath();c.moveTo(x,y+h);c.lineTo(x,y+r);c.arc(x+r,y+r,r,Math.PI,0);c.lineTo(x+w,y+h);c.closePath();c.fillStyle='#e9d8c8';c.fill();
  // Boxes waiting inside.
  R(c,x+w*.14,y+h-38,w*.4,36,'#e5c49c',3,'#c29f7b',1);L(c,x+w*.14,y+h-26,x+w*.54,y+h-26,'#c29f7b',1);R(c,x+w*.5,y+h-58,w*.34,56,BLUE,3,BLUE_D,1);heart(c,x+w*.67,y+h-30,.22,'#fff7ee');
  R(c,x+w*.2,y+h-60,w*.28,22,PINK,3,'#d69cae',1);
  // Curtain panels drawn aside with ribbons.
  for(const side of [0,1]){const cx=side?x+w:x,d=side?-1:1;c.beginPath();c.moveTo(cx,y+r*.4);c.quadraticCurveTo(cx+d*w*.46,y+h*.3,cx+d*w*.14,y+h*.55);c.quadraticCurveTo(cx+d*w*.3,y+h*.8,cx+d*w*.22,y+h);c.lineTo(cx,y+h);c.closePath();c.fillStyle=MINT;c.fill();
    for(let i=0;i<5;i++)E(c,cx+d*(6+i%2*8),y+r*.8+i*h*.16,2,2,'#ffffffb0');E(c,cx+d*w*.15,y+h*.55,4,4,'#f3a7bb');}
  c.beginPath();c.arc(x+r,y+r,r,Math.PI,0);c.lineWidth=5;c.strokeStyle='#f7e7d4';c.stroke();
  const pw=Math.max(w-6,size*3.2);R(c,x+r-pw/2,y-size*.9,pw,size*1.8,CREAM,7,'#d2ae8e',1.5);T(c,label,x+r,y+1,fit(c,label,pw-10,size,800),p.dark,800);
  if(locked){const lx=x+w-10,ly=y+h*.5;R(c,lx-8,ly,16,17,'#e7d19b',4,'#a59470',1);c.beginPath();c.arc(lx,ly,5,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=3;c.stroke();}}
/** Cubbies of soft toys (the `shelf`). */
function toyCubbies(c,p,x,y,w,h,label,size,rows){const head=size*2;
  R(c,x-4,y+head-2,w+8,h-head+2,WOOD_D,10);R(c,x,y+head+2,w,h-head-2,WOOD,8);
  R(c,x+w*.08,y,w*.84,head,p.light,12,'#dfb6c0',1.5);T(c,label,x+w/2,y+head/2+1,fit(c,label,w*.84-14,size),p.dark);
  const cols=3,iw=(w-16)/cols,ih=(h-head-12)/rows;
  for(let r=0;r<rows;r++)for(let i=0;i<cols;i++){const bx=x+8+i*iw,by=y+head+6+r*ih,j=r*cols+i;
    R(c,bx+2,by+2,iw-4,ih-4,[BLUE_L,'#fde9ee','#e8f6ef','#fdf3d9','#f0e9fa','#fdeee4'][j%6],6);R(c,bx+2,by+ih-9,iw-4,5,'#e7c7a8',2);
    const cx=bx+iw/2,base=by+ih-8,k=Math.min(iw/44,ih/48);
    [()=>bunny(c,cx,base,k,'#fff4ec'),()=>bear(c,cx,base,k,'#e8c197'),()=>{duck(c,cx-6*k,base,k*.9);ball(c,cx+12*k,base,k*.7);},()=>elephant(c,cx,base,k),()=>{blocks(c,cx-4*k,base,k);rattle(c,cx+14*k,base,k*.8);},
     ()=>bunny(c,cx,base,k,PINK),()=>bear(c,cx,base,k,'#f3dcc0'),()=>{bunny(c,cx-8*k,base,k*.72,'#e7f3ff');bear(c,cx+9*k,base,k*.72,'#d9b08a');},()=>duck(c,cx,base,k*1.1)][j%9]();}}
/** Nappies by size and formula tins (the `evidence`: check what fits). */
function nappyShelf(c,p,x,y,w,h,size,rows){const head=size*2;
  R(c,x-4,y+head-2,w+8,h-head+2,WOOD_D,10);R(c,x,y+head+2,w,h-head-2,'#fff5ea',8);
  const s='BỈM · SỮA';R(c,x+w*.1,y,w*.8,head,BLUE,12,BLUE_D,1.5);T(c,s,x+w/2,y+head/2+1,fit(c,s,w*.8-14,size,800),'#4f6f8c',800);
  const top=y+head+4,rh=(h-head-10)/rows;
  for(let r=0;r<rows;r++){const base=top+rh*(r+1)-4;R(c,x,base,w,7,'#e0b995',2);R(c,x+3,base-1,w-6,3,'#f3d6b8',1);
    if(r===0){// formula tins
      const n=Math.max(3,Math.floor((w-10)/30)),tw=(w-12)/n;for(let i=0;i<n;i++){const tx=x+6+i*tw+tw/2,th=Math.min(rh-10,40);
        R(c,tx-tw*.36,base-th,tw*.72,th,[WHITE,'#fef3e3',WHITE][i%3],5,'#cdb9a4',1);R(c,tx-tw*.38,base-th-5,tw*.76,8,[BLUE_D,'#e59bb0',MINT_D][i%3],3);
        R(c,tx-tw*.28,base-th*.66,tw*.56,th*.4,[BLUE,PINK,MINT][i%3],3);T(c,String(i%3+1),tx,base-th*.46,Math.min(12,th*.3),'#6f7d8c',800);}}
    else{// nappy packs by size
      const sizes=rows>2?(r===1?['S','M','L']:['XL','M','S']):['S','M','L','XL'],n=sizes.length,pw=(w-12)/n;
      sizes.forEach((sz,i)=>{const px=x+6+i*pw,ph=Math.min(rh-8,44),col=[PINK,BLUE,MINT,BUTTER][['S','M','L','XL'].indexOf(sz)];
        R(c,px+2,base-ph,pw-4,ph,col,9,'#c7a8a0',1);R(c,px+5,base-ph+3,pw-10,5,'#ffffff90',3);E(c,px+pw/2,base-ph*.58,Math.min(9,pw*.22),Math.min(9,pw*.22),WHITE);
        E(c,px+pw/2-2.5,base-ph*.6,1,1.2,INK);E(c,px+pw/2+2.5,base-ph*.6,1,1.2,INK);T(c,sz,px+pw/2,base-ph*.2,Math.min(13,ph*.3),'#7a5a64',800);});}}
  // Checklist clipboard on the side (compare the request).
  const cx=x+w-2,cy=y+head+14;R(c,cx-8,cy,26,34,'#d7ae86',4);R(c,cx-5,cy+4,20,27,WHITE,2);R(c,cx,cy-3,10,6,'#b89478',2);
  for(let i=0;i<3;i++){L(c,cx-2,cy+10+i*7,cx+1,cy+13+i*7,'#79b28f',1.6);L(c,cx+1,cy+13+i*7,cx+5,cy+7+i*7,'#79b28f',1.6);L(c,cx+7,cy+11+i*7,cx+13,cy+11+i*7,'#cbb6a3',1.5);}}
/** Sunny window with ruffled curtains; returns the sill y. */
function nurseryWindow(c,p,x,y,w,h,time,reduced){
  R(c,x-8,y-8,w+16,h+16,'#ecc7ad',[w/2+8,w/2+8,14,14]);c.save();c.beginPath();c.roundRect(x,y,w,h,[w/2,w/2,10,10]);c.clip();
  c.fillStyle='#d4ecf6';c.fillRect(x,y,w,h);E(c,x+w*.72,y+h*.3,15,15,'#fff0be');const drift=reduced?0:(time*5)%(w+60);
  for(const [dx,dy] of [[.25,.35],[.7,.6]]){const cx=x+((w*dx+drift)%(w+60))-30;cloud(c,cx,y+h*dy,.5,'#ffffffdd');}
  E(c,x+w*.18,y+h*.95,w*.3,h*.26,'#b3d9b8');E(c,x+w*.86,y+h*.98,w*.26,h*.3,'#a9d2bd');c.restore();
  L(c,x+w/2,y+4,x+w/2,y+h-2,'#fffaf0',5);L(c,x+4,y+h*.55,x+w-4,y+h*.55,'#fffaf0',5);
  // Ruffled valance and tied curtains.
  for(let i=0;i<7;i++)E(c,x-4+i*(w+8)/6,y+4,(w+8)/12+2,9,i%2?PEACH:'#fde6da');
  for(const side of [0,1]){const cx=side?x+w:x,d=side?-1:1;P(c,[[cx,y+8],[cx+d*w*.2,y+8],[cx+d*w*.08,y+h*.5],[cx+d*w*.16,y+h],[cx,y+h]],PEACH);E(c,cx+d*w*.1,y+h*.5,4,4,'#f3a7bb');}
  R(c,x-14,y+h+2,w+28,11,'#e4b99c',5);R(c,x-10,y+h+3,w+20,4,'#f3d4bd',2);return y+h+2;}
/** Clothes line of tiny onesies and socks. */
function onesieLine(c,p,x0,x1,y,k){c.strokeStyle='#cdb191';c.lineWidth=1.5;c.beginPath();c.moveTo(x0,y);c.quadraticCurveTo((x0+x1)/2,y+14*k,x1,y);c.stroke();
  const n=5;for(let i=0;i<n;i++){const t=(i+.5)/n,xx=x0+(x1-x0)*t,yy=y+14*k*4*t*(1-t)*.5+2,col=[PINK,BLUE,MINT,BUTTER,LILAC][i];
    if(i%2===1){R(c,xx-3*k,yy,6*k,11*k,col,2);R(c,xx-3*k,yy+8*k,10*k,5*k,col,2);R(c,xx+5*k,yy,6*k,11*k,col,2);R(c,xx+5*k,yy+8*k,10*k,5*k,col,2);}
    else{P(c,[[xx-12*k,yy+1],[xx+12*k,yy+1],[xx+15*k,yy+7*k],[xx+8*k,yy+10*k],[xx+8*k,yy+22*k],[xx+3*k,yy+27*k],[xx-3*k,yy+27*k],[xx-8*k,yy+22*k],[xx-8*k,yy+10*k],[xx-15*k,yy+7*k]],col);
      c.beginPath();c.arc(xx,yy+1,4*k,0,Math.PI);c.fillStyle='#fffaf2';c.fill();heart(c,xx,yy+15*k,.16*k,'#ffffffcc');}
    R(c,xx-1.5,yy-3,3,6,'#d9b58d',1);}}
/** Giraffe height chart on the wall. */
function giraffe(c,x,y,h,k){R(c,x,y,20*k,h,'#fbe3a6',8,'#e0bd73',1.5);for(let i=0;i<5;i++)E(c,x+(i%2?13:7)*k,y+h*.18+i*h*.16,3.5*k,3*k,'#e8b86e');
  for(let i=1;i<6;i++)L(c,x+20*k,y+i*h/6,x+26*k,y+i*h/6,'#c9a58a',1.5);E(c,x+10*k,y-4*k,11*k,8*k,'#fbe3a6');E(c,x+17*k,y-2*k,5*k,4*k,'#f7d7a1');
  L(c,x+5*k,y-10*k,x+3*k,y-17*k,'#e0bd73',2.5);L(c,x+12*k,y-10*k,x+13*k,y-17*k,'#e0bd73',2.5);E(c,x+8*k,y-6*k,1.3*k,1.6*k,INK);}
/** Cloud plaque with the bear mascot (the `property`). */
function cloudPlaque(c,p,x,y,k){cloud(c,x,y+2*k,1.02*k,'#e6c3a7');cloud(c,x,y,k,WHITE);mascot(c,x,y+8*k,.28*k);heart(c,x+22*k,y-8*k,.18*k,p.primary);}
/** Pastel door with a round window and the open / closed sign. */
function nurseryDoor(c,p,x,y,w,h,size,open,words){R(c,x-7,y-7,w+14,h+7,'#e7c3a4',[w/2+6,w/2+6,6,6]);
  if(open){R(c,x,y,w,h,'#fdf1e4',[w/2,w/2,4,4]);R(c,x+3,y+h*.7,w-6,h*.3,'#ecdcc6',0);E(c,x+w/2,y+h*.3,w*.22,w*.22,'#d4ecf6');L(c,x+3,y+h*.7,x+w-3,y+h*.7,'#d7bfa2',2);
    const leaf=Math.min(12,w*.14);P(c,[[x+w-2,y+w*.3],[x+w+leaf,y+w*.24],[x+w+leaf,y+h+4],[x+w-2,y+h]],BLUE);}
  else{R(c,x,y,w,h,BLUE,[w/2,w/2,4,4],BLUE_D,2);E(c,x+w/2,y+w*.52,w*.24,w*.24,'#e9f5fb');L(c,x+w/2,y+w*.3,x+w/2,y+w*.76,'#fffaf0',2);R(c,x+w*.16,y+h*.58,w*.68,h*.32,'#dcebf6',6);heart(c,x+w/2,y+h*.76,.3,'#f3a7bb');E(c,x+w-11,y+h*.54,3.5,3.5,'#e0c07a');}
  const s=open?words.open_sign:words.closed_sign,sw=w+16,sy=y+h*.4;L(c,x+w/2,sy-12,x+w/2-16,sy,'#b39070',1.5);L(c,x+w/2,sy-12,x+w/2+16,sy,'#b39070',1.5);
  R(c,x+w/2-sw/2,sy,sw,size*1.9,'#fff8e8',9,open?'#8fc4ae':'#e4a5b4',2);T(c,s,x+w/2,sy+size*.97,fit(c,s,sw-10,size,800),open?p.dark:'#a35f63',800);}
/** Security equivalents: camera, door bell, night light. */
function security(c,p,items,cam,bell,lamp){
  if(items.includes('camera')){const [x,y]=cam;L(c,x-8,y+12,x+2,y+2,'#b79b85',4);R(c,x-4,y-10,36,20,'#f5f2eb',7,'#a7aaa2',2);E(c,x+26,y,7,8,'#7a8992');E(c,x+27,y,3,4,'#b4d9df');E(c,x+2,y-5,2,2,'#90bd8b');}
  else{const [x,y]=cam;R(c,x-6,y-11,38,22,'#fff6e9',8,'#d5b59a',1);T(c,'♧',x+13,y,14,p.dark);}
  if(items.includes('bell')){const [x,y]=bell;L(c,x,y-14,x,y-4,'#ac8f73',2);P(c,[[x-10,y+11],[x+10,y+11],[x+7,y-3],[x-7,y-3]],'#f0ce85');E(c,x,y-3,7,4,'#f0ce85');E(c,x,y+13,4,3,'#d4ad64');}
  if(items.includes('light')){const [x,y]=lamp,g=c.createRadialGradient(x,y+20,0,x,y+20,90);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(x-90,y-70,180,180);moon(c,x,y,11,'#fff0b8','#ffe7b0');R(c,x-12,y-12,24,22,'#fff0b855',8,'#b69b79',1.5);}}
/** Flat puzzle play mat with a few toys (walkable). */
function playMat(c,p,x,y,rx,ry){c.save();c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.clip();
  const cols=[PINK,BLUE,MINT,BUTTER,LILAC,PEACH],tw=rx/3,th=ry/1.4;for(let i=-4;i<4;i++)for(let j=-2;j<2;j++){c.fillStyle=cols[((i+j)%6+6)%6];c.fillRect(x+i*tw,y+j*th,tw,th);}
  for(let i=-3;i<4;i++)L(c,x+i*tw,y-ry,x+i*tw,y+ry,'#ffffff80',1.5);for(let j=-1;j<2;j++)L(c,x-rx,y+j*th,x+rx,y+j*th,'#ffffff80',1.5);c.restore();
  c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.strokeStyle='#ffffffb0';c.lineWidth=3;c.stroke();
  star(c,x-rx*.55,y-ry*.2,7,'#fff6d8');star(c,x+rx*.5,y+ry*.25,6,'#fff6d8');}

/* ------------------------------------------------------------ Floor pieces (origin: middle of the feet line) */
/** Gift-wrapping table (the `workbench`): paper roll, ribbons, a wrapped gift. */
function giftTable(c,p,W,worn,time,reduced){const h=50;E(c,0,2,W*.55,8,SHADOW);
  for(const d of [-1,1])L(c,d*(W/2-12),-h+8,d*(W/2-12),0,EDGE,5);
  R(c,-W/2-6,-h-4,W+12,13,'#f5dec6',6,EDGE,2);R(c,-W/2,-h-2,W,4,'#fdf0de',2);
  // Scalloped cloth skirt.
  R(c,-W/2+2,-h+8,W-4,20,PINK,3);for(let i=0;i<9;i++)E(c,-W/2+2+(i+.5)*(W-4)/9,-h+28,(W-4)/18,6,PINK);for(let i=0;i<9;i++)E(c,-W/2+2+(i+.5)*(W-4)/9,-h+17,2,2,'#ffffffb0');
  // Paper roll dispenser on the left, a sheet pulled forward.
  const px=-W/2+10;L(c,px+4,-h-4,px+4,-h-30,EDGE,4);L(c,px+60,-h-4,px+60,-h-30,EDGE,4);R(c,px,-h-40,64,18,BLUE,9,BLUE_D,1.5);for(let i=0;i<5;i++)star(c,px+8+i*12,-h-31,3.5,'#ffffffcc');
  P(c,[[px+4,-h-26],[px+62,-h-26],[px+68,-h-4],[px+8,-h-4]],'#e7f2fb');for(let i=0;i<3;i++)star(c,px+20+i*16,-h-13,3,'#b9d4ea');
  // Wrapped gift with a bow.
  const gx=W*.06;R(c,gx-22,-h-34,44,30,'#fde2e8',4,'#d69cae',1.5);L(c,gx,-h-34,gx,-h-4,p.primary,5);L(c,gx-22,-h-20,gx+22,-h-20,p.primary,4);
  const wig=reduced?0:Math.sin(time*2)*1.2;E(c,gx-8,-h-38+wig*.3,9,5,p.primary);E(c,gx+8,-h-38-wig*.3,9,5,p.primary);E(c,gx,-h-37,3.5,3.5,'#b85f7c');L(c,gx-2,-h-35,gx-8,-h-26,p.primary,2);L(c,gx+2,-h-35,gx+9,-h-26,p.primary,2);
  // Ribbon spools with curly ends, scissors and a tag.
  const rx=W/2-44;[[0,PINK,'#d98ca3'],[16,BLUE,BLUE_D],[32,MINT,MINT_D]].forEach(([dx,col,dk])=>{E(c,rx+dx,-h-10,7,7,col);E(c,rx+dx,-h-10,2.5,2.5,dk);c.beginPath();c.moveTo(rx+dx,-h-3);c.bezierCurveTo(rx+dx+6,-h+4,rx+dx-4,-h+8,rx+dx+3,-h+14);c.strokeStyle=dk;c.lineWidth=2;c.stroke();});
  L(c,rx+4,-h-22,rx+22,-h-28,'#9aa6ab',2);L(c,rx+4,-h-28,rx+22,-h-22,'#9aa6ab',2);E(c,rx+2,-h-21,3,3,'#f3a7bb');E(c,rx+2,-h-29,3,3,'#f3a7bb');
  if(worn){R(c,-W/2+10,-h+10,74,16,'#f7d995',4);T(c,'CẦN KIỂM',-W/2+47,-h+18,10,'#94643d',800);}}
/** Checkout counter (the `counter`): cloud front, till, card reader, pacifier jar. */
function checkout(c,p,W){const h=62;E(c,0,2,W*.55,8,SHADOW);
  R(c,-W/2,-h+8,W,h-8,BLUE,10,BLUE_D,2);R(c,-W/2+8,-h+18,W-16,h-28,BLUE_L,8);cloud(c,-W*.2,-h*.42,.8,WHITE);cloud(c,W*.22,-h*.5,.6,WHITE);star(c,W*.02,-h*.62,5,BUTTER);star(c,W*.38,-h*.26,4,BUTTER);
  R(c,-W/2-8,-h-4,W+16,14,'#f5dec6',7,EDGE,2);R(c,-W/2-2,-h-2,W+4,4,'#fdf0de',2);
  // Till.
  const tx=-W/2+34;R(c,tx-24,-h-26,48,24,'#fdeef2',6,'#d69cae',1.5);R(c,tx-18,-h-22,24,10,'#e3f3ea',2);for(let i=0;i<3;i++)for(let j=0;j<2;j++)R(c,tx+10+i*4.5,-h-20+j*7,3,4,'#d69cae',1);
  R(c,tx-12,-h-46,28,20,'#fdeef2',5,'#d69cae',1.5);R(c,tx-8,-h-42,20,11,'#fff9e6',2);T(c,'♡',tx+2,-h-37,8,p.primary);R(c,tx+10,-h-34,4,8,'#fff',1);
  // Card reader, pacifier jar, paper bag.
  R(c,-W*.08,-h-18,16,16,'#8fa6b5',4);R(c,-W*.08+3,-h-15,10,5,'#d8f0ea',1);
  const jx=W*.14;R(c,jx-12,-h-30,24,28,'#f4fbff99',6,'#a9c3d6',1.5);R(c,jx-13,-h-34,26,6,'#e59bb0',3);for(let i=0;i<4;i++){E(c,jx-6+(i%2)*11,-h-18+Math.floor(i/2)*9,4,3,[PINK,MINT,BUTTER,BLUE][i]);E(c,jx-6+(i%2)*11,-h-21+Math.floor(i/2)*9,1.8,1.8,'#fff');}
  const bx=W/2-30;P(c,[[bx-15,-h-2],[bx+15,-h-2],[bx+13,-h-32],[bx-13,-h-32]],'#f3dcc0');c.beginPath();c.arc(bx,-h-31,7,Math.PI,0);c.strokeStyle='#caa27d';c.lineWidth=2;c.stroke();heart(c,bx,-h-15,.3,p.primary);}
/** Changing table: padded mat, folded nappies, lotion, drawers. */
function changingTable(c,p,W){const h=58;E(c,0,2,W*.55,7,SHADOW);
  R(c,-W/2,-h+6,W,h-6,WHITE,8,LINE,2);for(let i=0;i<2;i++){R(c,-W/2+6,-h+12+i*((h-18)/2),W-12,(h-22)/2,i?MINT:'#fdeef2',5,'#d3c2b3',1);E(c,0,-h+12+i*((h-18)/2)+(h-22)/4,3,3,'#d7b28a');}
  L(c,-W/2+6,-2,-W/2+6,2,EDGE,4);L(c,W/2-6,-2,W/2-6,2,EDGE,4);
  R(c,-W/2-4,-h-4,W+8,12,'#f5dec6',6,EDGE,2);R(c,-W/2+2,-h-12,W-4,11,MINT,6,MINT_D,1.5);E(c,-W/2+6,-h-7,5,6,MINT);E(c,W/2-6,-h-7,5,6,MINT);
  // Folded nappies, a lotion bottle and a little duck.
  for(let i=0;i<3;i++)R(c,-W/2+8,-h-20-i*7,26,7,[WHITE,'#fdf3f6','#eef6fd'][i],3,'#d9c6b8',1);
  R(c,W*.1,-h-30,12,20,'#fde2e8',4,'#d69cae',1);R(c,W*.1+3,-h-35,6,6,'#e59bb0',2);duck(c,W/2-12,-h-11,.55);}
/** White crib on display with a teddy, blanket and a clip-on mobile. */
function crib(c,p,W,time,reduced){const h=74,top=-h;E(c,0,2,W*.56,8,SHADOW);
  // Back posts and a headboard with a cloud cut-out.
  R(c,-W/2,top-8,10,h+8,WHITE,4,LINE,1.5);R(c,W/2-10,top-8,10,h+8,WHITE,4,LINE,1.5);E(c,-W/2+5,top-10,6,5,'#f3e6da');E(c,W/2-5,top-10,6,5,'#f3e6da');
  R(c,-W/2+8,top,W-16,26,WHITE,6,LINE,1);cloud(c,0,top+12,.36,BLUE_L);
  // Mattress, pillow, teddy and a pink blanket peeking over the front rail.
  R(c,-W/2+9,-50,W-18,12,'#eef5fb',4,'#dfe7ee',1);R(c,-W/2+12,-56,W*.26,11,'#fffdf8',6,'#e1d6ca',1);
  R(c,-W*.1,-54,W*.46,15,PINK,6);for(let i=0;i<3;i++)heart(c,-W*.04+i*W*.13,-46,.11,'#ffffffcc');bear(c,-W/2+14+W*.13,-42,.56,'#e8c197');
  // Front rail, slats and base rail.
  R(c,-W/2+6,-42,W-12,6,WHITE,3,LINE,1);const n=Math.max(5,Math.round((W-20)/10));for(let i=1;i<n;i++){const sx=-W/2+8+i*(W-16)/n;R(c,sx-1.5,-37,3,24,WHITE,1.5,'#e2d6c9',.8);}
  R(c,-W/2+6,-14,W-12,8,WHITE,3,LINE,1);L(c,-W/2+5,-2,-W/2+5,0,EDGE,4);L(c,W/2-5,-2,W/2-5,0,EDGE,4);
  // Clip-on mobile: a curved arm from the right post, a hub and three toys.
  const ax=W/2-5,hx=W*.12,hy=top-44;c.strokeStyle='#e6d2bd';c.lineWidth=4;c.lineCap='round';c.beginPath();c.moveTo(ax,top-8);c.lineTo(ax,top-30);c.quadraticCurveTo(ax,hy-6,hx+6,hy-4);c.stroke();
  E(c,hx,hy,5,3.5,'#e6d2bd');const sw=reduced?0:Math.sin(time*1.1)*2.5;
  [[-16,14,BUTTER,'s'],[0,20,PINK,'h'],[16,13,BLUE,'s']].forEach(([dx,dy,col,kind])=>{const tx=hx+dx+sw,ty=hy+dy;L(c,hx+dx*.4,hy+1,tx,ty-5,'#cdb191',1);kind==='s'?star(c,tx,ty,6,col):heart(c,tx,ty+3,.2,col);});
  // Price tag heart on the left post.
  L(c,-W/2+5,top+4,-W/2-3,top+16,'#b89478',1);R(c,-W/2-12,top+15,18,13,CREAM,3,'#d2ae8e',1);heart(c,-W/2-3,top+24,.15,p.primary);}
/** Pram on display. */
function pram(c,p,W){const k=W/80;E(c,0,2,W*.52,6,SHADOW);
  for(const dx of [-24,22]){E(c,dx*k,-9*k,10*k,10*k,'#8d8a95');E(c,dx*k,-9*k,6*k,6*k,'#e9e6ee');E(c,dx*k,-9*k,2*k,2*k,'#8d8a95');}
  L(c,-20*k,-20*k,18*k,-20*k,'#b8b3bf',2.5*k);L(c,-24*k,-9*k,-4*k,-24*k,'#b8b3bf',2.5*k);L(c,22*k,-9*k,6*k,-24*k,'#b8b3bf',2.5*k);
  c.beginPath();c.moveTo(-34*k,-40*k);c.quadraticCurveTo(-30*k,-18*k,-4*k,-18*k);c.lineTo(26*k,-18*k);c.quadraticCurveTo(36*k,-22*k,34*k,-40*k);c.closePath();c.fillStyle=MINT;c.fill();c.strokeStyle=MINT_D;c.lineWidth=1.5;c.stroke();
  R(c,-30*k,-42*k,64*k,6*k,'#e5f5ee',3,MINT_D,1);heart(c,4*k,-28*k,.24*k,'#ffffffcc');
  c.beginPath();c.moveTo(-34*k,-40*k);c.arc(-8*k,-40*k,26*k,Math.PI,Math.PI*1.62);c.lineTo(-8*k,-40*k);c.closePath();c.fillStyle=PEACH;c.fill();c.strokeStyle=PEACH_D;c.lineWidth=1.5;c.stroke();
  for(let i=1;i<3;i++){const a=Math.PI+i*.2;L(c,-8*k,-40*k,-8*k+Math.cos(a)*26*k,-40*k+Math.sin(a)*26*k,PEACH_D,1.2);}
  L(c,32*k,-40*k,42*k,-58*k,'#b8b3bf',3*k);L(c,38*k,-60*k,48*k,-56*k,'#8d8a95',5*k);}
/** Ledger desk (the `finance`): the shop book and a piggy bank. */
function ledgerDesk(c,p,W,label,size){const h=40;E(c,0,2,W*.55,6,SHADOW);R(c,-W/2+4,-h+8,W-8,h-8,'#e9cba9',8,EDGE,1.5);R(c,-W/2-3,-h,W+6,11,'#f5dec6',5,EDGE,1.5);
  R(c,-W/2+10,-h+14,W-20,h-22,CREAM,4,'#dcc1a4',1);T(c,label,0,-h+14+(h-22)/2,fit(c,label,W-24,size,800),p.dark,800);
  R(c,-W/2+6,-h-18,34,17,'#fff8e7',3,'#d9b596',1);L(c,-W/2+23,-h-18,-W/2+23,-h-1,'#d9b596',1);L(c,-W/2+10,-h-12,-W/2+20,-h-12,p.primary,1.5);
  const px=W/2-18,py=-h-11;E(c,px,py,13,9,'#f7c8d4');E(c,px+11,py+1,4,3.5,'#eaa5b5');P(c,[[px-3,py-7],[px+2,py-11],[px+3,py-5]],'#eaa5b5');E(c,px+4,py-2,1.4,1.4,INK);R(c,px-5,py-9,7,2,'#a26d7a',1);}
/** Nursing armchair for mums (sunny / garden lease). */
function armchair(c,p,W,garden){const k=W/70;E(c,0,2,W*.55,6,SHADOW);L(c,-26*k,-4*k,-26*k,0,EDGE,4);L(c,26*k,-4*k,26*k,0,EDGE,4);
  R(c,-30*k,-56*k,60*k,40*k,PEACH,16*k,PEACH_D,1.5);R(c,-34*k,-24*k,68*k,20*k,PEACH,8*k,PEACH_D,1.5);R(c,-38*k,-38*k,12*k,30*k,'#f7c9b3',6*k,PEACH_D,1.2);R(c,26*k,-38*k,12*k,30*k,'#f7c9b3',6*k,PEACH_D,1.2);
  E(c,0,-26*k,20*k,6*k,'#fde8dc');heart(c,0,-40*k,.3*k,'#f3a7bb');if(garden)bloom(c,30*k,-58*k,9*k,p.primary);}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  E(c,600,722,505,28,'#cba88d22');R(c,85,128,1030,590,'#ebbfa6',35);R(c,96,132,1008,574,'#fff9f2',30,'#dfb39b',3);
  R(c,108,142,984,318,p.wall,22);wallpaper(c,p,108,142,984,318,1);
  // Baby-blue wainscot and soft maple floor.
  R(c,108,404,984,46,BLUE_L,0);for(let x=120;x<1092;x+=22)L(c,x,410,x,448,'#ffffffb0',2);R(c,108,400,984,7,'#bcd5ea',3);
  R(c,108,448,984,242,'#f8ecdc',16);c.save();c.beginPath();c.roundRect(108,448,984,242,16);c.clip();
  for(let i=0,y=452;y<690;i++,y+=34){R(c,108,y,984,34,i%2?'#faf0e2':'#f5e6d2',0);for(let x=108+(i%3)*90;x<1092;x+=270)L(c,x,y+3,x,y+31,'#e8d2b6',1.5);L(c,108,y,1092,y,'#ecd9c0',1);}c.restore();
  R(c,108,446,984,7,'#e8c9b2',3);
  signBoard(c,p,370,28,460,102);
  bunting(c,120,1080,150,8,22);
  for(const [x,y,k] of [[260,190,.8],[640,178,.6],[935,196,.7],[180,262,.5]])cloud(c,x,y,k,'#ffffffe0');
  for(const [x,y,r,col] of [[340,184,7,BUTTER],[588,208,6,'#f5c3d0'],[700,196,5,BUTTER],[860,222,6,'#bcd6ec'],[965,212,5,'#f5c3d0'],[110+300,380,5,BUTTER]])star(c,x,y,r,col);
  storeDoor(c,p,122,290,80,160,words.store,items.includes('lock'),13);
  toyCubbies(c,p,216,208,190,242,p.shelves[0],13,3);
  nurseryWindow(c,p,420,202,140,148,w.time,w.reduced);
  onesieLine(c,p,414,568,378,1);
  mobile(c,p,610,142,38,1.05,w.time,w.reduced);
  nappyShelf(c,p,650,216,196,234,13,3);
  streetBoard(c,p,866,254,1);
  giraffe(c,888,352,92,1);
  cloudPlaque(c,p,1016,236,1);
  nurseryDoor(c,p,974,276,86,174,12,open,words);
  security(c,p,items,[134,206],[950,262],[1016,268]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,448+i*38,350,7,[p.primary,'#f2b9c9','#f3d98a'][i]);
  playMat(c,p,590,664,120,20);}

function portRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#ebbfa6',31);R(c,29,117,642,724,'#fff9f2',26,'#dfb39b',3);
  R(c,40,139,620,372,p.wall,21);wallpaper(c,p,40,139,620,372,1);
  R(c,40,462,620,44,BLUE_L,0);for(let x=52;x<660;x+=20)L(c,x,468,x,504,'#ffffffb0',2);R(c,40,458,620,7,'#bcd5ea',3);
  R(c,40,504,620,325,'#f8ecdc',15);c.save();c.beginPath();c.roundRect(40,504,620,325,15);c.clip();
  for(let i=0,y=508;y<830;i++,y+=38){R(c,40,y,620,38,i%2?'#faf0e2':'#f5e6d2',0);for(let x=40+(i%3)*70;x<660;x+=210)L(c,x,y+3,x,y+35,'#e8d2b6',1.5);L(c,40,y,660,y,'#ecd9c0',1);}c.restore();
  R(c,40,502,620,7,'#e8c9b2',3);
  bunting(c,46,654,152,7,24);
  for(const [x,y,k] of [[120,214,.75],[548,214,.7],[240,236,.5]])cloud(c,x,y,k,'#ffffffe0');
  for(const [x,y,r,col] of [[186,198,7,BUTTER],[470,200,6,'#f5c3d0'],[430,236,5,BUTTER],[272,208,5,'#bcd6ec'],[88,296,6,'#f5c3d0']])star(c,x,y,r,col);
  storeDoor(c,p,46,338,66,168,words.store,items.includes('lock'),16);
  toyCubbies(c,p,122,256,148,250,p.shelves[0],16,3);
  nurseryWindow(c,p,284,228,132,122,w.time,w.reduced);
  onesieLine(c,p,280,420,386,1);
  mobile(c,p,350,139,30,1,w.time,w.reduced);
  nappyShelf(c,p,430,264,146,242,16,3);
  streetBoard(c,p,588,198,.98);
  cloudPlaque(c,p,620,297,.9);
  nurseryDoor(c,p,588,338,62,168,15,open,words);
  security(c,p,items,[52,206],[572,318],[618,326]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,306+i*30,358,6,[p.primary,'#f2b9c9','#f3d98a'][i]);
  playMat(c,p,365,797,112,24);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',worn=(w.c?.ops?.equipment?.condition??100)<100,t=w.time,rd=w.reduced,out=[];
  out.push([602,()=>at(c,405,602,1,()=>giftTable(c,p,180,worn,t,rd))]);
  out.push([602,()=>at(c,755,602,1,()=>checkout(c,p,190))]);
  out.push([598,()=>at(c,186,598,1,()=>crib(c,p,100,t,rd))]);
  out.push([598,()=>at(c,945,598,1,()=>changingTable(c,p,82))]);
  out.push([668,()=>at(c,186,668,1,()=>pram(c,p,76))]);
  out.push([668,()=>at(c,1028,668,1,()=>ledgerDesk(c,p,78,words.ledger,11))]);
  if(tier!=='cozy')out.push([676,()=>at(c,268,676,1,()=>armchair(c,p,62,tier==='garden'))]);
  if(tier==='garden')for(const [x,y] of w.plan().garden)out.push([y+4,()=>plantAt(c,x,y,.55)]);
  return out;}

function portProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',worn=(w.c?.ops?.equipment?.condition??100)<100,t=w.time,rd=w.reduced,out=[];
  out.push([656,()=>at(c,185,656,.95,()=>giftTable(c,p,182,worn,t,rd))]);
  out.push([656,()=>at(c,469,656,.95,()=>checkout(c,p,190))]);
  out.push([736,()=>at(c,102,736,1,()=>changingTable(c,p,80))]);
  out.push([736,()=>at(c,593,736,.92,()=>crib(c,p,108,t,rd))]);
  out.push([818,()=>at(c,190,818,1,()=>pram(c,p,78))]);
  out.push([818,()=>at(c,600,818,.9,()=>ledgerDesk(c,p,82,words.ledger,17))]);
  if(tier!=='cozy')out.push([818,()=>at(c,102,818,.95,()=>armchair(c,p,72,tier==='garden'))]);
  if(tier==='garden')for(const [x,y] of w.plan().garden)out.push([y+4,()=>plantAt(c,x,y,.5)]);
  return out;}

export default {
  id:'babyshop',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
