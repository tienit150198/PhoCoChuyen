/** Kitchen scene (kind `kitchen`, restaurant): Quán Mì Cay Mây, a small
 * Korean-style spicy noodle shop on a warm evening.
 * Back wall, left to right: the walk-in cold store (`warehouse`), the spice &
 * topping shelves (`shelf`), the open kitchen line "Bếp mì" (`workbench`):
 * a stove with four big steaming broth pots (kim chi, tomyum, tương đen,
 * sữa phô mai) in front of teal tiles, under the hanging menu board with the
 * seven spice levels; the noodle boiler with its baskets under the order rail
 * (`evidence`); then the dining wall: a drinks fridge where Mướp naps, an
 * evening window, the street board, the shop plaque (`property`) and the door.
 * Red paper lanterns hang along the ceiling.
 * Floor: the pass (`counter`, bowls going out and the till) with the cook's
 * lane behind it, wooden tables with stools where guests sit, and the cash
 * desk with the shop ledger (`finance`). PLAN schema: see scenes/shop.js.
 * Phones: nothing important above y≈150 and no big sign (the title card
 * names the place); landscape keeps a sign above the wall. */
import {R,E,L,T,P,fit,heart,bloom,plantAt,streetBoard} from './kit.js';
import {room,shopFor,taskOf} from './backroom.js';
import {t as tr} from '../v4/i18n.js';

/* ------------------------------------------------------------ Floor plan */
// Tables: [x0,x1,base] of the table top span and its feet line; the block is
// the legs and stools. Guests stand just behind a table, so it hides their
// legs and they read as seated.
const LAND_TABLES=[[262,398,662],[532,668,662],[822,1008,594]];
const PORT_TABLES=[[84,262,736],[288,466,736]];
const tableBlock=([x0,x1,base])=>[x0+4,base-22,x1-4,base];

export const PLAN={
 land:{floor:[130,452,1070,682],lane:505,line:505,home:[600,505],kx:82,ky:45,sway:26,
   blocks:[[116,446,210,462],[336,446,748,462],[758,446,828,462],[232,544,742,582],[986,636,1068,660],...LAND_TABLES.map(tableBlock)],
   bench:[140,652,262,676],garden:[[146,686],[1058,690]],
   customers:[[330,630],[600,630],[870,562],[960,562]],event:[465,640],officer:[790,642],
   staff:{x:390,step:112,y:476},cat:[793,290],counterSpan:[0,0],
   decor:{corner:[1052,600],front:[715,676],center:[470,678]},sill:{plant:[858,379],lamp:[893,379],seat:[922,379],rug:[465,662]},
   badge:{workbench:[0,-30],board:[0,-46]},wall:{poster:[702,222]},
   spots:{'go:prep':[[163,262],40,[[163,505]]],shelf:[[273,318],58,[[273,505]]],evidence:[[702,294],40,[[702,505]]],workbench:[[495,330],72,[[495,505]]],counter:[[712,462],48,[[712,505]]],
     warehouse:[[163,352],50,[[163,505]]],board:[[976,334],40,[[976,505]]],finance:[[1027,604],42,[[940,648],[1027,675]]],
     property:[[1049,246],32,[[1049,505]]],security:[[131,172],28,[[180,505]]],door:[[1049,376],52,[[1049,505]]],pet:[[793,270],36,[[793,505]]]}},
 port:{floor:[62,512,638,822],lane:572,line:572,home:[330,572],kx:51,ky:57,sway:22,
   blocks:[[40,506,122,520],[124,506,552,520],[556,506,654,524],[72,606,444,644],[68,782,184,806],[560,796,622,812],...PORT_TABLES.map(tableBlock)],
   bench:[236,794,356,816],garden:[[262,828],[380,828]],
   customers:[[128,700],[216,700],[332,700],[420,700]],event:[560,700],officer:[440,790],
   staff:{x:170,step:105,y:532},cat:[606,362],counterSpan:[0,0],
   decor:{corner:[620,620],front:[500,822],center:[330,762]},sill:{plant:[92,556],lamp:[122,556],seat:[154,556],rug:[330,762]},
   badge:{workbench:[0,-40],board:[0,-50]},wall:{poster:[516,264]},
   spots:{'go:prep':[[82,352],36,[[82,572]]],shelf:[[98,262],50,[[98,572]]],evidence:[[507,336],40,[[507,572]]],workbench:[[292,412],72,[[292,572]]],counter:[[418,532],46,[[418,572]]],
     warehouse:[[82,430],45,[[82,572]]],board:[[604,296],40,[[604,572]]],finance:[[126,754],44,[[226,790],[126,772]]],
     property:[[606,228],32,[[606,572]]],security:[[74,188],28,[[150,572]]],door:[[590,770],45,[[520,800],[590,770]]],pet:[[606,344],36,[[606,572]]]}},
};

/* ------------------------------------------------------------ Palette */
const TILE='#fffaf3',GROUT='#efe1d2',TEAL='#a9d0c8',TEAL_G='#cfe6e0',WOOD='#cf9a6c',WOOD_L='#e8bd90',WOOD_D='#a06f4a',
  RED='#e7695c',RED_D='#c24c42',GOLD='#f3c45e',STEEL='#dfe5e4',STEEL_D='#a9b4b4',STEEL_L='#f3f6f5',CREAM='#fff6e6',INK='#6b4a3a',
  PEACH='#f8d8c4',CORAL='#ee8b78',CORAL_D='#c9665a',SHADOW='#6d4a3a1c';
// Broths: name, surface, bubble.
const BROTHS=[['Kim chi','#e0553d','#f7a488'],['Tomyum','#f08a2c','#fbc47d'],['Tương đen','#5e4136','#8e6857'],['Sữa phô mai','#f3cb52','#fbe7a0']];
const SPICE=['#f7e7a8','#f6d27f','#f4b565','#f19553','#ea7448','#dd5a3d','#c94333','#a93229'];

/* ------------------------------------------------------------ Small things */
/** Subway tiles over x,y,w,h. */
function tiles(c,x,y,w,h,tw,th,fill=TILE,grout=GROUT){R(c,x,y,w,h,fill,0);c.save();c.beginPath();c.rect(x,y,w,h);c.clip();
  for(let j=0,yy=y;yy<y+h;j++,yy+=th){L(c,x,yy,x+w,yy,grout,1.5);for(let xx=x+(j%2?tw/2:0);xx<x+w;xx+=tw)L(c,xx,yy,xx,yy+th,grout,1.5);}c.restore();}
/** Honey wooden floor planks, clipped to a rounded rect. */
function planks(c,x,y,w,h,rh){c.save();c.beginPath();c.roundRect(x,y,w,h,16);c.clip();
  for(let i=0,yy=y;yy<y+h;i++,yy+=rh){R(c,x,yy,w,rh,i%2?'#ecc79d':'#e4bb8f',0);for(let xx=x+(i%3)*67;xx<x+w;xx+=200)L(c,xx,yy+3,xx,yy+rh-3,'#cf9e72',1.5);L(c,x,yy,x+w,yy,'#d6a67a',1);}c.restore();}
/** Small square kitchen floor tiles. */
function kitchenFloor(c,x,y,w,h,s){c.save();c.beginPath();c.rect(x,y,w,h);c.clip();
  for(let i=0,yy=y;yy<y+h;i++,yy+=s)for(let j=0,xx=x;xx<x+w;j++,xx+=s){c.fillStyle=(i+j)%2?'#efe6da':'#f8f1e7';c.fillRect(xx,yy,s,s);}c.restore();}
/** A red chili with its green cap at (x,y). */
function chili(c,x,y,s,col=RED,rot=-.2){c.save();c.translate(x,y);c.rotate(rot);
  c.beginPath();c.moveTo(-6*s,-5*s);c.bezierCurveTo(4*s,-6*s,10*s,2*s,14*s,12*s);c.bezierCurveTo(6*s,6*s,-2*s,6*s,-7*s,4*s);c.bezierCurveTo(-10*s,2*s,-10*s,-4*s,-6*s,-5*s);c.closePath();c.fillStyle=col;c.fill();
  c.beginPath();c.moveTo(-3*s,-3*s);c.quadraticCurveTo(4*s,-3*s,8*s,3*s);c.strokeStyle='#ffffff80';c.lineWidth=1.4*s;c.lineCap='round';c.stroke();
  E(c,-8*s,0,3*s,4.5*s,'#7fb46f');L(c,-9*s,-2*s,-12*s,-8*s,'#6fa86a',2*s);c.restore();}
/** Font size that fits `max` px, allowed down to 7 px (small wall labels). */
function fitSmall(c,s,max,size,weight=800){c.font=`${weight} ${size}px "Trebuchet MS", "Segoe UI", sans-serif`;const w=c.measureText(tr(String(s))).width;return w>max?Math.max(7,Math.floor(size*max/w)):size;}
/** A noodle bowl seen from the front; y is the rim. */
function bowl(c,x,y,r,col,topping=0){c.beginPath();c.ellipse(x,y,r,r*.78,0,0,Math.PI);c.fillStyle='#fffaf1';c.fill();c.strokeStyle='#d8c3aa';c.lineWidth=1.2;c.stroke();
  c.beginPath();c.ellipse(x,y+r*.05,r*.93,r*.6,0,.35,Math.PI-.35);c.strokeStyle=RED;c.lineWidth=Math.max(1.2,r*.1);c.stroke();
  R(c,x-r*.34,y+r*.72,r*.68,r*.14,'#eadbc6',2);E(c,x,y,r,r*.3,'#f1e3d0');E(c,x,y+r*.02,r*.86,r*.22,col);
  for(let i=0;i<3;i++){c.beginPath();c.moveTo(x-r*.6,y-r*.02+i*r*.07);c.bezierCurveTo(x-r*.3,y-r*.14+i*r*.07,x-r*.1,y+r*.1+i*r*.07,x+r*.25,y-r*.04+i*r*.07);c.strokeStyle='#f7df98';c.lineWidth=Math.max(1,r*.08);c.stroke();}
  if(topping%2===0){E(c,x+r*.42,y-r*.03,r*.22,r*.13,'#fffdf5');E(c,x+r*.42,y-r*.03,r*.1,r*.07,'#f4b84a');}
  else{E(c,x+r*.38,y-r*.02,r*.2,r*.1,'#f2b9a6');E(c,x+r*.18,y+r*.05,r*.16,r*.08,'#f2b9a6');}
  for(let i=0;i<4;i++)E(c,x-r*.25+i*r*.16,y+(i%2?-.06:.07)*r,r*.05,r*.04,'#7dbb6b');}
/** A bowl with chopsticks lifting noodles: the shop's mark. */
function noodleLift(c,x,y,r,col=RED){bowl(c,x,y,r,col,0);
  for(let i=0;i<3;i++){const nx=x-r*.18+i*r*.16;c.beginPath();c.moveTo(nx,y);c.bezierCurveTo(nx-r*.14,y-r*.35,nx+r*.14,y-r*.6,nx,y-r*1.02);c.strokeStyle='#f3d27a';c.lineWidth=Math.max(1.2,r*.1);c.lineCap='round';c.stroke();}
  L(c,x-r*.3,y-r*1.02,x+r*1.05,y-r*1.75,'#b98252',Math.max(1.5,r*.1));L(c,x-r*.3,y-r*1.14,x+r*1.1,y-r*1.55,'#d4a06c',Math.max(1.5,r*.1));}
/** Rising steam puffs from (x,y) up to h; frozen when motion is reduced. */
function steam(c,x,y,h,s,t,reduced,seed){c.save();
  for(let j=0;j<3;j++){const ph=reduced?(j+.4)/3:(t*.3+j/3+seed*.37)%1,yy=y-ph*h,xx=x+Math.sin(ph*5+seed*1.3+j*2)*7*s,r=(6+ph*13)*s;
    c.globalAlpha=(reduced?.55:.8)*Math.sin(Math.PI*Math.min(1,ph*1.1+.05));E(c,xx,yy,r,r*.8,'#ffffff');E(c,xx+r*.55,yy+r*.25,r*.55,r*.45,'#ffffff');}
  c.restore();}
/** Red paper lantern hanging from (x,y); r is its radius. */
function lantern(c,x,y,r,t,reduced,i){const cy=y+r*1.6,g=c.createRadialGradient(x,cy,0,x,cy,r*3.4);g.addColorStop(0,'#ffcf8a66');g.addColorStop(1,'#ffcf8a00');c.fillStyle=g;c.fillRect(x-r*3.4,cy-r*3.4,r*6.8,r*6.8);
  c.save();c.translate(x,y);c.rotate(reduced?0:Math.sin(t*1.2+i*1.7)*.06);
  L(c,0,-4,0,r*.6,'#8b6a4d',1.5);R(c,-r*.45,r*.5,r*.9,r*.3,GOLD,2);E(c,0,r*1.6,r,r*.95,RED);
  for(const f of [.5,.9]){c.beginPath();c.ellipse(0,r*1.6,f*r,r*.95,0,0,Math.PI*2);c.strokeStyle=RED_D;c.lineWidth=1;c.stroke();}
  L(c,0,r*.66,0,r*2.54,RED_D,1);E(c,-r*.4,r*1.25,r*.2,r*.34,'#ffffff55');E(c,0,r*1.6,r*.34,r*.3,'#ffe0a066');
  R(c,-r*.45,r*2.42,r*.9,r*.3,GOLD,2);L(c,0,r*2.72,0,r*3.35,GOLD,2);L(c,-r*.16,r*2.75,-r*.22,r*3.3,GOLD,1.5);L(c,r*.16,r*2.75,r*.22,r*3.3,GOLD,1.5);c.restore();}
/** String of lanterns from x0 to x1 hanging off the ceiling at y. */
function lanterns(c,xs,x0,x1,y,r,t,reduced){c.strokeStyle='#9b7657';c.lineWidth=1.5;c.beginPath();c.moveTo(x0,y);
  for(const x of xs)c.quadraticCurveTo(x-20,y+10,x,y+6);c.lineTo(x1,y);c.stroke();xs.forEach((x,i)=>lantern(c,x,y+6,r,t,reduced,i));}

/* ------------------------------------------------------------ Kitchen line */
/** A big stock pot of broth; base is the stove top. */
function pot(c,cx,base,rx,h,b,k,t,reduced,i){const [,col,hi]=b;
  E(c,cx,base,rx+4*k,4*k,'#00000020');R(c,cx-rx,base-h,rx*2,h,STEEL,7*k,STEEL_D,1.5);R(c,cx-rx+6*k,base-h+9*k,6*k,h-18*k,'#ffffffa0',3);
  R(c,cx-rx-9*k,base-h+10*k,11*k,7*k,STEEL_D,3);R(c,cx+rx-2*k,base-h+10*k,11*k,7*k,STEEL_D,3);
  E(c,cx,base-h,rx+2*k,7*k,STEEL_D);E(c,cx,base-h+1,rx-1*k,5.5*k,col);
  for(let j=0;j<3;j++){const ph=reduced?j/3:(t*.9+j/3+i*.21)%1;E(c,cx-rx*.5+j*rx*.5,base-h+1,2.4*k*(1-ph*.5),1.6*k*(1-ph*.5),hi);}
  if(i===1){L(c,cx+rx*.3,base-h,cx+rx*.9,base-h-26*k,'#8f9a9b',3*k);E(c,cx+rx*.92,base-h-27*k,3*k,3*k,'#8f9a9b');}
  const tw=rx*1.7,ty=base-h*.55;
  E(c,cx,ty+8*k,10*k,10*k,CREAM);c.beginPath();c.arc(cx,ty+8*k,10*k,0,Math.PI*2);c.strokeStyle='#d8c2a8';c.lineWidth=1;c.stroke();E(c,cx,ty+8*k,6.5*k,6.5*k,col);}
/** Stove with four pots in a row over little flames. */
function stove(c,x0,x1,top,base,k,t,reduced){const w=x1-x0,n=4,rx=Math.min(36*k,(w/n)*.4),h=64*k;
  E(c,(x0+x1)/2,base+2,w*.52,6,SHADOW);R(c,x0,top,w,base-top,STEEL,6*k,STEEL_D,2);R(c,x0-4*k,top-6*k,w+8*k,10*k,STEEL_L,4*k,STEEL_D,1.5);
  for(let i=0;i<n;i++){const cx=x0+w*(i+.5)/n;
    // Oven door, knob and a glimpse of flame.
    R(c,cx-w/n*.38,top+14*k,w/n*.76,base-top-22*k,'#e9eeed',4*k,'#bdc6c5',1);L(c,cx-w/n*.25,top+20*k,cx+w/n*.25,top+20*k,'#b6c0bf',2*k);
    E(c,cx,top+7*k,4*k,3*k,'#7f8a8b');
    for(let f=-1;f<=1;f++){const fl=reduced?0:Math.sin(t*9+i*2+f)*1.2*k;P(c,[[cx+f*rx*.5-4*k,top-6*k],[cx+f*rx*.5,top-15*k-fl],[cx+f*rx*.5+4*k,top-6*k]],f?'#f7a64a':'#8fc3e6');}
    pot(c,cx,top-7*k,rx,h,BROTHS[i],k,t,reduced,i);}}
/** Steam over the four pots (drawn after the menu so it rises in front). */
function stoveSteam(c,x0,x1,top,k,t,reduced,h){const w=x1-x0;for(let i=0;i<4;i++)steam(c,x0+w*(i+.5)/4,top-7*k-64*k-4*k,h,k,t,reduced,i);}
/** Deep noodle boiler with wire baskets and a tray of noodle bricks. */
function boiler(c,x0,x1,top,base,k,t,reduced){const w=x1-x0;E(c,(x0+x1)/2,base+2,w*.55,5,SHADOW);
  R(c,x0,top,w,base-top,STEEL,6*k,STEEL_D,2);R(c,x0+w*.14,top+14*k,w*.72,base-top-24*k,'#e9eeed',4*k,'#bdc6c5',1);E(c,x0+w/2,top+8*k,4*k,3*k,'#7f8a8b');
  R(c,x0-3*k,top-24*k,w+6*k,26*k,STEEL_D,5*k);R(c,x0+3*k,top-21*k,w-6*k,8*k,'#cfe8ec',3);
  for(let i=0;i<3;i++){const bx=x0+w*(.22+i*.28),a=(i-1)*.25;
    L(c,bx,top-18*k,bx+Math.sin(a)*30*k,top-18*k-28*k,'#8f7d6b',3*k);R(c,bx+Math.sin(a)*30*k-3*k,top-50*k,6*k,8*k,RED_D,2);
    E(c,bx,top-19*k,9*k,3.5*k,'#c7b69f');for(let j=0;j<3;j++)L(c,bx-6*k+j*6*k,top-21*k,bx-4*k+j*6*k,top-17*k,'#f7df98',2*k);}
  steam(c,x0+w*.3,top-26*k,46*k,.9*k,t,reduced,7);steam(c,x0+w*.72,top-26*k,40*k,.8*k,t,reduced,9);}
/** Hanging menu: the four broths and the spice scale 0–7. */
function menuBoard(c,p,x,y,w,h,k,labels,hang){L(c,x+w*.18,hang,x+w*.18,y,'#8b6a4d',1.5);L(c,x+w*.82,hang,x+w*.82,y,'#8b6a4d',1.5);
  R(c,x-3,y+4,w+6,h,'#6d4a3a22',10*k);R(c,x,y,w,h,WOOD_D,9*k);R(c,x+4*k,y+4*k,w-8*k,h-8*k,'#fff3de',7*k);
  const top=h*.52;for(let i=0;i<4;i++){const bx=x+w*(i+.5)/4,by=y+(labels?top*.46:top*.52);bowl(c,bx,by,Math.min(17*k,w/12),BROTHS[i][1],i);
    if(labels)T(c,BROTHS[i][0],bx,y+top*.9,fitSmall(c,BROTHS[i][0],w/4-8,10*k),INK,800);}
  const sy=y+top+4*k,sh=h-top-12*k,x0=x+30*k,cw=(w-38*k)/8;chili(c,x+17*k,sy+sh/2,1.05*k);
  for(let i=0;i<8;i++){R(c,x0+i*cw+1,sy,cw-2,sh,SPICE[i],4*k);T(c,String(i),x0+i*cw+cw/2,sy+sh/2+1,Math.min(sh*.62,cw*.62),i>4?'#fff4e6':INK,800);}}
/** Rail of paper order tickets (the `evidence` hotspot). */
function orderRail(c,p,x,y,w,k){L(c,x-4*k,y,x+w+4*k,y,STEEL_D,4*k);E(c,x-4*k,y,3*k,3*k,'#8f9a9b');E(c,x+w+4*k,y,3*k,3*k,'#8f9a9b');
  const n=4;for(let i=0;i<n;i++){const tx=x+6*k+i*(w-12*k)/(n-1),th=(28+(i%2)*7)*k,col=i===1?'#ffe3e0':'#fffdf6';
    c.save();c.translate(tx,y+2*k);c.rotate((i-1.5)*.05);R(c,-9*k,0,18*k,th,col,2,'#d8cbb8',1);R(c,-9*k,0,18*k,5*k,[RED,GOLD,TEAL,CORAL][i],2);
    for(let j=0;j<3;j++)L(c,-5*k,10*k+j*6*k,(j===2?1:5)*k,10*k+j*6*k,'#c2b3a2',1.2);if(i===2)chili(c,2*k,th-5*k,.4*k);c.restore();}}
/** Walk-in cold store door (the `warehouse` hotspot). */
function coldStore(c,p,x0,x1,top,base,k,label,locked){const w=x1-x0,h=base-top;R(c,x0-5*k,top-6*k,w+10*k,h+6*k,STEEL_D,8*k);R(c,x0,top,w,h,'#e8eeee',6*k,'#b9c3c3',1.5);
  R(c,x0+w*.16,top+12*k,w*.68,h*.22,'#d8eff4',5*k,'#b9c3c3',1);const fx=x0+w/2,fy=top+12*k+h*.11,fr=Math.min(w*.2,h*.08);
  for(let i=0;i<3;i++){const a=i*Math.PI/3;L(c,fx-Math.cos(a)*fr,fy-Math.sin(a)*fr,fx+Math.cos(a)*fr,fy+Math.sin(a)*fr,'#9fcbd8',2*k);}
  R(c,x1-15*k,top+h*.42,7*k,h*.2,'#8f9a9b',3);R(c,x0+w*.14,top+h*.4,w*.52,17*k,'#4f5f60',4);T(c,'-2°C',x0+w*.4,top+h*.4+9*k,11*k,'#a5f0bb',800);
  const ly=top+h*.62;R(c,x0+w*.1,ly,w*.8,24*k,CREAM,5*k,'#c6b8a4',1.2);T(c,label,x0+w/2,ly+12*k,fit(c,label,w*.72,15*k,800),INK,800);
  for(let i=0;i<4;i++)L(c,x0+6*k+i*(w-12*k)/3,base-26*k,x0+6*k+i*(w-12*k)/3,base-6*k,'#cdd6d6',3*k);
  if(locked){const lx=x1-26*k,ly2=top+h*.3;R(c,lx-8*k,ly2,16*k,18*k,'#d8c596',5,'#a59470',1);c.beginPath();c.arc(lx,ly2,5*k,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=3;c.stroke();}}
/** Wall shelves of spices and toppings (the `shelf` hotspot). */
function spiceShelf(c,x0,x1,ys,k){const w=x1-x0;
  ys.forEach((y,row)=>{L(c,x0+10*k,y+6*k,x0+16*k,y+16*k,WOOD_D,3);L(c,x1-10*k,y+6*k,x1-16*k,y+16*k,WOOD_D,3);
    const n=Math.max(3,Math.floor(w/(30*k)));for(let i=0;i<n;i++){const x=x0+w*(i+.5)/n,kind=(i+row*2)%6;
      if(kind===0){R(c,x-10*k,y-26*k,20*k,26*k,'#fbeee7',5,'#d9c2b2',1);R(c,x-8*k,y-18*k,16*k,16*k,'#e0553d',3);R(c,x-10*k,y-31*k,20*k,6*k,'#8fbf78',2);}
      else if(kind===1){R(c,x-11*k,y-17*k,22*k,17*k,RED_D,4);R(c,x-12*k,y-21*k,24*k,6*k,GOLD,3);R(c,x-6*k,y-12*k,12*k,6*k,'#fff3e0',2);}
      else if(kind===2){R(c,x-5*k,y-24*k,10*k,24*k,'#5a3b30',3);R(c,x-2.5*k,y-31*k,5*k,8*k,'#5a3b30',2);R(c,x-5*k,y-15*k,10*k,7*k,CREAM,1);}
      else if(kind===3){R(c,x-12*k,y-12*k,24*k,12*k,'#d9b27c',4);for(let j=0;j<3;j++)E(c,x-7*k+j*7*k,y-13*k,4.5*k,5.5*k,'#fffaf0');}
      else if(kind===4){R(c,x-6*k,y-26*k,12*k,26*k,'#e7a94c',4);R(c,x-3*k,y-32*k,6*k,7*k,'#b8843a',2);R(c,x-6*k,y-17*k,12*k,8*k,CREAM,1);}
      else{for(let j=0;j<4;j++)L(c,x-6*k+j*4*k,y-2*k,x-8*k+j*5*k,y-26*k,j%2?'#86c077':'#a5d68f',3*k);R(c,x-8*k,y-8*k,16*k,5*k,'#f2e6c8',2);}}
    R(c,x0,y,w,7*k,WOOD,3,WOOD_D,1);});}

/* ------------------------------------------------------------ Dining wall */
/** Drinks fridge; Mướp naps on top. */
function drinksFridge(c,x0,x1,top,base,k){const w=x1-x0,h=base-top;E(c,(x0+x1)/2,base+2,w*.6,5,SHADOW);
  R(c,x0,top,w,h,CORAL,8*k,CORAL_D,2);R(c,x0+5*k,top+5*k,w-10*k,15*k,'#fff3e6',4);heart(c,x0+w/2,top+15*k,.26*k,CORAL);
  const gy=top+26*k,gh=h-44*k;R(c,x0+6*k,gy,w-12*k,gh,'#e4f4f2',5,CORAL_D,1.2);
  const cols=['#9fd3a0','#f3c45e','#f59a8c','#a9c7ea','#c9b5dc','#ffe08a'],rows=4,rh=gh/rows;
  for(let r=0;r<rows;r++){const y=gy+(r+1)*rh-3*k;L(c,x0+8*k,y+2*k,x1-8*k,y+2*k,'#c6dcda',2*k);
    for(let i=0;i<3;i++){const bx=x0+w*(.28+i*.22),col=cols[(r*3+i)%6];if((r+i)%2){R(c,bx-4*k,y-rh*.62,8*k,rh*.62,col,3);R(c,bx-2*k,y-rh*.78,4*k,rh*.18,col,1);}else R(c,bx-5*k,y-rh*.48,10*k,rh*.48,col,3);}}
  R(c,x0+6*k,gy,w*.18,gh,'#ffffff40',4);R(c,x1-12*k,gy+gh*.35,4*k,gh*.3,'#fff3e6',2);R(c,x0+6*k,base-14*k,w-12*k,8*k,CORAL_D,3);}
/** Evening window: dusk sky, moon, a lit street, a short red curtain. */
function eveningWindow(c,x,y,w,h,k,t,reduced){R(c,x-7*k,y-7*k,w+14*k,h+14*k,WOOD,12*k);c.save();c.beginPath();c.roundRect(x,y,w,h,8*k);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#8f8cc6');g.addColorStop(.55,'#d9a5b8');g.addColorStop(1,'#f7c29a');c.fillStyle=g;c.fillRect(x,y,w,h);
  for(let i=0;i<5;i++){const tw=reduced?1:.6+.4*Math.sin(t*2+i*1.9);c.globalAlpha=tw;E(c,x+w*((i*.37+.12)%1),y+h*(.12+(i%3)*.1),1.6*k,1.6*k,'#fffbe8');}c.globalAlpha=1;
  E(c,x+w*.74,y+h*.22,12*k,12*k,'#fff1c2');E(c,x+w*.74+5*k,y+h*.22-3*k,10*k,10*k,'#b39ac6');
  const bs=[[.0,.5,.3],[.26,.38,.24],[.5,.56,.22],[.7,.44,.32]];for(const [bx,bh,bw] of bs){const X=x+w*bx,Y=y+h*bh;R(c,X,Y,w*bw,h,'#6f6a9c',3);
    for(let i=0;i<3;i++)for(let j=0;j<3;j++)if((i+j+Math.round(bx*10))%2===0)R(c,X+5*k+i*w*bw*.3,Y+8*k+j*14*k,5*k,6*k,'#ffd98a',1);}
  L(c,x,y+h*.86,x+w,y+h*.8,'#9b7657',1);for(let i=0;i<5;i++)E(c,x+w*(i+.5)/5,y+h*.83+2*k,2.4*k,2.4*k,'#ffe3a1');c.restore();
  L(c,x+w/2,y,x+w/2,y+h,'#f3d6b4',4*k);
  // Short red café curtain with white dots.
  for(let i=0;i<3;i++){const cx=x+w*(i+.5)/3,cw=w/3;R(c,cx-cw/2+1,y,cw-2,h*.2,RED,0);E(c,cx,y+h*.2,cw/2-1,6*k,RED);E(c,cx,y+h*.1,4*k,4*k,'#fff4ea');}
  L(c,x-10*k,y+2,x+w+10*k,y+2,WOOD_D,4*k);R(c,x-12*k,y+h+6*k,w+24*k,9*k,WOOD_L,4,WOOD_D,1);}
/** Door with a red curtain, open / closed sign. */
function door(c,p,x,y,w,h,k,open,words){R(c,x-7*k,y-7*k,w+14*k,h+7*k,WOOD_D,8*k);
  if(open){const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#8f8cc6');g.addColorStop(1,'#f5c49e');c.fillStyle=g;c.fillRect(x,y,w,h);R(c,x,y+h*.78,w,h*.22,'#c9b39a',0);E(c,x+w*.5,y+h*.62,5*k,5*k,'#ffe3a1');L(c,x+w*.5,y+h*.62,x+w*.5,y+h*.8,'#6f6a9c',2*k);
    P(c,[[x+w-3,y],[x+w+10*k,y-4*k],[x+w+10*k,y+h+3*k],[x+w-3,y+h]],'#e6bb8f');}
  else{R(c,x,y,w,h,'#e6bb8f',5*k,WOOD_D,1.5);R(c,x+w*.16,y+h*.3,w*.68,h*.28,'#dbeff0',5*k,WOOD_D,1.2);R(c,x+w*.14,y+h*.66,w*.72,h*.26,'#dcac7e',4*k);E(c,x+w-10*k,y+h*.6,4*k,4*k,'#c69b52');}
  // Noren-style red curtain over the doorway with a noodle-bowl mark.
  const ch=h*.24;for(let i=0;i<2;i++){R(c,x+i*w/2+1,y,w/2-2,ch,RED,[0,0,4,4]);}bowl(c,x+w/2,y+ch*.5,Math.min(10*k,w*.13),GOLD,0);
  L(c,x-6*k,y+1,x+w+6*k,y+1,WOOD_D,5*k);
  const s=open?words.open_sign:words.closed_sign,sw=w+16*k,sy=y+h*.38,size=11*k;L(c,x+w/2,sy-10*k,x+w/2-16*k,sy,'#8b6a4d',1.5);L(c,x+w/2,sy-10*k,x+w/2+16*k,sy,'#8b6a4d',1.5);
  R(c,x+w/2-sw/2,sy,sw,size*2,'#fff8e8',8*k,open?'#8fb77f':'#d59a9a',2);T(c,s,x+w/2,sy+size+1,fit(c,s,sw-10,size,800),open?p.dark:'#a35f63',800);}
/** Small shop plaque (the `property` hotspot): a bowl and three chilis. */
function plaque(c,p,cx,y,w,h,k){R(c,cx-w/2,y,w,h,WOOD_D,7*k);R(c,cx-w/2+4*k,y+4*k,w-8*k,h-8*k,CREAM,5*k);bowl(c,cx-w*.2,y+h*.46,Math.min(11*k,h*.3),RED,0);for(let i=0;i<3;i++)chili(c,cx+w*.08+i*w*.12,y+h*.5,.45*k);}
/** Security equivalents: camera or a charm, a door bell, a porch light. */
function security(c,p,items,cam,bell,lamp){
  if(items.includes('camera')){const [x,y]=cam;L(c,x-8,y+12,x+2,y+2,'#b79b85',4);R(c,x-4,y-10,36,20,'#f5f2eb',7,'#a7aaa2',2);E(c,x+26,y,7,8,'#7a8992');E(c,x+27,y,3,4,'#b4d9df');E(c,x+2,y-5,2,2,'#90bd8b');}
  else{const [x,y]=cam;R(c,x-6,y-11,38,22,'#fff6e9',8,'#d5b59a',1);T(c,'♧',x+13,y,14,p.dark);}
  if(items.includes('bell')){const [x,y]=bell;L(c,x,y-14,x,y-4,'#ac8f73',2);P(c,[[x-11,y+12],[x+11,y+12],[x+8,y-3],[x-8,y-3]],'#f0ce85');E(c,x,y-3,8,4,'#f0ce85');E(c,x,y+14,4,3,'#d4ad64');}
  if(items.includes('light')){const [x,y]=lamp,g=c.createRadialGradient(x,y+20,0,x,y+20,90);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(x-90,y-70,180,180);R(c,x-14,y-12,28,22,'#fff0b8',8,'#b69b79',2);}}
/** Landscape shop sign: cream board, red frame, a steaming bowl and chilis. */
function shopSign(c,p,x,y,w,h,t,reduced){R(c,x-5,y+7,w+10,h,CORAL_D,30);R(c,x,y,w,h,'#fff8ec',28,CORAL,3);R(c,x+10,y+10,w-20,h-20,'#fffbf4',22,'#f4d3c2',2);
  noodleLift(c,x+54,y+h*.66,24);steam(c,x+40,y+h*.5,24,.7,t,reduced,3);
  const cx=x+w/2+8;T(c,p.title,cx,y+h*.42,fit(c,p.title,w-196,30,800),p.dark,800);T(c,p.sub,cx,y+h-26,fit(c,p.sub,w-170,12),p.dark);
  chili(c,x+w-62,y+h*.36,1.3,RED,.1);chili(c,x+w-50,y+h*.42,1.2,RED_D,.55);}

/* ------------------------------------------------------------ Floor pieces */
/** The pass (the `counter` hotspot): bowls ready to go out, chopsticks,
 * a service bell and the till at its right end. */
function passCounter(c,p,x0,x1,top,base,k,worn,portrait){const w=x1-x0;E(c,(x0+x1)/2,base+2,w*.52,9,SHADOW);
  R(c,x0+6*k,top+12*k,w-12*k,base-top-12*k,CORAL,10*k,CORAL_D,2);
  c.save();c.beginPath();c.roundRect(x0+6*k,top+12*k,w-12*k,base-top-12*k,10*k);c.clip();
  for(let r=0,yy=top+30*k;yy<base-6*k;r++,yy+=22*k)for(let xx=x0+(r%2?26:14)*k;xx<x1;xx+=24*k)E(c,xx,yy,3.2*k,3.2*k,'#fbd3c8');c.restore();
  R(c,x0+w*.36,top+26*k,w*.28,base-top-40*k,'#fff6e6',9*k,CORAL_D,1.5);{const py=top+26*k+(base-top-40*k)*.72;noodleLift(c,x0+w*.5-14*k,py,13*k);chili(c,x0+w*.5+18*k,py-12*k,.8*k,RED,.2);}
  R(c,x0,top,w,16*k,WOOD_L,8*k,WOOD_D,2);R(c,x0+5,top+3,w-10,4*k,'#f6d7b4',2);
  // On top: chopstick jar, ready bowls, bell and the till.
  const y=top+2;R(c,x0+18*k,y-26*k,16*k,26*k,'#b9d8cf',4,'#8fb5aa',1);for(let i=0;i<5;i++)L(c,x0+21*k+i*2.6*k,y-24*k,x0+19*k+i*3.4*k,y-40*k,i%2?'#c89060':'#e2b07c',2*k);
  R(c,x0+40*k,y-14*k,22*k,14*k,'#fffaf0',3,'#d8c3aa',1);E(c,x0+51*k,y-15*k,6*k,3*k,'#ffffff');
  const n=portrait?3:4,bx0=x0+w*.22,bx1=x1-w*(portrait?.34:.26);
  for(let i=0;i<n;i++){const bx=bx0+(bx1-bx0)*i/(n-1);R(c,bx-19*k,y-4*k,38*k,5*k,'#f0e2cf',2);bowl(c,bx,y-17*k,16*k,BROTHS[i%4][1],i);}
  const bell=x1-w*(portrait?.26:.2);E(c,bell,y-2*k,8*k,2.5*k,'#b99a5e');c.beginPath();c.arc(bell,y-3*k,7*k,Math.PI,0);c.fillStyle=GOLD;c.fill();E(c,bell,y-11*k,2*k,2*k,'#b99a5e');
  const tx=x1-40*k;R(c,tx-18*k,y-26*k,40*k,26*k,'#f6efe4',5,'#b9aa98',1.5);R(c,tx-12*k,y-22*k,28*k,9*k,'#5c6b6c',2);T(c,'35',tx+2*k,y-17.5*k,8*k,'#a5f0bb',800);
  for(let i=0;i<3;i++)R(c,tx-12*k+i*10*k,y-10*k,7*k,5*k,i===2?'#f2b9a6':'#dcd3c7',1);R(c,tx-16*k,y-38*k,20*k,12*k,'#fffdf6',2,'#d8cbb8',1);
  if(worn){R(c,x0+14*k,top+22*k,74*k,15*k,'#f7d995',4);T(c,'CẦN KIỂM',x0+51*k,top+30*k,Math.max(9,9*k),'#94643d',800);}}
/** A wooden table with two stools; bowls steam where someone sits. */
function table(c,x0,x1,base,k,seats,v){const w=x1-x0,cx=(x0+x1)/2,top=base-54*k;E(c,cx,base,w*.56,7,SHADOW);
  for(const sx of [x0-2*k,x1+2*k]){L(c,sx-8*k,base-20*k,sx-10*k,base,WOOD_D,3*k);L(c,sx+8*k,base-20*k,sx+10*k,base,WOOD_D,3*k);E(c,sx,base-21*k,15*k,5*k,RED);E(c,sx,base-23*k,13*k,3.5*k,'#f28d80');}
  L(c,x0+12*k,top+10*k,x0+14*k,base,WOOD_D,5*k);L(c,x1-12*k,top+10*k,x1-14*k,base,WOOD_D,5*k);
  R(c,x0+4*k,top+8*k,w-8*k,14*k,WOOD,4,WOOD_D,1.5);R(c,x0-3*k,top,w+6*k,11*k,WOOD_L,5,WOOD_D,1.5);R(c,x0+2*k,top+2*k,w-4*k,3*k,'#f6d7b4',2);
  // Table things: chopstick jar, chili sauce and soy, napkins.
  const y=top+1;R(c,x0+8*k,y-20*k,12*k,20*k,'#b9d8cf',3,'#8fb5aa',1);for(let i=0;i<4;i++)L(c,x0+10*k+i*2.4*k,y-18*k,x0+9*k+i*3*k,y-30*k,'#d9a36e',1.6*k);
  R(c,x1-22*k,y-20*k,8*k,20*k,RED,3);R(c,x1-20*k,y-25*k,4*k,6*k,'#f7e7c8',1);R(c,x1-12*k,y-17*k,7*k,17*k,'#5a3b30',3);
  if(v%2===0){R(c,x0+24*k,y-11*k,16*k,11*k,'#fffaf0',2,'#d8c3aa',1);E(c,x0+32*k,y-12*k,5*k,2.5*k,'#ffffff');}
  seats.forEach((sx,i)=>{bowl(c,sx,y-9*k,13*k,BROTHS[(v+i)%4][1],v+i);L(c,sx+15*k,y-3*k,sx+26*k,y-12*k,'#c89060',1.6*k);});
  return y-22*k;}
/** Cash desk (the `finance` hotspot) with the shop ledger and a coin jar. */
function cashDesk(c,p,x0,x1,top,base,k,label){const w=x1-x0,cx=(x0+x1)/2;E(c,cx,base+2,w*.56,7,SHADOW);
  R(c,x0,top+12*k,w,base-top-12*k,WOOD,9*k,WOOD_D,2);R(c,x0-5*k,top,w+10*k,14*k,WOOD_L,6*k,WOOD_D,1.5);
  R(c,x0+8*k,top+22*k,w-16*k,base-top-32*k,CREAM,6*k,'#d8c2a8',1);T(c,label,cx,top+22*k+(base-top-32*k)/2,fit(c,label,w-24*k,14*k,800),INK,800);
  const y=top+1;R(c,x0+8*k,y-7*k,w*.46,8*k,'#fffaf0',2,'#c9b9a3',1);L(c,x0+8*k+w*.23,y-7*k,x0+8*k+w*.23,y+1,'#c9b9a3',1);L(c,x0+14*k,y-4*k,x0+w*.2,y-4*k,p.primary,1.2);
  R(c,x1-30*k,y-24*k,16*k,24*k,'#e4f4f2',5,'#9fc2bd',1.2);for(let i=0;i<3;i++)E(c,x1-22*k,y-6*k-i*5*k,5*k,2*k,'#efc970');
  R(c,x0+w*.56,y-12*k,14*k,12*k,'#f5ede0',2,'#b9aa98',1);R(c,x0+w*.56+2*k,y-10*k,10*k,3*k,'#5c6b6c',1);}
/** Phone door: doormat and an A-frame board with the open sign. */
function aSign(c,p,cx,base,k,open,words){E(c,cx-6*k,base+4*k,56*k,9*k,'#c9a27f66');E(c,cx-6*k,base+3*k,48*k,6*k,'#e0c3a1');
  L(c,cx-26*k,base,cx-18*k,base-78*k,WOOD_D,5*k);L(c,cx+26*k,base,cx+18*k,base-78*k,WOOD_D,5*k);
  R(c,cx-30*k,base-86*k,60*k,62*k,'#4f6f63',7*k,WOOD_D,3*k);noodleLift(c,cx-3*k,base-60*k,10*k);
  const s=open?words.open_sign:words.closed_sign;T(c,s,cx,base-40*k,fit(c,s,52*k,16,800),open?'#fff3d6':'#f6c2bd',800);
  R(c,cx-38*k,base-100*k,76*k,16*k,RED,[6*k,6*k,0,0]);for(let i=0;i<4;i++)L(c,cx-38*k+(i+.5)*19*k,base-86*k,cx-38*k+(i+.5)*19*k,base-100*k,RED_D,1);}
/** Brown earthenware kimchi jar (onggi) standing on base. */
function onggi(c,x,base,s){E(c,x,base,26*s,6*s,SHADOW);c.beginPath();c.moveTo(x-12*s,base);c.bezierCurveTo(x-34*s,base-16*s,x-30*s,base-48*s,x-15*s,base-54*s);c.lineTo(x+15*s,base-54*s);c.bezierCurveTo(x+30*s,base-48*s,x+34*s,base-16*s,x+12*s,base);c.closePath();c.fillStyle='#a8683f';c.fill();
  c.beginPath();c.ellipse(x,base-30*s,25*s,3*s,0,0,Math.PI);c.strokeStyle='#8a5132';c.lineWidth=2*s;c.stroke();E(c,x-14*s,base-36*s,4*s,10*s,'#ffffff30');
  R(c,x-17*s,base-60*s,34*s,8*s,'#8a5132',4*s);E(c,x,base-61*s,13*s,4*s,'#b8764b');E(c,x,base-64*s,4*s,3*s,'#8a5132');}
/** Waiting bench (sunny / garden tiers). */
function bench(c,p,x0,x1,top,base,k,garden){const w=x1-x0;E(c,(x0+x1)/2,base+1,w*.55,5,SHADOW);
  L(c,x0+10,top+10,x0+10,base,WOOD_D,5);L(c,x1-10,top+10,x1-10,base,WOOD_D,5);R(c,x0,top-6*k,w,15*k,WOOD_L,6,WOOD_D,1.5);
  for(let i=0;i<2;i++)E(c,x0+w*(.3+i*.4),top-8*k,w*.16,6*k,i?'#f2b9a6':'#b9d8cf');if(garden)bloom(c,x1-6,top-14*k,8*k,p.primary);}

/* ------------------------------------------------------------ Rooms */
/** Soft warm evening wash over the room. */
function warmth(c,x,y,w,h){const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#ffb46a1c');g.addColorStop(.6,'#ffb46a08');g.addColorStop(1,'#ffb46a00');c.fillStyle=g;c.fillRect(x,y,w,h);}

function landRoom(w,p){const c=w.ctx,t=w.time||0,rd=!!w.reduced,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  E(c,600,722,505,28,'#cba88d22');R(c,85,128,1030,590,'#e3b694',35);R(c,96,132,1008,574,'#fff9ee',30,'#d9ac90',3);
  c.save();c.beginPath();c.roundRect(108,142,984,548,22);c.clip();
  // Kitchen: cream subway tiles, a teal splash-back behind the stove; dining: peach wall over a wood wainscot.
  tiles(c,108,142,648,312,36,18);R(c,108,300,648,10,'#f3b2a2',0);
  tiles(c,334,210,418,190,26,16,TEAL,TEAL_G);
  R(c,756,142,336,312,PEACH,0);for(let x=770;x<1092;x+=26)L(c,x,150,x,380,'#f3cdb766',2);
  R(c,756,382,336,72,'#dca77c',0);for(let x=766;x<1092;x+=22)L(c,x,386,x,452,'#c8915f',1.5);R(c,756,378,336,7,WOOD_D,2);
  R(c,750,142,10,312,WOOD_D,0);
  planks(c,108,448,984,242,30);kitchenFloor(c,108,448,652,96,16);R(c,108,446,984,7,'#c99b72',3);
  R(c,108,142,984,16,WOOD_D,0);for(let x=150;x<1092;x+=180)R(c,x,142,12,16,'#8a5b3b',0);
  c.restore();
  shopSign(c,p,368,26,464,104,t,rd);
  // Kitchen line along the back wall.
  coldStore(c,p,122,206,254,452,1,words.store,items.includes('lock'));
  spiceShelf(c,220,328,[252,316,380],1);
  menuBoard(c,p,356,172,290,86,1,true,158);
  stove(c,342,648,400,456,1,t,rd);stoveSteam(c,342,648,400,1,t,rd,100);
  boiler(c,660,744,404,456,1,t,rd);orderRail(c,p,664,276,76,1);
  // Dining wall.
  drinksFridge(c,762,826,290,456,1);
  eveningWindow(c,846,222,98,148,1,t,rd);
  streetBoard(c,p,950,298,.82);
  plaque(c,p,1049,230,70,32,1);
  door(c,p,1014,276,70,176,1,open,words);
  lanterns(c,[190,300,800,892,980],108,1092,158,13,t,rd);
  security(c,p,items,[114,172],[998,262],[1049,272]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,862+i*34,372,6,[p.primary,'#f2b9c9','#f3d98a'][i]);
  warmth(c,108,142,984,548);}

function portRoom(w,p){const c=w.ctx,t=w.time||0,rd=!!w.reduced,items=w.c?.ops?.security?.items||[],words=w.words();
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#e1b594',31);R(c,29,117,642,724,'#fff9ed',26,'#d9ae91',3);
  c.save();c.beginPath();c.roundRect(40,139,620,690,21);c.clip();
  tiles(c,40,139,620,380,34,18);R(c,40,352,620,10,'#f3b2a2',0);
  tiles(c,124,282,430,172,26,16,TEAL,TEAL_G);
  R(c,554,139,106,380,PEACH,0);R(c,550,139,8,380,WOOD_D,0);
  planks(c,40,508,620,321,36);kitchenFloor(c,40,508,620,110,18);R(c,40,504,620,7,'#c99b72',3);
  R(c,40,139,620,20,WOOD_D,0);
  c.restore();
  coldStore(c,p,46,118,338,512,1.1,words.store,items.includes('lock'));
  spiceShelf(c,46,150,[262,320],1.1);
  menuBoard(c,p,168,206,290,100,1.25,false,158);
  stove(c,128,460,456,516,1.1,t,rd);stoveSteam(c,128,460,456,1.1,t,rd,92);
  boiler(c,470,550,458,516,1.1,t,rd);orderRail(c,p,470,322,78,1.2);
  drinksFridge(c,562,650,364,520,1.2);
  streetBoard(c,p,572,258,.95);
  plaque(c,p,606,206,78,40,1.2);
  lanterns(c,[96,470,540],40,660,168,15,t,rd);
  security(c,p,items,[56,186],[640,318],[606,160]);
  warmth(c,40,139,620,690);}

/* ------------------------------------------------------------ Floor props */
/** Seat x positions of guests standing just behind a table. */
function seated(w,x0,x1,base){const out=[];for(const q of w.people||[]){if(!/^npc:|^event$/.test(q.id))continue;const s=w.project(q.x,q.y);if(s.x>x0-10&&s.x<x1+10&&base-s.y>0&&base-s.y<50)out.push(s.x);}return out;}

function landProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',worn=(w.c?.ops?.equipment?.condition??100)<100,out=[];
  out.push([582,()=>passCounter(c,p,228,746,482,582,1,worn,false)]);
  LAND_TABLES.forEach(([x0,x1,base],i)=>out.push([base,()=>table(c,x0,x1,base,1,seated(w,x0,x1,base),i)]));
  out.push([660,()=>cashDesk(c,p,984,1070,596,660,1,words.ledger)]);
  out.push([596,()=>{onggi(c,120,596,1.05);onggi(c,152,604,.72);}]);
  if(tier!=='cozy')out.push([676,()=>bench(c,p,140,262,652,676,1,tier==='garden')]);
  if(tier==='garden')for(const [x,y] of w.plan().garden)out.push([y+4,()=>plantAt(c,x,y,.55)]);
  return out;}

function portProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,worn=(w.c?.ops?.equipment?.condition??100)<100,out=[];
  out.push([644,()=>passCounter(c,p,66,450,558,644,1.2,worn,true)]);
  PORT_TABLES.forEach(([x0,x1,base],i)=>out.push([base,()=>table(c,x0,x1,base,1.15,seated(w,x0,x1,base),i)]));
  out.push([806,()=>cashDesk(c,p,66,186,744,806,1.2,words.ledger)]);
  out.push([812,()=>aSign(c,p,590,810,1.15,open,words)]);
  if(tier!=='cozy')out.push([816,()=>bench(c,p,236,356,792,816,1.3,tier==='garden')]);
  if(tier==='garden')for(const [x,y] of w.plan().garden)out.push([y+4,()=>plantAt(c,x,y,.5)]);
  return out;}

/* ------------------------------------------------------------ the cold store (scenes/backroom.js) */
/** Kho lạnh & sơ chế: the walk-in fridge, the prep counter with the sink, spare spices, crates of greens. */
const PREP=room({id:'prep',name:'Kho lạnh & sơ chế',icon:'🧊',back:'dining',sign:'KHU SƠ CHẾ',
  theme:{wall:'#e9f1ef',wallLow:'#cfe3df',floor:'#c9d3d6',floor2:'#bfcacd',tile:56,rim:'#8fa3a8',trim:'#4f8f8a',ink:'#a8402f',door:'#4f8f8a'},
  clock:[.58,.27],calendar:[.35,.34],
  items:[
    {k:'fridge',u:.2,v:.1,w:.19,h:232,tag:'KHO LẠNH',top:'#4f8f8a',fill:['🥩','🦐','🥬','🧊','🍤','🥚'],spot:'warehouse',label:'Kho lạnh'},
    {k:'counter',u:.58,v:.1,w:.34,h:84,sink:.16,top:'#e4eaee',col:'#c0c7cd',fill:['🔪','🥬','🧅','🌶️','🥕'],spot:'workbench',label:'Bàn sơ chế'},
    {k:'shelf',u:.88,v:.1,w:.13,h:220,col:'#c0c7cd',board:'#9aa6b0',fill:['🌶️','🧄','🫙','🧂'],spot:'shelf',label:'Kệ gia vị dự trữ'},
    {k:'boxes',u:.5,v:.64,w:.2,h:76,fill:['RAU','MÌ','ĐÁ'],spot:'look:crates',label:'Thùng hàng sáng nay'},
  ],
  looks:{crates:()=>'Thùng rau sáng nay: cải thảo, hành boa rô, nấm kim châm. Tươi rói.'},
  chat:['Bàn 3 thêm một tô cấp 7!','Hết hành phi rồi, phi thêm nha!','Rau mới về, rửa liền nè.'],
});

export default {
  id:'kitchen',
  areas:[{id:'dining',name:'Quán',icon:'🍜',main:true},PREP],
  areaFor:shopFor('dining'),
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
