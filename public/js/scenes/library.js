/** Library scene (career `library`, Thư viện – Lưu trữ phường Mây): the reading room on the second floor of the
 * ward's cultural house. Tall bookcases with coloured spines and call-number labels (shelf), the rules board
 * (evidence), the circulation desk with the scanner and the date stamp (workbench / counter), the returns cart
 * (warehouse), the archive store's door with its hygrometer (property), the loan book on a side table (finance),
 * reading tables with green lamps, a window onto the lane and the "Giữ yên lặng" sign at the door. The hygrometer
 * needle follows the day's weather (career data `mod`). The walking plan is homestay's (scenes/lodging.js), like
 * the nursery. Plan schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,heart,signBoard,streetBoard} from './kit.js';
import {PLAN} from './lodging.js';

export {PLAN};

const WOOD='#b98a62',WOOD_D='#86603f',CREAM='#fff8ec',BLUE='#5b6f9e',BLUE_D='#3e4f78',PAPER='#efe2c8',LAMP='#4f8a63';
const SPINES=['#c0533f','#5b6f9e','#d9a441','#4f8a63','#8a6da8','#d07c4a','#3f7f9a','#b8625e'];
const mod=w=>w.c?.data?.mod?.id||'normal';

/* ------------------------------------------------------------ pieces */
function floorBoards(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=30){c.fillStyle=row%2?'#ead2b0':'#e4c9a3';c.fillRect(x,yy,w,30);L(c,x,yy,x+w,yy,'#d2b08a',1.2);
    for(let xx=x+40+(row%3)*70;xx<x+w;xx+=210)L(c,xx,yy+4,xx,yy+26,'#d2b08a',1.1);}
  c.restore();}
/** A bookcase: rows of spines in colours, a call-number strip on each shelf. */
function bookcase(c,x,y,w,h,rows,label,fs){E(c,x+w/2,y+h+4,w/2+6,6,'#5a40281c');R(c,x,y,w,h,'#c9a079',8,WOOD_D,2);
  const rh=(h-16)/rows;
  for(let r=0;r<rows;r++){const sy=y+8+r*rh;R(c,x+6,sy,w-12,rh-4,'#f3e3c8',3);
    let bx=x+9,k=r*3;while(bx<x+w-14){const bw=7+((k*5)%6),bh=rh-10-((k*7)%9);R(c,bx,sy+rh-6-bh,bw,bh,SPINES[k%SPINES.length],1.5);bx+=bw+2;k++;}
    R(c,x+4,sy+rh-6,w-8,6,WOOD,2);R(c,x+w/2-14,sy+rh-5,28,4,CREAM,1);}
  if(label){R(c,x+w*.15,y-18,w*.7,fs+6,BLUE,6);T(c,label,x+w/2,y-18+(fs+6)/2,fit(c,label,w*.66,fs),'#fff',800);}}
/** The rules board (evidence): three short lines and a crossed-out phone. */
function rulesBoard(c,p,x,y,w,h){R(c,x,y,w,h,'#2f3f36',6,WOOD_D,2.5);T(c,'NỘI QUY',x+w/2,y+12,fit(c,'NỘI QUY',w-10,11),'#f6eccf',800);
  for(let i=0;i<3;i++)L(c,x+8,y+26+i*11,x+w-8,y+26+i*11,'#d8d2bf',2);
  E(c,x+w/2,y+h-14,9,9,'#c0533f');R(c,x+w/2-4,y+h-21,8,13,'#f6eccf',2);L(c,x+w/2-8,y+h-6,x+w/2+8,y+h-22,'#c0533f',2.5);}
/** The archive door (property) with the hygrometer beside it; the needle follows the weather of the day. */
function archiveDoor(c,w,x,y,wd,h,port){const damp=mod(w)==='nom';R(c,x,y,wd,h,'#7d8a96',6,'#4e5963',2.5);R(c,x+6,y+6,wd-12,h-12,'#93a1ae',4);
  L(c,x+wd/2,y+6,x+wd/2,y+h-6,'#4e5963',2);E(c,x+wd-14,y+h*.55,3.5,3.5,'#f2c84b');
  R(c,x+4,y-24,wd-8,20,BLUE_D,6);T(c,'KHO LƯU TRỮ',x+wd/2,y-14,fit(c,'KHO LƯU TRỮ',wd-14,port?12:11),'#fff',800);
  const gx=port?x+wd+24:x-26,gy=y+30;E(c,gx,gy,17,17,'#e9e2d2');E(c,gx,gy,14,14,CREAM);
  c.beginPath();c.arc(gx,gy,11,Math.PI*.8,Math.PI*2.2);c.strokeStyle='#cfc4b2';c.lineWidth=3;c.stroke();
  c.beginPath();c.arc(gx,gy,11,Math.PI*1.75,Math.PI*2.2);c.strokeStyle='#c0533f';c.lineWidth=3;c.stroke();
  const a=Math.PI*(damp?1.95:1.45);L(c,gx,gy,gx+Math.cos(a)*10,gy+Math.sin(a)*10,'#2f2a24',2);E(c,gx,gy,2,2,'#2f2a24');
  T(c,damp?'ẩm!':'%RH',gx,gy+24,port?11:10,damp?'#c0533f':'#6b6257',800);}
function laneWindow(c,x,y,w,h,t,wet){R(c,x-8,y-8,w+16,h+16,'#9fb7c9',10,'#6f8798',2);c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,wet?'#a9b3bd':'#cfe6ef');g.addColorStop(1,wet?'#d9dcd8':'#f6efdd');c.fillStyle=g;c.fillRect(x,y,w,h);
  R(c,x+w*.12,y+h*.4,w*.05,h*.7,'#8a6b52',2);for(const [dx,dy,r] of [[.14,.3,.18],[.04,.42,.12],[.26,.4,.13]])E(c,x+w*dx,y+h*dy,w*r,h*r*.9,wet?'#6f8f78':'#6f9f74');
  R(c,x+w*.55,y+h*.35,w*.5,h*.8,'#f0d3b0',0);for(let i=0;i<3;i++)R(c,x+w*.6+i*w*.12,y+h*.45,w*.06,h*.12,'#a9c7d6',1);
  if(wet)for(let i=0;i<14;i++){const rx=x+((i*37+t*60)%w),ry=y+((i*23+t*140)%h);L(c,rx,ry,rx-3,ry+9,'#ffffff99',1.2);}
  c.restore();L(c,x+w/2,y,x+w/2,y+h,'#6f8798',4);}
/** The returns cart (warehouse): two shelves of books on wheels. */
function bookCart(c,x,y,w,h,label,fs){E(c,x+w/2,y+h+4,w/2+6,5,'#5a40281c');R(c,x,y,w,h-10,'#d9e2ec',6,'#6f8798',2);L(c,x+4,y+(h-10)/2,x+w-4,y+(h-10)/2,'#6f8798',2);
  for(let r=0;r<2;r++)for(let i=0;i<5;i++){const bx=x+8+i*(w-16)/5,top=y+4+r*(h-10)/2;R(c,bx,top+4,(w-16)/5-3,(h-10)/2-8,SPINES[(i+r*2)%SPINES.length],1.5);}
  E(c,x+10,y+h-4,5,5,'#3a3a3a');E(c,x+w-10,y+h-4,5,5,'#3a3a3a');T(c,label,x+w/2,y+h+14,fit(c,label,w+20,fs),BLUE_D,800);}
/** The circulation desk: scanner and screen at the workbench end, the date stamp and a stack of returns at the counter end. */
function desk(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,t=w.reduced?0:w.time,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#5a40281d');R(c,x0,top+16,x1-x0,bottom-top-16,'#c99a72',10,WOOD_D,2);
  for(let k=1;k<4;k++)L(c,x0+(x1-x0)*k/4,top+22,x0+(x1-x0)*k/4,bottom-6,'#b3845e',1.5);
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2+8;R(c,cx-pw/2,py,pw,ph,CREAM,ph/2,'#c7ad90',2);
  const motto='mượn · trả · tra cứu';T(c,motto,cx,py+ph/2+1,fit(c,motto,pw-60,fs),BLUE_D);heart(c,cx-pw/2+20,py+ph/2+5,.33,BLUE);heart(c,cx+pw/2-20,py+ph/2+5,.33,BLUE);
  R(c,x0-10,top,x1-x0+20,22,'#f4eee6',8,'#c8bdb0',2);
  // screen and barcode scanner
  R(c,a-30,top-58,60,40,'#2f3a4a',6,'#1f2733',2);R(c,a-25,top-53,50,30,'#cfe3f4',3);for(let i=0;i<3;i++)L(c,a-19,top-46+i*8,a+(i===1?6:16),top-46+i*8,BLUE,2);
  R(c,a-6,top-18,12,18,'#3e4f78',3);R(c,a+34,top-26,14,24,'#2f3a4a',4);E(c,a+41,top-24,5,3,'#c0533f');
  if(!w.reduced){const ph2=(t*1.4)%1;c.globalAlpha=(1-ph2)*.6;L(c,a+41,top-22,a+41,top-8+ph2*6,'#ff6a5a',2);c.globalAlpha=1;}
  // date stamp, ink pad, a stack of returned books
  R(c,b-64,top-14,30,12,'#3a3a3a',3);R(c,b-56,top-34,14,22,WOOD,4,WOOD_D,1);E(c,b-49,top-36,9,6,'#5b3a2a');
  for(let i=0;i<4;i++)R(c,b-14-(i%2)*4,top-12-i*9,58,8,SPINES[(i+3)%SPINES.length],2);
  R(c,b+52,top-28,30,26,PAPER,4,'#c9a46a',1.5);T(c,'TRẢ',b+67,top-15,port?11:10,BLUE_D,800);}
function readingTable(c,cx,bottom,s){c.save();c.translate(cx,bottom);c.scale(s,s);E(c,0,2,62,8,'#5a40281c');
  L(c,-48,-4,-48,-36,WOOD_D,5);L(c,48,-4,48,-36,WOOD_D,5);R(c,-60,-44,120,12,'#d6b089',5,WOOD_D,1.5);
  R(c,-34,-58,40,14,'#f6eee0',2,'#d8cbb8',1);L(c,-14,-58,-14,-44,'#c9b9a5',1);
  L(c,34,-44,34,-74,'#6b6b6b',2.5);P(c,[[20,-74],[48,-74],[42,-86],[26,-86]],LAMP);E(c,34,-70,6,3,'#fff3b0');c.restore();}
function ledgerTable(c,p,x,y,wd,label,fs){E(c,x+wd/2,y+48,wd/2+8,6,'#5a40281c');L(c,x+10,y+12,x+10,y+46,WOOD_D,5);L(c,x+wd-10,y+12,x+wd-10,y+46,WOOD_D,5);
  R(c,x-4,y,wd+8,14,'#d6b089',6,WOOD_D,1.5);R(c,x+wd*.15,y-14,wd*.5,14,'#f6eee0',2,'#cfc4b5',1);L(c,x+wd*.4,y-14,x+wd*.4,y,'#cfc4b5',1);
  R(c,x+wd*.7,y-20,8,20,'#3e4f78',2);T(c,label,x+wd/2,y+30,fit(c,label,wd+10,fs),p.dark,800);}
function quietSign(c,p,cx,bottom,open,words,port){const bw=port?150:120,bh=port?40:32,fs=port?15:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,WOOD_D,4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,WOOD_D,4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,CREAM,13,'#c6a182',2);const s=open?words.open_sign:words.closed_sign;T(c,s,cx,bottom-bh/2-23,fit(c,s,bw-16,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,'#7fb28a');T(c,'🤫',cx+bw/2+12,bottom-bh/2-22,port?20:16,'#333',400);}
function doorway(c,x,y,w,h,label,fs){R(c,x,y,w,h,'#e9dcc6',[w/2,w/2,0,0],WOOD_D,2);R(c,x+6,y+8,w-12,h-8,'#d8c8ad',[w/2-6,w/2-6,0,0]);T(c,label,x+w/2,y+h*.55,fit(c,label,w-8,fs),'#7a6450',800);}
function security(c,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#b79b85',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
  if(items.includes('lock')){const lk=port?[560,470]:[262,420];R(c,lk[0],lk[1],16,18,'#d8c596',4,'#a09675',1.2);}}

/* ------------------------------------------------------------ the room */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words(),wet=mod(w)==='nom';
  E(c,605,724,503,30,'#a08a7022');R(c,85,165,1030,550,'#b9967a',35);R(c,96,168,1008,533,'#fffaf0',30,'#d8b79a',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#e8ecf666';c.fillRect(108,179,984,120);R(c,108,380,984,4,'#d9c7ad',0);c.restore();
  floorBoards(c,108,445,984,244,16);R(c,108,438,984,10,'#d2b691',3);R(c,108,179,984,18,WOOD,[22,22,0,0]);
  doorway(c,218,232,80,100,'HÀNH LANG',11);
  bookCart(c,214,384,88,62,wd.warehouse.toUpperCase(),11);
  streetBoard(c,p,310,322);
  laneWindow(c,420,300,200,104,t,wet);
  bookcase(c,640,250,180,190,4,wd.shelf.toUpperCase(),12);
  rulesBoard(c,p,830,318,62,84);
  archiveDoor(c,w,930,232,90,206,false);
  security(c,items,false);
  signBoard(c,p,370,64,460,106);}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words(),wet=mod(w)==='nom';
  E(c,350,857,324,23,'#a08a7022');R(c,22,114,656,738,'#b9967a',31);R(c,29,117,642,724,'#fffaf0',26,'#d8b79a',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);c.fillStyle='#e8ecf666';c.fillRect(40,139,620,160);c.restore();
  floorBoards(c,40,506,620,323,15);R(c,40,500,620,10,'#d2b691',3);R(c,40,139,620,17,WOOD,[21,21,0,0]);
  archiveDoor(c,w,80,290,100,212,true);
  laneWindow(c,226,300,130,110,t,wet);
  bookcase(c,378,300,160,140,3,wd.shelf.toUpperCase(),14);
  rulesBoard(c,p,424,446,66,52);
  doorway(c,544,330,70,92,'HÀNH LANG',11);
  bookCart(c,538,440,64,48,wd.warehouse.toUpperCase(),12);
  streetBoard(c,p,548,186,1.6);
  security(c,items,true);
  signBoard(c,p,135,30,430,106);}

function landProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([586,()=>desk(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>readingTable(c,1010,562,1)]);
  out.push([650,()=>readingTable(c,400,650,.9)]);
  out.push([620,()=>ledgerTable(c,p,140,572,110,wd.ledger,11)]);
  out.push([668,()=>quietSign(c,p,988,668,open,wd,false)]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([655,()=>desk(w,p,215,515,570,655,290,440,16,true)]);
  out.push([660,()=>readingTable(c,110,660,.85)]);
  out.push([746,()=>ledgerTable(c,p,556,700,98,wd.ledger,15)]);
  out.push([760,()=>readingTable(c,300,760,.9)]);
  out.push([808,()=>quietSign(c,p,527,808,open,wd,true)]);
  return out;}

export default {
  id:'library',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
