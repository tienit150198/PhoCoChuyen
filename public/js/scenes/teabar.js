/** Tea bar scene (milk_tea): "Trà Mây & Trân Châu", a trendy bubble tea bar
 * in pink and mint. Back wall: a glowing menu lightbox, a mint tiled
 * backsplash with tea urns and the fructose machine on the back bar, a pink
 * "trà sữa" neon, glass jars of toppings on shelves (`shelf`), the order
 * screen (`evidence`), a window bar with stools where Mướp naps, the street
 * notice board (`board`) and a little shop plaque (`property`).
 * Floor: the long fluted bar counter with the pearl pot and the shaker
 * station (`workbench`, "Quầy pha chế"), the cup sealer and the till at its
 * pickup end (`counter`), the ingredient fridge (`warehouse`, "Kho nguyên
 * liệu"), the tip-jar ledger desk (`finance`) and the door sign (`door`).
 * The barista lane runs behind the bar and opens at its right end.
 * PLAN schema: see scenes/shop.js. Portrait keeps everything important
 * below scene y≈200 (the title card and hint float over the top). */
import {R,E,L,T,P,fit,heart,bloom,plantAt} from './kit.js';
import {room,shopFor,taskOf} from './backroom.js';
import {t as tr} from '../v4/i18n.js';

export const PLAN={
 land:{floor:[130,452,1070,682],lane:505,line:563,home:[470,505],kx:82,ky:45,sway:30,
   blocks:[[136,448,212,530],[232,540,700,584],[815,496,845,508],[880,496,910,508],[945,496,975,508],
     [985,560,1072,582],[970,652,1082,668],[100,570,136,582]],
   bench:[148,652,273,676],garden:[[775,470],[1000,470]],
   customers:[[320,628],[445,634],[570,628],[690,634]],event:[870,570],officer:[800,668],
   staff:{x:300,step:115,y:462},cat:[962,352],counterSpan:[232,700],
   decor:{corner:[138,640],front:[925,676],center:[712,672]},sill:{plant:[828,352],lamp:[868,352],seat:[912,352],rug:[575,662]},
   wall:{poster:[1044,236]},
   badge:{board:[36,-22]},
   spots:{'go:prep':[[150,392],40,[[252,505]]],shelf:[[310,300],90,[[310,505]]],evidence:[[751,285],50,[[751,505]]],workbench:[[398,462],62,[[446,505]]],counter:[[588,462],60,[[634,505]]],
     warehouse:[[174,470],48,[[252,505],[172,562]]],board:[[1044,338],45,[[1044,515]]],finance:[[1028,535],42,[[946,570],[1028,612]]],
     property:[[172,293],30,[[252,505]]],security:[[150,218],30,[[252,505]]],door:[[1026,640],45,[[940,640],[1026,612]]],pet:[[962,335],38,[[995,515]]]}},
 port:{badge:{board:[-36,-6]},floor:[62,512,638,822],lane:572,line:626,home:[330,572],kx:51,ky:57,sway:24,
   blocks:[[52,506,112,612],[124,604,500,650],[556,742,654,760],[470,806,584,820],[64,788,196,814],[629,812,655,824]],
   bench:[226,806,336,822],garden:[[210,832],[352,832]],
   customers:[[200,702],[320,698],[440,702],[270,772]],event:[520,735],officer:[590,690],
   staff:{x:175,step:95,y:526},cat:[578,320],counterSpan:[124,500],
   decor:{corner:[90,700],front:[410,818],center:[335,760]},sill:{plant:[522,320],lamp:[546,320],seat:[626,320],rug:[330,745]},
   wall:{poster:[627,452]},
   spots:{'go:prep':[[80,470],36,[[142,572]]],shelf:[[128,340],80,[[175,572]]],evidence:[[550,386],45,[[550,572]]],workbench:[[214,528],58,[[262,572]]],counter:[[392,526],56,[[436,572]]],
     warehouse:[[82,560],45,[[142,572],[82,672]]],board:[[627,375],40,[[615,572]]],finance:[[605,728],42,[[605,782],[520,760]]],
     property:[[628,180],30,[[600,572]]],security:[[85,180],30,[[175,572]]],door:[[527,802],45,[[527,775],[440,800]]],pet:[[578,305],36,[[578,572]]]}},
};

/* ------------------------------------------------------------ Palette & helpers */
const FONT='"Trebuchet MS", "Segoe UI", sans-serif';
const PINK='#f5b3c7',PINK_L='#fde4ec',PINK_D='#dc8aa6',BERRY='#c4668b',MINT='#bfe7d8',MINT_L='#e6f7f0',MINT_D='#88c6b0',
  CREAM='#fffaf4',MARBLE='#fbf5ef',STEEL='#e4eaee',STEEL_D='#a3b3bb',PEARL='#5a382d',WOOD='#e9c6a6',WOOD_D='#c99b7d',INK='#6f4a58',SHADOW='#8b735322';
const TEA=['#d8b08a','#b9d99a','#f6a9b8','#c9b0e0','#f3d18a'];
/** Draw `fn` with the origin at (x,y) scaled by s. */
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
/** Deterministic 0…1 noise so the terrazzo never shimmers. */
const hash=i=>{const v=Math.sin(i*127.1+311.7)*43758.5453;return v-Math.floor(v);};

/** A bubble tea cup with a sealed film, pearls and a straw; origin = bottom middle. */
function cup(c,x,y,s,tea,{face=false,straw=BERRY,pearls=true,lid=true}={}){at(c,x,y,s,()=>{
  E(c,0,1,13,3,'#8b73531a');P(c,[[-15,-44],[15,-44],[11,0],[-11,0]],tea);
  if(pearls)for(let i=0;i<7;i++)E(c,-7+(i%4)*4.6+(i>3?2.3:0),-4-(i>3?5:0),2.6,2.6,PEARL);
  P(c,[[-15,-44],[-9,-44],[-7,0],[-11,0]],'#ffffff38');
  if(lid){R(c,-17,-48,34,6,'#ffffffd0',3,'#e3cfd5',1);L(c,5,-47,11,-66,straw,4.5);}
  if(face){E(c,-5,-24,1.9,2.4,'#5b4038');E(c,5,-24,1.9,2.4,'#5b4038');E(c,-9,-19,3,1.8,'#f19ab6');E(c,9,-19,3,1.8,'#f19ab6');c.beginPath();c.arc(0,-21,2.4,0,Math.PI);c.strokeStyle='#5b4038';c.lineWidth=1.2;c.stroke();}});}

/** A glass jar of one topping; (x,y) = bottom middle. */
function jar(c,x,y,w,h,kind,i){const top=y-h,fill=h*.72;
  R(c,x-w/2,top,w,h,'#f4fbfbd8',6,'#b9d3d3',1.4);
  c.save();c.beginPath();c.roundRect(x-w/2+2,y-fill,w-4,fill-2,4);c.clip();
  if(kind==='pearl'){R(c,x-w/2,y-fill,w,fill,'#7a4c3b',0);for(let k=0;k<12;k++)E(c,x-w/2+4+(k%4)*(w-8)/3,y-fill+5+Math.floor(k/4)*7,3,3,PEARL);}
  else if(kind==='jelly'){R(c,x-w/2,y-fill,w,fill,'#fff4f6',0);for(let k=0;k<9;k++)R(c,x-w/2+3+(k%3)*(w-6)/3,y-fill+3+Math.floor(k/3)*(fill/3),(w-10)/3,fill/3-3,['#9fd6a8','#f6a3b8','#f7d27a'][(k+i)%3],2);}
  else if(kind==='pudding'){R(c,x-w/2,y-fill,w,fill,'#f6dc8e',0);R(c,x-w/2,y-fill,w,fill*.24,'#c98a45',0);}
  else if(kind==='coco'){R(c,x-w/2,y-fill,w,fill,'#eef6f4',0);for(let k=0;k<9;k++)R(c,x-w/2+3+(k%3)*(w-6)/3,y-fill+3+Math.floor(k/3)*(fill/3),(w-10)/3,fill/3-3,'#ffffff',2,'#d5e7e3',1);}
  else if(kind==='bean'){R(c,x-w/2,y-fill,w,fill,'#b8676a',0);for(let k=0;k<10;k++)E(c,x-w/2+4+(k%4)*(w-8)/3,y-fill+4+Math.floor(k/4)*7,2.6,2,'#8e3f48');}
  else if(kind==='pop'){R(c,x-w/2,y-fill,w,fill,'#fff6ea',0);for(let k=0;k<11;k++)E(c,x-w/2+5+(k%4)*(w-10)/3,y-fill+5+Math.floor(k/4)*7,3.2,3.2,['#f7a1b6','#ffd36e','#9ed7c3','#c6a8ea'][(k+i)%4]);}
  else if(kind==='matcha'){R(c,x-w/2,y-fill,w,fill,'#a9cf87',0);R(c,x-w/2,y-fill,w,4,'#c6e2a8',0);}
  else{R(c,x-w/2,y-fill,w,fill,'#fff1d6',0);R(c,x-w/2,y-fill,w,fill*.35,'#fffaf0',0);}
  c.restore();
  L(c,x-w/2+4,top+6,x-w/2+4,y-6,'#ffffffa0',2);
  R(c,x-w/2-2,top-6,w+4,8,[PINK,MINT,'#f7d99b','#d6c5ef'][i%4],3,'#c9a9b4',1);
  R(c,x-w/2+4,y-h*.5,w-8,9,'#fffaf0e8',2);heart(c,x,y-h*.5+6,.16,PINK_D);}
const JARS=['pearl','jelly','pudding','coco','bean','pop','matcha','cheese'];

/* ------------------------------------------------------------ Wall pieces */
/** Pink striped wallpaper with little dots and a mint wainscot at the bottom. */
function wallpaper(c,p,x,y,w,h,wains){R(c,x,y,w,h,p.wall,20);c.save();c.beginPath();c.roundRect(x,y,w,h,20);c.clip();
  for(let xx=x+10;xx<x+w;xx+=46)R(c,xx,y,20,h,'#f9cfdc38',0);
  for(let r=0,yy=y+30;yy<y+h-wains;r++,yy+=46)for(let xx=x+(r%2?43:20);xx<x+w;xx+=92)E(c,xx,yy,2.4,2.4,'#f3b8c9');
  R(c,x,y+h-wains,w,wains,MINT_L,0);for(let xx=x+12;xx<x+w;xx+=18)L(c,xx,y+h-wains+6,xx,y+h-2,'#ffffffb0',2);
  R(c,x,y+h-wains-5,w,8,'#f3cbd6',3);c.restore();}
/** Scalloped valance along the top of the wall. */
function valance(c,x,w,y,r){c.save();c.beginPath();c.rect(x,y-2,w,r*2+6);c.clip();R(c,x,y-2,w,r,PINK,0);
  for(let i=0,xx=x+r;xx<x+w+r;i++,xx+=r*2){E(c,xx,y+r-2,r,r*.8,i%2?PINK:'#fff3f6');E(c,xx,y+r-6,r*.4,r*.25,'#ffffff55');}c.restore();}
/** Speckled terrazzo floor with a pink skirting line. */
function terrazzo(c,x,y,w,h){R(c,x,y,w,h,'#fbf1e8',15);c.save();c.beginPath();c.roundRect(x,y,w,h,15);c.clip();
  const cols=['#f7cad6','#cfeadf','#f5e2b6','#ecdccf','#e2d5f0'];const n=Math.round(w*h/1700);
  for(let i=0;i<n;i++){const px=x+hash(i)*w,py=y+hash(i+999)*h,r=.9+hash(i+77)*1.5;E(c,px,py,r*1.4,r,cols[i%5]);}
  for(let yy=y+60;yy<y+h;yy+=62)L(c,x,yy,x+w,yy,'#efe0d2',1);c.restore();R(c,x,y-2,w,6,'#f2c4d1',3);}
/** Mint subway tiles. */
function backsplash(c,x,y,w,h){R(c,x,y,w,h,'#dff3ec',6);c.save();c.beginPath();c.rect(x,y,w,h);c.clip();
  for(let r=0,yy=y;yy<y+h;r++,yy+=13){L(c,x,yy,x+w,yy,'#ffffff',1.5);for(let xx=x+(r%2?0:13);xx<x+w;xx+=26)L(c,xx,yy,xx,yy+13,'#ffffff',1.5);}c.restore();}
/** Glowing menu lightbox with three drinks and the toppings line. */
function menuBoard(c,p,x,y,w,h,z,glow){
  const g=c.createRadialGradient(x+w/2,y+h/2,10,x+w/2,y+h/2,w*.75);g.addColorStop(0,'#fff4c8'+(glow?'70':'38'));g.addColorStop(1,'#fff4c800');c.fillStyle=g;c.fillRect(x-60,y-50,w+120,h+100);
  R(c,x-6,y-6,w+12,h+12,'#f29bb8',16,'#d9809f',2);R(c,x,y,w,h,'#fffdf9',11);
  for(let i=0;i<=12;i++){const bx=x-2+i*(w+4)/12;E(c,bx,y-3,2.6,2.6,glow?'#fff6c4':'#fbe7d6');E(c,bx,y+h+3,2.6,2.6,glow?'#fff6c4':'#fbe7d6');}
  const head=z.head+12;R(c,x+8,y+7,w-16,head,PINK_L,8);const title='MENU HÔM NAY';T(c,title,x+w/2,y+7+head/2+1,fit(c,title,w-60,z.head,800),BERRY,800);
  heart(c,x+22,y+7+head/2+4,.22,PINK_D);heart(c,x+w-22,y+7+head/2+4,.22,PINK_D);
  const drinks=[['Trà sữa','25k',TEA[0]],['Trà xanh','28k',TEA[1]],['Vị trái cây','30k',TEA[2]]];const cw=(w-16)/3,ty=y+head+12,th=h-head-12-z.chip-14;
  drinks.forEach(([name,price,col],i)=>{const cx=x+8+cw*i+cw/2;R(c,cx-cw/2+3,ty,cw-6,th,[MINT_L,'#fff4df',PINK_L][i],8);
    cup(c,cx-z.price*.6,ty+z.cupY,z.cup,col,{face:i===0});
    c.font=`800 ${z.price}px ${FONT}`;const pw=c.measureText(price).width+10;R(c,cx+cw/2-pw-7,ty+5,pw,z.price+6,PINK,(z.price+6)/2);T(c,price,cx+cw/2-pw/2-7,ty+8+z.price/2,z.price,'#fffafc',800);
    T(c,name,cx,ty+z.cupY+z.name*.85,fit(c,name,cw-14,z.name,800),INK,800);});
  const chips=['Trân châu','Bọt mây','Thạch dừa'],cy=y+h-z.chip/2-8;
  chips.forEach((s,i)=>{const cx=x+w*(i+.5)/3;T(c,s,cx,cy,fit(c,s,w/3-14,z.chip,700),'#8a6272',700);if(i)E(c,x+w*i/3,cy,2.4,2.4,PINK_D);});}
/** Pink neon "trà sữa" with a cup outline, on a clear acrylic board. */
function neon(c,cx,cy,size,on){const s=tr('trà sữa');c.font=`italic 800 ${size}px ${FONT}`;const tw=c.measureText(s).width,bw=tw+size*2.1,bh=size*1.55;
  R(c,cx-bw/2,cy-bh/2,bw,bh,'#ffffff38',12,'#ffffffb0',1.5);for(const [dx,dy] of [[-1,-1],[1,-1],[-1,1],[1,1]])E(c,cx+dx*(bw/2-8),cy+dy*(bh/2-7),2.4,2.4,'#d9c6cc');
  const tube=on?'#ff8fb8':'#e7b3c4',core=on?'#fff5f9':'#f6d6e0',tx=cx+size*.45;
  c.save();if(on){c.shadowColor='#ff7fb0';c.shadowBlur=size*.55;}c.textAlign='center';c.textBaseline='middle';c.lineJoin='round';
  c.strokeStyle=tube;c.lineWidth=Math.max(3,size*.16);c.strokeText(s,tx,cy);c.fillStyle=core;c.fillText(s,tx,cy);
  // cup outline with a straw and three pearls
  const ux=cx-tw/2-size*.25,k=size/34;c.strokeStyle=on?'#8fe6cc':'#b9ddd0';c.lineWidth=3*k;c.beginPath();c.moveTo(ux-11*k,cy-13*k);c.lineTo(ux-8*k,cy+14*k);c.lineTo(ux+8*k,cy+14*k);c.lineTo(ux+11*k,cy-13*k);c.closePath();c.stroke();
  c.beginPath();c.moveTo(ux+3*k,cy-13*k);c.lineTo(ux+8*k,cy-24*k);c.stroke();for(let i=0;i<3;i++){c.beginPath();c.arc(ux-5*k+i*5*k,cy+8*k,1.6*k,0,Math.PI*2);c.stroke();}
  c.restore();}
/** Wall shelves of topping jars: the `shelf` hotspot. */
function toppingShelf(c,p,label,x,y,w,h,ts,rows){const head=ts+14;
  R(c,x-4,y+head-4,w+8,h-head+8,WOOD_D,10);R(c,x+2,y+head+2,w-4,h-head-4,'#fff6ee',7);
  R(c,x+8,y,w-16,head,PINK_L,10,'#e9b3c4',1.5);T(c,label,x+w/2,y+head/2+1,fit(c,label,w-28,ts,800),BERRY,800);
  const gap=(h-head-6)/rows,n=Math.max(3,Math.floor((w-12)/36)),jw=Math.min(28,(w-20)/n-6);
  for(let r=0;r<rows;r++){const base=y+head+gap*(r+1)-4;
    for(let i=0;i<n;i++){const jx=x+10+jw/2+i*(w-20-jw)/(n-1);jar(c,jx,base,jw,gap-16,JARS[(r*n+i+r)%JARS.length],r+i);}
    R(c,x,base,w,7,WOOD,2,WOOD_D,1);}}
/** Back bar: three tea urns, the fructose machine and a blender on a cabinet. */
function backBar(c,p,x,top,w,bottom,s){R(c,x,top+10,w,bottom-top-10,PINK,4);for(let i=1;i<4;i++)L(c,x+w*i/4,top+16,x+w*i/4,bottom-3,'#e59bb3',2);
  for(let i=0;i<4;i++)R(c,x+w*(i+.5)/4-8,top+22,16,4,'#fff3f6',2);R(c,x-4,top,w+8,12,MARBLE,4,'#dcc8bb',1.5);
  const bands=['#c9774f','#8dbf78','#d9a24c'];
  for(let i=0;i<3;i++)at(c,x+w*(.1+i*.14),top,s,()=>{R(c,-13,-52,26,48,STEEL,7,STEEL_D,1.5);R(c,-13,-40,26,11,bands[i],2);L(c,-9,-48,-9,-12,'#ffffffb0',2);
    E(c,0,-53,9,3.5,'#cfd9de');E(c,0,-57,3.5,3,STEEL_D);R(c,-4,-12,8,6,STEEL_D,2);L(c,0,-6,0,-2,'#8a969c',2);R(c,-6,-4,12,4,'#cfd9de',1);});
  // fructose dispenser with a little display
  at(c,x+w*.56,top,s,()=>{R(c,-20,-46,40,44,'#f4f7f8',7,STEEL_D,1.5);R(c,-14,-40,28,11,'#57707a',3);T(c,'Đường',0,-34.5,7,'#bff5dc',700);
    for(let i=0;i<3;i++){E(c,-10+i*10,-22,3,3,[PINK_D,MINT_D,'#f3c969'][i]);}R(c,-8,-10,16,6,STEEL_D,2);});
  // blender
  at(c,x+w*.74,top,s,()=>{R(c,-14,-16,28,14,'#6f5a66',5);E(c,0,-9,3,3,PINK);P(c,[[-12,-16],[12,-16],[15,-52],[-15,-52]],'#eaf6f7c8');R(c,-16,-58,32,7,'#6f5a66',3);R(c,-10,-40,20,22,TEA[2],3);});
  // stacked cups
  at(c,x+w*.9,top,s,()=>{for(let i=0;i<5;i++)P(c,[[-11,-4-i*7],[11,-4-i*7],[13,-12-i*7],[-13,-12-i*7]],i%2?'#f7fbfc':'#eef6f8');R(c,-13,-48,26,5,'#dfeef1',2);heart(c,0,-20,.2,PINK_D);});}
/** Window with a street view, and the window bar ledge in front of it. */
function windowBar(c,p,x,y,w,h,ledge,apronTo,world){
  R(c,x-8,y-8,w+16,h+12,'#f0c3d0',18);const pane=(w-10)/2;
  for(let i=0;i<2;i++){const px=x+i*(pane+10);c.save();c.beginPath();c.roundRect(px,y,pane,h,[pane/2,pane/2,6,6]);c.clip();
    R(c,px,y,pane,h,'#cfeaf0',0);E(c,px+pane*.7,y+h*.3,12,12,i?'#fff2c4':'#cfeaf000');
    R(c,px,y+h*.72,pane,h*.28,'#f3e1cf',0);E(c,px+pane*(i?.25:.75),y+h*.7,pane*.3,h*.24,'#a9d3b3');L(c,px+pane*(i?.25:.75),y+h*.72,px+pane*(i?.25:.75),y+h*.9,'#b08a6c',4);
    R(c,px+pane*(i?.55:.05),y+h*.62,pane*.4,h*.1,i?'#f6c1a8':'#bcd7ef',2);c.restore();
    c.beginPath();c.roundRect(px,y,pane,h,[pane/2,pane/2,6,6]);c.strokeStyle='#fffaf4';c.lineWidth=5;c.stroke();}
  // A cloud drifting past each pane (inside the frame's white edge), and fairy lights along the arch over them:
  // drawn on every frame over the cached room (BobaWorld.ambient), so the rest of the room is painted once.
  world.ambient(c=>{for(let i=0;i<2;i++){const px=x+i*(pane+10);c.save();c.beginPath();c.roundRect(px+2.5,y+2.5,pane-5,h-5,[pane/2-2.5,pane/2-2.5,3.5,3.5]);c.clip();
      const drift=world.reduced?0:(world.time*5+i*40)%(pane+50);E(c,px+drift-25,y+h*.35,16,6,'#ffffffc8');c.restore();}
    for(let i=0;i<7;i++){const a=Math.PI+i*Math.PI/6;E(c,x+w/2+Math.cos(a)*(w/2+2),y+w/2*.1+h*.42+Math.sin(a)*(h*.5),2.6,2.6,'#fff1b8');}});
  R(c,x-14,ledge,w+28,11,MARBLE,4,'#dcc8bb',1.5);R(c,x-10,ledge+11,w+20,apronTo-ledge-11,MINT,0);
  for(let xx=x-2;xx<x+w+10;xx+=12)L(c,xx,ledge+16,xx,apronTo-2,'#ffffff90',2.5);R(c,x-10,ledge+11,w+20,4,MINT_D,0);}
/** Hanging order screen: the `evidence` hotspot. */
function orderScreen(c,p,x,y,w,h,z,orders,top){L(c,x+12,top,x+12,y,'#b9a2aa',1.5);L(c,x+w-12,top,x+w-12,y,'#b9a2aa',1.5);
  R(c,x,y,w,h,'#6b5561',9);R(c,x+5,y+5,w-10,h-10,'#fff7fa',5);R(c,x+5,y+5,w-10,z.head+8,PINK,5);
  T(c,'Đơn',x+w/2,y+5+(z.head+8)/2,fit(c,'Đơn',w-24,z.head,800),'#fffafc',800);
  const rows=3,rh=(h-z.head-22)/rows;
  for(let i=0;i<rows;i++){const ry=y+z.head+17+i*rh,live=i<orders;R(c,x+10,ry,w-20,rh-5,live?(i===0?'#fff0c9':MINT_L):'#f5eef0',4);
    T(c,'#'+(12+i),x+14,ry+(rh-5)/2,z.row,live?INK:'#c6b4ba',800,'left');cup(c,x+w-40,ry+rh-8,z.cup,live?TEA[i]:'#e8dfe2',{pearls:live,straw:live?BERRY:'#d8ccd0'});
    E(c,x+w-18,ry+(rh-5)/2,4,4,live?(i===0?'#f3b54d':'#7cc49a'):'#dccfd4');}}
/** Framed little shop with an awning: the `property` hotspot. */
function plaque(c,p,x,y,w,h){R(c,x,y,w,h,WOOD_D,8);R(c,x+4,y+4,w-8,h-8,CREAM,6);const cx=x+w/2,b=y+h-9,s=w/44;
  R(c,cx-13*s,b-17*s,26*s,17*s,MINT_L,2,MINT_D,1);for(let i=0;i<4;i++)R(c,cx-14*s+i*7*s,b-22*s,7*s,7*s,i%2?'#fff':PINK,1);R(c,cx-3*s,b-10*s,6*s,10*s,BERRY,1);}
/** Security gear: camera, door bell, night lamp (or a tiny clover plate). */
function security(c,items,cam,bell,lamp){
  if(items.includes('camera')){const [x,y]=cam;L(c,x,y+18,x+14,y+10,'#b79b85',4);R(c,x+6,y,39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,x+40,y+10,8,9,'#7a8992');E(c,x+41,y+10,4,5,'#b4d9df');E(c,x+12,y+5,2,2,'#90bd8b');}
  else{const [x,y]=cam;R(c,x+4,y,44,24,CREAM,8,'#e2b8c6',1);T(c,'♧',x+26,y+12,15,BERRY);}
  if(items.includes('bell')){const [x,y]=bell;L(c,x,y,x,y+14,'#ac8f73',2);P(c,[[x-10,y+31],[x+10,y+31],[x+7,y+17],[x-7,y+17]],'#f0ce85');E(c,x,y+33,4,3,'#d4ad64');}
  if(items.includes('light')){const [x,y]=lamp;const g=c.createRadialGradient(x,y+20,0,x,y+20,70);g.addColorStop(0,'#ffe1a45a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(x-70,y-50,140,140);R(c,x-12,y+8,24,32,'#fff0b8',8,'#b69b79',2);L(c,x,y-2,x,y+8,'#b69b79',3);}}
/** Fairy-light string with little paper cups hanging off it. */
function cupGarland(c,x0,x1,y,sag,n){c.strokeStyle='#e0bccb';c.lineWidth=2;c.beginPath();c.moveTo(x0,y);c.quadraticCurveTo((x0+x1)/2,y+sag*2,x1,y);c.stroke();
  for(let i=1;i<n;i++){const t=i/n,xx=x0+(x1-x0)*t,yy=y+sag*4*t*(1-t);L(c,xx,yy,xx,yy+6,'#d7b8c4',1);
    if(i%2)E(c,xx,yy+11,4,6,'#fff0b0');else{P(c,[[xx-6,yy+6],[xx+6,yy+6],[xx+4,yy+19],[xx-4,yy+19]],[PINK,MINT,'#f7d99b'][i%3]);E(c,xx-2,yy+16,1.3,1.3,PEARL);E(c,xx+2,yy+16,1.3,1.3,PEARL);}}}

/* ------------------------------------------------------------ Floor pieces (local units, origin = middle of the feet line) */
/** Tall two-door ingredient fridge with milk, jars and a sack of pearls on top. */
function fridge(w,p,ts,tall){const c=w.ctx,words=w.words(),items=w.c?.ops?.security?.items||[],H=tall?170:100;
  E(c,0,2,42,7,SHADOW);R(c,-38,-H,76,H-2,MINT_D,10);R(c,-34,-H+4,68,H-10,MINT,7);
  const glass=tall?H*.52:H*.46;R(c,-29,-H+10,58,glass,'#eefaf9',5,'#9fd0c1',1.5);
  const g1=-H+10+glass*.48,g2=-H+8+glass;L(c,-28,g1,28,g1,'#9fd0c1',2);L(c,-28,g2,28,g2,'#9fd0c1',2);
  for(let i=0;i<4;i++){R(c,-24+i*13,g1-20,9,19,'#ffffff',3,'#d5e3e8',1);R(c,-23+i*13,g1-24,7,5,['#8ab4e8','#f4a9bd','#8ab4e8','#9ed7b5'][i],2);}
  for(let i=0;i<3;i++){R(c,-24+i*17,g2-17,14,16,['#7a4c3b','#f6dc8e','#f6a3b8'][i],3,'#c9b0a0',1);}
  L(c,24,-H+14,24,-H+14+glass-8,'#ffffffb0',3);
  R(c,-29,-H+16+glass,58,ts+12,CREAM,6,MINT_D,1.2);T(c,words.store,0,-H+16+glass+(ts+12)/2+1,fit(c,words.store,50,ts,800),'#4f7d6d',800);
  L(c,29,-H+22+glass+ts+14,29,-18,'#ffffffc0',3);R(c,-34,-10,10,9,MINT_D,2);R(c,24,-10,10,9,MINT_D,2);
  // sack of tapioca pearls and a box on top
  P(c,[[-32,-H],[-2,-H],[-5,-H-30],[-29,-H-30]],'#ecd9b8');R(c,-31,-H-34,24,6,'#d9c29c',2);E(c,-17,-H-14,6,6,PEARL);E(c,-13,-H-18,2,2,'#8a6a5c');
  R(c,2,-H-22,30,22,'#f7c9d6',3,'#dc8aa6',1.2);L(c,2,-H-14,32,-H-14,'#dc8aa6',1.2);heart(c,17,-H-5,.2,'#fff5f8');
  if(items.includes('lock')){R(c,8,-34,16,18,'#d8c596',5,'#a09675',1);c.beginPath();c.arc(16,-34,5,Math.PI,0);c.strokeStyle='#a09675';c.lineWidth=3;c.stroke();}}
/** Pot of tapioca pearls on a hob, steaming. */
function pearlPot(c,t,reduced){R(c,-28,-10,56,10,'#e3e9ec',3,STEEL_D,1.2);E(c,18,-5,3,3,'#f08a8a');
  R(c,-23,-46,46,36,STEEL,7,STEEL_D,1.5);R(c,-29,-40,7,6,STEEL_D,2);R(c,22,-40,7,6,STEEL_D,2);L(c,-17,-42,-17,-14,'#ffffffa0',2);
  E(c,0,-46,23,6,'#4a2f26');for(let i=0;i<9;i++)E(c,-15+i*3.8,-46+Math.sin(i*1.7)*2.2,2.6,2.2,'#7b5040');
  c.strokeStyle='#ffffffb0';c.lineWidth=2.4;c.lineCap='round';for(let k=0;k<3;k++){const ph=reduced?k:t*1.6+k*2.1,o=(ph%3)/3;c.globalAlpha=reduced?.6:1-o;c.beginPath();c.moveTo(-10+k*10,-52-o*18);c.quadraticCurveTo(-4+k*10,-60-o*18,-10+k*10,-68-o*18);c.stroke();}c.globalAlpha=1;}
/** Tray of topping tubs set into the counter. */
function tubs(c){R(c,-36,-8,72,10,CREAM,4,'#dcc6b4',1);const cols=['#7a4c3b','#f6dc8e','#9fd6a8','#f6a3b8'];for(let i=0;i<4;i++){E(c,-25+i*17,-7,7.5,3.5,cols[i]);E(c,-27+i*17,-8,2,1,'#ffffff90');}L(c,20,-10,34,-26,STEEL_D,2);E(c,35,-27,4,2.5,STEEL);}
/** Shaker station: a mint shaking machine holding two shaker cups. */
function shaker(c,t,on,reduced,worn){const j=on&&!reduced?Math.sin(t*24)*1.2:0;
  R(c,-30,-8,60,8,'#e5ecef',3,STEEL_D,1);R(c,-27,-66,54,58,MINT,10,MINT_D,1.5);R(c,-21,-60,42,12,'#fff9fb',4);E(c,-12,-54,3,3,on?'#ff9ab8':'#e5cfd6');E(c,0,-54,3,3,'#f3d06d');E(c,12,-54,3,3,MINT_D);
  for(const dx of [-11,11]){R(c,dx-8+j,-45,16,30,STEEL,4,STEEL_D,1.2);R(c,dx-9+j,-49,18,6,'#cfd9de',3);L(c,dx-4+j,-42,dx-4+j,-19,'#ffffffb0',2);R(c,dx-9+j,-30,18,4,MINT_D,1);}
  if(on&&!reduced)for(const dx of [-34,34]){L(c,dx,-44,dx+(dx<0?-5:5),-44,'#dcb8c6',1.5);L(c,dx,-36,dx+(dx<0?-7:7),-36,'#dcb8c6',1.5);}
  if(worn){L(c,-18,-80,-12,-66,'#b48d64',1.5);L(c,18,-80,12,-66,'#b48d64',1.5);R(c,-32,-94,64,16,'#f7d995',5,'#d3a35c',1.2);T(c,'CẦN KIỂM',0,-86,9,'#94643d',800);}}
/** Clear cup tower and a pot of straws. */
function cupsAndStraws(c){for(let i=0;i<5;i++)P(c,[[-24,-3-i*7],[-4,-3-i*7],[-2,-11-i*7],[-26,-11-i*7]],i%2?'#f8fcfd':'#eaf5f7');R(c,-26,-46,24,4,'#dcecf0',2);
  R(c,4,-26,18,24,PINK,5,PINK_D,1);for(let i=0;i<4;i++)L(c,8+i*3.5,-26,6+i*5,-44+i%2*4,[BERRY,MINT_D,'#f3c969','#b894d6'][i],2.4);heart(c,13,-12,.2,'#fff5f8');}
/** Cup sealing machine with a freshly sealed cup under its head. */
function sealer(c,p){R(c,-26,-8,52,8,'#efe2e8',3,'#c9a9b4',1);R(c,10,-72,18,64,PINK,6,PINK_D,1.5);
  E(c,-24,-54,9,9,'#fffafc');c.beginPath();c.arc(-24,-54,9,0,Math.PI*2);c.strokeStyle='#e3b9c7';c.lineWidth=2;c.stroke();E(c,-24,-54,3,3,'#e3b9c7');
  R(c,-22,-74,50,18,PINK,8,PINK_D,1.5);R(c,-16,-70,20,8,'#fff5f8',3);T(c,'♡',-6,-66,8,BERRY);L(c,24,-70,38,-88,'#b9a2aa',4);E(c,39,-90,6,6,BERRY);
  R(c,-18,-12,32,5,'#dcc6cf',2);cup(c,-2,-12,.62,TEA[0],{lid:false});R(c,-12.5,-43,21,4,'#ffffffe8',2,'#f0c2d0',1);heart(c,-2,-40,.14,PINK_D);}
/** Till tablet and a pickup bell with a little "Đơn" stand. */
function till(c,p){L(c,0,-2,0,-16,'#8b7680',4);R(c,-12,-4,24,4,'#8b7680',2);R(c,-20,-44,40,30,'#6b5561',6);R(c,-16,-40,32,22,'#fdf2f6',3);heart(c,-6,-29,.2,PINK_D);L(c,2,-33,12,-33,MINT_D,2);L(c,2,-27,10,-27,'#e3c9d2',2);
  E(c,30,-3,11,3,'#d9b35d');c.beginPath();c.arc(30,-5,8,Math.PI,0);c.fillStyle='#f1d27f';c.fill();E(c,30,-14,2,2,'#d9b35d');}
/** The long fluted bar counter (feet line at `base`, top surface at `top`). */
function barCounter(w,p,x0,x1,top,base,s,xs){const c=w.ctx,t=w.time,on=!!w.c?.open,reduced=w.reduced,worn=(w.c?.ops?.equipment?.condition??100)<100,check=w.c?.upgrades?.includes('workbench');
  const slab=18*s;E(c,(x0+x1)/2,base+2,(x1-x0)*.55,9,SHADOW);
  R(c,x0+6,top+slab-4,x1-x0-12,base-top-slab+2,PINK,6,PINK_D,1.5);
  for(let x=x0+18;x<x1-10;x+=14*s)L(c,x,top+slab+4,x,base-12*s,'#ffffff66',4*s);
  R(c,x0+6,base-12*s,x1-x0-12,12*s,MINT,4,MINT_D,1);
  // round badge in the middle of the front with the shop's cup mascot
  const bx=(x0+x1)/2,by=top+slab+(base-top-slab)/2-3;E(c,bx,by,30*s,24*s,CREAM);c.beginPath();c.ellipse(bx,by,30*s,24*s,0,0,Math.PI*2);c.strokeStyle=PINK_D;c.lineWidth=2;c.stroke();cup(c,bx,by+17*s,.62*s,TEA[0],{face:true});
  R(c,x0,top,x1-x0,slab,MARBLE,6,'#dcc8bb',1.5);L(c,x0+8,top+4,x1-8,top+4,'#ffffff',2);
  for(let i=0;i<5;i++)L(c,x0+30+i*(x1-x0)/5,top+slab-5,x0+48+i*(x1-x0)/5,top+slab-8,'#ecdcd4',1.2);
  const on_=(x,fn)=>at(c,x,top+4,s,fn);
  on_(xs.pot,()=>pearlPot(c,t,reduced));on_(xs.tubs,()=>tubs(c));
  on_(xs.shaker,()=>shaker(c,t,on,reduced,worn));if(xs.cups)on_(xs.cups,()=>cupsAndStraws(c));
  on_(xs.sealer,()=>sealer(c,p));on_(xs.till,()=>till(c,p));
  if(check)on_(xs.shaker+44,()=>{R(c,-12,-30,24,30,CREAM,4,'#c7ad90',1.5);L(c,-7,-20,-3,-16,'#6fae7c',2);L(c,-3,-16,5,-24,'#6fae7c',2);L(c,-7,-8,7,-8,'#c4b3a0',1.5);});}
/** Bar stool: round cushion, chrome pole and foot ring. */
function stool(c,x,y,s,col){at(c,x,y,s,()=>{E(c,0,0,16,4,SHADOW);E(c,0,-2,13,4,'#cfd9de');L(c,0,-4,0,-46,STEEL_D,4);E(c,0,-22,10,3,'#ffffff00');c.beginPath();c.ellipse(0,-22,11,3,0,0,Math.PI*2);c.strokeStyle=STEEL_D;c.lineWidth=2;c.stroke();
  R(c,-17,-54,34,10,col,5);E(c,0,-54,17,5,col);E(c,-4,-56,8,2,'#ffffff70');});}
/** Round standing table with two stools and two drinks (portrait front corner). */
function highTable(c,p){stool(c,-44,0,.95,PINK);stool(c,44,0,.95,MINT);E(c,0,-2,24,5,SHADOW);E(c,0,-3,16,4,'#cfd9de');L(c,0,-4,0,-66,STEEL_D,5);
  E(c,0,-68,46,11,PINK_D);E(c,0,-71,46,11,CREAM);c.beginPath();c.ellipse(0,-71,46,11,0,0,Math.PI*2);c.strokeStyle='#e3b9c7';c.lineWidth=2;c.stroke();
  cup(c,-14,-70,.62,TEA[1],{});cup(c,14,-68,.62,TEA[3],{face:true,straw:MINT_D});}
/** Loveseat for the bigger lease tiers. */
function loveseat(c,p,s,garden){at(c,0,0,s,()=>{E(c,0,2,60,6,SHADOW);for(const x of [-50,44])R(c,x,-14,6,14,WOOD_D,2);
  R(c,-56,-62,112,36,MINT,16,MINT_D,1.5);R(c,-60,-34,120,22,MINT,9,MINT_D,1.5);R(c,-66,-48,16,36,MINT_D,8);R(c,50,-48,16,36,MINT_D,8);
  E(c,-22,-44,16,12,PINK_L);E(c,22,-44,16,12,'#fff3d6');heart(c,-22,-42,.25,PINK_D);T(c,'ngồi nghỉ nhé',0,-22,11,'#4f7d6d',700);
  if(garden)bloom(c,56,-60,11,PINK);});}
/** Small ledger desk with the tip jar: the `finance` hotspot. */
function ledgerDesk(w,p,ts){const c=w.ctx,words=w.words();E(c,0,2,48,6,SHADOW);R(c,-42,-40,84,38,PINK,9,PINK_D,1.5);R(c,-36,-34,72,24,'#fff3f6',5);
  T(c,words.ledger,0,-22,fit(c,words.ledger,66,ts,800),INK,800);R(c,-46,-50,92,12,MARBLE,5,'#dcc8bb',1.5);
  P(c,[[-30,-52],[-6,-49],[-6,-61],[-28,-64]],'#fff8e7');P(c,[[18,-52],[-6,-49],[-6,-61],[16,-64]],'#fffdf5');L(c,-6,-49,-6,-61,'#c7ad90',1.5);L(c,-24,-58,-11,-56,PINK_D,1.5);
  R(c,22,-72,18,20,'#eef8f8c8',5,'#a9c9d0',1);E(c,31,-56,5,2,'#e6c36b');E(c,29,-60,5,2,'#f3d590');heart(c,31,-64,.18,PINK_D);}
/** Open/closed sign on two little posts. */
function doorSign(c,p,open,words,x,y,wd,ht,ts){const s=open?words.open_sign:words.closed_sign;L(c,x+14,y+ht-4,x+8,y+ht+14,WOOD_D,4);L(c,x+wd-14,y+ht-4,x+wd-8,y+ht+14,WOOD_D,4);
  R(c,x,y,wd,ht,CREAM,14,PINK_D,2);T(c,s,x+wd/2,y+ht/2+1,fit(c,s,wd-20,ts,800),BERRY,800);E(c,x+12,y+ht/2,3.5,3.5,open?'#7cc49a':'#e0a0b4');}

/* ------------------------------------------------------------ Signs */
/** The shop sign over the room (landscape only; portrait shows the title card). */
function sign(c,p,x,y,w,h){R(c,x-5,y+7,w+10,h,PINK_D,30);R(c,x,y,w,h,CREAM,28,'#f1bfd0',3);R(c,x+10,y+10,w-20,h-20,'#fffdf9',22,PINK_L,2);
  cup(c,x+48,y+h-18,.95,TEA[0],{face:true});const cx=x+w/2+22;T(c,p.title,cx,y+42,fit(c,p.title,w-140,30,800),BERRY,800);T(c,p.sub,cx,y+h-27,fit(c,p.sub,w-120,12),INK);heart(c,x+w-34,y+50,.36,PINK_D);
  L(c,x+60,y,x+80,y-30,'#d9b4c1',2);L(c,x+w-60,y,x+w-80,y-30,'#d9b4c1',2);}

/* ------------------------------------------------------------ Rooms */
function activeOrders(w){return (w.c?.tasks||[]).filter(t=>!['completed','referred','cancelled'].includes(t.status)).length;}
function landRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open;
  E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#eeb4c6',35);R(c,96,168,1008,533,CREAM,30,'#e6a9bd',3);
  wallpaper(c,p,108,179,984,274,46);terrazzo(c,108,447,984,242);valance(c,108,984,179,11);
  sign(c,p,370,62,460,100);
  plaque(c,p,150,270,44,46);
  toppingShelf(c,p,p.shelves?.[1]||'Vị trái cây & topping',222,214,176,212,13,3);
  backsplash(c,404,322,300,130);
  menuBoard(c,p,412,190,284,120,{head:15,name:12,price:10,chip:11,cup:.56,cupY:36},open);
  backBar(c,p,404,398,300,452,1);
  orderScreen(c,p,712,236,80,98,{head:12,row:11,cup:.36},activeOrders(w),179);
  neon(c,897,222,30,open);
  windowBar(c,p,812,258,172,86,352,452,w);
  cupGarland(c,184,404,198,6,7);
  // right wall: street notice board, a cup-shaped cutout and the lamp
  R(c,1012,300,65,77,'#d7a9b8',9);R(c,1018,306,53,65,CREAM,6);T(c,'CHUYỆN',1044,324,10,BERRY);T(c,'PHỐ',1044,340,14,BERRY);heart(c,1044,359,.35,PINK_D);
  cup(c,1044,440,.9,TEA[3],{face:true,straw:MINT_D});
  security(c,items,[124,198],[1080,196],[1078,392]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,1016+i*28,285,7,[PINK,'#f3d98a',MINT_D][i]);}
function portRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open;
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#eeb4c6',31);R(c,29,117,642,724,CREAM,26,'#e6a9bd',3);
  wallpaper(c,p,40,139,620,372,40);terrazzo(c,40,508,620,321);valance(c,40,620,139,12);
  cupGarland(c,110,212,168,4,5);
  toppingShelf(c,p,p.shelves?.[1]||'Vị trái cây & topping',50,222,156,226,16,3);
  backsplash(c,214,306,272,205);
  menuBoard(c,p,220,170,260,130,{head:17,name:15,price:13,chip:14,cup:.56,cupY:40},open);
  neon(c,350,334,30,open);
  backBar(c,p,214,446,272,511,.9);
  windowBar(c,p,512,212,132,92,310,346,w);
  orderScreen(c,p,504,360,94,96,{head:16,row:15,cup:.4},activeOrders(w),346);
  R(c,601,344,52,62,'#d7a9b8',8);R(c,606,349,42,52,CREAM,5);T(c,'CHUYỆN',627,364,9,BERRY);T(c,'PHỐ',627,378,12,BERRY);heart(c,627,393,.28,PINK_D);
  plaque(c,p,608,158,40,44);
  security(c,items,[56,166],[495,174],[494,238]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,520+i*24,300,6,[PINK,'#f3d98a',MINT_D][i]);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,pl=PLAN.land,tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,words=w.words(),out=[];
  out.push([530,()=>at(c,174,530,1,()=>fridge(w,p,12,true))]);
  out.push([584,()=>barCounter(w,p,232,700,478,584,1,{pot:272,tubs:334,shaker:398,cups:522,sealer:588,till:672})]);
  [[830,PINK],[895,MINT],[960,'#f7d99b']].forEach(([x,col])=>out.push([508,()=>stool(c,x,508,1,col)]));
  out.push([582,()=>at(c,1028,582,1,()=>ledgerDesk(w,p,11))]);
  out.push([668,()=>doorSign(c,p,open,words,972,624,110,34,12)]);
  out.push([582,()=>plantAt(c,118,578,1.15)]);
  if(tier!=='cozy')out.push([676,()=>at(c,211,676,1,()=>loveseat(c,p,1,tier==='garden'))]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+4,()=>plantAt(c,x,y,.6)]);
  return out;}
function portProps(w,p){const c=w.ctx,pl=PLAN.port,tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,words=w.words(),out=[];
  out.push([612,()=>at(c,82,612,.8,()=>fridge(w,p,18,false))]);
  out.push([650,()=>barCounter(w,p,124,500,548,650,.92,{pot:151,tubs:318,shaker:214,sealer:392,till:474})]);
  out.push([814,()=>at(c,130,812,1,()=>highTable(c,p))]);
  out.push([760,()=>at(c,605,760,1.05,()=>ledgerDesk(w,p,16))]);
  out.push([820,()=>doorSign(c,p,open,words,470,768,128,38,17)]);
  out.push([826,()=>plantAt(c,642,822,.72)]);
  if(tier!=='cozy')out.push([822,()=>at(c,281,822,.9,()=>loveseat(c,p,1,tier==='garden'))]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+4,()=>plantAt(c,x,y,.5)]);
  return out;}

/* ------------------------------------------------------------ the back kitchen (scenes/backroom.js) */
/** Bếp sau: the pearl pots on the stove, the topping shelf, the milk fridge, the recipe table (the task). */
const PREP=room({id:'prep',name:'Bếp sau',icon:'🍳',back:'bar',sign:'BẾP TRÂN CHÂU',
  theme:{wall:'#fde4ec',wallLow:'#e6f7f0',floor:'#f3ece6',floor2:'#ebe1d8',tile:70,rim:'#dc8aa6',trim:'#88c6b0',ink:'#c4668b',door:'#88c6b0'},
  win:{u0:.13,u1:.29,frame:'#e6f7f0'},clock:[.5,.27],calendar:[.34,.32],
  items:[
    {k:'shelf',u:.42,v:.1,w:.12,h:230,fill:['🍯','🫙','🥥','🍓','🍵','🧋'],spot:'warehouse',label:'Kệ nguyên liệu'},
    {k:'counter',u:.66,v:.1,w:.3,h:84,pots:[.18,.5,.82],brew:['#5a382d','#a8683c','#efe0c8'],potCol:['#c0c7cd','#e4eaee','#c0c7cd'],spot:'look:pots',label:'Nồi trân châu'},
    {k:'fridge',u:.89,v:.1,w:.13,h:220,tag:'SỮA TƯƠI',top:'#88c6b0',fill:['🥛','🍓','🥭','🧊','🍑']},
    {k:'table',u:.5,v:.56,w:.26,h:58,fill:['🧋','🫖','🥄'],cloth:'#fde4ec',spot:'workbench',label:'Bàn thử công thức'},
    {k:'sacks',u:.2,v:.62,w:.14,h:62,fill:['ĐƯỜNG','BỘT','TRÀ']},
  ],
  looks:{pots:()=>'Trân châu đường đen đang sôi lăn tăn. Khuấy đều tay kẻo dính đáy.'},
  chat:['Trân châu mẻ mới chín rồi nha!','Ai lấy giùm thùng sữa tươi với…','Đơn online nổ quá trời!'],
});

export default {
  id:'teabar',
  areas:[{id:'bar',name:'Quầy bar',icon:'🧋',main:true},PREP],
  areaFor:shopFor('bar'),
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
