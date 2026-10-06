/** Station scene (police, "Công an phường Mây"): the reception room of a ward police station. The lost-and-found
 * cabinet with its tagged boxes (warehouse), the residence-desk shelf of file boxes by tổ (shelf), the noticeboard
 * with the scam warning and the hotline (evidence), the reception desk (workbench = the computer and the files,
 * counter = the queue-number machine, the duty phone and the stamp pad), a row of waiting chairs (property), the
 * small desk of the duty book (finance), a window onto the lane and the door with its sign.
 * Nothing official is drawn: no emblem, no weapon, only the ward's own fictional sign.
 * The walking plan is homestay's (scenes/lodging.js), like the ward and the nursery. Plan schema: see scenes/shop.js. */
import {R,E,L,T,fit,signBoard,streetBoard} from './kit.js';
import {PLAN} from './lodging.js';

export {PLAN};

const BLUE='#2f5d8a',BLUE_L='#d6e4f2',SKY='#e6eef7',STEEL='#9aa8b2',STEEL_D='#6f7d87',CREAM='#fbfaf6',RED='#d64545',AMBER='#e0a33a',WOOD='#c9a27e',WOOD_D='#9a7656';

/* ------------------------------------------------------------ small pieces */
function floorTiles(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=44)for(let col=0,xx=x;xx<x+w;col++,xx+=44){c.fillStyle=['#eef1f5','#e3e8ee'][(row+col)%2];c.fillRect(xx,yy,44,44);}
  c.restore();}
/** A small round badge (the ward's own: a blue disc with a white star-less shield outline). */
function badge(c,x,y,s){E(c,x,y,s,s,BLUE);c.beginPath();c.moveTo(x,y-s*.6);c.lineTo(x+s*.5,y-s*.35);c.lineTo(x+s*.42,y+s*.2);c.lineTo(x,y+s*.6);c.lineTo(x-s*.42,y+s*.2);c.lineTo(x-s*.5,y-s*.35);c.closePath();
  c.strokeStyle='#ffffff';c.lineWidth=Math.max(1.5,s*.14);c.stroke();}
/** The lost-and-found cabinet: glass doors, boxes with tags, an umbrella and a helmet (warehouse). */
function lostCabinet(c,x,y,w,h){E(c,x+w/2,y+h+4,w/2+6,5,'#5a6b7322');R(c,x,y,w,h,'#f4f7f8',8,STEEL_D,2);
  for(let i=0;i<3;i++){const yy=y+8+i*(h-12)/3;L(c,x+4,yy+(h-12)/3-4,x+w-4,yy+(h-12)/3-4,'#b9c5cc',2);
    for(let j=0;j<2;j++){R(c,x+8+j*(w-16)/2,yy+4,(w-16)/2-6,(h-12)/3-14,['#f7e6b5','#cfe3f4','#e8d5f0'][(i+j)%3],3,'#b9a98a',1);R(c,x+10+j*(w-16)/2,yy+6,10,6,'#ffffff',1.5,'#c4ccd0',1);}}
  R(c,x+w-8,y-30,6,30,'#3b5a7a',2);E(c,x+w-5,y-32,9,5,'#3b5a7a');}
/** The residence desk's shelf: file boxes by tổ (shelf). */
function fileShelf(c,p,x,y,w,h,label,fs){R(c,x,y,w,h,'#ffffff',8,STEEL_D,2);R(c,x,y,w,22,BLUE,[8,8,0,0]);T(c,label,x+w/2,y+11,fit(c,label,w-10,fs),'#ffffff',800);
  for(let r=0;r<3;r++)for(let k=0;k<4;k++){const bw=(w-14)/4,bh=(h-34)/3;R(c,x+6+k*bw,y+28+r*bh,bw-3,bh-4,['#dbe6f1','#f3e3c3','#e2efe0','#f2dcdc'][(r+k)%4],3,'#b9c5cc',1);
    T(c,String(r*4+k+1),x+6+k*bw+(bw-3)/2,y+28+r*bh+(bh-4)/2,9,p.dark,800);}}
/** The noticeboard: a scam warning, the ward hotline, the residence steps (evidence). */
function noticeBoard(c,p,x,y,w,h){R(c,x,y,w,h,WOOD,6,WOOD_D,2);R(c,x+5,y+5,w-10,h-10,'#e9dcc6',4);
  R(c,x+10,y+10,w*.46,h*.55,'#fff4c2',2,'#d9c58a',1);T(c,'⚠',x+10+w*.23,y+22,13,'#c0533f');for(let i=0;i<3;i++)L(c,x+16,y+34+i*7,x+w*.5,y+34+i*7,'#c9b98a',1.5);
  R(c,x+w*.54,y+12,w*.38,h*.38,'#ffffff',2,'#c4ccd0',1);T(c,'☎',x+w*.73,y+26,12,BLUE);L(c,x+w*.58,y+36,x+w*.88,y+36,'#c4ccd0',1.5);
  R(c,x+12,y+h*.68,w-24,h*.22,'#dfeaf6',2,'#b9c5cc',1);for(let i=0;i<3;i++)E(c,x+20+i*(w-40)/2,y+h*.79,3,3,BLUE);
  E(c,x+12,y+12,2.5,2.5,RED);E(c,x+w*.55,y+14,2.5,2.5,BLUE);
  T(c,'BẢNG TIN',x+w/2,y-9,fit(c,'BẢNG TIN',w,10),p.dark,800);}
/** The window onto the lane: a tamarind tree, a motorbike going by. */
function laneWindow(c,x,y,w,h,t){R(c,x-8,y-8,w+16,h+16,'#a9bccf',10,'#7f93a8',2);
  c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#d9eaf6');g.addColorStop(1,'#f3efe3');c.fillStyle=g;c.fillRect(x,y,w,h);
  R(c,x,y+h*.72,w,h*.28,'#c9c3b5',0);for(let k=0;k<4;k++)L(c,x+k*w/4+10,y+h*.86,x+k*w/4+30,y+h*.86,'#f4f0e6',3);
  R(c,x+w*.08,y+h*.25,w*.05,h*.5,'#8a6b52',2);E(c,x+w*.11,y+h*.22,w*.18,h*.22,'#7fae86');
  const m=(t*30)%(w+80)-40;R(c,x+m,y+h*.66,26,10,'#c0533f',4);E(c,x+m+4,y+h*.78,5,5,'#3e3e44');E(c,x+m+22,y+h*.78,5,5,'#3e3e44');E(c,x+m+12,y+h*.6,5,6,'#f2c9a0');
  c.restore();L(c,x+w/2,y,x+w/2,y+h*.62,'#7f93a8',4);L(c,x,y+h*.4,x+w,y+h*.4,'#7f93a8',3);}
/** Waiting chairs in a row (property) with a ticket on one. */
function chairs(c,x,bottom,n,s){c.save();c.translate(x,bottom);c.scale(s,s);E(c,n*22,2,n*26,5,'#5a6b731c');
  for(let i=0;i<n;i++){const cx=i*46;R(c,cx,-44,40,10,BLUE,4);R(c,cx+2,-70,36,26,BLUE_L,6,'#9fb3c7',1.5);L(c,cx+6,-34,cx+6,-2,STEEL_D,3);L(c,cx+34,-34,cx+34,-2,STEEL_D,3);}
  R(c,50,-50,12,7,'#fff6c9',1.5,'#c9b98a',1);c.restore();}
/** The reception desk: the computer and the file trays (workbench end), the queue machine, the duty phone and the stamp (counter end). */
function station(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,t=w.reduced?0:w.time,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#5a6b731d');
  R(c,x0,top+16,x1-x0,bottom-top-16,'#e5ecf3',10,'#9fb3c7',2);for(let k=1;k<4;k++)L(c,x0+(x1-x0)*k/4,top+22,x0+(x1-x0)*k/4,bottom-6,'#cbd7e3',1.5);
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2+8;R(c,cx-pw/2,py,pw,ph,CREAM,ph/2,'#a9bccf',2);
  const motto='ai cũng như ai · không phong bì';T(c,motto,cx,py+ph/2+1,fit(c,motto,pw-56,fs),p.dark);badge(c,cx-pw/2+18,py+ph/2,8);badge(c,cx+pw/2-18,py+ph/2,8);
  R(c,x0-10,top,x1-x0+20,22,'#f3f6f9',8,'#b9c7d4',2);
  // Computer, file trays.
  R(c,a-34,top-62,56,40,'#3b4a52',5);R(c,a-30,top-58,48,32,'#cfe2f3',3);L(c,a-26,top-50,a+10,top-50,BLUE,2);L(c,a-26,top-42,a+2,top-42,BLUE,2);R(c,a-10,top-22,16,8,'#55606a',2);
  for(let i=0;i<3;i++)R(c,a+30,top-14-i*6,34,6,['#f7e6b5','#cfe3f4','#f6d2d2'][i],1.5,'#c4ccd0',1);
  // Queue-number machine (the number turns), duty phone, stamp pad.
  R(c,b-70,top-50,30,50,'#55606a',5);R(c,b-66,top-44,22,16,'#1d2730',3);const num=String(12+Math.floor(t*.2)%40).padStart(3,'0');T(c,num,b-55,top-36,10,'#ff7a6b',800);
  R(c,b-30,top-18,34,18,'#55606a',5);R(c,b-26,top-26,26,10,'#6f7d87',5);
  const ring=!w.reduced&&Math.floor(t*1.5)%6===0;if(ring){c.globalAlpha=.35;E(c,b-13,top-24,18,10,AMBER);c.globalAlpha=1;}
  R(c,b+22,top-16,30,14,'#7a4a3a',3);R(c,b+28,top-30,18,14,'#2f3a44',3);
}
function wallClock(c,x,y,r){E(c,x,y,r+3,r+3,BLUE);E(c,x,y,r,r,CREAM);for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,x+Math.cos(a)*r*.92,y+Math.sin(a)*r*.92,STEEL_D,1.5);}
  L(c,x,y,x,y-r*.6,'#3e3e44',2.5);L(c,x,y,x+r*.45,y+r*.1,'#3e3e44',2);}
function bookDesk(c,x,y,wd){E(c,x+wd/2,y+48,wd/2+8,6,'#5a6b731c');L(c,x+10,y+12,x+10,y+46,WOOD_D,5);L(c,x+wd-10,y+12,x+wd-10,y+46,WOOD_D,5);
  R(c,x-4,y,wd+8,14,WOOD,6,WOOD_D,1.5);R(c,x+wd*.1,y-14,wd*.4,14,'#2f5d8a',2,'#22476b',1);R(c,x+wd*.55,y-10,wd*.3,10,'#ffffff',2,'#cfc4b5',1);R(c,x+wd*.86,y-14,6,14,'#2f5d8a',1.5);}
function doorSign(c,p,cx,bottom,open,words,port){const bw=port?150:120,bh=port?40:32,fs=port?16:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,STEEL_D,4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,STEEL_D,4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,CREAM,13,'#a9bccf',2);const s=open?words.open_sign:words.closed_sign;T(c,s,cx,bottom-bh/2-23,fit(c,s,bw-20,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,'#5fb38a');}
/** A helmet rack by the door: the patrol's helmets and a raincoat. */
function helmetRack(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);E(c,0,0,26,5,'#5a6b731c');
  L(c,0,0,0,-92,WOOD_D,5);L(c,-18,-80,18,-80,WOOD_D,4);E(c,-16,-74,11,9,BLUE);E(c,16,-74,11,9,'#3f78ad');R(c,-10,-66,20,40,'#e0a33a',6,'#b8822a',1.5);c.restore();}
function security(c,p,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#9aa8b2',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
  if(items.includes('lock')){const lk=port?[560,470]:[262,420];R(c,lk[0],lk[1],16,18,'#d8c596',4,'#a09675',1.2);}
}

/* -------------------------------------------------------------- the room */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,605,724,503,30,'#9fb0aa22');R(c,85,165,1030,550,'#a9bccf',35);R(c,96,168,1008,533,'#fbfcfd',30,'#b4c5d6',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#e6eef766';c.fillRect(108,179,984,140);R(c,108,380,984,6,'#cbd7e3',0);R(c,108,386,984,4,BLUE,0);c.restore();
  floorTiles(c,108,445,984,244,16);R(c,108,438,984,10,'#cbd7e3',3);
  R(c,108,179,984,18,BLUE,[22,22,0,0]);
  lostCabinet(c,200,330,96,110);
  streetBoard(c,p,310,322);
  wallClock(c,440,350,24);
  laneWindow(c,512,320,206,108,t);
  fileShelf(c,p,730,312,86,128,wd.shelf.toUpperCase(),10);
  noticeBoard(c,p,830,330,90,72);
  chairs(c,940,450,3,.95);
  R(c,930,660,120,16,'#cbd7e3',8,'#a9bccf',1);
  security(c,p,items,false);
  signBoard(c,p,370,64,460,106);
}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,350,857,324,23,'#9fb0aa22');R(c,22,114,656,738,'#a9bccf',31);R(c,29,117,642,724,'#fbfcfd',26,'#b4c5d6',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);c.fillStyle='#e6eef766';c.fillRect(40,139,620,170);c.restore();
  floorTiles(c,40,506,620,323,15);R(c,40,500,620,10,'#cbd7e3',3);
  R(c,40,139,620,17,BLUE,[21,21,0,0]);
  lostCabinet(c,520,392,90,112);
  streetBoard(c,p,548,186,1.6);
  noticeBoard(c,p,70,330,120,96);
  laneWindow(c,230,332,160,136,t);
  fileShelf(c,p,405,330,105,170,wd.shelf.toUpperCase(),14);
  R(c,465,818,128,16,'#cbd7e3',8,'#a9bccf',1);
  security(c,p,items,true);
  signBoard(c,p,135,30,430,106);
}

function landProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([586,()=>station(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>helmetRack(c,1040,562,1)]);
  out.push([620,()=>{bookDesk(c,140,572,110);T(c,wd.ledger,195,604,fit(c,wd.ledger,90,11),p.dark);}]);
  out.push([668,()=>doorSign(c,p,988,668,open,wd,false)]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([655,()=>station(w,p,215,515,570,655,290,440,16,true)]);
  out.push([652,()=>helmetRack(c,98,652,.95)]);
  out.push([700,()=>chairs(c,60,700,2,.8)]);
  out.push([746,()=>{bookDesk(c,556,700,98);T(c,wd.ledger,605,731,fit(c,wd.ledger,84,16),p.dark);}]);
  out.push([808,()=>doorSign(c,p,527,808,open,wd,true)]);
  return out;}

export default {
  id:'station',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
