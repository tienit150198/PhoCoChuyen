/** Minimart scene kind (grocery): "Tạp Hoá Cô Ba", a corner shop at the
 * mouth of an alley ("tạp hóa đầu hẻm"). Painted cement tiles (gạch bông) on
 * the floor, a mint wainscot, and everything crammed in:
 *   back wall, left → right: a floor-to-ceiling goods shelf (`shelf`) full of
 *   noodle packs, fish sauce, cooking oil, detergent, cans and milk; the
 *   curtained doorway to the back stock (`warehouse`) with the camera sign
 *   above (`security`); the little Thần Tài altar, a tear-off calendar and
 *   strings of snacks and shampoo sachets; a glass-door drinks fridge with
 *   Mướp asleep on top (`pet`); the framed business licence (`property`) and
 *   the street notice board (`board`); the roll-up shutter entrance onto the
 *   alley (`door`), rolled up while open, half down when closed.
 *   floor: the glass display counter with the calculator and cash tray
 *   (`workbench`, "Quầy tính tiền"), candy jars, the credit book "sổ nợ"
 *   (`evidence`) and the red dial scale (`counter`); rice and bean sacks with
 *   scoops, a red plastic stool with a conical hat, a crate of vegetables and
 *   egg trays, and the owner's cash desk with the shop ledger (`finance`).
 * The player works along the lane behind the counter; customers queue in
 * front of it. PLAN schema: see scenes/shop.js.
 *
 * Floor pieces are drawn in local units with their origin at the middle of
 * their feet line and placed with `at(x, y, scale)`. Portrait keeps its
 * text at about 16 scene px and nothing important above y≈150.
 */
import {R,E,L,T,P,fit,heart,bloom,plantAt,streetBoard} from './kit.js';

export const PLAN={
 land:{floor:[130,452,1070,682],lane:505,line:563,home:[600,505],kx:82,ky:45,sway:30,
   blocks:[[300,548,740,588],[146,634,282,666],[286,648,318,664],[798,644,904,668],[962,588,1052,612]],
   bench:[540,662,680,682],garden:[[1062,676],[136,684]],
   customers:[[390,628],[510,634],[630,628],[750,634]],event:[960,656],officer:[220,600],
   staff:{x:440,step:110,y:470},cat:[763,241],counterSpan:[300,760],
   decor:{corner:[1050,530],front:[720,674],center:[460,672]},sill:{plant:[585,380],lamp:[635,380],seat:[682,380],rug:[560,652]},
   badge:{board:[0,-18]},
   spots:{shelf:[[236,320],100,[[236,505]]],evidence:[[540,452],48,[[540,505]]],workbench:[[400,440],56,[[400,505]]],
     counter:[[672,424],55,[[672,505]]],warehouse:[[421,340],48,[[421,505]]],board:[[858,330],45,[[858,505]]],
     finance:[[1007,570],42,[[930,600],[1007,640]]],property:[[859,237],32,[[880,505]]],security:[[421,226],30,[[421,505],[350,505]]],
     door:[[994,360],60,[[994,505],[994,560]]],pet:[[763,222],38,[[763,505]]]}},
 port:{floor:[62,512,638,822],lane:572,line:626,home:[330,572],kx:51,ky:57,sway:24,
   blocks:[[132,610,500,650],[66,760,186,792],[200,778,236,792],[456,776,556,802],[566,684,638,708]],
   bench:[230,796,350,816],garden:[[612,836],[88,836]],
   customers:[[190,700],[310,706],[430,700],[330,764]],event:[100,712],officer:[470,742],
   staff:{x:175,step:95,y:526},cat:[493,269],counterSpan:[132,540],
   decor:{corner:[80,540],front:[612,790],center:[420,812]},sill:{plant:[352,472],lamp:[386,472],seat:[416,472],rug:[330,735]},
   badge:{board:[0,-33]},
   spots:{shelf:[[137,330],90,[[137,572]]],evidence:[[330,528],44,[[330,572]]],workbench:[[212,516],48,[[212,572]]],
     counter:[[452,500],48,[[452,572]]],warehouse:[[278,420],42,[[278,572]]],board:[[384,388],40,[[400,572]]],
     finance:[[602,660],40,[[540,700],[602,736]]],property:[[379,305],30,[[370,572]]],security:[[278,306],26,[[250,572]]],
     door:[[602,400],48,[[602,572],[602,630]]],pet:[[493,250],36,[[493,572]]]}},
};

/* ------------------------------------------------------------ Palette & helpers */
const WOOD='#d9a877',WOOD_L='#f0cfa4',WOOD_D='#b98555',CREAM='#fff8ec',MINT='#d3e9df',MINT_D='#a9cfc1',RED='#e0685a',RED_D='#b8453a',SHADOW='#8b735322';
const PACK=['#ef7a66','#f4c14f','#86c47c','#f59c55','#79aee0','#e98fb3'];
const SNACK=['#f28c5b','#f5c64f','#7fc39b','#ef7a8f','#7ab6e6','#f0a24a'];
/** Draw `fn` with the origin at (x,y) scaled by s. */
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
/** Stable pseudo-random 0..1 for a number (keeps the clutter still between frames). */
const rnd=i=>{const s=Math.sin(i*127.1+311.7)*43758.5453;return s-Math.floor(s);};
const ring=(c,x,y,r,col,lw)=>{c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.strokeStyle=col;c.lineWidth=lw;c.stroke();};

/* ------------------------------------------------------------ Goods (local: x = left edge, base y = 0) */
function noodles(c,x,seed){const n=2+seed%2;for(let k=0;k<n;k++){const y=-11*(k+1),col=PACK[(seed+k*2)%6];R(c,x,y,24,10.5,col,3);R(c,x+2,y+2,20,2.4,'#ffffff70',1);E(c,x+12,y+7,3.6,2,'#fff4d8');}}
function fishSauce(c,x){for(const bx of [x+5,x+16]){R(c,bx-4.5,-25,9,25,'#c9793a',3);R(c,bx-2,-32,4,8,'#c9793a',1);R(c,bx-2.6,-35,5.2,4,'#d9534f',1.5);R(c,bx-4.5,-17,9,8,'#fff1cf',1);L(c,bx-2.5,-23,bx-2.5,-19,'#ffffff80',1.2);}}
function oil(c,x){R(c,x,-31,16,31,'#f6cf52',5);R(c,x+5,-36,6,6,'#5da55a',2);R(c,x+2,-20,12,9,'#fff8e2',2);E(c,x+8,-15.5,3,2,RED);L(c,x+3,-28,x+3,-22,'#ffffff90',1.5);}
function detergent(c,x,seed){const col=['#6aaee6','#ef92b4','#8fd0c0'][seed%3];R(c,x+3,-34,20,7,col,3);R(c,x,-30,26,30,col,7);E(c,x+9,-19,4,4,'#ffffffb0');E(c,x+17,-12,3,3,'#ffffffa0');E(c,x+18,-23,2.4,2.4,'#ffffff90');R(c,x+5,-8,16,4,'#ffffff70',2);}
function cans(c,x,seed){const a=PACK[(seed+1)%6],b=PACK[(seed+4)%6];for(let j=0;j<2;j++){R(c,x+j*13,-14,12,14,a,3);E(c,x+j*13+6,-14,6,1.8,'#e3e7ea');R(c,x+j*13+1,-9,10,4,'#ffffff60',1);}R(c,x+6.5,-28,12,14,b,3);E(c,x+12.5,-28,6,1.8,'#e3e7ea');R(c,x+7.5,-23,10,4,'#ffffff60',1);}
function milk(c,x,seed){for(let j=0;j<2;j++){const bx=x+j*14;P(c,[[bx,-22],[bx+12,-22],[bx+6,-28]],'#eee6d4');R(c,bx,-22,12,22,'#fdfbf3',2,'#d8d0bd',1);R(c,bx,-15,12,6,['#79aee0','#86c47c','#e98fb3'][(seed+j)%3],1);}}
const GOODS=[[24,noodles],[22,fishSauce],[17,oil],[26,detergent],[26,cans],[27,milk]];
/** One crammed shelf row between x0 and x1 (scene px), goods standing on `base`. */
function goodsRow(c,x0,x1,base,s,seed){c.save();c.translate(x0,base);c.scale(s,s);const W=(x1-x0)/s;let x=2;
  for(let i=0;i<40;i++){const k=Math.floor(rnd(seed*31+i)*GOODS.length),pick=[0,1,2,3,4,5].map(j=>GOODS[(k+j)%GOODS.length]).find(([w])=>x+w<=W-2);if(!pick)break;pick[1](c,x,seed+i);x+=pick[0]+2;}c.restore();}

/* ------------------------------------------------------------ Wall pieces */
function wallAndFloor(c,p,x,y,w,wallH,floorY,floorH,tile){
  R(c,x,y,w,wallH,p.wall,22);
  const wy=floorY-70;R(c,x,wy,w,70,MINT,0);L(c,x,wy,x+w,wy,'#ffffffb0',3);for(let xx=x+18;xx<x+w;xx+=36)L(c,xx,wy+6,xx,floorY-4,'#b9d9cd80',1.5);
  c.save();c.beginPath();c.roundRect(x,floorY,w,floorH,15);c.clip();
  for(let j=0;floorY+j*tile<floorY+floorH;j++)for(let i=0;x+i*tile<x+w;i++){const tx=x+i*tile,ty=floorY+j*tile,cx=tx+tile/2,cy=ty+tile/2;
    c.fillStyle=(i+j)%2?'#f8eedd':'#f5e9d5';c.fillRect(tx,ty,tile,tile);
    E(c,cx-tile*.17,cy,tile*.15,tile*.07,'#f1cdb6');E(c,cx+tile*.17,cy,tile*.15,tile*.07,'#f1cdb6');E(c,cx,cy-tile*.17,tile*.07,tile*.15,'#f1cdb6');E(c,cx,cy+tile*.17,tile*.07,tile*.15,'#f1cdb6');E(c,cx,cy,tile*.06,tile*.06,'#f2d08e');}
  for(let j=0;floorY+j*tile<=floorY+floorH;j++)for(let i=0;x+i*tile<=x+w;i++)E(c,x+i*tile,floorY+j*tile,tile*.15,tile*.15,'#d2e7df');
  for(let j=1;floorY+j*tile<floorY+floorH;j++)L(c,x,floorY+j*tile,x+w,floorY+j*tile,'#eadbc4',1);
  for(let i=1;x+i*tile<x+w;i++)L(c,x+i*tile,floorY,x+i*tile,floorY+floorH,'#eadbc4',1);
  c.restore();R(c,x,floorY-6,w,10,'#d9b99a',3);R(c,x,floorY-6,w,3,'#ecd3b8',2);}
/** Floor-to-ceiling goods shelf: the `shelf` hotspot. */
function goodsShelf(c,x,y,w,h,rows,s,seed){
  R(c,x-5,y-5,w+10,h+5,WOOD_D,10);R(c,x,y,w,h,'#f1dcc0',6);const gap=h/rows;
  for(let r=0;r<rows;r++){const base=y+gap*(r+1)-5;R(c,x+2,base-gap+8,w-4,gap-10,'#ead1b2',3);goodsRow(c,x+3,x+w-3,base,s,seed*7+r*13);
    R(c,x-3,base,w+6,8,WOOD,2);R(c,x,base,w,2.5,'#f5dcbc',1);
    for(let t=0;t<3;t++){const tx=x+12+t*(w-40)/2+rnd(seed+r*5+t)*14;R(c,tx,base+1,14*s,6,t%2?'#fff3a6':'#ffffff',1.5,'#e4c77a',.8);}}
  R(c,x-5,y-5,8,h+5,WOOD_D,4);R(c,x+w-3,y-5,8,h+5,WOOD_D,4);}
/** Strings of snack bags and strips of shampoo sachets from a rod. */
function snacks(c,x0,x1,y,len,n,s){L(c,x0-8,y,x1+8,y,'#9b7450',4);E(c,x0-8,y,3,3,'#9b7450');E(c,x1+8,y,3,3,'#9b7450');
  for(let i=0;i<n;i++){const xx=x0+(x1-x0)*(i+.5)/n,l=len*(.82+rnd(i+3)*.18);
    if(i%3===1){const pair=i%2?['#3d3a4a','#e3b44c']:['#e98fb3','#b98ad0'];R(c,xx-7*s,y+3,14*s,l,'#f8f3e6',2);
      for(let k=0;y+6+(k+1)*12*s<y+l;k++)R(c,xx-5.5*s,y+6+k*12*s,11*s,10.5*s,pair[k%2],2);continue;}
    L(c,xx,y,xx,y+l,'#c9b08e',1.2);
    for(let k=0;y+6+(k+1)*21*s<=y+l+4;k++){const by=y+6+k*21*s,col=SNACK[(i*3+k)%6];c.save();c.translate(xx,by);c.rotate((rnd(i*7+k)-.5)*.5);R(c,-9*s,0,18*s,19*s,col,5*s);
      L(c,-7*s,2*s,7*s,2*s,'#ffffffa0',1.4);L(c,-7*s,17*s,7*s,17*s,'#ffffff80',1.4);E(c,0,9.5*s,4.4*s,4.4*s,'#fff6dc');E(c,0,9.5*s,2*s,2*s,col);c.restore();}}}
/** Glass-door drinks fridge; Mướp naps on top. */
function fridge(c,p,x,y,w,h,open){E(c,x+w/2,y+h+1,w/2+6,5,SHADOW);R(c,x,y,w,h,'#f7f5ef',10,'#c7c0b1',2);
  R(c,x+5,y+5,w-10,20,RED,6);T(c,'❄',x+w/2,y+15.5,14,'#fff8ec');E(c,x+16,y+15,3,3,'#ffffff90');E(c,x+w-16,y+15,3,3,'#ffffff90');
  const gx=x+8,gy=y+31,gw=w-16,gh=h-52;R(c,gx,gy,gw,gh,open?'#d7eef3':'#c9dde2',6,'#9cc6d0',2);
  for(let r=0;r<4;r++){const sy=gy+gh*(r+1)/4-3;const n=Math.floor((gw-6)/11);
    for(let i=0;i<n;i++){const bx=gx+8+i*11,col=['#f07b6b','#8fcf85','#f5c35a','#7cb5e8','#c79bdc'][(r*2+i)%5];
      if((r+i)%3){R(c,bx-3.5,sy-18,7,18,col,2);R(c,bx-1.5,sy-22,3,4,col,1);R(c,bx-2,sy-24,4,2.5,'#ffffff',1);R(c,bx-3.5,sy-12,7,4,'#ffffffa0',1);}
      else{R(c,bx-4,sy-12,8,12,col,2);E(c,bx,sy-12,4,1.4,'#e7ecee');}}
    L(c,gx+3,sy,gx+gw-3,sy,'#b8d6de',2);}
  if(open){const g=c.createLinearGradient(gx,gy,gx,gy+gh);g.addColorStop(0,'#ffffff40');g.addColorStop(1,'#ffffff00');c.fillStyle=g;c.fillRect(gx,gy,gw,gh*.4);}
  L(c,gx+10,gy+gh-12,gx+gw-14,gy+18,'#ffffff55',6);L(c,gx+24,gy+gh-8,gx+gw-4,gy+50,'#ffffff35',3);
  R(c,x+w-13,gy+gh*.35,4,gh*.3,'#b3ada1',2);R(c,x+6,y+h-17,w-12,11,'#e9e5dc',3);for(let i=1;i<6;i++)L(c,x+6+(w-12)*i/6,y+h-14,x+6+(w-12)*i/6,y+h-9,'#c9c2b4',1.5);
  heart(c,x+w-20,y+h-26,.22,p.primary);}
/** Curtained doorway to the back stock room: the `warehouse` hotspot. */
function backDoor(c,p,x,y,w,h,words,lock,ts){
  R(c,x-7,y-7,w+14,h+7,WOOD_D,[16,16,0,0]);R(c,x,y,w,h,'#7d604d',[11,11,0,0]);
  // cartons stacked inside
  for(const [bx,by,bw,bh] of [[.08,.62,.42,.38],[.5,.7,.44,.3],[.14,.36,.36,.26],[.52,.46,.36,.24]]){const X=x+w*bx,Y=y+h*by,W=w*bw,H=h*bh;R(c,X,Y,W,H,'#dcb27c',3,'#b88c58',1);L(c,X+W/2,Y+2,X+W/2,Y+H*.4,'#f3e3c2',3);}
  // name plate
  const pw=Math.min(w-10,58*ts/13),py=y+6;R(c,x+w/2-pw/2,py,pw,ts+10,CREAM,5,'#c9a47f',1.5);T(c,words.store,x+w/2,py+ts/2+5,fit(c,words.store,pw-8,ts,800),'#6f5646',800);
  // flowered curtain on a rod, tied back
  const ry=py+ts+16;L(c,x-4,ry,x+w+4,ry,'#9b7450',3);
  const cloth='#f5cfc4',spot='#e98fa6';
  P(c,[[x,ry],[x+w*.44,ry],[x+w*.2,y+h*.56],[x+w*.26,y+h],[x,y+h]],cloth);
  P(c,[[x+w,ry],[x+w*.56,ry],[x+w*.8,y+h*.56],[x+w*.74,y+h],[x+w,y+h]],cloth);
  for(let i=0;i<7;i++){const t=i/6,yy=ry+10+t*(y+h-ry-18);bloom(c,x+w*(.07+.08*(i%2)),yy,4,spot);bloom(c,x+w*(.93-.08*(i%2)),yy,4,i%2?'#f3c35f':spot);}
  R(c,x+w*.14,y+h*.54,w*.14,6,p.primary,3);R(c,x+w*.72,y+h*.54,w*.14,6,p.primary,3);
  if(lock){R(c,x+w+1,y+h*.44,10,10,'#8f8f8f',2);R(c,x+w-1,y+h*.5,14,15,'#d8c596',4,'#a09675',1);c.beginPath();c.arc(x+w+6,y+h*.5,4.5,Math.PI,0);c.strokeStyle='#a09675';c.lineWidth=2.5;c.stroke();}}
/** Little floor altar for Ông Địa & Thần Tài, facing the door. */
function altar(c,x,y,s,t,reduced){c.save();c.translate(x,y);c.scale(s,s);E(c,0,1,26,4,SHADOW);
  R(c,-22,-32,44,32,'#c9463d',4);R(c,-17,-28,34,21,'#8f2f2a',3);P(c,[[-27,-32],[27,-32],[19,-42],[-19,-42]],'#b83a33');R(c,-21,-45,42,4,'#e2b04a',2);
  E(c,-8,-13,6,6,'#f3d27a');E(c,-8,-21,4.4,4.4,'#f8dcc2');E(c,8,-13,6,6,'#e98a5e');E(c,8,-21,4.4,4.4,'#f8dcc2');E(c,-8,-24,4,2,'#3e3a3a');E(c,8,-24,4,2,'#3e3a3a');
  R(c,-24,-4,48,4,'#e2b04a',2);E(c,15,-7,8,2.5,'#fffaf0');E(c,12,-10,3.6,3.6,'#f39a3d');E(c,18,-10,3.6,3.6,'#f39a3d');E(c,15,-13,3.4,3.4,'#f7ad4d');
  R(c,-20,-12,10,8,'#d9b36b',2);for(const dx of [-17,-15,-13]){L(c,dx,-12,dx-1,-30,'#b8453a',1.2);E(c,dx-1,-30,1.3,1.3,'#ffb347');}
  const k=reduced?0:t;c.strokeStyle='#d8d0c888';c.lineWidth=1.3;c.beginPath();c.moveTo(-16,-32);for(let i=1;i<6;i++)c.lineTo(-16+Math.sin(k*1.4+i)*3,-32-i*5);c.stroke();c.restore();}
/** Tear-off calendar showing today's in-game day. */
function calendar(c,x,y,w,h,day){L(c,x+w/2,y-6,x+w/2,y,'#9b7450',2);E(c,x+w/2,y-7,2.4,2.4,'#9b7450');R(c,x,y,w,h,'#fffdf6',4,'#d6c7ae',1.5);R(c,x,y,w,h*.26,RED,[4,4,0,0]);
  L(c,x+8,y+h*.13,x+w-8,y+h*.13,'#ffe6d8',2);T(c,String(day),x+w/2,y+h*.6,Math.round(h*.4),'#d0473d',800);L(c,x+10,y+h*.88,x+w-10,y+h*.88,'#d9cbb5',1.5);}
/** Framed business licence: the `property` hotspot. */
function licence(c,p,x,y,w,h){R(c,x,y,w,h,'#c89f7f',5);R(c,x+4,y+4,w-8,h-8,'#fffaf0',3);const cx=x+w/2;
  L(c,cx-w*.26,y+h*.26,cx+w*.26,y+h*.26,p.primary,2.2);for(let i=0;i<3;i++)L(c,x+10,y+h*(.44+i*.13),x+w-(i===2?w*.45:10),y+h*(.44+i*.13),'#cdbfae',1.4);
  ring(c,x+w*.72,y+h*.72,Math.min(w,h)*.13,'#d9534f',2);E(c,x+w*.72,y+h*.72,Math.min(w,h)*.05,Math.min(w,h)*.05,'#d9534f');}
/** Wall ledge with a thermos and a teapot (the "by the window" decor spot). */
function ledge(c,x,y,w,busy){R(c,x,y,w,8,WOOD,3,WOOD_D,1.2);P(c,[[x+8,y+8],[x+20,y+8],[x+8,y+22]],WOOD_D);P(c,[[x+w-8,y+8],[x+w-20,y+8],[x+w-8,y+22]],WOOD_D);
  if(busy)return;R(c,x+10,y-34,15,34,'#e98a7a',6);R(c,x+12,y-40,11,7,'#cfd6da',2);R(c,x+13,y-26,9,10,'#fff3e6',3);
  E(c,x+w-26,y-11,14,11,'#f3f0e6');R(c,x+w-31,y-26,10,5,'#f3f0e6',2);L(c,x+w-13,y-12,x+w-5,y-20,'#f3f0e6',3.5);c.beginPath();c.arc(x+w-28,y-15,8,Math.PI*1.05,Math.PI*1.95);c.strokeStyle='#b9a58f';c.lineWidth=2;c.stroke();
  E(c,x+w/2,y-5,6,5,'#f3f0e6');E(c,x+w/2,y-8,4,1.5,'#d8b770');}
/** Roll-up shutter entrance onto the alley: the `door` hotspot. */
function entrance(c,p,x,y,w,h,open,words,ts){
  c.save();c.beginPath();c.roundRect(x,y,w,h,[6,6,0,0]);c.clip();
  R(c,x,y,w,h,'#d6eef3',0);R(c,x,y+h*.2,w,h*.64,'#f7e3b0',0);R(c,x,y+h*.2,w,5,'#e8cf96',0);
  const wx=x+w*.14,wy=y+h*.32,ww=w*.34,wh=h*.2;R(c,wx,wy,ww,wh,'#b9dcd6',3,'#8cc0b0',2);L(c,wx+ww/2,wy,wx+ww/2,wy+wh,'#8cc0b0',2);R(c,wx-6,wy,6,wh,'#7fb3a2',2);R(c,wx+ww,wy,6,wh,'#7fb3a2',2);
  for(let i=0;i<9;i++){E(c,x+w*(.62+rnd(i)*.4),y+h*(.2+rnd(i+9)*.16),7,6,i%3?'#ef8fb6':'#f6a9c9');if(i%2)E(c,x+w*(.6+rnd(i+20)*.4),y+h*(.24+rnd(i+30)*.14),6,4,'#8fc28a');}
  c.strokeStyle='#6f6a6a';c.lineWidth=1.3;for(const k of [0,1]){c.beginPath();c.moveTo(x,y+h*(.08+k*.05));c.quadraticCurveTo(x+w/2,y+h*(.16+k*.05),x+w,y+h*(.07+k*.05));c.stroke();}
  R(c,x,y+h*.84,w,h*.16,'#dcd3c5',0);L(c,x,y+h*.84,x+w,y+h*.84,'#c9bfae',2);
  // parked scooter and a pot of flowers on the pavement
  const mx=x+w*.62,my=y+h*.95,ms=Math.min(1.2,w/150);
  ring(c,mx-24*ms,my-8*ms,8*ms,'#5e5a5a',4*ms);ring(c,mx+24*ms,my-8*ms,8*ms,'#5e5a5a',4*ms);
  P(c,[[mx-30*ms,my-12*ms],[mx+16*ms,my-12*ms],[mx+26*ms,my-30*ms],[mx+8*ms,my-24*ms],[mx-22*ms,my-26*ms]],'#8fb8d8');R(c,mx-24*ms,my-32*ms,26*ms,7*ms,'#6d5a52',3);
  L(c,mx+22*ms,my-28*ms,mx+18*ms,my-48*ms,'#7b8a90',3*ms);L(c,mx+12*ms,my-48*ms,mx+26*ms,my-48*ms,'#5e5a5a',3*ms);E(c,mx+27*ms,my-36*ms,4*ms,4*ms,'#fff3b0');
  R(c,x+8,y+h*.86,20,18,'#d98e6e',4);E(c,x+18,y+h*.86,12,7,'#86c07a');bloom(c,x+14,y+h*.84,4,'#f3c35f');
  c.restore();
  // rails, shutter and drum
  R(c,x-9,y-4,11,h+4,'#aebbc1',3);R(c,x+w-2,y-4,11,h+4,'#aebbc1',3);
  const down=open?16:h*.58;R(c,x,y+14,w,down,'#c9d3d8',0);for(let yy=y+19;yy<y+14+down-4;yy+=7)L(c,x,yy,x+w,yy,'#aab7bd',1.5);
  R(c,x-3,y+10+down,w+6,8,'#93a2a8',3);R(c,x+w/2-12,y+13+down,24,5,'#7d8b91',2);
  R(c,x-13,y-6,w+26,24,'#b7c3c8',10,'#93a2a8',1.5);L(c,x-6,y,x+w+6,y,'#d6dee1',2);
  R(c,x-8,y+h-4,w+16,8,'#cdbba5',3);
  // open / closed board
  const s=open?words.open_sign:words.closed_sign,bw=Math.min(w-8,Math.max(96,ts*7.2)),bh=ts+16,bx=x+w/2-bw/2,by=open?y+h*.46:y+14+down-bh-18;
  L(c,bx+14,by-12,bx+bw/2,by-24,'#9b7450',1.5);L(c,bx+bw-14,by-12,bx+bw/2,by-24,'#9b7450',1.5);E(c,bx+bw/2,by-24,2.4,2.4,'#9b7450');
  R(c,bx,by-12,bw,bh,open?'#fff8e8':'#fdebd6',9,open?'#6fae7c':'#c6a182',2);T(c,s,bx+bw/2,by-12+bh/2+1,fit(c,s,bw-12,ts,800),open?'#3f7a4b':p.dark,800);}
/** A bunch of bananas hanging from a hook. */
function bananas(c,x,y,s){L(c,x,y,x,y+10*s,'#9b7450',1.5);E(c,x,y,2.4,2.4,'#9b7450');R(c,x-2.5*s,y+8*s,5*s,9*s,'#8a6d3b',2);
  for(const [dx,dy,rot,col] of [[-9,30,-1.2,'#eec446'],[9,30,-1.95,'#eec446'],[-5,36,-1.4,'#f5d45a'],[5,36,-1.75,'#f5d45a']]){c.save();c.translate(x+dx*s*.2,y+16*s);c.rotate(rot);c.scale(s,s);
    c.beginPath();c.moveTo(0,0);c.quadraticCurveTo(14,dx>0?-12:12,30,dx>0?-4:4);c.quadraticCurveTo(14,dx>0?-4:4,0,0);c.fillStyle=col;c.fill();c.strokeStyle='#d7a93a';c.lineWidth=1;c.stroke();
    E(c,30,dx>0?-4:4,1.8,1.8,'#6b5a3a');c.restore();}}
/** Security gear: camera (or the neighbourhood-watch sign), door bell, porch light. */
function security(c,p,items,cam,bell,light){const [x,y]=cam;
  if(items.includes('camera')){L(c,x-24,y+8,x-14,y+2,'#b79b85',4);R(c,x-18,y-10,38,20,'#f5f2eb',7,'#a7aaa2',2);E(c,x+15,y,7,8,'#7a8992');E(c,x+16,y,3,4,'#b4d9df');E(c,x-12,y-5,2,2,'#90bd8b');}
  else{R(c,x-21,y-12,42,24,'#fff6e9',8,'#d5b59a',1);T(c,'♧',x,y,15,p.dark);}
  if(items.includes('bell')){const [bx,by]=bell;L(c,bx,by,bx,by+12,'#ac8f73',2);P(c,[[bx-10,by+28],[bx+10,by+28],[bx+7,by+14],[bx-7,by+14]],'#f0ce85');E(c,bx,by+30,4,3,'#d4ad64');}
  if(items.includes('light')){const [lx,ly]=light,g=c.createRadialGradient(lx,ly+10,0,lx,ly+10,80);g.addColorStop(0,'#ffe1a45a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(lx-80,ly-70,160,160);R(c,lx-12,ly-6,24,14,'#fff0b8',6,'#b69b79',2);}}
/** Retro tin shop sign (landscape only; portrait hides the top under the title card). */
function tinSign(c,p,x,y,w,h){L(c,x+40,y+h,x+40,y+h+14,'#9b7450',4);L(c,x+w-40,y+h,x+w-40,y+h+14,'#9b7450',4);
  R(c,x-4,y+7,w+8,h,'#00000018',16);R(c,x,y,w,h,p.primary,14,'#fff4e0',4);c.setLineDash([6,5]);R(c,x+9,y+9,w-18,h-18,'#00000000',9,'#ffe9c4aa',1.6);c.setLineDash([]);
  for(const [rx,ry] of [[x+16,y+16],[x+w-16,y+16],[x+16,y+h-16],[x+w-16,y+h-16]])E(c,rx,ry,3,3,'#ffe9c4');
  // basket icon and heart
  const bx=x+56,by=y+h/2+4;c.beginPath();c.arc(bx,by-8,13,Math.PI,0);c.strokeStyle='#fff8ec';c.lineWidth=3.5;c.stroke();P(c,[[bx-20,by-8],[bx+20,by-8],[bx+14,by+14],[bx-14,by+14]],'#fff8ec');
  E(c,bx-6,by-12,5,5,'#86c47c');E(c,bx+5,by-13,5,5,'#ef7a66');for(let i=0;i<3;i++)L(c,bx-10+i*10,by-3,bx-8+i*8,by+10,p.primary,2);
  heart(c,x+w-52,y+h/2+6,.5,'#fff8ec');
  const cx=x+w/2+6;T(c,p.title,cx,y+h*.42,fit(c,p.title,w-150,34,800),'#fff8ec',800);T(c,p.sub,cx,y+h*.76,fit(c,p.sub,w-150,13),'#ffe9c4');}

/* ------------------------------------------------------------ Floor pieces (local units, origin = middle of the feet line) */
/** Glass display counter; its top surface is at y = -114. */
function glassCounter(c,p,hw){E(c,0,3,hw+14,9,SHADOW);
  R(c,-hw,-38,hw*2,36,'#c98f5c',8,'#a8744a',2);for(let x=-hw+60;x<hw-20;x+=70)L(c,x,-32,x,-8,'#b17d51',2);R(c,-hw+8,-6,14,6,'#8f6340',2);R(c,hw-22,-6,14,6,'#8f6340',2);
  R(c,-hw+4,-102,hw*2-8,66,'#e3f3f2',6,'#9cc7c4',2);
  goodsRow(c,-hw+10,hw-10,-72,.7,5);L(c,-hw+8,-71,hw-8,-71,'#b9dad8',2);goodsRow(c,-hw+10,hw-10,-41,.7,9);
  for(const x of [-hw+34,-hw*.2,hw*.5])L(c,x,-44,x+34,-98,'#ffffff80',5);
  R(c,-hw-8,-114,hw*2+16,16,WOOD_L,7,WOOD_D,2);L(c,-hw-2,-110,hw+2,-110,'#fbe6c8',2);
  R(c,-hw+10,-30,hw*2-20,5,p.primary+'66',2);}
function calculator(c){R(c,-18,-30,36,30,'#f3efe6',5,'#a89d8c',1.5);R(c,-14,-26,28,8,'#cfe0c2',2);T(c,'88',4,-22,7,'#4e5a48',800);
  for(let r=0;r<2;r++)for(let i=0;i<4;i++)R(c,-13+i*7,-15+r*7,5,5,i===3&&r===1?'#f59c55':'#ddd6c9',1.5);}
/** Calculator and cash tray: the `workbench` (Quầy tính tiền). */
function till(c,p){calculator(c);R(c,22,-18,42,18,'#7e98a3',4,'#5f7883',1.5);R(c,26,-25,15,8,'#9fd29a',1);R(c,38,-24,15,8,'#f0a7b8',1);R(c,50,-23,11,7,'#c4e0f0',1);
  for(let i=0;i<4;i++)E(c,28+i*9,-14,3.4,1.6,'#d9dfe2');}
function qrStand(c,p){R(c,-3,-6,6,6,'#b9ab98',1);R(c,-14,-40,28,35,'#fffdf8',4,'#c9bfae',1.2);R(c,-14,-12,28,7,p.primary,[0,0,4,4]);
  for(let r=0;r<7;r++)for(let i=0;i<7;i++){const corner=(r<3&&i<3)||(r<3&&i>3)||(r>3&&i<3);if(!corner&&rnd(r*7+i+2)>.5)R(c,-10+i*3,-36+r*3,2.6,2.6,'#3d3a4a',.4);}
  for(const [fx,fy] of [[-10,-36],[2,-36],[-10,-24]]){R(c,fx,fy,8,8,'#3d3a4a',1.5);R(c,fx+2,fy+2,4,4,'#fffdf8',.5);R(c,fx+3,fy+3,2,2,'#3d3a4a',.3);}}
function jar(c,x,col){R(c,x-12,-28,24,28,'#eaf6f6d0',8,'#a9cccc',1.5);R(c,x-10,-34,20,7,col,3);for(let i=0;i<9;i++)E(c,x-7+(i%3)*7,-6-Math.floor(i/3)*7,3.2,3.2,SNACK[(i+col.length)%6]);L(c,x-8,-24,x-8,-12,'#ffffffb0',2);}
/** The credit book "sổ nợ": the `evidence` hotspot. */
function debtBook(c,ts){c.save();c.rotate(-.05);R(c,-40,-8,80,8,'#fffaf0',2,'#d6c7ae',1);R(c,-42,-30,84,24,'#4f8a86',5,'#35635f',1.5);
  const s='Sổ ghi nợ';R(c,-32,-26,64,15,'#fffaf0',3);T(c,s,0,-18.5,fit(c,s,58,ts,800),'#35635f',800);
  L(c,34,-30,35,-6,'#e98fb3',2.5);L(c,-8,-35,34,-39,'#3e6fb0',3.5);L(c,34,-39,39,-39.5,'#f0ce85',3.5);c.restore();}
/** Red dial scale with a pan of vegetables: the `counter` hotspot. */
function dialScale(c,p){P(c,[[-24,0],[24,0],[19,-32],[-19,-32]],RED);R(c,-27,-4,54,6,RED_D,2);
  E(c,0,-46,22,22,'#fbf7ee');ring(c,0,-46,22,RED_D,3.5);for(let i=0;i<12;i++){const a=-Math.PI*.8+i*Math.PI*1.6/11;L(c,Math.sin(a)*15,-46-Math.cos(a)*15,Math.sin(a)*18,-46-Math.cos(a)*18,'#8a7f73',1.3);}
  L(c,0,-46,Math.sin(.7)*15,-46-Math.cos(.7)*15,'#d9534f',2.2);E(c,0,-46,2.6,2.6,'#555');
  R(c,-3,-76,6,8,'#b3ada1',2);E(c,0,-76,32,6,'#dfe4e6');c.beginPath();c.ellipse(0,-76,32,6,0,0,Math.PI*2);c.strokeStyle='#b3bcc1';c.lineWidth=1.5;c.stroke();
  E(c,-12,-84,10,6,'#86c47c');E(c,-16,-88,6,4,'#6aa84f');E(c,6,-83,6.5,6.5,'#e8604f');E(c,16,-82,5.5,5.5,'#ef7a66');E(c,4,-85,1.6,1.2,'#6aa84f');
}
/** Things on the counter top at scene coordinates (top surface y = ty). */
function counterTop(w,p,c,x,ty,s,ts){const worn=(w.c?.ops?.equipment?.condition??100)<100,check=w.c?.upgrades?.includes('workbench');
  at(c,x.qr,ty,s,()=>qrStand(c,p));
  at(c,x.till,ty,s,()=>{till(c,p);if(check){R(c,-44,-26,20,24,CREAM,4,'#c7ad90',1.2);L(c,-40,-15,-36,-11,'#6fae7c',2);L(c,-36,-11,-29,-20,'#6fae7c',2);}});
  at(c,x.jar1,ty,s,()=>jar(c,0,RED));at(c,x.jar2,ty,s,()=>jar(c,0,'#6fae7c'));
  at(c,x.book,ty,s,()=>debtBook(c,ts));
  at(c,x.scale,ty,s,()=>dialScale(c,p));
  // Worn equipment: a paper tag hung from the counter rim under the scale.
  if(worn){const s2='CẦN KIỂM',tw=Math.max(72,ts*6.6),th=ts+8,tx=x.scale-tw/2,y0=ty+14;L(c,tx+10,y0-8,tx+14,y0,'#b48d64',1.5);L(c,tx+tw-10,y0-8,tx+tw-14,y0,'#b48d64',1.5);
    R(c,tx,y0,tw,th,'#f7d995',5,'#d3a35c',1.5);T(c,s2,x.scale,y0+th/2+1,fit(c,s2,tw-8,ts,800),'#94643d',800);}}
/** Rice, sticky rice and green beans in rolled-down sacks with scoops. */
function riceSacks(c,p,ts){E(c,0,2,72,8,SHADOW);
  for(const [dx,top,tag,h] of [[0,'#fbf6ea','18k',56],[-46,'#fffdf6','Gạo',48],[46,'#a8d27f','25k',46]]){
    R(c,dx-23,-h,46,h,'#f3ecdc',[12,12,14,14],'#cbbd9f',1.5);for(let yy=-h+14;yy<-4;yy+=7)L(c,dx-19,yy,dx+19,yy,'#e6dcc6',1);
    R(c,dx-25,-h-4,50,11,'#e6d9bc',5,'#cbbd9f',1);E(c,dx,-h-4,20,6,top);for(let i=0;i<6;i++)E(c,dx-12+i*5,-h-5+(i%2)*2,1.4,1,top==='#a8d27f'?'#7fb35a':'#e4dccb');
    E(c,dx+7,-h-7,7,4,'#cfd6da');L(c,dx+11,-h-9,dx+20,-h-24,'#b3bcc1',3);
    const tw=Math.max(30,ts*2.6);R(c,dx-tw/2,-h+14,tw,ts+6,'#ffe7a0',3,'#d9b35c',1);T(c,tag,dx,-h+17+ts/2,fit(c,tag,tw-6,ts,800),'#8a5a2b',800);}}
/** Red plastic stool with a conical hat resting on it. */
function stool(c){E(c,0,2,20,5,SHADOW);P(c,[[-16,0],[-9,0],[-6,-22],[-12,-22]],'#d9534f');P(c,[[16,0],[9,0],[6,-22],[12,-22]],'#d9534f');R(c,-16,-28,32,8,'#e8665c',4);E(c,0,-28,16,4,'#f07a70');
  P(c,[[-22,-30],[22,-30],[0,-52]],'#f1dfb0');L(c,-22,-30,22,-30,'#d4bd87',2);for(const t of [.35,.65])L(c,-22*t,-30-22*(1-t)*0,0,-52,'#e2cd98',1);E(c,0,-31,20,2,'#d4bd8780');}
/** Blue crate of vegetables beside stacked egg trays. */
function vegCrate(c,p,ts){E(c,0,2,56,7,SHADOW);R(c,-50,-30,66,30,'#6fa8c9',5,'#4f87a8',1.5);for(let r=0;r<2;r++)for(let i=0;i<6;i++)R(c,-45+i*10,-24+r*11,6,6,'#8fc0db',1.5);
  for(const [x,y,rx,ry,col] of [[-40,-34,12,8,'#86c47c'],[-26,-38,11,9,'#6aa84f'],[-10,-35,10,7,'#9ccf72'],[4,-34,8,6,'#86c47c'],[-34,-30,6,6,'#e8604f'],[-18,-31,6,6,'#ef7a66'],[-2,-31,5.5,5.5,'#b07aa1'],[10,-31,5,5,'#b07aa1']])E(c,x,y,rx,ry,col);
  L(c,-22,-40,-20,-48,'#5f9a44',2);
  for(let k=0;k<3;k++){const y=-k*11;R(c,18,y-10,40,10,'#ead8b6',3,'#cdb48a',1);for(let i=0;i<4;i++)E(c,24+i*9.4,y-4,3,2,'#d9c39c');}
  for(let i=0;i<4;i++){E(c,24+i*9.4,-38,4.2,5.2,i%2?'#f6e4c8':'#f0cfa4');E(c,23+i*9.4,-40,1.3,1.8,'#ffffffb0');}
  const s='Trứng',tw=Math.max(40,ts*3.4);R(c,-17-tw/2,-22,tw,ts+6,CREAM,4,'#cdb48a',1);T(c,s,-17,-22+ts/2+3,fit(c,s,tw-6,ts,800),'#8a5a2b',800);}
/** The owner's little cash desk with the shop ledger: the `finance` hotspot. */
function cashDesk(c,p,words,ts){E(c,0,2,48,6,SHADOW);R(c,-40,-8,6,8,WOOD_D,2);R(c,34,-8,6,8,WOOD_D,2);R(c,-44,-44,88,38,WOOD,8,WOOD_D,2);R(c,-38,-38,76,26,'#f3dbbb',5);
  T(c,words.ledger,0,-25,fit(c,words.ledger,70,ts,800),'#6f5646',800);R(c,-48,-54,96,12,WOOD_L,5,WOOD_D,1.5);
  R(c,-40,-80,32,27,'#8fa9a0',4,'#6b8880',1.5);E(c,-24,-67,6,6,'#dfe8e4');L(c,-24,-67,-21,-70,'#6b8880',1.5);R(c,-36,-76,8,3,'#dfe8e4',1);
  P(c,[[0,-56],[22,-53],[22,-66],[2,-69]],'#fff8e7');P(c,[[44,-56],[22,-53],[22,-66],[42,-69]],'#fffdf5');L(c,22,-53,22,-66,'#c7ad90',1.5);L(c,6,-62,18,-60,p.primary,1.5);L(c,26,-60,38,-62,'#c4b3a0',1.5);}
/** Long wooden bench for neighbours, with iced tea (property tier). */
function bench(c,p){E(c,0,2,68,6,SHADOW);for(const x of [-60,52])R(c,x,-22,8,22,WOOD_D,3);R(c,-68,-30,136,11,WOOD,5,WOOD_D,1.5);
  E(c,-30,-38,11,8,'#b9dcd6');R(c,-34,-48,8,4,'#b9dcd6',2);L(c,-19,-38,-12,-44,'#b9dcd6',3);for(const x of [0,16]){R(c,x-5,-44,10,14,'#e8b76acc',2,'#d5c7b5',1);E(c,x,-42,3,1.5,'#ffffffc0');}heart(c,40,-40,.25,p.primary);}

/* ------------------------------------------------------------ Rooms */
const sillBusy=w=>Object.values(w.c?.decor||{}).some(e=>e?.spot==='window');
function landRoom(w,p){const c=w.ctx,words=w.words(),open=!!w.c?.open,items=w.c?.ops?.security?.items||[];
  E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#d8a57f',35);R(c,96,168,1008,533,'#fff9ee',30,'#cf9f80',3);
  wallAndFloor(c,p,108,179,984,272,447,242,56);
  tinSign(c,p,370,52,460,104);
  goodsShelf(c,118,192,238,258,5,1.12,1);
  backDoor(c,p,378,266,86,184,words,items.includes('lock'),13);
  snacks(c,494,700,198,112,6,1);
  calendar(c,494,324,48,58,w.c?.day||1);
  altar(c,512,450,1,w.time,w.reduced);
  ledge(c,558,382,150,sillBusy(w));
  fridge(c,p,714,242,98,208,open);
  licence(c,p,832,214,54,46);
  streetBoard(c,p,826,292);
  entrance(c,p,908,204,172,246,open,words,14);
  security(c,p,items,[421,226],[930,218],[994,196]);}
function portRoom(w,p){const c=w.ctx,words=w.words(),open=!!w.c?.open,items=w.c?.ops?.security?.items||[];
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#d8a57f',31);R(c,29,117,642,724,'#fff9ed',26,'#cf9f80',3);
  wallAndFloor(c,p,40,139,620,372,506,323,52);
  goodsShelf(c,50,168,178,338,6,1.25,2);
  backDoor(c,p,242,336,72,170,words,items.includes('lock'),16);
  snacks(c,246,436,164,100,5,1.15);
  licence(c,p,344,282,70,46);
  streetBoard(c,p,352,350);
  ledge(c,334,474,104,sillBusy(w));
  fridge(c,p,446,270,94,236,open);
  bananas(c,530,172,1.3);
  entrance(c,p,552,196,100,310,open,words,17);
  security(c,p,items,[278,306],[566,214],[602,190]);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',out=[];
  out.push([588,()=>{at(c,520,588,1,()=>glassCounter(c,p,220));counterTop(w,p,c,{qr:334,till:392,jar1:466,jar2:604,book:540,scale:672},474,1,12);}]);
  out.push([666,()=>at(c,214,666,1,()=>riceSacks(c,p,12))]);
  out.push([664,()=>at(c,302,664,1,()=>stool(c))]);
  out.push([668,()=>at(c,850,668,1,()=>vegCrate(c,p,11))]);
  out.push([612,()=>at(c,1007,612,1,()=>cashDesk(c,p,words,12))]);
  if(tier!=='cozy')out.push([682,()=>at(c,610,682,1,()=>bench(c,p))]);
  if(tier==='garden')for(const [x,y] of PLAN.land.garden)out.push([y+4,()=>plantAt(c,x,y,.6)]);
  return out;}
function portProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',out=[];
  out.push([650,()=>{at(c,316,650,1,()=>glassCounter(c,p,184));counterTop(w,p,c,{qr:152,till:200,jar1:274,jar2:390,book:330,scale:452},536,1.2,14);}]);
  out.push([792,()=>at(c,126,792,.92,()=>riceSacks(c,p,18))]);
  out.push([792,()=>at(c,218,792,1,()=>stool(c))]);
  out.push([802,()=>at(c,506,802,1,()=>vegCrate(c,p,16))]);
  out.push([708,()=>at(c,602,708,.84,()=>cashDesk(c,p,words,19))]);
  if(tier!=='cozy')out.push([816,()=>at(c,290,816,.88,()=>bench(c,p))]);
  if(tier==='garden')for(const [x,y] of PLAN.port.garden)out.push([y+4,()=>plantAt(c,x,y,.55)]);
  return out;}

export default {
  id:'minimart',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
