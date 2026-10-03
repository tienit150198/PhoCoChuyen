/** Nursery scene (babysitter "Tổ trông trẻ Mèo Con"): cô Tâm's playroom on the ground floor of a tube house in
 * ngõ Hoa Sữa. A baby gate across the staircase, the toy chest under it (warehouse), the toy shelf with its cubbies
 * (shelf) and the parents' notes pinned on a cork board (evidence), a window onto the lane, the low counter (workbench
 * = high chair and a bowl, counter = the bottle warmer and the fruit plate), a crib with a turning mobile (property),
 * a rocking chair for naps, a foam alphabet mat, the low drawing table (finance) and the front door with small shoes.
 * The walking plan is homestay's (scenes/lodging.js), like the homemaker's house. Plan schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,heart,signBoard,streetBoard} from './kit.js';
import {PLAN} from './lodging.js';

export {PLAN};

const WOOD='#c99a72',WOOD_D='#9a6c4c',CREAM='#fff8ec',MINT='#cfeadf',PEACH='#fbd9c4',SKY='#cfe3f4',BUTTER='#f8e3a0';
const TOYS=['#f2a3a0','#9fc3e8','#f5d58a','#a8d5b5','#c9b3e3'];

/* ------------------------------------------------------------ small pieces */
function floorMat(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=40)for(let col=0,xx=x;xx<x+w;col++,xx+=40){c.fillStyle=['#f6ead8','#f1e2cc'][(row+col)%2];c.fillRect(xx,yy,40,40);}
  c.restore();}
/** The foam alphabet mat: interlocking squares with a letter each. */
function alphaMat(c,cx,cy,cols,rows,s){const ch='ABCDEGHIKLMNOP';
  for(let r=0;r<rows;r++)for(let k=0;k<cols;k++){const x=cx-cols*s/2+k*s,y=cy-rows*s*.5/2+r*s*.5,col=TOYS[(r*cols+k)%TOYS.length];
    P(c,[[x,y],[x+s,y],[x+s-4,y+s*.5],[x-4,y+s*.5]],col);T(c,ch[(r*cols+k)%ch.length],x+s/2-2,y+s*.25,Math.round(s*.3),'#ffffffd0',800);}}
function stairs(c,bx,by,tx,ty,n){const pts=[[bx,by]];for(let i=0;i<n;i++){const xs=bx+(tx-bx)*i/n,xe=bx+(tx-bx)*(i+1)/n,y=by-(by-ty)*(i+1)/n;pts.push([xs,y],[xe,y]);}pts.push([tx,by]);
  P(c,pts,'#ecd2b2');c.strokeStyle=WOOD_D;c.lineWidth=2;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.stroke();
  const step=(tx-bx)/n,rise=(by-ty)/n;
  for(let i=0;i<n;i++){const x=bx+step*(i+.5),y=by-rise*(i+1);R(c,Math.min(x-step/2,x+step/2)-2,y-1,Math.abs(step)+4,6,'#f6e1c6',2);L(c,x,y,x,y-38,'#8a8f96',2.5);}
  L(c,bx+step*.5,by-rise-38,tx-step*.5,ty-38,'#6f757c',5);}
/** The white baby gate across the foot of the stairs (closed: the latch is green). */
function babyGate(c,x,bottom,w,h){R(c,x,bottom-h,w,h,'#ffffffcc',6,'#b9c0c5',2);for(let i=1;i<6;i++)L(c,x+i*w/6,bottom-h+6,x+i*w/6,bottom-6,'#c9d1d6',2.5);
  R(c,x+w-14,bottom-h*.6,10,12,'#7fc39a',3);}
/** The toy chest (warehouse): lid ajar, a ball and a block peeking out. */
function toyChest(c,x,y,w,h){E(c,x+w/2,y+h,w/2+6,5,'#8b73531c');R(c,x,y,w,h,'#f2c9a0',8,WOOD_D,2);R(c,x+6,y+h*.35,w-12,h*.5,'#f7dcbd',5);
  E(c,x+w*.3,y-2,11,11,TOYS[1]);R(c,x+w*.55,y-12,16,16,TOYS[2],3);R(c,x-3,y-8,w+6,10,'#e3b48a',4,WOOD_D,1.5);heart(c,x+w/2,y+h*.62,.3,'#e58b86');}
/** The toy shelf (shelf): three rows of cubbies with books, blocks, a teddy and a xylophone. */
function toyShelf(c,p,x,y,w,h,label,fs){R(c,x,y,w,h,'#f4e2c8',8,WOOD_D,2);
  for(let r=1;r<3;r++)L(c,x+3,y+r*h/3,x+w-3,y+r*h/3,WOOD_D,2);L(c,x+w/2,y+3,x+w/2,y+h-3,WOOD_D,2);
  for(let i=0;i<4;i++)R(c,x+6+i*7,y+h/3-28,6,26,TOYS[i],1.5);
  E(c,x+w*.75,y+h/3-12,12,12,'#d6a47c');E(c,x+w*.75-9,y+h/3-22,4,4,'#d6a47c');E(c,x+w*.75+9,y+h/3-22,4,4,'#d6a47c');E(c,x+w*.75,y+h/3-10,5,4,'#f5e3c9');
  for(let i=0;i<3;i++)R(c,x+8+i*11,y+2*h/3-14-(i%2)*10,10,10,TOYS[(i+2)%5],2);
  for(let i=0;i<5;i++)R(c,x+w/2+6+i*6,y+2*h/3-12-i*1.5,5,10+i*1.5,TOYS[i],1.5);
  R(c,x+w*.12,y+h-24,w*.76,fs+4,'#fff',3);T(c,label,x+w/2,y+h-24+fs/2+2,fit(c,label,w*.7,fs*.8),p.dark,800);}
/** The cork board with the parents' notes (evidence). */
function noteBoard(c,p,x,y,w,h){R(c,x,y,w,h,'#d9b17f',8,WOOD_D,2);R(c,x+5,y+5,w-10,h-10,'#e6c595',5);
  for(const [dx,dy,col,rot] of [[.1,.12,'#fffbe8',-.06],[.52,.1,'#fde2e4',.05],[.18,.54,'#e3f1ff',.04],[.58,.56,'#fffbe8',-.04]]){
    c.save();c.translate(x+w*dx+w*.17,y+h*dy+h*.18);c.rotate(rot);R(c,-w*.17,-h*.17,w*.34,h*.34,col,2);for(let i=0;i<3;i++)L(c,-w*.12,-h*.08+i*h*.07,w*.12,-h*.08+i*h*.07,'#c9b9a5',1);c.restore();
    E(c,x+w*dx+w*.17,y+h*dy+h*.05,3,3,'#e7635f');}
  T(c,'GIẤY DẶN',x+w/2,y-9,fit(c,'GIẤY DẶN',w,10),p.dark,800);}
/** The window onto the lane: a hoa sữa tree, a kite, the house opposite. */
function laneWindow(c,x,y,w,h,t){R(c,x-8,y-8,w+16,h+16,'#8fb3a5',10,'#6c8f82',2);
  c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#cfe6ef');g.addColorStop(1,'#f3efe1');c.fillStyle=g;c.fillRect(x,y,w,h);
  R(c,x+w*.58,y+h*.3,w*.5,h*.8,'#f0d3b0',0);for(let i=0;i<3;i++)R(c,x+w*.63+i*w*.11,y+h*.4,w*.06,h*.12,'#a9c7d6',1);
  R(c,x+w*.18,y+h*.45,w*.05,h*.6,'#8a6b52',2);for(const [dx,dy,r] of [[.2,.32,.2],[.08,.42,.14],[.33,.4,.15]])E(c,x+w*dx,y+h*dy,w*r,h*r*.9,'#6f9f74');
  const k=Math.sin(t*1.2)*4;P(c,[[x+w*.45,y+h*.08+k],[x+w*.52,y+h*.2+k],[x+w*.45,y+h*.32+k],[x+w*.38,y+h*.2+k]],'#f2a3a0');L(c,x+w*.45,y+h*.32+k,x+w*.55,y+h*.9,'#ffffff',1);
  c.restore();L(c,x+w/2,y,x+w/2,y+h,'#6c8f82',4);
  R(c,x-14,y-14,w*.22,h+20,'#f6c9c4',[8,0,8,8]);R(c,x+w*.8+14,y-14,w*.22,h+20,'#f6c9c4',[0,8,8,8]);}
/** The crib (property) with a turning mobile of stars and a moon. */
function crib(c,cx,top,bottom,w,t){const y=top+(bottom-top)*.42,h=bottom-y;
  E(c,cx,bottom,w/2+10,7,'#8b73531c');R(c,cx-w/2,y,w,h-14,'#ffffff',10,'#c9b9a5',2);
  for(let i=1;i<9;i++)L(c,cx-w/2+i*w/9,y+8,cx-w/2+i*w/9,y+h-22,'#e3d6c4',3);
  R(c,cx-w/2+8,y+h*.55,w-16,h*.25,'#d7ecf7',6);E(c,cx-w*.25,y+h*.55,14,9,'#ffffff');R(c,cx-w*.1,y+h*.5,w*.4,h*.2,'#f6c9c4',6);
  L(c,cx-w/2-4,y-6,cx-w/2-4,bottom-4,WOOD_D,5);L(c,cx+w/2+4,y-6,cx+w/2+4,bottom-4,WOOD_D,5);
  // The mobile hangs from an arm over the crib.
  L(c,cx+w/2,y-4,cx+w/2,top+12,'#b9a38a',3);L(c,cx+w/2,top+12,cx,top+12,'#b9a38a',3);
  const a=t*.8;L(c,cx-w*.3,top+30,cx+w*.3,top+30,'#b9a38a',2);L(c,cx,top+12,cx,top+30,'#b9a38a',1.5);
  for(let k=0;k<4;k++){const ph=a+k*Math.PI/2,dx=Math.cos(ph)*w*.28,hy=top+56+Math.sin(ph)*6;L(c,cx+dx,top+30,cx+dx,hy-8,'#c9b9a5',1);
    if(k%2)E(c,cx+dx,hy,9,9,BUTTER);else P(c,[[cx+dx,hy-10],[cx+dx+4,hy-2],[cx+dx+11,hy-2],[cx+dx+5,hy+3],[cx+dx+7,hy+11],[cx+dx,hy+6],[cx+dx-7,hy+11],[cx+dx-5,hy+3],[cx+dx-11,hy-2],[cx+dx-4,hy-2]],TOYS[k%5]);}}
/** The low counter (workbench end: high chair and bowl; counter end: bottle warmer and fruit plate). */
function counter(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,t=w.reduced?0:w.time,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#bb97781d');
  R(c,x0,top+16,x1-x0,bottom-top-16,'#e9c4a2',10,WOOD_D,2);for(let k=1;k<4;k++)L(c,x0+(x1-x0)*k/4,top+22,x0+(x1-x0)*k/4,bottom-6,'#cfa47f',1.5);
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2+8;R(c,cx-pw/2,py,pw,ph,CREAM,ph/2,'#c7ad90',2);
  const motto='bé no · bé ngủ · bé vui';T(c,motto,cx,py+ph/2+1,fit(c,motto,pw-60,fs),p.dark);heart(c,cx-pw/2+20,py+ph/2+5,.33,p.primary);heart(c,cx+pw/2-20,py+ph/2+5,.33,p.primary);
  R(c,x0-10,top,x1-x0+20,22,'#f4eee6',8,'#c8bdb0',2);
  // High chair with a tray, a bowl and a spoon.
  R(c,a-30,top-62,60,10,'#ffffff',4,'#c9b9a5',1.5);R(c,a-22,top-96,44,36,PEACH,10,'#d9a98a',1.5);L(c,a-24,top-52,a-30,top-2,'#c9b9a5',4);L(c,a+24,top-52,a+30,top-2,'#c9b9a5',4);
  E(c,a+4,top-66,14,5,'#f7f1e6');E(c,a+4,top-68,10,3,'#f5d58a');L(c,a+16,top-70,a+28,top-80,'#9aa5ac',2.5);
  if(!w.reduced)for(let k=0;k<2;k++){const ph2=(t*.7+k/2)%1;c.globalAlpha=(1-ph2)*.5;E(c,a+4+Math.sin(t*2+k)*4,top-76-ph2*26,5+ph2*4,3+ph2*3,'#ffffff');c.globalAlpha=1;}
  // Bottle warmer, a bottle, the fruit plate.
  R(c,b-62,top-30,34,30,SKY,8,'#9fb7c9',1.5);R(c,b-52,top-52,14,26,'#ffffff',5,'#c9d1d6',1);R(c,b-50,top-58,10,7,'#f2a3a0',3);
  E(c,b,top-6,24,6,'#ffffff');for(const [dx,col] of [[-12,'#f5d58a'],[-2,'#e8743b'],[9,'#7fb069'],[16,'#f2a3a0']])E(c,b+dx,top-10,5,4,col);
  R(c,b+38,top-24,30,24,'#a8d5b5',6,'#7fae8f',1.5);E(c,b+53,top-26,8,4,'#ffffff');
}
function rockingChair(c,cx,bottom,s){c.save();c.translate(cx,bottom);c.scale(s,s);E(c,0,0,40,7,'#8b73531c');
  c.beginPath();c.arc(0,-60,62,Math.PI*.32,Math.PI*.68);c.strokeStyle=WOOD_D;c.lineWidth=5;c.stroke();
  L(c,-26,-6,-22,-44,WOOD,5);L(c,26,-6,22,-44,WOOD,5);R(c,-30,-48,60,10,'#e3b48a',4,WOOD_D,1.2);
  R(c,-26,-100,52,54,'#e8c39a',10,WOOD_D,1.5);R(c,-20,-62,40,14,MINT,6);E(c,-6,-80,11,10,'#d6a47c');E(c,-14,-90,4,4,'#d6a47c');E(c,2,-90,4,4,'#d6a47c');c.restore();}
/** The low drawing table (finance) with crayons and a drawing of a house and a sun. */
function drawTable(c,x,y,wd,fs){E(c,x+wd/2,y+48,wd/2+8,6,'#8b73531c');L(c,x+10,y+12,x+10,y+46,WOOD_D,5);L(c,x+wd-10,y+12,x+wd-10,y+46,WOOD_D,5);
  R(c,x-4,y,wd+8,14,BUTTER,6,'#c9a96a',1.5);R(c,x+wd*.12,y-16,wd*.36,16,'#ffffff',2,'#cfc4b5',1);P(c,[[x+wd*.2,y-6],[x+wd*.28,y-13],[x+wd*.36,y-6]],'#e58b86');R(c,x+wd*.22,y-6,wd*.12,5,'#f5d58a',1);E(c,x+wd*.42,y-12,3,3,'#f5b84a');
  for(let i=0;i<4;i++)R(c,x+wd*.58+i*7,y-8,5,8,TOYS[i],1.5);E(c,x+wd*.9,y-6,6,6,'#9fc3e8');}
function shoes(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);for(const [dx,col] of [[-12,'#f2a3a0'],[-2,'#f2a3a0'],[12,'#9fc3e8'],[22,'#9fc3e8']])E(c,dx,-3,5,9,col);c.restore();}
function doorSign(c,p,cx,bottom,open,words,port){const bw=port?140:112,bh=port?40:32,fs=port?16:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,WOOD_D,4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,WOOD_D,4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,CREAM,13,'#c6a182',2);const s=open?words.open_sign:words.closed_sign;T(c,s,cx,bottom-bh/2-23,fit(c,s,bw-16,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,'#7fb28a');}
function clock(c,x,y,r){E(c,x,y,r+3,r+3,'#f2a3a0');E(c,x,y,r,r,CREAM);for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,x+Math.cos(a)*r*.92,y+Math.sin(a)*r*.92,'#8a6b52',1.5);}
  L(c,x,y,x,y-r*.6,'#3e3e44',2.5);L(c,x,y,x+r*.45,y+r*.1,'#3e3e44',2);E(c,x-r*.7,y-r*.9,r*.3,r*.3,'#f2a3a0');E(c,x+r*.7,y-r*.9,r*.3,r*.3,'#f2a3a0');}
/** A garland of paper flags along the top of the wall. */
function bunting(c,x0,x1,y,t){const n=Math.floor((x1-x0)/34),sag=10;
  c.strokeStyle='#c9b9a5';c.lineWidth=1.5;c.beginPath();c.moveTo(x0,y);c.quadraticCurveTo((x0+x1)/2,y+sag*2,x1,y);c.stroke();
  for(let i=0;i<n;i++){const f=(i+.5)/n,x=x0+(x1-x0)*f,yy=y+4*sag*f*(1-f)+Math.sin(t*1.5+i)*1.2;P(c,[[x-11,yy],[x+11,yy],[x,yy+18]],TOYS[i%5]);}}
function security(c,p,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#b79b85',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
  if(items.includes('lock')){const lk=port?[560,470]:[262,420];R(c,lk[0],lk[1],16,18,'#d8c596',4,'#a09675',1.2);}
}

/* -------------------------------------------------------------- the room */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#d4ab8a',35);R(c,96,168,1008,533,'#fffaf0',30,'#e2b79a',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#fde9dc66';c.fillRect(108,179,984,120);for(let x=120;x<1092;x+=48)E(c,x,330,3,3,'#ffffff80');R(c,108,380,984,4,'#ecd2b8',0);c.restore();
  floorMat(c,108,445,984,244,16);R(c,108,438,984,10,'#e0c4a4',3);
  // Upper floor through the stairwell, paper flags.
  for(const [x,col] of [[392,'#f2a3a0'],[530,'#9fc3e8'],[668,'#c9b3e3']]){R(c,x,212,72,78,'#ecd2b2',[8,8,2,2],WOOD_D,1.5);E(c,x+58,256,3,3,'#a8843c');R(c,x+18,198,36,12,CREAM,6,col,2);}
  R(c,292,290,800,14,WOOD,0);for(let x=300;x<1088;x+=20)L(c,x,266,x,290,'#8a8f96',2.5);L(c,292,266,1092,266,'#6f757c',5);
  R(c,108,179,984,18,WOOD,[22,22,0,0]);
  bunting(c,130,1070,310,t);
  stairs(c,118,450,292,292,8);babyGate(c,120,450,64,46);
  toyChest(c,220,382,78,58);
  streetBoard(c,p,310,322);
  clock(c,440,350,24);
  laneWindow(c,512,320,206,108,t);
  toyShelf(c,p,730,312,86,128,wd.shelf.toUpperCase(),11);
  noteBoard(c,p,822,334,76,62);
  crib(c,972,214,450,128,t);
  alphaMat(c,965,512,5,2,36);
  R(c,930,660,120,16,'#dcc39a',8,'#c4a67c',1);
  security(c,p,items,false);
  signBoard(c,p,370,64,460,106);
}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#d4ab8a',31);R(c,29,117,642,724,'#fffaf0',26,'#e2b79a',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);c.fillStyle='#fde9dc66';c.fillRect(40,139,620,160);c.restore();
  floorMat(c,40,506,620,323,15);R(c,40,500,620,10,'#e0c4a4',3);
  for(const [x,col] of [[90,'#f2a3a0'],[250,'#9fc3e8'],[410,'#c9b3e3']]){R(c,x,196,80,100,'#ecd2b2',[8,8,2,2],WOOD_D,1.5);R(c,x+20,176,40,16,CREAM,8,col,2);}
  R(c,40,300,488,14,WOOD,0);for(let x=48;x<528;x+=20)L(c,x,276,x,300,'#8a8f96',2.5);L(c,40,276,528,276,'#6f757c',5);
  R(c,40,139,620,17,WOOD,[21,21,0,0]);
  bunting(c,60,640,322,t);
  stairs(c,652,512,522,306,9);babyGate(c,590,512,62,48);
  toyChest(c,522,446,78,58);
  streetBoard(c,p,548,186,1.6);
  crib(c,130,318,512,150,t);
  laneWindow(c,230,332,160,136,t);
  toyShelf(c,p,405,330,105,170,wd.shelf.toUpperCase(),15);
  alphaMat(c,135,566,5,2,34);
  R(c,465,818,128,16,'#dcc39a',8,'#c4a67c',1);
  security(c,p,items,true);
  signBoard(c,p,135,30,430,106);
}

function landProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([586,()=>counter(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>rockingChair(c,1040,562,1)]);
  out.push([620,()=>{drawTable(c,140,572,110,11);T(c,wd.ledger,195,604,fit(c,wd.ledger,90,11),p.dark);}]);
  out.push([668,()=>{doorSign(c,p,988,668,open,wd,false);shoes(c,930,672,1);}]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([655,()=>counter(w,p,215,515,570,655,290,440,16,true)]);
  out.push([652,()=>rockingChair(c,98,652,.95)]);
  out.push([746,()=>{drawTable(c,556,700,98,16);T(c,wd.ledger,605,731,fit(c,wd.ledger,84,16),p.dark);}]);
  out.push([808,()=>{doorSign(c,p,527,808,open,wd,true);shoes(c,455,812,1.1);}]);
  return out;}

export default {
  id:'nursery',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
