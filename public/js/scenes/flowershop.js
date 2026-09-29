/** Flower shop scene (florist): "Tiệm Hoa Nắng", a sunny little florist.
 * Back wall: sage paint over a whitewashed brick dado, ivy along the ceiling
 * and down both sides, bunches of flowers drying upside down, an arched
 * display window with hanging planters where Mướp naps, a chalkboard of
 * today's flowers, the street notice board, a green door with a wreath and
 * the open / closed sign (`door`), the shop plaque above it (`property`).
 * Floor: the glass flower cooler (`warehouse`), tiered wooden stands of zinc
 * buckets (`shelf`), the long wrapping table with kraft paper, ribbon spools
 * and a bouquet half wrapped (`workbench`, "Cắm hoa"), the till counter with
 * the order book (`evidence`) and the register (`counter`), a small ledger
 * desk (`finance`), a bucket crate by the entrance and petals on the stones.
 * PLAN schema: see scenes/shop.js.
 *
 * Floor pieces are drawn in local units with the origin at the middle of
 * their feet line and placed with `at(x, y, scale)`, so portrait reuses them.
 */
import {R,E,L,T,P,fit,heart,bloom,streetBoard} from './kit.js';

export const PLAN={
 land:{floor:[130,452,1070,682],lane:520,line:520,home:[600,520],kx:82,ky:45,sway:30,
   blocks:[[138,452,254,502],[270,452,480,502],[420,556,720,594],[800,556,980,594],[140,600,250,628],[990,628,1066,656],[104,662,146,680]],
   bench:[150,652,262,676],garden:[[1060,470],[475,684]],
   customers:[[500,652],[630,656],[760,652],[890,656]],event:[360,650],officer:[280,560],
   staff:{x:545,step:110,y:470},cat:[690,402],counterSpan:[420,980],
   decor:{corner:[165,568],front:[700,678],center:[1062,574]},sill:{plant:[540,400],lamp:[575,400],seat:[620,400],rug:[640,622]},
   wall:{poster:[952,405]},badge:{board:[33,-24]},
   spots:{shelf:[[375,380],95,[[375,520]]],evidence:[[835,500],45,[[835,520]]],workbench:[[585,470],70,[[585,520],[515,520]]],
     counter:[[935,495],50,[[935,520]]],warehouse:[[196,400],55,[[225,530],[196,545]]],board:[[920,297],45,[[920,520]]],
     finance:[[1028,618],42,[[950,650],[1028,610]]],property:[[1025,233],32,[[995,520]]],security:[[170,222],30,[[250,520]]],
     door:[[1025,370],55,[[1025,520]]],pet:[[690,384],38,[[690,520]]]}},
 port:{floor:[62,512,638,822],lane:616,line:616,home:[330,616],kx:51,ky:57,sway:22,
   blocks:[[44,508,152,598],[166,508,340,566],[120,660,400,700],[440,660,610,700],[560,790,640,818]],
   bench:[70,790,190,818],garden:[[80,700],[624,628]],
   customers:[[170,758],[300,762],[430,758],[560,762]],event:[230,808],officer:[420,808],
   staff:{x:200,step:100,y:584},cat:[500,400],counterSpan:[120,610],
   decor:{corner:[90,745],front:[480,818],center:[620,740]},sill:{plant:[378,400],lamp:[405,400],seat:[443,400],rug:[330,736]},
   wall:{poster:[98,318]},badge:{board:[27,-18]},
   spots:{shelf:[[253,440],90,[[253,616]]],evidence:[[475,590],45,[[475,616]]],workbench:[[262,578],60,[[262,616],[200,616]]],
     counter:[[565,586],45,[[565,616]]],warehouse:[[99,470],45,[[100,632],[190,616]]],board:[[576,227],40,[[576,590]]],
     finance:[[600,776],40,[[525,790],[600,776]]],property:[[630,226],30,[[620,590]]],security:[[87,240],30,[[175,616]]],
     door:[[598,400],50,[[598,580]]],pet:[[500,385],36,[[500,616]]]}},
};

/* ------------------------------------------------------------ Palette & helpers */
const SAGE='#e6efdc',SAGE_L='#eef4e6',SAGE_D='#a9c3a0',LEAF='#78ab80',LEAF_D='#5b9069',LEAF_L='#a6cd98',
  WOOD='#dfb690',WOOD_L='#f2d8b8',WOOD_D='#b98d69',EDGE='#a97f5e',ZINC='#cfd8db',ZINC_L='#eef2f3',ZINC_D='#97a7ac',
  KRAFT='#d6aa78',KRAFT_D='#b5875a',CREAM='#fffaf1',BRICK='#f4e6da',MORTAR='#e4cdbd',SHADOW='#7c6a5022',CHALK='#3f5b4c';
const ROSE={red:['#e5707f','#b94a5c'],pink:['#f6b8c8','#d98aa1'],peach:['#f8caa9','#dc9a78'],white:['#fff8f1','#dccbbd'],yellow:['#f8dc7c','#d9b04a']};
/** Draw `fn` with the origin at (x,y) scaled by s. */
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
const ring=(c,x,y,r,col,lw)=>{c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.strokeStyle=col;c.lineWidth=lw;c.stroke();};
/** A leaf of length `len` pointing at angle `a` from (x,y). */
function leaf(c,x,y,len,a,col=LEAF){c.save();c.translate(x,y);c.rotate(a);E(c,len/2,0,len/2,len*.2,col);L(c,len*.1,0,len*.8,0,'#ffffff40',1);c.restore();}

/* ------------------------------------------------------------ Flowers */
function rose(c,x,y,r,[col,dk]){E(c,x,y,r,r*.9,col);c.lineCap='round';c.strokeStyle=dk;c.lineWidth=Math.max(1,r*.2);
  c.beginPath();c.arc(x,y+r*.05,r*.58,Math.PI*.85,Math.PI*2.1);c.stroke();c.beginPath();c.arc(x+r*.08,y,r*.26,Math.PI*1.1,Math.PI*2.6);c.stroke();E(c,x-r*.38,y-r*.42,r*.24,r*.13,'#ffffff70');}
function sunflower(c,x,y,r){for(let i=0;i<12;i++){const a=i*Math.PI/6;c.save();c.translate(x+Math.cos(a)*r*.62,y+Math.sin(a)*r*.62);c.rotate(a);E(c,0,0,r*.48,r*.22,i%2?'#f7c948':'#f2b53a');c.restore();}
  E(c,x,y,r*.44,r*.44,'#8a5a34');E(c,x-r*.1,y-r*.12,r*.2,r*.15,'#a8744a');for(let i=0;i<5;i++)E(c,x+Math.cos(i*1.3)*r*.26,y+Math.sin(i*1.3)*r*.26,.9,.9,'#5f3d23');}
function lily(c,x,y,r){for(let i=0;i<6;i++){const a=i*Math.PI/3-Math.PI/2;P(c,[[x+Math.cos(a-.4)*r*.22,y+Math.sin(a-.4)*r*.22],[x+Math.cos(a)*r,y+Math.sin(a)*r],[x+Math.cos(a+.4)*r*.22,y+Math.sin(a+.4)*r*.22]],i%2?'#fffaf3':'#f7ede2');}
  for(let i=0;i<3;i++){const a=i*2.1+.4;L(c,x,y,x+Math.cos(a)*r*.5,y+Math.sin(a)*r*.5,'#b9a66c',1);E(c,x+Math.cos(a)*r*.5,y+Math.sin(a)*r*.5,1.6,1.2,'#c98a4a');}E(c,x,y,r*.15,r*.15,'#eed27a');}
function mum(c,x,y,r,col='#fffaf0',dk='#e8dfcc'){for(let i=0;i<14;i++){const a=i*Math.PI/7;c.save();c.translate(x+Math.cos(a)*r*.56,y+Math.sin(a)*r*.56);c.rotate(a);E(c,0,0,r*.46,r*.16,dk);c.restore();}
  for(let i=0;i<10;i++){const a=i*Math.PI/5+.3;c.save();c.translate(x+Math.cos(a)*r*.34,y+Math.sin(a)*r*.34);c.rotate(a);E(c,0,0,r*.34,r*.15,col);c.restore();}E(c,x,y,r*.18,r*.18,'#e3cc6a');}
function tulip(c,x,y,r,col,dk){P(c,[[x-r*.8,y-r*.6],[x-r*.3,y-r*.2],[x,y-r],[x+r*.3,y-r*.2],[x+r*.8,y-r*.6],[x+r*.7,y+r*.3],[x,y+r*.7],[x-r*.7,y+r*.3]],col);L(c,x,y-r*.6,x,y+r*.4,dk,1.2);}
function lavender(c,x,y,h,col='#b8a2da'){L(c,x,y,x,y-h,'#8aa77f',1.4);for(let i=0;i<6;i++)E(c,x+(i%2?1.2:-1.2),y-h+i*h*.08,2.2,2.8,col);}
function babys(c,x,y,rx,ry){for(let i=0;i<22;i++){const a=i*2.4,d=((i*37)%10)/10;E(c,x+Math.cos(a)*rx*d,y+Math.sin(a)*ry*d,1.8,1.8,'#fffdf7');}for(let i=0;i<7;i++)E(c,x+Math.cos(i*.9)*rx*.7,y+Math.sin(i*.9)*ry*.7,1,1,'#dde8cf');}
function euca(c,x,y,h,dir){c.strokeStyle='#8c9f8e';c.lineWidth=1.4;c.beginPath();c.moveTo(x,y);c.quadraticCurveTo(x+dir*h*.3,y-h*.6,x+dir*h*.12,y-h);c.stroke();
  for(let i=1;i<6;i++){const t=i/6,px=x+dir*h*.3*2*t*(1-t)+dir*h*.12*t*t,py=y-h*t;E(c,px-4,py,3.6,3,'#a9c2b3');E(c,px+4,py-2,3.6,3,'#9db8a9');}}

/** Stems, leaves and heads of one kind, rising from a bucket rim at (0,0). */
function bunch(c,kind){
  for(const [x,y,a] of [[-4,-2,-2.3],[4,-2,-.8],[-2,-6,-1.9],[3,-7,-1.2]])leaf(c,x,y,15,a,x<0?LEAF:LEAF_D);
  const stems=pts=>{for(const [x,y] of pts)L(c,x*.3,2,x,y,'#6f9f74',1.4);};
  if(kind==='sun'){const h=[[-9,-26],[10,-30],[0,-13]];stems(h);leaf(c,-6,-14,13,-2.6,LEAF_D);leaf(c,6,-18,13,-.5);h.forEach(([x,y])=>sunflower(c,x,y,9.5));}
  else if(kind==='lily'){const h=[[-9,-25],[9,-21],[0,-11]];stems([...h,[3,-36]]);E(c,3,-37,3,8,'#f3efe2');h.forEach(([x,y])=>lily(c,x,y,10));}
  else if(kind==='mum'){const h=[[-10,-19],[3,-27],[12,-15],[-2,-9]];stems(h);h.forEach(([x,y],i)=>mum(c,x,y,7.5,i%2?'#fffaf0':'#fff3cf',i%2?'#e8dfcc':'#ecd79a'));}
  else if(kind==='lav'){for(let i=-3;i<=3;i++)lavender(c,i*3.4,0,30-Math.abs(i)*3);}
  else if(kind==='baby'){stems([[-8,-16],[8,-18],[0,-22]]);babys(c,0,-18,16,11);}
  else if(kind==='euc'){euca(c,-3,0,34,-1);euca(c,3,0,36,1);euca(c,0,0,30,.3);}
  else if(kind==='tulip'){const h=[[-9,-20],[1,-27],[10,-19],[-3,-11],[7,-9]];stems(h);h.forEach(([x,y],i)=>tulip(c,x,y,5.5,i%2?'#f39aa9':'#f7c46c',i%2?'#d77388':'#d99e3e'));}
  else{const col=ROSE[kind]||ROSE.pink,h=[[-11,-20],[0,-27],[11,-21],[-6,-10],[7,-11]];stems(h);h.forEach(([x,y])=>rose(c,x,y,6.5,col));}}

/** Zinc bucket of flowers standing at (x, base); returns nothing. */
function bucket(c,kind,x,base,s=1,tag=null){at(c,x,base,s,()=>{const w=30,h=26;
  E(c,0,1,17,3.5,SHADOW);E(c,0,-h,w/2-2,3,'#6e7d82');
  at(c,0,-h,1,()=>bunch(c,kind));
  P(c,[[-w/2,-h],[w/2,-h],[w*.38,0],[-w*.38,0]],ZINC);P(c,[[w*.2,-h],[w/2,-h],[w*.38,0],[w*.18,0]],'#bac6ca');
  L(c,-w*.46,-h*.62,w*.46,-h*.62,ZINC_D,1.2);L(c,-w*.42,-h*.2,w*.42,-h*.2,ZINC_D,1.2);
  c.beginPath();c.ellipse(0,-h,w/2,3,0,0,Math.PI);c.strokeStyle=ZINC_L;c.lineWidth=2.4;c.stroke();
  for(const d of [-1,1])E(c,d*(w/2-1),-h+6,2,2.6,ZINC_D);
  if(tag){L(c,-6,-h+3,-3,-h+9,KRAFT_D,1);R(c,-9,-h+8,13,9,'#f6e6cc',2,KRAFT_D,.8);E(c,-7,-h+12.5,1.2,1.2,KRAFT_D);heart(c,-1.5,-h+13,.14,tag);}});}

/* ------------------------------------------------------------ Walls & floor */
function wallPaint(c,p,x,y,w,h,col){R(c,x,y,w,h,col,22);c.save();c.beginPath();c.roundRect(x,y,w,h,22);c.clip();
  for(let xx=x+14;xx<x+w;xx+=44)R(c,xx,y,18,h,'#ffffff2c',0);c.restore();}
/** Whitewashed brick dado from y0 to y1. */
function bricks(c,x,y0,w,y1){R(c,x,y0,w,y1-y0,BRICK,0);c.save();c.beginPath();c.rect(x,y0,w,y1-y0);c.clip();const bh=15;
  for(let r=0,y=y0;y<y1;r++,y+=bh){L(c,x,y,x+w,y,MORTAR,1.4);for(let xx=x+(r%2?-18:0);xx<x+w;xx+=38){L(c,xx,y,xx,y+bh,MORTAR,1.4);if((r*7+Math.round(xx/38))%9===0)R(c,xx+2,y+2,34,bh-3,'#efcfbe',2);}}c.restore();
  R(c,x,y0-6,w,8,'#eed9c3',2);L(c,x,y0-5,x+w,y0-5,'#fff7ec',2);}
/** Warm flagstone floor with a few petals. */
function flagstones(c,x,y,w,h,petals){c.save();c.beginPath();c.roundRect(x,y,w,h,16);c.clip();R(c,x,y,w,h,'#ead3bf',0);
  const sz=52;for(let r=0,yy=y;yy<y+h;r++,yy+=sz)for(let i=0,xx=x;xx<x+w;i++,xx+=sz){R(c,xx+1.5,yy+1.5,sz-3,sz-3,(r+i)%2?'#f6e4d4':'#f2dac8',3);
    if((r+i)%2===0){const cx=xx+sz/2,cy=yy+sz/2;P(c,[[cx,cy-9],[cx+9,cy],[cx,cy+9],[cx-9,cy]],'#f9ede2');E(c,cx,cy,2.4,2.4,'#e8b8a6');}}
  for(let r=0,yy=y;yy<=y+h;r++,yy+=sz)for(let xx=x;xx<=x+w;xx+=sz)P(c,[[xx,yy-5],[xx+5,yy],[xx,yy+5],[xx-5,yy]],'#c9dcc0');
  const pc=['#f2a7b8','#e5707f','#f8d77a','#fff6ee','#f6b8c8'];
  petals.forEach(([px,py,a],i)=>{c.save();c.translate(px,py);c.rotate(a);E(c,0,0,5,2.8,pc[i%5]);E(c,-1.5,-.8,2,1,'#ffffff60');c.restore();});
  c.restore();}
/** Ivy garland along the ceiling. */
function ivyTop(c,x0,x1,y){c.strokeStyle='#7f9f6f';c.lineWidth=2;c.beginPath();c.moveTo(x0,y);for(let x=x0;x<=x1;x+=40)c.quadraticCurveTo(x+20,y+10,x+40,y);c.stroke();
  for(let x=x0+6,i=0;x<x1;x+=17,i++){leaf(c,x,y+3+(i%3)*2,11+(i%2)*3,1.2+(i%4)*.35,i%3?LEAF:LEAF_L);if(i%5===2)bloom(c,x+4,y+10,3.5,i%2?'#f6b8c8':'#fff4dc');}}
/** A trailing ivy vine from (x,y0) down to y1. */
function ivyDown(c,x,y0,y1,dir){c.strokeStyle='#7f9f6f';c.lineWidth=1.8;c.beginPath();c.moveTo(x,y0);for(let y=y0;y<y1;y+=30)c.quadraticCurveTo(x+dir*8,y+15,x,y+30);c.stroke();
  for(let y=y0+8,i=0;y<y1;y+=16,i++)leaf(c,x+(i%2?3:-3),y,10+(i%3)*2,i%2?.5:2.6,i%3?LEAF:LEAF_D);}
/** Bunches of flowers hanging upside down to dry from a rod. */
function dryingRod(c,x0,x1,y,s=1){L(c,x0-6,y,x1+6,y,WOOD_D,4);E(c,x0-6,y,3,3,EDGE);E(c,x1+6,y,3,3,EDGE);const n=Math.max(3,Math.round((x1-x0)/40)),kinds=['lav','rose','baby','wheat','rose','lav'];
  for(let i=0;i<n;i++){const x=x0+(i+.5)*(x1-x0)/n,k=kinds[i%6],len=(14+(i%2)*8)*s;L(c,x,y,x,y+len,'#b79a74',1);const ty=y+len;
    for(let j=-2;j<=2;j++)L(c,x+j*.8,ty,x+j*4*s,ty+24*s,'#9aa482',1.3);R(c,x-4*s,ty-1,8*s,5*s,KRAFT,2);
    if(k==='lav')for(let j=-2;j<=2;j++)for(let q=0;q<4;q++)E(c,x+j*4*s,ty+(24+q*4)*s,2*s,2.6*s,'#a693c6');
    else if(k==='rose')for(const [dx,dy] of [[-5,27],[5,28],[0,33]])rose(c,x+dx*s,ty+dy*s,4.6*s,['#c98a8f','#9e5f68']);
    else if(k==='baby')babys(c,x,ty+30*s,11*s,7*s);
    else for(let j=-2;j<=2;j++){c.save();c.translate(x+j*4*s,ty+30*s);E(c,0,0,2*s,6*s,'#dcbb7a');c.restore();}}}
/** Arched display window with hanging planters; `count` = planters. */
function displayWindow(c,p,x,y,w,h,time,reduced,count){const rr=Math.min(w/2-6,70);
  R(c,x-10,y-10,w+20,h+14,'#dcb893',[rr+10,rr+10,8,8]);c.save();c.beginPath();c.roundRect(x,y,w,h,[rr,rr,6,6]);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#cfeaf0');g.addColorStop(1,'#eef6e6');c.fillStyle=g;c.fillRect(x,y,w,h);
  E(c,x+w*.74,y+h*.26,18,18,'#fff1c0');const drift=reduced?0:(time*5)%(w+60);
  for(const [dx,dy] of [[.18,.22],[.6,.44]]){const cx=x+((w*dx+drift)%(w+60))-30;E(c,cx,y+h*dy,18,7,'#ffffffd0');E(c,cx+11,y+h*dy-5,11,7,'#ffffffd0');}
  R(c,x,y+h*.78,w,h*.22,'#e8dcc8',0);E(c,x+w*.14,y+h*.7,w*.2,h*.2,'#a9cfad');E(c,x+w*.9,y+h*.72,w*.2,h*.24,'#9fc6a6');L(c,x+w*.14,y+h*.86,x+w*.14,y+h*.7,'#a9876a',4);
  L(c,x+w*.5,y+h*.5,x+w*.5,y+h*.84,'#8b8f8a',3);E(c,x+w*.5,y+h*.49,6,5,'#fff1c0');
  c.restore();
  // Mullions, hand-painted flower on the glass, sill.
  L(c,x+w/2,y+2,x+w/2,y+h-2,'#fffaf0',6);L(c,x+2,y+h*.56,x+w-2,y+h*.56,'#fffaf0',6);
  for(let i=0;i<6;i++){const a=i*Math.PI/3;E(c,x+w*.3+Math.cos(a)*6,y+h*.36+Math.sin(a)*6,4,4,'#ffffff90');}E(c,x+w*.3,y+h*.36,3,3,'#f8d77a');
  R(c,x-16,y+h,w+32,12,'#d4a487',5);R(c,x-12,y+h+1,w+24,4,'#e8c2a4',2);
  // Hanging macramé planters with trailing ivy.
  const spots=count>1?[x+w*.16,x+w*.84]:[x+w*.18];
  spots.forEach((hx,i)=>{const top=y-14,py=y+h*.3+(i%2)*10;E(c,hx,top,3,3,EDGE);for(const d of [-12,0,12])L(c,hx,top,hx+d,py-12,'#d9c3a0',1.3);
    R(c,hx-15,py-14,30,20,'#e9a07f',[3,3,10,10]);R(c,hx-16,py-16,32,5,'#d88b6c',2);
    for(let j=0;j<5;j++)leaf(c,hx-12+j*6,py-15,10,-1.9+j*.4,j%2?LEAF:LEAF_L);ivyDown(c,hx-10,py,py+46+i*10,-1);ivyDown(c,hx+9,py,py+30,1);});}
/** Chalkboard of today's flowers. */
function chalkboard(c,p,x,y,w,h,size){L(c,x+w/2,y-16,x+12,y,'#b39070',1.5);L(c,x+w/2,y-16,x+w-12,y,'#b39070',1.5);E(c,x+w/2,y-16,3,3,'#b39070');
  R(c,x-5,y-5,w+10,h+10,'#b98a5e',8);R(c,x,y,w,h,CHALK,5);E(c,x+w*.3,y+h*.3,w*.25,h*.2,'#ffffff08');
  const rows=[['Hồng đỏ','#f2a0ac'],['Hướng dương','#f7d368'],['Ly trắng','#fffaf0'],['Cúc trắng','#e9f0d8']],top=y+size*1.9,rh=(h-size*2.4)/rows.length;
  for(let i=0;i<3;i++)bloom(c,x+w/2+(i-1)*size*1.3,y+size*.95,size*.34,['#f2a0ac','#f7d368','#bfe0a4'][i]);
  rows.forEach(([name,col],i)=>{const yy=top+rh*(i+.5);E(c,x+size*.8,yy,size*.3,size*.3,col);T(c,name,x+size*1.5,yy+1,fit(c,name,w-size*2,size,600),'#f4f1e3',600,'left');});
  R(c,x+w-26,y+h-6,20,5,'#f7f1e2',2);}
/** Framed little shop front: the `property` hotspot. */
function plaque(c,p,x,y,w,h){R(c,x,y,w,h,'#c89f7f',7);R(c,x+4,y+4,w-8,h-8,CREAM,5);const cx=x+w/2,b=y+h-8,s=w/44;
  R(c,cx-14*s,b-18*s,28*s,18*s,'#f3dfe4',2);for(let i=0;i<4;i++)R(c,cx-15*s+i*7.5*s,b-24*s,7.5*s,7*s,i%2?CREAM:p.primary,[0,0,3*s,3*s]);
  R(c,cx-4*s,b-12*s,8*s,12*s,'#8fb389',2);E(c,cx-9*s,b-2*s,3*s,2.5*s,'#e5707f');E(c,cx+9*s,b-2*s,3*s,2.5*s,'#f7c948');}
/** Green door with a wreath and the open / closed sign. */
function door(c,p,x,y,w,h,size,open,words){R(c,x-8,y-8,w+16,h+8,'#cfa47f',[12,12,0,0]);R(c,x,y,w,h,'#9fc197',[8,8,0,0],'#7fa377',2);
  R(c,x+w*.16,y+h*.08,w*.68,h*.4,open?'#e9f6ef':'#d3e9e6',6,'#7fa377',2);L(c,x+w*.18,y+h*.3,x+w*.42,y+h*.12,'#ffffffb0',3);
  R(c,x+w*.16,y+h*.58,w*.68,h*.34,'#b2d0aa',5,'#8fb389',1.5);E(c,x+w-12,y+h*.54,4,4,'#e1c16f');
  // Wreath on the glass.
  const wx=x+w/2,wy=y+h*.28,r=Math.min(w*.24,h*.1);for(let i=0;i<14;i++){const a=i*Math.PI/7;leaf(c,wx+Math.cos(a)*r,wy+Math.sin(a)*r,r*.7,a+1.9,i%2?LEAF:LEAF_D);}
  for(let i=0;i<4;i++){const a=i*Math.PI/2+.4;rose(c,wx+Math.cos(a)*r,wy+Math.sin(a)*r,r*.26,i%2?ROSE.pink:ROSE.red);}
  P(c,[[wx-6,wy+r+2],[wx,wy+r+6],[wx+6,wy+r+2],[wx+4,wy+r+12],[wx,wy+r+7],[wx-4,wy+r+12]],p.primary);
  if(open){P(c,[[x+w-3,y],[x+w+10,y-4],[x+w+10,y+h],[x+w-3,y+h]],'#8fb389');}
  const s=open?words.open_sign:words.closed_sign,sw=w+14,sy=y+h*.5;L(c,wx,sy-12,wx-16,sy,'#b39070',1.5);L(c,wx,sy-12,wx+16,sy,'#b39070',1.5);
  R(c,wx-sw/2,sy,sw,size*1.9,'#fff8e8',9,open?'#8fb77f':'#d59a9a',2);T(c,s,wx,sy+size*.97,fit(c,s,sw-10,size,800),open?p.dark:'#a35f63',800);}
/** Hanging shop sign with a sunflower (the scene's title; phones hide it under the title card). */
function sign(c,p,x,y,w,h){R(c,x-4,y+8,w+8,h,'#b58b69',30);R(c,x,y,w,h,'#fffaf1',28,'#dcb994',3);R(c,x+9,y+9,w-18,h-18,'#fffdf7',22,'#e6d3b5',1.5);
  sunflower(c,x+54,y+h/2,28);const cx=x+w/2+26;T(c,p.title,cx,y+h*.42,fit(c,p.title,w-160,30,800),p.dark,800);T(c,p.sub,cx,y+h-25,fit(c,p.sub,w-140,13),p.dark);
  for(const [lx,ly,a] of [[w-34,4,-.6],[w-22,8,.3],[w-44,10,-1.4],[w-10,20,1.1]])leaf(c,x+lx,y+ly,16,a,LEAF);rose(c,x+w-30,y+10,7,ROSE.pink);rose(c,x+w-16,y+18,6,ROSE.red);bloom(c,x+w-42,y+18,5,'#fff4dc');}
/** Security gear at the given spots (camera or a plaque, bell, lamp). */
function security(c,p,items,[cx,cy],[bx,by],[lx,ly]){
  if(items.includes('camera')){L(c,cx-18,cy+12,cx-4,cy+3,'#b79b85',4);R(c,cx-12,cy-10,38,20,'#f5f2eb',7,'#a7aaa2',2);E(c,cx+21,cy,7,8,'#7a8992');E(c,cx+22,cy,3,4,'#b4d9df');E(c,cx-6,cy-5,2,2,'#90bd8b');}
  else{R(c,cx-16,cy-11,38,22,'#fff6e9',8,'#d5b59a',1);T(c,'♧',cx+3,cy,14,p.dark);}
  if(items.includes('bell')){L(c,bx,by-14,bx,by-4,'#ac8f73',2);P(c,[[bx-10,by+12],[bx+10,by+12],[bx+7,by-3],[bx-7,by-3]],'#f0ce85');E(c,bx,by+14,4,3,'#d4ad64');}
  if(items.includes('light')){const g=c.createRadialGradient(lx,ly+18,0,lx,ly+18,80);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(lx-80,ly-62,160,160);
    L(c,lx,ly-14,lx,ly-6,'#b69b79',3);R(c,lx-12,ly-6,24,22,'#fff0b8',[4,4,9,9],'#b69b79',2);}}

/* ------------------------------------------------------------ Floor pieces (local units, origin = middle of the feet line) */
/** Glass flower cooler: the `warehouse`. */
function cooler(w,p,W,H,ts){const c=w.ctx,items=w.c?.ops?.security?.items||[];
  E(c,0,2,W/2+10,7,SHADOW);R(c,-W/2,-H,W,H,'#f1f5f0',10,'#9fb8a6',2);
  const hh=ts*1.9;R(c,-W/2+6,-H+6,W-12,hh,'#dcebd6',7);T(c,'❄',-W/2+6+ts*.8,-H+6+hh/2,ts,'#6f9fb0');T(c,'Tủ mát',ts*.4,-H+6+hh/2+1,fit(c,'Tủ mát',W-ts*2.6,ts,800),'#4f7560',800);
  const gx=-W/2+8,gy=-H+hh+12,gw=W-16,gh=H-hh-12-32;
  c.save();c.beginPath();c.roundRect(gx,gy,gw,gh,5);c.clip();const g=c.createLinearGradient(gx,gy,gx+gw,gy+gh);g.addColorStop(0,'#eef9fa');g.addColorStop(1,'#d3eaee');c.fillStyle=g;c.fillRect(gx,gy,gw,gh);
  const rows=3,rh=gh/rows,kinds=['red','lily','pink','sun','white','tulip','peach','mum','baby'];
  for(let r=0;r<rows;r++){const base=gy+rh*(r+1)-4;const n=Math.max(2,Math.floor(gw/30));for(let i=0;i<n;i++)bucket(c,kinds[(r*3+i)%9],gx+gw*(i+.5)/n,base,.62);R(c,gx,base,gw,4,'#b9c9cc',1);}
  R(c,gx,gy,gw,gh,'#e8f6f855',0);L(c,gx+gw*.12,gy+gh*.62,gx+gw*.5,gy+gh*.08,'#ffffffa0',5);L(c,gx+gw*.3,gy+gh*.8,gx+gw*.72,gy+gh*.22,'#ffffff70',3);R(c,gx,gy+gh-10,gw,10,'#ffffff80',0);c.restore();
  c.beginPath();c.roundRect(gx,gy,gw,gh,5);c.strokeStyle='#a9bfc3';c.lineWidth=2;c.stroke();L(c,0,gy,0,gy+gh,'#a9bfc3',2);
  R(c,-6,gy+gh*.4,3,18,'#c8d4d6',1.5);R(c,3,gy+gh*.4,3,18,'#c8d4d6',1.5);
  R(c,-W/2+8,-28,W-16,20,'#dfe7e1',4);for(let x=-W/2+16;x<W/2-44;x+=8)L(c,x,-24,x,-12,'#b7c6bd',2);
  R(c,W/2-40,-26,28,14,'#4b5a55',3);T(c,'4°C',W/2-26,-19,9,'#b6f0c0',700);
  R(c,-W/2+4,-4,10,6,'#b7c6bd',2);R(c,W/2-14,-4,10,6,'#b7c6bd',2);
  // Pothos on top.
  R(c,-W/2+10,-H-18,26,18,'#e9a07f',[3,3,8,8]);for(let j=0;j<5;j++)leaf(c,-W/2+13+j*5,-H-18,11,-2+j*.45,j%2?LEAF:LEAF_L);ivyDown(c,-W/2+12,-H,-H+hh+30,-1);
  R(c,W/2-44,-H-12,34,12,'#f6e6cc',2,KRAFT_D,1);L(c,W/2-44,-H-6,W/2-10,-H-6,KRAFT_D,1);
  if(items.includes('lock')){const lx=W/2-16,ly=gy+gh*.5;R(c,lx-8,ly,16,18,'#d8c596',5,'#a09675',1);c.beginPath();c.arc(lx,ly,5,Math.PI,0);c.strokeStyle='#a09675';c.lineWidth=3;c.stroke();}}
/** Stepped wooden stand of zinc buckets: the `shelf`. W is its width. */
function stand(c,p,W){const hw=W/2;E(c,0,2,hw+8,7,SHADOW);
  const tiers=[{y:-96,xs:[-.72,-.24,.24,.72],k:['sun','lily','sun','euc']},{y:-54,xs:[-.8,-.32,.16,.64],k:['red','lav','pink','mum']},{y:-12,xs:[-.62,-.14,.34,.82],k:['tulip','white','baby','red']}];
  // Side frames step down towards the viewer.
  for(const d of [-1,1]){R(c,d*hw-(d>0?8:0),-102,8,102,WOOD_D,2);}
  tiers.forEach((t,i)=>{if(i<2){R(c,-hw+10,t.y+8,6,-t.y-8,EDGE,2);R(c,hw-16,t.y+8,6,-t.y-8,EDGE,2);}
    R(c,-hw,t.y,W,9,WOOD,3,EDGE,1.5);L(c,-hw+4,t.y+2,hw-4,t.y+2,WOOD_L,2);
    t.xs.forEach((f,j)=>bucket(c,t.k[j],f*(hw-16),t.y,i===2?1.05:1,i===2&&j%2===0?p.primary:null));});
  // Watering can resting on the floor at the stand's end.
  at(c,hw-14,0,.8,()=>{E(c,0,1,16,3,SHADOW);R(c,-12,-24,24,24,'#a9c9b8',[6,6,4,4],'#7fa392',1.5);L(c,10,-14,26,-30,'#7fa392',3.5);E(c,28,-31,4,3,'#a9c9b8');c.beginPath();c.arc(-2,-24,10,Math.PI,0);c.strokeStyle='#7fa392';c.lineWidth=3;c.stroke();R(c,-12,-14,24,4,'#ffffff40',2);});}
/** The long wrapping table ("Cắm hoa"): the `workbench`. */
function wrapTable(w,p,W,ts){const c=w.ctx,hw=W/2,top=-90,cond=w.c?.ops?.equipment?.condition??100,check=w.c?.upgrades?.includes('workbench');
  E(c,0,3,hw+14,8,SHADOW);
  for(const d of [-1,1])R(c,d*(hw-24)-4,top+12,8,-top-16,EDGE,2);
  // Lower shelf: paper rolls and tissue stacks.
  R(c,-hw+10,-24,W-20,7,WOOD,2,EDGE,1);
  const rolls=[['#f5c6d4','#e3a3b6'],[CREAM,'#e3d6c4'],[KRAFT,KRAFT_D],['#cfe2c6','#a9c3a0']];
  rolls.forEach(([a,b],i)=>{const rx=-hw+22+i*44;R(c,rx,-40,40,16,a,8,b,1);E(c,rx+40,-32,4,8,b);E(c,rx+40,-32,1.5,3,'#8b735355');});
  for(let i=0;i<3;i++)R(c,hw-78,-30-i*5,50,5,['#fdeef3','#fff8ef','#f7e7c9'][i],1.5,'#d9c6b0',.8);
  for(const d of [-1,1])R(c,d*(hw-8)-6,top+12,12,-top-12,WOOD_D,3);
  // Apron with the label.
  R(c,-hw+2,top+10,W-4,22,WOOD,3,EDGE,1.5);for(let x=-hw+30;x<hw-20;x+=60)L(c,x,top+14,x,top+28,'#c89e79',1.2);
  const lab=w.game?.catalogue?.find(x=>x.id===w.career)?.station||'Cắm hoa',lw=Math.min(W*.42,ts*7.5);R(c,-lw/2,top+12,lw,18,'#f6e6cc',4,KRAFT_D,1);T(c,lab,0,top+21.5,fit(c,lab,lw-16,ts,800),p.dark,800);
  R(c,-hw-6,top,W+12,13,WOOD_L,5,EDGE,1.5);L(c,-hw,top+3,hw,top+3,'#fff0dc',2);
  // Kraft roll on its dispenser, the sheet draped over the front edge.
  const dx=-hw+10;P(c,[[dx+4,top-8],[dx+60,top-8],[dx+58,top+1],[dx+6,top+1]],'#8b73531c');
  for(const bx of [dx,dx+62]){P(c,[[bx-2,top],[bx+8,top],[bx+6,top-22],[bx,top-22]],WOOD_D);E(c,bx+3,top-20,5,5,EDGE);}
  P(c,[[dx+8,top-16],[dx+58,top-16],[dx+62,top+22],[dx+52,top+30],[dx+34,top+26],[dx+16,top+31],[dx+6,top+20]],'#e2bd8f');L(c,dx+10,top+2,dx+60,top+2,'#c99b69',1);
  R(c,dx+4,top-28,58,18,KRAFT,9,KRAFT_D,1.5);L(c,dx+10,top-24,dx+56,top-24,'#ecd0a8',2.5);L(c,dx+10,top-14,dx+56,top-14,'#c1905f',1);
  for(const ex of [dx+4,dx+62]){E(c,ex,top-19,4,9,'#c8996a');ring(c,ex,top-19,3,'#a57a50',1);ring(c,ex,top-19,6,'#b5875a',1);}
  // Bouquet in a cone of pink paper, ribbon bow.
  const bx=-4;at(c,bx,top,1,()=>{for(const [x,y,a] of [[-18,-44,-2.4],[18,-46,-.7],[-8,-58,-1.9],[10,-58,-1.2]])leaf(c,x,y,18,a,LEAF_D);
    euca(c,-20,-34,26,-1);euca(c,20,-34,26,1);babys(c,0,-62,22,10);
    rose(c,-11,-54,8,ROSE.pink);rose(c,8,-58,8,ROSE.red);rose(c,-1,-46,8,ROSE.peach);rose(c,15,-44,7,ROSE.pink);rose(c,-17,-42,6.5,ROSE.white);
    P(c,[[-30,-40],[-6,-34],[0,-1],[-4,-1]],'#f7cbd7');P(c,[[30,-40],[6,-34],[0,-1],[4,-1]],'#f3b9c9');P(c,[[-16,-38],[16,-38],[3,-1],[-3,-1]],p.light);
    L(c,-12,-30,0,-4,'#e6a8ba',1);L(c,12,-30,0,-4,'#e6a8ba',1);
    E(c,-6,-16,7,4,p.primary);E(c,6,-16,7,4,p.primary);E(c,0,-16,3,3,p.dark);L(c,-1,-14,-6,-2,p.primary,2);L(c,1,-14,6,-3,p.primary,2);});
  // Scissors, twine, cut leaves.
  at(c,34,top+2,1,()=>{L(c,-2,-4,18,-10,'#9aa6ab',2.5);L(c,-2,-10,18,-4,'#9aa6ab',2.5);ring(c,-6,-3,3.5,p.primary,2);ring(c,-6,-11,3.5,p.primary,2);});
  E(c,62,top-5,9,8,'#e9d3a6');for(let i=0;i<3;i++)L(c,55,top-9+i*4,69,top-7+i*3,'#cdb080',1);
  leaf(c,76,top+1,10,-.2,LEAF_L);leaf(c,86,top+2,9,.4,LEAF);E(c,98,top+2,3,1.6,'#e5707f');
  // Ribbon spools on a rod, tails over the edge.
  const sx=hw-50;R(c,sx-24,top-40,5,40,EDGE,2);R(c,sx+24,top-40,5,40,EDGE,2);L(c,sx-24,top-34,sx+28,top-34,EDGE,3);
  [[p.primary,-14],['#f7c948',0],['#9fc197',14]].forEach(([col,ox])=>{R(c,sx+ox-6,top-44,12,20,col,3,'#00000022',1);R(c,sx+ox-7,top-45,14,3,'#e9d8c2',1);
    c.beginPath();c.moveTo(sx+ox,top-24);c.quadraticCurveTo(sx+ox+6,top+4,sx+ox-2,top+18);c.quadraticCurveTo(sx+ox-6,top+26,sx+ox+2,top+32);c.strokeStyle=col;c.lineWidth=3;c.stroke();});
  if(check){R(c,hw-36,top-30,22,28,CREAM,4,'#c7ad90',1.5);L(c,hw-31,top-20,hw-27,top-16,'#6fae7c',2);L(c,hw-27,top-16,hw-19,top-24,'#6fae7c',2);L(c,hw-31,top-9,hw-19,top-9,'#c4b3a0',1.5);}
  if(cond<100){const tw=ts*6.5,th=ts*1.6,tx=-hw+8,ty=top-58;L(c,tx+12,top-26,tx+16,ty+th,'#b48d64',1.5);L(c,tx+tw-12,top-26,tx+tw-16,ty+th,'#b48d64',1.5);R(c,tx,ty,tw,th,'#f7d995',6,'#d3a35c',1.5);T(c,'CẦN KIỂM',tx+tw/2,ty+th/2+1,fit(c,'CẦN KIỂM',tw-10,ts,800),'#94643d',800);}}
/** Till counter: the order book (`evidence`) on the left, register (`counter`) on the right. */
function till(w,p,W,big){const c=w.ctx,hw=W/2,top=-94;E(c,0,3,hw+12,8,SHADOW);
  R(c,-hw,top+12,W,-top-12,'#cfe2c6',8,'#9fbf9a',2);for(let x=-hw+14;x<hw-6;x+=14)L(c,x,top+20,x,-10,'#b9d3b0',2);R(c,-hw,-12,W,12,'#b7cfae',[0,0,8,8]);
  E(c,0,top+50,15,15,CREAM);ring(c,0,top+50,15,p.primary,2);rose(c,0,top+50,7,ROSE.red);leaf(c,4,top+56,8,.6,LEAF);
  R(c,-hw-6,top,W+12,14,WOOD_L,6,EDGE,1.5);L(c,-hw,top+3,hw,top+3,'#fff0dc',2);
  // Order book, open, with a bookmark and a pen; order slips on a spike.
  const ox=-hw+(big?40:34);P(c,[[ox-24,top+2],[ox,top+5],[ox,top-9],[ox-22,top-13]],'#fff8e7');P(c,[[ox+24,top+2],[ox,top+5],[ox,top-9],[ox+22,top-13]],'#fffdf5');L(c,ox,top+5,ox,top-9,'#c7ad90',1.5);
  for(let i=0;i<2;i++){L(c,ox-18,top-7+i*4,ox-5,top-5+i*4,'#c4b3a0',1.2);L(c,ox+5,top-5+i*4,ox+18,top-7+i*4,'#c4b3a0',1.2);}heart(c,ox-11,top-3,.13,p.primary);L(c,ox+2,top+3,ox+2,top+12,p.primary,2);L(c,ox+14,top,ox+28,top-12,'#6f5646',2);
  const kx=ox+(big?44:38);L(c,kx,top+1,kx,top-26,'#9aa6ab',2);E(c,kx,top+1,7,2.5,'#9aa6ab');for(let i=0;i<3;i++){c.save();c.translate(kx,top-8-i*6);c.rotate((i-1)*.25);R(c,-9,-4,18,8,['#fff8e7','#fdeef3','#eef7ee'][i],1.5,'#c9b8a3',.8);c.restore();}
  // Bud vase with one rose.
  const vx=big?6:10;R(c,vx-5,top-18,10,18,'#dff0f2c0',4,'#a9c9d0',1);L(c,vx,top-16,vx+2,top-40,'#6f9f74',1.5);leaf(c,vx+1,top-28,9,-.6,LEAF);rose(c,vx+2,top-42,6,ROSE.red);
  // Vintage register.
  const rx=hw-(big?36:40);R(c,rx-26,top-34,52,34,'#f3d7dd',7,p.dark,1.5);R(c,rx-20,top-46,26,14,CREAM,3,'#c9a9b2',1);T(c,'♡',rx-7,top-39,10,p.primary);
  for(let i=0;i<4;i++)for(let j=0;j<2;j++)E(c,rx-16+i*9,top-24+j*7,2.4,2.4,j?'#fff8ef':p.primary);R(c,rx-24,top-8,48,6,'#e7bfc9',2);R(c,rx+12,top-44,10,10,'#fff8ef',2,'#c9a9b2',1);
  E(c,rx+32,top-4,5,3,'#e1c16f');E(c,rx+32,top-7,3,3,'#f0d58c');}
/** Small ledger desk: the `finance` hotspot. */
function ledgerDesk(w,p,ts){const c=w.ctx,words=w.words();E(c,0,2,44,6,SHADOW);R(c,-38,-44,6,44,EDGE,2);R(c,32,-44,6,44,EDGE,2);
  R(c,-40,-44,80,32,WOOD,7,EDGE,1.5);R(c,-33,-38,66,20,'#f6e6cc',4);T(c,words.ledger,0,-28,fit(c,words.ledger,60,ts,800),'#6f5646',800);
  R(c,-46,-54,92,12,WOOD_L,5,EDGE,1.5);P(c,[[-26,-55],[-2,-52],[-2,-64],[-24,-67]],'#fff8e7');P(c,[[22,-55],[-2,-52],[-2,-64],[20,-67]],'#fffdf5');L(c,-18,-60,-6,-58,p.primary,1.5);L(c,3,-58,15,-60,'#c4b3a0',1.5);
  R(c,26,-68,16,14,'#e9a07f',[2,2,5,5]);for(let j=0;j<4;j++)leaf(c,28+j*4,-68,8,-2.1+j*.45,j%2?LEAF:LEAF_L);}
/** Low crate of buckets by the entrance (landscape). */
function crate(c,p){E(c,0,2,58,7,SHADOW);bucket(c,'sun',-34,-22,1);bucket(c,'pink',0,-24,1.05,p.primary);bucket(c,'tulip',34,-22,1);
  R(c,-56,-24,112,24,WOOD,4,EDGE,1.5);for(const y of [-17,-9])L(c,-52,y,52,y,'#c89e79',1.5);for(const x of [-56,50])R(c,x,-24,6,24,WOOD_D,2);}
/** Big monstera in a terracotta pot (landscape front corner). */
function monstera(c){E(c,0,2,26,6,SHADOW);const ls=[[-34,-72,-2.5],[26,-86,-.6],[-10,-108,-1.7],[14,-62,-.2],[-30,-46,-2.9]];
  ls.forEach(([x,y,a],i)=>{L(c,0,-30,x*.6,y*.8,'#6b9a6c',2.5);c.save();c.translate(x,y);c.rotate(a+Math.PI/2);E(c,0,0,17,22,i%2?'#6ea77a':'#5f9a70');for(const d of [-1,1])for(const k of [-8,2])L(c,d*6,k,d*17,k-3,'#fff9ee',2);L(c,0,-20,0,20,'#8dc095',1.2);c.restore();});
  P(c,[[-20,-34],[20,-34],[15,0],[-15,0]],'#e39b78');R(c,-23,-38,46,8,'#d38766',3);L(c,-15,-22,15,-22,'#f0b596',2);}
/** Garden bench with a cushion (sunny / garden tiers). */
function bench(c,p,W,garden){const hw=W/2;E(c,0,2,hw+6,6,SHADOW);for(const x of [-hw+6,hw-12])R(c,x,-26,6,26,'#8fb389',2);
  R(c,-hw,-64,W,30,'#b8d4ae',10,'#8fb389',1.5);for(let x=-hw+14;x<hw-6;x+=14)L(c,x,-60,x,-38,'#e8f2e2',2);R(c,-hw-4,-34,W+8,10,'#a8c79f',5,'#8fb389',1.5);
  R(c,-hw+8,-44,W*.45,12,'#f6c9d4',6);heart(c,-hw+8+W*.22,-37,.22,'#fff8ef');if(garden){bucket(c,'sun',hw-18,-34,.72);}}
/** Terracotta pot of blooms (garden tier). */
function potBloom(c,x,y,s,col){at(c,x,y,s,()=>{E(c,0,1,16,4,SHADOW);for(const [dx,dy,a] of [[-8,-30,-2.4],[8,-32,-.7],[0,-36,-1.6]])leaf(c,dx*.4,-20,14,a,LEAF);
  bloom(c,-8,-38,6,col);bloom(c,7,-42,6,col);bloom(c,0,-30,5,'#fff4dc');P(c,[[-13,-22],[13,-22],[10,0],[-10,0]],'#e39b78');R(c,-15,-25,30,6,'#d38766',2);});}

/* ------------------------------------------------------------ Rooms */
const LAND_PETALS=[[300,528,.4],[352,560,1.2],[455,612,2],[520,604,.7],[742,640,2.6],[780,610,1.1],[612,672,.3],[1010,560,1.8],[236,660,.9],[880,672,2.2],[690,612,1.5],[160,540,.2]];
const PORT_PETALS=[[150,605,.4],[250,720,1.2],[370,730,2],[420,640,.7],[520,730,2.6],[610,760,1.1],[90,800,.3],[340,800,1.8],[210,640,.9],[480,610,2.2]];
function wallColor(w,p){return ['sage','lavender','warm'].includes(w.c?.theme)?p.wall:SAGE;}
function landRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  E(c,605,724,503,30,'#8fa07c22');R(c,85,165,1030,550,'#dcb391',35);R(c,96,168,1008,533,'#fffaf1',30,'#d7b391',3);
  wallPaint(c,p,108,179,984,270,wallColor(w,p));bricks(c,108,372,984,446);
  flagstones(c,108,445,984,244,LAND_PETALS);R(c,108,440,984,9,'#d9c2a4',3);
  sign(c,p,360,56,480,102);
  ivyDown(c,114,190,420,1);ivyDown(c,1086,190,420,-1);ivyTop(c,108,1092,184);
  dryingRod(c,300,470,212);
  displayWindow(c,p,500,214,240,178,w.time,w.reduced,2);
  chalkboard(c,p,764,232,108,118,13);
  streetBoard(c,p,888,258);
  plaque(c,p,1003,212,44,40);
  door(c,p,980,262,90,183,12,open,words);
  security(c,p,items,[170,222],[962,266],[262,302]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<4;i++)bloom(c,520+i*66,388,6,[p.primary,'#f7c948','#f6b8c8','#fff4dc'][i]);}
function portRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  E(c,350,857,324,23,'#8fa07c22');R(c,22,114,656,738,'#dcb391',31);R(c,29,117,642,724,'#fffaf1',26,'#d7b391',3);
  wallPaint(c,p,40,139,620,372,wallColor(w,p));bricks(c,40,430,620,506);
  flagstones(c,40,506,620,323,PORT_PETALS);R(c,40,500,620,9,'#d9c2a4',3);
  sign(c,p,125,30,450,100);
  ivyDown(c,46,150,470,1);ivyDown(c,654,150,470,-1);ivyTop(c,40,660,146);
  dryingRod(c,184,326,196,.95);
  chalkboard(c,p,186,272,134,118,16);
  displayWindow(c,p,356,200,174,190,w.time,w.reduced,1);
  streetBoard(c,p,547,194,.86);
  plaque(c,p,610,206,40,40);
  door(c,p,550,300,94,206,15,open,words);
  security(c,p,items,[86,240],[536,212],[443,176]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,380+i*60,396,6,[p.primary,'#f7c948','#f6b8c8'][i]);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,tier=w.c?.ops?.property?.tier||'cozy',out=[];
  out.push([502,()=>at(c,196,500,1,()=>cooler(w,p,112,212,14))]);
  out.push([502,()=>at(c,375,500,1,()=>stand(c,p,206))]);
  out.push([594,()=>at(c,570,594,1,()=>wrapTable(w,p,300,13))]);
  out.push([594,()=>at(c,890,594,1,()=>till(w,p,180,false))]);
  out.push([628,()=>at(c,195,628,1,()=>crate(c,p))]);
  out.push([656,()=>at(c,1028,656,1,()=>ledgerDesk(w,p,12))]);
  out.push([680,()=>at(c,126,678,1,()=>monstera(c))]);
  if(tier!=='cozy')out.push([676,()=>at(c,206,676,1,()=>bench(c,p,112,tier==='garden'))]);
  if(tier==='garden')w.plan().garden.forEach(([x,y],i)=>out.push([y+4,()=>potBloom(c,x,y,1,i%2?'#f7c948':p.primary)]));
  return out;}
function portProps(w,p){const c=w.ctx,tier=w.c?.ops?.property?.tier||'cozy',out=[];
  out.push([598,()=>at(c,98,598,1,()=>cooler(w,p,104,226,16))]);
  out.push([566,()=>at(c,253,566,.85,()=>stand(c,p,206))]);
  out.push([700,()=>at(c,260,700,1,()=>wrapTable(w,p,284,16))]);
  out.push([700,()=>at(c,525,700,1,()=>till(w,p,170,true))]);
  out.push([818,()=>at(c,600,818,1,()=>ledgerDesk(w,p,16))]);
  if(tier!=='cozy')out.push([818,()=>at(c,130,818,1,()=>bench(c,p,112,tier==='garden'))]);
  if(tier==='garden')w.plan().garden.forEach(([x,y],i)=>out.push([y+4,()=>potBloom(c,x,y,.9,i%2?'#f7c948':p.primary)]));
  return out;}

export default {
  id:'flowershop',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
