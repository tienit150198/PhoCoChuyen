/** Dispatch scene (rescue, "Tổng đài Cứu hộ phường Mây"): the call centre's duty room. The radio rack with its
 * handsets (warehouse), the unit board with the six teams and their lights (shelf), the log book and the map pins
 * (evidence), the console with two screens and the headset (workbench), the red emergency phone (counter), the wall
 * map of the ward with blinking calls (property), the small desk of paperwork (finance), a rainy window, the coat
 * rack with the reflective vest and the door with its sign.
 * The walking plan is homestay's (scenes/lodging.js), like the ward and the nursery. Plan schema: see scenes/shop.js. */
import {R,E,L,T,fit,signBoard,streetBoard} from './kit.js';
import {PLAN} from './lodging.js';

export {PLAN};

const RED='#c4532f',RED_D='#9b3a1f',NAVY='#2c3e57',NAVY_L='#45607f',STEEL='#9aa8b2',STEEL_D='#6f7d87',CREAM='#fbf8f2',AMBER='#e6a23c',GREEN='#5fb38a',WOOD='#c9a27e',WOOD_D='#9a7656';
const LIGHT=['#5fb38a','#5fb38a','#e6a23c','#5fb38a','#d64545','#5fb38a'];

/* ------------------------------------------------------------ small pieces */
function floorTiles(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=44)for(let col=0,xx=x;xx<x+w;col++,xx+=44){c.fillStyle=['#e9edf1','#dfe5eb'][(row+col)%2];c.fillRect(xx,yy,44,44);}
  c.restore();}
/** A phone handset on a disc (the centre's sign). */
function phoneMark(c,x,y,s,col=RED){E(c,x,y,s,s,'#ffffff');c.save();c.translate(x,y);c.rotate(-.6);R(c,-s*.62,-s*.2,s*1.24,s*.4,col,s*.2);R(c,-s*.7,-s*.38,s*.34,s*.5,col,s*.12);R(c,s*.36,-s*.38,s*.34,s*.5,col,s*.12);c.restore();}
/** The radio rack: four handsets in their chargers, a green light each (warehouse). */
function radioRack(c,x,y,w,h,t){E(c,x+w/2,y+h+4,w/2+6,5,'#4a566322');R(c,x,y,w,h,'#eef1f4',8,STEEL_D,2);
  for(let i=0;i<4;i++){const xx=x+8+i*(w-16)/4;R(c,xx,y+10,(w-16)/4-4,h-20,'#cfd6dd',4,'#a7b2bc',1);R(c,xx+4,y+4,(w-16)/4-12,h-26,'#3b4652',3);
    L(c,xx+(w-16)/8-2,y+4,xx+(w-16)/8-2,y-10,'#3b4652',3);E(c,xx+(w-16)/8-2,y+h-8,3,3,(i+Math.floor(t))%5?GREEN:AMBER);}}
/** The unit board (shelf): six teams with their status lights. */
function unitBoard(c,p,x,y,w,h,label,fs,t){R(c,x,y,w,h,'#ffffff',8,STEEL_D,2);R(c,x,y,w,22,NAVY,[8,8,0,0]);T(c,label,x+w/2,y+11,fit(c,label,w-10,fs),'#ffffff',800);
  const icons=['🚒','🚑','🚤','🛗','🚓','🧰'],row=(h-30)/6;
  for(let i=0;i<6;i++){const yy=y+26+i*row;R(c,x+5,yy,w-10,row-3,i%2?'#f1f4f7':'#e8edf2',4);T(c,icons[i],x+16,yy+row/2-1,Math.min(12,row-4));
    L(c,x+28,yy+row/2-1,x+w-20,yy+row/2-1,'#b8c4cf',2);const blink=LIGHT[i]==='#d64545'&&Math.floor(t*2)%2===0;E(c,x+w-12,yy+row/2-1,3.5,3.5,blink?'#f2b3b3':LIGHT[i]);}}
/** The log book and the pins on a little map (evidence). */
function logBook(c,p,x,y,w,h){c.save();c.translate(x+w*.26,y+h/2);c.rotate(-.05);R(c,-w*.24,-h/2,w*.48,h,'#f4ead8',4,WOOD_D,1.5);
  for(let i=0;i<5;i++)L(c,-w*.18,-h/2+12+i*9,w*.18,-h/2+12+i*9,'#c4b49a',1.2);R(c,-w*.24,-h/2,6,h,RED_D,2);c.restore();
  c.save();c.translate(x+w*.74,y+h/2);c.rotate(.04);R(c,-w*.22,-h/2,w*.44,h,'#dfeee3',4,'#9db7a6',1.5);L(c,-w*.18,-h*.1,w*.18,h*.12,'#8fb39b',3);L(c,-w*.05,-h/2+6,0,h/2-6,'#8fb39b',2);
  for(const [dx,dy,col] of [[-.1,-.2,RED],[.08,.1,AMBER],[-.02,.28,'#3f7fbf']])E(c,w*dx,h*dy,4,4,col);c.restore();
  T(c,'NHẬT KÝ',x+w/2,y-9,fit(c,'NHẬT KÝ',w,10),p.dark,800);}
/** A window with the rain coming down. */
function rainWindow(c,x,y,w,h,t){R(c,x-8,y-8,w+16,h+16,'#a9b8c6',10,'#7d8fa1',2);
  c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#9fb4c8');g.addColorStop(1,'#d7e0e8');c.fillStyle=g;c.fillRect(x,y,w,h);
  for(let i=0;i<4;i++){const bx=x+w*(.1+i*.22);R(c,bx,y+h*(.55-i%2*.12),w*.16,h*.6,['#7d8ea0','#8d9db0'][i%2],2);for(let k=0;k<3;k++)R(c,bx+5,y+h*(.62-i%2*.12)+k*12,5,5,'#f6e7a8',1);}
  c.strokeStyle='#ffffff99';c.lineWidth=1.2;for(let i=0;i<14;i++){const rx=x+((i*37+t*60)%w),ry=y+((i*53+t*140)%h);c.beginPath();c.moveTo(rx,ry);c.lineTo(rx-3,ry+10);c.stroke();}
  c.restore();L(c,x+w/2,y,x+w/2,y+h,'#7d8fa1',4);L(c,x,y+h*.45,x+w,y+h*.45,'#7d8fa1',3);}
/** The wall map of the ward with the calls blinking on it (property). */
function wallMap(c,cx,top,bottom,w,t,ring){const h=(bottom-top)*.62,x=cx-w/2,y=top+10;
  E(c,cx,bottom,w/2+12,7,'#4a566318');R(c,x-6,y-6,w+12,h+12,NAVY,10);R(c,x,y,w,h,'#1f2d40',6);
  c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  c.strokeStyle='#3e5a7a';c.lineWidth=5;c.beginPath();c.moveTo(x+w*.08,y+h*.7);c.bezierCurveTo(x+w*.3,y+h*.55,x+w*.55,y+h*.85,x+w*.95,y+h*.6);c.stroke();
  for(let i=1;i<5;i++){L(c,x+w*i/5,y,x+w*i/5,y+h,'#2c4058',1.5);L(c,x,y+h*i/5,x+w,y+h*i/5,'#2c4058',1.5);}
  const pts=[[.25,.3],[.7,.25],[.55,.62],[.3,.78]];pts.forEach(([px,py],i)=>{const on=ring&&i===Math.floor(t*1.5)%pts.length;E(c,x+w*px,y+h*py,on?8:5,on?8:5,on?'#ff6b5b':i%2?AMBER:GREEN);});
  c.restore();T(c,'PHƯỜNG MÂY',cx,y+h+16,fit(c,'PHƯỜNG MÂY',w,12),'#e8eef5',800);
  R(c,cx-8,y+h+26,16,(bottom-(y+h+26))-6,STEEL_D,3);R(c,cx-w*.3,bottom-12,w*.6,10,STEEL,5);}
/** The console: two screens, the headset, the red emergency phone and the big call light. */
function console_(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,t=w.reduced?0:w.time,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#4a56631d');
  R(c,x0,top+16,x1-x0,bottom-top-16,'#e3e9ef',10,'#9fb0c0',2);for(let k=1;k<4;k++)L(c,x0+(x1-x0)*k/4,top+22,x0+(x1-x0)*k/4,bottom-6,'#c6d1db',1.5);
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2+8;R(c,cx-pw/2,py,pw,ph,CREAM,ph/2,'#b5c3d0',2);
  const motto='địa chỉ trước · đúng đội · giữ máy';T(c,motto,cx,py+ph/2+1,fit(c,motto,pw-56,fs),p.dark);phoneMark(c,cx-pw/2+18,py+ph/2,8);phoneMark(c,cx+pw/2-18,py+ph/2,8);
  R(c,x0-10,top,x1-x0+20,22,'#f2f5f8',8,'#b9c6d2',2);
  // Two screens: the call form and the unit board.
  for(const [dx,col] of [[-40,'#cfe3f4'],[22,'#f6dccf']]){R(c,a+dx-4,top-62,58,40,'#33404d',5);R(c,a+dx,top-58,50,32,col,3);L(c,a+dx+4,top-50,a+dx+40,top-50,NAVY_L,2);L(c,a+dx+4,top-42,a+dx+30,top-42,NAVY_L,2);}
  R(c,a-14,top-22,16,8,'#55606a',2);
  // Headset on its hook.
  c.beginPath();c.arc(b-46,top-24,12,Math.PI,0);c.strokeStyle='#2f3a46';c.lineWidth=3;c.stroke();R(c,b-62,top-26,8,12,'#2f3a46',3);R(c,b-38,top-26,8,12,'#2f3a46',3);
  // The red phone and the call light.
  R(c,b-18,top-18,36,18,RED,6);R(c,b-14,top-26,28,10,RED_D,5);
  const on=!w.reduced&&Math.floor(t*2)%2===0;R(c,b+28,top-48,40,46,'#ffffff',6,STEEL_D,1.5);E(c,b+48,top-30,11,11,on?'#ff6b5b':'#f3c4bd');T(c,'GỌI',b+48,top-10,9,p.dark,800);
}
function wallClock(c,x,y,r){E(c,x,y,r+3,r+3,NAVY);E(c,x,y,r,r,CREAM);for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,x+Math.cos(a)*r*.92,y+Math.sin(a)*r*.92,STEEL_D,1.5);}
  L(c,x,y,x,y-r*.6,'#3e3e44',2.5);L(c,x,y,x+r*.45,y+r*.1,'#3e3e44',2);}
function paperDesk(c,x,y,wd){E(c,x+wd/2,y+48,wd/2+8,6,'#4a56631c');L(c,x+10,y+12,x+10,y+46,WOOD_D,5);L(c,x+wd-10,y+12,x+wd-10,y+46,WOOD_D,5);
  R(c,x-4,y,wd+8,14,WOOD,6,WOOD_D,1.5);R(c,x+wd*.1,y-12,wd*.36,12,'#ffffff',2,'#cfc4b5',1);R(c,x+wd*.52,y-16,wd*.3,16,'#f7e6b5',2,'#d9c58a',1);R(c,x+wd*.86,y-14,6,14,RED,1.5);}
function doorSign(c,p,cx,bottom,open,words,port){const bw=port?150:120,bh=port?40:32,fs=port?16:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,STEEL_D,4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,STEEL_D,4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,CREAM,13,'#b5c3d0',2);const s=open?words.open_sign:words.closed_sign;T(c,s,cx,bottom-bh/2-23,fit(c,s,bw-20,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,GREEN);}
/** The coat rack: a reflective vest and a helmet. */
function coatRack(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);E(c,0,0,26,5,'#4a56631c');
  L(c,0,0,0,-96,WOOD_D,5);L(c,-18,0,18,0,WOOD_D,5);L(c,-14,-90,14,-84,WOOD_D,3);
  R(c,-16,-82,32,40,'#f0a23a',6);L(c,-16,-68,16,-68,'#f6f2c4',4);L(c,-16,-56,16,-56,'#f6f2c4',4);
  c.beginPath();c.arc(10,-92,11,Math.PI,0);c.fillStyle=RED;c.fill();R(c,-2,-93,24,4,RED_D,2);c.restore();}
function security(c,p,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#9aa8b2',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
  if(items.includes('lock')){const lk=port?[560,470]:[262,420];R(c,lk[0],lk[1],16,18,'#d8c596',4,'#a09675',1.2);}
}
const ringing=w=>!!(w.c?.tasks||[]).some(t=>t.kind!=='shift'&&!['completed','cancelled','referred'].includes(t.status));

/* -------------------------------------------------------------- the room */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,605,724,503,30,'#9fa9b322');R(c,85,165,1030,550,'#a9b8c6',35);R(c,96,168,1008,533,'#fbfcfd',30,'#b5c3d0',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#e3e9f066';c.fillRect(108,179,984,140);R(c,108,380,984,6,'#c9d3dc',0);R(c,108,386,984,4,RED,0);c.restore();
  floorTiles(c,108,445,984,244,16);R(c,108,438,984,10,'#c9d3dc',3);
  // The glass wall onto the radio room, a cable tray.
  R(c,292,214,800,74,'#eef2f6',[8,8,0,0],'#b9c6d2',1.5);for(let x=312;x<1080;x+=120){R(c,x,226,92,50,'#f7f9fb',4,'#d3dce4',1);}
  for(const x of [520,690])phoneMark(c,x,251,12);
  L(c,292,300,1092,300,STEEL_D,4);for(let x=300;x<1088;x+=36)E(c,x,300,3,3,STEEL);
  R(c,108,179,984,18,RED,[22,22,0,0]);
  radioRack(c,206,384,90,56,t);
  streetBoard(c,p,310,322);
  wallClock(c,440,350,24);
  rainWindow(c,512,320,206,108,t);
  unitBoard(c,p,730,306,86,134,wd.shelf.toUpperCase(),10,t);
  logBook(c,p,822,334,76,62);
  wallMap(c,972,226,450,150,t,ringing(w));
  R(c,930,660,120,16,'#d3dce4',8,'#b5c3d0',1);
  security(c,p,items,false);
  signBoard(c,p,370,64,460,106);
}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,350,857,324,23,'#9fa9b322');R(c,22,114,656,738,'#a9b8c6',31);R(c,29,117,642,724,'#fbfcfd',26,'#b5c3d0',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);c.fillStyle='#e3e9f066';c.fillRect(40,139,620,170);c.restore();
  floorTiles(c,40,506,620,323,15);R(c,40,500,620,10,'#c9d3dc',3);
  R(c,40,196,488,90,'#eef2f6',[8,8,0,0],'#b9c6d2',1.5);for(let x=56;x<520;x+=116)R(c,x,208,96,64,'#f7f9fb',4,'#d3dce4',1);
  phoneMark(c,290,240,14);L(c,40,300,528,300,STEEL_D,4);
  R(c,40,139,620,17,RED,[21,21,0,0]);
  radioRack(c,520,446,86,58,t);
  streetBoard(c,p,548,186,1.6);
  wallMap(c,130,318,512,170,t,ringing(w));
  rainWindow(c,230,332,160,136,t);
  unitBoard(c,p,405,326,105,176,wd.shelf.toUpperCase(),14,t);
  R(c,465,818,128,16,'#d3dce4',8,'#b5c3d0',1);
  security(c,p,items,true);
  signBoard(c,p,135,30,430,106);
}

function landProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([586,()=>console_(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>coatRack(c,1040,562,1)]);
  out.push([620,()=>{paperDesk(c,140,572,110);T(c,wd.ledger,195,604,fit(c,wd.ledger,90,11),p.dark);}]);
  out.push([668,()=>doorSign(c,p,988,668,open,wd,false)]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([655,()=>console_(w,p,215,515,570,655,290,440,16,true)]);
  out.push([652,()=>coatRack(c,98,652,.95)]);
  out.push([746,()=>{paperDesk(c,556,700,98);T(c,wd.ledger,605,731,fit(c,wd.ledger,84,16),p.dark);}]);
  out.push([808,()=>doorSign(c,p,527,808,open,wd,true)]);
  return out;}

export default {
  id:'dispatch',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
