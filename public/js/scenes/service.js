/** Service scene kind (salon, pet_care, repair, nail): a work room, not a shop
 * counter. The main station (the `workbench` hotspot) is the centre of the
 * room and changes per career: two styling chairs at a lit mirror, a
 * grooming table beside a bath tub, or a repair bench under a ticket board.
 * Around it: a wall unit (`shelf`), a second station and a side machine, the
 * supply cabinet (`warehouse`), a reception desk with the appointment book
 * (`evidence`) and the till (`counter`), a small ledger desk (`finance`), a
 * waiting bench and the door sign. PLAN schema: see scenes/shop.js.
 *
 * Every floor piece is drawn in local units with its origin at the middle of
 * its feet line, then placed with `at(x, y, scale)`; portrait reuses the same
 * pieces at a smaller scale and keeps its text at 16 scene px or more.
 */
import {R,E,L,T,P,fit,heart,bloom,plantAt,signBoard,streetBoard,openSign} from './kit.js';
import {room,shopFor,taskOf} from './backroom.js';

export const PLAN={
 land:{badge:{board:[0,-44]},floor:[130,452,1070,682],lane:596,line:596,home:[600,596],kx:82,ky:45,sway:28,
   blocks:[[138,452,212,540],[236,462,372,508],[394,462,448,508],[474,466,724,510],[872,494,1052,534],
     [882,644,962,666],[146,648,280,670],[985,650,1082,668],[1061,540,1089,552],[107,664,143,676]],
   bench:[770,468,840,500],garden:[[752,500],[858,500]],
   customers:[[440,655],[560,662],[680,655],[800,662]],event:[320,660],officer:[250,598],
   staff:{x:300,step:115,y:548},cat:[940,404],counterSpan:[380,860],
   decor:{corner:[120,600],front:[990,600],center:[798,600]},sill:{plant:[780,404],lamp:[825,404],seat:[875,404],rug:[600,640]},
   spots:{'go:wash':[[150,390],40,[[175,596]]],'go:kennel':[[150,390],40,[[175,596]]],'go:parts':[[150,390],40,[[175,596]]],shelf:[[311,300],90,[[311,596]]],evidence:[[905,462],55,[[905,580]]],workbench:[[599,430],80,[[599,596],[540,596]]],
     counter:[[1002,462],55,[[1002,580]]],warehouse:[[175,470],48,[[175,566],[175,596]]],board:[[1055,350],45,[[1050,582]]],
     finance:[[922,612],42,[[922,628],[1000,628]]],property:[[1000,302],30,[[1000,580]]],security:[[205,222],30,[[190,596],[350,596]]],
     door:[[1030,636],45,[[1040,626],[960,628]]],pet:[[940,390],38,[[846,560]]]}},
 port:{badge:{board:[-46,-8]},floor:[62,512,638,822],lane:676,line:676,home:[352,676],kx:51,ky:57,sway:22,
   blocks:[[46,508,108,598],[122,528,216,572],[240,530,464,578],[484,528,532,572],[552,560,652,604],
     [572,682,658,708],[66,798,196,820],[488,806,592,820]],
   bench:[206,800,256,820],garden:[[228,604],[262,836]],
   customers:[[160,738],[290,745],[420,738],[520,745]],event:[300,812],officer:[446,800],
   staff:{x:150,step:100,y:624},cat:[545,336],counterSpan:[100,560],
   decor:{corner:[96,690],front:[638,792],center:[615,745]},sill:{plant:[495,336],lamp:[592,336],seat:[622,336],rug:[352,760]},
   spots:{'go:wash':[[77,460],36,[[140,676]]],'go:kennel':[[77,460],36,[[140,676]]],'go:parts':[[77,460],36,[[140,676]]],shelf:[[170,380],70,[[170,676]]],evidence:[[574,532],45,[[574,650]]],workbench:[[352,500],65,[[352,676]]],
     counter:[[628,532],45,[[628,650]]],warehouse:[[77,540],42,[[80,660],[140,676]]],board:[[600,388],42,[[610,650]]],
     finance:[[615,666],40,[[540,692]]],property:[[502,376],30,[[500,676]]],security:[[90,242],30,[[140,676]]],
     door:[[540,796],45,[[540,768],[440,772]]],pet:[[545,322],36,[[520,660]]]}},
};

/* ------------------------------------------------------------ Helpers */
const SEAT='#b8dccf',SEAT_D='#93bfb0',WOOD='#e3b694',WOOD_L='#f3d7bb',WOOD_D='#c79b85',EDGE='#b98f73',CREAM='#fff8ec',METAL='#d5dde0',METAL_D='#98a6ac',SHADOW='#8b735322';
/** Draw `fn` with the origin at (x,y) scaled by s. */
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
const mixHex=(a,b,t)=>{const q=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));const A=q(a),B=q(b);return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join('');};
const soft=(p,t=.55)=>mixHex(p.primary,'#ffffff',t);
/** The nail shop dresses like the salon (mirrors, tiles, flags); only its emblem and main table differ. */
const look=w=>w.career==='nail'?'salon':w.career;
/** A polish bottle: body, cap and a little shine. */
function bottle(c,x,y,s,col){R(c,x-5*s,y-12*s,10*s,12*s,col,3*s,'#00000030',1);R(c,x-2.5*s,y-19*s,5*s,7*s,'#3b3b3b',1.5*s);E(c,x-2*s,y-8*s,1.2*s,2.5*s,'#ffffff90');}
/** Paw print centred at (x,y). */
function paw(c,x,y,s,col){E(c,x,y+2*s,7*s,6*s,col);for(const [dx,dy] of [[-7,-6],[-2.5,-10],[2.5,-10],[7,-6]])E(c,x+dx*s,y+dy*s,2.6*s,3.2*s,col);}
/** The career's emblem (scissors, paw or wrench) in a round badge. */
function emblem(c,p,k,x,y,r){E(c,x,y,r,r,CREAM);c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.strokeStyle=p.primary;c.lineWidth=2;c.stroke();const s=r/14;
  if(k==='nail'){bottle(c,x,y+8*s,s,p.primary);return;}
  if(k==='salon'){L(c,x-7*s,y-7*s,x+6*s,y+6*s,p.dark,2.2*s);L(c,x+7*s,y-7*s,x-6*s,y+6*s,p.dark,2.2*s);for(const dx of [-1,1]){c.beginPath();c.arc(x+dx*6*s,y+7*s,3.4*s,0,Math.PI*2);c.strokeStyle=p.primary;c.lineWidth=2*s;c.stroke();}}
  else if(k==='pet_care')paw(c,x,y+2*s,1.05*s,p.primary);
  else{L(c,x-6*s,y+7*s,x+4*s,y-3*s,p.dark,3.2*s);c.beginPath();c.arc(x+6*s,y-5*s,4.6*s,Math.PI*.9,Math.PI*2.35);c.strokeStyle=p.dark;c.lineWidth=3*s;c.stroke();}}
/** Little paper tag on a string. */
function tag(c,x,y,col){L(c,x,y,x+3,y+7,'#a58b73',1);R(c,x-1,y+6,12,8,col,2,'#b9a58f',1);}

/* ------------------------------------------------------------ Walls & floor */
function wallPattern(c,p,k,x,y,w,h){c.save();c.beginPath();c.roundRect(x,y,w,h,20);c.clip();
  if(k==='salon'){for(let i=0;x+i*46<x+w;i++)R(c,x+i*46+12,y,20,h,'#ffffff40',0);for(let i=0;x+i*92<x+w;i++)heart(c,x+i*92+68,y+h-40,.22,soft(p,.75));}
  else if(k==='pet_care'){for(let r=0;y+r*74<y+h;r++)for(let i=0;x+i*96<x+w;i++)paw(c,x+i*96+(r%2?70:22),y+r*74+34,.9,mixHex(p.wall,p.primary,.16));}
  else{for(let yy=y+22;yy<y+h;yy+=26)L(c,x,yy,x+w,yy,'#7b6a5a12',1.5);R(c,x,y+h-66,w,66,mixHex(p.wall,p.primary,.12),0);L(c,x,y+h-66,x+w,y+h-66,'#ffffff90',3);}
  c.restore();}
function floorTiles(c,p,k,x,y,w,h){c.save();c.beginPath();c.roundRect(x,y,w,h,15);c.clip();
  if(k==='repair'){const bh=40;for(let r=0;y+r*bh<y+h;r++){c.fillStyle=r%2?'#f2e2cb':'#ecd8bc';c.fillRect(x,y+r*bh,w,bh);for(let xx=x+(r%2?-60:-10);xx<x+w;xx+=170)L(c,xx,y+r*bh+3,xx,y+r*bh+bh-3,'#d4bb9a',2);L(c,x,y+r*bh,x+w,y+r*bh,'#dcc3a2',1.5);}}
  else{const sz=62,a=k==='salon'?mixHex(p.light,'#ffffff',.25):'#fdf2e3',b=k==='salon'?'#fffaf6':'#f5e2cb';
    for(let xx=x;xx<x+w;xx+=sz)for(let yy=y;yy<y+h;yy+=sz){c.fillStyle=(Math.round((xx-x)/sz)+Math.round((yy-y)/sz))%2?a:b;c.fillRect(xx,yy,sz,sz);}
    if(k==='pet_care')for(const [px,py] of [[.2,.55],[.26,.72],[.33,.6],[.4,.78],[.72,.7],[.8,.84]])paw(c,x+w*px,y+h*py,.8,'#e7c9ae70');}
  c.restore();}
/** String of little flags (salon, pet) or hanging bulbs (repair). */
function bunting(c,p,k,x0,x1,y,sag){c.strokeStyle='#cfb28e';c.lineWidth=2;c.beginPath();c.moveTo(x0,y);c.quadraticCurveTo((x0+x1)/2,y+sag*2,x1,y);c.stroke();
  const n=Math.max(4,Math.round((x1-x0)/58)),cols=[p.primary,'#f3d590',p.mint,soft(p,.7)];
  for(let i=1;i<n;i++){const t=i/n,xx=x0+(x1-x0)*t,yy=y+sag*4*t*(1-t);
    if(k==='repair'){L(c,xx,yy,xx,yy+12,'#9a8a78',1.5);R(c,xx-3,yy+10,6,5,'#8f8f8f',1);E(c,xx,yy+19,6,7,'#ffe9a8');E(c,xx-2,yy+17,2,2.5,'#fffbe8');}
    else{P(c,[[xx-11,yy],[xx+11,yy],[xx,yy+20]],cols[i%4]);if(k==='pet_care')paw(c,xx,yy+8,.45,'#fff8ec');}}}
function windowAt(c,p,x,y,w,h){R(c,x-9,y-9,w+18,h+9,'#e2bea0',22);R(c,x,y,w,h,'#cbe8e7',16);E(c,x+w*.78,y+h*.26,19,19,'#fff0be');
  c.save();c.beginPath();c.roundRect(x,y,w,h,16);c.clip();E(c,x+w*.12,y+h*.98,w*.24,h*.34,'#aacead');E(c,x+w*.88,y+h,w*.2,h*.42,'#a7cdb4');E(c,x+w*.55,y+h*1.02,w*.45,h*.16,'#d7e6b6');E(c,x+w*.4,y+h*.2,w*.1,6,'#ffffffb0');E(c,x+w*.47,y+h*.2,w*.08,8,'#ffffffb0');c.restore();
  L(c,x+w/2,y+4,x+w/2,y+h-2,'#fffaf0',7);L(c,x+4,y+h*.45,x+w-4,y+h*.45,'#fffaf0',7);
  for(let i=0;i<5;i++){R(c,x+i*5,y,6,h*.62-i*10,soft(p,.72),3);R(c,x+w-6-i*5,y,6,h*.62-i*10,soft(p,.72),3);}
  R(c,x-14,y+h,w+28,12,'#d4a487',5);R(c,x-10,y+h+1,w+20,4,'#e8c2a4',2);}
/** Framed little house on the wall: the `property` hotspot. */
function plaque(c,p,x,y,w,h){R(c,x,y,w,h,'#c89f7f',7);R(c,x+4,y+4,w-8,h-8,CREAM,5);const cx=x+w/2,b=y+h-9,s=w/40;
  P(c,[[cx-13*s,b-14*s],[cx,b-25*s],[cx+13*s,b-14*s]],p.primary);R(c,cx-10*s,b-15*s,20*s,15*s,soft(p,.6),2);R(c,cx-3*s,b-9*s,6*s,9*s,p.dark,2);}
/** Wall unit behind the second station: the `shelf` hotspot. */
function wallUnit(c,p,k,label,x,y,w,h,big){
  const head=big?30:26,ts=big?17:13,hw=big?Math.max(w,142):w-24,hx=x+w/2-hw/2;
  R(c,x-4,y+head-6,w+8,h-head+10,WOOD_D,10);R(c,x+2,y+head,w-4,h-head,k==='repair'?'#dcb68d':'#fff3e0',7);
  R(c,hx,y,hw,head,p.light,12,'#d9b7a1',1.5);T(c,label,x+w/2,y+head/2+1,fit(c,label,hw-12,ts),p.dark);
  const top=y+head,in_=h-head;
  if(k==='repair'){// pegboard with tools
    for(let yy=top+10;yy<y+h-4;yy+=13)for(let xx=x+10;xx<x+w-6;xx+=13)E(c,xx,yy,1.6,1.6,'#b48d64');
    const sx=w/158,sy=in_/116,X=v=>x+v*sx,Y=v=>top+v*sy;
    L(c,X(22),Y(14),X(22),Y(70),'#7e8c93',6);c.beginPath();c.arc(X(22),Y(12),8*sx,Math.PI*.15,Math.PI*1.85);c.strokeStyle='#7e8c93';c.lineWidth=5*sx;c.stroke();
    R(c,X(46),Y(10),8*sx,34*sy,'#e0795d',3);L(c,X(50),Y(44),X(50),Y(76),'#9aa6ab',3);
    L(c,X(72),Y(12),X(66),Y(64),'#6f8b95',5);L(c,X(80),Y(12),X(86),Y(64),'#6f8b95',5);R(c,X(62),Y(46),12*sx,20*sy,'#e0b65d',3);R(c,X(80),Y(46),12*sx,20*sy,'#e0b65d',3);
    R(c,X(104),Y(10),30*sx,12*sy,'#7e8c93',4);L(c,X(119),Y(20),X(119),Y(70),'#c8976c',6);
    c.beginPath();c.arc(X(40),Y(94),13*sx,0,Math.PI*2);c.strokeStyle='#e0795d';c.lineWidth=5*sx;c.stroke();E(c,X(40),Y(94),5*sx,5*sx,'#dcb68d');
    R(c,X(70),Y(84),24*sx,20*sy,'#f2c94c',5);E(c,X(82),Y(94),5*sx,5*sx,'#8a6d1f');
    c.beginPath();c.arc(X(120),Y(94),12*sx,0,Math.PI*2);c.strokeStyle='#5b9bd5';c.lineWidth=4*sx;c.stroke();c.beginPath();c.arc(X(120),Y(94),6*sx,0,Math.PI*2);c.stroke();
    return;}
  const rows=big?3:2,gap=in_/rows;
  for(let r=0;r<rows;r++){const base=top+gap*(r+1)-6;R(c,x,base,w,8,'#d6a581',2);R(c,x+3,base-1,w-6,3,'#efcbaa',1);
    const n=Math.max(4,Math.floor((w-16)/22));
    for(let i=0;i<n;i++){const xx=x+14+i*(w-28)/(n-1),j=r*n+i;
      if(k==='salon'){const tones=['#3d2719','#6d2433','#8c6440','#caa56c','#b25f86','#7d6a5a','#e0c58e','#9b7bb8'],col=tones[j%tones.length];
        if(j%3===2){R(c,xx-5,base-24,10,24,col,3);R(c,xx-5,base-30,10,7,'#f1ece6',2);}else{R(c,xx-7,base-30,14,30,col,5);R(c,xx-4,base-38,8,9,'#f6f1ea',2);R(c,xx-6,base-20,12,8,CREAM,2);}}
      else{// pet: shampoo, toys, brush
        const m=j%4;if(m===0){R(c,xx-7,base-30,14,30,['#a9d6c6','#eeb8c7','#b6c9e3'][j%3],5);L(c,xx,base-30,xx,base-38,'#9aa6ab',3);L(c,xx,base-38,xx+6,base-38,'#9aa6ab',3);paw(c,xx,base-14,.45,'#fff8ec');}
        else if(m===1){E(c,xx,base-9,9,9,'#f3a47e');L(c,xx-8,base-11,xx+8,base-7,'#fff3e6',2);}
        else if(m===2){L(c,xx-8,base-6,xx+8,base-12,'#f6ead7',5);for(const [bx,by] of [[-8,-6],[8,-12]]){E(c,xx+bx,by+base-3,3.5,3.5,'#f6ead7');E(c,xx+bx,by+base+2,3.5,3.5,'#f6ead7');}}
        else{R(c,xx-8,base-12,16,10,'#c8976c',3);for(let t=0;t<4;t++)L(c,xx-6+t*4,base-12,xx-6+t*4,base-17,'#6f5646',1.5);}}}}
}

/* ------------------------------------------------------------ Wall features above the main station */
function mirrors(c,p,x,y,w,h){const pw=(w-30)/2;
  for(const px of [x+10,x+w-10-pw]){R(c,px-8,y-8,pw+16,h+16,'#f3dfd2',[pw/2+8,pw/2+8,12,12],'#d9b39c',2);
    c.beginPath();c.roundRect(px,y,pw,h,[pw/2,pw/2,8,8]);const g=c.createLinearGradient(px,y,px+pw,y+h);g.addColorStop(0,'#e3f1f4');g.addColorStop(1,'#c9e0e6');c.fillStyle=g;c.fill();
    L(c,px+pw*.25,y+h*.45,px+pw*.55,y+h*.2,'#ffffffb8',6);L(c,px+pw*.35,y+h*.62,px+pw*.62,y+h*.4,'#ffffff80',4);
    const bulbs=[];for(let i=0;i<5;i++){const a=Math.PI+i*Math.PI/4;bulbs.push([px+pw/2+Math.cos(a)*(pw/2+2),y+pw/2+Math.sin(a)*(pw/2+2)]);}
    for(let yy=y+pw/2+22;yy<y+h-6;yy+=26){bulbs.push([px-3,yy],[px+pw+3,yy]);}
    for(const [bx,by] of bulbs){E(c,bx,by,6,6,'#fff6cf');E(c,bx,by,3.2,3.2,'#ffe391');}}
  const mx=x+w/2;R(c,mx-12,y+h*.52,24,6,WOOD_D,3);R(c,mx-7,y+h*.52-18,8,18,p.primary,3);R(c,mx+2,y+h*.52-13,6,13,'#a9d6c6',2);}
function tileWall(c,p,x,y,w,h,t,reduced){R(c,x,y+34,w,h-34,'#f5fbfb',14,'#cfe3e6',2);c.save();c.beginPath();c.roundRect(x,y+34,w,h-34,14);c.clip();
  for(let xx=x+26;xx<x+w;xx+=26)L(c,xx,y+34,xx,y+h,'#d9eaec',1.5);for(let yy=y+60;yy<y+h;yy+=26)L(c,x,yy,x+w,yy,'#d9eaec',1.5);R(c,x,y+h-58,w,20,soft(p,.72),0);c.restore();
  // towel hooks with towels over the table
  L(c,x+20,y+48,x+112,y+48,WOOD_D,5);for(const [i,col] of [soft(p,.45),p.mint,'#f6d8a8'].entries()){R(c,x+26+i*30,y+50,24,40,col,6);L(c,x+28+i*30,y+80,x+48+i*30,y+80,'#ffffff90',2);}
  // shower pipe and head over the tub
  const sx=x+w-44;L(c,sx,y+h-38,sx,y+62,METAL_D,5);L(c,sx,y+62,sx-34,y+62,METAL_D,5);E(c,sx-40,y+68,15,8,METAL);E(c,sx-40,y+72,12,4,'#b7c4c9');
  for(let i=0;i<5;i++){const off=reduced?0:((t*40+i*14)%40);E(c,sx-50+i*5,y+84+off,1.6,3,'#9fd1e0');}
  E(c,x+w-22,y+h-78,11,11,'#fff');paw(c,x+w-22,y+h-78,.6,p.primary);}
function ticketBoard(c,p,x,y,w,h){const bw=w*.62;R(c,x,y,bw,h-30,'#c89f7f',10);R(c,x+7,y+7,bw-14,h-44,'#e6c79f',6);
  for(let i=0;i<60;i++)E(c,x+14+(i*37%(bw-28)),y+14+(i*53%(h-58)),1.2,1.2,'#c9a57a');
  const cols=['#fff8e7','#fdeef3','#eef7f4','#fff3d6'];
  for(let r=0;r<2;r++)for(let i=0;i<3;i++){const tx=x+18+i*(bw-36)/3,ty=y+18+r*(h-60)/2,tw=(bw-54)/3;R(c,tx,ty,tw,(h-80)/2,cols[(r*3+i)%4],3,'#cdb79c',1);E(c,tx+tw/2,ty+2,4,4,[p.primary,'#e0795d','#6fae7c'][(r+i)%3]);
    for(let l=0;l<3;l++)L(c,tx+6,ty+12+l*8,tx+tw-8-(l===2?10:0),ty+12+l*8,'#c4b3a0',1.5);if((r+i)%2===0)L(c,tx+tw-14,ty+(h-80)/2-12,tx+tw-8,ty+(h-80)/2-6,'#6fae7c',2);}
  // round wall clock and a small circuit poster
  const cx=x+bw+(w-bw)/2,cy=y+30;E(c,cx,cy,26,26,'#fffaf0');c.beginPath();c.arc(cx,cy,26,0,Math.PI*2);c.strokeStyle=p.dark;c.lineWidth=4;c.stroke();L(c,cx,cy,cx,cy-15,p.dark,3);L(c,cx,cy,cx+10,cy+4,p.dark,3);
  R(c,cx-30,y+68,60,60,'#dcecef',6,'#9fb3ba',2);L(c,cx-20,y+84,cx+18,y+84,p.primary,2);L(c,cx-4,y+84,cx-4,y+112,p.primary,2);L(c,cx-20,y+112,cx+18,y+112,p.primary,2);R(c,cx-12,y+92,16,10,'#f2c94c',2);E(c,cx+12,y+100,4,4,'#e0795d');}

/* ------------------------------------------------------------ Floor pieces (local units, origin = middle of the feet line) */
function warehouse(w,p,ts){const c=w.ctx,k=look(w),words=w.words(),items=w.c?.ops?.security?.items||[];
  const body=k==='repair'?'#c9d9de':k==='salon'?'#f7e4ea':'#edcfae',edge=k==='repair'?'#86a1aa':k==='salon'?'#cf9fb3':'#c8a27e';
  E(c,0,0,42,7,SHADOW);R(c,-37,-168,74,166,edge,9);R(c,-32,-162,64,152,body,6);L(c,0,-160,0,-12,edge,2);
  E(c,-5,-78,2.6,2.6,edge);E(c,5,-78,2.6,2.6,edge);R(c,-34,-10,10,9,edge,2);R(c,24,-10,10,9,edge,2);
  if(k==='repair')for(let i=0;i<3;i++){L(c,-24,-150+i*6,-8,-150+i*6,edge,1.5);L(c,8,-150+i*6,24,-150+i*6,edge,1.5);}
  R(c,-29,-128,58,26,CREAM,7,edge,1.5);T(c,words.store,0,-114,fit(c,words.store,50,ts,800),'#6f5646',800);
  if(k==='salon'){for(let i=0;i<3;i++){R(c,-30+i*20,-184,18,16,[p.light,'#ffffff',p.mint][i],7,'#d8c3c9',1);E(c,-21+i*20,-176,3,3,'#e6d6da');}}
  else if(k==='pet_care'){P(c,[[-30,-168],[-2,-168],[-5,-202],[-27,-202]],'#e9b872');R(c,-30,-206,28,6,'#d7a35c',2);paw(c,-16,-184,.8,'#fff8ec');P(c,[[2,-168],[28,-168],[26,-194],[4,-194]],'#9fcfc2');R(c,4,-198,22,6,'#86b9ac',2);E(c,15,-180,5,5,'#fff8ec');}
  else{R(c,-30,-194,40,26,'#dcb68d',3,'#b48d64',1.5);L(c,-30,-186,10,-186,'#b48d64',1.5);R(c,12,-184,18,16,'#e0795d',3);}
  if(items.includes('lock')){R(c,6,-92,16,18,'#d8c596',5,'#a09675',1);c.beginPath();c.arc(14,-92,5,Math.PI,0);c.strokeStyle='#a09675';c.lineWidth=3;c.stroke();}}
function stationB(w,p){const c=w.ctx,k=look(w);E(c,0,0,74,8,SHADOW);
  if(k==='salon'){// shampoo bed: sloping cushion towards a basin
    R(c,-62,-28,100,26,'#f3e6ea',8,'#d6b3c1',2);R(c,-56,-8,8,8,'#cdb9c0',2);R(c,26,-8,8,8,'#cdb9c0',2);
    P(c,[[-66,-28],[38,-28],[38,-62],[-8,-54],[-66,-44]],p.primary);L(c,-62,-44,-8,-53,'#ffffff55',4);L(c,-8,-53,34,-60,'#ffffff55',4);
    R(c,-58,-54,26,10,'#fffaf6',5,'#e3cdd5',1);
    R(c,36,-44,32,42,'#fdf8f4',7,'#d4c3c3',2);E(c,52,-66,28,13,'#fffdfb');c.beginPath();c.ellipse(52,-66,28,13,0,0,Math.PI*2);c.strokeStyle='#cbbcc0';c.lineWidth=2;c.stroke();E(c,52,-68,21,7,'#d7e9ef');R(c,40,-62,12,6,p.dark,3);
    c.beginPath();c.moveTo(64,-70);c.lineTo(64,-96);c.quadraticCurveTo(64,-104,54,-102);c.strokeStyle=METAL_D;c.lineWidth=4;c.lineCap='round';c.stroke();E(c,52,-98,4,5,METAL);
    R(c,-24,-66,10,14,'#a9d6c6',3);R(c,-12,-64,9,12,'#f3d590',3);return;}
  if(k==='pet_care'){// boarding kennels, a cat and a dog peeking out
    R(c,-68,-118,136,116,'#e0bb94',10,'#c19870',2);
    for(let r=0;r<2;r++)for(let q=0;q<2;q++){const x=-63+q*65,y=-113+r*56,cx=x+30,cy=y+30;R(c,x,y,60,50,'#fff3e0',6);
      if(r===1&&q===0){E(c,cx,cy+12,22,11,soft(p,.6));E(c,cx-2,cy+6,15,9,'#b9b1ab');E(c,cx+10,cy+2,8,7,'#b9b1ab');L(c,cx+6,cy+2,cx+10,cy+2,'#6b5a52',1.2);}
      if(r===1&&q===1){E(c,cx,cy+14,22,8,p.mint);L(c,cx-8,cy+8,cx+8,cy+4,'#f6ead7',4);E(c,cx-9,cy+9,3,3,'#f6ead7');E(c,cx+9,cy+3,3,3,'#f6ead7');}
      for(let i=1;i<6;i++)L(c,x+i*10,y+3,x+i*10,y+48,'#b9a48e',2);R(c,x+44,y+22,8,8,'#d6c5a4',2);
      if(r===0&&q===0){// cat face in front of the bars
        E(c,cx,cy+2,16,13,'#f2c38f');P(c,[[cx-14,cy-4],[cx-12,cy-17],[cx-4,cy-10]],'#f2c38f');P(c,[[cx+14,cy-4],[cx+12,cy-17],[cx+4,cy-10]],'#f2c38f');
        E(c,cx-6,cy,2.4,3,'#5f4538');E(c,cx+6,cy,2.4,3,'#5f4538');E(c,cx,cy+5,2,1.5,'#d98f86');L(c,cx-8,cy+6,cx-17,cy+4,'#c79a73',1);L(c,cx+8,cy+6,cx+17,cy+4,'#c79a73',1);L(c,cx-6,cy-10,cx-3,cy-5,'#d99a5e',2);}
      if(r===0&&q===1){// dog face with floppy ears and paws on the rail
        E(c,cx-14,cy,6,11,'#9b6b4c');E(c,cx+14,cy,6,11,'#9b6b4c');E(c,cx,cy,14,13,'#d8a77b');E(c,cx,cy+6,8,6,'#f1d6b8');
        E(c,cx-5,cy-2,2.4,3,'#4b372d');E(c,cx+5,cy-2,2.4,3,'#4b372d');E(c,cx,cy+3,3,2.2,'#4b372d');E(c,cx,cy+9,2.5,2,'#e98f8f');E(c,cx-8,cy+22,5,4,'#d8a77b');E(c,cx+8,cy+22,5,4,'#d8a77b');}}
    R(c,-58,-120,26,10,CREAM,3,'#c19870',1);heart(c,-45,-114,.18,p.primary);R(c,8,-120,26,10,CREAM,3,'#c19870',1);paw(c,21,-114,.35,p.primary);return;}
  // repair: rack of devices waiting, each with a tag
  R(c,-66,-120,6,118,METAL_D,3);R(c,60,-120,6,118,METAL_D,3);for(const y of [-122,-64,-10])R(c,-68,y,136,7,METAL,3,METAL_D,1);
  // lower: rice cooker and radio
  R(c,-54,-44,40,32,'#fbf7f0',12,'#c8bdb0',1.5);R(c,-56,-50,44,10,'#e8e1d8',6);E(c,-34,-51,6,3,'#b9aea2');R(c,-40,-30,12,6,'#e0795d',2);tag(c,-20,-46,'#fff8e7');
  R(c,-4,-50,56,38,'#c9976b',7,'#a0724d',1.5);E(c,12,-31,12,12,'#8d6749');E(c,12,-31,8,8,'#6d5038');R(c,30,-44,16,6,'#f5e3c1',2);E(c,38,-24,5,5,'#f5e3c1');L(c,46,-50,58,-74,METAL_D,2);tag(c,-2,-48,'#fdeef3');
  // upper: desk fan, phone, kettle
  E(c,-40,-92,20,20,'#d7eef2');c.beginPath();c.arc(-40,-92,20,0,Math.PI*2);c.strokeStyle='#8fb4bd';c.lineWidth=2;c.stroke();for(let i=0;i<3;i++){c.save();c.translate(-40,-92);c.rotate(i*2.1+.3);E(c,0,-10,5,10,'#a8cbd3');c.restore();}E(c,-40,-92,4,4,'#6f8b95');R(c,-43,-72,6,8,'#8fb4bd',2);tag(c,-24,-108,'#eef7f4');
  R(c,-8,-96,20,30,'#3f4b52',4);R(c,-5,-93,14,22,'#9fd1e0',2);L(c,-3,-90,7,-78,'#ffffff',1);tag(c,6,-98,'#fff3d6');
  R(c,24,-94,30,28,'#e7eef0',10,'#9fb3ba',1.5);R(c,50,-88,8,12,'#9fb3ba',3);R(c,30,-100,18,7,'#c9d6da',3);tag(c,28,-100,'#fff8e7');}
function stationD(w,p){const c=w.ctx,k=look(w);E(c,0,0,32,6,SHADOW);
  if(k==='salon'){// hood dryer on a rolling stand
    for(const dx of [-22,-10,10,22])L(c,0,-6,dx,-1,METAL_D,4);for(const dx of [-22,22])E(c,dx,0,4,3,'#7c8a90');
    R(c,-3,-112,6,108,METAL_D,3);R(c,-9,-74,18,20,CREAM,5,'#c8bdb0',1.5);E(c,0,-67,3,3,p.primary);
    c.save();c.translate(6,-128);c.rotate(-.18);E(c,0,0,31,25,soft(p,.55));E(c,-6,-8,12,6,'#ffffff60');E(c,0,15,27,10,mixHex(p.primary,'#ffffff',.78));c.beginPath();c.ellipse(0,15,27,10,0,0,Math.PI*2);c.strokeStyle=p.primary;c.lineWidth=2;c.stroke();for(let i=0;i<3;i++)L(c,-14+i*10,-16,-12+i*10,-10,p.dark,1.5);c.restore();return;}
  if(k==='pet_care'){// blower on wheels with its hose to a nozzle
    R(c,12,-132,5,128,METAL_D,2);R(c,-26,-50,44,42,soft(p,.3),10,p.dark,1.5);for(let i=0;i<4;i++)L(c,-18,-40+i*7,8,-40+i*7,'#ffffff70',2);E(c,-17,-4,5,5,'#6f6a6a');E(c,11,-4,5,5,'#6f6a6a');
    c.beginPath();c.moveTo(-10,-50);c.bezierCurveTo(-34,-80,20,-96,-2,-126);c.strokeStyle='#b8c3c7';c.lineWidth=7;c.stroke();
    R(c,-12,-138,34,12,'#8fb4bd',5);for(let i=0;i<3;i++)L(c,-18-i*4,-140+i*6,-26-i*6,-142+i*8,'#bfe1ea',2);return;}
  // repair: chest of tiny parts drawers
  R(c,-27,-134,54,132,'#cfdde2',6,'#86a1aa',2);
  for(let r=0;r<6;r++)for(let q=0;q<3;q++){const x=-23+q*16,y=-128+r*20;R(c,x,y,14,17,'#f7fbfc',3,'#9fb3ba',1);R(c,x+4,y+10,6,2.5,'#86a1aa',1);E(c,x+7,y+5,2,2,['#e0795d','#f2c94c','#6fae7c','#5b9bd5'][(r+q)%4]);}
  E(c,-10,-140,11,6,'#e0795d');E(c,-10,-142,6,3,'#b85d45');R(c,6,-152,16,18,'#eef3f4',4,'#9fb3ba',1);for(let i=0;i<4;i++)E(c,10+i*3,-140,1.6,1.6,'#98a6ac');}
/** Fluffy little dog sitting on the grooming table, bow on its head. */
function poodle(c,p,x,y){const fur='#fbf5ee',ln='#e6d8c8';E(c,x+17,y-14,7,7,fur);E(c,x,y-18,19,18,fur);E(c,x-9,y-3,8,5,fur);E(c,x+9,y-3,8,5,fur);
  E(c,x-15,y-42,8,12,ln);E(c,x+15,y-42,8,12,ln);E(c,x,y-46,15,14,fur);E(c,x,y-60,9,7,fur);E(c,x,y-40,7,5,'#fffdf9');
  E(c,x-5,y-47,2.2,2.8,'#4b372d');E(c,x+5,y-47,2.2,2.8,'#4b372d');E(c,x,y-41,2.6,2,'#4b372d');E(c,x-9,y-42,3,2,'#f2b8b0');E(c,x+9,y-42,3,2,'#f2b8b0');
  c.beginPath();c.ellipse(x+2,y-32,9,4,0,0,Math.PI*2);c.strokeStyle='#e0795d';c.lineWidth=2.5;c.stroke();heart(c,x+8,y-62,.22,p.primary);}
function chair(c,p,x){E(c,x,-2,30,6,SHADOW);E(c,x,-6,24,6,'#cfc9cc');E(c,x,-8,19,4,'#e9e4e6');R(c,x-4,-32,8,26,'#bdb6b9',3);
  R(c,x-38,-66,12,34,p.dark,6);R(c,x+26,-66,12,34,p.dark,6);R(c,x-31,-54,62,22,p.primary,10);
  R(c,x-27,-118,54,70,p.primary,20);R(c,x-19,-110,38,52,'#ffffff2c',14);for(const [dx,dy] of [[-8,-96],[8,-96],[0,-80]])E(c,x+dx,dy,2.4,2.4,p.dark);
  L(c,x,-120,x,-128,p.dark,4);R(c,x-15,-138,30,13,p.dark,7);}
function mainStation(w,p,big){const c=w.ctx,k=w.career,cond=w.c?.ops?.equipment?.condition??100,check=w.c?.upgrades?.includes('workbench');
  E(c,0,0,128,9,SHADOW);
  if(k==='nail'){// manicure table: two stools, a hand cushion, the gel lamp glowing, a row of bottles
    chair(c,p,-82);chair(c,p,82);R(c,-52,-62,8,58,'#c8976c',3);R(c,44,-62,8,58,'#c8976c',3);R(c,-60,-74,120,14,'#f7e4ea',6,'#cf9fb3',2);
    R(c,-24,-88,30,12,soft(p,.6),6);R(c,14,-104,34,26,'#f4f1f7',8,'#b7a8d8',1.5);R(c,18,-84,26,6,'#6c4bd1',2);
    const t=w.reduced?0:w.time,g=.35+.15*Math.sin(t*2);c.fillStyle=`rgba(140,110,240,${g})`;c.fillRect(18,-82,26,4);
    for(let i=0;i<4;i++)bottle(c,-52+i*10,-76,.9,['#b5122e','#e6b3a6','#9cd9c0','#1d1d1f'][i]);}
  else if(k==='salon'){chair(c,p,-60);chair(c,p,60);
    R(c,-15,-72,30,68,'#f5e9ec',6,'#d1b1bd',1.5);L(c,-13,-50,13,-50,'#d1b1bd',1.5);L(c,-13,-28,13,-28,'#d1b1bd',1.5);E(c,-9,-3,3,3,'#9b9296');E(c,9,-3,3,3,'#9b9296');
    R(c,-11,-92,8,20,p.light,3,'#d1b1bd',1);R(c,-10,-98,6,6,'#9aa6ab',1);L(c,2,-80,12,-80,'#6f5646',2);for(let i=0;i<5;i++)L(c,3+i*2,-80,3+i*2,-75,'#6f5646',1);
    for(const dx of [-1,1]){c.beginPath();c.arc(2+dx*5,-38,3.5,0,Math.PI*2);c.strokeStyle=p.dark;c.lineWidth=1.6;c.stroke();}L(c,-3,-44,8,-60,METAL_D,1.8);L(c,7,-44,-4,-60,METAL_D,1.8);}
  else if(k==='pet_care'){// grooming table with its arm, and a raised tub
    L(c,-112,-60,-112,-4,METAL_D,5);L(c,-20,-60,-20,-4,METAL_D,5);L(c,-112,-26,-20,-26,METAL_D,3);
    R(c,-124,-72,116,14,'#e4ebee',6,'#9fb0b6',2);R(c,-118,-76,104,7,'#9fcfc2',3);
    L(c,-16,-74,-16,-176,METAL_D,5);L(c,-16,-176,-62,-176,METAL_D,5);L(c,-62,-174,-62,-110,'#e0795d',2);
    R(c,-118,-86,26,10,soft(p,.5),4,'#d8b8a6',1);R(c,-40,-84,18,7,'#c8976c',3);for(let i=0;i<5;i++)L(c,-38+i*4,-84,-38+i*4,-89,'#6f5646',1.2);
    poodle(c,p,-64,-76);
    R(c,6,-56,120,54,'#fbf7f2',8,'#d5c7b8',2);L(c,66,-52,66,-6,'#d5c7b8',1.5);E(c,58,-30,2.4,2.4,'#b9aea2');E(c,74,-30,2.4,2.4,'#b9aea2');
    R(c,2,-94,128,42,'#eaf6f8',18,'#a9c9d0',2);E(c,66,-88,56,7,'#cfe9ef');
    const t=w.reduced?0:w.time;for(const [bx,by,r] of [[30,-94,7],[44,-98,5],[92,-95,6],[104,-100,4],[70,-97,5]]){E(c,bx,by+Math.sin(t*2+bx)*1.2,r,r,'#ffffff');c.beginPath();c.arc(bx,by+Math.sin(t*2+bx)*1.2,r,0,Math.PI*2);c.strokeStyle='#cfe3e8';c.lineWidth=1;c.stroke();}
    E(c,22,-100,8,6,'#f7d56b');E(c,27,-107,5,5,'#f7d56b');P(c,[[31,-107],[36,-105],[31,-104]],'#e8a04c');E(c,28,-108,1,1,'#5f4538');}
  else{// repair bench: fan opened up, multimeter, soldering iron, phone, magnifier lamp
    R(c,-118,-62,10,60,'#c8976c',3);R(c,108,-62,10,60,'#c8976c',3);R(c,-114,-24,228,8,'#d9a878',3);
    R(c,-94,-44,52,20,p.primary,5);c.beginPath();c.roundRect(-80,-50,24,8,3);c.strokeStyle=p.dark;c.lineWidth=2;c.stroke();R(c,40,-38,56,14,'#dcb68d',3,'#b48d64',1.5);
    R(c,-126,-74,252,16,'#e3b082',6,'#b98a60',2);L(c,-120,-70,120,-70,'#f3d0a8',2);
    E(c,-84,-76,18,5,METAL_D);R(c,-87,-104,6,28,METAL_D,2);E(c,-84,-120,23,23,'#e6f3f6');c.beginPath();c.arc(-84,-120,23,0,Math.PI*2);c.strokeStyle='#8fb4bd';c.lineWidth=2;c.stroke();
    for(let i=0;i<3;i++){c.save();c.translate(-84,-120);c.rotate(i*2.1+.5);E(c,0,-11,6,11,'#a8cbd3');c.restore();}E(c,-84,-120,4,4,'#6f8b95');
    c.beginPath();c.ellipse(-44,-77,15,4,0,0,Math.PI*2);c.strokeStyle='#8fb4bd';c.lineWidth=2;c.stroke();
    R(c,-30,-108,28,34,'#f2c94c',6,'#b88f22',1.5);R(c,-26,-104,20,10,'#dfe9d6',2);E(c,-16,-84,6,6,'#8a6d1f');
    c.beginPath();c.moveTo(-26,-76);c.quadraticCurveTo(-40,-60,-62,-80);c.strokeStyle='#d9534f';c.lineWidth=2;c.stroke();c.beginPath();c.moveTo(-8,-76);c.quadraticCurveTo(-30,-56,-70,-86);c.strokeStyle='#3b3b3b';c.stroke();
    R(c,10,-90,34,16,'#8aa3ac',4);E(c,20,-82,3,3,'#e0795d');for(let i=0;i<4;i++)E(c,40,-96-i*4,5,2,'#9aa6ab');L(c,34,-96,58,-118,'#3f4b52',5);L(c,58,-118,66,-124,METAL,2.5);
    const t=w.reduced?0:w.time;c.strokeStyle='#ffffffb0';c.lineWidth=2;c.beginPath();c.moveTo(67,-126);for(let i=1;i<5;i++)c.lineTo(67+Math.sin(t*3+i)*4,-126-i*7);c.stroke();
    R(c,76,-104,20,30,'#3f4b52',4);R(c,79,-101,14,22,'#9fd1e0',2);L(c,81,-99,91,-84,'#ffffff',1);R(c,66,-80,40,6,'#9fcfc2',2);
    L(c,118,-74,112,-132,METAL_D,4);L(c,112,-132,80,-146,METAL_D,4);E(c,72,-144,15,15,'#e2f2f6c0');c.beginPath();c.arc(72,-144,15,0,Math.PI*2);c.strokeStyle='#6f8b95';c.lineWidth=3;c.stroke();}
  if(check){R(c,big?84:92,-40,24,30,CREAM,4,'#c7ad90',1.5);L(c,big?89:97,-30,big?93:101,-26,'#6fae7c',2);L(c,big?93:101,-26,big?101:109,-34,'#6fae7c',2);L(c,big?89:97,-18,big?103:111,-18,'#c4b3a0',1.5);}
  if(cond<100){const tw=big?124:92,th=big?28:20,ty=-164;L(c,-tw/2+8,ty-10,-tw/2+14,ty,'#b48d64',1.5);L(c,tw/2-8,ty-10,tw/2-14,ty,'#b48d64',1.5);R(c,-tw/2,ty,tw,th,'#f7d995',6,'#d3a35c',1.5);T(c,'CẦN KIỂM',0,ty+th/2+1,big?20:11,'#94643d',800);}}
function reception(w,p,half,big){const c=w.ctx,k=look(w);E(c,0,2,half+10,7,SHADOW);
  R(c,-half,-48,half*2,46,soft(p,.55),10,mixHex(p.primary,'#ffffff',.25),2);for(let x=-half+16;x<half-8;x+=18)L(c,x,-40,x,-10,'#ffffff30',2);
  emblem(c,p,w.career,0,-25,big?13:14);R(c,-half-6,-60,half*2+12,15,WOOD_L,6,WOOD_D,2);
  const bx=-half+(big?22:34),tx=half-(big?20:30);
  // appointment book / tickets (evidence)
  P(c,[[bx-22,-66],[bx,-62],[bx,-74],[bx-20,-78]],'#fff8e7');P(c,[[bx+22,-66],[bx,-62],[bx,-74],[bx+20,-78]],'#fffdf5');L(c,bx,-62,bx,-74,'#c7ad90',1.5);
  for(let i=0;i<2;i++){L(c,bx-16,-72+i*4+2,bx-4,-70+i*4+2,'#c4b3a0',1.2);L(c,bx+4,-70+i*4+2,bx+16,-72+i*4+2,'#c4b3a0',1.2);}L(c,bx+2,-64,bx+2,-56,p.primary,2);L(c,bx+14,-66,bx+26,-76,'#6f5646',2);
  // till / card terminal (counter)
  R(c,tx-16,-92,32,30,'#f7f2ea',6,'#b9a894',1.5);R(c,tx-12,-88,24,10,p.light,2);for(let i=0;i<3;i++)for(let j=0;j<2;j++)E(c,tx-7+i*7,-72+j*5,1.8,1.8,'#b9a894');R(c,tx-12,-100,24,8,'#fffdf8',2,'#d8cbbb',1);
  if(big)return;
  if(k==='salon'){L(c,-6,-64,-6,-92,'#8eaf82',2);bloom(c,-6,-96,10,p.primary);R(c,-14,-72,16,12,soft(p,.6),4);E(c,24,-66,9,5,'#e6c36b');E(c,24,-70,5,5,'#f3d590');}
  else if(k==='pet_care'){R(c,-14,-90,26,28,'#eaf4f5c0',8,'#a9c9d0',1.5);R(c,-12,-96,22,7,soft(p,.4),3);L(c,-6,-76,6,-80,'#f6ead7',4);E(c,-7,-76,2.6,2.6,'#f6ead7');E(c,7,-80,2.6,2.6,'#f6ead7');E(c,26,-66,9,4,p.primary);c.beginPath();c.arc(26,-74,7,Math.PI*.2,Math.PI*1.8);c.strokeStyle=p.dark;c.lineWidth=2;c.stroke();}
  else{R(c,-18,-82,24,20,'#fff8e7',3,'#cdb79c',1);R(c,-14,-86,24,20,'#fdeef3',3,'#cdb79c',1);L(c,20,-62,20,-90,METAL_D,2);R(c,14,-80,12,8,'#fff8e7',1);}}
function financeDesk(w,p,ts){const c=w.ctx,words=w.words();E(c,0,2,46,6,SHADOW);R(c,-42,-40,84,38,'#e2bd97',9,'#c49a74',2);R(c,-36,-34,72,24,'#f3dbbb',5);
  T(c,words.ledger,0,-22,fit(c,words.ledger,66,ts,800),'#6f5646',800);R(c,-46,-50,92,12,'#f0d2ad',5,'#c49a74',1.5);
  P(c,[[-24,-52],[0,-49],[0,-61],[-22,-64]],'#fff8e7');P(c,[[24,-52],[0,-49],[0,-61],[22,-64]],'#fffdf5');L(c,0,-49,0,-61,'#c7ad90',1.5);L(c,-18,-58,-5,-56,p.primary,1.5);L(c,5,-56,18,-58,'#c4b3a0',1.5);
  R(c,28,-66,14,16,'#eaf4f5c0',4,'#a9c9d0',1);E(c,35,-54,4,2,'#e6c36b');E(c,33,-58,4,2,'#f3d590');}
function waitBench(w,p){const c=w.ctx,k=look(w);E(c,0,2,70,6,SHADOW);
  for(const x of [-58,50])R(c,x,-22,8,22,'#b48d64',3);R(c,-66,-70,132,26,WOOD_D,10);R(c,-60,-66,120,18,SEAT,8);
  R(c,-68,-34,136,12,WOOD,6,WOOD_D,1.5);R(c,-62,-42,58,12,SEAT,6);R(c,4,-42,58,12,SEAT,6);heart(c,32,-54,.26,p.primary);
  if(k==='salon'){c.save();c.translate(-34,-44);c.rotate(-.12);R(c,-14,-8,28,8,'#b6c9e3',2);R(c,-12,-14,26,7,soft(p,.5),2);c.restore();P(c,[[-6,-44],[14,-46],[16,-54],[-4,-52]],'#fff8e7');E(c,6,-50,3,4,'#6d2433');}
  else if(k==='pet_care'){E(c,-30,-46,20,7,soft(p,.45));E(c,-30,-48,14,4,'#fff3e6');E(c,10,-48,6,6,'#f3a47e');L(c,24,-44,40,-44,'#9fcfc2',3);c.beginPath();c.arc(44,-48,5,0,Math.PI*2);c.strokeStyle='#9fcfc2';c.lineWidth=3;c.stroke();}
  else{R(c,-44,-48,34,8,'#f5f1e6',2,'#c4b3a0',1);L(c,-40,-45,-16,-45,'#c4b3a0',1);R(c,6,-54,12,12,'#f6e8c9c0',3,'#c49a74',1);E(c,12,-52,4,1.5,'#e8b97b');}}
function armchair(w,p){const c=w.ctx;E(c,0,2,40,6,SHADOW);for(const x of [-28,24])R(c,x,-14,5,14,'#b48d64',2);
  R(c,-30,-70,60,40,SEAT,16,SEAT_D,1.5);R(c,-36,-40,72,26,SEAT,10,SEAT_D,1.5);R(c,-40,-52,14,34,SEAT_D,7);R(c,26,-52,14,34,SEAT_D,7);heart(c,0,-52,.3,'#fff8ec');}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,k=look(w),words=w.words();
  E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#e3b694',35);R(c,96,168,1008,533,'#fff9ee',30,'#d9ac90',3);
  R(c,108,179,984,301,p.wall,22);wallPattern(c,p,k,108,179,984,262);
  floorTiles(c,p,k,108,445,984,244);R(c,108,434,984,13,'#ecd2b8',4);R(c,108,444,984,4,'#d8b597',2);
  bunting(c,p,k,250,720,198,10);
  wallUnit(c,p,k,words.shelf,232,214,158,172,false);
  if(k==='salon')mirrors(c,p,474,228,250,192);else if(k==='pet_care')tileWall(c,p,470,214,258,226,w.time,w.reduced);else ticketBoard(c,p,470,222,258,200);
  windowAt(c,p,740,226,230,178);
  plaque(c,p,982,282,36,40);
  streetBoard(c,p,1023,311);
  R(c,988,662,94,24,'#e7c3a7',8);for(let i=0;i<5;i++)L(c,998+i*18,666,998+i*18,682,'#d8ad8c',2);
  signBoard(c,p,370,62,460,100);
  for(let i=0;i<9;i++){E(c,98+Math.sin(i)*13,186+i*19,15,7,i%2?'#a2c596':'#81b095');E(c,1102+Math.cos(i)*10,185+i*19,15,7,i%2?'#a2c596':'#81b095');}
  w.securityProps();}
function portRoom(w,p){const c=w.ctx,k=look(w),words=w.words();
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#e1b594',31);R(c,29,117,642,724,'#fff9ed',26,'#d9ae91',3);
  R(c,40,139,620,406,p.wall,21);wallPattern(c,p,k,40,139,620,360);
  floorTiles(c,p,k,40,506,620,323);R(c,40,494,620,14,'#ecd2b8',4);R(c,40,505,620,4,'#d8b597',2);
  wallUnit(c,p,k,words.shelf,110,276,120,196,true);bunting(c,p,k,110,450,160,8);
  if(k==='salon')mirrors(c,p,243,226,218,258);else if(k==='pet_care')tileWall(c,p,240,206,224,290,w.time,w.reduced);else ticketBoard(c,p,240,232,226,236);
  windowAt(c,p,472,182,166,154);
  plaque(c,p,482,354,40,44);
  streetBoard(c,p,572,350,.92);
  R(c,484,818,112,18,'#e7c3a7',7);
  signBoard(c,p,135,34,430,100);
  for(let i=0;i<10;i++){E(c,34+Math.sin(i)*9,170+i*24,13,7,i%2?'#a2c596':'#81b095');E(c,665+Math.cos(i)*9,169+i*24,13,7,i%2?'#a2c596':'#81b095');}
  portSecurity(w,p);}
/** Portrait security gear, placed clear of this room's window and desk. */
function portSecurity(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[];
  if(items.includes('camera')){L(c,62,255,79,243,'#b89d84',4);R(c,73,231,39,22,'#f4f1e7',6,'#a5a89e',2);E(c,108,242,7,8,'#7a8992');E(c,109,242,3,4,'#b4d9df');}
  else{R(c,66,228,46,26,CREAM,8,'#d5b59a',1);T(c,'♧',89,241,17,p.dark);}
  if(items.includes('bell')){L(c,462,150,462,168,'#ad9073',2);P(c,[[451,186],[473,186],[470,170],[454,170]],'#f1d189');E(c,462,188,4,3,'#d3ad67');}
  if(items.includes('light')){const g=c.createRadialGradient(77,352,0,77,352,60);g.addColorStop(0,'#ffe2a56a');g.addColorStop(1,'#ffe2a500');c.fillStyle=g;c.fillRect(17,292,120,120);R(c,65,336,24,30,'#fff0bc',6,'#b89b7e',2);L(c,77,326,77,336,'#b89b7e',3);}}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,pl=PLAN.land,tier=w.c?.ops?.property?.tier||'cozy',open=w.c?.open,words=w.words(),out=[];
  out.push([540,()=>at(c,175,540,1,()=>warehouse(w,p,13))]);
  out.push([508,()=>at(c,304,508,1,()=>stationB(w,p))]);
  out.push([508,()=>at(c,421,508,1,()=>stationD(w,p))]);
  out.push([510,()=>at(c,599,510,1,()=>mainStation(w,p,false))]);
  out.push([534,()=>at(c,962,534,1,()=>reception(w,p,90,false))]);
  out.push([666,()=>at(c,922,666,1,()=>financeDesk(w,p,12))]);
  out.push([670,()=>at(c,213,670,1,()=>waitBench(w,p))]);
  out.push([668,()=>{L(c,990,650,984,668,'#b48d64',4);L(c,1078,650,1084,668,'#b48d64',4);openSign(c,p,972,622,open,words);}]);
  out.push([552,()=>plantAt(c,1075,548,.8)],[676,()=>plantAt(c,125,672,.85)]);
  if(tier!=='cozy')out.push([500,()=>at(c,805,500,1,()=>armchair(w,p))]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+4,()=>plantAt(c,x,y,.62)]);
  return out;}
function portProps(w,p){const c=w.ctx,pl=PLAN.port,tier=w.c?.ops?.property?.tier||'cozy',open=w.c?.open,words=w.words(),out=[];
  out.push([598,()=>at(c,77,598,.84,()=>warehouse(w,p,20))]);
  out.push([572,()=>at(c,169,572,.69,()=>stationB(w,p))]);
  out.push([572,()=>at(c,508,572,.88,()=>stationD(w,p))]);
  out.push([578,()=>at(c,352,578,.9,()=>mainStation(w,p,true))]);
  out.push([604,()=>at(c,602,604,1,()=>reception(w,p,50,true))]);
  out.push([708,()=>at(c,615,708,1,()=>financeDesk(w,p,16))]);
  out.push([820,()=>at(c,131,820,.97,()=>waitBench(w,p))]);
  out.push([820,()=>{const s=open?words.open_sign:words.closed_sign;L(c,492,806,486,822,'#b48d64',4);L(c,588,806,594,822,'#b48d64',4);R(c,476,770,128,38,'#fff8e8',14,'#c6a182',2);T(c,s,540,790,fit(c,s,116,17,800),p.dark,800);}]);
  out.push([832,()=>plantAt(c,50,830,.7)]);
  if(tier!=='cozy')out.push([820,()=>at(c,231,820,.72,()=>armchair(w,p))]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+4,()=>plantAt(c,x,y,.55)]);
  return out;}

/* ------------------------------------------------------------ the back rooms (scenes/backroom.js) */
/** Salon: Phòng gội (wash chairs, towels, supplies). Pet care: Phòng lưu chuồng (boarding pets, food).
 * Repair: Kho linh kiện (parts, the test bench). */
const WASH=room({id:'wash',name:'Phòng gội',icon:'🫧',back:'salon',sign:'PHÒNG GỘI ĐẦU',
  theme:{wall:'#f3eef6',wallLow:'#e2f0f3',floor:'#e6e0d8',floor2:'#ddd5cb',tile:56,rim:'#b9a8c9',trim:'#9fc7cf',ink:'#7a5e8c',door:'#9fc7cf'},
  win:{u0:.14,u1:.32,frame:'#e2f0f3'},clock:[.5,.27],
  items:[
    {k:'washchair',u:.32,v:.46,w:.14,h:120,spot:'workbench',label:'Ghế gội đầu'},
    {k:'washchair',u:.56,v:.46,w:.14,h:120,col:'#56606c',spot:'look:wash',label:'Ghế gội thứ hai'},
    {k:'shelf',u:.86,v:.1,w:.16,h:220,col:'#e8e0ee',board:'#b9a8c9',fill:['🧴','🧼','🪮','💆','🧽'],spot:'warehouse',label:'Kho vật tư'},
    {k:'basket',u:.15,v:.72,w:.1,h:40,fill:['#ffffff','#bfe7d8','#fde4ec']},
  ],
  looks:{wash:()=>'Nước ấm vừa tay, dầu gội hương bưởi. Khách nào cũng lim dim.'},
  chat:['Nước ấm vừa chưa chị?','Khăn sạch phơi xong rồi nè!','Khách hẹn 3 giờ tới sớm đó.'],
});
const KENNEL=room({id:'kennel',name:'Phòng lưu chuồng',icon:'🐾',back:'groom',sign:'PHÒNG LƯU CHUỒNG',
  theme:{wall:'#f4efe2',wallLow:'#e3efd9',floor:'#e2d6c2',floor2:'#d8cab3',tile:62,rim:'#b9a48f',trim:'#8fbf8a',ink:'#6f8a4f',door:'#8fbf8a'},
  clock:[.5,.27],
  items:[
    {k:'cages',u:.26,v:.1,w:.3,h:210,fill:['🐶','🐱','🐰','🐹','🐕','🐈'],spot:'look:cages',label:'Dãy chuồng'},
    {k:'cages',u:.64,v:.1,w:.24,h:210,fill:['🐱','🐶','🐹','🐈']},
    {k:'shelf',u:.88,v:.1,w:.14,h:220,fill:['🦴','🥫','🧸','🧼'],spot:'warehouse',label:'Kho thức ăn & vật tư'},
    {k:'table',u:.46,v:.62,w:.22,h:56,fill:['🥣','🦴','💊'],spot:'workbench',label:'Bàn chăm thú'},
  ],
  looks:{cages:w=>['Bé Mochi đang ngủ ngáy khò khò.','Một bé mèo thò chân ra đòi vuốt ve.','Hai bé cún ngồi nhìn bạn, đuôi vẫy tít.'][(w.c?.day||0)%3]},
  chat:['Bé lông xù đòi ra chơi kìa!','Tới giờ cho ăn chiều rồi nha.','Chuồng số 3 cần thay lót.'],
});
const PARTS=room({id:'parts',name:'Kho linh kiện',icon:'🔩',back:'shop',sign:'KHO LINH KIỆN',
  theme:{wall:'#eef1f3',wallLow:'#dfe5ea',floor:'#d6d0c6',floor2:'#ccc5ba',tile:60,rim:'#9aa6b0',trim:'#e3b04b',ink:'#4f6273',door:'#6d8aa5'},
  clock:[.6,.24],calendar:[.6,.42],
  items:[
    {k:'shelf',u:.22,v:.1,w:.22,h:240,col:'#9aa6b0',board:'#6d7880',fill:['#e3b04b','#9cc3d5','#e3a7b8','#b8d39c'],spot:'warehouse',label:'Kệ linh kiện'},
    {k:'boxes',u:.84,v:.1,w:.2,h:150,fill:['ỐC VÍT','DÂY ĐIỆN','PIN']},
    {k:'desk',u:.5,v:.6,w:.26,h:58,col:'#dfe5ea',book:'#4f6273',fill:['🔌','📻','🔋'],spot:'workbench',label:'Bàn thử máy'},
  ],
  chat:['Ai thấy cái tua vít bake đâu không?','Linh kiện mới về để kệ trên nha.','Cái quạt này chạy lại rồi nè!'],
});
const BACK={
  salon:[{id:'salon',name:'Phòng làm tóc',icon:'💇',main:true},WASH],
  pet_care:[{id:'groom',name:'Phòng chăm sóc',icon:'✂️',main:true},KENNEL],
  repair:[{id:'shop',name:'Tiệm sửa',icon:'🔧',main:true},PARTS],
};

export default {
  id:'service',
  areas:w=>BACK[w.career]||[],
  areaFor:w=>BACK[w.career]?shopFor(BACK[w.career][0].id)(w):null,
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
