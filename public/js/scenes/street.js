/** Street scene (kind `street`): an outdoor pavement in front of a row of
 * Vietnamese shophouses, with a strip of road and a crosswalk at the front.
 * delivery: the depot of "Giao Nhanh Mây Chiều" — parcel shelves behind an
 *   open roller shutter, a weighing counter, a parked scooter with its box,
 *   a route map on an easel, a parcel cage and a helmet rack.
 * tour_guide: the meeting point of "Mây Lang Thang" — a small tour office
 *   with postcards, a meeting desk, a bus stop, a parked minibus, a route
 *   board, a flag pole with the map stand and the group's luggage.
 * Both careers share one plan (see shop.js for the PLAN schema); only the
 * drawing on each footprint changes. */
import {R,E,L,T,P,fit,heart,bloom,plantAt,signBoard,streetBoard} from './kit.js';

export const PLAN={
 land:{badge:{board:[31,-23]},floor:[110,470,1090,658],lane:525,line:580,home:[800,530],kx:82,ky:45,sway:38,
   blocks:[[120,478,215,540],[175,592,330,622],[570,462,750,492],[872,478,928,496],[990,560,1080,585],[995,628,1065,645]],
   bench:[640,642,765,658],garden:[[300,484],[780,484]],
   customers:[[455,620],[580,634],[705,620],[830,638]],event:[340,652],officer:[885,598],
   staff:{x:360,step:125,y:565},cat:[262,440],counterSpan:[570,750],
   decor:{corner:[140,652],front:[880,655],center:[520,656]},sill:{plant:[420,266],lamp:[480,266],seat:[540,266],rug:[600,622]},
   spots:{shelf:[[450,372],100,[[450,525]]],evidence:[[900,418],60,[[900,525]]],workbench:[[252,560],62,[[360,606],[252,572]]],counter:[[660,428],60,[[660,525]]],
     warehouse:[[167,470],48,[[167,566],[250,525]]],board:[[1045,360],48,[[1045,525]]],finance:[[1035,540],42,[[950,572],[1035,606]]],
     property:[[332,232],35,[[380,525]]],security:[[262,228],30,[[250,525]]],door:[[1030,606],45,[[950,636],[1030,612]]],pet:[[262,420],38,[[262,525]]]}},
 port:{badge:{board:[46,-40]},floor:[48,512,652,792],lane:575,line:630,home:[165,615],kx:51,ky:57,sway:24,
   blocks:[[50,515,132,582],[66,690,222,722],[340,512,492,542],[578,522,634,545],[562,678,652,700],[470,764,574,782]],
   bench:[548,742,648,758],garden:[[190,522],[520,522]],
   customers:[[230,650],[350,660],[470,648],[330,740]],event:[290,790],officer:[410,790],
   staff:{x:250,step:105,y:612},cat:[505,500],counterSpan:[340,492],
   decor:{corner:[72,770],front:[622,792],center:[430,712]},sill:{plant:[220,300],lamp:[275,300],seat:[340,300],rug:[330,700]},
   spots:{shelf:[[280,412],100,[[280,575]]],evidence:[[606,470],55,[[606,582]]],workbench:[[144,650],58,[[262,706],[144,676]]],counter:[[416,470],56,[[416,575]]],
     warehouse:[[92,545],45,[[92,615],[165,575]]],board:[[82,342],50,[[165,575]]],finance:[[607,655],42,[[520,690],[607,730]]],
     property:[[168,240],35,[[230,575]]],security:[[85,247],30,[[165,575]]],door:[[522,742],45,[[430,772],[522,742]]],pet:[[505,480],38,[[520,578]]]}},
};

const OUT='#c79b85',WOOD='#c89f7f',WOOD_D='#a57d5f',SHUT='#8fbfa6',SHUT_D='#6f9f86',GLASS='#cfe7ea',ROOF='#e0957a',ROOF_D='#c07a62';
/** Scene frame per orientation: the rounded diorama card and its layers. */
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,road:680,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,road:812,sign:[135,30,430,104]}};

/* ------------------------------------------------------------ Backdrop */
function cloud(c,x,y,s){E(c,x,y,34*s,15*s,'#ffffffcc');E(c,x-24*s,y+4*s,22*s,11*s,'#ffffffcc');E(c,x+26*s,y+3*s,24*s,12*s,'#ffffffcc');E(c,x-4*s,y-10*s,20*s,13*s,'#ffffffdd');}
function sky(c,w,f){const g=c.createLinearGradient(0,f.y,0,f.base);g.addColorStop(0,'#cfe8ee');g.addColorStop(.7,'#f6f1df');g.addColorStop(1,'#fdeccf');
  c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  const drift=w.reduced?0:Math.sin(w.time*.08)*14,port=f===F.port;
  E(c,port?600:1030,port?175:170,port?26:30,port?26:30,'#fff3c4');E(c,port?600:1030,port?175:170,port?19:22,port?19:22,'#fde8a6');
  if(port){cloud(c,95+drift,170,.8);cloud(c,470-drift,160,.6);}else{cloud(c,190+drift,160,1);cloud(c,905-drift,150,.75);cloud(c,640+drift*.5,168,.55);}
}
function tree(c,x,base,top,s=1){L(c,x,base,x,top+40*s,'#a07a5a',9*s);L(c,x,top+70*s,x+18*s,top+46*s,'#a07a5a',4*s);
  for(const [dx,dy,r,col] of [[-30,30,34,'#86b893'],[28,26,36,'#94c49c'],[0,0,40,'#a3cea4'],[-8,36,30,'#7fb08c'],[20,-14,24,'#b2d6ad']])E(c,x+dx*s,top+dy*s,r*s,r*.86*s,col);
  E(c,x-10*s,top-8*s,9*s,6*s,'#ffffff30');}
/** A pole of the power lines, with two cross arms. */
function pole(c,x,base,top){L(c,x,base,x,top,'#b7a391',7);L(c,x-20,top+14,x+20,top+14,'#a69280',4);L(c,x-15,top+30,x+15,top+30,'#a69280',4);for(const dx of [-17,17])E(c,x+dx,top+11,3,4,'#e9ddc9');}
function wires(c,x0,x1,y0,y1,sag){c.strokeStyle='#8f7f7299';c.lineWidth=1.6;for(const [dy,k] of [[14,1],[30,.8],[22,1.2]]){c.beginPath();c.moveTo(x0,y0+dy);c.quadraticCurveTo((x0+x1)/2,Math.max(y0,y1)+dy+sag*k,x1,y1+dy);c.stroke();}}
/** A window with green louvred shutters. */
function win(c,cx,y,w,h,shut=SHUT){R(c,cx-w/2-4,y-4,w+8,h+8,'#fff8ec',6,'#d6b394',1.5);R(c,cx-w/2,y,w,h,GLASS,4);E(c,cx-w/4,y+h/3,w/7,h/5,'#ffffff55');L(c,cx,y,cx,y+h,'#fff8ec',3);
  for(const s of [-1,1]){const sx=s<0?cx-w/2-17:cx+w/2+3;R(c,sx,y-2,14,h+4,shut,3,SHUT_D,1);for(let yy=y+5;yy<y+h;yy+=7)L(c,sx+3,yy,sx+11,yy,SHUT_D,1);}}
/** Balcony ledge with railing and little pots; `y` is the ledge top. */
function balcony(c,x,y,w,pots=true){R(c,x,y,w,8,'#ecd3b6',3,'#c9a585',1.2);L(c,x+2,y-22,x+w-2,y-22,'#b98f73',3);for(let xx=x+10;xx<x+w-4;xx+=13)L(c,xx,y-21,xx,y,'#c7a084',1.6);
  if(pots)for(let xx=x+22;xx<x+w-10;xx+=Math.max(60,w/3)){R(c,xx-8,y-34,16,12,'#e4ad92',3);E(c,xx,y-38,11,8,'#8dbb8f');bloom(c,xx+4,y-42,5,'#f2b7c3');}}
/** A shophouse facade from `top` down to the pavement at `base`. */
function house(c,x,top,w,base,col,{wins=1,ww=44,wh=52,shut=SHUT,bal=true,roof=ROOF}={}){
  R(c,x,top,w,base-top+2,col,6,'#d6b394',2);
  R(c,x-6,top-13,w+12,18,roof,8,ROOF_D,1.5);for(let xx=x;xx<x+w;xx+=16)E(c,xx+8,top+5,8,4,roof);
  for(let i=0;i<wins;i++)win(c,x+w*(i+.5)/wins,top+26,ww,wh,shut);
  if(bal)balcony(c,x+8,top+26+wh+10,w-16);
}
/** Pavement tiles, curb and the road strip with a crosswalk. */
function street(c,f,x0,x1){const {base,curb,road}=f,bottom=f.y+f.h;
  R(c,f.x,base,f.w,curb-base,'#f4e4cc',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,curb-base);c.clip();
  const tw=f===F.port?50:56,th=f===F.port?36:34;
  for(let y=base,row=0;y<curb;y+=th,row++)for(let x=f.x-(row%2)*tw/2;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%3===0?'#f8ead5':'#efdcc1';c.fillRect(x+1.5,y+1.5,tw-3,th-3);}
  c.restore();
  R(c,f.x,base-4,f.w,8,'#e7cfb0',2);
  R(c,f.x,curb,f.w,road-curb,'#e2cdb2',0);L(c,f.x,curb,f.x+f.w,curb,'#c9ab8c',2);
  R(c,f.x,road,f.w,bottom-road,'#b9c3c6',0);
  for(let x=x0;x<x1;x+=34)R(c,x,road+6,20,bottom-road-4,'#f5f3ea',3);
  for(let x=f.x+20;x<f.x+f.w;x+=110)if(x+50<x0-10||x>x1+10)R(c,x,road+(bottom-road)/2-2,50,4,'#f1e7c8',2);
}

/* ------------------------------------------------------------ Shop front */
/** The open ground floor: interior, rolled shutter, hanging bulbs. */
function opening(c,w,x,y,W,H){R(c,x,y,W,H,'#f6e6cd',4);R(c,x,y+H*.62,W,H*.38,'#efd8b8',0);R(c,x,y+H-10,W,10,'#e3c7a3',0);
  for(let i=0;i<4;i++){const bx=x+W*(i+.5)/4;L(c,bx,y,bx,y+16,'#b99f86',1.2);E(c,bx,y+21,5,7,'#ffe8a4');}
  R(c,x-8,y-16,W+16,20,'#d6d8d3',9,'#a8aca6',1.5);for(let xx=x;xx<x+W;xx+=22)L(c,xx,y-12,xx,y,'#c3c6c0',1);
  if(!w.c?.open){const h=H*.42;R(c,x,y,W,h,'#dfe1dc',3,'#a8aca6',1.5);for(let yy=y+8;yy<y+h;yy+=9)L(c,x+4,yy,x+W-4,yy,'#c6c9c3',1.2);R(c,x+W/2-22,y+h-10,44,7,'#a8aca6',3);}
}
/** Brown parcel with tape and label; (x,y) is its bottom-left. */
function parcel(c,x,y,bw,bh,col='#e2b68a',tag=null){R(c,x,y-bh,bw,bh,col,3,'#b9895f',1.3);R(c,x+bw/2-3,y-bh,6,bh,'#f4dfb4',1);R(c,x+4,y-bh+5,Math.min(14,bw/3),Math.min(9,bh/3),tag||'#fff8ec',1.5);}
function parcelShelf(c,p,w,x,y,W,H,port){R(c,x-4,y-4,W+8,H+6,'#dcb396',8,'#b78b6c',2);R(c,x+4,y+4,W-8,H-6,'#fff3e0',5);
  const rows=3,rh=(H-12)/rows,tags=[p.primary,'#a9d6c6','#b6c9e3',p.light];
  for(let r=0;r<rows;r++){const by=y+8+rh*(r+1);let xx=x+10,k=r;
    while(xx<x+W-26){const bw=18+((k*7)%3)*8,bh=Math.min(rh-10,18+((k*5)%3)*7);if(xx+bw>x+W-8)break;parcel(c,xx,by-4,bw,bh,k%3?'#e2b68a':'#d8a879',tags[k%4]);xx+=bw+5;k++;}
    R(c,x,by-5,W,7,'#d6a581',2);}
  const label=w.words().shelf,size=port?17:13,pw=Math.max(W-20,fit(c,label,W+40,size)*label.length*.62+26);
  R(c,x+W/2-pw/2,y-34,pw,port?30:26,p.light,11,'#d9b7a1',1.5);T(c,label,x+W/2,y-34+(port?15:13),fit(c,label,pw-16,size),p.dark);
}
/** Postcard wall for the tour office. */
function postcardWall(c,p,w,x,y,W,H,port){R(c,x-4,y-4,W+8,H+6,'#dcb396',8,'#b78b6c',2);R(c,x+4,y+4,W-8,H-6,'#fff6e6',5);
  const cols=Math.max(3,Math.floor((W-16)/38)),rows=3,cw=(W-16)/cols,rh=(H-16)/rows,cards=['#f4c7c3','#bfe0d8','#c8d6f0','#f6dfa3','#d9c8ec'];
  for(let r=0;r<rows;r++)for(let k=0;k<cols;k++){const cx=x+8+k*cw+cw/2,cy=y+10+r*rh+rh/2,tilt=((r+k)%3-1)*.06;c.save();c.translate(cx,cy);c.rotate(tilt);
    R(c,-cw/2+4,-rh/2+4,cw-8,rh-10,'#fffaf0',3,'#d9c3a8',1);R(c,-cw/2+7,-rh/2+7,cw-14,rh-22,cards[(r*cols+k)%5],2);
    const s=(r*cols+k)%3;if(s===0){P(c,[[-cw/2+8,rh/2-15],[-3,-rh/2+10],[cw/2-8,rh/2-15]],'#8fbf9c');}else if(s===1){E(c,0,-3,6,6,'#fff3c4');L(c,-cw/2+8,rh/2-17,cw/2-8,rh/2-17,'#8cc0cf',3);}else heart(c,0,2,.3,p.primary);
    c.restore();}
  const label=w.words().shelf,size=port?17:13,pw=W+(port?34:10);
  R(c,x+W/2-pw/2,y-34,pw,port?30:26,p.light,11,'#d9b7a1',1.5);T(c,label,x+W/2,y-34+(port?15:13),fit(c,label,pw-16,size),p.dark);
}
/** Travel poster on the tour office's back wall. */
function travelPoster(c,p,x,y,W,H){R(c,x,y,W,H,'#fffaf0',6,'#d6b394',2);R(c,x+6,y+6,W-12,H-12,'#cfe9ee',4);E(c,x+W*.72,y+H*.3,9,9,'#fff0bb');
  P(c,[[x+6,y+H-6],[x+W*.28,y+H*.35],[x+W*.5,y+H-6]],'#8fbf9c');P(c,[[x+W*.32,y+H-6],[x+W*.58,y+H*.45],[x+W-6,y+H-6]],'#a8cfa6');R(c,x+6,y+H-18,W-12,12,'#8cc0cf',2);
  P(c,[[x+W*.25,y+H-20],[x+W*.4,y+H-20],[x+W*.36,y+H-14],[x+W*.28,y+H-14]],'#e7a283');}
/** Wall-mounted helmet rack (delivery). */
function helmetRack(c,p,x,y,n=3){R(c,x,y,n*30+10,8,WOOD,3,WOOD_D,1);for(let i=0;i<n;i++){const hx=x+20+i*30;L(c,hx,y+8,hx,y+13,WOOD_D,2);
  c.beginPath();c.arc(hx,y+28,13,Math.PI,0);c.fillStyle=[p.primary,'#9fc6d8','#f2c96f'][i%3];c.fill();R(c,hx-14,y+26,28,5,'#fff6e6',2);R(c,hx+2,y+20,10,6,'#dff1f4',2);}}
function fuelCan(c,x,base){R(c,x,base-34,30,34,'#e07a6a',5,'#b85a4e',1.5);R(c,x+18,base-42,8,10,'#b85a4e',2);L(c,x+4,base-38,x+14,base-38,'#b85a4e',3);R(c,x+6,base-24,18,12,'#fff3e0',2);}
/** The tour minibus parked in the bay, facing left. */
function minibus(c,p,x,base,len,title,port){const h=port?150:118,top=base-h-6;
  if(port){R(c,x+40,top-12,len-70,6,'#8b8480',3);R(c,x+56,top-30,40,20,'#f2c96f',5,'#c89f4f',1.2);R(c,x+102,top-26,34,16,'#e6a9a0',5,'#c78c83',1.2);}
  E(c,x+len/2,base+2,len/2,7,'#7a5e4420');
  R(c,x,top,len,h,'#fff6e6',22,OUT,2);R(c,x,top+h*.62,len,h*.38-6,p.primary,10);R(c,x+4,top+4,len-8,14,p.light,10);
  const n=Math.max(2,Math.floor((len-70)/46));for(let i=0;i<n;i++)R(c,x+58+i*46,top+22,38,34,GLASS,7,'#b8cdd0',1.2);
  R(c,x+8,top+22,40,44,GLASS,10,'#b8cdd0',1.2);E(c,x+18,top+34,6,8,'#ffffff66');
  T(c,title,x+len/2+16,top+h*.62+16,fit(c,title,len-70,port?16:14,800),'#fffaf0',800);
  E(c,x+6,top+h-24,6,5,'#fff0bb');
  for(const wx of [x+44,x+len-44]){E(c,wx,base-6,17,17,'#6e6360');E(c,wx,base-6,8,8,'#d9d4cc');}
}
/** Bus stop: a roof, a back panel, a bench and the round sign. */
function busStop(c,p,x,base,W){R(c,x,base-130,W,10,'#9fc6c9',5,'#76a5a8',1.5);L(c,x+8,base-120,x+8,base,'#9aa8aa',5);L(c,x+W-8,base-120,x+W-8,base,'#9aa8aa',5);
  R(c,x+14,base-116,W-28,70,'#e6f3f3aa',6,'#b8cdd0',1.2);R(c,x+20,base-110,56,40,'#fff4dc',4);E(c,x+34,base-94,6,6,'#f2b7c3');L(c,x+26,base-80,x+70,base-80,'#9fc6c9',3);
  R(c,x+20,base-38,W-40,9,WOOD,4,WOOD_D,1);L(c,x+32,base-29,x+32,base,WOOD_D,4);L(c,x+W-32,base-29,x+W-32,base,WOOD_D,4);
  L(c,x+W+18,base,x+W+18,base-150,'#9aa8aa',5);E(c,x+W+18,base-150,19,19,'#fffaf0');E(c,x+W+18,base-150,15,15,'#7fb3c9');
  R(c,x+W+7,base-157,22,11,'#fffaf0',3);E(c,x+W+11,base-145,3,3,'#fffaf0');E(c,x+W+25,base-145,3,3,'#fffaf0');}
/** Street lamp; glows warm when the "light" security item is bought. */
function lamp(c,x,base,top,dir,lit){L(c,x,base,x,top,'#a9a39b',6);c.strokeStyle='#a9a39b';c.lineWidth=5;c.beginPath();c.moveTo(x,top);c.quadraticCurveTo(x,top-20,x+dir*30,top-16);c.stroke();
  const hx=x+dir*34;if(lit){const g=c.createRadialGradient(hx,top-4,0,hx,top-4,110);g.addColorStop(0,'#ffe1a466');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(hx-110,top-114,220,220);}
  P(c,[[hx-16,top-8],[hx+16,top-8],[hx+10,top-20],[hx-10,top-20]],'#8d8a84');E(c,hx,top-6,11,6,lit?'#fff2bf':'#f3ead6');}
function camera(c,x,y,dir,has){if(has){L(c,x,y,x+dir*14,y-9,'#b79b85',5);R(c,x+dir*14-(dir<0?39:0),y-21,39,21,'#f5f2eb',7,'#a7aaa2',2);const lx=x+dir*14+(dir<0?-35:35);E(c,lx,y-11,8,9,'#7a8992');E(c,lx+dir,y-11,4,5,'#b4d9df');}
  else{R(c,x-18,y-24,36,26,'#fff6e9',8,'#d5b59a',1.2);T(c,'♧',x,y-11,15,'#9a7a62');}}
function bell(c,x,y){L(c,x,y,x,y+14,'#ac8f73',2);P(c,[[x-10,y+32],[x+10,y+32],[x+7,y+18],[x-7,y+18]],'#f0ce85');E(c,x,y+34,4,3,'#d4ad64');}
/** Blue house-number plate (the `property` hotspot). */
function plate(c,x,y,s=1){R(c,x-22*s,y-13*s,44*s,26*s,'#5f8fbf',6,'#fffaf0',2);T(c,'26',x,y+1,15*s,'#fffaf0',800);}

/* ------------------------------------------------------------ Floor props */
function scooter(c,p,cx,fy,s,worn){c.save();c.translate(cx,fy);c.scale(s,s);E(c,0,2,86,9,'#7a5e4424');
  // Wheels, kickstand, floorboard.
  for(const wx of [-54,50]){E(c,wx,-17,17,17,'#5f5552');E(c,wx,-17,8,8,'#e4dfd6');E(c,wx,-17,3,3,'#9b938d');}
  L(c,10,-14,2,0,'#8b8480',3);R(c,-44,-34,62,10,'#efe2cf',5,'#c9b49a',1.2);
  // Rounded rear body over the back wheel, with a side stripe.
  R(c,-2,-72,82,48,p.primary,24,p.dark,1.5);E(c,50,-24,22,7,p.dark);R(c,10,-54,56,6,'#ffffff50',3);
  // Leg shield and front fender.
  P(c,[[-60,-30],[-50,-98],[-34,-98],[-36,-30]],p.primary);c.strokeStyle=p.dark;c.lineWidth=1.5;c.stroke();
  c.beginPath();c.arc(-54,-22,20,Math.PI*1.05,Math.PI*1.95);c.lineWidth=7;c.strokeStyle=p.primary;c.stroke();
  // Handlebar, headlight, mirror; seat.
  R(c,-62,-110,34,9,'#6f6a6a',4);E(c,-62,-94,7,8,'#fff2bf');L(c,-36,-108,-30,-124,'#8b8480',2.5);E(c,-29,-127,6,4,'#cfe0e6');
  R(c,-4,-84,60,14,'#6f5a4f',7);R(c,4,-82,40,4,'#ffffff30',2);
  // Delivery box on the rear rack.
  R(c,22,-92,58,8,'#8b8480',3);R(c,18,-146,66,56,'#fff6e6',10,p.dark,2);R(c,18,-124,66,11,p.primary,2);heart(c,51,-133,.42,p.primary);R(c,16,-150,70,11,p.dark,5);
  if(worn){R(c,14,-176,74,20,'#f7d995',6,'#d2a85c',1);T(c,'CẦN KIỂM',51,-166,11,'#94643d');}
  c.restore();}
/** Flag pole with the tour flag, next to the itinerary map stand. */
function flagStand(c,p,w,x0,x1,fy,worn,port){const mx=x0+(x1-x0)*.38,fx=x1-18,wave=w.reduced?0:Math.sin(w.time*2.4)*5;
  E(c,(x0+x1)/2,fy+2,(x1-x0)/2+6,8,'#7a5e4420');
  L(c,mx-40,fy,mx-24,fy-66,WOOD_D,5);L(c,mx+40,fy,mx+24,fy-66,WOOD_D,5);
  R(c,mx-58,fy-120,116,70,'#fffaf0',8,WOOD_D,2.5);R(c,mx-51,fy-113,102,56,'#e8efcf',4);
  L(c,mx-40,fy-66,mx-10,fy-90,'#a7c4d6',8);L(c,mx-10,fy-90,mx+38,fy-100,'#a7c4d6',8);
  c.setLineDash([5,5]);L(c,mx-40,fy-72,mx+34,fy-104,p.dark,2);c.setLineDash([]);
  for(const [dx,dy] of [[-40,-72],[0,-92],[34,-104]]){E(c,mx+dx,fy+dy,6,6,'#fffaf0');E(c,mx+dx,fy+dy,3.5,3.5,p.primary);}
  T(c,'✦',mx+38,fy-70,port?18:15,p.dark);
  R(c,fx-12,fy-12,24,14,'#d7c2a8',4,WOOD_D,1);L(c,fx,fy-10,fx,fy-(port?190:180),'#b4a597',5);E(c,fx,fy-(port?192:182),5,5,'#f3d590');
  const ty=fy-(port?186:176);c.beginPath();c.moveTo(fx,ty);c.quadraticCurveTo(fx-30,ty+8+wave,fx-62,ty+20+wave);c.lineTo(fx,ty+42);c.closePath();c.fillStyle=p.primary;c.fill();c.strokeStyle=p.dark;c.lineWidth=1.5;c.stroke();
  heart(c,fx-20,ty+22+wave*.4,.34,'#fffaf0');
  if(worn){R(c,mx-40,fy-146,80,20,'#f7d995',6,'#d2a85c',1);T(c,'CẦN KIỂM',mx,fy-136,11,'#94643d');}
}
function parcelCage(c,p,x0,x1,fy,locked,port){const W=x1-x0,top=fy-(port?118:108);E(c,(x0+x1)/2,fy+2,W/2+6,7,'#7a5e4420');
  const tags=[p.primary,'#a9d6c6','#b6c9e3'];
  parcel(c,x0+8,fy-8,W*.5,34,'#e2b68a',tags[0]);parcel(c,x0+W*.55,fy-8,W*.38,28,'#d8a879',tags[1]);parcel(c,x0+14,fy-44,W*.36,26,'#d8a879',tags[2]);parcel(c,x0+W*.48,fy-38,W*.42,36,'#e2b68a',p.light);parcel(c,x0+W*.2,fy-72,W*.46,24,'#e2b68a',tags[1]);
  R(c,x0,top,W,6,'#b5b8b4',3);R(c,x0,fy-10,W,6,'#b5b8b4',3);for(let x=x0+2;x<=x1-2;x+=W/6)L(c,x,top+3,x,fy-6,'#b5b8b4',2.2);L(c,x0,top+(fy-top)/2,x1,top+(fy-top)/2,'#c6c9c4',1.5);
  for(const wx of [x0+10,x1-10])E(c,wx,fy-2,6,6,'#7b7471');
  if(locked){R(c,x1-26,top+16,20,24,'#d2c290',5,'#a59470',1);c.beginPath();c.arc(x1-16,top+16,7,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=3;c.stroke();}}
function luggage(c,p,x0,x1,fy,locked,port){const W=x1-x0;E(c,(x0+x1)/2,fy+2,W/2+10,7,'#7a5e4420');
  // Big rolling suitcase with stickers, a small one, a backpack and a rolled mat.
  L(c,x0+22,fy-96,x0+22,fy-112,'#8c8580',3);L(c,x0+40,fy-96,x0+40,fy-112,'#8c8580',3);L(c,x0+20,fy-112,x0+42,fy-112,'#8c8580',4);
  R(c,x0+6,fy-98,50,92,p.primary,9,p.dark,2);for(const k of [16,31,46])L(c,x0+k,fy-92,x0+k,fy-12,'#ffffff40',2);E(c,x0+22,fy-70,7,7,'#f6dfa3');heart(c,x0+40,fy-44,.3,'#fffaf0');
  for(const wx of [x0+14,x0+48])E(c,wx,fy-3,4,4,'#6e6360');
  R(c,x0+52,fy-56,40,50,'#f2c96f',8,'#c89f4f',1.5);R(c,x0+60,fy-62,24,8,'#c89f4f',3);E(c,x0+72,fy-30,5,5,'#fffaf0');
  E(c,x1-18,fy-30,20,26,'#8fbfa6');R(c,x1-30,fy-34,24,18,'#a8d2bb',6);L(c,x1-26,fy-54,x1-10,fy-54,'#6f9f86',3);
  R(c,x0+18,fy-126,60,14,'#e6a9a0',7,'#c78c83',1);
  if(locked){R(c,x0+56,fy-80,16,18,'#d2c290',4,'#a59470',1);c.beginPath();c.arc(x0+64,fy-80,5,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=2.5;c.stroke();}
  if(port)T(c,'✈',x0+72,fy-100,18,p.dark);}
/** The front counter: a wooden desk with the career's plate and top things. */
function counter(c,p,w,x0,x1,fy,port){const W=x1-x0,h=port?66:60,tour=w.career==='tour_guide';
  E(c,(x0+x1)/2,fy+3,W/2+8,9,'#7a5e4420');
  R(c,x0,fy-h,W,h,tour?p.light:'#f0d7b6',10,'#b99476',2);R(c,x0-8,fy-h-12,W+16,16,'#e6bd99',7,'#b99476',2);R(c,x0-3,fy-h-10,W+6,5,'#f5d7b6',3);
  const label=w.words().counter,size=port?17:13,pw=Math.min(W-16,fit(c,label,W-30,size)*label.length*.62+30);
  R(c,(x0+x1)/2-pw/2,fy-h+6,pw,port?30:26,'#fffaf0',12,'#c7ad90',1.5);T(c,label,(x0+x1)/2,fy-h+6+(port?15:13),fit(c,label,pw-14,size),p.dark);
  const top=fy-h-12;
  if(tour){// clipboard list, bell, maps and a mini flag
    R(c,x0+14,top-40,36,42,'#d7b58f',4);R(c,x0+18,top-34,28,34,'#fffaf0',2);for(let i=0;i<3;i++){L(c,x0+22,top-26+i*9,x0+26,top-22+i*9,p.primary,2);L(c,x0+29,top-24+i*9,x0+42,top-24+i*9,'#c2b8b1',2);}
    c.beginPath();c.arc(x0+W*.5,top,12,Math.PI,0);c.fillStyle='#f0ce85';c.fill();E(c,x0+W*.5,top-13,3,3,'#d4ad64');
    R(c,x1-60,top-16,40,16,'#bfe0d8',3,'#8fb8ad',1);R(c,x1-56,top-26,40,12,'#f6dfa3',3,'#c9ab6d',1);
    L(c,x1-16,top,x1-16,top-44,'#b4a597',2.5);P(c,[[x1-16,top-44],[x1-38,top-37],[x1-16,top-30]],p.primary);
  }else{// the parcel scale with a parcel on it, a stamp and envelopes
    const sx=x0+W*.32;R(c,sx-32,top-8,64,9,'#dfe3e3',3,'#9aa3a4',1.5);parcel(c,sx-22,top-8,44,30,'#e2b68a',p.primary);
    R(c,sx+34,top-34,30,26,'#f4f6f4',5,'#9aa3a4',1.5);R(c,sx+37,top-30,24,12,'#cfe8d8',2);T(c,'2,4',sx+49,top-24,port?11:10,'#4f7f63',800);L(c,sx+49,top-8,sx+49,top,'#9aa3a4',3);
    R(c,x1-64,top-10,44,10,'#fffaf0',2,'#d3b7a1',1);R(c,x1-58,top-16,44,10,'#fdf3df',2,'#d3b7a1',1);
    R(c,x1-100,top-22,12,16,WOOD_D,3);R(c,x1-104,top-8,20,8,p.primary,3);
  }
}
/** Easel with the route map (delivery) or the route board (tour). */
function easel(c,p,w,cx,fy,port){const tour=w.career==='tour_guide',bw=port?96:100,bh=port?84:80,top=fy-(port?140:134);
  E(c,cx,fy+2,40,6,'#7a5e4420');L(c,cx-26,fy,cx-12,top+20,WOOD_D,5);L(c,cx+26,fy,cx+12,top+20,WOOD_D,5);L(c,cx,fy-6,cx,top+30,'#8f6c52',4);
  R(c,cx-bw/2-5,top-5,bw+10,bh+10,WOOD,8,WOOD_D,2);R(c,cx-bw/2,top,bw,bh,tour?'#eef3df':'#f3f5ee',5);
  if(tour){P(c,[[cx-bw/2+4,top+bh-4],[cx-bw/2+24,top+bh-34],[cx-bw/2+44,top+bh-4]],'#a8cfa6');R(c,cx+8,top+bh-20,bw/2-12,16,'#bfe0e6',3);
    c.setLineDash([5,4]);c.strokeStyle=p.dark;c.lineWidth=2.5;c.beginPath();c.moveTo(cx-bw/2+14,top+bh-14);c.quadraticCurveTo(cx-10,top+10,cx+bw/2-14,top+22);c.stroke();c.setLineDash([]);
    for(const [dx,dy,n] of [[-bw/2+14,bh-14,'1'],[-6,26,'2'],[bw/2-14,22,'3']]){E(c,cx+dx,top+dy,9,9,'#fffaf0');T(c,n,cx+dx,top+dy,port?12:11,p.dark,800);}
  }else{for(const yy of [.3,.66])L(c,cx-bw/2+3,top+bh*yy,cx+bw/2-3,top+bh*yy,'#dfe3e3',6);for(const xx of [.28,.7])L(c,cx-bw/2+bw*xx,top+3,cx-bw/2+bw*xx,top+bh-3,'#dfe3e3',6);
    E(c,cx+bw*.22,top+bh*.48,10,7,'#bfe0c8');
    c.setLineDash([5,4]);c.strokeStyle=p.primary;c.lineWidth=3;c.beginPath();c.moveTo(cx-bw/2+12,top+bh-10);c.lineTo(cx-bw/2+bw*.28,top+bh*.66);c.lineTo(cx+bw*.2,top+bh*.3);c.lineTo(cx+bw/2-12,top+14);c.stroke();c.setLineDash([]);
    E(c,cx-bw/2+12,top+bh-10,5,5,p.dark);E(c,cx+bw/2-12,top+11,8,8,p.primary);P(c,[[cx+bw/2-18,top+14],[cx+bw/2-6,top+14],[cx+bw/2-12,top+26]],p.primary);E(c,cx+bw/2-12,top+11,3,3,'#fffaf0');}
}
function ledgerTable(c,p,w,x0,x1,fy,port){const cx=(x0+x1)/2,W=x1-x0+(port?24:12),top=fy-(port?58:52);E(c,cx,fy+2,W/2,7,'#7a5e4420');
  L(c,cx-W/2+10,top+12,cx-W/2+14,fy,WOOD_D,4);L(c,cx+W/2-10,top+12,cx+W/2-14,fy,WOOD_D,4);
  R(c,cx-W/2,top,W,14,'#f0d2ad',6,'#b99476',2);R(c,cx-W/2+6,top+14,W-12,port?30:24,'#d4b391',6);
  const label=w.words().ledger;T(c,label,cx,top+14+(port?15:12),fit(c,label,W-18,port?16:11),'#6b5040',800);
  R(c,cx-W/2+10,top-22,34,22,'#9fc6c9',4,'#76a5a8',1.5);E(c,cx-W/2+27,top-22,6,3,'#f3d590');
  R(c,cx+2,top-14,W/2-12,14,'#fff8e7',3,'#d9b596',1);L(c,cx+W/4-4,top-13,cx+W/4-4,top,p.primary,1.5);}
function aFrame(c,p,w,cx,fy,port){const open=w.c?.open,s=w.words(),label=open?s.open_sign:s.closed_sign,bw=port?128:112,bh=port?50:44,top=fy-bh-26;
  E(c,cx,fy+2,bw/2,6,'#7a5e4420');L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,WOOD_D,4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,WOOD_D,4);
  R(c,cx-bw/2,top,bw,bh,'#fdf7e8',14,'#b99171',2);T(c,label,cx,top+bh/2-(port?3:4),fit(c,label,bw-18,port?17:13,800),open?p.dark:'#9a8272',800);
  for(let i=0;i<3;i++)E(c,cx-14+i*14,top+bh-9,3,3,open?p.primary:'#d6c6b6');}
function bench(c,p,x0,x1,fy,garden){const W=x1-x0;L(c,x0+12,fy-16,x0+12,fy,'#af8b6c',6);L(c,x1-12,fy-16,x1-12,fy,'#af8b6c',6);R(c,x0,fy-24,W,12,p.mint,6,'#b8a58e',1);R(c,x0+4,fy-52,W-8,22,p.mint,8,'#b8a58e',1);
  for(let x=x0+14;x<x1-10;x+=18)L(c,x,fy-48,x,fy-34,'#ffffff55',2);if(garden)bloom(c,x1-6,fy-58,11,p.primary);}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,f=F.land,tour=w.career==='tour_guide',items=w.c?.ops?.security?.items||[];
  E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#e3b694',38);
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  pole(c,96,f.base,170);pole(c,1108,f.base,186);wires(c,96,1108,170,186,40);
  // Left house (bus stop / ground window), bay, right house.
  house(c,78,214,222,f.base,'#f7e0aa',{wins:2,ww:40,wh:50});
  if(tour){tree(c,888,f.base,262,1.15);R(c,782,408,216,f.base-408,'#e8d4b8',6,'#cdb293',1.5);for(let x=790;x<995;x+=24)L(c,x,410,x,f.base,'#dcc6a8',1);}
  else{house(c,780,236,220,f.base,'#f6d0c8',{wins:2,ww:36,wh:44,shut:'#e8a9a0'});R(c,796,336,188,f.base-336,'#f2dccf',4,'#d6b394',1.5);R(c,806,346,168,f.base-352,'#e2d3c3',3);for(let y=352;y<f.base-8;y+=10)L(c,808,y,972,y,'#d2c1ae',1);
    helmetRack(c,p,806,360);fuelCan(c,948,f.base);parcel(c,810,f.base,40,28,'#e2b68a',p.primary);parcel(c,815,f.base-28,30,20,'#d8a879','#a9d6c6');}
  house(c,1000,222,126,f.base,'#cfe6d6',{wins:1,ww:42,wh:50});
  if(!tour)tree(c,1004,f.base,238,.9);
  // Main building: upper floor, name band, open ground floor.
  R(c,300,184,480,f.base-182,'#fff4e2',6,'#d6b394',2);R(c,294,170,492,20,ROOF,8,ROOF_D,1.5);for(let x=300;x<780;x+=16)E(c,x+8,190,8,4,ROOF);
  L(c,420,164,420,122,'#b89478',5);L(c,740,164,740,122,'#b89478',5);
  for(let i=0;i<4;i++)win(c,360+i*120,204,40,40);balcony(c,318,266,444,false);
  R(c,300,276,480,26,p.primary,4);R(c,300,300,480,4,p.dark,0);for(let i=0;i<8;i++){const x=330+i*60;if(i%2)heart(c,x,294,.3,'#fffaf0');else E(c,x,288,4,4,'#fffaf0');}
  opening(c,w,322,318,436,f.base-318);
  if(tour){postcardWall(c,p,w,338,352,218,104,false);travelPoster(c,p,592,338,120,72);R(c,580,420,150,10,'#e8d0b0',3);E(c,742,352,12,12,'#fffaf0');L(c,742,352,742,345,'#8f7f72',1.5);L(c,742,352,747,354,'#8f7f72',1.5);}
  else{parcelShelf(c,p,w,338,352,226,104,false);R(c,596,338,108,64,'#f3f5ee',5,'#d6b394',2);for(let i=0;i<3;i++)L(c,606,352+i*14,694,352+i*14,i?'#dfe3e3':p.primary,4);E(c,720,352,12,12,'#fffaf0');L(c,720,352,720,345,'#8f7f72',1.5);L(c,720,352,725,354,'#8f7f72',1.5);}
  // Ground floor of the left house.
  if(tour)busStop(c,p,90,f.base,186);
  else{R(c,222,370,64,56,GLASS,5,'#d6b394',2);L(c,254,370,254,426,'#fff8ec',3);R(c,214,426,80,10,'#ecd3b6',3,'#c9a585',1.2);R(c,100,330,100,f.base-330,'#e8d0ad',5,'#cdb293',1.5);R(c,108,338,84,f.base-338,'#dcc3a2',3);}
  street(c,f,440,760);
  lamp(c,tour?1010:790,f.base,196,-1,items.includes('light'));
  streetBoard(c,p,1013,322);
  plate(c,332,232);camera(c,280,238,-1,items.includes('camera'));if(items.includes('bell'))bell(c,768,304);
  if(tour)minibus(c,p,790,f.base-2,200,p.title,false);
  c.restore();
  signBoard(c,p,...f.sign);
}
function portRoom(w,p){const c=w.ctx,f=F.port,tour=w.career==='tour_guide',items=w.c?.ops?.security?.items||[];
  E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#e1b594',33);
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  pole(c,36,f.base,198);pole(c,668,f.base,214);wires(c,36,668,198,214,30);
  house(c,24,238,116,f.base,'#f7e0aa',{wins:0,bal:false});
  if(tour){tree(c,610,f.base,300,1);minibus(c,p,540,f.base-2,200,p.title,true);}
  else{house(c,520,256,180,f.base,'#f6d0c8',{wins:1,ww:40,wh:44,shut:'#e8a9a0'});R(c,532,352,148,f.base-352,'#f2dccf',4,'#d6b394',1.5);helmetRack(c,p,534,366,2);fuelCan(c,630,f.base);}
  // Main building.
  R(c,140,212,380,f.base-210,'#fff4e2',6,'#d6b394',2);R(c,134,198,392,20,ROOF,8,ROOF_D,1.5);for(let x=140;x<520;x+=16)E(c,x+8,218,8,4,ROOF);
  for(let i=0;i<3;i++)win(c,236+i*100,228,40,40);balcony(c,200,300,300,false);
  R(c,140,310,380,24,p.primary,4);R(c,140,332,380,4,p.dark,0);for(let i=0;i<6;i++){const x=175+i*62;if(i%2)heart(c,x,327,.3,'#fffaf0');else E(c,x,321,4,4,'#fffaf0');}
  opening(c,w,200,350,302,f.base-350);
  if(tour){postcardWall(c,p,w,210,390,150,100,true);travelPoster(c,p,382,378,106,64);}
  else{parcelShelf(c,p,w,210,390,150,100,true);R(c,384,378,100,56,'#f3f5ee',5,'#d6b394',2);for(let i=0;i<3;i++)L(c,394,390+i*13,474,390+i*13,i?'#dfe3e3':p.primary,4);}
  street(c,f,250,470);
  lamp(c,528,f.base,262,1,items.includes('light'));
  streetBoard(c,p,30,282,1.6);
  plate(c,168,240,.95);camera(c,112,258,-1,items.includes('camera'));if(items.includes('bell'))bell(c,510,336);
  c.restore();
  signBoard(c,p,...f.sign);
}

/* ------------------------------------------------------------ Props */
function streetProps(w,p){const c=w.ctx,port=w.isPortrait(),pl=w.plan(),b=pl.blocks,tour=w.career==='tour_guide',tier=w.c?.ops?.property?.tier||'cozy',
  locked=(w.c?.ops?.security?.items||[]).includes('lock'),worn=(w.c?.ops?.equipment?.condition??100)<100,out=[];
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>tour?luggage(c,p,wh[0]-6,wh[2]+10,wh[3],locked,port):parcelCage(c,p,wh[0],wh[2],wh[3],locked,port)]);
  out.push([wb[3],()=>tour?flagStand(c,p,w,wb[0],wb[2],wb[3],worn,port):scooter(c,p,(wb[0]+wb[2])/2,wb[3],port?.95:1,worn)]);
  out.push([co[3],()=>counter(c,p,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>easel(c,p,w,(ev[0]+ev[2])/2,ev[3],port)]);
  out.push([fi[3],()=>ledgerTable(c,p,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>aFrame(c,p,w,(dr[0]+dr[2])/2,dr[3],port)]);
  if(tier!=='cozy'){const [x0,,x1,y1]=pl.bench;out.push([y1,()=>bench(c,p,x0,x1,y1,tier==='garden')]);}
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+4,()=>plantAt(c,x,y,.62)]);
  return out;
}

export default {
  id:'street',
  plan:PLAN,
  room(w,p){(w.isPortrait()?portRoom:landRoom)(w,p);},
  props(w,p){return streetProps(w,p);},
};
