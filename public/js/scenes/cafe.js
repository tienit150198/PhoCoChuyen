/** Bakery-café scene (cafe_bakery): "Tiệm Bánh & Cà Phê Sớm Mai" at sunrise.
 * Back wall, left to right: a bread rack of baskets (baguettes, boules,
 * croissants), a brick-arched deck oven glowing warm, a white subway-tiled
 * back bar with the espresso machine and grinder (the `workbench`, "Quầy &
 * lò"), a chalkboard coffee menu, Bé Men the sourdough starter on the shelf
 * and the order-ticket rail (`evidence`), then a gingham-curtained window with
 * the morning sun, a window bar with stools where Mướp naps (`pet`), the house
 * plaque (`property`) and the street board.
 * Floor: the front counter, whose left half is the glass pastry case (`shelf`)
 * and whose right end is the till and pickup bell (`counter`); the flour
 * pantry (`warehouse`); a round marble café table; a little ledger stand
 * (`finance`) and a chalk A-frame by the door (`door`). Honey wood floor with
 * morning light slanting in. PLAN schema: see scenes/shop.js.
 *
 * Floor pieces are drawn in local units with the origin at the middle of
 * their feet line and placed with `at(x, y, scale)`; portrait reuses them.
 * Portrait keeps everything important below scene y≈150 (the title card
 * covers the top) and its text at 16 scene px or more.
 */
import {R,E,L,T,P,fit,heart,bloom,plantAt,streetBoard} from './kit.js';
import {room,shopFor,taskOf} from './backroom.js';

export const PLAN={
 land:{floor:[130,452,1070,682],lane:522,line:600,home:[600,522],kx:82,ky:45,sway:30,
   blocks:[[136,452,212,532],[238,452,420,468],[432,452,768,468],[220,556,740,598],[806,452,990,482],[838,604,930,628],[1012,558,1070,584],[982,652,1070,668]],
   bench:[148,656,268,678],garden:[[290,680],[560,680]],
   customers:[[330,636],[455,648],[580,636],[700,648]],event:[215,622],officer:[800,668],
   staff:{x:300,step:120,y:484},cat:[962,424],counterSpan:[240,730],
   decor:{corner:[150,614],front:[930,674],center:[640,676]},sill:{plant:[812,402],lamp:[842,402],seat:[905,406],rug:[520,662]},
   wall:{poster:[1036,432]},badge:{workbench:[-30,-20],board:[34,-32]},
   spots:{'go:bakery':[[150,388],40,[[246,522]]],shelf:[[350,486],62,[[350,522]]],evidence:[[704,358],45,[[730,522]]],workbench:[[500,392],82,[[520,522]]],counter:[[680,486],52,[[680,522]]],
     warehouse:[[175,470],48,[[175,566],[246,522]]],board:[[1050,340],45,[[1045,505]]],finance:[[1040,540],42,[[975,572],[1040,612]]],
     property:[[1030,254],30,[[1045,505]]],security:[[150,202],30,[[250,522]]],door:[[1026,630],45,[[940,650],[1026,612]]],pet:[[962,404],38,[[935,522]]]}},
 port:{floor:[62,512,638,822],lane:574,line:660,home:[330,574],kx:51,ky:57,sway:22,
   blocks:[[50,512,114,600],[120,506,262,520],[268,506,478,520],[95,612,530,654],[592,512,652,550],[58,756,176,782],[480,806,584,820]],
   bench:[190,806,300,822],garden:[[70,826],[620,826]],
   customers:[[200,708],[330,702],[460,708],[250,776]],event:[375,792],officer:[600,735],
   staff:{x:175,step:95,y:536},cat:[566,338],counterSpan:[110,520],
   decor:{corner:[92,690],front:[420,815],center:[330,760]},sill:{plant:[500,336],lamp:[528,336],seat:[618,336],rug:[330,745]},
   wall:{poster:[85,300]},badge:{workbench:[0,-10],board:[-50,-6],'ops:finance':[0,-12]},
   spots:{'go:bakery':[[80,460],36,[[140,574]]],shelf:[[205,586],58,[[205,574]]],evidence:[[436,350],40,[[430,574]]],workbench:[[270,440],70,[[290,574]]],counter:[[470,586],50,[[470,574]]],
     warehouse:[[82,545],45,[[80,676],[140,574]]],board:[[603,395],42,[[548,574]]],finance:[[622,522],38,[[548,574],[615,592]]],
     property:[[508,400],30,[[508,574]]],security:[[90,236],30,[[140,574]]],door:[[530,798],45,[[440,786],[530,776]]],pet:[[566,318],36,[[548,574]]]}},
};

/* ------------------------------------------------------------ Palette & helpers */
const WALL='#fbf2e4',TILE='#fffdf8',GROUT='#e9e0d2',COFFEE='#6b4430',COFFEE_D='#4b2f22',MOCHA='#8a5a3c',
  WOOD='#c98f5f',WOOD_L='#e4b68a',WOOD_D='#9c6a45',CRUST='#d89a4c',CRUST_D='#b8773a',CRUST_L='#efc27d',
  BRICK='#d68d66',BRICK_D='#b9714c',STEEL='#dfe3e2',STEEL_D='#98a1a2',SLATE='#3b3835',CHALK='#f6f0e3',CHALK_Y='#f3d88f',CHALK_P='#f2b8ae',
  CREAM='#fff8ec',SAGE='#b7cdab',SAGE_D='#8fb08a',BERRY='#e0697a',SHADOW='#6b44301f';
/** Draw `fn` with the origin at (x,y) scaled by s. */
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
const clip=(c,x,y,w,h,r,fn)=>{c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();fn();c.restore();};
const now=w=>w.reduced?0:w.time;

/* ------------------------------------------------------------ Bakes & cups */
function croissant(c,x,y,s=1){E(c,x-12*s,y+2*s,5*s,3.6*s,CRUST_D);E(c,x+12*s,y+2*s,5*s,3.6*s,CRUST_D);E(c,x-6.5*s,y-1*s,7*s,5.6*s,CRUST);E(c,x+6.5*s,y-1*s,7*s,5.6*s,CRUST);
  E(c,x,y-3*s,7.5*s,7*s,CRUST_L);L(c,x-3.5*s,y-8*s,x-4.5*s,y+2*s,CRUST_D,1.2*s);L(c,x+3.5*s,y-8*s,x+4.5*s,y+2*s,CRUST_D,1.2*s);E(c,x-2*s,y-6*s,2.6*s,1.4*s,'#fff2d0');}
function baguette(c,x,y,len,ang,s=1){c.save();c.translate(x,y);c.rotate(ang);R(c,-len/2,-5*s,len,10*s,CRUST,5*s);R(c,-len/2+3*s,-4*s,len-6*s,3.5*s,CRUST_L,2*s);
  for(let i=-2;i<=2;i++)L(c,i*len/6-4*s,-2.5*s,i*len/6+4*s,2.5*s,'#f7dcaa',1.4*s);c.restore();}
function boule(c,x,y,r){E(c,x,y,r,r*.72,CRUST_D);E(c,x,y-r*.08,r*.92,r*.62,CRUST);const lw=Math.max(1,r*.12);
  L(c,x-r*.5,y-r*.32,x+r*.5,y+r*.12,'#f4d8a8',lw);L(c,x-r*.5,y+r*.12,x+r*.5,y-r*.32,'#f4d8a8',lw);E(c,x-r*.42,y-r*.36,r*.2,r*.1,'#fff4de');}
function bun(c,x,y,r){E(c,x,y,r,r*.7,CRUST_D);E(c,x,y-r*.1,r*.85,r*.55,'#e3a55a');E(c,x-r*.25,y-r*.3,r*.3,r*.15,'#f6cf8e');}
function swirl(c,x,y,r){E(c,x,y,r,r*.7,'#dca368');c.beginPath();for(let a=0;a<Math.PI*5;a+=.3){const q=r*.82*a/(Math.PI*5);c.lineTo(x+Math.cos(a)*q,y+Math.sin(a)*q*.66);}
  c.strokeStyle='#a8662f';c.lineWidth=Math.max(1,r*.12);c.stroke();L(c,x-r*.6,y-r*.25,x+r*.5,y+r*.2,'#fffaf0',Math.max(1,r*.14));}
function painChoc(c,x,y,s){R(c,x-11*s,y-8*s,22*s,12*s,CRUST,4*s);R(c,x-9*s,y-7*s,18*s,3*s,CRUST_L,1.5*s);L(c,x-5*s,y-6*s,x-5*s,y+3*s,COFFEE,2*s);L(c,x+5*s,y-6*s,x+5*s,y+3*s,COFFEE,2*s);}
function slice(c,x,y,s,cream){R(c,x-11*s,y-15*s,22*s,15*s,'#fbe8cf',2*s);L(c,x-11*s,y-10*s,x+11*s,y-10*s,cream,2*s);L(c,x-11*s,y-5*s,x+11*s,y-5*s,cream,2*s);
  R(c,x-12*s,y-19*s,24*s,5*s,cream,2.5*s);E(c,x+4*s,y-21*s,3.6*s,3.2*s,BERRY);E(c,x+3*s,y-24*s,1.6*s,1.2*s,'#8fb08a');}
function tart(c,x,y,s){E(c,x,y-3*s,12*s,5*s,CRUST_D);E(c,x,y-5*s,11*s,4*s,CRUST);E(c,x,y-6*s,8.5*s,2.8*s,'#fbe3a4');for(const [dx,col] of [[-4,BERRY],[1,'#8c6fd0'],[5,BERRY]])E(c,x+dx*s,y-7*s,2.2*s,2*s,col);}
function miniCake(c,x,y,s,col){R(c,x-12*s,y-20*s,24*s,20*s,col,5*s);R(c,x-12*s,y-22*s,24*s,6*s,'#fffaf3',3*s);for(let i=-1;i<=1;i++)E(c,x+i*8*s,y-16*s,3*s,3.5*s,'#fffaf3');E(c,x,y-25*s,3.2*s,3*s,BERRY);}
/** Cup on a saucer with latte art (or a small espresso cup). */
function cup(c,x,y,s=1,col=CREAM){E(c,x,y,13*s,3.4*s,'#efe4d4');c.beginPath();c.arc(x+8*s,y-7*s,4*s,-Math.PI/2,Math.PI/2);c.strokeStyle=col;c.lineWidth=2.2*s;c.stroke();
  P(c,[[x-9*s,y-13*s],[x+9*s,y-13*s],[x+7*s,y-1*s],[x-7*s,y-1*s]],col);E(c,x,y-13*s,9*s,2.6*s,'#c99a6e');heart(c,x,y-12.4*s,.14*s,'#fff4e2');}
function plate(c,x,y,s){E(c,x,y,15*s,4*s,'#fffaf3');E(c,x,y+1*s,15*s,3*s,'#e8dccb');croissant(c,x,y-4*s,.72*s);}
/** Wicker basket front. */
function basket(c,x,y,w,h){R(c,x,y,w,h,'#c9975a',5);clip(c,x,y,w,h,5,()=>{for(let i=x-h;i<x+w;i+=7){L(c,i,y+h,i+h,y,'#b2804a',1.2);L(c,i,y,i+h,y+h,'#dcae72',1);}});R(c,x-2,y-2,w+4,5,'#b7854c',3);}

/* ------------------------------------------------------------ Wall pieces */
function floorPlanks(c,x,y,w,h,r){clip(c,x,y,w,h,r,()=>{const bh=28;
  for(let row=0;y+row*bh<y+h;row++){const yy=y+row*bh;c.fillStyle=row%2?'#ecd1a8':'#e7c99c';c.fillRect(x,yy,w,bh);L(c,x,yy,x+w,yy,'#d8b385',1.5);
    for(let xx=x+(row*97)%180-180;xx<x+w;xx+=180){L(c,xx,yy+3,xx,yy+bh-3,'#d4ad7c',1.6);E(c,xx+60,yy+bh/2,6,2,'#dfbb8d');}}});}
function subway(c,x,y,w,h){R(c,x,y,w,h,TILE,0);clip(c,x,y,w,h,0,()=>{const bw=34,bh=15;for(let r=0;y+r*bh<y+h;r++){const yy=y+r*bh;L(c,x,yy,x+w,yy,GROUT,1.3);
  for(let xx=x+(r%2?-bw/2:0);xx<x+w;xx+=bw)L(c,xx,yy,xx,yy+bh,GROUT,1.3);}});}
/** Brick-arched deck oven with two glowing decks (local, feet at 0). */
function deckOven(c,t){const g=.82+.18*Math.sin(t*2.2);
  R(c,-92,-226,184,226,BRICK,[84,84,4,4]);
  clip(c,-92,-226,184,226,[84,84,4,4],()=>{for(let r=0;r<15;r++){const yy=-226+r*16;L(c,-92,yy,92,yy,BRICK_D,1.4);for(let xx=-92+(r%2?16:0);xx<92;xx+=32)L(c,xx,yy,xx,yy+16,BRICK_D,1.4);}});
  R(c,-12,-226,24,14,'#e7a57f',4,BRICK_D,1.5);
  // warm halo around the doors
  const halo=c.createRadialGradient(0,-100,10,0,-100,120);halo.addColorStop(0,`rgba(255,184,92,${.34*g})`);halo.addColorStop(1,'rgba(255,184,92,0)');c.fillStyle=halo;c.fillRect(-120,-220,240,220);
  R(c,-74,-180,148,176,STEEL,10,STEEL_D,2);
  R(c,-66,-174,132,22,'#cdd3d2',5);R(c,-60,-169,36,12,'#3c3a38',3);T(c,'220°',-42,-163,9,'#ffb35c',800);for(const dx of [16,34,52]){E(c,dx,-163,5.5,5.5,'#fbfbf8');L(c,dx,-163,dx+3,-167,'#6f7778',1.5);}
  for(const [k,y0] of [[0,-146],[1,-98]]){R(c,-66,y0,132,44,'#767b7c',7);
    const glow=c.createLinearGradient(0,y0+6,0,y0+34);glow.addColorStop(0,'#ffcf78');glow.addColorStop(1,'#ff9b45');R(c,-58,y0+6,116,26,glow,5);
    if(k===0){boule(c,-30,y0+26,13);boule(c,2,y0+26,13);boule(c,34,y0+26,13);}else{baguette(c,-22,y0+24,56,-.06,.9);baguette(c,26,y0+25,56,.05,.9);}
    R(c,-58,y0+6,116,26,`rgba(255,238,200,${.18*(1-g)+.05})`,5);L(c,-52,y0+38,52,y0+38,'#e3e7e6',4);}
  R(c,-74,-50,148,44,'#c9905f',6,WOOD_D,1.5);L(c,0,-48,0,-8,WOOD_D,1.5);L(c,-22,-28,-10,-28,'#f3dcc0',3);L(c,10,-28,22,-28,'#f3dcc0',3);
  R(c,-70,-6,8,6,'#6f7778',2);R(c,62,-6,8,6,'#6f7778',2);
  // wooden peel leaning on the arch
  L(c,84,-4,96,-120,WOOD_D,5);E(c,99,-146,13,28,WOOD_L);L(c,99,-122,99,-170,'#d9a676',1.2);}
function breadRack(c,x,y,w,h){R(c,x,y,w,h,WOOD_D,8);R(c,x+5,y+5,w-10,h-10,'#f3e0c4',5);const rows=3,gap=(h-10)/rows;
  for(let r=0;r<rows;r++){const base=y+5+gap*(r+1)-2;R(c,x+2,base-3,w-4,7,WOOD,2);
    if(r===0){basket(c,x+10,base-18,w*.44,16);for(let i=0;i<4;i++)baguette(c,x+16+i*8,base-30,40,-1.15+i*.12,.8);boule(c,x+w*.74,base-9,11);}
    else if(r===1){for(let i=0;i<3;i++)boule(c,x+18+i*(w-36)/2,base-8,10);}
    else{basket(c,x+8,base-12,w-16,10);for(let i=0;i<4;i++)croissant(c,x+20+i*(w-40)/3,base-14,.72);}}}
/** Coffee menu in chalk. `big` (landscape) lists drinks and bakes. */
function chalkboard(c,x,y,w,h,big){R(c,x-7,y-7,w+14,h+14,WOOD_D,10);R(c,x,y,w,h,SLATE,5);E(c,x+w*.3,y+h*.6,w*.22,h*.3,'#ffffff08');E(c,x+w*.78,y+h*.3,w*.16,h*.26,'#ffffff07');
  const head='MENU HÔM NAY';T(c,head,x+w/2,y+(big?15:20),fit(c,head,w-60,big?14:18,800),CHALK,800);
  c.setLineDash([4,5]);L(c,x+16,y+(big?27:36),x+w-16,y+(big?27:36),'#f6f0e370',1.2);c.setLineDash([]);
  const cupD=(cx,cy,s)=>{c.strokeStyle=CHALK;c.lineWidth=1.8;c.beginPath();c.moveTo(cx-9*s,cy-8*s);c.lineTo(cx-7*s,cy+6*s);c.lineTo(cx+7*s,cy+6*s);c.lineTo(cx+9*s,cy-8*s);c.stroke();
    c.beginPath();c.arc(cx+10*s,cy-2*s,4*s,-Math.PI/2,Math.PI/2);c.stroke();for(const dx of [-3,3]){c.beginPath();c.moveTo(cx+dx*s,cy-11*s);c.quadraticCurveTo(cx+(dx+4)*s,cy-15*s,cx+dx*s,cy-19*s);c.stroke();}};
  const crD=(cx,cy,s)=>{c.strokeStyle=CHALK_Y;c.lineWidth=1.8;c.beginPath();c.moveTo(cx-14*s,cy+3*s);c.quadraticCurveTo(cx,cy-16*s,cx+14*s,cy+3*s);c.quadraticCurveTo(cx,cy-3*s,cx-14*s,cy+3*s);c.stroke();
    for(const dx of [-5,0,5])L(c,cx+dx*s,cy-7*s,cx+dx*1.2*s,cy+1*s,CHALK_Y,1.2);};
  if(big){const col=w/2,rows=[['Espresso','29k'],['Latte','39k'],['Bạc xỉu','35k']],bakes=[['Croissant','25k'],['Bánh mì','15k'],['Bánh kem','45k']];
    cupD(x+22,y+52,.9);crD(x+col+22,y+50,.9);
    rows.forEach(([n,v],i)=>{T(c,n,x+38,y+40+i*17,fit(c,n,col-70,11),CHALK,700,'left');T(c,v,x+col-12,y+40+i*17,10,CHALK_Y,700,'right');});
    bakes.forEach(([n,v],i)=>{T(c,n,x+col+38,y+40+i*17,fit(c,n,col-70,11),CHALK,700,'left');T(c,v,x+w-12,y+40+i*17,10,CHALK_P,700,'right');});
    L(c,x+col,y+34,x+col,y+h-8,'#f6f0e340',1.2);heart(c,x+w-16,y+15,.22,CHALK_P);}
  else{cupD(x+w*.25,y+62,1.2);crD(x+w*.75,y+60,1.2);const a='Cà phê',b='Bánh mì que';
    T(c,a,x+w*.25,y+h-16,fit(c,a,w/2-14,16),CHALK,700);T(c,b,x+w*.75,y+h-16,fit(c,b,w/2-10,16),CHALK_Y,700);}}
/** Bé Men, the sourdough starter jar with a little face (local, feet at 0). */
function beMen(c,t,label){const rise=Math.sin(t*.8)*1.5;R(c,-16,-40,32,40,'#eef6f5',8,'#b9cfcc',1.5);R(c,-13,-24-rise,26,21+rise,'#f1e3c4',6);
  for(const [bx,by,r] of [[-6,-18,2],[5,-12,1.6],[-2,-8,1.3],[7,-21,1.2]])E(c,bx,by-rise*.5,r,r,'#fffaf0');L(c,-16,-28,16,-28,'#e58f7d',2);
  E(c,-5,-15,1.8,2.2,'#5a4035');E(c,5,-15,1.8,2.2,'#5a4035');c.beginPath();c.arc(0,-12,2.6,.1,Math.PI-.1);c.strokeStyle='#5a4035';c.lineWidth=1.3;c.stroke();E(c,-9,-11,2.6,1.6,'#f2a9a0');E(c,9,-11,2.6,1.6,'#f2a9a0');
  R(c,-19,-47,38,9,'#f2c6c0',4);for(let i=-15;i<17;i+=6)E(c,i,-43,1.3,1.3,'#fff6f2');L(c,-17,-40,17,-40,'#b98a73',1.5);
  if(label){L(c,16,-36,22,-30,'#b98a73',1);const tw=Math.max(34,label.w);R(c,20,-32,tw,label.size+6,CREAM,3,'#d1b28f',1);T(c,label.text,20+tw/2,-32+(label.size+6)/2+.5,label.size,COFFEE,800);}}
/** Little paper name tag hanging from a shelf. */
function nameTag(c,x,y,s,size){const tw=56;L(c,x-6,y,x-4,y+3,'#b98a73',1);L(c,x+6,y,x+4,y+3,'#b98a73',1);R(c,x-tw/2,y+3,tw,size+5,CREAM,3,'#d1b28f',1);T(c,s,x,y+3+(size+5)/2+.5,fit(c,s,tw-6,size,800),COFFEE,800);}
function jar(c,x,y,h,fill){R(c,x-9,y-h,18,h,'#eef6f5',5,'#b9cfcc',1.2);R(c,x-7,y-h*.7,14,h*.66,fill,3);R(c,x-10,y-h-4,20,5,WOOD_D,2);}
function ticketRail(c,x,y,w){L(c,x,y,x+w,y,STEEL_D,4);L(c,x,y-1,x+w,y-1,'#f3f5f4',1.2);const n=Math.max(3,Math.floor(w/26));
  for(let i=0;i<n;i++){const tx=x+6+i*(w-12)/n,tw=(w-12)/n-5,th=30-(i%2)*5;R(c,tx,y+2,tw,th,i===1?'#fff3d9':'#fffdf5',2,'#d8cdbd',1);R(c,tx+tw/2-3,y-3,6,6,STEEL_D,1.5);
    for(let l=0;l<3;l++)L(c,tx+4,y+10+l*6,tx+tw-4-(l===2?6:0),y+10+l*6,'#c4b3a0',1.2);if(i===0)L(c,tx+tw-8,y+th-6,tx+tw-4,y+th-2,'#6fae7c',1.6);}}
function espresso(c,p,t){E(c,0,0,62,5,SHADOW);
  R(c,-56,-62,112,58,STEEL,10,STEEL_D,2);R(c,-56,-62,15,58,MOCHA,[10,0,0,10]);R(c,41,-62,15,58,MOCHA,[0,10,10,0]);
  R(c,-50,-70,100,9,'#c9cfce',3);for(let i=0;i<4;i++){R(c,-40+i*22,-82,14,12,'#fffaf3',[2,2,4,4],'#d8cdbd',1);}
  E(c,0,-47,9,9,'#fffdf7');c.beginPath();c.arc(0,-47,9,0,Math.PI*2);c.strokeStyle=STEEL_D;c.lineWidth=1.8;c.stroke();L(c,0,-47,5,-51,'#d9534f',1.6);
  R(c,-17,-31,34,9,CREAM,4);heart(c,0,-26.5,.2,p.primary||MOCHA);
  for(const gx of [-27,27]){R(c,gx-10,-36,20,8,STEEL_D,3);L(c,gx,-28,gx+(gx<0?-22:22),-25,COFFEE_D,5);R(c,gx-4,-27,8,4,'#7d8586',1);
    const flow=(t*3+gx)%1;L(c,gx,-23,gx,-15,'#7a4a2a',1.6);E(c,gx,-15+flow*0,1,1,'#7a4a2a');cup(c,gx,-6,.62,'#fffaf3');}
  R(c,-50,-7,100,6,STEEL_D,2);
  // steam wand and a jug of milk, with steam curling up
  L(c,52,-40,64,-12,STEEL_D,3);R(c,56,-16,16,16,'#e9eeed',[2,2,4,4],STEEL_D,1.2);
  for(let i=0;i<3;i++){const k=((t*.45+i/3)%1),a=Math.max(0,.8*(1-k));c.save();c.globalAlpha=a;E(c,64+Math.sin(t*2+i)*5,-24-k*56,5+k*7,4+k*5,'#e6e0d6');E(c,63+Math.sin(t*2+i)*5,-25-k*56,3+k*5,2.5+k*4,'#fbf8f3');c.restore();}}
function grinder(c){E(c,0,0,18,4,SHADOW);R(c,-13,-40,26,38,COFFEE,6);R(c,-9,-30,18,10,'#f1e3cf',3);R(c,-15,-4,30,5,COFFEE_D,2);
  P(c,[[-15,-68],[15,-68],[8,-42],[-8,-42]],'#e6f2f1');for(let i=0;i<9;i++)E(c,-8+(i%3)*8,-50-Math.floor(i/3)*5,2.6,1.8,'#5a3322');P(c,[[-15,-68],[15,-68],[8,-42],[-8,-42]],'#ffffff33');R(c,-16,-73,32,6,COFFEE_D,3);}
function windowMorning(c,p,x,y,w,h,t){R(c,x-10,y-10,w+20,h+14,WOOD,20);
  clip(c,x,y,w,h,14,()=>{const sky=c.createLinearGradient(0,y,0,y+h);sky.addColorStop(0,'#bfe0ea');sky.addColorStop(.55,'#fde3c3');sky.addColorStop(1,'#ffd6a6');c.fillStyle=sky;c.fillRect(x,y,w,h);
    const sx=x+w*.7,sy=y+h*.62,sun=c.createRadialGradient(sx,sy,6,sx,sy,w*.45);sun.addColorStop(0,'#fff6d2');sun.addColorStop(.25,'#ffe7a8aa');sun.addColorStop(1,'#ffe7a800');c.fillStyle=sun;c.fillRect(x,y,w,h);E(c,sx,sy,w*.1,w*.1,'#fff3c4');
    for(let i=0;i<4;i++){const a=-Math.PI*.95+i*.28+Math.sin(t*.3)*.02;L(c,sx+Math.cos(a)*w*.14,sy+Math.sin(a)*w*.14,sx+Math.cos(a)*w*.24,sy+Math.sin(a)*w*.24,'#fff1c0',3);}
    E(c,x+w*.2,y+h*.22,w*.1,6,'#ffffffb0');E(c,x+w*.28,y+h*.2,w*.08,8,'#ffffffb0');
    // rooftops of the street across
    P(c,[[x,y+h*.78],[x+w*.12,y+h*.66],[x+w*.24,y+h*.78]],'#e3b7a0');R(c,x,y+h*.78,w*.26,h*.3,'#efd0b8',0);
    R(c,x+w*.3,y+h*.7,w*.18,h*.4,'#e9c6ae',0);R(c,x+w*.33,y+h*.75,w*.05,h*.06,'#fff3d2',1);R(c,x+w*.4,y+h*.75,w*.05,h*.06,'#fff3d2',1);
    E(c,x+w*.9,y+h*.86,w*.18,h*.22,SAGE);E(c,x+w*.62,y+h,w*.3,h*.12,'#d9e5bc');});
  L(c,x+w/2,y+3,x+w/2,y+h-2,CREAM,6);L(c,x+3,y+h*.42,x+w-3,y+h*.42,CREAM,6);
  // gingham café curtain on a brass rod
  const cy=y+h*.56;L(c,x-6,cy,x+w+6,cy,'#c9a45a',4);E(c,x-7,cy,4,4,'#c9a45a');E(c,x+w+7,cy,4,4,'#c9a45a');
  for(const [x0,x1] of [[x,x+w*.47],[x+w*.53,x+w]]){R(c,x0,cy+2,x1-x0,h-(cy-y)-4,'#fff6ee',[0,0,8,8]);clip(c,x0,cy+2,x1-x0,h-(cy-y)-4,[0,0,8,8],()=>{
    for(let xx=x0+4;xx<x1;xx+=12)R(c,xx,cy+2,6,h,'#f0b9a455',0);for(let yy=cy+6;yy<y+h;yy+=12)R(c,x0,yy,x1-x0,6,'#f0b9a455',0);});
    for(let xx=x0+6;xx<x1;xx+=12)L(c,xx,cy+4,xx,cy+10,'#e7a48f70',1);}}
function pendant(c,x,y0,y1,t){L(c,x,y0,x,y1,'#7d6a5a',1.6);P(c,[[x-7,y1],[x+7,y1],[x+18,y1+16],[x-18,y1+16]],MOCHA);E(c,x,y1+16,18,4,COFFEE_D);
  const g=c.createRadialGradient(x,y1+20,2,x,y1+20,34);g.addColorStop(0,'#fff2c2cc');g.addColorStop(1,'#fff2c200');c.fillStyle=g;c.fillRect(x-34,y1-8,68,64);E(c,x,y1+19,5,4,'#fff6d6');}
/** Slanting morning light from the window onto the floor. */
function lightBeams(c,beams){c.save();for(const pts of beams){const g=c.createLinearGradient(0,pts[0][1],0,pts[2][1]);g.addColorStop(0,'#fff3c440');g.addColorStop(1,'#fff3c410');c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=g;c.fill();}c.restore();}
/** Framed little bakery house on the wall: the `property` hotspot. */
function plaque(c,p,x,y,w,h){R(c,x,y,w,h,WOOD_D,7);R(c,x+4,y+4,w-8,h-8,CREAM,5);const cx=x+w/2,b=y+h-9,s=w/40;
  P(c,[[cx-14*s,b-14*s],[cx,b-25*s],[cx+14*s,b-14*s]],MOCHA);R(c,cx-11*s,b-15*s,22*s,15*s,'#f3d7b6',2);R(c,cx-3*s,b-9*s,6*s,9*s,COFFEE,2);R(c,cx-10*s,b-17*s,20*s,4*s,'#f0b9a4',1);}
function wheat(c,x,y,s,col=CRUST){L(c,x,y,x,y-26*s,col,1.6*s);for(let i=0;i<4;i++){E(c,x-3.5*s,y-10*s-i*5*s,2.6*s,4*s,col);E(c,x+3.5*s,y-10*s-i*5*s,2.6*s,4*s,col);}E(c,x,y-31*s,2.4*s,4*s,col);}
/** Sign over the landscape room: café board with cup and wheat. */
function cafeSign(c,p,x,y,w,h){L(c,x+60,y-26,x+60,y+4,'#8c7056',3);L(c,x+w-60,y-26,x+w-60,y+4,'#8c7056',3);
  R(c,x-4,y+6,w+8,h,COFFEE_D,28);R(c,x,y,w,h,MOCHA,26);R(c,x+9,y+9,w-18,h-18,'#fbf1e2',20,'#e2c39c',2);
  at(c,x+56,y+h/2+12,1,()=>{cup(c,0,6,1.9,'#fffaf3');for(const dx of [-5,5]){c.beginPath();c.moveTo(dx,-22);c.quadraticCurveTo(dx+6,-30,dx,-38);c.strokeStyle='#d9b98f';c.lineWidth=2.4;c.lineCap='round';c.stroke();}});
  wheat(c,x+w-40,y+h-18,1.25);croissant(c,x+w-66,y+h-28,.9);
  const cx=x+w/2+6;T(c,p.title,cx,y+40,fit(c,p.title,w-190,30,800),COFFEE,800);T(c,p.sub,cx,y+h-25,fit(c,p.sub,w-170,12),'#a0714e');}

/* ------------------------------------------------------------ Floor pieces (local units, origin = middle of the feet line) */
/** Glass pastry case: two tiers of bakes behind curved glass. */
function pastryCase(c,W,s){const x0=-W/2,x1=W/2,top=-124,mid=-88,low=-54;E(c,0,2,W/2+8,7,SHADOW);
  R(c,x0,low,W,54,COFFEE,[0,0,10,10]);for(let i=0;i<3;i++)R(c,x0+10+i*(W-20)/3,low+8,(W-20)/3-8,36,'#7c4f35',5);R(c,x0-3,-3,W+6,5,COFFEE_D,2);
  R(c,x0,top,W,low-top+2,'#fbf1e2',[24,6,0,0],'#b88b64',3);
  const glow=c.createLinearGradient(0,top,0,low);glow.addColorStop(0,'#fff5d8');glow.addColorStop(1,'#f8e9d2');R(c,x0+4,top+4,W-8,low-top-4,glow,[20,4,0,0]);
  L(c,x0+6,mid,x1-6,mid,'#cfe4e2',3);L(c,x0+6,mid+1,x1-6,mid+1,'#ffffff',1);
  const nUp=Math.max(4,Math.floor(W/(40*s))),nLo=Math.max(4,Math.floor(W/(40*s))),cols=['#fbd3dc','#fff3dc','#d9eccd','#f6e1b8'];
  for(let i=0;i<nUp;i++){const x=x0+W*(i+.5)/nUp,y=mid-2;const k=i%4;if(k===0)slice(c,x,y,s,'#f7b8c6');else if(k===1)tart(c,x,y,s);else if(k===2)miniCake(c,x,y,s,cols[(i>>2)%4]);else slice(c,x,y,s,'#b98a6a');}
  for(let i=0;i<nLo;i++){const x=x0+W*(i+.5)/nLo,y=low-4;const k=i%4;if(k===0){croissant(c,x-5*s,y-3*s,.8*s);croissant(c,x+6*s,y-8*s,.7*s);}else if(k===1){baguette(c,x,y-5*s,30*s,-.18,.85*s);baguette(c,x+2*s,y-10*s,30*s,-.3,.8*s);}else if(k===2){painChoc(c,x,y-2*s,s*.9);painChoc(c,x+3*s,y-11*s,s*.85);}else{swirl(c,x,y-5*s,10*s);}}
  for(let i=0;i<nLo;i+=2){const x=x0+W*(i+.5)/nLo;R(c,x-8,low-3,16,7,CREAM,2,'#d8cdbd',1);}
  // glass: soft tint and reflections over everything
  R(c,x0+3,top+3,W-6,low-top-3,'#dff0ef38',[21,4,0,0]);for(const k of [.14,.2,.68])L(c,x0+W*k,top+10,x0+W*k+22,low-8,'#ffffffa0',3);
  R(c,x0-4,top-7,W+8,9,WOOD_L,5,WOOD_D,1.5);}
function register(c,p){P(c,[[-24,0],[24,0],[20,-26],[-20,-26]],'#f4e3c6');R(c,-25,-4,50,6,'#dfc8a3',2);for(let i=0;i<3;i++)for(let j=0;j<3;j++)R(c,-15+i*10,-21+j*6,7,4,'#fffaf0',1.5);
  R(c,-18,-46,36,20,COFFEE,5);R(c,-13,-42,26,10,'#c7e3cf',2);L(c,-8,-37,6,-37,'#6f9f7c',1.6);R(c,16,-44,11,17,'#fffdf5',1,'#d8cdbd',1);L(c,18,-38,25,-38,'#c4b3a0',1);}
function bell(c){E(c,0,-1,11,3,'#b8913f');c.beginPath();c.arc(0,-3,9,Math.PI,0);c.fillStyle='#efc964';c.fill();E(c,-3,-8,2.4,1.6,'#fff3c4');E(c,0,-13,2.2,2.2,'#b8913f');}
function cakeDome(c){L(c,0,0,0,-9,'#e8dccb',4);E(c,0,-10,24,4,'#f5efe6');R(c,-17,-32,34,22,'#fbe0e6',5);R(c,-17,-34,34,7,'#fffaf3',4);for(let i=-2;i<=2;i++)E(c,i*7,-28,2.6,3.4,'#fffaf3');
  for(const dx of [-8,0,8])E(c,dx,-37,3,2.8,BERRY);c.beginPath();c.ellipse(0,-10,26,34,0,Math.PI,0);c.fillStyle='#e6f4f340';c.fill();c.strokeStyle='#bcd5d3';c.lineWidth=2;c.stroke();E(c,0,-45,3.2,3.2,'#bcd5d3');L(c,-16,-30,-10,-38,'#ffffffb0',2.5);}
function tipJar(c){R(c,-9,-24,18,24,'#eef6f5b0',5,'#b9cfcc',1.2);for(const [dx,dy] of [[-3,-5],[3,-7],[0,-10]])E(c,dx,dy,3.4,1.6,'#e0bd62');heart(c,0,-15,.18,'#e7a48f');}
/** Front counter: pastry case (left) and a mocha wood counter with the till. */
function landCounter(w,p){const c=w.ctx,t=now(w);E(c,482,600,266,10,SHADOW);
  at(c,349,598,1,()=>pastryCase(c,246,1.3));
  R(c,470,500,272,98,MOCHA,[0,12,12,0]);for(let x=486;x<740;x+=16)L(c,x,508,x,590,'#7a4d33',1.4);R(c,466,488,280,15,WOOD_L,7,WOOD_D,2);
  R(c,560,524,90,40,'#fbf1e2',16,'#d9b98f',2);at(c,592,556,1,()=>cup(c,0,0,1.1,'#fffaf3'));wheat(c,626,556,.7);
  at(c,520,488,1,()=>cakeDome(c));at(c,574,488,1,()=>tipJar(c));at(c,666,488,1,()=>register(c,p));at(c,722,488,1,()=>bell(c));
  L(c,605,480,618,470,'#e8dccb',3);E(c,611,472,9,3,'#fffaf3');
  counterExtras(w,p,472,488,1);}
function portCounter(w,p){const c=w.ctx;E(c,312,656,226,9,SHADOW);
  at(c,203,654,1,()=>pastryCase(c,208,1.2));
  R(c,305,566,225,88,MOCHA,[0,12,12,0]);for(let x=320;x<528;x+=16)L(c,x,574,x,646,'#7a4d33',1.4);R(c,301,554,233,15,WOOD_L,7,WOOD_D,2);
  at(c,346,554,.95,()=>cakeDome(c));at(c,396,554,1,()=>tipJar(c));at(c,466,554,1,()=>register(c,p));at(c,514,554,1,()=>bell(c));
  R(c,372,596,98,40,'#fbf1e2',16,'#d9b98f',2);at(c,404,628,1,()=>cup(c,0,0,1.1,'#fffaf3'));wheat(c,440,628,.7);
  counterExtras(w,p,307,554,1.2);}
/** Worn equipment and checklist marks shared by both counters. */
function counterExtras(w,p,x,y,s){const c=w.ctx;
  if(w.c?.upgrades?.includes('workbench')){R(c,x+4,y-34,22,28,CREAM,4,'#c7ad90',1.5);L(c,x+9,y-24,x+13,y-20,'#6fae7c',2);L(c,x+13,y-20,x+21,y-28,'#6fae7c',2);L(c,x+9,y-13,x+21,y-13,'#c4b3a0',1.5);}
}
/** "Needs checking" tag hung on the oven arch when the equipment is worn. */
function wornTag(w,x,y,tw,size){const c=w.ctx;if((w.c?.ops?.equipment?.condition??100)>=100)return;const th=size+10;
  L(c,x-tw/2+10,y-12,x-tw/2+16,y,'#b48d64',1.5);L(c,x+tw/2-10,y-12,x+tw/2-16,y,'#b48d64',1.5);R(c,x-tw/2,y,tw,th,'#f7d995',6,'#d3a35c',1.5);T(c,'CẦN KIỂM',x,y+th/2+1,fit(c,'CẦN KIỂM',tw-10,size,800),'#94643d',800);}
function pantry(w,p,ts){const c=w.ctx,words=w.words(),items=w.c?.ops?.security?.items||[];E(c,0,0,42,7,SHADOW);
  R(c,-38,-170,76,168,WOOD_D,9);R(c,-33,-164,66,82,'#e8c9a2',6);L(c,0,-162,0,-84,WOOD_D,2);
  for(const dx of [-17,17]){R(c,dx-12,-156,24,30,'#f8ecd8',4,'#caa57c',1);L(c,dx,-156,dx,-126,'#caa57c',1);L(c,dx-12,-141,dx+12,-141,'#caa57c',1);}
  R(c,-29,-118,58,24,CREAM,7,'#caa57c',1.5);T(c,words.store,0,-106,fit(c,words.store,50,ts,800),COFFEE,800);E(c,-6,-88,2.4,2.4,'#f3dcc0');E(c,6,-88,2.4,2.4,'#f3dcc0');
  R(c,-33,-78,66,72,'#b98559',5);R(c,-33,-44,66,5,WOOD,2);
  // flour sacks, one open with a scoop
  for(const [sx,sy,sw] of [[-16,-48,26],[12,-46,24]]){R(c,sx-sw/2,sy-26,sw,26,'#f3ead8',8,'#d6c6a8',1.2);L(c,sx-sw/2+3,sy-22,sx+sw/2-3,sy-22,'#d6c6a8',1.5);wheat(c,sx,sy-3,.55,'#c9a45a');}
  R(c,-29,-40,58,34,'#f3ead8',10,'#d6c6a8',1.2);E(c,0,-40,26,6,'#fbf8f1');L(c,8,-44,20,-58,WOOD_D,3);E(c,6,-42,6,3,'#c9cfce');
  if(ts<16){const lbl='Bột mì';T(c,lbl,0,-20,fit(c,lbl,50,ts-1),'#a0714e',700);}
  if(items.includes('lock')){R(c,10,-104,16,18,'#d8c596',5,'#a09675',1);c.beginPath();c.arc(18,-104,5,Math.PI,0);c.strokeStyle='#a09675';c.lineWidth=3;c.stroke();}}
function cafeTable(c,p){E(c,0,2,60,7,SHADOW);
  for(const dir of [-1,1]){const cx=dir*44;c.beginPath();c.arc(cx,-44,14,Math.PI*(dir<0?.95:.05),Math.PI*(dir<0?1.9:1.1),dir>0);c.strokeStyle=COFFEE;c.lineWidth=4;c.lineCap='round';c.stroke();
    L(c,cx-dir*2,-40,cx-dir*2,-22,COFFEE,4);E(c,cx,-22,15,5,MOCHA);E(c,cx,-24,13,3.5,'#a8714a');L(c,cx-10,-20,cx-13,0,COFFEE,3);L(c,cx+10,-20,cx+13,0,COFFEE,3);L(c,cx-4,-20,cx-4,-1,COFFEE,3);}
  L(c,0,-2,0,-38,COFFEE_D,5);E(c,0,-2,16,4,COFFEE_D);E(c,0,-42,36,10,'#d9cfc2');E(c,0,-44,34,9,'#f7f3ec');L(c,-18,-46,6,-42,'#e3dbd0',1.2);
  cup(c,-14,-44,.72);plate(c,12,-43,.72);}
function stool(c){E(c,0,1,15,4,SHADOW);L(c,-9,-34,-12,0,COFFEE,3);L(c,9,-34,12,0,COFFEE,3);L(c,0,-34,0,-2,COFFEE,3);c.beginPath();c.ellipse(0,-14,10,3,0,0,Math.PI*2);c.strokeStyle=COFFEE;c.lineWidth=2;c.stroke();
  E(c,0,-36,15,5,MOCHA);E(c,0,-38,14,4,SAGE);}
function financeStand(w,p,ts,wide){const c=w.ctx,words=w.words(),hw=wide/2;E(c,0,2,hw+6,5,SHADOW);R(c,-hw+4,-48,6,48,WOOD_D,2);R(c,hw-10,-48,6,48,WOOD_D,2);
  R(c,-hw,-44,wide,30,'#e8c9a2',6,WOOD_D,1.5);T(c,words.ledger,0,-29,fit(c,words.ledger,wide-10,ts,800),COFFEE,800);R(c,-hw-4,-56,wide+8,12,WOOD_L,5,WOOD_D,1.5);
  P(c,[[-hw+6,-58],[-2,-55],[-2,-67],[-hw+8,-70]],'#fff8e7');P(c,[[hw-6,-58],[2,-55],[2,-67],[hw-8,-70]],'#fffdf5');L(c,0,-55,0,-67,'#c7ad90',1.5);L(c,-hw+10,-63,-6,-61,p.primary,1.5);L(c,6,-61,hw-10,-63,'#c4b3a0',1.5);}
/** Chalk A-frame sign by the door with the open/closed words. */
function aFrame(w,p,ts,open){const c=w.ctx,words=w.words(),s=open?words.open_sign:words.closed_sign;E(c,0,2,50,5,SHADOW);
  L(c,-38,0,-30,-78,WOOD_D,5);L(c,38,0,30,-78,WOOD_D,5);L(c,-34,-30,34,-30,WOOD_D,3);R(c,-44,-84,88,50,WOOD,8);R(c,-39,-79,78,40,SLATE,5);
  T(c,s,0,-64,fit(c,s,70,ts,800),open?CHALK:CHALK_P,800);c.setLineDash([3,4]);L(c,-26,-50,26,-50,'#f6f0e370',1);c.setLineDash([]);heart(c,0,-44,.16,open?CHALK_Y:'#f6f0e390');}
function banquette(c,p,tier){E(c,0,2,62,6,SHADOW);for(const x of [-52,46])R(c,x,-16,6,16,COFFEE,2);R(c,-60,-58,120,28,MOCHA,10);R(c,-55,-54,110,20,SAGE,8);
  R(c,-62,-30,124,14,WOOD,6,WOOD_D,1.5);R(c,-56,-38,54,12,SAGE,6);R(c,2,-38,54,12,SAGE,6);T(c,'ngồi nghỉ nhé',0,-44,fit(c,'ngồi nghỉ nhé',96,11),'#557052',700);
  if(tier==='garden')bloom(c,50,-62,11,'#f2b8ae');}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,t=now(w),words=w.words();
  E(c,605,724,503,30,'#6b443022');R(c,85,165,1030,550,WOOD,35);R(c,96,168,1008,533,CREAM,30,WOOD_D,3);
  R(c,108,179,984,300,WALL,22);clip(c,108,179,984,300,22,()=>{for(let x=130;x<1092;x+=56)for(let y=204;y<300;y+=48)E(c,x+((y/48)%2?28:0),y,2,2,'#e9d6bc');});
  floorPlanks(c,108,445,984,244,16);R(c,108,438,984,10,WOOD_L,3);R(c,108,446,984,3,WOOD_D,1);
  breadRack(c,118,224,108,146);
  at(c,329,452,1,()=>deckOven(c,t));wornTag(w,329,240,110,13);
  // back bar: white subway tiles, the menu, the shelf with Bé Men and the ticket rail
  subway(c,432,292,336,110);R(c,432,288,336,5,WOOD_L,2);
  chalkboard(c,478,184,244,86,true);
  R(c,648,318,114,6,WOOD,2,WOOD_D,1);
  at(c,670,318,.85,()=>beMen(c,t,null));nameTag(c,670,326,'Bé Men',9);jar(c,712,318,26,'#6b4430');jar(c,736,318,22,'#f1e3c4');
  for(let i=0;i<3;i++)R(c,752-i*2,300-i*6,14,6,'#fffaf3',2,'#d8cdbd',1);
  ticketRail(c,648,344,114);
  for(const [hx,col] of [[446,STEEL_D],[458,WOOD_D]])L(c,hx,300,hx,300+10,'#8c7056',1.5);c.beginPath();c.ellipse(446,322,5,10,0,0,Math.PI*2);c.strokeStyle=STEEL_D;c.lineWidth=1.6;c.stroke();L(c,446,310,446,332,STEEL_D,1.2);L(c,458,310,458,340,WOOD_D,3);E(c,458,344,4,5,WOOD_D);
  R(c,428,396,344,12,WOOD_L,5,WOOD_D,1.5);R(c,434,408,332,44,MOCHA,[0,0,4,4]);for(let i=0;i<4;i++){R(c,442+i*82,414,74,32,'#7c4f35',5);L(c,470+i*82,424,488+i*82,424,'#f3dcc0',2.5);}
  at(c,525,396,1,()=>espresso(c,p,t));at(c,604,396,1,()=>grinder(c));
  R(c,640,380,18,16,'#e9eeed',[2,2,4,4],STEEL_D,1.2);at(c,690,396,.9,()=>{R(c,-26,-6,52,6,'#e8dccb',2);croissant(c,-12,-12,.7);croissant(c,12,-12,.7);});at(c,742,396,.9,()=>cup(c,0,0,1));
  // window and its bar
  windowMorning(c,p,796,214,200,178,t);
  R(c,784,404,224,12,WOOD_L,5,WOOD_D,1.5);L(c,800,416,812,436,WOOD_D,3);L(c,992,416,980,436,WOOD_D,3);
  at(c,860,404,1,()=>cup(c,0,0,1));at(c,900,404,1,()=>plate(c,0,0,1));L(c,832,402,832,388,SAGE_D,2);bloom(c,832,384,7,'#f2b8ae');R(c,826,392,12,12,'#eef6f5',3,'#b9cfcc',1);
  plaque(c,p,1010,232,40,44);streetBoard(c,p,1017,300);
  pendant(c,452,179,220,t);pendant(c,770,179,206,t);
  lightBeams(c,[[[806,404],[862,404],[700,684],[590,684]],[[902,404],[968,404],[880,684],[756,684]]]);
  R(c,988,664,94,20,'#e7c3a7',8);for(let i=0;i<5;i++)L(c,998+i*18,667,998+i*18,681,'#d8ad8c',2);
  cafeSign(c,p,370,64,460,98);
  landSecurity(w,p);}
function portRoom(w,p){const c=w.ctx,t=now(w);
  E(c,350,857,324,23,'#6b443022');R(c,22,114,656,738,WOOD,31);R(c,29,117,642,724,CREAM,26,WOOD_D,3);
  R(c,40,139,620,372,WALL,21);clip(c,40,139,620,372,21,()=>{for(let x=60;x<660;x+=52)for(let y=160;y<280;y+=46)E(c,x+((y/46)%2?26:0),y,2,2,'#e9d6bc');});
  floorPlanks(c,40,506,620,323,15);R(c,40,498,620,10,WOOD_L,3);R(c,40,506,620,3,WOOD_D,1);
  breadRack(c,124,190,138,128);
  at(c,193,506,.77,()=>deckOven(c,t));wornTag(w,193,344,124,17);
  subway(c,268,286,210,170);R(c,268,282,210,5,WOOD_L,2);
  chalkboard(c,280,168,188,98,false);
  R(c,370,318,104,6,WOOD,2,WOOD_D,1);at(c,392,318,.95,()=>beMen(c,t,null));jar(c,432,318,24,'#6b4430');jar(c,456,318,20,'#f1e3c4');
  ticketRail(c,396,340,78);
  R(c,264,452,218,12,WOOD_L,5,WOOD_D,1.5);R(c,270,464,206,42,MOCHA,[0,0,4,4]);for(let i=0;i<3;i++){R(c,277+i*67,470,60,30,'#7c4f35',5);L(c,297+i*67,480,317+i*67,480,'#f3dcc0',2.5);}
  at(c,328,452,.92,()=>espresso(c,p,t));at(c,410,452,.92,()=>grinder(c));at(c,452,452,.9,()=>cup(c,0,0,1));
  windowMorning(c,p,488,186,154,142,t);R(c,478,330,174,11,WOOD_L,5,WOOD_D,1.5);
  plaque(c,p,488,378,40,44);streetBoard(c,p,572,356,.92);
  lightBeams(c,[[[496,342],[548,342],[430,828],[340,828]],[[578,342],[634,342],[600,828],[500,828]]]);
  R(c,484,820,112,16,'#e7c3a7',7);
  portSecurity(w,p);}
/** Security gear placed clear of this room's rack, oven and window. */
function landSecurity(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[];
  if(items.includes('camera')){L(c,130,205,144,196,'#b79b85',5);R(c,134,186,39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,168,196,8,9,'#7a8992');E(c,169,196,4,5,'#b4d9df');E(c,140,191,2,2,'#90bd8b');}
  else{R(c,128,188,43,24,CREAM,8,'#d5b59a',1);T(c,'♧',150,200,15,COFFEE);}
  if(items.includes('bell')){L(c,1070,190,1070,205,'#ac8f73',2);P(c,[[1060,222],[1080,222],[1077,209],[1063,209]],'#f0ce85');E(c,1070,224,4,3,'#d4ad64');}
  if(items.includes('light')){const g=c.createRadialGradient(1078,420,0,1078,420,90);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(988,330,180,180);R(c,1065,398,27,36,'#fff0b8',8,'#b69b79',2);L(c,1078,386,1078,398,'#b69b79',3);}}
function portSecurity(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[];
  if(items.includes('camera')){L(c,62,248,79,236,'#b89d84',4);R(c,73,224,39,22,'#f4f1e7',6,'#a5a89e',2);E(c,108,235,7,8,'#7a8992');E(c,109,235,3,4,'#b4d9df');}
  else{R(c,66,222,46,26,CREAM,8,'#d5b59a',1);T(c,'♧',89,235,17,COFFEE);}
  if(items.includes('bell')){L(c,650,176,650,192,'#ad9073',2);P(c,[[640,210],[660,210],[657,196],[643,196]],'#f1d189');E(c,650,212,4,3,'#d3ad67');}
  if(items.includes('light')){const g=c.createRadialGradient(80,420,0,80,420,60);g.addColorStop(0,'#ffe2a56a');g.addColorStop(1,'#ffe2a500');c.fillStyle=g;c.fillRect(20,360,120,120);R(c,68,404,24,30,'#fff0bc',6,'#b89b7e',2);L(c,80,394,80,404,'#b89b7e',3);}}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,pl=PLAN.land,tier=w.c?.ops?.property?.tier||'cozy',open=w.c?.open,out=[];
  out.push([532,()=>at(c,174,532,1,()=>pantry(w,p,13))]);
  out.push([598,()=>landCounter(w,p)]);
  for(const x of [830,898,966])out.push([482,()=>at(c,x,482,1,()=>stool(c))]);
  out.push([628,()=>at(c,884,620,1,()=>cafeTable(c,p))]);
  out.push([584,()=>at(c,1041,584,1,()=>financeStand(w,p,11,58))]);
  out.push([668,()=>at(c,1026,666,1,()=>aFrame(w,p,12,open))]);
  out.push([560,()=>plantAt(c,1076,556,.62)]);
  if(tier!=='cozy')out.push([678,()=>at(c,208,678,1,()=>banquette(c,p,tier))]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+4,()=>plantAt(c,x,y,.6)]);
  return out;}
function portProps(w,p){const c=w.ctx,pl=PLAN.port,tier=w.c?.ops?.property?.tier||'cozy',open=w.c?.open,out=[];
  out.push([600,()=>at(c,82,600,.84,()=>pantry(w,p,20))]);
  out.push([654,()=>portCounter(w,p)]);
  out.push([550,()=>at(c,622,550,1,()=>financeStand(w,p,16,62))]);
  out.push([782,()=>at(c,117,778,.92,()=>cafeTable(c,p))]);
  out.push([820,()=>at(c,532,818,1,()=>aFrame(w,p,17,open))]);
  if(tier!=='cozy')out.push([822,()=>at(c,245,822,.9,()=>banquette(c,p,tier))]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+4,()=>plantAt(c,x,y,.55)]);
  return out;}

/* ------------------------------------------------------------ the bakery (scenes/backroom.js) */
/** Lò bánh: the deck oven, the cooling rack, butter in the fridge, the kneading table, the flour sacks. */
const BAKERY=room({id:'bakery',name:'Lò bánh',icon:'🔥',back:'shop',sign:'LÒ BÁNH SỚM MAI',
  theme:{wall:'#fbf1e2',wallLow:'#f3dfc4',floor:'#e9cfa8',floor2:'#e1c49b',tile:60,rim:'#c99b7d',trim:'#c4946c',ink:'#a0623f',door:'#b97a52'},
  win:{u0:.12,u1:.24,frame:'#f3dfc4'},clock:[.555,.27],
  items:[
    {k:'oven',u:.4,v:.1,w:.22,h:210,fill:['🥖','🥐','🍞'],spot:'look:oven',label:'Lò nướng'},
    {k:'shelf',u:.68,v:.1,w:.14,h:230,col:'#d9b48e',fill:['🥐','🍞','🥯','🧁','🥖'],spot:'shelf',label:'Giá bánh mới ra lò'},
    {k:'fridge',u:.88,v:.1,w:.13,h:220,tag:'BƠ SỮA',top:'#c4946c',fill:['🧈','🥚','🥛','🍓']},
    {k:'table',u:.5,v:.58,w:.3,h:58,col:'#f4efe6',fill:['🥣','🧈','🥚'],spot:'workbench',label:'Bàn nhồi bột'},
    {k:'sacks',u:.18,v:.64,w:.16,h:70,fill:['BỘT MÌ','ĐƯỜNG'],spot:'warehouse',label:'Kho bột'},
  ],
  looks:{oven:()=>'Lò đá nóng hừng hực. Vỏ bánh mì nứt lách tách nghe vui tai.'},
  chat:['Mẻ croissant thứ hai ra lò rồi!','Bé Men hôm nay nở đẹp ghê.','Ai canh giùm lò năm phút nha.'],
});

export default {
  id:'cafe',
  areas:[{id:'shop',name:'Gian bánh',icon:'🥐',main:true},BAKERY],
  areaFor:shopFor('shop'),
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
