/** Pool scene (lifeguard, "Hồ bơi Sóng Xanh"): the deck of the ward's public pool. Behind the railing the pool with
 * its lane ropes and the depth marks; the rack of rescue tubes, the ring buoy and the reaching pole (warehouse), the
 * rules and depth board (shelf), the water log and test strips on the wall (evidence), the lifeguard's desk
 * (workbench = the shift book and the radio, counter = the AED box and the emergency phone), the high chair with
 * its umbrella and the tube hanging on it (property), the small table of paperwork (finance), the gate sign.
 * The walking plan is homestay's (scenes/lodging.js), like the ward and the nursery. Plan schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,signBoard,streetBoard} from './kit.js';
import {PLAN} from './lodging.js';

export {PLAN};

const BLUE='#1f8fc4',BLUE_D='#17608a',WATER='#7fd0ee',WATER_D='#4fb3dc',TILE='#eaf6fb',RED='#d6453a',WHITE='#ffffff',WOOD='#c9a27e',WOOD_D='#9a7656',STEEL='#9aa8b2',STEEL_D='#6f7d87',SUN='#f6c544';

/* ------------------------------------------------------------ small pieces */
function deckTiles(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=40)for(let col=0,xx=x;xx<x+w;col++,xx+=40){c.fillStyle=['#f3f9fb','#e6f1f5'][(row+col)%2];c.fillRect(xx,yy,40,40);}
  c.restore();}
/** The pool: water, lane ropes in red and white floats, black lane lines on the floor, a ripple. */
function pool(c,x,y,w,h,t,lanes=4){
  R(c,x-8,y-8,w+16,h+16,'#d9edf4',14,'#a9cbd8',2);
  c.save();c.beginPath();c.roundRect(x,y,w,h,8);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,WATER);g.addColorStop(1,WATER_D);c.fillStyle=g;c.fillRect(x,y,w,h);
  for(let i=1;i<lanes;i++){const yy=y+h*i/lanes;for(let xx=x+6;xx<x+w;xx+=14)E(c,xx,yy,5,3.5,(Math.floor((xx-x)/14)%4<2)?RED:WHITE);}
  for(let i=0;i<lanes;i++){const yy=y+h*(i+.5)/lanes;L(c,x+30,yy,x+w-30,yy,'#2f6f8f55',3);}
  const s=Math.sin(t*1.2);c.globalAlpha=.35;for(let k=0;k<5;k++){const xx=x+(k*w/5+t*14)%w;L(c,xx,y+8+k*6,xx+28,y+10+k*6+s,'#ffffff',2);}c.globalAlpha=1;
  c.restore();}
/** The rescue rack (warehouse): two red tubes, a ring buoy with its line, the long reaching pole. */
function rescueRack(c,x,y,w,h){E(c,x+w/2,y+h+4,w/2+6,5,'#5a6b7322');
  L(c,x+6,y+h,x+6,y-6,STEEL_D,4);L(c,x+w-6,y+h,x+w-6,y-6,STEEL_D,4);L(c,x+2,y-6,x+w-2,y-6,STEEL_D,4);
  R(c,x+12,y,12,h-8,RED,6,'#9e2f27',1.5);R(c,x+30,y+4,12,h-12,RED,6,'#9e2f27',1.5);T(c,'SOS',x+18,y+h/2-4,8,WHITE,900);
  c.beginPath();c.arc(x+w-26,y+h/2,18,0,Math.PI*2);c.lineWidth=9;c.strokeStyle=RED;c.stroke();
  for(let i=0;i<4;i++){const a=i*Math.PI/2+.4;L(c,x+w-26+Math.cos(a)*14,y+h/2+Math.sin(a)*14,x+w-26+Math.cos(a)*22,y+h/2+Math.sin(a)*22,WHITE,4);}
  L(c,x-8,y+h+2,x+w+30,y-18,'#c4ccd0',4);E(c,x+w+30,y-18,5,5,STEEL_D);}
/** The rules and depth board (shelf). */
function rulesBoard(c,p,x,y,w,h,label,fs){R(c,x,y,w,h,WHITE,8,STEEL_D,2);R(c,x,y,w,22,BLUE,[8,8,0,0]);T(c,label,x+w/2,y+11,fit(c,label,w-10,fs),WHITE,800);
  const rows=[['0,6 m','🚫'],['1,2 m','🏊'],['1,8 m','🛟'],['⚡','30′']];
  rows.forEach(([a,b],i)=>{const yy=y+30+i*(h-36)/4;R(c,x+6,yy,w-12,(h-36)/4-4,i%2?'#eef7fb':'#e2f1f8',4);T(c,a,x+24,yy+(h-36)/8-2,10,p.dark,800);T(c,b,x+w-18,yy+(h-36)/8-2,11,p.dark,400);});}
/** The water log and the test strips (evidence). */
function waterLog(c,p,x,y,w,h){c.save();c.translate(x+w*.26,y+h/2);c.rotate(-.04);
  R(c,-w*.22,-h/2,w*.44,h,WOOD,4,WOOD_D,1.5);R(c,-w*.18,-h/2+8,w*.36,h-14,WHITE,2);R(c,-w*.08,-h/2-4,w*.16,9,STEEL,3);
  for(let i=0;i<4;i++)L(c,-w*.13,-h/2+18+i*9,w*.13,-h/2+18+i*9,'#c4ccd0',1.2);c.restore();
  R(c,x+w*.56,y+6,w*.34,h-14,'#fffdf4',4,'#d9c58a',1.2);for(let i=0;i<3;i++)R(c,x+w*.6+i*8,y+12,5,h-28,['#f2d64b','#e6a0c4','#9ed27a'][i],2);
  T(c,'SỔ NƯỚC',x+w/2,y-9,fit(c,'SỔ NƯỚC',w,10),p.dark,800);}
/** The high chair with its umbrella and the tube hanging on it (property). */
function highChair(c,cx,top,bottom,w,t,busy){
  E(c,cx,bottom,w/2+12,7,'#5a6b731c');
  L(c,cx-w*.35,bottom-4,cx-w*.12,top+70,WOOD_D,6);L(c,cx+w*.35,bottom-4,cx+w*.12,top+70,WOOD_D,6);
  for(let i=1;i<5;i++){const yy=top+70+(bottom-top-74)*i/5,k=i/5;L(c,cx-w*.12-w*.23*k,yy,cx+w*.12+w*.23*k,yy,WOOD,4);}
  R(c,cx-w*.22,top+56,w*.44,16,WOOD,5,WOOD_D,1.5);R(c,cx-w*.2,top+30,w*.4,28,'#d8b48e',6,WOOD_D,1.5);
  L(c,cx,top+30,cx,top-14,STEEL_D,3);P(c,[[cx-w*.5,top-6],[cx,top-34],[cx+w*.5,top-6]],busy?RED:'#f08a3c');
  for(let i=0;i<4;i++)P(c,[[cx-w*.5+i*w/4,top-6],[cx-w*.5+(i+.5)*w/4,top-12],[cx-w*.5+(i+1)*w/4,top-6]],i%2?WHITE:'#f7d0b6');
  R(c,cx+w*.24,top+72,12,46,RED,6,'#9e2f27',1.5);
  const s=Math.sin(t*2);if(busy){c.globalAlpha=.25+.15*s;E(c,cx,top-20,w*.6,18,RED);c.globalAlpha=1;}}
/** The lifeguard's desk: the shift book and the radio (workbench end), the AED box and the phone (counter end). */
function guardDesk(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,t=w.reduced?0:w.time,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#5a6b731d');
  R(c,x0,top+16,x1-x0,bottom-top-16,'#e3f2f8',10,'#9cc4d4',2);for(let k=1;k<4;k++)L(c,x0+(x1-x0)*k/4,top+22,x0+(x1-x0)*k/4,bottom-6,'#c9e0ea',1.5);
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2+8;R(c,cx-pw/2,py,pw,ph,'#fbfeff',ph/2,'#a9cbd8',2);
  const motto='mắt không rời mặt nước';T(c,motto,cx,py+ph/2+1,fit(c,motto,pw-56,fs),p.dark);E(c,cx-pw/2+18,py+ph/2,8,8,RED);E(c,cx+pw/2-18,py+ph/2,8,8,RED);
  R(c,x0-10,top,x1-x0+20,22,'#f4fafc',8,'#b9d3dd',2);
  // Shift book, radio, whistle.
  R(c,a-34,top-30,46,30,'#f7e6b5',3,'#d9c58a',1.2);L(c,a-28,top-20,a+4,top-20,'#c9b27a',1.5);L(c,a-28,top-12,a-2,top-12,'#c9b27a',1.5);
  R(c,a+20,top-44,16,40,'#3b4a52',4);L(c,a+32,top-44,a+32,top-60,'#3b4a52',3);E(c,a+28,top-30,3,3,'#7fd06a');
  E(c,a+54,top-8,7,5,SUN);L(c,a+48,top-8,a+40,top-16,'#e05a5a',2);
  // AED box, phone, the 115 card.
  R(c,b-66,top-48,40,46,'#2e9e6a',6,'#1f6e4a',1.5);T(c,'AED',b-46,top-30,10,WHITE,900);E(c,b-46,top-16,6,6,WHITE);
  R(c,b-16,top-18,34,18,'#55606a',5);R(c,b-12,top-26,26,10,'#6f7d87',5);
  R(c,b+26,top-44,46,40,WHITE,6,STEEL_D,1.5);T(c,'115',b+49,top-24,14,RED,900);
  const on=!w.reduced&&Math.floor(t*.8)%2===0;E(c,b+66,top-38,4,4,on?RED:'#e0c3c3');}
function ringStand(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);E(c,0,0,26,5,'#5a6b731c');
  L(c,0,0,0,-64,STEEL_D,3);c.beginPath();c.arc(0,-74,16,0,Math.PI*2);c.lineWidth=8;c.strokeStyle=RED;c.stroke();
  for(let i=0;i<4;i++){const a=i*Math.PI/2+.4;L(c,Math.cos(a)*12,-74+Math.sin(a)*12,Math.cos(a)*20,-74+Math.sin(a)*20,WHITE,3.5);}c.restore();}
function logTable(c,x,y,wd){E(c,x+wd/2,y+48,wd/2+8,6,'#5a6b731c');L(c,x+10,y+12,x+10,y+46,WOOD_D,5);L(c,x+wd-10,y+12,x+wd-10,y+46,WOOD_D,5);
  R(c,x-4,y,wd+8,14,WOOD,6,WOOD_D,1.5);R(c,x+wd*.1,y-12,wd*.36,12,WHITE,2,'#cfc4b5',1);R(c,x+wd*.52,y-16,wd*.3,16,'#f7e6b5',2,'#d9c58a',1);R(c,x+wd*.86,y-14,6,14,BLUE_D,1.5);}
function gateSign(c,p,cx,bottom,open,words,port){const bw=port?150:120,bh=port?40:32,fs=port?16:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,STEEL_D,4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,STEEL_D,4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,'#fbfeff',13,'#9cc4d4',2);const s=open?words.open_sign:words.closed_sign;T(c,s,cx,bottom-bh/2-23,fit(c,s,bw-20,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,'#5fb38a');}
function security(c,p,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#9aa8b2',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
  if(items.includes('lock')){const lk=port?[560,470]:[262,420];R(c,lk[0],lk[1],16,18,'#d8c596',4,'#a09675',1.2);}
}
/** Something is going on in the water: a rescue under way, or thunder. */
const busy=w=>!!(w.c?.tasks||[]).some(t=>['watch','storm'].includes(t.kind)&&!['completed','cancelled','referred'].includes(t.status)&&(t.needs?.alarm||t.kind==='storm'));

/* -------------------------------------------------------------- the deck */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,605,724,503,30,'#9fb0aa22');R(c,85,165,1030,550,'#9cc4d4',35);R(c,96,168,1008,533,'#fbfeff',30,'#a9cbd8',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#dff2fa66';c.fillRect(108,179,984,140);R(c,108,380,984,6,'#bfe0ec',0);R(c,108,386,984,4,BLUE,0);c.restore();
  deckTiles(c,108,445,984,244,16);R(c,108,438,984,10,'#c9e0ea',3);
  // The pool beyond the railing.
  pool(c,292,206,800,94,t,4);
  L(c,292,306,1092,306,STEEL_D,4);for(let x=300;x<1088;x+=36)L(c,x,306,x,292,STEEL,2.5);
  R(c,108,179,984,18,BLUE,[22,22,0,0]);
  rescueRack(c,198,384,92,56);
  streetBoard(c,p,310,322);
  E(c,452,350,26,26,SUN);for(let i=0;i<8;i++){const a=i*Math.PI/4+t*.2;L(c,452+Math.cos(a)*30,350+Math.sin(a)*30,452+Math.cos(a)*38,350+Math.sin(a)*38,SUN,3);}
  pool(c,520,330,198,96,t,2);T(c,'1,2 m',619,318,11,p.dark,800);
  rulesBoard(c,p,730,312,86,128,wd.shelf.toUpperCase(),10);
  waterLog(c,p,822,334,76,62);
  highChair(c,972,226,450,128,t,busy(w));
  R(c,930,660,120,16,'#c9e0ea',8,'#a9cbd8',1);
  security(c,p,items,false);
  signBoard(c,p,370,64,460,106);
}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,350,857,324,23,'#9fb0aa22');R(c,22,114,656,738,'#9cc4d4',31);R(c,29,117,642,724,'#fbfeff',26,'#a9cbd8',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);c.fillStyle='#dff2fa66';c.fillRect(40,139,620,170);c.restore();
  deckTiles(c,40,506,620,323,15);R(c,40,500,620,10,'#c9e0ea',3);
  pool(c,40,190,488,100,t,4);
  L(c,40,300,528,300,STEEL_D,4);
  R(c,40,139,620,17,BLUE,[21,21,0,0]);
  rescueRack(c,512,446,88,58);
  streetBoard(c,p,548,186,1.6);
  highChair(c,130,318,512,150,t,busy(w));
  pool(c,230,340,160,124,t,2);T(c,'1,2 m',310,328,13,p.dark,800);
  rulesBoard(c,p,405,330,105,170,wd.shelf.toUpperCase(),14);
  R(c,465,818,128,16,'#c9e0ea',8,'#a9cbd8',1);
  security(c,p,items,true);
  signBoard(c,p,135,30,430,106);
}

function landProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([586,()=>guardDesk(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>ringStand(c,1040,562,1)]);
  out.push([620,()=>{logTable(c,140,572,110);T(c,wd.ledger,195,604,fit(c,wd.ledger,90,11),p.dark);}]);
  out.push([668,()=>gateSign(c,p,988,668,open,wd,false)]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([655,()=>guardDesk(w,p,215,515,570,655,290,440,16,true)]);
  out.push([652,()=>ringStand(c,98,652,.95)]);
  out.push([746,()=>{logTable(c,556,700,98);T(c,wd.ledger,605,731,fit(c,wd.ledger,84,16),p.dark);}]);
  out.push([808,()=>gateSign(c,p,527,808,open,wd,true)]);
  return out;}

export default {
  id:'pool',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
