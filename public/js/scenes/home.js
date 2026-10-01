/** Home scene (homemaker "Nhà chị Thảo"): the ground floor of a narrow tube house in ngõ Hoa Sữa.
 * A staircase climbs to the bedrooms (the washing machine and laundry basket sit under it), the
 * fridge with the family notebook stuck on it (shelf / evidence), a window onto the lane and its
 * hoa sữa tree, the kitchen counter (workbench = stove and pot, counter = rice cooker and the
 * market basket), the family altar on its tall cabinet, bà Lành's rocking chair, bé Su's study desk
 * (finance) and the front door with sandals.
 * The walking plan is homestay's (scenes/lodging.js): the same blocks and spots, another house on top.
 * Plan schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,heart,signBoard,streetBoard} from './kit.js';
import {PLAN} from './lodging.js';

export {PLAN};

const WOOD='#b9825c',WOOD_D='#946446',WOOD_L='#d6a47c',TILE='#efe3cf',TILE_L='#f7eedf',CREAM='#fff7ea';

/* ------------------------------------------------------------ small pieces */
function floorTiles(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=34)for(let col=0,xx=x;xx<x+w;col++,xx+=34){c.fillStyle=(row+col)%2?TILE:TILE_L;c.fillRect(xx,yy,34,34);}
  for(let yy=y;yy<y+h;yy+=34)L(c,x,yy,x+w,yy,'#e2d2b8',1);for(let xx=x;xx<x+w;xx+=34)L(c,xx,y,xx,y+h,'#e2d2b8',1);c.restore();}
function stairs(c,bx,by,tx,ty,n){const pts=[[bx,by]];for(let i=0;i<n;i++){const xs=bx+(tx-bx)*i/n,xe=bx+(tx-bx)*(i+1)/n,y=by-(by-ty)*(i+1)/n;pts.push([xs,y],[xe,y]);}pts.push([tx,by]);
  P(c,pts,'#e9c9a4');c.strokeStyle=WOOD_D;c.lineWidth=2;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.stroke();
  const step=(tx-bx)/n,rise=(by-ty)/n;
  for(let i=0;i<n;i++){const x=bx+step*(i+.5),y=by-rise*(i+1);R(c,Math.min(x-step/2,x+step/2)-2,y-1,Math.abs(step)+4,6,'#f4dcbc',2);L(c,x,y,x,y-38,'#8a8f96',2.5);}
  L(c,bx+step*.5,by-rise-38,tx-step*.5,ty-38,'#6f757c',5);}
/** Front-loading washing machine with a spinning drum. */
function washer(c,x,y,w,h,t,on){R(c,x,y,w,h,'#f4f6f7',8,'#b9c0c5',2);R(c,x+4,y+4,w-8,h*.18,'#e3e8eb',4);E(c,x+w-12,y+4+h*.09,4,4,on?'#7fc39a':'#c5cdd2');
  const cx=x+w/2,cy=y+h*.6,r=Math.min(w,h)*.3;E(c,cx,cy,r+4,r+4,'#c9d1d6');E(c,cx,cy,r,r,'#bfe0f0');
  if(on){c.save();c.beginPath();c.arc(cx,cy,r,0,Math.PI*2);c.clip();const a=t*5;for(let k=0;k<3;k++){const b=a+k*2.1;E(c,cx+Math.cos(b)*r*.45,cy+Math.sin(b)*r*.45,r*.32,r*.22,['#f2a3a0','#9fc3e8','#f5d58a'][k]);}c.restore();}
  E(c,cx-r*.35,cy-r*.35,r*.18,r*.12,'#ffffffaa');}
function basket(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);E(c,0,0,26,5,'#8b73531c');
  P(c,[[-24,-34],[24,-34],[19,0],[-19,0]],'#d9b77f');for(let i=-2;i<=2;i++)L(c,i*9,-32,i*7,-2,'#bf9a62',1.5);for(let k=1;k<4;k++)L(c,-23+k,-34+k*8,23-k,-34+k*8,'#c9a56d',1.5);
  E(c,-10,-38,10,7,'#f2a3a0');E(c,6,-40,11,7,'#9fc3e8');E(c,14,-36,7,5,'#fff1c8');c.restore();}
/** The fridge (shelf) with the family notebook and a child's drawing stuck on it (evidence). */
function fridge(c,p,x,y,w,h,label,fs){R(c,x,y,w,h,'#eef3f5',10,'#aab6bd',2);L(c,x+3,y+h*.36,x+w-3,y+h*.36,'#aab6bd',2);
  R(c,x+w-10,y+12,4,h*.18,'#9aa5ac',2);R(c,x+w-10,y+h*.42,4,h*.22,'#9aa5ac',2);
  R(c,x+8,y+h*.44,w*.52,h*.38,'#fffbe8',3,'#e3cf9a',1);L(c,x+12,y+h*.44,x+12,y+h*.82,'#e58b86',1.5);
  for(let i=0;i<4;i++)L(c,x+16,y+h*.52+i*h*.07,x+w*.52,y+h*.52+i*h*.07,i===0?'#e58b86':'#cbbfa8',1.2);
  E(c,x+8+w*.26,y+h*.44,4,4,'#e7635f');
  R(c,x+w*.18,y+8,w*.5,h*.22,'#ffffff',2,'#d8c9ae',1);E(c,x+w*.3,y+h*.2,5,5,'#f2a3a0');E(c,x+w*.43,y+h*.2,5,5,'#9fc3e8');E(c,x+w*.55,y+h*.19,4,4,'#f5d58a');L(c,x+w*.22,y+h*.27,x+w*.64,y+h*.27,'#8fc49a',2);
  R(c,x+w*.62,y+h*.86,w*.3,fs+4,'#fff',3);T(c,label,x+w*.77,y+h*.86+fs/2+2,fit(c,label,w*.28,fs*.8),p.dark,800);}
/** The window onto the lane: a hoa sữa tree, a wire of laundry, the house opposite. */
function laneWindow(c,x,y,w,h,t){R(c,x-8,y-8,w+16,h+16,'#7f8f86',10,'#5f6d65',2);
  c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#cfe6ef');g.addColorStop(1,'#f3efe1');c.fillStyle=g;c.fillRect(x,y,w,h);
  R(c,x+w*.55,y+h*.25,w*.5,h*.8,'#f0d3b0',0);for(let i=0;i<3;i++)R(c,x+w*.6+i*w*.12,y+h*.36,w*.07,h*.12,'#a9c7d6',1);
  R(c,x+w*.18,y+h*.45,w*.05,h*.6,'#8a6b52',2);for(const [dx,dy,r] of [[.2,.32,.2],[.08,.42,.14],[.33,.4,.15],[.2,.18,.13]])E(c,x+w*dx,y+h*dy,w*r,h*r*.9,'#6f9f74');
  for(let i=0;i<9;i++)E(c,x+w*(.06+((i*37)%30)/100),y+h*(.18+((i*53)%30)/100),3,3,'#fbf6e0');
  const sw=Math.sin(t*1.5)*2;L(c,x,y+h*.2,x+w,y+h*.24,'#6c6c6c',1);
  for(const [f,col] of [[.48,'#f2a3a0'],[.62,'#9fc3e8'],[.76,'#f5d58a']])R(c,x+w*f-7,y+h*.22+sw*f,14,16,col,3);
  c.restore();L(c,x+w/2,y,x+w/2,y+h,'#5f6d65',4);
  for(let k=1;k<5;k++)L(c,x+k*w/5,y+2,x+k*w/5,y+h-2,'#5f6d6555',1.5);}
/** The family altar (bàn thờ) on a tall cabinet: photo, incense bowl, fruit tray, two lamps. */
function altar(c,p,cx,top,bottom,w,t){const sh=top+(bottom-top)*.42;
  R(c,cx-w/2,sh,w,bottom-sh,'#7a3b2a',6,'#5a2a1d',2);R(c,cx-w/2+8,sh+12,w/2-12,bottom-sh-20,'#8a4a35',4);R(c,cx+4,sh+12,w/2-12,bottom-sh-20,'#8a4a35',4);
  E(c,cx-8,sh+(bottom-sh)/2,3,3,'#e2b24f');E(c,cx+8,sh+(bottom-sh)/2,3,3,'#e2b24f');
  R(c,cx-w/2-6,sh-8,w+12,10,'#9c4c32',3,'#5a2a1d',1.5);
  R(c,cx-w*.16,top,w*.32,w*.38,'#e8d7b4',3,'#b98a45',3);E(c,cx,top+w*.16,w*.07,w*.08,'#c9b190');R(c,cx-w*.1,top+w*.25,w*.2,w*.1,'#c9b190',4);
  R(c,cx-w*.12,sh-26,w*.24,18,'#d9b25c',6,'#a8843c',1.5);for(let i=-1;i<=1;i++){L(c,cx+i*8,sh-26,cx+i*8+i*2,sh-56,'#8a5a3a',2);const glow=.6+.4*Math.sin(t*3+i);E(c,cx+i*8+i*2,sh-57,2,2,`rgba(255,120,60,${glow.toFixed(2)})`);}
  E(c,cx-w*.36,sh-16,w*.11,6,'#d9b25c');for(const [dx,dy,r,col] of [[-.4,-26,9,'#f2c14e'],[-.32,-28,8,'#7fb069'],[-.36,-36,7,'#e8743b']])E(c,cx+w*dx,sh+dy,r,r,col);
  for(const s of [-1,1]){const lx=cx+s*w*.42;R(c,lx-5,sh-34,10,26,'#e9c46a',3,'#b98a45',1);E(c,lx,sh-38,5,6,`rgba(255,${(150+60*Math.sin(t*4+s)).toFixed(0)},90,0.9)`);}}
/** The kitchen counter (workbench end: stove and pot; counter end: rice cooker and market basket). */
function kitchen(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,t=w.reduced?0:w.time,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#bb97781d');
  R(c,x0,top+16,x1-x0,bottom-top-16,'#c98e66',10,WOOD_D,2);for(let k=1;k<4;k++)L(c,x0+(x1-x0)*k/4,top+22,x0+(x1-x0)*k/4,bottom-6,'#a8724f',1.5);
  for(let k=0;k<4;k++)E(c,x0+(x1-x0)*(k+.5)/4,top+30,6,2,'#e7c39b');
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2+8;R(c,cx-pw/2,py,pw,ph,CREAM,ph/2,'#c7ad90',2);
  const motto='cơm nhà là ngon nhất';T(c,motto,cx,py+ph/2+1,fit(c,motto,pw-60,fs),p.dark);heart(c,cx-pw/2+20,py+ph/2+5,.33,p.primary);heart(c,cx+pw/2-20,py+ph/2+5,.33,p.primary);
  R(c,x0-10,top,x1-x0+20,22,'#e9e4dc',8,'#b8b0a4',2);R(c,x0-5,top+2,x1-x0+10,6,'#f6f2ec',3);
  // Stove with a steaming pot and a pan.
  R(c,a-56,top-6,112,12,'#3e3e44',4);E(c,a-26,top-1,14,3,'#e2603d');E(c,a+26,top-1,14,3,'#e2603d');
  R(c,a-44,top-36,38,30,'#c7ccd2',6,'#8f969d',1.5);R(c,a-48,top-40,46,7,'#aeb5bc',3);E(c,a-25,top-43,5,3,'#6f767d');
  if(!w.reduced)for(let k=0;k<3;k++){const ph2=(t*.8+k/3)%1;c.globalAlpha=(1-ph2)*.6;E(c,a-25+Math.sin(t*2+k)*5,top-48-ph2*36,6+ph2*6,4+ph2*4,'#ffffff');c.globalAlpha=1;}
  E(c,a+26,top-8,20,6,'#2f3136');L(c,a+44,top-8,a+70,top-14,'#2f3136',4);E(c,a+20,top-11,5,3,'#f5d58a');E(c,a+30,top-10,5,3,'#f2a3a0');
  // Rice cooker, cutting board with greens, market basket.
  R(c,b-62,top-34,40,34,'#fdf6ee',12,'#c9b9a5',1.5);E(c,b-42,top-34,18,6,'#efe2d0');E(c,b-42,top-20,4,4,(w.c?.open?'#e2603d':'#9aa5ac'));
  R(c,b-14,top-8,44,8,'#e3c08f',3,'#b8925a',1);for(const [dx,col] of [[-6,'#6f9f74'],[4,'#7fb069'],[14,'#e8743b']])E(c,b+dx,top-11,5,3,col);
  basket(c,b+60,top+2,.75);
  if((w.c?.ops?.equipment?.condition??100)<100){R(c,x0+10,top+3,port?112:90,port?22:15,'#f7d995',4);T(c,'CẦN KIỂM',x0+10+(port?56:45),top+(port?14.5:11),port?16:9,'#94643d');}
}
function rockingChair(c,cx,bottom,s){c.save();c.translate(cx,bottom);c.scale(s,s);E(c,0,0,40,7,'#8b73531c');
  c.beginPath();c.arc(0,-60,62,Math.PI*.32,Math.PI*.68);c.strokeStyle=WOOD_D;c.lineWidth=5;c.stroke();
  L(c,-26,-6,-22,-44,WOOD,5);L(c,26,-6,22,-44,WOOD,5);R(c,-30,-48,60,10,WOOD_L,4,WOOD_D,1.2);
  R(c,-26,-100,52,54,'#d9b48a',10,WOOD_D,1.5);for(let i=-2;i<=2;i++)L(c,i*9,-94,i*9,-52,'#c49a6c',2);
  R(c,-20,-60,40,14,'#e7b8a8',6);E(c,0,-84,10,8,'#f5e3c9');c.restore();}
function studyDesk(c,p,x,y,wd,fs){E(c,x+wd/2,y+62,wd/2+8,6,'#8b73531c');L(c,x+8,y+14,x+8,y+60,WOOD_D,5);L(c,x+wd-8,y+14,x+wd-8,y+60,WOOD_D,5);
  R(c,x+4,y+12,wd-8,fs+16,'#e8b48a',6,WOOD_D,1.5);R(c,x-4,y,wd+8,14,'#f2cfa4',6,'#b99476',1.5);
  R(c,x+wd*.14,y-14,wd*.3,14,'#ffffff',2,'#cfc4b5',1);for(let i=0;i<2;i++)L(c,x+wd*.17,y-9+i*4,x+wd*.4,y-9+i*4,'#9fc3e8',1.1);
  R(c,x+wd*.5,y-20,wd*.12,20,'#f2a3a0',3);R(c,x+wd*.64,y-16,wd*.1,16,'#9fc3e8',3);E(c,x+wd*.85,y-6,7,7,'#f5d58a');}
function sandals(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);for(const [dx,col] of [[-14,'#e8743b'],[0,'#9fc3e8'],[16,'#f2a3a0']]){E(c,dx,-4,6,12,col);L(c,dx-5,-8,dx+5,-8,'#ffffffaa',2);}c.restore();}
function doorSign(c,p,cx,bottom,open,words,port){const bw=port?140:112,bh=port?40:32,fs=port?16:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,WOOD_D,4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,WOOD_D,4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,CREAM,13,'#c6a182',2);const s=open?words.open_sign:words.closed_sign;T(c,s,cx,bottom-bh/2-23,fit(c,s,bw-16,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,'#7fb28a');}
function clock(c,x,y,r){E(c,x,y,r+3,r+3,WOOD_D);E(c,x,y,r,r,CREAM);for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,x+Math.cos(a)*r*.92,y+Math.sin(a)*r*.92,'#8a6b52',1.5);}
  L(c,x,y,x,y-r*.6,'#3e3e44',2.5);L(c,x,y,x+r*.45,y+r*.1,'#3e3e44',2);}
function familyPhoto(c,x,y,w,h){R(c,x-4,y-4,w+8,h+8,WOOD,5,WOOD_D,1.2);R(c,x,y,w,h,'#e6eef0',3);
  for(const [f,hh,col] of [[.18,.55,'#9fc3e8'],[.38,.62,'#f2a3a0'],[.58,.4,'#f5d58a'],[.78,.5,'#b9a3d6']]){E(c,x+w*f,y+h*(1-hh),w*.07,w*.07,'#f1d3b5');R(c,x+w*f-w*.08,y+h*(1-hh)+w*.06,w*.16,h*hh,col,4);}}
function security(c,p,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#b79b85',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
  if(items.includes('lock')){const lk=port?[560,470]:[262,420];R(c,lk[0],lk[1],16,18,'#d8c596',4,'#a09675',1.2);}
}

/* -------------------------------------------------------------- the room */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,open=!!w.c?.open,items=w.c?.ops?.security?.items||[];
  E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#c9a184',35);R(c,96,168,1008,533,'#fffaf0',30,'#d9ac90',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#f6e7cf55';c.fillRect(108,179,984,120);R(c,108,380,984,4,'#e3cfb2',0);c.restore();
  floorTiles(c,108,445,984,244,16);R(c,108,438,984,10,'#d8c0a0',3);
  // Upper floor: the bedroom doors seen through the stairwell, a ceiling fan.
  for(const [x,col] of [[392,'#f2a3a0'],[530,'#9fc3e8'],[668,'#b9a3d6']]){R(c,x,212,72,78,'#e9c9a4',[8,8,2,2],WOOD_D,1.5);E(c,x+58,256,3,3,'#a8843c');R(c,x+18,198,36,12,CREAM,6,col,2);}
  R(c,292,290,800,14,WOOD,0);for(let x=300;x<1088;x+=20)L(c,x,266,x,290,'#8a8f96',2.5);L(c,292,266,1092,266,'#6f757c',5);
  const fa=t*6;L(c,835,200,835,226,'#6f757c',3);for(let k=0;k<3;k++){const a=fa+k*2.09;P(c,[[835,228],[835+Math.cos(a)*48,228+Math.sin(a)*8],[835+Math.cos(a+.3)*44,228+Math.sin(a+.3)*8]],'#d6a47c');}E(c,835,228,8,5,'#9aa5ac');
  R(c,108,179,984,18,WOOD,[22,22,0,0]);
  familyPhoto(c,128,262,56,40);
  stairs(c,118,450,292,292,8);
  washer(c,224,374,62,66,t,open);
  streetBoard(c,p,310,322);
  clock(c,440,350,24);
  laneWindow(c,512,320,206,108,t);
  fridge(c,p,732,312,82,128,w.words().evidence.toUpperCase(),11);
  R(c,818,330,82,72,'#fff7e7',8,'#d8c3a6',1.5);for(let i=0;i<4;i++)L(c,826,346+i*14,892,346+i*14,i?'#cdbfae':p.primary,1.4);T(c,'LỊCH',859,338,10,p.dark,800);
  altar(c,p,972,214,450,120,t);
  E(c,965,512,92,21,'#d8c6e8');E(c,965,512,80,16,'#e9ddf3');
  R(c,930,660,120,16,'#dcc39a',8,'#c4a67c',1);
  security(c,p,items,false);
  signBoard(c,p,370,64,460,106);
}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,open=!!w.c?.open,items=w.c?.ops?.security?.items||[];
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#c9a184',31);R(c,29,117,642,724,'#fffaf0',26,'#d9ae91',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);c.fillStyle='#f6e7cf55';c.fillRect(40,139,620,160);c.restore();
  floorTiles(c,40,506,620,323,15);R(c,40,500,620,10,'#d8c0a0',3);
  for(const [x,col] of [[90,'#f2a3a0'],[250,'#9fc3e8'],[410,'#b9a3d6']]){R(c,x,196,80,100,'#e9c9a4',[8,8,2,2],WOOD_D,1.5);R(c,x+20,176,40,16,CREAM,8,col,2);}
  R(c,40,300,488,14,WOOD,0);for(let x=48;x<528;x+=20)L(c,x,276,x,300,'#8a8f96',2.5);L(c,40,276,528,276,'#6f757c',5);
  R(c,40,139,620,17,WOOD,[21,21,0,0]);
  stairs(c,652,512,522,306,9);
  washer(c,527,438,70,68,t,open);
  streetBoard(c,p,548,186,1.6);
  altar(c,p,130,318,512,150,t);
  laneWindow(c,230,332,160,136,t);
  fridge(c,p,405,330,105,170,w.words().evidence.toUpperCase(),15);
  E(c,135,566,96,20,'#d8c6e8');E(c,135,566,84,15,'#e9ddf3');
  R(c,465,818,128,16,'#dcc39a',8,'#c4a67c',1);
  security(c,p,items,true);
  signBoard(c,p,135,30,430,106);
}

function landProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([586,()=>kitchen(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>rockingChair(c,1040,562,1)]);
  out.push([620,()=>{studyDesk(c,p,140,560,110,11);T(c,wd.ledger,195,590,fit(c,wd.ledger,90,11),p.dark);}]);
  out.push([668,()=>{doorSign(c,p,988,668,open,wd,false);sandals(c,930,672,1);}]);
  out.push([675,()=>basket(c,1068,675,1)]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([655,()=>kitchen(w,p,215,515,570,655,290,440,16,true)]);
  out.push([652,()=>rockingChair(c,98,652,.95)]);
  out.push([746,()=>{studyDesk(c,p,556,688,98,16);T(c,wd.ledger,605,719,fit(c,wd.ledger,84,16),p.dark);}]);
  out.push([808,()=>{doorSign(c,p,527,808,open,wd,true);sandals(c,455,812,1.1);}]);
  out.push([800,()=>basket(c,628,800,.92)]);
  return out;}

export default {
  id:'home',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
