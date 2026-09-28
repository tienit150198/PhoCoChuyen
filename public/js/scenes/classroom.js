/** Classroom scene (teacher): "Lớp học Mầm Nắng", a small primary class.
 * Back wall: alphabet strip, "HỌC TỐT · CHĂM NGOAN" banner, a big green
 * blackboard with today's lesson (the `workbench`), a sunny window where
 * Mướp naps, the class notebook pocket chart (`evidence`), the street notice
 * board, a wall clock, the class plaque (`property`) over the door.
 * Floor: the teacher's desk (`counter`) at the front left with the teacher's
 * lane behind it, rows of two-seat pupil desks with aisles, cubbies
 * (`warehouse`), a reading corner with rug and low bookshelf (`shelf`) and
 * the class fund cabinet (`finance`). PLAN schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,heart,bloom,plantAt,mascot,signBoard,streetBoard} from './kit.js';

/* ------------------------------------------------------------ Floor plan */
// Pupil desk footprints (chairs included): columns × rows.
const LAND_DESKS=[[370,480],[560,670],[750,860]].flatMap(([x0,x1])=>[[x0,574,x1,600],[x0,644,x1,670]]);
const PORT_DESKS=[[262,352],[432,522]].flatMap(([x0,x1])=>[[x0,672,x1,698],[x0,752,x1,778]]);

export const PLAN={
 land:{floor:[130,452,1070,682],lane:505,line:563,home:[600,505],kx:82,ky:45,sway:30,
   blocks:[[130,452,208,498],[140,532,280,562],[134,618,210,646],[990,560,1066,590],[1048,672,1070,682],...LAND_DESKS],
   bench:[150,655,262,678],garden:[[372,468],[842,468]],
   customers:[[520,620],[710,620],[905,640],[322,640]],event:[440,535],officer:[960,522],
   staff:{x:450,step:105,y:470},cat:[335,392],counterSpan:[0,0],
   decor:{corner:[300,468],front:[960,676],center:[950,470]},sill:{plant:[245,390],lamp:[272,390],seat:[290,390],rug:[600,540]},
   badge:{workbench:[150,40],board:[0,52]},
   spots:{shelf:[[172,600],50,[[255,620]]],evidence:[[845,262],50,[[845,505]]],workbench:[[595,310],85,[[595,505]]],counter:[[210,500],55,[[210,510]]],
     warehouse:[[168,410],50,[[245,480]]],board:[[845,372],42,[[845,505]]],finance:[[1028,535],42,[[950,575],[1028,620]]],
     property:[[1029,236],35,[[990,505]]],security:[[150,200],30,[[262,505]]],door:[[1029,405],55,[[1029,500]]],pet:[[335,372],38,[[335,505]]]}},
 port:{floor:[62,512,638,822],lane:572,line:626,home:[330,572],kx:51,ky:57,sway:24,
   blocks:[[62,512,118,560],[72,604,222,632],[64,706,140,734],[566,768,636,796],...PORT_DESKS],
   bench:[70,788,160,812],garden:[[600,520],[626,612]],
   customers:[[392,725],[590,685],[210,790],[392,806]],event:[575,600],officer:[440,645],
   staff:{x:250,step:85,y:532},cat:[152,338],counterSpan:[0,0],
   decor:{corner:[150,660],front:[300,815],center:[566,540]},sill:{plant:[66,336],lamp:[90,336],seat:[112,336],rug:[330,628]},
   badge:{workbench:[127,60],board:[0,70]},
   spots:{shelf:[[102,690],48,[[190,712]]],evidence:[[532,262],45,[[532,572]]],workbench:[[328,300],80,[[330,572]]],counter:[[147,580],52,[[147,575]]],
     warehouse:[[90,468],45,[[160,535]]],board:[[532,382],42,[[532,572]]],finance:[[601,742],42,[[601,812],[560,740]]],
     property:[[618,300],35,[[600,560]]],security:[[66,196],30,[[175,572]]],door:[[618,440],50,[[612,560]]],pet:[[152,318],38,[[200,560]]]}},
};

/* ------------------------------------------------------------ Pieces */
const PASTEL=['#eeb8c7','#a9d6c6','#b6c9e3','#e8cc95','#c9b5dc','#f6d8c1'];
const LETTERS=['A','Ă','Â','B','C','D','Đ','E','Ê','G','H','I','K','L','M','N','O','Ô','Ơ','P','Q','R','S','T','U','Ư','V','X','Y'];

/** Row of pastel alphabet cards along the top of the wall. */
function alphabet(c,x0,x1,y,size,count){const n=Math.min(count,LETTERS.length),gap=3,cw=(x1-x0-gap*(n-1))/n;
  L(c,x0-6,y-3,x1+6,y-3,'#cbb08e',2);
  for(let i=0;i<n;i++){const x=x0+i*(cw+gap);R(c,x,y,cw,size*1.6,PASTEL[i%6],5,'#c9ab8c',1);T(c,LETTERS[i],x+cw/2,y+size*.82,size,'#6d5646',800);}}

/** Paper banner with the class motto. */
function banner(c,p,cx,y,w,h,size){P(c,[[cx-w/2-18,y+4],[cx-w/2,y],[cx-w/2,y+h],[cx-w/2-18,y+h+4],[cx-w/2-8,y+h/2+2]],p.awning);P(c,[[cx+w/2+18,y+4],[cx+w/2,y],[cx+w/2,y+h],[cx+w/2+18,y+h+4],[cx+w/2+8,y+h/2+2]],p.awning);
  R(c,cx-w/2,y,w,h,'#fff6dc',8,'#d2b48f',2);const s='HỌC TỐT · CHĂM NGOAN';T(c,s,cx,y+h/2+1,fit(c,s,w-60,size,800),p.dark,800);
  T(c,'★',cx-w/2+16,y+h/2+1,size,'#e8b85c');T(c,'★',cx+w/2-16,y+h/2+1,size,'#e8b85c');}

/** A chalk apple. */
function chalkApple(c,x,y,r,col){E(c,x,y,r,r*.92,col);E(c,x-r*.35,y-r*.3,r*.28,r*.22,'#ffffff55');L(c,x,y-r*.8,x+r*.15,y-r*1.25,'#e9dcc0',Math.max(1.5,r*.18));E(c,x+r*.45,y-r*1.05,r*.35,r*.18,'#bfe0a4');}

/** The big green blackboard with today's lesson. Closed: the answer is up. */
function blackboard(c,p,x,y,w,h,k,open){
  R(c,x-12,y-6,w+24,h+22,'#8b73531a',14);R(c,x-10,y-10,w+20,h+20,'#b98a5e',12,'#946a45',2);R(c,x,y,w,h,'#3f6b55',6);
  E(c,x+w*.3,y+h*.35,w*.2,h*.22,'#ffffff08');E(c,x+w*.72,y+h*.62,w*.18,h*.2,'#ffffff07');
  T(c,'HÔM NAY MÌNH CÙNG HỌC',x+w/2,y+20*k,fit(c,'HÔM NAY MÌNH CÙNG HỌC',w-120*k,12*k,800),'#fff0c9',800);
  // Chalk sun doodle and a little flower in the corners.
  E(c,x+30*k,y+30*k,11*k,11*k,'#f3d98a');for(let i=0;i<8;i++){const a=i*Math.PI/4;L(c,x+30*k+Math.cos(a)*15*k,y+30*k+Math.sin(a)*15*k,x+30*k+Math.cos(a)*20*k,y+30*k+Math.sin(a)*20*k,'#f3d98a',2);}
  bloom(c,x+w-28*k,y+30*k,9*k,'#f2b9c9');
  T(c,open?'3 + 4 = ?':'3 + 4 = 7',x+w/2,y+h*.4,32*k,'#fff9e8',800);
  if(!open)T(c,'✓',x+w/2+100*k,y+h*.4,26*k,'#bfe0a4',800);
  // 3 red + 4 green apples so the sum can be counted.
  const r=8*k,gy=y+h*.66,step=24*k,start=x+w/2-3.5*step+step/2-10*k;
  for(let i=0;i<7;i++)chalkApple(c,start+i*step+(i>2?20*k:0),gy,r,i<3?'#f0a3a0':'#b9dca0');
  T(c,'+',start+2.5*step+10*k,gy,16*k,'#fff9e8',800);
  for(let i=0;i<5;i++)T(c,'★',x+w/2+(i-2)*22*k,y+h-16*k,15*k,i<3?'#f1cb73':'#9dc39a');
  // Chalk tray with chalk and a duster.
  R(c,x-6,y+h+6,w+12,9,'#c99c70',4,'#9d734f',1);R(c,x+20,y+h+1,26*k,8,'#fbf6e6',3);R(c,x+52*k,y+h+2,18*k,7,'#f5c7d3',3);R(c,x+w-70*k,y+h-4,44*k,13,'#8f6a4c',4);R(c,x+w-70*k,y+h+2,44*k,7,'#e9d8c3',3);}

/** Window with sky, sun, clouds, trees and curtains; returns the sill y. */
function window_(c,p,x,y,w,h,time,reduced){
  R(c,x-8,y-8,w+16,h+16,'#e2bea0',16);R(c,x,y,w,h,'#cbe8e7',11);c.save();c.beginPath();c.roundRect(x,y,w,h,11);c.clip();
  E(c,x+w*.72,y+h*.25,17,17,'#fff0be');const drift=reduced?0:(time*6)%(w+60);
  for(const [dx,dy] of [[.2,.2],[.62,.5]]){const cx=x+((w*dx+drift)%(w+60))-30;E(c,cx,y+h*dy,20,8,'#ffffffcc');E(c,cx+12,y+h*dy-5,12,8,'#ffffffcc');}
  E(c,x+w*.2,y+h*.86,w*.3,h*.3,'#aacead');E(c,x+w*.85,y+h*.9,w*.28,h*.34,'#a7cdb4');L(c,x+w*.2,y+h,x+w*.2,y+h*.8,'#a9876a',5);E(c,x+w*.55,y+h*1.02,w*.5,h*.14,'#d7e6b6');c.restore();
  L(c,x+w/2,y+2,x+w/2,y+h-2,'#fffaf0',6);L(c,x+2,y+h*.48,x+w-2,y+h*.48,'#fffaf0',6);
  for(let i=0;i<5;i++){R(c,x+i*5,y,6,h*.62-i*10,p.light,3);R(c,x+w-6-i*5,y,6,h*.62-i*10,p.light,3);}
  R(c,x-14,y+h+4,w+28,11,'#d4a487',5);return y+h+4;}

/** Round wall clock; the second hand ticks unless motion is reduced. */
function clock(c,p,x,y,r,time,reduced){E(c,x+2,y+3,r+3,r+3,'#8b73531c');E(c,x,y,r+3,r+3,p.primary);E(c,x,y,r,r,'#fffaf0');
  for(let i=0;i<12;i++){const a=i*Math.PI/6;E(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,1.4,1.4,'#b39b85');}
  L(c,x,y,x+r*.02,y-r*.55,'#6d5646',3);L(c,x,y,x+r*.45,y+r*.1,'#6d5646',3);const a=reduced?1:time*Math.PI/30;L(c,x,y,x+Math.sin(a)*r*.75,y-Math.cos(a)*r*.75,'#d27d7d',1.3);E(c,x,y,2.5,2.5,'#6d5646');}

/** Fabric pocket chart holding each pupil's "sổ liên lạc" (evidence). */
function pocketChart(c,p,x,y,w,h,size){R(c,x-3,y-3,w+6,h+6,'#c8a27e',8);R(c,x,y,w,h,'#fff7e7',6);L(c,x+w/2,y-14,x+10,y-2,'#b39070',1.5);L(c,x+w/2,y-14,x+w-10,y-2,'#b39070',1.5);E(c,x+w/2,y-14,3,3,'#b39070');
  const head=size*2.3;R(c,x+5,y+5,w-10,head,p.light,5);const t1='SỔ',t2='LIÊN LẠC';T(c,t1,x+w/2,y+5+head*.3,size,p.dark,800);T(c,t2,x+w/2,y+5+head*.74,fit(c,t2,w-12,size,800),p.dark,800);
  const top=y+head+12,rows=3,rh=(h-head-18)/rows;
  for(let r=0;r<rows;r++){const yy=top+r*rh;for(let i=0;i<3;i++){const bw=(w-22)/3,bx=x+7+i*(bw+4);R(c,bx,yy+2,bw,rh*.62,PASTEL[(r*3+i)%6],3,'#a98c70',1);R(c,bx+3,yy+5,bw-6,3,'#ffffff90',1);}
    R(c,x+4,yy+rh*.45,w-8,rh*.4,p.primary,3);R(c,x+4,yy+rh*.45,w-8,3,'#ffffff40',1);}}

/** Star sticker chart "BÉ NGOAN" (landscape only). */
function starChart(c,p,x,y,w,h){R(c,x,y,w,h,'#fffaf0',6,'#d2b48f',2);R(c,x+4,y+4,w-8,18,p.awning,4);T(c,'BÉ NGOAN',x+w/2,y+13,fit(c,'BÉ NGOAN',w-12,11,800),p.dark,800);
  for(let r=0;r<4;r++){L(c,x+6,y+34+r*17,x+w-6,y+34+r*17,'#e7d6bd',1);for(let i=0;i<4;i++)if((r*4+i)%5!==3)T(c,'★',x+14+i*((w-24)/3),y+29+r*17,11,['#f1cb73','#eaa5b5','#9dc39a','#9fbde0'][(r+i)%4]);}}

/** Door on the back wall with the open / closed sign. */
function door(c,p,x,y,w,h,size,open,words){R(c,x-8,y-8,w+16,h+8,'#d1a27f',10);R(c,x,y,w,h,'#f3dcc0',6,'#c49a78',2);
  if(open){R(c,x+3,y+3,w-6,h-3,'#efe4d0',4);R(c,x+3,y+h*.72,w-6,h*.28-1,'#dcc6a4',0);R(c,x+w*.24,y+h*.14,w*.46,h*.22,'#dff0ee',4,'#d6c2a3',1.5);L(c,x+w*.47,y+h*.14,x+w*.47,y+h*.36,'#fffaf0',2);L(c,x+3,y+h*.72,x+w-3,y+h*.72,'#cdb28e',2);
    const leaf=Math.min(12,w*.13);P(c,[[x+w-3,y+2],[x+w+leaf,y-4],[x+w+leaf,y+h+4],[x+w-3,y+h]],'#f3dcc0');P(c,[[x+w+1,y+h*.12],[x+w+leaf-3,y+h*.1],[x+w+leaf-3,y+h*.38],[x+w+1,y+h*.4]],'#cbe8e7');}
  else{R(c,x+w*.18,y+h*.1,w*.64,h*.3,'#cbe8e7',6,'#c49a78',2);L(c,x+w/2,y+h*.1,x+w/2,y+h*.4,'#fffaf0',3);R(c,x+w*.14,y+h*.55,w*.72,h*.36,'#ecd0b0',5);E(c,x+w-14,y+h*.52,4,4,'#c09a5b');}
  const s=open?words.open_sign:words.closed_sign,sw=w+18,sy=y+h*.44;L(c,x+w/2,sy-12,x+w/2-18,sy,'#b39070',1.5);L(c,x+w/2,sy-12,x+w/2+18,sy,'#b39070',1.5);
  R(c,x+w/2-sw/2,sy,sw,size*1.9,'#fff8e8',9,open?'#8fb77f':'#d59a9a',2);T(c,s,x+w/2,sy+size*.97,fit(c,s,sw-10,size,800),open?p.dark:'#a35f63',800);}

/** Class plaque over the door (the `property` hotspot). */
function plaque(c,p,cx,y,w,h,size){R(c,cx-w/2,y,w,h,p.primary,9,p.dark,2);R(c,cx-w/2+4,y+4,w-8,h-8,'#fffaf0',6);T(c,'LỚP 1A',cx,y+h/2+1,size,p.dark,800);heart(c,cx+w/2-11,y+h/2+4,.2,p.primary);}

/** Security equivalents: dome camera or a safety plaque, school bell, lamp. */
function security(c,p,items,cam,bell,lamp){
  if(items.includes('camera')){const [x,y]=cam;L(c,x-8,y+12,x+2,y+2,'#b79b85',4);R(c,x-4,y-10,36,20,'#f5f2eb',7,'#a7aaa2',2);E(c,x+26,y,7,8,'#7a8992');E(c,x+27,y,3,4,'#b4d9df');E(c,x+2,y-5,2,2,'#90bd8b');}
  else{const [x,y]=cam;R(c,x-6,y-11,38,22,'#fff6e9',8,'#d5b59a',1);T(c,'♧',x+13,y,14,p.dark);}
  if(items.includes('bell')){const [x,y]=bell;L(c,x,y-14,x,y-4,'#ac8f73',2);P(c,[[x-11,y+12],[x+11,y+12],[x+8,y-3],[x-8,y-3]],'#f0ce85');E(c,x,y-3,8,4,'#f0ce85');E(c,x,y+14,4,3,'#d4ad64');}
  if(items.includes('light')){const [x,y]=lamp,g=c.createRadialGradient(x,y+20,0,x,y+20,90);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(x-90,y-70,180,180);R(c,x-14,y-12,28,22,'#fff0b8',8,'#b69b79',2);}}

/** Tall cubby unit (warehouse): pastel bins, label plate, lock. */
function cubbies(c,p,x0,x1,top,base,size,label,locked){const w=x1-x0,h=base-top;E(c,x0+w/2,base+2,w*.6,7,'#8b73531c');
  R(c,x0,top,w,h,'#c8a27e',8,'#a98462',2);R(c,x0+5,top+size*2.2,w-10,h-size*2.2-8,'#f4dfc2',5);
  R(c,x0+6,top+5,w-12,size*1.7,'#fff7e7',6);T(c,label,x0+w/2,top+5+size*.87,fit(c,label,w-18,size,800),p.dark,800);
  const rows=3,iy=top+size*2.2+5,rh=(h-size*2.2-18)/rows,cw=(w-16)/2;
  for(let r=0;r<rows;r++)for(let i=0;i<2;i++){const bx=x0+8+i*cw,by=iy+r*rh;R(c,bx+1,by+rh*.28,cw-3,rh*.66,PASTEL[(r*2+i+1)%6],5,'#a98c70',1);R(c,bx+cw/2-7,by+rh*.44,12,5,'#ffffff90',2);if((r+i)%2===0)R(c,bx+6,by+rh*.12,8,rh*.2,PASTEL[(r+i+3)%6],2);}
  if(locked){const lx=x1-18,ly=top+size*2.2+10;R(c,lx-8,ly,16,18,'#d8c596',5,'#a59470',1);c.beginPath();c.arc(lx,ly,5,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=3;c.stroke();}}

/** Teacher's desk (counter): apple, book stack, hand bell, pencil cup. */
function teacherDesk(c,p,x0,x1,top,base,size,worn){const cx=(x0+x1)/2,w=x1-x0;E(c,cx,base+2,w*.56,8,'#8b73531c');
  R(c,x0+4,top+12,w-8,base-top-12,'#e6bd99',8,'#b99476',2);R(c,x0+12,top+22,w*.34,base-top-32,'#efcfab',6,'#c9a582',1.2);E(c,x0+12+w*.17,top+22+(base-top-32)/2,3,3,'#b08a67');
  R(c,cx+6,top+22,w*.36,(base-top-32)*.45,'#efcfab',5,'#c9a582',1.2);R(c,cx+6,top+22+(base-top-32)*.55,w*.36,(base-top-32)*.45,'#efcfab',5,'#c9a582',1.2);
  R(c,x0-6,top,w+12,16,'#f0cfa8',8,'#b99476',2);R(c,x0,top+2,w,4,'#f8e2c3',2);
  // On the desk: books, a red apple, a pencil cup and the hand bell.
  const by=top+1;R(c,x0+10,by-12,44*size,11,'#b6c9e3',3,'#8d9fb8',1);R(c,x0+14,by-22,40*size,10,'#eeb8c7',3,'#c18c9d',1);R(c,x0+8,by-31,42*size,9,'#e8cc95',3,'#b99c68',1);
  E(c,cx+2,by-11,10*size,10*size,'#e0676b');E(c,cx-2,by-14,3,2.5,'#ffffff70');L(c,cx+2,by-20*size,cx+4,by-25*size,'#8a6448',2);E(c,cx+9,by-23*size,6*size,3*size,'#8fbf78');
  R(c,cx+22*size,by-24*size,15*size,24*size,p.light,4,'#a89a7e',1);L(c,cx+26*size,by-24*size,cx+24*size,by-36*size,'#e8b85c',3);L(c,cx+32*size,by-24*size,cx+35*size,by-34*size,'#8fbfd0',3);
  const bx=x1-22;L(c,bx,by-30*size,bx,by-18*size,'#8a6448',4);P(c,[[bx-12*size,by-1],[bx+12*size,by-1],[bx+8*size,by-18*size],[bx-8*size,by-18*size]],'#f0ce85');E(c,bx,by-18*size,8*size,4,'#f0ce85');
  if(worn){R(c,x0+12,top+26,66,16,'#f7d995',4);T(c,'CẦN KIỂM',x0+45,top+34,9*size,'#94643d',800);}}

/** Two-seat pupil desk with its chairs; (x0..x1, base) is the footprint. */
function pupilDesk(c,p,x0,x1,base,k,v){const w=x1-x0,cx=(x0+x1)/2,top=base-50*k;E(c,cx,base,w*.52,6,'#8b73531a');
  L(c,x0+8,top+8,x0+8,base-14*k,'#b99270',4);L(c,x1-8,top+8,x1-8,base-14*k,'#b99270',4);
  R(c,x0+4,top+8,w-8,15*k,'#e9c8a0',4,'#c49c75',1.5);R(c,x0-2,top,w+4,10*k,'#f3d7ae',5,'#c49c75',1.5);
  // Things on the desk top.
  const ty=top+1;
  if(v%3!==2){R(c,x0+w*.14,ty-7*k,w*.28,8*k,'#fffaf0',2,'#c9b9a3',1);L(c,x0+w*.28,ty-7*k,x0+w*.28,ty+1,'#c9b9a3',1);}
  if(v%2===0){L(c,x0+w*.5,ty-3*k,x0+w*.68,ty-7*k,'#e8b85c',3);}else{E(c,x0+w*.6,ty-6*k,6*k,6*k,'#e0676b');L(c,x0+w*.6,ty-11*k,x0+w*.62,ty-14*k,'#8a6448',1.5);}
  if(v%3===2){R(c,x0+w*.16,ty-9*k,w*.22,9*k,PASTEL[(v+2)%6],2,'#a98c70',1);R(c,x0+w*.62,ty-8*k,w*.2,8*k,'#fffaf0',2,'#c9b9a3',1);}
  else R(c,x0+w*.74,ty-9*k,w*.14,9*k,PASTEL[(v+4)%6],2,'#a98c70',1);
  // Chairs face the blackboard: the viewer sees their backs.
  for(const f of [.27,.73]){const sx=x0+w*f,col=PASTEL[(v*2+(f>.5?1:0))%6];
    L(c,sx-12*k,base-18*k,sx-13*k,base,'#a98462',3);L(c,sx+12*k,base-18*k,sx+13*k,base,'#a98462',3);
    R(c,sx-16*k,base-21*k,32*k,7*k,'#d8b58f',3);R(c,sx-15*k,base-46*k,30*k,24*k,col,7,'#b08f73',1.5);R(c,sx-10*k,base-41*k,20*k,4*k,'#ffffff70',2);
    L(c,sx-11*k,base-22*k,sx-11*k,base-26*k,'#a98462',3);L(c,sx+11*k,base-22*k,sx+11*k,base-26*k,'#a98462',3);}}

/** Low bookshelf of the reading corner (shelf hotspot) with the class bear. */
function bookshelf(w,c,p,x0,x1,top,base,size){const wd=x1-x0;E(c,(x0+x1)/2,base+2,wd*.6,7,'#8b73531c');
  R(c,x0,top,wd,base-top,'#d6b492',8,'#b08c6c',2);R(c,x0+5,top+6,wd-10,base-top-12,'#fff3e0',5);
  const mid=top+(base-top)/2;R(c,x0+3,mid-2,wd-6,6,'#c9a27e',2);
  const spines=Math.floor((wd-14)/11);for(const [row,y1] of [[0,mid-2],[1,base-7]]){for(let i=0;i<spines;i++){const hgt=(y1-top)*(row?0:1)+(row?(y1-mid-4):-8);const bh=Math.min(hgt,(base-top)/2-12)-(i%3)*3;R(c,x0+8+i*11,y1-bh,9,bh,PASTEL[(i+row*2)%6],2,'#a98c70',.8);}}
  mascot(c,x0+wd*.3,top-14,.42*size);R(c,x0+wd*.55,top-24*size,wd*.35,22*size,'#fff7e7',5,'#c9a582',1);T(c,'♡',x0+wd*.725,top-13*size,12*size,p.primary);}

/** Reading rug with floor cushions (flat, behind people). */
function rug(c,p,x,y,rx,ry){E(c,x,y,rx,ry,p.mint);E(c,x,y,rx-8,ry-5,'#fff6e2');E(c,x,y,rx-16,ry-10,p.mint+'88');
  for(let i=0;i<10;i++){const a=i*Math.PI/5;E(c,x+Math.cos(a)*(rx-4),y+Math.sin(a)*(ry-2.5),3,2,'#ffffffaa');}
  E(c,x-rx*.45,y-ry*.1,17,8,'#f2b9c9');E(c,x+rx*.42,y+ry*.15,17,8,'#b6c9e3');}

/** Class fund cabinet (finance): piggy bank, coins, the class ledger. */
function fundCabinet(c,p,x0,x1,top,base,size,label,k=1){const w=x1-x0,cx=(x0+x1)/2;E(c,cx,base+2,w*.56,7,'#8b73531c');
  R(c,x0,top+10,w,base-top-10,'#d6b492',9,'#b08c6c',2);R(c,x0-5,top,w+10,13,'#eed3b0',5,'#c7a482',1.5);
  R(c,x0+8,top+20,w-16,base-top-30,'#fff7e8',6,'#d5b395',1);T(c,label,cx,top+20+(base-top-30)/2,fit(c,label,w-22,size,800),p.dark,800);
  // Piggy bank and a few coins on top.
  const py=top-12*k,px=cx-8;E(c,px,py,20*k,14*k,'#f2b9c9');E(c,px+18*k,py+1,6*k,5*k,'#eaa5b5');E(c,px+17*k,py+1,1.5,1.5,'#a26d7a');E(c,px+19.5*k,py+1,1.5,1.5,'#a26d7a');
  P(c,[[px+6*k,py-11*k],[px+12*k,py-16*k],[px+12*k,py-8*k]],'#eaa5b5');E(c,px+8*k,py-3*k,2,2,'#6a5944');R(c,px-6*k,py-13*k,10*k,2.5,'#a26d7a',1);
  L(c,px-10*k,py+10*k,px-10*k,py+14*k,'#d98fa0',4);L(c,px+8*k,py+10*k,px+8*k,py+14*k,'#d98fa0',4);
  for(let i=0;i<3;i++)E(c,x1-14,top-3-i*4,7*k,2.8,'#efc970');}

/** Kids' drawings pinned to the wall (portrait filler). */
function drawings(c,p,x,y,w,h){for(let i=0;i<2;i++){const dx=x+i*(w/2+4);R(c,dx,y,w/2-4,h,'#fffaf0',3,'#d9c3a6',1.5);E(c,dx+(w/2-4)/2,y-1,3,3,'#e0676b');}
  E(c,x+18,y+h*.35,8,8,'#f3d98a');L(c,x+8,y+h*.78,x+w/2-12,y+h*.78,'#9dc39a',3);heart(c,x+w*.75,y+h*.62,.45,'#eaa5b5');}

/** Low reading bench on the rug (sunny / garden tiers). */
function readingBench(c,p,x0,x1,top,base,size,garden){const w=x1-x0;E(c,(x0+x1)/2,base+1,w*.55,5,'#8b73531a');
  L(c,x0+10,top+10,x0+10,base,'#af8b6c',5);L(c,x1-10,top+10,x1-10,base,'#af8b6c',5);R(c,x0,top-size*.7,w,size*1.9,p.mint,8,'#9fb89a',1.5);
  T(c,'đọc sách',(x0+x1)/2,top+size*.25,fit(c,'đọc sách',w-16,size,700),p.dark);if(garden)bloom(c,x1-6,top-size*.7-4,size*.8,p.primary);}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  E(c,600,722,505,28,'#cba88d22');R(c,85,128,1030,590,'#e3b694',35);R(c,96,132,1008,574,'#fff9ee',30,'#d9ac90',3);
  // Wall, wainscot and a warm plank floor.
  R(c,108,142,984,318,p.wall,22);
  R(c,108,414,984,44,p.light,0);for(let x=120;x<1092;x+=24)L(c,x,418,x,456,'#ffffff80',2);R(c,108,409,984,8,'#e3c9a4',3);
  R(c,108,448,984,242,'#f5e2c3',16);c.save();c.beginPath();c.roundRect(108,448,984,242,16);c.clip();
  for(let i=0,y=452;y<690;i++,y+=30){R(c,108,y,984,30,i%2?'#f7e8cd':'#f2dcbb',0);for(let x=108+(i%3)*70;x<1092;x+=210)L(c,x,y+2,x,y+28,'#dfc39d',1.5);L(c,108,y,1092,y,'#e3c9a4',1);}c.restore();
  R(c,108,446,984,7,'#d8b594',3);
  signBoard(c,p,370,28,460,102);
  alphabet(c,122,1078,150,13,29);
  banner(c,p,595,186,330,30,15);
  blackboard(c,p,400,236,390,160,1,open);
  // Left: camera corner, clock, sunny window with Mướp's sill, cubbies below.
  clock(c,p,300,212,19,w.time,w.reduced);
  window_(c,p,225,244,150,132,w.time,w.reduced);
  // Right: class notebooks, street notice board, stars chart, clock plaque, door.
  pocketChart(c,p,806,212,78,108,12);
  streetBoard(c,p,812,334,1);
  starChart(c,p,893,244,72,108);
  plaque(c,p,1029,220,92,32,15);
  door(c,p,983,264,92,184,12,open,words);
  security(c,p,items,[134,200],[930,372],[1029,262]);
  if(w.c?.ops?.property?.tier==='garden'){for(let i=0;i<3;i++)bloom(c,240+i*50,380,7,[p.primary,'#f2b9c9','#f3d98a'][i]);}
  // Reading corner: rug on the floor in front of the low bookshelf.
  rug(c,p,238,662,92,20);}

function portRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#e1b594',31);R(c,29,117,642,724,'#fff9ed',26,'#d9ae91',3);
  R(c,40,139,620,372,p.wall,21);
  R(c,40,470,620,38,p.light,0);for(let x=52;x<660;x+=22)L(c,x,474,x,506,'#ffffff80',2);R(c,40,465,620,8,'#e3c9a4',3);
  R(c,40,504,620,325,'#f5e2c3',15);c.save();c.beginPath();c.roundRect(40,504,620,325,15);c.clip();
  for(let i=0,y=508;y<830;i++,y+=36){R(c,40,y,620,36,i%2?'#f7e8cd':'#f2dcbb',0);for(let x=40+(i%3)*60;x<660;x+=180)L(c,x,y+2,x,y+34,'#dfc39d',1.5);L(c,40,y,660,y,'#e3c9a4',1);}c.restore();
  R(c,40,502,620,7,'#d8b594',3);
  alphabet(c,52,648,146,16,18);
  signBoard(c,p,135,30,430,104);
  banner(c,p,328,182,250,32,17);
  blackboard(c,p,180,236,296,164,1.12,open);
  window_(c,p,50,226,118,98,w.time,w.reduced);
  drawings(c,p,56,356,112,40);
  pocketChart(c,p,492,214,80,118,16);
  streetBoard(c,p,500,346,1.2);
  clock(c,p,618,236,20,w.time,w.reduced);
  plaque(c,p,618,284,74,32,17);
  door(c,p,584,330,68,176,15,open,words);
  security(c,p,items,[52,196],[655,300],[618,322]);
  if(w.c?.ops?.property?.tier==='garden'){for(let i=0;i<3;i++)bloom(c,70+i*30,318,6,[p.primary,'#f2b9c9','#f3d98a'][i]);}
  rug(c,p,125,776,70,26);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',items=w.c?.ops?.security?.items||[],worn=(w.c?.ops?.equipment?.condition??100)<100,out=[];
  out.push([498,()=>cubbies(c,p,128,210,318,498,13,words.store,items.includes('lock'))]);
  out.push([562,()=>teacherDesk(c,p,138,282,486,562,1,worn)]);
  out.push([646,()=>bookshelf(w,c,p,132,212,590,646,1)]);
  out.push([590,()=>fundCabinet(c,p,988,1068,528,590,12,words.ledger)]);
  LAND_DESKS.forEach(([x0,,x1,y1],i)=>out.push([y1,()=>pupilDesk(c,p,x0,x1,y1,1,i)]));
  out.push([682,()=>plantAt(c,1060,680,.62)]);
  if(tier!=='cozy')out.push([678,()=>readingBench(c,p,150,262,652,678,11,tier==='garden')]);
  if(tier==='garden')for(const [x,y] of w.plan().garden)out.push([y+4,()=>plantAt(c,x,y,.55)]);
  return out;}

function portProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',items=w.c?.ops?.security?.items||[],worn=(w.c?.ops?.equipment?.condition??100)<100,out=[];
  out.push([560,()=>cubbies(c,p,56,124,400,560,16,words.store,items.includes('lock'))]);
  out.push([632,()=>teacherDesk(c,p,70,224,558,632,1.1,worn)]);
  out.push([734,()=>bookshelf(w,c,p,62,142,672,734,1.2)]);
  out.push([796,()=>fundCabinet(c,p,564,638,730,796,16,words.ledger,1.15)]);
  PORT_DESKS.forEach(([x0,,x1,y1],i)=>out.push([y1,()=>pupilDesk(c,p,x0,x1,y1,1,i)]));
    if(tier!=='cozy')out.push([812,()=>readingBench(c,p,70,160,784,812,16,tier==='garden')]);
  if(tier==='garden')for(const [x,y] of w.plan().garden)out.push([y+4,()=>plantAt(c,x,y,.5)]);
  return out;}

export default {
  id:'classroom',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
